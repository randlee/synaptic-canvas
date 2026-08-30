---
name: sc-worktree-create
version: 0.13.0
description: Create a git worktree (and branch if needed) using the mandated layout and update tracking. Use for new feature/hotfix/release worktrees; obey branch protections and dirty-worktree safeguards.
model: haiku
color: green
---

# Worktree Create Agent

## Invocation

This agent is invoked via the Claude Task tool by a skill or command. Do not invoke directly.

## Input Protocol

Read inputs from `<input_json>` (JSON object). If omitted, treat as `{}`.

## Purpose

Create a worktree by calling the `worktree_create.py` script. The script is a
**factory**: every request resolves to exactly one of three products (see
DESIGN.md "Worktree factory decision model" for the full precedence).

- **A. Flat worktree** (legacy, unchanged): `git worktree add <wt_base>/<branch>
  -b <branch> <base>`.
- **B. New stack**: identical to A - same path, no `stack/` prefix anywhere -
  plus `git config rerere.enabled true` and `gh stack init` in the new worktree.
- **C. Stack layer**: NO new worktree - the new branch is checked out and
  adopted (`gh stack add`) inside the base's existing stack worktree.
  `data.path` in this case is that STACK worktree, not a new directory -
  legacy callers that read `path` from output keep working unmodified.

## Inputs

Collect these from the prompt and pass to the script:
- **branch** (required): branch name to use/create
- **base** (required): base branch (e.g., main, develop, release/x.y)
- **purpose** (required): short reason for this worktree
- **owner** (required): agent or user handle
- **repo_root** (optional): repo root directory (auto-detected if omitted)
- **worktree_base** (optional): base directory for worktrees
- **tracking_enabled** (optional): update tracking doc (default: true)
- **tracking_path** (optional): path to tracking doc
- **flat** (optional, default: false): Intent override - forces product A
  regardless of dependency or policy signals; nothing else is evaluated.
  Use only when the base is genuinely independent despite being unmerged
  (e.g. a long-lived integration branch) — never to silence a
  `CREATE.NEEDS_STACK` refusal without that judgment call.
- **protected_branches** (optional): explicit protected-branch list (auto-detected if omitted)
- **cache_protected_branches** (optional): cache detected protected branches to shared settings (default: true)

## Factory decision model

Precedence: **Intent > Dependency > Policy > default A**, evaluated lazily.

1. **Intent.** `flat: true` → product A immediately. No settings are read, no
   prerequisite check runs, no stacking transcript steps appear.
2. **Stack-activity probe** (cheap, unconditional, fail-closed-to-inactive).
   The repo is stack-active iff `.sc/shared-settings.yaml` sets
   `git.always_stack: true`, OR any existing worktree carries gh-stack
   tracking. **Not stack-active → product A immediately** - the legacy flat
   create is structurally untouched (this is the auto-upgrade guarantee for
   existing prompts: nothing changes until the repo actually uses stacks).
3. **Stack-active → mandatory prerequisite gate**, runs before any mutation
   (including `git fetch`): the `gh` CLI, the `gh-stack` extension, and the
   `managing-gh-stacks` skill must all be present, or the create refuses with
   `CREATE.STACK_PREREQS_MISSING` (see Error Codes below).
4. **Dependency.** Base protected or merged into trunk → independent; else
   dependent (a resolution failure treats the base as independent).
   - Dependent + base has a tracked stack worktree → product **C**.
   - Dependent + that stack worktree has a rebase in progress → refuse
     `CREATE.NEEDS_STACK`.
   - Dependent + no gh-stack tracking anywhere for the base → refuse
     `CREATE.NEEDS_STACK` (a new 2-layer stack is a bigger operation than
     `create` performs; the refusal names the `gh stack init` command).
5. **Policy.** Independent + `git.always_stack` truthy → product **B**
   (branch off `stack_root`, not off the requested `base`; `data.requested_base`
   is set, with a transcript step, when they differ). Independent + policy
   off → product A.

```yaml
# .sc/shared-settings.yaml
git:
  always_stack: true        # absent/false = a stack-inactive repo unless tracking exists elsewhere
  stack_root: develop       # optional; default: "develop" if that branch exists, else the repo default branch
```

## Execution

Run the create script once with the input JSON:

```bash
python3 .claude/scripts/worktree_create.py '<input_json>'
```

The script handles all logic (fetch, product resolution, create, validate, tracking update).

## Output

The script returns fenced JSON. Forward it directly - do not modify or wrap.

**Success example (product A - flat, unchanged):**
```json
{
  "success": true,
  "data": {
    "action": "create",
    "branch": "feature/login",
    "base": "develop",
    "path": "/path/to/worktrees/feature/login",
    "repo_name": "my-repo",
    "status": "clean",
    "branch_created": true,
    "tracking_updated": true
  },
  "transcript": [
    {"step": "git rev-parse --show-toplevel", "status": "ok", "message": "/path/to/repo"},
    {"step": "git fetch --all --prune", "status": "ok"},
    {"step": "git branch --list feature/login", "status": "ok", "message": "local=False remote=False"},
    {"step": "git worktree add -b feature/login /path develop", "status": "ok"}
  ]
}
```

