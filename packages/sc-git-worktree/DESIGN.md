# sc-git-worktree Design

## Core Principles

1. **Git is source of truth** - Always query git for actual state
2. **JSONL is supplemental metadata** - Tracks owner, created date, purpose
3. **Auto-reconciliation** - JSONL stays in sync via scan
4. **Safe defaults** - Never delete unmerged or remote-ahead branches without explicit approval

## Branch Tracking (JSONL)

### Purpose

The tracking file (`worktree-tracking.jsonl`) stores metadata that git doesn't capture:
- **owner** - Who created the branch (from first commit author)
- **created** - When it was created (from first commit date)
- **purpose** - Why it was created (user-provided)

### Entry Lifecycle

| State | local_worktree | remote_exists | Action |
|-------|----------------|---------------|--------|
| Active worktree | true | true | Keep |
| Local only (not pushed) | true | false | Keep |
| Orphaned remote | false | true | **Keep** until cleanup deletes remote |
| Fully cleaned | false | false | **Remove** from JSONL |

Key rule: Entry is only removed when **both** local worktree and remote branch are gone.

### Schema

```json
{
  "branch": "feature/login",
  "owner": "Rand Lee",
  "created": "2024-01-15T10:30:00Z",
  "purpose": "implement OAuth login",
  "path": "/path/to/worktrees/feature/login",
  "local_worktree": true,
  "remote_exists": true,
  "remote_ahead": 0
}
```

## Operations

### Scan (default)

Reconciles existing JSONL entries with git state:

1. Load JSONL entries
2. For each entry:
   - Update `local_worktree` (does path exist?)
   - Update `remote_exists` (does `origin/<branch>` exist?)
   - Update `remote_ahead` (commits on remote not in local)
   - If `!local_worktree && !remote_exists` → remove entry
3. Save JSONL
4. Report status

### Scan --all

Discovers all remote branches and adds to JSONL:

1. Run default scan first
2. Query all remote branches (e.g., `feature/*`, `hotfix/*`)
3. For each branch not in JSONL:
   - Get first unique commit → extract author + date
   - Add entry with real owner/created
4. Enables cleanup by owner across large repos

### Create

1. Create worktree via git
2. Add JSONL entry with:
   - owner = git config user.name
   - created = now
   - purpose = user-provided
   - local_worktree = true
   - remote_exists = false (until pushed)

### Cleanup (default - batch)

1. Run scan/reconcile to refresh JSONL from git
2. Add untracked local worktrees to JSONL (rogue-agent safety)
2. For each entry:
   - Skip if dirty (uncommitted changes)
   - Skip if unmerged (has unique commits)
   - Skip if `remote_ahead > 0` (remote has unpulled commits)
   - Delete local worktree
   - Delete local branch
   - Delete remote branch
3. Next scan removes entries where both local and remote are gone

### Cleanup --owner="Name"

Filter cleanup to only branches created by specified owner. Useful for cleaning up your own branches in a shared repo with many contributors.

### Cleanup (orphaned remotes)

For entries where `local_worktree=false` and `remote_exists=true`:
- Local was deleted (manually or by rogue agent)
- Remote still exists
- Cleanup deletes the remote branch
- Next scan removes the entry

### Abort

Force-remove a worktree, discarding uncommitted changes:

1. Remove worktree with `--force`
2. Optionally delete branch (requires explicit approval for non-protected)
3. Update JSONL entry (local_worktree=false)
4. Remote deletion handled by subsequent cleanup

## Safety Guards

### Protected Branches

Resolved from `.sc/shared-settings.yaml` (`git.protected_branches`) or auto-detected from gitflow config and cached there:
- Worktree can be removed
- Branch is **never** deleted (local or remote)

### Remote Ahead Check

Before deleting a remote branch:
- Check `git rev-list --count <branch>..origin/<branch>`
- If `remote_ahead > 0`, preserve remote with warning
- Prevents data loss when someone pushed commits you haven't pulled

### Dirty Worktree Check

Before cleanup:
- Check `git status --porcelain`
- If dirty, report files and skip (or require `--force`)

### Unmerged Check

Before cleanup:
- Check `git branch --merged` and unique commit count
- If unmerged, preserve branch and report

## Worktree factory decision model

Create is a **factory**: every request produces exactly one of three products.
This section replaces the three accreted stacking guards (`check_needs_stack_guard`,
the `always_stack` gate, `create_stacked_worktree`) with one designed decision
model, implemented in `scripts/worktree_create.py`.

### Products

- **A. Flat worktree** (legacy, unchanged):
  `git worktree add <wt_base>/<branch> -b <branch> <base>`. No `stack/` prefix,
  no extra config, no `gh` invocation.
- **B. New stack**: identical to A - **same path**, no `stack/` prefix anywhere -
  plus, inside the new worktree: `git config rerere.enabled true` and
  `gh stack init --base <stack_root> <branch>` (`stdin=DEVNULL`; a failed init
  does not roll the worktree back - it succeeds with
  `data.stack_init = {"ok": false, "stderr": ..., "next_step": ...}`).
