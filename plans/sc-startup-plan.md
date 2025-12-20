---
status: Preliminary
created: 2025-12-19
version: 0.1.0
owner: TBD
---

# /sc-startup Slash Command – Plan (Preliminary)

## Intent
Provide a one-shot project startup command that reads repo-specific startup configuration, runs required background agents (PR triage, worktree scan/cleanup, status/checklist sync), loads the startup prompt and master checklist, waits for sub-agents, then delivers a concise status report with recommended next steps. The command should be marketplace-ready and aligned with the v0.5 Claude Code skills/agents guidelines (versioned frontmatter, fenced JSON contracts, registry enforcement).

## Proposed Artifacts
- Command: `.claude/commands/sc-startup.md` (version 0.1.0)
- Skill: `.claude/skills/sc-startup/SKILL.md` (thin orchestration, defers logic to agents)
- Agents: new `sc-checklist-status` (status/checklist sync); reuse existing `sc-worktree-*` agents; reuse `ci-pr-agent` for PR list/fix (resolve `--pr` gap); optionally minimal launcher agent if orchestration needs isolation.
- Config: `.claude/sc-startup.yaml` (repo-root relative) supplying startup prompt/checklist paths and worktree scan mode.
- State/logging: `.claude/state/logs/sc-startup/` for agent-runner audit records (optional).
- Manifest deps: declare required packages/agents (at minimum `ci-pr-agent`, `sc-worktree-*`, `ci-automation`, `sc-checklist-status`) in `manifest.yaml` dependencies; fail closed if missing at runtime.

## Config Contract (`.claude/sc-startup.yaml`)
- `startup-prompt` (string, required): Path relative to repo root that contains the startup prompt to load/read aloud.
- `check-list` (string, required): Path relative to repo root for the master checklist to validate/update.
- `worktree-scan` (string, optional): One of `scan`, `cleanup`, `none`/`""`.
- `pr-enabled` (bool, optional): If false, skip PR agent entirely (must be false if PR agent package is unavailable).
- `worktree-enabled` (bool, optional): If false, skip worktree agents entirely (must be false if worktree package is unavailable).
- Validation: Block with actionable error if required paths are missing; treat `none`/empty as no-op for worktree tasks; fail closed if config enables a feature whose package is unavailable.

## Command Surface
- Invocation: `/sc-startup [--pr] [--pull] [--fast] [--readonly]`
- Flags:
  - `--pr`: Immediately deploy PR triage via `ci-pr-agent`; default `--list --fix` unless `--readonly` is set, in which case run list-only and report.
  - `--pull`: Immediately deploy `ci-automation` (pull-only) targeting master→develop handle (fetch/sync path).
  - `--fast`: Short-circuit to preserve context; read the startup prompt only, assume the role, and exit (no checklist, no status, no agents).
  - `--readonly`: Global report-only mode. Prevents mutations: PR triage becomes list-only, checklist agent runs in report mode, and worktree cleanup runs as scan/report (no deletions).
- Help: If invoked with `--help` or invalid flag combinations, print concise usage, config expectations, and examples without invoking agents.

## Orchestration Flow
1) Load `.claude/sc-startup.yaml`; validate required keys/paths. Validate feature/package availability: if `pr-enabled` is true but `ci-pr-agent` (or equivalent) is missing, fail closed with `DEPENDENCY.MISSING`. Same for worktree agents. Treat `none`/empty worktree mode as no-op. Enforce repo-root-relative paths.
2) If `--fast`: read `startup-prompt` only, summarize role/intent, and exit (skip checklist read, status report, and all agents).
3) If `--pr` and PR feature is enabled: launch background task via Agent Runner to invoke `ci-pr-agent` (PR list/fix). Default `--list --fix`, but `--readonly` forces list-only. Collect summary table (or "no PRs found"). If PR package is disabled/missing but `--pr` is passed, fail closed with `DEPENDENCY.MISSING`.
4) If `worktree-scan` is `scan` or `cleanup` and worktree feature is enabled: launch background `sc-worktree-{scan|cleanup}` via run-task/Agent Runner. If `--readonly`, always run scan/report-only; for `cleanup` without `--readonly`, include cleaned count in the table. If config enables worktree but packages are missing, fail closed with `DEPENDENCY.MISSING`.
5) If `--pull`: invoke `ci-automation` in pull-only mode (master → develop handle) and wait for completion before checklist updates to ensure updates reflect merged state. Report status (success/failure/timeout) but continue best-effort.
6) Launch `sc-checklist-status` background agent to read `check-list` (master checklist) and scan repo for missing items; default behavior updates the checklist when gaps are found unless `--readonly`, in which case run report-only. Agent returns fenced JSON `{success, data, error}` with checklist deltas and repo findings. Checklist changes stay in workspace only (no auto-commit).
7) Read `startup-prompt` file; summarize role/intent.
8) Read `check-list` file (post-update if applicable).
9) Await background agents; aggregate results deterministically (ordered by correlation_id) with status per task (success/failure/timeout/partial). Do not abort on agent errors; proceed best-effort.
10) Output: concise project status report (prompt summary + checklist highlights + PR/worktree/status outcomes) followed by recommended next steps, including partial failures.

