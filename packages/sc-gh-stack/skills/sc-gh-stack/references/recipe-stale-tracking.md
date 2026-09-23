# Recipe: clear stale local stack tracking

Use when `/sc-gh-stack-view` shows 🔄 on a layer, reports NOT COHERENT with
`-` rows, or names a stack number that no longer exists on GitHub; and after
every unstack or re-link as a matter of course.

## Why it happens

gh-stack tracking is stored **per worktree**. After `gh stack unstack` and a
re-link, the worktree that ran them knows the new stack; every other worktree
still holds the old stack number and the old layer list. The view tool
discovers stacks through `git worktree list`, runs `gh stack view --json` in
each, and keeps the *longest* view of a stack (a lower-layer worktree only
sees the layers linked from it). A stale worktree therefore wins with its
longer, obsolete list and the report shows a false NOT COHERENT.

## Steps

1. Find the worktrees that carry tracking:

   ```bash
   for wt in $(git worktree list --porcelain | awk '/^worktree /{print $2}'); do
     out=$(cd "$wt" && gh stack view --json 2>/dev/null) || continue
     printf '%s: ' "$wt"
     printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["trunk"], "->", [b["name"] for b in d["branches"]])'
   done
   ```

   `/sc-gh-stack-view --all --json` shows the same information as
   `stacks[].worktree` and `stacks[].rows[]`.

2. In every worktree whose list is not the current stack:

   ```bash
   cd <stale-worktree> && gh stack unstack --local     # local only, GitHub untouched
   ```

3. In one worktree that is checked out on a branch of the current stack:

   ```bash
   gh stack checkout <new-stack#>      # imports tracking; "Already on <branch>" is fine
   ```

   If the local and remote compositions differ, `checkout` opens an
   interactive prompt that cannot be bypassed; that is exactly why step 2 runs
   first.

4. `/sc-gh-stack-view`. The verdict now reflects GitHub, not a dead list.

## Notes

- `gh stack unstack --local` never contacts GitHub and never touches PRs or
  branches.
- A worktree that prints "Checkout an existing stack using gh stack checkout"
  has no tracking; run `gh stack checkout <stack#>` there before any write
  command from it.
- Do not run `gh stack sync` or `gh stack rebase` from a stale worktree: they
  rewrite and force-push every layer over someone else's push.
