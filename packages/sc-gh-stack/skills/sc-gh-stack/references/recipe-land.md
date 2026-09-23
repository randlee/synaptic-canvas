# Recipe: land the stack

Use when every layer below the top is frozen, the top's QA verdict is PASS and
the top's CI is green. One atomic merge lands the stack; two fallbacks cover
the cases GitHub refuses. Landing is irreversible: confirm with the user
unless the user directed it.

## Landing checklist

- [ ] Every layer below the top is frozen and recorded with its head SHA.
- [ ] Top layer: local gates green, QA PASS posted on the PR.
- [ ] Top CI green on the exact landing SHA. If the repository's CI runs only
      for trunk-family base branches (stacked PRs get no check-runs), open a
      plain CI-trigger PR `top-head → trunk`, not linked into the stack, wait
      for its run on the landing SHA, then close it; check-runs are per
      commit, so the ruleset's required checks are satisfied.
- [ ] No draft PR in the stack; `branches[]` read in full; no empty upper
      layer that would be swept in.
- [ ] `/sc-gh-stack-view`: COHERENT, LANDING ✅.
- [ ] FREEZE sent to every trunk writer and acked. Anything for the trunk
      became a layer before the final sync or waits.

## Primary: one atomic stack merge

```bash
gh stack merge --yes --merge            # from a worktree on the stack
gh stack merge <stack#> --yes --merge   # from anywhere
```

All-or-nothing, bottom to top. Only open, non-draft state is checked; the
ruleset's required checks are satisfied because the top head carried CI
(skipped docs-only checks count as satisfied). Never `--squash`. If the base
uses a merge queue the stack is queued as a group and may land in separate
batches; the queue picks the method.

Refusals and what they mean:

| Message | Cause | Go to |
|---------|-------|-------|
| "stack is out-of-date with its base branch" | Someone pushed to the trunk after the final sync | Freeze, then fallback A or one `gh stack sync` and retry |
| "PR #X's branch is not a linear descendant of PR #Y's branch" | A lower layer was rewritten after children branched | Fallback B |
| Draft PR listed | A layer is still a draft | `gh pr ready <pr#>`, retry |

## Fallback A: merge one stacked PR through the async API

`gh pr merge` on a stacked PR is refused ("must be merged using the
asynchronous merge REST API") and the synchronous `POST pulls/N/merge`
returns 404. The working call:

```bash
SHA=$(gh pr view <n> --json headRefOid -q .headRefOid)        # FULL 40 characters
gh api -X PUT repos/{owner}/{repo}/pulls/<n>/merge-async \
  -H "Accept: application/vnd.github+json" \
  -f merge_method=merge -f sha="$SHA"                        # returns a uuid
gh api repos/{owner}/{repo}/pulls/<n>/merge-async/<uuid>     # poll until status == "merged"
```

An abbreviated SHA fails with the misleading "Pull request head branch was
modified". After the parent merges, GitHub retargets **and rebases** the child
branch within about 30 seconds (same tree, new committer dates). In the child
worktree:

```bash
git fetch origin
git diff --stat HEAD origin/<child>        # must be empty: identical trees
git reset --hard origin/<child>            # ONLY if the diff was empty; otherwise stop and report
```

Never force-push the local child over GitHub's rebase. Do not use fallback A
to land a whole stack layer by layer: each merge rebases every remaining
frozen layer.

## Fallback B: non-linear stack

When a lower layer was rewritten after its children branched, do not fall back
to sequential fallback-A merges (each rebases frozen layers). Instead land the
top PR directly:

```bash
gh stack unstack <stack#>
gh pr edit <top-pr#> --base <trunk>
gh pr merge <top-pr#> --merge          # top head already carried CI on this SHA
```

Verify every lower head is an ancestor of the new trunk head; GitHub marks the
lower PRs MERGED by itself and the merge commit carries the whole history.

```bash
git fetch origin
for b in <lower layers>; do git merge-base --is-ancestor origin/$b origin/<trunk> && echo "landed $b" || echo "NOT LANDED $b"; done
```

## After landing

1. `/sc-gh-stack-view`: all PRs MERGED, or the remaining open stack coherent
   on the new trunk head.
2. Confirm no in-flight PR was closed as a side effect
   (`gh pr list --state merged --limit 10` around the merge time, and the
   specific PRs you know are in flight).
3. Send "landed"; lift the freeze; push any held trunk commits.
4. Reset local refs to origin in every layer worktree; never force-push a
   landed branch.
5. For a phase stack: the phase PR `trunk → develop` opens now; a
   review-findings stack, if any, opens above the trunk.

## Never

- `--squash`.
- `gh pr merge --admin` to get past a ruleset; that is the user's decision
  and the user's account.
- A push to the trunk between the final sync and the landed confirmation.
