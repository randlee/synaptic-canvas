# Changelog

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
