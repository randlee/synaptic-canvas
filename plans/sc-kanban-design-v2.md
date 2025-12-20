# sc-kanban Package Design Document (v0.2.0 Draft)

**Status:** Draft for adoption (supersedes v0.1.0; intended replacement)  
**Target Release:** Marketplace v0.7.0  
**Compliance:** Claude skills/agents v0.5 (versioned frontmatter, fenced JSON, standard envelopes, registry/attestation)

---

## 1) Purpose & Scope
- Pure state machine for cards: validates transitions, enforces gates, WIP, and scrubbing; no orchestration logic.
- Consumer-agnostic: PM/Scrum-Master agents orchestrate; kanban enforces.
- Multi-agent native: scalar or array worktrees/PRs; strict ALL validation.

## 2) Architecture
- Command `/kanban <action>` → Skill `sc-kanban/SKILL.md` → Agents (invoked via Agent Runner):
  - `kanban-init` (setup/wizard/migration)
  - `kanban-card` (create/update)
  - `kanban-transition` (move/archive + gates)
  - `kanban-query` (read/filter/validate board)
- Registry/attestation: `.claude/agents/registry.yaml` (name, version, path). Agent Runner resolves, computes SHA-256, logs audit to `.claude/state/logs/`, and fails closed on mismatches.

## 2a) Agent Inventory & Command Map
- Commands:
  - `/kanban init` → `kanban-init`
  - `/kanban migrate <file>` → `kanban-init` (migration mode)
  - `/kanban create|update <card/fields>` → `kanban-card`
  - `/kanban move <card> <column>` and `/kanban archive <card>` → `kanban-transition`
  - `/kanban list [filters]`, `/kanban status --by-phase` → `kanban-query`
  - `/kanban help` and `/kanban --help` → usage table (concise commands/args summary)
- Agent roles:
  - `kanban-init` (opus, foreground): scaffolds config/templates, Q&A wizard, migrations. High complexity, 4–6KB. Must run foreground and interact with user.
  - `kanban-card` (haiku): CRUD on card fields, schema validation (hybrid scalar/array). Low complexity, 2–3KB.
  - `kanban-transition` (haiku): runs gate set (parallel), WIP, archive scrubbing, external validation. High complexity, 5–7KB.
  - `kanban-query` (haiku): parses board, filters, rollups, validation. Medium complexity, 3–4KB.

## 2b) Skill/Agent/Script Flow
- The skill never calls scripts directly; it always invokes agents via Agent Runner.
- Agents may invoke Python helper scripts for validations; scripts are pure-read and return structured JSON consumed by the calling agent.
- If a script fails or a gate fails, the agent returns a v0.5 envelope with `failed_gates`/`warnings` and `suggested_action` so PM/Scrum-Master agents can remediate and re-run. No hidden subagents are spawned; remediation is guided by the returned actions.

## 3) Response Contract (v0.5 Standard Envelope)
- Fenced JSON required. Fields: `success` (bool), `canceled` (bool), `aborted_by` ("timeout"|"user"|"policy"|null), `data` (object|null), `error` (object|null).
- Error object: `{ code, message, recoverable, suggested_action }`.
- Optional metadata: `{ duration_ms, tool_calls, retry_count, correlation_id }`.
- Unfenced/malformed JSON = failure; skills must treat as error.

## 4) Gate Execution Model
- Gates run in parallel with capped concurrency (default 3–4) and per-task timeout (e.g., 5–10s). Deterministic ordering by `correlation_id` or array index.
- Aggregation payload (returned in `data` or `error.details`):
  - `results[]`: `{ correlation_id, rule, field, location, success, canceled, aborted_by, warnings[], error }`
  - `summary`: `{ all_successful, succeeded:[], failed:[], warned:[] }`
- Retry: default 0–1 retries only when `recoverable: true`; no auto-retry for external state unless flagged recoverable.

## 5) Gate/Check Failure Shape
- `failed_gates[]`: `{ rule, field, location (e.g., "worktrees[1]"), code (GATE.VALIDATION|GATE.EXTERNAL_STATE|WIP.EXCEEDED|SCRUB.FAIL), detail, evidence, suggested_action, recoverable }`
- `warnings[]`: advisory check outcomes.
- Multi-agent arrays: stable order; per-item evidence (paths, branch, PR URL, HEAD SHA vs remote SHA).

