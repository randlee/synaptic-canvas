# Recipe: restack (insert, remove a red layer, collapse the bottom)

Three operations share one mechanism: `gh stack unstack <n>` (PRs and branches
untouched), fix PR bases with `gh pr edit --base`, then one full
`gh stack link --base <trunk> <ordered list>`. Every cycle mints a **new stack
number**; update any ledger or PR text that names it, clear stale tracking in
other worktrees, and finish with `/sc-gh-stack-view`. Merged PRs drop out of
the new stack by themselves.

Unstacking and closing PRs are outward-facing: confirm with the user unless
the user directed the exact operation.

## 1. Insert a layer mid-stack

`gh stack link` cannot insert; with the new branch in the middle it fails with
`HTTP 422 PullRequest.base is invalid` and then "new PRs must be added to the
top of the existing stack". Confirmed three times.

The layer above the insertion point must already contain the new branch's
head (its writer merges it forward with one merge commit first), or the
result is non-linear and cannot land. Then:

```bash
gh stack unstack <n>                                   # PRs untouched
gh pr edit <pr-above> --base <new-branch>              # direct edit succeeds once unstacked
python3 .claude/scripts/gh_stack_chain_check.py --trunk <trunk> <bottom> ... <new> <above> ... <top>   # must print LINKABLE
gh stack link --base <trunk> <bottom-pr#> ... <new-pr#> <pr-above#> ... <top-pr#>
```

If the worktree reports "Checkout an existing stack using gh stack checkout"
before the link, run `gh stack checkout <old stack#>` there first. Then
`recipe-stale-tracking.md`, then `/sc-gh-stack-view`.

## 2. Remove a red layer whose fix lives above

The stack cannot merge with a failing layer, and frozen layers are never fixed
in place. Do this the moment a layer goes red with its fix on a layer above,
so CI runs on every remaining layer in parallel instead of serialising behind
the merge.

```bash
gh stack unstack <n>
gh stack link --base <trunk> <every GREEN pr#, bottom to top>   # reduced list drops the red layer
gh pr close <red-pr#> --comment "Carried by #<pr-above>; branch kept."
```

Why this works: `link` never removes PRs, so the reduced list is the only way
to drop a layer. It retargets the green layer above onto the red layer's
parent, so the red layer's commits ride in the green PR's diff. The branch is
kept; nothing is deleted. Base changes do not restart CI on unchanged heads.

Field result (phase-bc, 2026-09-23): four red PRs closed, absorbed by the two
green layers above them; stack #1564 became #1570 with 17 layers, coherent,
all green in one pass.

Then `recipe-stale-tracking.md`, then `/sc-gh-stack-view`.

## 3. Collapse the bottom

When a contiguous bottom run is QA PASS and **green by itself**, merge it and
keep the open stack 2 to 3 layers deep. A 19-deep stack landed as one merge
after ten hours instead of six to eight small merges over the day, and its
`needsRebase` and stale-tracking noise made the view tool's verdict stop
matching reality.

1. `/sc-gh-stack-view`: LANDING green, bottom layers QA PASS, no open
   findings on them.
2. Read `branches[]` from `gh stack view --json`; confirm the layer above the
   run has unique commits (an empty draft would be swept in and deleted).
3. If the bottom's own CI is red for a reason fixed above it, do **not** merge
   it: remove the red layer first (section 2) so the fixing layer carries its
   commits, then collapse. Merging #1492 alone put its red on `develop`.
4. Freeze the trunk (`preconditions.md`), then:

   ```bash
   gh stack merge <highest-passing-pr#> --yes --merge
   ```

   Merges everything up to and including that PR, bottom to top, atomically.
5. GitHub retargets the next layer onto the trunk within about 30 seconds
   and may rebase its branch (same tree, new committer dates). In that
   layer's worktree:

   ```bash
   git fetch origin
   git diff --stat HEAD origin/<child>      # must be empty: identical trees
   git reset --hard origin/<child>          # ONLY if the diff was empty; otherwise stop and report
   ```

   Never force-push the local branch over GitHub's rebase.
6. `/sc-gh-stack-view`. The next layer's `base` may now read as "behind
   trunk", which is a note, not a rebase order. Lift the freeze; the next unit
   of work is cut from the new trunk head.

## Finish

Every branch of this recipe ends with `recipe-stale-tracking.md` where a
stack number changed, `/sc-gh-stack-view` pasted verbatim, and the new stack
number recorded.
