# sc-kanban Package Design Document (v0.7.0 Draft)

**Status:** Draft for adoption (supersedes v0.1.0; intended replacement)  
**Target Release:** Marketplace v0.7.0  
**Compliance:** Claude skills/agents v0.5 (versioned frontmatter, fenced JSON, standard envelopes, registry/attestation)  
**Integration:** Shared board config with sc-project-manager; defaults to kanban state-machine provider, degrades to markdown checklist if kanban not installed

---

## 0) Shared Board Config (common with sc-project-manager)
- Board metadata is sourced from a YAML file (default: `.project/board.config.yaml`, overridable by command flag/env). This same file is read by sc-project-manager so both skills operate on one schema. Example: `templates/board.config.example.yaml`.
- Kanban provider uses three files (rich vs lean lifecycle):
  - `backlog.json` (lean; 100s items; unplanned)
  - `board.json` (rich; 10–20 active/review; includes prompts/criteria/agents)
  - `done.json` (lean; scrubbed)
- Checklist provider is different: `roadmap.md` plus ephemeral `prompts/<sprint_id>.md` (no gates, no rich inline fields).
- Minimal schema:
  ```yaml
  version: 0.7
  board:
    backlog_path: .project/backlog.json  # lean
    board_path: .project/board.json      # rich
    done_path: .project/done.json        # lean
    provider: kanban | checklist         # kanban = sc-kanban agents; checklist = markdown checklist fallback (roadmap.md flow)
    wip:
      per_column:
        active: 3
        review: 2
    columns:
      - id: planned
        name: Planned
      - id: active
        name: In Progress
      - id: review
        name: In Review
      - id: done
        name: Done
  cards:
    fields:
      - id: worktree
        required: true
        type: string
      - id: pr_url
        required: false
        type: string
      - id: assignee
        required: false
        type: string
    conventions:
      worktree_pattern: "<project-branch>/<sprint-id>-<sprint-name>"
      sprint_id_grammar: "<phase>.<number>[<letter>]*"
  agents:
    transition: sc-kanban/kanban-transition
    query: sc-kanban/kanban-query
    checklist_fallback: checklist-agent/query-update   # invoked when provider=checklist
  ```
- When `provider=kanban`, all transitions must route through sc-kanban agents; sc-project-manager simply calls the transition agent. When `provider=checklist`, sc-kanban returns a structured “not installed / provider=checklist” response and sc-project-manager calls the checklist agent using the same fenced JSON contract.
- Card store format: JSON or YAML with stable IDs. Fields align with worktree schema so `sc-git-worktree` references map 1:1 to card entries.

---

## 1) Purpose & Scope
- Pure state machine for cards: validates transitions, enforces gates, WIP, and scrubbing; no orchestration logic.
- Three-file lifecycle (kanban provider): backlog (lean) → board (rich) → done (lean scrubbed).
- Consumer-agnostic: PM/Scrum-Master agents orchestrate; kanban enforces.
- Multi-agent native: scalar or array worktrees/PRs; strict ALL validation.
- Board/provider abstraction: driven by shared YAML config (`provider=kanban|checklist`). If kanban provider missing, agents return a structured `provider_unavailable` error with suggested checklist agent call (`templates/checklist-agent.md`); PM can swap in checklist agent without changing schema. Checklist provider uses roadmap.md + ephemeral prompts (no gates, no rich inline fields).

## 1a) Card Schema & Lifecycle
- Lean backlog (backlog.json): `sprint_id`, `title`, `dependencies`.
- Rich planning (board.json): adds `worktree`, `dev_agent`, `qa_agent`, `dev_prompt`, `qa_prompt`, `acceptance_criteria`, `max_retries`, `base_branch`.
- Execution fields (board.json updates): `pr_url`, `status_report`, `actual_cycles`, `started_at`, `completed_at`, `status`.
- Done (done.json, scrubbed): keep `sprint_id`, `title`, `pr_url`, `completed_at`, `actual_cycles`; drop prompts/criteria/assignments.

