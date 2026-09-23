# Recipe: open the PR and link it into the stack

Use on the first push of every layer, and whenever several open PRs on one
trunk depend on each other. Stacking happens when the PR opens, never "once it
is green". One link command, the full ordered list, `--base` every time.

## A. First push of a new layer

1. Open the PR with base = the parent layer (the trunk for the bottom layer).
   The body records the parent SHA the layer was cut from, the task or sprint
   id, and the file fence:

   ```bash
   gh pr create --base <parent> --head <layer> --title "<title>" --body "$(cat <<'B'
   Parent: <parent> @ <parent-sha>
   Task: <id>
   Fence: <paths this layer may touch>
   B
   )"
   ```

   Drafts block `gh stack merge`; open as ready, or mark ready before landing.

2. Pre-link check from the main checkout (read-only):

   ```bash
   python3 .claude/scripts/gh_stack_chain_check.py --trunk <trunk> <bottom> ... <layer>
   ```

   Exit 0 means every head is pushed, each layer contains its parent, PR bases
   match the chain and the top merges clean into the trunk. Fix anything it
   lists before linking.

3. Link. The canonical form, used for the first link, after any unstack, and
   whenever in doubt, is the full ordered list with `--base`:

   ```bash
   gh stack link --base <trunk> <bottom-pr#> ... <top-pr#>
   ```

   Idempotent: re-run with the whole list whenever a PR is added. Sets every
   base, pushes branches that are not pushed, creates PRs for branches without
   one. Confirmed working for 2 to 21 PRs. The chain check prints this
   command with the numbers filled in.

   Accepted shortcut when appending exactly one PR to an existing stack:

   ```bash
   gh stack link <stack#> <pr#>
   ```

   It appends on top and retargets that PR onto the current top; it cannot
   insert (`recipe-restack.md`), and `--base` is ignored by it.

   Run from a worktree checked out on a stack branch. Pass PR numbers, not
   branch names, when running from the main checkout: a branch name pushes
   the *local* ref, which may be another writer's unpushed state.

4. Verify: `/sc-gh-stack-view`. Every base must equal its parent's head
   (`✅` in the rebase column, VERDICT COHERENT). Record the stack number the
   link printed.

## B. Several open PRs on one trunk that must land together

When two or more open PRs against the same trunk depend on each other (a fix
another PR's CI needs, docs describing code in a sibling, evidence for a fix),
or should land in one CI cycle instead of three:

1. Order them by dependency, cleanest-first at the bottom: the PR the others
   need lowest, docs and likely-PASS layers low, code with open findings
   above.
2. Make the chain linear before linking. For each layer above the bottom, its
   writer makes **one plain merge-forward commit** of the layer below
   (`git merge --no-ff origin/<lower>`; never a rebase, never a force-push),
   pushes, and that layer is then frozen unless it is the top. Independent
   PRs are never left as a fork: `gh stack merge` refuses a stack whose layers
   are not linear descendants, and the chain check fails it.
3. `python3 .claude/scripts/gh_stack_chain_check.py --trunk <trunk> <bottom-pr#> ... <top-pr#>`
   until it prints LINKABLE.
4. `gh stack link --base <trunk> <bottom-pr#> ... <top-pr#>` from a layer
   worktree.
5. From here the stack follows the model: nothing below the top is edited
   again, QA runs once on the top (a QA already in flight on a lower PR may
   finish and its verdict carries forward), CI gates the top, and the stack
   lands once. Tell every writer that bases changed and that only the top
   moves.
6. `/sc-gh-stack-view`; record the stack number.

## Never

- `gh stack link` without `--base` when creating or re-creating a stack.
- The trunk, the trunk worktree, or the phase PR as a layer.
- Holding a PR out of the stack until CI is green.
- A mid-stack insert via `link` (it fails with HTTP 422 then "new PRs must be
  added to the top"): use `recipe-restack.md`.

## Finish

`/sc-gh-stack-view`, pasted verbatim, and the stack number recorded wherever
the team tracks it (ledger, PR bodies).
