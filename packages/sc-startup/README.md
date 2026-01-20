# sc-startup (v0.6.0)

Startup runner for Synaptic Canvas. Reads repo-specific startup config, loads the startup prompt, syncs the master checklist, and optionally runs PR triage, worktree hygiene, and CI pull before producing a concise status with recommended next steps. Supports readonly and fast paths to control mutations and context usage.

## Badges
- Status: pre-release (0.6.0)
- Compatibility: Synaptic Canvas 0.6.x
- Safety: readonly mode available

## Installation
```bash
# Install via marketplace (example)
/marketplace install sc-startup --local
```
After install, copy the example config into your repo:
```bash
mkdir -p .claude
cp packages/sc-startup/.claude/sc-startup.yaml.example .claude/sc-startup.yaml
```
Edit paths to point to your prompt/checklist files (repo-root-relative).

## Quick Start
```bash
/sc-startup          # normal run: prompt + checklist update + worktree/PR/CI if enabled
/sc-startup --pr     # include PR triage (auto-fix unless --readonly)
/sc-startup --pull   # pull master -> develop before checklist update
/sc-startup --readonly  # report-only everywhere
/sc-startup --fast      # prompt-only, no agents, minimal context
```

## Features
- Reads startup prompt and master checklist with repo-root-relative paths.
- Optional PR triage (`ci-pr-agent`), worktree scan/cleanup (`sc-git-worktree` agents), and CI pull (`ci-automation` pull-only).
- Readonly mode for safe reporting; fast mode for minimal context.
- Best-effort status aggregation with per-task status (success/failure/timeout/partial).
- Dependency validation with explicit `DEPENDENCY.MISSING` errors.
- Checklist updates stay in workspace (no auto-commit).

## Configuration (`.claude/sc-startup.yaml`)
```yaml
startup-prompt: pm/ARCH-SC.md              # required
check-list: pm/checklist.md                # required
worktree-scan: scan        # scan | cleanup | none | ""
pr-enabled: true           # set false if PR package unavailable
worktree-enabled: true     # set false if worktree package unavailable
```

**Path Detection:**
The `sc-startup-init` agent automatically scans for potential startup prompts and checklists in:
- `pm/` directory (project management files)
- `project*/` directories (project-specific files)
- Repository root

When multiple candidates are found, they are sorted by modification time (most recent first) and presented for selection.
Path rules: must be repo-root-relative. Set worktree/PR toggles to false if the package is not installed.

## Dependency Validation
- If a feature is enabled but its package is missing, the command fails closed with:
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
- Dependencies (package level):
  - `sc-ci-automation >= 0.1.0` (provides `ci-pr-agent`, pull-only support)
  - `sc-git-worktree >= 0.6.0` (provides worktree scan/cleanup agents)

## Usage Examples
- Daily kickoff:
  ```
  /sc-startup --pr
  ```
  Loads prompt, syncs checklist, triages PRs, reports worktrees.
- Readonly status for standup:
  ```
  /sc-startup --readonly
  ```
  Report-only; no fixes or updates.
- Prompt-only onboarding:
  ```
  /sc-startup --fast
  ```
  Load prompt, assume role, no agents/checklist.
- CI pull before checklist:
  ```
  /sc-startup --pull --readonly
  ```
  Pull master → develop, then readonly checklist status.
- Worktree hygiene sweep:
  ```
  /sc-startup   # with worktree-scan: cleanup
  ```
  Cleans worktrees (unless --readonly) and reports cleaned count.

## Agents
- `ci-pr-agent` (PR list/fix; list-only under `--readonly`)
- `sc-worktree-scan` / `sc-worktree-cleanup` (scan/report or cleanup; scan-only under `--readonly`)
- `ci-automation` (pull-only when `--pull` is set; runs before checklist update)
- `sc-checklist-status` (report/update checklist; no auto-commit; report-only under `--readonly`)

## Security
- Repo-root-relative paths only; block escapes.
- Default mutating; `--readonly` forces report-only.
- No auto-commit of checklist changes.
- Best-effort: errors/timeouts reported but do not abort.
- Logging: Agent Runner audit logs under `.claude/state/logs/sc-startup/`; prune ~14 days.

## Troubleshooting (high level)
- Dependency missing: install required package or set feature toggle false.
- Config missing/paths invalid: copy `.claude/sc-startup.yaml.example` and fix paths.
- Checklist not updating: ensure not using `--readonly`; check permissions.
- Worktree cleanup skipped: ensure `worktree-scan: cleanup` and not `--readonly`.
See `TROUBLESHOOTING.md` for more.

## Use Cases
- Daily kickoff, pre-standup snapshot, handoff validation, onboarding prompt-only, repo hygiene sweep, guarded PR triage, CI-sync-first status. See `USE-CASES.md` for details.

## Changelog
See `CHANGELOG.md`.

## License
MIT, see `LICENSE`.
/sc-startup --init     # discover config, ask for missing settings, optionally write config
## Init Flow (`--init`)
- Runs detection-only agent `sc-startup-init`:
  - Finds existing config (if present), parses YAML.
  - Suggests prompt/checklist candidates (globbed, bounded).
  - Detects installed packages (`sc-ci-automation`, `sc-git-worktree`, `sc-startup`).
- Skill parses results and uses AskQuestion to resolve missing/ambiguous settings (prompt path, checklist path, worktree-scan, pr-enabled, worktree-enabled).
- If not `--readonly`, writes `.claude/sc-startup.yaml`; otherwise shows synthesized YAML and exits.
- After init, normal startup flow can proceed with the resolved config.
