# Recipe: clear stale local stack tracking

Use when `/sc-gh-stack-view` shows 🔄 on a layer, reports NOT COHERENT with
`-` rows, conflicting catalog definitions, or a stack number that no longer
exists on GitHub. An unstack/re-link invalidates affected observations; use
its response to identify stale tracking rather than scanning as a precaution.

## Why it happens

Legacy gh-stack tracking is stored **per worktree**; newer catalogs may be
shared. After `gh stack unstack` and a re-link, legacy worktrees can retain the
old stack number and layer list. The helper reads catalogs locally and reports
conflicting definitions instead of selecting the longest obsolete list.

## Steps

1. Find the worktrees that carry tracking:

   ```bash
   python3 .claude/scripts/gh_stack_view.py --all --no-pr --no-fetch --json
   ```

   Inspect catalog conflict diagnostics and `stacks[].worktree` /
   `stacks[].branches[]`; reuse already available diagnostics when sufficient.
   `catalogs[]` retains source paths, ordered compositions and branch owners,
   including disputed definitions. If no stack can be accepted, read those
   records under `error.details.catalogs` instead; no checkout is needed.
   Do not run `gh stack view` once per worktree to discover tracking.

2. In every worktree whose list is not the current stack:

   ```bash
   cd <stale-worktree> && gh stack unstack --local     # local only, GitHub untouched
   ```

3. In one worktree that is checked out on a branch of the current stack:

   ```bash
   gh stack checkout <new-stack#>      # imports tracking; "Already on <branch>" is fine
   gh stack checkout <any-pr#-in-the-stack>   # same effect when the stack number was not recorded
   ```

   If the local and remote compositions differ, `checkout` opens an
   interactive prompt that cannot be bypassed; that is exactly why step 2 runs
   first.

4. Verify the imported local composition and affected bases/heads with
   `gh_stack_view.py --stack <branch> --json`; request `--refresh-status` only
   when current hosted facts are missing. Recovery does not itself prove CI
   or hosted eligibility.

## Notes

- `gh stack unstack --local` never contacts GitHub and never touches PRs or
  branches.
- A worktree that prints "Checkout an existing stack using gh stack checkout"
  has no tracking; run `gh stack checkout <stack#>` there before any write
  command from it.
- Do not run `gh stack sync` or `gh stack rebase` from a stale worktree: they
  rewrite and force-push every layer over someone else's push.
