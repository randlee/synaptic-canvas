# Changelog

## 0.1.0 — 2026-08-28

Initial package (skill-only, no agents).

- `managing-gh-stacks` skill: use-case router with model, hard rules, CLI
  verification (Step 1), preflight gate, and situation → playbook table
- `references/playbook-convert.md`: worked example converting N parallel PRs
  into one stack via `git rebase --onto`, `gh stack init`, `gh stack submit --auto`
- `scripts/gh_stack_preflight.py` (read-only environment gate) and
  `scripts/gh_stack_convert.py` (deterministic, idempotent chaining; exit 3 on
  first conflict; refuses dirty trees, in-progress rebases, and diverged
  branches; exact per-layer rebase bounds via transient `refs/sc-gh-stack/orig/*`
  so dependent branches never replay a lower layer's commits); stdlib-only,
  fenced JSON envelopes
- `tests/`: 40 pytest cases — mocked unit tests plus real-git integration tests
  (conflict → resume, dependent layers, trunk-merge linearisation, stale and
  diverged remotes)
- upstream `github/gh-stack` references (`commands.md`, `troubleshooting.md`,
  `stack-design.md`) carried verbatim for on-demand loading
- `references/installation-and-troubleshooting.md` per guidelines v0.7

Planned for 0.2.0: `playbook-new-stack.md`, `playbook-daily-loop.md`,
`playbook-landing.md`, `playbook-graph-to-stacks.md`.
