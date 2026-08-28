# Playbook: convert N existing PRs into one stack

**Situation.** Several branches each fork from trunk and each has (or will have) its own PR.
Merging them one at a time costs n(n+1)/2 CI runs and forces every remaining branch to rebase
after each merge. As a stack they cost n CI runs and land atomically.

**Do not:** force-push, merge branches into each other by hand, `gh pr merge`, use `gh stack add`
(it only appends to a stack's top), or try to "fix" order with metadata. Ancestry first.

## Inputs

- Trunk name (usually `main`).
- The branches or PR numbers in **merge order, bottom to top**. Ordering rule: if B uses code
  from A, A is below B. Ties: smaller/riskier-to-conflict first. If the user has not given an
  order and dependencies are not obvious from the diffs, ask — do not guess an order, because
  reordering later means unstack + rebase + init again.

## Steps

```bash
python3 .claude/scripts/gh_stack_preflight.py                    # success: true
python3 .claude/scripts/gh_stack_convert.py main 101 102 103 104  # PR numbers or branch names, bottom → top
```

`gh_stack_convert.py` fetches, resolves PR numbers to branches, then for each layer runs
`git rebase --onto <layer-below> origin/main <layer>` so only that layer's own commits move.
It stops at the **first** conflict. Every run emits one fenced JSON envelope; read `success`,
`error.code`, and `data`.

### On exit 3 — `error.code: "CONVERT.CONFLICT"`

```json
{
  "success": false,
  "data": {
    "shape": "(main) <- feat/schema <- feat/api <- feat/ui",
    "chained": [{ "branch": "feat/schema", "onto": "origin/main", "action": "skip" }],
    "conflict": { "layer": "feat/api", "onto": "feat/schema", "files": ["src/api/routes.rs"] },
    "next_step": "resolve the listed files, `git add` them, `git rebase --continue`, then re-run this command; finished layers are skipped"
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

Every conflict is attributed to a specific layer. Resolve, continue, re-run, until `success: true`.
rerere records each resolution, so the same conflict never needs a second manual resolution
when the stack is rebased again later.

### On exit 0 — `success: true`

`data.stack_init.action` is `"initialised"` (or `"existing_stack_kept"` if a local stack was
already present — check its composition). Nothing has been pushed yet. Now inspect the stack:

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
earlier pushes stand; `git fetch`, rebase that layer, re-run the same command.
Exit **9** means stacked PRs are not enabled on the repository — stop and tell the user.

Existing PR titles/bodies are kept. New PRs get auto titles; edit with `gh pr edit <n>`.

## Result

CI runs once per layer on the corrected bases. When green, land everything at once with
`gh stack merge <stack#> --yes` (see `commands.md`, "merge").

## Why rebase, not merge, to chain

`rebase --onto` keeps each layer linear and replays only its own commits, so conflicts are
isolated per commit per layer and the history matches what `gh stack sync` reproduces after
every squash-merge. Merge commits between layers are discarded by later rebases, which would
throw away conflict resolutions.