## 2) Architecture
- Command `/kanban <action>` → Skill `sc-kanban/SKILL.md` → Agents (invoked via Agent Runner):
  - `kanban-init` (setup/wizard/migration)
  - `kanban-card` (create/update)
  - `kanban-transition` (move/archive + gates)
  - `kanban-query` (read/filter/validate board)
- Registry/attestation: `.claude/agents/registry.yaml` (name, version, path). Agent Runner resolves, computes SHA-256, logs audit to `.claude/state/logs/`, and fails closed on mismatches.
- Config binding: all agents read board settings from YAML (path resolved from command flag/env). They refuse to mutate if config version mismatch or `provider=checklist` (returns advisory envelope).
- File layout (kanban provider): expects `backlog.json`, `board.json`, `done.json` paths from config. Checklist provider expects `roadmap.md` + ephemeral prompts directory.

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
  - `kanban-transition` (haiku): runs gate set (parallel), WIP, archive scrubbing, external validation. Medium complexity.
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
- Lifecycle enforcement:
  - backlog (lean) → board (rich) requires expansion of planning fields (`worktree`, `dev_agent`, `qa_agent`, `dev_prompt`, `qa_prompt`, `acceptance_criteria`, `max_retries`).
  - review → done triggers scrubbing: keep `sprint_id`, `title`, `pr_url`, `completed_at`, `actual_cycles`; drop rich prompts/criteria/assignments.

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
- PM visibility: PM operates on references (worktree/pr_url/status_report) and does not need rich prompts once planning is done; rich fields stay on board.json until review→done scrubbing.

## 10) Templates (Solo Dev / Team Sprint / QA Pipeline)
- Retain structures; upgrade semantics to v0.5 envelope + gate/check schema; add git cleanliness gates before entering review columns.

## 11) Implementation Plan (delta-focused)
- Add shared board YAML schema (versioned) used by sc-project-manager; support `provider=kanban` (default) and `provider=checklist` (fallback).
- Validate board config with Pydantic v2 models (strict mode) and fail closed on version mismatch.
- Update all agents to v0.5 envelope + versioned frontmatter; register in `.claude/agents/registry.yaml`; require Agent Runner invocation.
- Add Python automation scripts and wire `kanban-transition` to `run_gates.py`.
- Implement parallel gate runner with timeout/concurrency controls and deterministic aggregation.
- Enhance error contract in `kanban-transition`: `failed_gates`, `warnings`, `summary`, `aborted_by`.
- Add git cleanliness gates; PR/worktree checks prefer tools, fall back to filesystem/attestation.
- Update SKILL.md to surface partial results and suggested actions.
- Docs: refresh README/TROUBLESHOOTING with codes, suggested actions, attestation policy.
- Tests (pytest in release pipeline): parallel gates, timeouts, missing tools, git dirty/not pushed, multi-agent arrays with partial failures, archive scrubbing failures, WIP blocking vs warning, board config validation (see tests/test_board_config.py) and lifecycle file moves (backlog→board→done).
- Gate execution (v0.7.1+): add PR/GIT/worktree gates with codes/actions; current v0.7.0 code stubs gates (kanban-transition TODO).

## 12) Success Criteria (v0.7.0)
- All agents return v0.5-compliant fenced JSON with registry-validated versions.
- Parallel gate runner reports partials with per-item evidence/actions; PM can remediate and retry.
- Automated worktree/PR/git checks reduce manual multi-agent hops; clear remediation guidance.
- Missing tool/timeout paths return structured errors with recoverability guidance; no silent degradation.
- Archive/WIP enforcement emit explicit codes; no silent skips.
- Shared YAML config works for both sc-kanban and sc-project-manager; when kanban provider absent, checklist fallback path returns structured advisory and preserves schema compatibility.
- v0.7.0: pr_url gate only; full gate suite deferred to v0.7.1 (scripts stubbed).