- **C. Stack layer** (dependent work): **no new worktree**. In the base's
  existing stack worktree: `git checkout -b <branch> <base>` then
  `gh stack add <branch>` (non-interactive form). The envelope succeeds with
  `data.path` set to the **stack worktree** (not a new directory) - legacy
  callers that read `path` from output keep working unmodified - plus
  `stacked: true`, `product: "layer"`, and the stack shape.

### Decision function

`resolve_product(input, repo) -> (product, reason)`, precedence
**Intent > Dependency > Policy > default A**, evaluated **lazily**. In the
implementation, stage 3 (a hard side-effecting verification, not a decision
branch) is run by the caller between stages 2 and 4 rather than inside
`resolve_product()` itself, so that its mandatory refusal can fire before any
mutation - see "Implementation split" below.

1. **Intent.** `input.flat` is `true` → product **A**, and NOTHING else is
   evaluated: no settings are read, no prerequisite check runs, no transcript
   entries about stacks appear. `data.flat_override` would record that the
   override suppressed a positive dependency signal, but determining that
   requires exactly the evaluation stage 1 must skip - so in practice this
   field is never populated (see "Judgment calls" below).
2. **Stack-activity probe** (cheap, unconditional, fail-closed-to-inactive).
   The repo is stack-active iff `git.always_stack` is truthy in
   `.sc/shared-settings.yaml`, OR any existing worktree carries gh-stack
   tracking (`git worktree list --porcelain` + `check_gh_stack_tracked` per
   worktree). Any error probing either signal resolves to **not** stack-active.
   **Not stack-active → product A immediately** - the legacy path is
   structurally untouched: no prerequisite check, no settings read beyond the
   one `always_stack` lookup, no new transcript entries, and a data payload
   byte-identical to the pre-guard package. This is the positive-signal rule:
   every indeterminate input resolves to A.
3. **Stack-active → mandatory prerequisite gate.** Runs `check_stack_prerequisites`
   (gh CLI, the `gh-stack` extension, the `managing-gh-stacks` skill). Missing
   → refuse `CREATE.STACK_PREREQS_MISSING` naming the three install commands.
   This is the mandatory collaborator gate and the **only** refusal that fires
   before product resolution, and it runs before any mutation, including
   `git fetch`.
4. **Dependency.** Base protected or merged into trunk → independent; else
   dependent. A trunk/protected-branch resolution failure treats the base as
   independent (positive-signal rule) - this must never surface
   `CONFIG.PROTECTED_BRANCH_NOT_SET` from create.
   - **Dependent** → product **C**, unless it is not mechanically executable:
     - the base's stack worktree has a rebase in progress, or
     - the base is unmerged but carries **no** gh-stack tracking anywhere -
       there is no stack to join, and creating one is a strictly bigger
       operation (a new 2-layer stack) than `create` performs.
     Either case refuses `CREATE.NEEDS_STACK`, with `suggested_action` routing
     to the fix (resolve the rebase; or, for the 2-layer case, the exact
     `gh stack init` command plus a pointer to the `managing-gh-stacks` skill).
5. **Policy.** Independent + `always_stack` truthy → product **B** (branch off
   `stack_root`; `resolve_stack_root` chain unchanged; `data.requested_base`
   is recorded, with a transcript step, when `input.base != stack_root`).
   Independent + `always_stack` false → product **A**.

### Implementation split

`resolve_product()` in `worktree_create.py` implements stages 4-5 (Dependency
and Policy) as a pure decision function returning a `ProductDecision`
(`product`, `reason`, plus the context - `stack_worktree_path`, `base`,
`trunk` - the caller needs to build B/C). `create_worktree_main()` drives
stages 1-3 directly (intent short-circuit, the stack-activity probe, and the
mandatory prerequisite gate) because stage 3's refusal must happen before the
unconditional `git fetch`/base-existence steps that both remaining stages
need as input; `resolve_product()` is only invoked once the repo is confirmed
stack-active, intent hasn't already resolved to A, and prerequisites have
already passed.

### Settings parsing

`get_shared_settings` / `get_always_stack_setting` / etc. are unchanged in
shape, but the no-PyYAML fallback parser in `_load_yaml`:

- strips inline comments (`raw.split("#", 1)[0]`) before coercing a scalar
  value, so `always_stack: false  # why` parses as `False`, not the string
  `"false  # why"`;
- coerces an unrecognized scalar for a boolean key (currently `always_stack`)
  to `False` rather than passing it through as a truthy string;
- these only ever run on stack-active branches of the tree now (a
  stack-inactive repo never calls into settings beyond the one `always_stack`
  read in stage 2), but must still be correct since that one read decides
  activity.

`pyyaml` is now a declared runtime requirement in `manifest.yaml` (it was an
implicit, gracefully-degraded dependency before).

## File Layout

```
<repo>/                          # Main repository
<repo>-worktrees/                # Sibling worktree directory
├── worktree-tracking.jsonl      # Tracking metadata
├── feature/
│   └── login/                   # Worktree for feature/login branch
├── hotfix/
│   └── urgent-fix/              # Worktree for hotfix/urgent-fix branch
└── develop/                     # Worktree for develop branch (protected)
```
