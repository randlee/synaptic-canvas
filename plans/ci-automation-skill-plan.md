---
status: Preliminary
created: 2025-01-22
version: 0.1.0
owner: TBD
---

# CI Automation Skill – Plan (Preliminary)

## Intent
Create a skill/command to run end-to-end CI quality gates with optional auto-fix and PR flow. Default behavior executes pull → build → test → fix-if-straightforward → PR or report.

## Proposed Command
- File: `.claude/commands/ci-automation.md`
- Frontmatter name: `ci-automation` (user invocation `/ci-automation`)
- Version: 0.1.0
- Flags (all support `--help`):
  - `--build`: run pull + build only (skip tests/PR)
  - `--test`: run pull + build + test (skip commit/push/PR)
  - `--dest <branch>`: override inferred upstream/target branch (rare; to bypass develop and PR to main/master)
  - `--src <branch>`: override inferred source branch/worktree if needed
  - `--allow-warnings`: allow warnings to pass gates (otherwise warnings block PR)
  - `--yolo`: enable aggressive auto-fix through commit/push/PR (default flow stops before commit/PR unless clean)
  - `--help`: display usage, flag descriptions, examples; exit without executing

**Help output (example)**:
```
/ci-automation - Run end-to-end CI quality gates

Usage:
  /ci-automation [flags]

Flags:
  --build              Run pull + build only (skip tests/PR)
  --test               Run pull + build + test (skip commit/push/PR)
  --dest <branch>      Override target branch for PR (default: inferred from tracking)
  --src <branch>       Override source branch/worktree (default: current branch)
  --allow-warnings     Allow warnings to pass quality gates
  --yolo               Enable auto-commit/push/PR (requires clean gates)
  --help               Show this help message

Examples:
  /ci-automation --test
  /ci-automation --dest main
  /ci-automation --yolo
```

## Default Flow (no flags)
0) Validation: run `ci-validate-agent` to ensure clean repo, config present, auth available; stop with actionable error if blocked.
1) Pull from inferred upstream branch (from current branch tracking) and resolve merge conflicts if straightforward; allow override via `--dest` or config.
2) Build all.
3) If build fails and fix is straightforward, invoke `ci-fix-agent` via Agent Runner (registry-enforced), then restart at step 2.
4) Test all.
5) If tests fail or warnings occur and fix is straightforward, invoke `ci-fix-agent` via Agent Runner, then restart at step 2.
6) If quality gates still not met and user input needed, run `ci-root-cause-agent` and produce a report with recommendations.
7) If quality gates achieved and user confirms (unless `--yolo`), commit, push, and create PR to `{upstream}`; output concise summary of completed tasks.

## Scope & Defaults
- Upstream inferred from current branch’s tracking/upstream (e.g., feature off develop → dest=develop). Allow override via `--dest` for rare PR-to-main flows.
- Source branch/worktree inferred from current branch; allow override via `--src`.
- Build/test commands configurable via skill-specific config (recommended: `.claude/ci-automation.yaml`); accept `.claude/config.yaml` as fallback. If recognizable (.NET/Python/etc.), suggest detected commands for user confirmation; otherwise prompt and save.
- Avoid storing extra metadata unless config is missing; prompt on first run to populate config.

## Agents (minimal set, v0.1.0)
- `ci-validate-agent`: check prerequisites (clean repo unless override, config present, auth available); block with actionable error if not satisfied.
- `ci-pull-agent`: pull upstream, attempt straightforward conflict resolution; report status.
- `ci-build-agent`: run build; classify failures (straightforward vs. needs input).
- `ci-test-agent`: run tests; classify failures/warnings.
- `ci-fix-agent`: attempt straightforward fixes for build/test issues; return patch summary.
- `ci-root-cause-agent`: analyze unresolved failures; produce root cause + recommendation report.
- `ci-pr-agent`: commit/push/create PR when gates pass.

## Data Contracts
All agents return fenced JSON using the minimal envelope:
```json
{
  "success": true,
  "data": {
    "summary": "Operation completed successfully",
    "actions": ["action1", "action2"]
  },
  "error": null
}
```

### Error Response Schema
When `success: false`, agents return:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "NAMESPACE.CODE",
    "message": "Human-friendly error description",
    "recoverable": false,
    "suggested_action": "What the user/skill should do next"
  }
}
```

Error code namespaces (examples):
- `VALIDATION.*` (config missing, dirty repo)
- `GIT.*` (merge conflict, protected branch)
- `BUILD.*` (compile failure, dependency missing)
- `TEST.*` (assertion failure, timeout)
- `PR.*` (no changes, auth failed)
- `EXECUTION.*` (timeout, tool limit)

### Agent-Specific Notes
- Fix agent output includes `patch_summary`, `risk`, `files_changed`, `followups`.
- Root-cause agent output includes `root_causes[]`, `recommendations[]`, `blocking`, `requires_human_input`.

- Command: `.claude/commands/ci-automation.md`
- Skill: `.claude/skills/ci-automation/SKILL.md` (<2KB, references heavy)
- Agents: `.claude/agents/ci-*.md` (7 files, version 0.1.0 including validation)
- References: `.claude/references/ci-automation-commands.md` (build/test commands, warn patterns, detection hints), `.claude/references/ci-automation-checklists.md` (gates, fix heuristics)
- Config example: prefer `.claude/ci-automation.yaml` (fallback `.claude/config.yaml`) with `upstream_branch`, `build_command`, `test_command`, `warn_patterns`, `repo_root` (optional), detection guidance for common stacks (.NET, Python, Node).
- Reports: `.claude/reports/skill-reviews/` for reviews; `.claude/reports/ci-automation/` for execution logs (fallback `.claude/.tmp/skill-reviews/`); prompts: `.claude/.prompts/`.

## Safety & Policies
- Never force-push; respect protected branches.
- Default (conservative) path: auto-fix build/test if straightforward but stop before commit/push/PR unless all gates clean and user confirms.
- `--yolo`: aggressive path that auto-commits/pushes/PRs on agent judgment after gates are satisfied.
- Fix agent limited to “straightforward” patterns (configurable heuristics); allow multiple simple fixes; stop if fundamental logic change is required; otherwise defer to root-cause report.
- Warnings block PR by default; `--allow-warnings` or config can relax this.
- Protected-branch guard: even with `--yolo`, require explicit confirmation for PRs to main/master unless `--dest main` is provided.
- Audit: Agent Runner should log invocations to `.claude/state/logs/ci-automation/`.

## Marketplace Integration (post-implementation)
- Package the skill for Synaptic Canvas marketplace after approval and testing:
  - Ensure `manifest.yaml` includes command/skill/agents/references paths and versions.
  - Verify registry alignment and versioning (agents 0.1.0).
  - Include `.claude/ci-automation.yaml.example` for config onboarding.
  - Add README/install notes for marketplace consumers.
  - Run `/skill-review` before publish; attach review report.
## Open Questions
1) Fix heuristics: define “straightforward” as non-fundamental logic changes; allow multiple simple fixes (not limited to one file). Add a stop if logic change is required. Formalize heuristics in references.
2) Warnings policy: default block PRs on warnings; allow override via `--allow-warnings` or config.
3) PR naming: use source branch as PR head; default upstream target from tracking. Need a head branch pattern when auto-creating from main? Suggested: `ci/auto-{date}-{hash}`.
4) Idempotency keys (optional v0.2.0): use for PR creation to avoid duplicates.

## Next Steps
- Confirm upstream default and config prompts.
- Approve plan → set status Proposed/Approved.
- Generate artifacts via `/skill-create plans/ci-automation-skill-plan.md` (after approval).