## Agents & Contracts
- `sc-checklist-status` (renamed/new)
  - Inputs: `--report` (read-only) or `--update` (default; update checklist when gaps found); `checklist_path`, `repo_root`.
  - Behavior: read checklist; scan repo for TODOs/open tasks; detect missing entries; if `--update`, append/patch checklist; return summary of changes. Honor `--readonly` by forcing report-only. Checklist changes remain in workspace; no auto-commit.
  - Output (minimal envelope, fenced JSON):
    ```json
    { "success": true, "data": { "synced": true, "added": [], "missing": [], "notes": [] }, "error": null }
    ```
    Errors use `error.code` namespaces `VALIDATION.*`, `SCAN.*`, `IO.*`, `DEPENDENCY.MISSING`.
- PR agent call: reuse `ci-pr-agent` with params `{list: true, fix: true}`; `--readonly` enforces list-only. Expect structured result with PR table fields (id/title/status/fixes_applied) and status metadata.
- Worktree agents: reuse `sc-worktree-scan` or `sc-worktree-cleanup`; expect table-friendly fields and `worktrees_cleaned` for cleanup; `--readonly` forces scan-only.
- `ci-automation` (pull-only): invoked when `--pull` is set; must complete before checklist updates; report status even on failure/timeout.

## Safety & UX
- Default path is mutating (auto-fix PRs, update checklist, cleanup when requested); `--readonly` switches every agent to report-only.
- Enforce repo-root-relative paths; refuse absolute paths outside repo.
- Cap background concurrency to 3; default timeout 120s; treat timeouts as partial failures and include in report.
- All agent calls go through Agent Runner with registry version enforcement and fenced JSON validation.
- Dependency validation: if a feature is enabled but the required package/agent is missing, fail closed with `DEPENDENCY.MISSING` and surface it in the final report.
- Logging: Agent Runner audit logs under `.claude/state/logs/sc-startup/`; retention policy: prune entries older than 14 days (documented and scriptable).

## Status Aggregation & Reporting
- Each task returns a status tuple: `{ agent_id, status: "success"|"failure"|"timeout"|"partial", results, error? }`.
- Aggregator preserves deterministic order (by `correlation_id`) and never aborts the run; errors/timeouts are reported, not treated as fatal.
- Final report includes a summary table of statuses plus narrative bullets for prompt/checklist/PR/worktree/CI. Partial failures surface suggested next steps.
- Mixed outcome example:
  - `sc-checklist-status`: success (added 3 items)
  - `ci-pr-agent`: failure (auth error) → reported with `error.code` and suggested action
  - `sc-worktree-cleanup`: timeout → reported as timeout with reminder to rerun or switch to `scan`

## Open Questions
1) Resolved: `--pr` never runs fixes when `--readonly` is set (list-only).
2) Resolved: Checklist should update when out of date by default; `--readonly` forces report-only.
3) Resolved: No additional dry-run mode for worktree cleanup beyond `--readonly`.

## Next Steps
- Confirm open questions and approve the plan.
- Implement command/spec and supporting skill/agent docs per this plan.
- Add registry entries + example config (`.claude/sc-startup.yaml.example`) before marketplace packaging.
