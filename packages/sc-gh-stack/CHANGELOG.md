# Changelog

## 0.1.0 — 2026-08-28

Initial package (skill-only, no agents).

- `managing-gh-stacks` skill: use-case router with model, hard rules, CLI
  verification (Step 1), preflight gate, and situation → playbook table
- `references/playbook-convert.md`: worked example converting N parallel PRs
  into one stack via `git rebase --onto`, `gh stack init`, `gh stack submit --auto`
- `scripts/preflight.sh` (read-only environment gate) and `scripts/convert.sh`
  (deterministic, idempotent chaining; exit 3 on first conflict)
- upstream `github/gh-stack` references (`commands.md`, `troubleshooting.md`,
  `stack-design.md`) carried verbatim for on-demand loading
- `references/installation-and-troubleshooting.md` per guidelines v0.7

Planned for 0.2.0: `playbook-new-stack.md`, `playbook-daily-loop.md`,
`playbook-landing.md`, `playbook-graph-to-stacks.md`.
