# Changelog

## Unreleased

- Layering fix: dropped the `stack/<bottom-slug>` worktree path scheme. Default stack
  worktree location is now the bottom branch's normal worktree location,
  `<repo_root>-worktrees/<bottom-branch>` — the same convention as any worktree (directory =
  branch name), created with plain `git worktree add` when absent. Stack-ness was never a
  path concern: it is repository state (`.git/worktrees/<wt>/gh-stack`). The one-worktree-per-
  stack invariant is unchanged; only the path scheme is simpler. `correlation_id` continues
  to use the bottom-branch slug as an identifier (unrelated to paths).

## 0.2.0 — 2026-08-28

Orchestration release: background agents over the deterministic scripts.

- Agents (Task tool, `run_in_background: true`, one per stack):
  `sc-stack-plan` (task graph → stacks + worktree plan, read-only),
  `sc-stack-convert` (flat PRs → stack in an isolated worktree),
  `sc-stack-sync` (post-merge / mid-stack-fix rebase). Convert and sync apply a
  trivial-vs-risky conflict rubric: trivial conflicts are resolved and reported
  as low-risk decisions; risky conflicts stay paused in the worktree for
  review; push happens only via `gh stack submit --auto`/`sync` when fully
  clean, with per-branch `pushed` state in every report.
- `scripts/gh_stack_sync.py`: wraps `gh stack sync` (all-or-nothing: conflict
  restores every branch) with the shared guards and envelope.
- Report/state contract: success envelopes are minimal decision logs
  (per-branch before/after SHAs, pushed flags, resolutions); failure envelopes
  are forensic (exact failing command, stderr, recovery action) so a caller
  recovers without investigation.
- Worktree policy: one worktree per stack at `<repo>-worktrees/<bottom>` (the bottom
  branch's normal worktree location); gh-stack tracking verified per-worktree, so
  parallel stacks never interfere and surfaced conflicts are reviewable in place.
- SKILL.md rewritten orchestration-first (plan / convert / sync + agent
  delegation); new `playbook-graph-to-stacks.md` and `playbook-sync.md`;
  `playbook-convert.md` reworked agent-first with the manual path as fallback.
- Descope note: the 0.1.0-planned `playbook-new-stack.md`, `playbook-daily-loop.md`,
  and `playbook-landing.md` were folded into existing routes instead of shipping
  separately (new stack = `playbook-graph-to-stacks.md` step 3; daily loop =
  `playbook-sync.md`; landing = `gh stack merge --yes` via SKILL.md).
- `gh_stack_convert.py --dry-run` (alias `--validate`): previews the per-layer
  plan (skip / rebase / fast-forward / refuse) using the same freshness
  classifier the executor uses, mutating nothing; with preflight this is the
  package's `--validate` surface (`--auto-fix` is deliberately replaced by the
  trivial-conflict rubric).
- Convert and sync agents use the Standard envelope (`canceled`, `aborted_by`,
  `metadata.*`); a risky-conflict stop is `canceled: true, aborted_by: "policy"`
  with `CONVERT.CONFLICT_RISKY` / `SYNC.CONFLICT_RISKY`, `recoverable: false`.
- Scripts survive missing binaries (synthetic rc-127 results — always a fenced
  envelope, never a traceback; `PREFLIGHT.GIT_MISSING` distinct from
  `PREFLIGHT.NOT_A_REPO`).
- `SYNC.ABORTED` (exit 5): non-interactive `gh stack sync` on a diverged local/remote stack
  prints "Sync aborted" but exits 0 without syncing — the script detects it, so exit 0
  always means synced and pushed.
- Preflight enforces the manifest's runtime floors (`git_version` >= 2.23,
  `python_version` >= 3.9) instead of deferring unsupported-runtime failures into later
  workflow steps.
- Agents resolve the installed script directory (project `.claude/scripts` first, then
  user-scope `~/.claude`) instead of hard-coding a project-local path, matching the skill's
  `scope: both`; `PREFLIGHT.SCRIPTS_MISSING` when neither exists.
- Pre-merge membership check in SKILL.md: `gh stack merge` lands only PRs tracked in the
  stack — verify every intended PR appears in `gh stack view --json` before merging, never
  land a subset.
- New references from field incidents: `playbook-merge.md` (membership check before any
  merge, scope semantics, all-or-nothing, merge queue) and `playbook-rebase.md`
  ("believe the report": `needsRebase` is computed against remote/parent state — never
  deny a reported rebase after local inspection; conflict-free cascade procedure).
- `evals/`: `claude plugin eval` suite (haiku-pinned) reproducing the field incidents in
  local fixture repos with a scripted `gh` stub — denied-rebase, subset-merge, exit-0
  "Sync aborted", merge-forward-vs-rebase, release-stack-shape, and post-merge
  verification cases; no GitHub repo or network needed.
- Field-incident hardening from a second report: merge scope is the GitHub stack
  object, not branch topology (silent non-touch of unlinked PRs); pre-merge branch
  protection check for stale required contexts (`--admin` is never a fallback —
  hard rule 2); no protected-branch heads as stack layers (hard rule 7, plan agent
  rule 7, playbook-merge "Release stacks"); merge-forward-only drift check before any
  rebase recommendation (hard rule 8, playbook-rebase "Merge-forward repositories");
  single-watcher CI polling guidance; atomic post-merge verification.
- 68 pytest cases.

## 0.1.0 — 2026-08-28

Initial package (skill-only, no agents).

- `managing-gh-stacks` skill: use-case router with model, hard rules, CLI
  verification (Step 1), preflight gate, and situation → playbook table
- `references/playbook-convert.md`: worked example converting N parallel PRs
  into one stack via `git rebase --onto`, `gh stack init`, `gh stack submit --auto`
- `scripts/gh_stack_preflight.py` (read-only environment gate) and
  `scripts/gh_stack_convert.py` (deterministic, idempotent chaining; exit 3 on
  first conflict; refuses dirty trees, in-progress rebases, and branches that
  diverged from their remote — checked for every layer, before the skip test;
  exact per-layer rebase bounds via `refs/sc-gh-stack/orig/*` pre-rebase tips,
  keyed to the conversion identity in `sc-gh-stack.conversion` and cleared when
  a different conversion starts, so dependent branches never replay a lower
  layer's commits and stale bookkeeping never leaks between conversions);
  stdlib-only, fenced JSON envelopes
- `tests/`: 49 pytest cases — mocked unit tests plus real-git integration tests
  (conflict → resume, abort → re-run, dependent layers, fork-point bounds,
  trunk-merge linearisation, stale and diverged remotes, adopted-layer
  divergence and reconcile, post-submit idempotency, rerere-staged conflict
  resumability, stale-bookkeeping clearing)
- upstream `github/gh-stack` references (`commands.md`, `troubleshooting.md`,
  `stack-design.md`) carried verbatim for on-demand loading
- `references/installation-and-troubleshooting.md` per guidelines v0.7

Planned for 0.2.0: `playbook-new-stack.md`, `playbook-daily-loop.md`,
`playbook-landing.md`, `playbook-graph-to-stacks.md`.
