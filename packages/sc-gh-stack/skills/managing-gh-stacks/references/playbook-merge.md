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

If an expected PR is missing: STOP. Link it (`gh stack link`) or restructure
(`troubleshooting.md`, "Restructuring a stack"), re-verify with `view --json`, then merge.
Never merge the subset and patch up afterwards.

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

## After the merge

```bash
gh stack view --json        # merged layers: "isMerged": true; remaining PRs retargeted
gh stack sync --prune       # rebase what remains and delete local branches of merged PRs
```

If only part of the stack landed, the remaining stack is still a stack — continue with
`playbook-sync.md` for the daily loop.

## Failure modes

- Refusal names a specific PR: fix that PR (draft, closed, failing required check) and
  re-run — nothing merged, nothing to unwind.
- `gh pr merge` said "part of a stack": that is not an error to work around — the answer
  is `gh stack merge` after the membership check, never REST experiments.