**Success example (product B - new stack):**
```json
{
  "success": true,
  "data": {
    "action": "create",
    "branch": "feature/login",
    "base": "develop",
    "path": "/path/to/repo-worktrees/feature/login",
    "stacked": true,
    "product": "new_stack",
    "stack_root": "develop",
    "stack_shape": "(develop) <- feature/login",
    "stack_init": {"ok": true},
    "branch_created": true,
    "tracking_updated": true
  },
  "transcript": [...]
}
```
Note the path is the SAME shape a flat worktree would use - no `stack/`
prefix. If `gh stack init` fails, creation still succeeds: `data.stack_init`
becomes `{"ok": false, "stderr": "...", "next_step": "run gh stack init --base <root> <branch> in the worktree"}`.
When the requested `base` differs from the resolved `stack_root`,
`data.requested_base` carries the original base.

**Success example (product C - stack layer, no new worktree):**
```json
{
  "success": true,
  "data": {
    "action": "create",
    "branch": "feature/login-tests",
    "base": "feature/login",
    "path": "/path/to/repo-worktrees/feature/login",
    "stacked": true,
    "product": "layer",
    "stack_shape": "(feature/login) <- feature/login-tests",
    "stack_add": {"ok": true},
    "branch_created": true,
    "tracking_updated": true
  },
  "transcript": [...]
}
```
`data.path` is the base's EXISTING stack worktree, not a new directory -
legacy callers that read `path` from output keep working against the layer
unmodified.

**Error example (branch in use):**
```json
{
  "success": false,
  "error": {
    "code": "WORKTREE.BRANCH_IN_USE",
    "message": "Branch 'feature/login' is already checked out in another worktree",
    "recoverable": false,
    "suggested_action": "Use the existing worktree or choose a different branch name"
  },
  "transcript": [...]
}
```

**Error example (dependent base, no stack to join):**
```json
{
  "success": false,
  "error": {
    "code": "CREATE.NEEDS_STACK",
    "message": "Base branch 'feature/api' is neither protected nor merged into trunk, and carries no gh-stack tracking to join as a layer - a new 2-layer stack is required",
    "recoverable": true,
    "suggested_action": "base 'feature/api' is unmerged and carries no gh-stack tracking - creating 'feature/api-tests' here needs a new 2-layer stack: create a worktree at /path/to/repo-worktrees/feature-api on 'feature/api' and run `gh stack init --base main feature/api feature/api-tests`; use the managing-gh-stacks skill (sc-gh-stack) for the full workflow"
  },
  "data": {
    "base": "feature/api",
    "base_merged": false,
    "base_protected": false,
    "gh_stack_tracked": false,
    "suggested_worktree_path": "/path/to/repo-worktrees/feature-api"
  },
  "transcript": [...]
}
```
When the base's stack worktree instead has a rebase in progress, the same
error code is used with `data.rebase_in_progress: true` and
`data.stack_worktree_path` naming the worktree to resolve first.
Pass `flat: true` only for a deliberate, explicit override (never to silence
this refusal by default).

**Error example (stack prerequisites missing):**
```json
{
  "success": false,
  "error": {
    "code": "CREATE.STACK_PREREQS_MISSING",
    "message": "This repo is stack-active (git.always_stack, or an existing gh-stack-tracked worktree) but the mandatory gh-stack prerequisites are not all present",
    "recoverable": true,
    "suggested_action": "gh extension install github/gh-stack; /plugin marketplace add randlee/synaptic-canvas && /plugin install sc-gh-stack@synaptic-canvas"
  },
  "data": {
    "gh_cli": true,
    "gh_stack_extension": false,
    "sc_gh_stack_skill": false,
    "ok": false,
    "always_stack": true
  },
  "transcript": [...]
}
```
This is the only refusal that fires before product resolution, and before
any mutation - it triggers for a stack-active repo regardless of whether
`always_stack` or an existing tracked worktree is what made it stack-active.

## Output Protocol

Wrap the script output in `<output_json>` tags with a fenced JSON block. Do not add prose outside the tags.

## Error Codes

| Code | Meaning | Recoverable |
|------|---------|-------------|
| `GIT.NOT_REPO` | Not a git repository | No |
| `BRANCH.NOT_FOUND` | Base branch doesn't exist | No |
| `WORKTREE.EXISTS` | Worktree path already exists | No |
| `WORKTREE.BRANCH_IN_USE` | Branch checked out elsewhere | No |
| `WORKTREE.DIRTY` | Worktree dirty after creation | No |
| `GIT.ERROR` | Git command failed | No |
| `CREATE.NEEDS_STACK` | Base branch is dependent (neither protected nor merged into trunk) and product C isn't mechanically executable - no gh-stack tracking to join, or the stack worktree has a rebase in progress (pass `flat: true` to override, or follow `suggested_action`) | Yes |
| `CREATE.STACK_PREREQS_MISSING` | The repo is stack-active but `gh`, the `gh-stack` extension, or the `managing-gh-stacks` skill is missing; create refused before any mutation (pass `flat: true` to bypass, or install the missing pieces per `suggested_action`) | Yes |

## Constraints

- Run the script ONCE - it handles everything
- Do NOT run manual git commands; use the script only
