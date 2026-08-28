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
bash scripts/preflight.sh                       # all OK
bash scripts/convert.sh main 101 102 103 104    # PR numbers or branch names, bottom → top
```

`convert.sh` fetches, resolves PR numbers to branches, then for each layer runs
`git rebase --onto <layer-below> origin/main <layer>` so only that layer's own commits move.
It stops at the **first** conflict and prints the layer and files.

### On exit 3 (conflict)

```bash
# output shows:  CONFLICT in layer: feat/api (rebasing onto feat/schema)
#                  src/api/routes.rs
# resolve src/api/routes.rs — keep the lower layer's version of anything the lower layer owns
git add src/api/routes.rs
git rebase --continue
bash scripts/convert.sh main 101 102 103 104   # re-run: finished layers print "skip"
```

Every conflict is attributed to a specific layer. Resolve, continue, re-run, until exit 0.
rerere records each resolution, so the same conflict never needs a second manual resolution
when the stack is rebased again later.

### On exit 0

The script has run `gh stack init --base main <branches...>` (adopting the existing branches —
nothing pushed yet) and printed `gh stack view --json`. Check it before pushing:

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
`playbook-landing.md` (`gh stack merge <stack#> --yes`).

## Why rebase, not merge, to chain

`rebase --onto` keeps each layer linear and replays only its own commits, so conflicts are
isolated per commit per layer and the history matches what `gh stack sync` reproduces after
every squash-merge. Merge commits between layers are discarded by later rebases, which would
throw away conflict resolutions.
