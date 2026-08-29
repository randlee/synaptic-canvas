# Playbook: convert N existing PRs into one stack

**Situation.** Several branches each fork from trunk and each has (or will have) its own PR.
Merging them one at a time costs n(n+1)/2 CI runs and forces every remaining branch to rebase
after each merge. As a stack they cost n CI runs and land atomically.

**Do not:** force-push, `git reset --hard` (to abandon a conflicted rebase use
`git rebase --abort`; to move a branch to its remote let the script fast-forward it), merge
branches into each other by hand, `gh pr merge`, use `gh stack add` (it only appends to a
stack's top), or try to "fix" order with metadata. Ancestry first.

## Inputs

- Trunk name (usually `main`).
- The branches or PR numbers in **merge order, bottom to top**. Ordering rule: if B uses code
  from A, A is below B. Determine dependencies by comparing what the PRs touch —
  `gh pr diff <n> --name-only` overlap is the first signal, shared APIs/symbols the second.
  Branches with no dependency between them are ties: order ties smaller/riskier-to-conflict
  first, without asking. Ask only about pairs whose relative order is both unknown and
  consequential, presenting the order you inferred for the rest — a wrong order costs
  unstack + rebase + init to undo.

## Steps

```bash
python3 .claude/scripts/gh_stack_preflight.py                    # success: true
python3 .claude/scripts/gh_stack_convert.py main 101 102 103 104  # PR numbers or branch names, bottom → top
```

`gh_stack_convert.py` refuses to run over a dirty tree or an in-progress rebase
(`GIT.DIRTY_TREE` / `GIT.REBASE_IN_PROGRESS`), fetches, resolves PR numbers to branches,
fast-forwards any local branch strictly behind its remote, and refuses a branch that has
diverged from its remote (`GIT.BRANCH_DIVERGED` — converting it would drop the remote's
commits at submit). On `GIT.BRANCH_DIVERGED`, reconcile exactly as the envelope's
`suggested_action` says (`git checkout <layer> && git rebase <remote>/<layer>`) — that single
rebase is expected and allowed here, and **do not push afterwards**: `gh stack submit` owns
all pushing — then re-run the script. Then each layer is rebased `--onto` the layer below so
only that layer's own commits move (a layer that merged trunk in — GitHub's "Update branch" —
is linearised, not kept; if a layer reports `"action": "rebased_empty"` it contained only
merge commits — verify no conflict-resolution content from an "evil merge" was lost before
continuing). It stops at the **first** conflict. Every run emits one fenced JSON envelope;
read `success`, `error.code`, and `data`. The sample payloads below show the fields to act
on; `data` also always carries `trunk`, `remote`, and `layers`. Exit 1 with
`CONVERT.REBASE_FAILED` (a rebase failed without leaving a resumable rebase) or
`CONVERT.FF_FAILED` (a fast-forward failed — often the branch is checked out in another
worktree) — read `error.message`, fix that (never re-chain by hand), and re-run; finished
layers are skipped.

### On exit 3 — `error.code: "CONVERT.CONFLICT"`

```json
{
  "success": false,
  "data": {
    "shape": "(main) <- feat/schema <- feat/api <- feat/ui",
    "chained": [{ "branch": "feat/schema", "onto": "origin/main", "action": "skip" }],
    "conflict": { "layer": "feat/api", "onto": "feat/schema", "files": ["src/api/routes.rs"] },
    "next_step": "resolve the listed files, `git add` them, `git rebase --continue` (repeat if it conflicts again), then re-run this command; finished layers are skipped"
  },
  "error": { "code": "CONVERT.CONFLICT", "message": "conflict rebasing feat/api onto feat/schema", "recoverable": true, "suggested_action": "..." }
}
```

```bash
# resolve src/api/routes.rs — keep the lower layer's version of anything the lower layer owns
git add src/api/routes.rs
git rebase --continue
python3 .claude/scripts/gh_stack_convert.py main 101 102 103 104   # re-run: finished layers report "skip"
```

Every conflict is attributed to a specific layer. If `conflict.files` is empty, rerere has
already staged every resolution — run `git rebase --continue` directly, then re-run the
script. If `git rebase --continue` conflicts again
(a layer with several conflicting commits), repeat resolve + `git add` + `--continue` until
the rebase itself finishes; only then re-run the script — run mid-rebase it refuses with
`GIT.REBASE_IN_PROGRESS`. Loop until `success: true`. rerere records each resolution, so the
same conflict never needs a second manual resolution when the stack is rebased again later.

### On exit 0 — `success: true`

`data.stack_init.action` is `"initialised"` (or `"existing_stack_kept"` if a local stack was
already present — if the reported branches differ from your list, run `gh stack unstack --local`
and re-run the script).

On exit 1 with `error.code: "STACK.INIT_FAILED"`, read `data.stack_init.stderr`, fix the
reported problem, and re-run — chained layers are skipped; do not run `view` or `submit`
until the re-run succeeds.

On success: nothing has been pushed yet. Now inspect the stack:

```bash
gh stack view --json
```

```json
{
  "trunk": "main",
  "currentBranch": "feat/ui",
  "branches": [
    { "name": "feat/schema", "isCurrent": false, "isMerged": false, "needsRebase": false },
    { "name": "feat/api",    "isCurrent": false, "isMerged": false, "needsRebase": false },
    { "name": "feat/ui",     "isCurrent": true,  "isMerged": false, "needsRebase": false }
  ]
}
```

Required: every branch present, in the order you gave, `needsRebase: false` everywhere.
Existing `pr` objects still show their old base on GitHub; the next step fixes that.

### Push and re-base the PRs

```bash
gh stack submit --auto      # force-with-lease push of every layer, PR bases corrected, stack linked on GitHub
gh stack view --json        # each branches[].pr now present; state "OPEN"
```

`submit` is not atomic. If one push is rejected (someone pushed to that branch meanwhile),
earlier pushes stand. Integrate the remote's new commits into that layer, then let the stack
push again:

```bash
git fetch
git checkout <rejected-layer>
git rebase <remote>/<rejected-layer>    # bring the collaborator's commits into the layer
gh stack rebase --upstack               # propagate through the layers above
gh stack submit --auto
```

If that `git rebase <remote>/<rejected-layer>` itself conflicts, resolve + `git add` +
`git rebase --continue` exactly as in the conversion loop (rerere replays earlier
resolutions); never `--abort` into a force-push. Duplicated lower-layer commits are dropped
by the following `gh stack rebase --upstack`.

Never resolve a rejected push with `git push --force`, and never pick "keep the local
version" when branch **content** has diverged (a rejected push) — the remote-only commits
are someone's work. The keep-local path in `troubleshooting.md` applies only to
stack-**grouping** divergence, where no commits differ.
Exit **9** means stacked PRs are not enabled on the repository — stop and tell the user,
reporting which layers (if any) were already pushed per the submit output; the local branches
remain chained and the stack tracked — do not attempt to undo that without the user.

Existing PR titles/bodies are kept. New PRs get auto titles; edit with `gh pr edit <n>`.

## Result

CI runs once per layer on the corrected bases. When green, land everything at once with
`gh stack merge --yes` run with any stack branch checked out — with no argument it targets
the current stack, so no stack number is needed. From elsewhere, pass a PR number instead
("merge that PR and every unmerged PR below it"; see `commands.md`, "merge").

## Why rebase, not merge, to chain

`rebase --onto` keeps each layer linear and replays only its own commits, so conflicts are
isolated per commit per layer and the history matches what `gh stack sync` reproduces after
every squash-merge. Merge commits between layers are discarded by later rebases, which would
throw away conflict resolutions.
