# Troubleshooting gh stack

Read this when a `gh stack` command fails, exits non-zero, or produces a confusing message — it maps error signatures to root cause and the concrete recovery steps, including failure modes only confirmed by hands-on use, not by `--help`.

**Stack-writer only.** `unstack`, `sync`, `rebase`, `submit` and `merge` rewrite
or land shared state: only the stack writer runs them, `merge`, `unstack` and
`gh pr close` are confirmed with the user unless the user directed them
(`SKILL.md` precondition 10), and a layer that has children is never
rewritten. Where a recovery below differs from a recipe, the recipe wins.

## Handle rebase conflicts (exit 3)

```bash
gh stack rebase
# exit 3 — conflicted paths listed on stderr
# Read the files, resolve the <<<<<<< / ======= / >>>>>>> markers
git add path/to/resolved-file
gh stack rebase --continue     # repeat if the next branch also conflicts
# or, to bail out entirely:
gh stack rebase --abort        # restores every branch in the stack
```

`sync` restores all branches to their pre-rebase state before exiting 3, so a failed `sync` never leaves anything half-applied; a failed plain `rebase` stops mid-flight and waits for `--continue`/`--abort`. Because `init` enables `git rerere`, a conflict resolved once is replayed automatically the next time it recurs — common, since a low change gets rebased through every branch above it.

## Squash-merge recovery

**Not applicable in this model** (merge commits only, never `--squash`); kept for repositories that squash. A squash-merged PR's original commits no longer exist in trunk history. `gh stack sync` detects this and rebases with `git rebase --onto` to replay the remaining commits correctly, skipping the merged branch:

```bash
gh stack sync
gh stack view --json   # merged branch: "isMerged": true, "state": "MERGED"
```

If the replay conflicts, `sync` restores everything and exits 3 — resolve with `gh stack rebase` / `--continue` as above.

## Local and remote stacks diverged

Divergence: the local stack and the GitHub stack changed differently (e.g. a branch added locally while a PR was added to the stack on github.com). **Non-interactively, `sync` prints `ℹ Sync aborted`, changes nothing, and exits 0.** Exit 0 here is NOT success — always check stderr for "Sync aborted" or diff `gh stack view --json` before/after to confirm sync actually happened.

Resolution in this model: the GitHub stack is the truth, local tracking is
disposable. In every worktree whose tracking is stale run
`gh stack unstack --local` (GitHub untouched), then `gh stack checkout <stack#>`
in one worktree on a stack branch: `recipe-stale-tracking.md`. Never resolve a
divergence with `gh stack submit --auto`; it force-pushes every local branch,
which may be another writer's unpushed state.

Remote unstacking leaves queued or auto-merge-enabled PRs stacked; clear that state first if you need a clean unstack.

## Restructure a stack

No non-interactive reorder, rename or removal exists, and `gh stack link`
cannot insert mid-stack. The mechanism for every restructure (insert a layer,
drop a red layer, collapse the bottom) is `gh stack unstack <n>` (PRs and
branches untouched), `gh pr edit <pr> --base <intended parent>` where a base
must change, then one full `gh stack link --base <trunk> <bottom-pr#> ...
<top-pr#>`: `recipe-restack.md`. Do not use `gh stack init` + `gh stack submit
--auto` to rebuild: `init` checks out the last branch in the current worktree
(wrong under one-worktree-per-layer) and `submit` force-pushes local refs.
Ancestry is fixed with git first, and only on a layer that has no children;
metadata never changes ancestry.

## Branch belongs to several stacks (exit 6)

The current branch can't identify a single stack (typically it's the trunk of more than one). No flag disambiguates:

```bash
gh stack checkout <a-branch-unique-to-the-intended-stack>
```

Commands taking an explicit stack number (`merge 7`, `unstack 7`) sidestep this since they don't infer from the current branch.

## Stack file locked (exit 8)

Another `gh stack` process holds `.git/gh-stack.lock`. The lock times out after ~5 seconds — wait and retry. A persistent exit 8 means another process still holds it; find and stop it.

## Interrupted modify (exit 10)

`gh stack modify` is TUI-only and this skill never invokes it. If a repo is left in this state by someone else:

```bash
gh stack modify --abort
```

`submit` also detects a pending modify state and, under a TTY, asks before overwriting the GitHub stack with local state.

## Stacked PRs unavailable (exit 9)

The repository doesn't have stacked PRs enabled. This can't be fixed from the CLI — a repo admin must enable it on GitHub. Stop and tell the user.

## `checkout` conflict prompt

`gh stack checkout <pr-number>` when a different local stack already exists over those branches triggers an unbypassable interactive conflict-resolution prompt. Avoid it: run `gh stack unstack --local` first (keeps the GitHub stack intact), then retry the checkout.

## Field-verified failure signatures

| Observed message | Cause | Fix |
|---|---|---|
| `stack is out-of-date with its base branch` | Someone pushed to trunk after the final sync | Freeze trunk pushes during merge, use the merge-async fallback, or re-sync (`gh stack sync`) and retry |
| `PR #X's branch is not a linear descendant of PR #Y's branch` | A lower layer was rewritten (rebased/force-pushed) after children branched from it | `gh stack unstack`, `gh pr edit <top-PR> --base <trunk>`, merge the top PR directly — GitHub marks the lower PRs MERGED by ancestry |
| `HTTP 422 PullRequest.base is invalid` / `new PRs must be added to the top of the existing stack` | Tried a mid-stack insert via `gh stack link` | `unstack` + `gh pr edit <PR> --base <new-base>` + full re-link with the complete branch list |
| `Pull request head branch was modified` (on a `merge-async` call) | Passed an abbreviated SHA instead of the full 40-char `headRefOid` | Re-fetch `headRefOid` from `gh stack view --json` / `gh pr view --json headRefOid` and pass it in full |
| `...part of a stack and must be merged using the asynchronous merge REST API` | Ran `gh pr merge` on a stacked PR | Use `gh stack merge`, or the `merge-async` API fallback directly |
| False `NOT COHERENT` / `-` rows from the view tool | Stale per-worktree gh-stack tracking after an unstack/re-link done in a different worktree | `gh stack unstack --local` in the stale worktree, then `gh stack checkout <new-stack#>` |
| `Checkout an existing stack using gh stack checkout` | Worktree lost tracking after an unstack elsewhere | `gh stack checkout <stack#>` — "Already on `<branch>`" in response is fine, not an error |
| `GH013: Repository rule violations... required status checks are expected` | Direct push to a protected trunk hits a ruleset | Not transient — go through a PR, or use a bypass-listed account; never edit the ruleset yourself |
| Legacy `git merge-tree <base> <a> <b>` prints diff3-style hunks | 3-arg `merge-tree` always prints combined diff output — it is not a conflict signal by itself | Use `git merge-tree --write-tree <a> <b>` and check its exit code, or do a real `git merge --no-commit` in a scratch worktree |
| CI log on a lower layer reads `Merge <head> into <base>` and is red | CI ran against the base as it stood at run start; a base-branch defect fixed afterward will show green on the next push | Read that log line before escalating — it's often stale, not a real regression |

## Multi-worktree note

gh-stack's local tracking is per worktree. After any `unstack`/re-link done in one worktree, treat tracking in every other worktree as stale: run `gh stack unstack --local` there, then `gh stack checkout <new-stack#>` in exactly one worktree that is on a stack branch.
