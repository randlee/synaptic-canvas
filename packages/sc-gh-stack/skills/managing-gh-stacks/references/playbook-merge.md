# Playbook: landing a stack (`gh stack merge`)

Use when a stack (or part of one) is green and ready to land, or when `gh pr merge` was
refused because a PR is "part of a stack".

## Rule zero: verify membership before merging

`gh stack merge` lands **only PRs tracked in the stack**. A PR that targets the same trunk
(or another layer's branch) but was never linked into the stack is invisible to merge —
it will be silently skipped, and the tracked subset lands without it, possibly out of
order. Field incident: `gh stack merge <top> --yes` on what looked like a 2-PR stack merged
only the top PR because the other was never linked; repairing the order cost an extra PR,
CI cycle, and approval gate.

```bash
gh stack view --json   # every PR you intend to land MUST appear here
```

Assert the expected PR **set and order** against `view --json` — not just presence. If it
differs: STOP. Link the missing PR (`gh stack link`) or restructure (`troubleshooting.md`,
"Restructuring a stack"), re-verify with `view --json`, then merge. Never merge the subset
and patch up afterwards.

**Merge scope is defined by the GitHub stack object — not by branch topology or PR base
relationships.** `gh stack merge <pr#>` means "merge the stack up to PR N", never "merge
these PRs I have in mind". A PR based on a stack branch, targeting the same trunk, with
every appearance of being a layer, is simply not touched if it was never linked — silently.

## Scope and semantics

- `gh stack merge --yes` — every unmerged PR in the current stack.
- `gh stack merge <pr#> --yes` — that PR **and every unmerged tracked PR below it**; PRs
  above retarget automatically and stay open.
- `gh stack merge <stack#> --yes` — that stack from anywhere in the repo.
- **All-or-nothing**: if any PR in the merge set cannot merge, none do, and the reason is
  reported. Only basic state is pre-checked (open, not draft) — branch protection can
  still refuse; bypassing merge requirements is not supported for stacks.
- Method: `--squash` / `--rebase` / `--merge` / `--merge-method <m>`; without one the
  last-used method is reused. A **merge queue on the base branch overrides everything**:
  the set is queued (method flags ignored with a warning) and may land in separate groups.
- Bottom merges first. Never merge top-down by hand, never `gh pr merge` a stacked PR,
  never hand-roll REST calls. GitHub's web UI stack merge is the same native flow — fine
  for humans, not agent-drivable.

## Pre-merge protection check

Branch protection can refuse a merge that looks green. **Stale required contexts** are the
usual cause: protection requires status-check names that no current workflow produces
(e.g. protection still lists `Clippy` / `Format check` after CI was renamed to
`Just lint`). Compare before merging:

```bash
gh api repos/{owner}/{repo}/branches/<base>/protection --jq '.required_status_checks.contexts'
gh api repos/{owner}/{repo}/commits/<head-sha>/check-runs --jq '[.check_runs[].name]'
```

Any required context absent from the head's check-run names will block the merge no matter
how green CI is. Surface it — the fix is updating the protection rule, a human decision.
Never route around it with `gh pr merge --admin`.

## Release stacks and the carry layer

The position of a protected-head PR (e.g. `develop -> main`) in a stack decides whether
it is sound or broken. The test: **is anything below it merging into its head?**

**Broken — protected head fed from below.** `release/0.6.0 -> develop` beneath
`develop -> main`: the bottom merge mutates `develop` — the top layer's head — mid-cascade,
invalidating its gated CI from inside the stack, and the tooling cannot rebase a protected
head. Never build this shape. Fix: land the stack into the protected branch, then the
onward PR separately.

**Sound — the carry layer.** The same PR at the **bottom** of a main-based stack.
The canonical release shape is thin — the carry plus one release-prep layer:

```
(main) <- develop <- version-bump+preflight-fixes
```

(Feature layers normally do NOT ride release stacks: day-to-day work lives in
**develop-based stacks** — `(develop) <- L1 <- L2` — and integration-tests on develop
first. The release stack carries *develop itself*, which already integrated them, plus
the bump/preflight layer where `set-package-version.py` output lands.)

Nothing below feeds `develop`, so nothing in the stack moves its head. On
`gh stack merge --yes`, the carry layer merges first (main catches up to develop), then
each feature layer **retargets to main** and merges with its head SHA — and therefore its
green CI — unchanged. One atomic walk-away merge lands everything on main; the follow-up
`main -> develop` merge-forward needs no approval and no waiting (and is required in
either flow, so it never costs extra). The carry layer also makes that back-merge
**conflict-free by construction**: it carried all of develop's content into main first,
so after the cascade develop's tip is fully contained in main — develop holds nothing
main lacks. A main-based stack WITHOUT the carry layer forfeits this: develop's unmerged
accumulation diverges from the landed features and the back-merge can genuinely conflict.

Walk-away preconditions for the carry-layer shape — all four, every time:
1. **Membership**: every intended PR is in the stack object (Rule zero above) — the
   walk-away is only safe because nothing is unlinked.
2. **Approval freshness**: with stale-approval dismissal on, the carry layer's approval is
   given right before the merge (an act-gate on "release what develop contains now").
3. **No external churn window**: anything merging into `develop` between the carry layer's
   CI clearing and the landing invalidates it — land promptly after green.
4. **Main's protection**: "require branches up to date" and merge queues on main break the
   carried-greens property (forced re-runs mid-cascade) — this shape assumes neither.

## Waiting on CI

One watcher per head, not ad-hoc polling: `gh pr checks <pr#> --watch`, or a single loop
with a >= 30s interval and a `--jq` filter to non-success runs only. Per-tick `gh api
.../check-runs` calls (especially from cron) burn the 5,000/hr REST limit fast; if you are
rate-limited, stop polling entirely until the limit window resets — polling through it
just extends the outage.

## After the merge — verify atomically, then report

Verification is part of the merge step, not an afterthought. Before reporting success,
assert in the same step:

```bash
gh pr view <each-expected-pr#> --json state,mergedAt   # every one: "MERGED"
gh stack view --json                                   # remaining PRs retargeted correctly
git fetch && git show <remote>/<target>:<version-file> # target really carries the change
gh stack sync --prune                                  # then clean up local branches
```

Any expected PR still `OPEN` means the membership check was skipped or wrong — say so
explicitly rather than reporting the merge as done. The ideal transcript for a two-layer
landing is about four calls: `gh stack view --json` → assert both layers present in order
→ `gh stack merge --yes` → verify both `MERGED` + the target branch's content.

## Failure modes

- Refusal names a specific PR: fix that PR (draft, closed, failing required check) and
  re-run — nothing merged, nothing to unwind.
- `gh pr merge` said "part of a stack": that is not an error to work around — the answer
  is `gh stack merge` after the membership check, never REST experiments and never
  `gh pr merge --admin`.
