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

3. Link. Two forms:

   - **Append to an existing stack** (the common case):

     ```bash
     gh stack link <stack#> <pr#>
     ```

     Appends on top and retargets that PR onto the current top. `--base` is
     ignored here.

   - **Full ordered list** (first link, or after any unstack):

     ```bash
     gh stack link --base <trunk> <bottom-pr#> ... <top-pr#>
     ```

     Idempotent; re-run with the whole list whenever a PR is added. Sets every
     base, pushes branches that are not pushed, creates PRs for branches
     without one. Confirmed working for 2 to 21 PRs.

   Run from a worktree checked out on a stack branch. Pass PR numbers when
   running from the main checkout (branch names push the *local* ref).

4. Verify: `/sc-gh-stack-view`. Every base must equal its parent's head
   (`✅` in the rebase column, VERDICT COHERENT). Record the stack number the
   link printed.

## B. Several independent PRs on one trunk

When two or more open PRs against the same trunk depend on each other (a fix
another PR's CI needs, docs describing code in a sibling, evidence for a fix)
or simply should land together to save CI cycles:

1. Order them cleanest-first at the bottom: docs and likely-PASS layers low,
   code with open findings above, the PR others need lowest.
2. If a lower one must be *contained* by an upper one, the upper's writer does
   one plain merge-forward commit; otherwise leave every branch unrebased so
   each dev keeps pushing to their own head.
3. `gh stack link --base <trunk> <bottom-pr#> ... <top-pr#>` from a layer
   worktree.
4. Tell every writer and QA that bases changed and nobody rebases; QA reviews
   each PR's three-dot diff against its pinned base.
5. `/sc-gh-stack-view`; record the stack number.

## Never

- `gh stack link` without `--base` when creating or re-creating a stack.
- The trunk, the trunk worktree, or the phase PR as a layer.
- Holding a PR out of the stack until CI is green.
- A mid-stack insert via `link` (it fails with HTTP 422 then "new PRs must be
  added to the top"): use `recipe-restack.md`.

## Finish

`/sc-gh-stack-view`, pasted verbatim, and the stack number recorded wherever
the team tracks it (ledger, PR bodies).
