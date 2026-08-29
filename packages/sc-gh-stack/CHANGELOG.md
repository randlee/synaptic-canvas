# Changelog

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
- Worktree policy: one worktree per stack at `<repo>-worktrees/stack/<bottom>`;
  gh-stack tracking verified per-worktree, so parallel stacks never interfere
  and surfaced conflicts are reviewable in place.
- SKILL.md rewritten orchestration-first (plan / convert / sync + agent
  delegation); new `playbook-graph-to-stacks.md` and `playbook-sync.md`;
  `playbook-convert.md` reworked agent-first with the manual path as fallback.
- Descope note: the 0.1.0-planned `playbook-new-stack.md`, `playbook-daily-loop.md`,
  and `playbook-landing.md` were folded into existing routes instead of shipping
  separately (new stack = `playbook-graph-to-stacks.md` step 3; daily loop =
  `playbook-sync.md`; landing = `gh stack merge --yes` via SKILL.md).
- 55 pytest cases.

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
