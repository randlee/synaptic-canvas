# Preconditions: the checks that stop each known failure

Read this before any `gh stack` write command (`link`, `unstack`, `sync`,
`rebase`, `merge`) and before pushing to a trunk that has a stack above it.
Each entry is a check, the failure it prevents, and the recovery if the check
was skipped. Incident references are dates and PR numbers from the phases the
rules were learned in.

## Before `gh stack link`

**Check:** the command carries `--base <trunk>` and the full ordered list
bottom to top; it runs from a worktree checked out on a stack branch (never
from the trunk worktree, never with the trunk or the phase PR as a layer).
**Failure:** without `--base`, `link` retargets the bottom PR to the
repository default branch and GitHub then refuses `gh pr edit --base` on a
stacked PR (PR #1400, 2026-09-11; PR #1253 sat on `main` for 50 seconds).
**Recovery:** `gh stack unstack <n>`, `gh pr edit <pr> --base <trunk>`,
re-link with `--base`. Confirm with
`gh api repos/{owner}/{repo}/issues/<pr>/events` filtered on `base_ref_changed`;
`/timeline` does not show it.

**Check:** pass PR numbers, not branch names, when linking from the main
checkout. **Failure:** a branch name pushes the *local* ref, which may be
another agent's unpushed state.

**Check:** every head is pushed and each layer contains its parent
(`gh_stack_chain_check.py`). **Failure:** a layer cut from a stale or unpushed
head shows phantom diffs and false conflicts.

**Check:** no two layers share a parent without a declared merge-forward
order. **Failure:** two layers cut from the same top (2026-09-13, both from
#1453) meant missing files upstack, red CI on stale merge refs and false
conflict reports. **Recovery:** the declared sibling merges the other forward
with a plain merge commit, then re-link the linear order.

**Check:** after linking, verify every base with the view tool (one GraphQL
query), not with per-PR `gh pr view` calls.

## Before rewriting or rebasing a layer

**Check:** the layer has no children, or every child will be rebased in the
same pass. **Failure:** rewriting a lower layer after children branched made
the stack non-linear; `gh stack merge` refused with "not a linear descendant"
(stack #1416, 2026-09-12). **Recovery:** `recipe-land.md`, fallback B.

**Check:** the layer is not frozen and this is the start of a task on it by
its writer. **Failure:** rebasing frozen layers to "catch up" and per-push
rebases cascaded force-pushes under live agents.

**Check:** the layer's CI is not running, unless it is the landing layer and
the sync is required to land.

## Before pushing to the trunk

**Check:** no stack sync or merge targeting this trunk is in flight; if one
is, an explicit FREEZE was sent to every trunk writer and acked, and this push
waits. **Failure:** one routine event-log push to the trunk one minute after
the final sync made the stack "out-of-date with its base branch", forced the
async-merge fallback and restarted 40 to 60 minutes of CI on every layer
(2026-09-06). **Rule:** anything that must reach the trunk becomes a layer
*before* the final sync, or waits behind the landing. Same for the phase PR
into `develop`: resolve `develop` drift before opening the merge window.

**Check:** a direct push to a protected trunk is not blocked by a ruleset
(GH013 "required status checks are expected" is the ruleset, not a transient).
**Rule:** never edit rulesets or branch protection; report the state and the
exact change needed. The only working bypass is `gh pr merge --merge --admin`
by a bypass-listed account, and that is the user's call.

## Before `gh stack merge`

**Check:** read the full `branches[]` from `gh stack view --json` and confirm
nothing above the merge target would be swept in. **Failure:** a scoped
`gh stack merge <lower-pr>` merged and deleted an upper draft that held only a
merge-forward commit (#1386, 2026-09-10). **Recovery:** a fresh PR for the
remaining work; the old one cannot be restored.

**Check:** the top's CI is green and its QA verdict is PASS; every lower layer
is frozen with its head SHA recorded; every lower head is an ancestor of the
top (`git merge-base --is-ancestor`). Lower-layer CI is not a gate.

**Check:** no draft PR in the stack (`gh stack merge` refuses drafts; the view
tool flags them).

**Check:** the trunk is frozen and acked (above).

**Check:** the method is `--merge`. Never `--squash`; squash-merged layers
rewrite history for every child.

## Before merging a bottom layer alone (collapse)

**Check:** the layer is green **by itself**, not merely "its red is fixed on
the layer above". **Failure:** merging #1492 alone, whose known-red test was
fixed by #1493 above it, put the red on `develop`; an unrelated PR then failed
on it and had to hold its push (2026-09-13). **Rule:** remove the red layer
from the stack first so the fixing layer above carries its commits
(`recipe-restack.md`, section 2); required status checks block a red PR from
merging inside a stack merge anyway (phase-bc, 2026-09-23). If a red layer
ever reaches the trunk, treat the trunk as frozen until the fix lands: no
cuts, no merges.

## Before trusting the view tool

**Check:** the 🔄 icon or a NOT COHERENT verdict with `-` rows after an
unstack is stale per-worktree tracking, not a real problem. gh-stack tracking
lives per worktree; after an unstack or re-link, other worktrees still show
the old stack number and layer list, and the view tool keeps the *longest*
list it finds. **Recovery:** `recipe-stale-tracking.md`.

## Before dispatching a fix for red CI

**Check:** the job log's "Merge <head> into <base>" line. PR CI builds the
merge ref against the base **as it stood when the run started**; a red on a
lower layer may be a base-branch defect fixed minutes later (PR #1460: a lint
failed on a dependency the layer below had not yet allow-listed). The next
push re-runs it green; nobody is dispatched.

**Check:** a lower layer is frozen. Red CI on a frozen layer is not fixed; the
top gates.

## Before any fix dispatch

**Check:** could this land as one more commit on a PR that will get CI anyway,
going to the same base, without blocking that PR's review? Default to that.
A separate PR costs a full CI cycle and a runner slot.

**Check:** one line per finding stating the exact change and the files
allowed. "Fix these findings" with no ruling and no fence made devs re-edit
whole modules for one-line findings, and each QA sweep filed more.

## Standing rules that need no check

- Devs never run `gh stack` write commands, never open PRs, never push to
  another layer or the trunk.
- Never hold a push "until the parent SHA is known"; push the WIP, record the
  SHA afterwards.
- No cosmetic or metadata commit to a green or running PR head.
- At most one CI watcher, interval 60 seconds or more; one verification pass
  right before merging, not one per status ping. On an HTTP 403 secondary
  rate limit, stop all `gh` calls for at least 30 minutes.
- Read files at a pinned head with `git show <sha>:<path>`; a worktree may be
  checked out elsewhere and a verdict on a stale checkout is rejected.
- Refresh a rarely-touched local ref before branching from it
  (`git fetch origin <b> && git update-ref refs/heads/<b> origin/<b>`); a
  stale local `main` produced two worktrees on the wrong base in one session.
