# sc-startup (v0.1.0)

Startup runner for Synaptic Canvas. Reads repo startup config, loads the startup prompt, syncs the master checklist, and optionally runs PR triage, worktree hygiene, and CI pull before producing a concise status with next steps.

## Command
```
/sc-startup [--pr] [--pull] [--fast] [--readonly]
```

- `--pr`: PR list/fix via `ci-pr-agent` (list-only when `--readonly`)
- `--pull`: Run `ci-automation` in pull-only mode (master → develop) before checklist updates
- `--fast`: Prompt-only short-circuit (no agents, no checklist)
- `--readonly`: Report-only everywhere (no fixes/updates/cleanup)

## Config (`.claude/sc-startup.yaml`)
```yaml
startup-prompt: docs/startup-prompt.md
check-list: docs/master-checklist.md
worktree-scan: scan        # scan | cleanup | none | ""
pr-enabled: true           # set false if PR package unavailable
worktree-enabled: true     # set false if worktree package unavailable
```

## Agents
- `ci-pr-agent` (PR list/fix)
- `sc-checklist-status` (checklist report/update; no auto-commit)
- `sc-worktree-scan` / `sc-worktree-cleanup` (scan/report or cleanup)
- `ci-automation` (pull-only for `--pull`)

## Safety
- Path safety: repo-root-relative only
- Default mutating; `--readonly` is report-only
- Checklist changes stay in workspace (no auto-commit)
- Dependency validation: fail closed with `DEPENDENCY.MISSING` when enabled feature is absent
- Logging: Agent Runner audit logs under `.claude/state/logs/sc-startup/`; prune ~14 days