## 6) External Validation & Automation
- Worktree existence/cleanup:
  - Prefer `sc-git-worktree`; fallback `test -d`.
  - Codes: `VALIDATION.EXTERNAL_STATE` (missing), `TOOL.MISSING`, `EXECUTION.TIMEOUT`.
  - Suggested action: install `sc-git-worktree`/`git`, recreate worktree, rerun.
- PR state:
  - Prefer `gh pr view --json state`; codes `PR.NOT_FOUND`, `PR.NOT_OPEN`, `PR.NOT_MERGED`, `TOOL.MISSING`, `EXECUTION.TIMEOUT`.
  - Fallback attestation (`evidence: "user_attested"`); recoverable=false unless policy allows.
- Code committed/pushed:
  - `git status --porcelain` → `GIT.DIRTY`.
  - `git rev-parse HEAD` vs `git ls-remote` → `GIT.NOT_PUSHED`.
  - Suggested actions: `git add/commit/push`, then retry transition.

## 7) Automation Scripts (Python, read-only)
- Implement as Python CLIs (cross-platform). No mutations; pure validation.
- `scripts/validate_worktrees.py`: input card path or worktree list; parallel checks; outputs fenced JSON with per-worktree status.
- `scripts/validate_pr_state.py`: PR URL(s) + branch/worktree; `gh` status; git clean/push verification; outputs per-PR and git cleanliness.
- `scripts/run_gates.py`: orchestrates gate set for a transition (worktree exists, PR present/merged, WIP, scrub pre-check); parallel with timeouts; emits aggregated gate payload.
- Testing: pytest-based unit/integration tests for all scripts; included in package release process (CI gate).

## 8) Transitions & Codes (Team Sprint template example)
- `planned → active`: gates `field_required(worktree)`, `worktree_exists`; checks `assignee` warning.
- `active → review`: gates `field_required(pr_url)`, `GIT.DIRTY`, `GIT.NOT_PUSHED`.
- `review → done`: gates `pr_merged`, `worktree_removed`; checks `branch_deleted` warning.
- WIP enforcement: `WIP.EXCEEDED` (blocking|warning per config).
- Archive scrubbing: `SCRUB.MISSING_FIELD` enumerates transient fields not scrubbed; blocking failure if configured.

## 9) PM/Scrum-Master Interaction
- Agents surface actionable `suggested_action` for every gate failure (e.g., “Commit and push branch main/2-1-auth-backend, then retry”).
- Parallel gate results + per-item evidence allow PM to re-run only failing worktrees/PRs.
- Partial success surfaced: “2 passed, 1 failed (worktrees[1]: PR not merged)”.

## 10) Templates (Solo Dev / Team Sprint / QA Pipeline)
- Retain structures; upgrade semantics to v0.5 envelope + gate/check schema; add git cleanliness gates before entering review columns.

## 11) Implementation Plan (delta-focused)
- Update all agents to v0.5 envelope + versioned frontmatter; register in `.claude/agents/registry.yaml`; require Agent Runner invocation.
- Add Python automation scripts and wire `kanban-transition` to `run_gates.py`.
- Implement parallel gate runner with timeout/concurrency controls and deterministic aggregation.
- Enhance error contract in `kanban-transition`: `failed_gates`, `warnings`, `summary`, `aborted_by`.
- Add git cleanliness gates; PR/worktree checks prefer tools, fall back to filesystem/attestation.
- Update SKILL.md to surface partial results and suggested actions.
- Docs: refresh README/TROUBLESHOOTING with codes, suggested actions, attestation policy.
- Tests (pytest in release pipeline): parallel gates, timeouts, missing tools, git dirty/not pushed, multi-agent arrays with partial failures, archive scrubbing failures, WIP blocking vs warning.

## 12) Success Criteria (v0.2.0)
- All agents return v0.5-compliant fenced JSON with registry-validated versions.
- Parallel gate runner reports partials with per-item evidence/actions; PM can remediate and retry.
- Automated worktree/PR/git checks reduce manual multi-agent hops; clear remediation guidance.
- Missing tool/timeout paths return structured errors with recoverability guidance; no silent degradation.
- Archive/WIP enforcement emit explicit codes; no silent skips.
