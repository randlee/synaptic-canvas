---
name: sc-startup
version: 0.1.0
description: Run the repo startup workflow: load the startup prompt, sync the master checklist, launch optional PR/worktree/CI agents, and return a concise status with next steps.
options:
  - name: --pr
    description: Immediately deploy the `ci-pr-agent` with `--list --fix`; render PRs as a table (state “No open PRs” if none). If `--readonly`, run list-only (no fixes).
  - name: --pull
    description: Immediately deploy the `ci-automation` skill in pull-only mode to sync master → develop.
  - name: --fast
    description: Short-circuit: read the startup prompt only, assume the assigned role, and exit (no checklist, no agents, no status report).
  - name: --readonly
    description: Global report-only mode; disable fixes/updates/cleanup. PRs list-only, checklist agent report-only, worktree cleanup becomes scan/report.
  - name: --help
    description: Show usage and config requirements, then exit.
---

# /sc-startup command

Kick off the Synaptic Canvas project startup routine. Reads repo-specific configuration, launches background agents for PR triage, worktree hygiene, and checklist synchronization, loads the startup prompt and master checklist, waits for sub-agents, then outputs a concise status report with recommended next steps.

## Configuration
- File (repo-root relative): `.claude/sc-startup.yaml`
- Keys:
  - `startup-prompt` (string): Path to the startup prompt file (relative to repo root).
  - `check-list` (string): Path to the master checklist file (relative to repo root).
  - `worktree-scan` (string): One of `scan`, `cleanup`, `none`/`""`.
  - `pr-enabled` (bool, optional): If false, skip PR agent; must be false if PR package is unavailable.
  - `worktree-enabled` (bool, optional): If false, skip worktree agents; must be false if worktree package is unavailable.
- Validation: Fail closed with a short error if the config is missing or paths are invalid; enforce repo-root-relative paths only. If a feature is enabled but required packages are missing, fail closed with `DEPENDENCY.MISSING` and a specific message, e.g.:
  ```json
  {
    "success": false,
    "data": null,
    "error": {
      "code": "DEPENDENCY.MISSING",
      "message": "Feature 'pr' enabled but required agent 'ci-pr-agent' is not installed",
      "recoverable": true,
      "suggested_action": "Install ci-pr-agent or set pr-enabled: false in .claude/sc-startup.yaml"
    }
  }
  ```

## Execution Flow
1) Load `.claude/sc-startup.yaml`; resolve prompt/checklist paths; abort with help if invalid. Validate feature availability against installed packages; fail closed with `DEPENDENCY.MISSING` when enabled packages are absent.
2) `--help`: Print concise usage, flags, and config example; exit without invoking agents.
3) If `--fast`: Read `startup-prompt` only, summarize the role, and exit (skip checklist read, status, and all agents).
4) If `--pr`: Launch background agent via Agent Runner for `ci-pr-agent`; default `--list --fix`, but `--readonly` forces list-only (no fixes). Capture fenced JSON and render as a table (explicit “No open PRs” if empty).
5) If `worktree-scan` is `scan` or `cleanup`: Launch background `sc-worktree-scan` or `sc-worktree-cleanup` respectively; render results as a table. If `--readonly`, always run scan/report-only; for `cleanup` without `--readonly`, include a `worktrees_cleaned` column.
6) If `--pull`: Run `ci-automation` in pull-only mode (master → develop handle) and wait for completion before checklist updates to ensure updates reflect merged state. Report status even on failure/timeout.
7) Always deploy `sc-checklist-status` (inputs: `--update` by default; `--report` for dry runs). Default updates the master checklist when gaps are detected unless `--readonly`, which forces report-only. Return fenced JSON `{success, data, error}` with deltas and any added checklist entries. Checklist changes remain workspace-only (no auto-commit).
8) Read `startup-prompt` and `check-list` files (post-update if applicable).
9) Await background agents; aggregate results in deterministic order by `correlation_id`; surface partial failures/timeouts as statuses (best-effort, do not abort).
10) Output a concise status report:
   - Prompt summary/role
   - Checklist sync summary (updated items, remaining gaps)
   - PR findings (table) if requested
   - Worktree scan/cleanup table if configured
   - CI pull result if `--pull`
   - Recommended next steps

## Agents & Delegation
- `sc-checklist-status`: Inputs `--report` or `--update`; outputs fenced JSON `{ "success": bool, "data": { "synced": bool, "added": [], "missing": [], "notes": [] }, "error": null|object }`. Honor `--readonly` by forcing `--report`. No auto-commit of checklist changes.
- `ci-pr-agent`: Run with `--list --fix` when `--pr` is set; `--readonly` switches to list-only. Show PR table even if fixes fail (include errors).
- `sc-worktree-scan` / `sc-worktree-cleanup`: Invoked based on `worktree-scan` value; show table with worktree path/branch/state and cleaned count when applicable; `--readonly` enforces scan/report-only.
- `ci-automation` (pull-only mode): Launched when `--pull` is set to sync master → develop handle before checklist updates.
- All invocations go through Agent Runner with registry version enforcement; treat malformed/unfenced JSON as failure and report succinctly.

## Output & UX
- Default mode is mutating: PR auto-fix and checklist update are enabled unless `--readonly` is provided. `--report` passthrough is available for dry runs. No additional dry-run mode beyond `--readonly` for worktree cleanup.
- Keep stdout concise; no tool traces. Tables for PRs/worktrees; bullet summaries for checklist and prompt.
- Use minimal envelope for agent responses; handle `canceled`/timeout cases as partial failures and include them in the report. Aggregate per-task status objects `{agent_id, status: success|failure|timeout|partial, results, error?}` and present best-effort even on failures.

## Examples
```
/sc-startup
/sc-startup --pr
/sc-startup --pull
/sc-startup --fast
/sc-startup --pr --readonly
```

## Error Handling
- Missing config/paths: abort with a short, actionable message showing the expected `.claude/sc-startup.yaml` keys.
- Agent failure/timeout: continue aggregating other results; mark failure in the final report with suggested next actions.
- Path safety: refuse absolute paths or locations outside the repo root.
- Dependencies: if required packages are missing while enabled, fail closed with `DEPENDENCY.MISSING` and surface in the report.
- Logging: Agent Runner audit logs under `.claude/state/logs/sc-startup/`; prune after ~14 days (script/CI).
