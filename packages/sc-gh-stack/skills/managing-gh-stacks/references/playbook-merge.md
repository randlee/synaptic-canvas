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

## Release stacks: no protected-branch heads

A PR whose **head is a protected/long-lived branch** (e.g. `develop -> main`) is a bad
stack layer: its head moves when the layer below merges, invalidating the CI the merge was
gated on, and stack tooling cannot rebase a protected head. Shape a bump-then-release flow
as a stack landing INTO the protected branch (`release/0.6.0 -> develop`), then open the
`develop -> main` PR separately after the stack lands — or one PR straight to the final
target (`release/0.6.0 -> main`) plus a merge-forward.

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
