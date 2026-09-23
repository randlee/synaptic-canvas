# Lifecycle of a stack, step by step

Read this when you are about to start, extend, verify or QA a stack. Each step
names the recipe that carries the exact commands. The steps are what worked
across five production phases; the checks inside them are what stopped the
failures listed in `preconditions.md`.

## 0. Plan the layers before any code

Cut layers on module or crate boundaries (storage → runtime → CLI → docs), one
concern per layer, so no two layers touch the same files. Vertical slices that
touch every module in every layer make every layer conflict with its neighbour
and turn the phase into merge-forwards. Details and the stop rule:
`stack-design.md`.

## 1. Cut the layer from the current pushed top

New worktree, branch from `origin/<current top>`, after verifying the top
contains every lower layer's head. Never from a local ref, never from a head
that is still unpushed. Recipe: `recipe-cut-layer.md`.

Trigger for the *next* sprint: "could the next sprint compile against this
head?" As soon as a sprint's types, schema and core paths are pushed and only
test, lint or QA rounds remain, cut the next layer and start its dev. Waiting
for QA PASS, CI green or the merge left two devs idle for an hour.

## 2. PR on the first push, link immediately

The dev pushes a WIP commit within minutes. The stack writer opens the PR
(base = parent branch; body records the parent SHA, the task id and the file
fence) and links it. Stacking is part of opening the PR, not of merging it. A
branch without a PR has no CI and cannot be judged; a PR held out of the stack
"until it is green" hides the state it was meant to show. Recipe:
`recipe-link.md`.

## 3. Verify with git before every link

The stack writer runs, for the proposed order bottom to top:

```bash
git fetch origin
git log --format='%h %p' -1 origin/<layer>            # parents
git merge-base --is-ancestor origin/<parent> origin/<layer> && echo contains-parent
git diff --stat origin/<parent> origin/<layer>           # file fence check
git merge-tree --write-tree origin/<trunk> origin/<top>  # exit 0 = merges clean
```

`gh_stack_chain_check.py --trunk <trunk> <bottom> ... <top>` runs exactly these
checks and reports PR bases too. Mergeability is the `--write-tree` exit code
or a real `git merge --no-commit` in a scratch worktree, never the legacy
3-arg `merge-tree` (it printed a false conflict on a clean merge and the report
had to be retracted).

## 4. Rebase at task start, once, by the writer

A layer moves exactly once per task, at the start, by its single writer, and
only if it is live and has no children (`preconditions.md`, "Before rewriting
or rebasing a layer"):

```bash
git fetch origin
git rebase --onto origin/<parent> <recorded-parent-base> <layer>
git push --force-with-lease
```

Record the new parent SHA (ledger, PR body). Between tasks layers do not move.
Never per-push rebases (they cascade force-pushes under live agents), never a
rebase of a frozen layer to catch up with the trunk, never a rebase of a layer
whose CI could go green just to catch up. Frozen intermediate layers are
rebased by the stack writer in one pass, only when the layer below them
freezes and only if the landing needs it.

## 5. Freeze means freeze

When a layer's minimum functionality is complete and its task closes, it is
frozen. Red CI on it is not fixed there. A finding on it is a new layer above
the top. If a lower layer *must* be rewritten, every child is rebased in the
same pass before anyone branches again; otherwise the children hold stale
copies, every downstream diff shows phantom regressions, and the stack can no
longer land linearly (`recipe-land.md`, fallback B).

## 6. Fix rounds bundle every finding for one owner on one layer

Non-blocking findings from every layer are collected and fixed once, on a new
top layer, with one QA pass there. New findings that arrive mid-round are
appended to the same task when the file fence covers them. Before dispatching
a fix, write one line per finding stating the exact change and the files
allowed; a fix layer that touches an unlisted file is rejected. Never
per-branch fix rounds; never wait for a lower layer's QA or CI before the top
moves.

## 7. QA at a pinned SHA, on the top

Dispatch QA once when the top is pushed. Pin the review head; QA reads code
with `git show <sha>:<path>`, never from a worktree that may move. The diff
under review is `layer head` versus the commit it was cut from
(`git merge-base <base> <head>`, or the second parent of the last merge-forward
commit), not versus the moving remote base; otherwise a rewritten lower layer's
delta is misattributed as this layer's regression. Post the verdict on the PR.

## 8. Status after every write

`/sc-gh-stack-view` after every link, merge, unstack and before any dispatch.
It shows base coherence (base == parent head), `needsRebase`,
`mergeStateStatus`, CI, stale local tracking and a LANDING line. If the
LANDING line is green and a contiguous bottom run is QA PASS and green by
itself, collapse it (`recipe-restack.md`) and keep the open stack 2 to 3 deep.

## 9. Land once, from the top

All layers frozen, QA PASS on the top, top CI green, trunk frozen and acked:
one `gh stack merge --yes --merge`. Then `/sc-gh-stack-view`, confirm no
in-flight PR was closed as a side effect, lift the freeze. Recipe:
`recipe-land.md`.

## Roles at a glance

| Action | Who |
|--------|-----|
| Push commits to a layer | That layer's writer only |
| Open PR, `gh stack link` / `unstack` / `sync` / `rebase` / `merge` | Stack writer only |
| Rebase a layer at task start | That layer's writer |
| Rebase frozen intermediate layers | Stack writer, one pass |
| Push to trunk | Nobody while a stack sync or merge is in flight |
| Edit repository rulesets or branch protection | Never the agent; report the exact change needed |
