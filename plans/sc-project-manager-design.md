# Project Manager Skill - Revised Design Document

**Target Release:** Marketplace v0.7.0  
**Integration:** Prefers sc-kanban as task engine via shared YAML board config; degrades to markdown checklist agent if kanban unavailable (same fenced JSON contract).  
**Alignment:** v0.5 envelopes + registry/attestation (Agent Runner), shared schema with sc-git-worktree naming and sprint grammar.

## Updated Architecture

Based on your clarifications and the sc-git-worktree interface analysis:

### Package Structure

```
sc-project-manager/
├── manifest.yaml
├── README.md
├── CHANGELOG.md
├── TROUBLESHOOTING.md
├── USE-CASES.md
├── commands/
│   ├── project-init.md           # /project-init <path-to-checklist>
│   ├── project-resume.md         # /project-resume <path-to-checklist>
│   └── project-status.md         # /project-status [--light|--deep]
├── skills/
│   └── sc-project-manager/
│       └── SKILL.md              # Main skill orchestration doc
├── agents/
│   ├── sc-pm-manager.md          # v0.7.0: Foreground PM (user-facing)
│   ├── sc-pm-scrum-master.md     # v0.7.0: Standard sprint coordinator
│   ├── sc-pm-dev-default.md      # v0.7.0: Default dev agent (fallback)
│   ├── sc-pm-qa-default.md       # v0.7.0: Default QA agent (fallback)
│   └── future/                   # v0.8.0+
│       ├── sc-pm-planner.md          # Creates initial project structure
│       ├── sc-pm-status.md           # Status analysis agent
│       ├── sc-pm-parallel-scrum.md   # Multi-worktree coordinator
│       ├── sc-pm-competitive-scrum.md # A/B solution coordinator
│       └── sc-pm-merge.md            # Branch merge specialist
└── templates/
    ├── master-checklist.md
    ├── project-settings.json
    ├── board.config.example.yaml
    ├── sprint-plan.md
    └── startup-prompt.md
```

### File Naming Convention (Multi-Project Support)

Given a project checklist at `/projects/my-app/.project/roadmap.md`:

```
roadmap.md                  # Master checklist
roadmap.json                # Project settings (same basename)
roadmap-worktrees.json      # Active worktree registry
roadmap-startup.md          # PM agent startup prompt
```

This allows multiple projects in the same repo:
```
/repo/.project/
├── backend-migration.md
├── backend-migration.json
├── backend-migration-worktrees.json
├── backend-migration-startup.md
├── frontend-redesign.md
├── frontend-redesign.json
├── frontend-redesign-worktrees.json
└── frontend-redesign-startup.md
```

### Sprint Identifier Grammar

```
Phase:  <number>[<letter>]*          → 1, 2, 3a, 3b, 12, 3ab
Sprint: <phase>.<number>[<letter>]*  → 1.1, 3a.2, 3b.2a, 3b.2b
```

### Worktree Naming (via sc-git-worktree)

Pattern: `<project-branch>/<sprint-id>-<sprint-name>` with normalization (`.` → `-`, ` ` → `-`)

Examples:
- `main/1-1-project-setup`
- `main/3a-2b-api-validation`
- `develop/2-1a-auth-service`

The project manager will invoke `sc-git-worktree` agents with appropriate branch names.

### PM Daily Cadence (Autonomous Loop)
- Morning (user/ARCH): select 8–10 items from backlog.json (lean), expand into rich cards on board.json (add worktree, dev/qa agents, prompts, acceptance_criteria, max_retries).
- Daytime (PM unattended): run planned→active→review cycles, coordinating scrum-master and dev→QA iterations; accumulate PRs, update status_report and actual_cycles.
- Evening (user): review PRs and transition review→done; kanban scrubs rich fields into done.json (keep sprint_id, title, pr_url, completed_at, actual_cycles).

### Shared Board Config (with sc-kanban)

- Single YAML source of truth shared with sc-kanban (default path: `.project/board.config.yaml`; override via command flag/env). Versioned to 0.7 schema. Example config: `templates/board.config.example.yaml`.
- Kanban provider uses three files: `backlog.json` (lean), `board.json` (rich), `done.json` (scrubbed). Checklist provider uses `roadmap.md` + ephemeral `prompts/<sprint_id>.md` (no gates).
- Provider flag allows plug-in swap between kanban engine and markdown checklist agent while keeping the same fenced JSON interface and card schema.
- Config is validated (Pydantic v2 strict models) before orchestration; mutations are refused on version mismatch or invalid schema.
- Card schema (kanban provider):
  - Backlog (lean): `sprint_id`, `title`, `dependencies`.
  - Board (rich planning): `worktree`, `dev_agent`, `qa_agent`, `dev_prompt`, `qa_prompt`, `acceptance_criteria`, `max_retries`, `base_branch`.
  - Execution updates: `pr_url`, `status_report`, `actual_cycles`, `started_at`, `completed_at`, `status`.
  - Done (scrubbed): keep `sprint_id`, `title`, `pr_url`, `completed_at`, `actual_cycles`; drop prompts/criteria/assignments.
- Current status: Core board operations implemented; gates stubbed (v0.7.1), PM agents not yet implemented.
- Example:
  ```yaml
  version: 0.7
  board:
    backlog_path: .project/backlog.json
    board_path: .project/board.json
    done_path: .project/done.json
    provider: kanban                   # kanban|checklist
    wip:
      per_column:
        active: 3
        review: 2
    columns:
      - id: planned
      - id: active
      - id: review
      - id: done
  cards:
    fields:
      - id: worktree
        required: true
      - id: pr_url
        required: false
      - id: assignee
        required: false
    conventions:
      worktree_pattern: "<project-branch>/<sprint-id>-<sprint-name>"
      sprint_id_grammar: "<phase>.<number>[<letter>]*"
  agents:
    transition: sc-kanban/kanban-transition
    query: sc-kanban/kanban-query
    checklist_fallback: checklist-agent/query-update
  ```
- When `provider=kanban`, PM calls sc-kanban agents for `transition`/`query` and consumes `failed_gates`/`warnings`. When `provider=checklist`, PM swaps to the checklist agent but keeps the same envelope contract and card fields.

---

## Schema Definitions

### project-settings.json (roadmap.json)

```json
{
  "$schema": "./schemas/project-settings.schema.json",
  "projectName": "Backend Migration",
  "planName": "backend-migration",
  "repoPath": "/Users/randlee/projects/my-app",
  "repoUrl": "git@github.com:org/my-app.git",
  "mainBranch": "main",
  "projectDocsPath": ".project",
  
  "agents": {
    "dev": [
      {
        "name": "dotnet-dev",
        "path": ".claude/agents/dotnet-dev.md",
        "tags": ["csharp", "dotnet", "api", "backend"],
        "description": "Specialized for C#/.NET development"
      },
      {
        "name": "react-dev", 
        "path": ".claude/agents/react-dev.md",
        "tags": ["typescript", "react", "frontend"],
        "description": "Specialized for React/TypeScript frontend"
      }
    ],
    "qa": [
      {
        "name": "integration-qa",
        "path": ".claude/agents/integration-qa.md",
        "tags": ["integration", "api", "e2e"],
        "description": "Integration and E2E testing specialist"
      },
      {
        "name": "unit-qa",
        "path": ".claude/agents/unit-qa.md", 
        "tags": ["unit", "tdd", "coverage"],
        "description": "Unit testing and coverage specialist"
      }
    ]
  },
  
  "conventions": {
    "commitStyle": "conventional",
    "prTemplate": ".github/PULL_REQUEST_TEMPLATE.md",
    "worktreeBase": "../{{REPO_NAME}}-worktrees",
    "trackingEnabled": true
  },
  
  "workflow": {
    "autoCommit": true,
    "autoPush": true,
    "autoCreatePR": true,
    "requireReviewBeforeMerge": true
  }
}
```

### worktree-list.json (roadmap-worktrees.json)

```json
{
  "$schema": "./schemas/worktree-list.schema.json",
  "planName": "backend-migration",
  "worktrees": [
    {
      "sprintId": "3a.2b",
      "sprintName": "api-validation",
      "worktreeBranch": "main/3a-2b-api-validation",
      "path": "../my-app-worktrees/main/3a-2b-api-validation",
      "baseBranch": "main",
      "status": "active",
      "assignedAgents": {
        "dev": "dotnet-dev",
        "qa": "integration-qa"
      },
      "createdAt": "2025-01-15T10:30:00Z",
      "lastActivity": "2025-01-15T14:22:00Z",
      "scrumMasterType": "standard",
      "notes": ""
    }
  ],
  "archived": []
}
```

### Master Checklist Structure (roadmap.md) — checklist provider only

```markdown
# Backend Migration Roadmap

## Project Overview
Brief description and goals.

## Documents
- Requirements: [requirements.md](./requirements.md)
- ADR Log: [adr/](./adr/)
- Test Plan: [test-plan.md](./test-plan.md)

---

## Phase 1: Foundation
> Status: In Progress | Started: 2025-01-10

### Sprint 1.1: Project Setup
- **Status**: ✅ Complete
- **Worktree**: `main/1-1-project-setup`
- **Agent**: dotnet-dev
- **Deliverables**:
  - [x] Initialize solution structure
  - [x] Configure CI/CD pipeline
  - [x] Setup development environment
- **Review**: [Requirement Review](./reviews/1.1-req-review.md) ✅

### Sprint 1.2a: Database Schema (Parallel A)
- **Status**: 🔄 Active
- **Worktree**: `main/1-2a-database-schema`
- **Agent**: dotnet-dev
- **Deliverables**:
  - [ ] Design entity models
  - [ ] Create migrations
- **Review**: Pending

### Sprint 1.2b: API Contracts (Parallel B)
- **Status**: 🔄 Active
- **Worktree**: `main/1-2b-api-contracts`
- **Agent**: dotnet-dev
- **Deliverables**:
  - [ ] Define OpenAPI spec
  - [ ] Generate client SDKs
- **Review**: Pending

---

## Phase 2: Core Implementation
> Status: Not Started

### Sprint 2.1: Authentication Service
- **Status**: ⏳ Pending
- **Depends On**: 1.2a, 1.2b
- **Agent**: (scrum-master selects)
...

---

## Phase 3a: Performance Optimization (Inserted)
> Status: Not Started | Inserted after Phase 3 scope expansion

### Sprint 3a.1: Caching Layer
...
```

---

## Agent Interaction Model

### Delegation Flow (Task Tool)

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│              /project-resume roadmap.md                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   COMMAND HANDLER                                │
│              (project-resume.md)                                 │
│  1. Validate checklist path                                      │
│  2. Load project settings + shared board config (yaml)           │
│  3. Select provider: kanban (preferred) or checklist fallback    │
│  4. Task → sc-pm-status (background) using provider agents       │
│  5. Read startup prompt                                          │
│  6. Task → sc-pm-manager (foreground handoff)                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ sc-pm-status  │   │ sc-pm-manager │   │    (other)    │
│  (background) │   │  (foreground) │   │               │
│               │   │               │   │               │
│ • Analyze git │   │ • User dialog │   │               │
│ • Update docs │   │ • Decisions   │   │               │
│ • Flag stale  │   │ • Delegate    │   │               │
└───────────────┘   └───────┬───────┘   └───────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │ sc-pm-scrum │   │sc-pm-parallel│  │ sc-pm-merge │
   │   -master   │   │   -scrum    │   │             │
   └──────┬──────┘   └──────┬──────┘   └─────────────┘
          │                 │
          ▼                 ▼
   ┌─────────────────────────────────┐
   │   sc-git-worktree agents        │
   │   (create, scan, cleanup)       │
   └─────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────┐
   │   DEV AGENT → QA AGENT cycle    │
   │   (project-specific or default) │
   └─────────────────────────────────┘
```

### Agent Selection Logic

```
1. Sprint specifies agent in plan?
   → Use specified agent

2. No agent specified, project-settings.json has agents?
   → Scrum-master matches sprint tags to agent tags
   → Select best-fit agent

3. No agents in project-settings.json?
   → Scrum-master uses sc-pm-dev-default / sc-pm-qa-default
   → OR creates inline agent prompt based on sprint requirements
```

Provider selection for task tracking (shared with sc-kanban):
- If `provider=kanban`, status/manager/scrum agents call `kanban-query` for reads and `kanban-transition` for moves/archives, consuming `failed_gates`/`warnings`.
- If `provider=checklist`, the same calls route to the checklist agent (`templates/checklist-agent.md`), which returns the same v0.5 envelope shape so orchestration code is unchanged.
- Checklist provider flow: PM reads `roadmap.md`, creates ephemeral prompts under `prompts/<sprint_id>.md`, runs manual transitions (no gates), and stores lean card refs; does not use backlog/board/done JSON files.

---

## Scrum Master Sprint Process (Detailed)

### Standard Scrum Master Flow

```
sc-pm-scrum-master receives sprint assignment:

a) VERIFY STARTING CONDITIONS
   - Read sprint plan from checklist
   - Verify base branch exists and is clean
   - Check dependencies (prior sprints complete)
   - Load agent assignments or select agents
   - Query board via provider (kanban-query or checklist agent) to ensure card exists with matching worktree naming

b) CREATE WORKTREE
   - Task → sc-git-worktree-create
     branch: <project-branch>/<sprint-id>-<sprint-name>
     base: <base-branch>
     purpose: <sprint-description>
   - Update roadmap-worktrees.json
   - Create/update rich card on board.json (kanban provider) with prompts, acceptance_criteria, max_retries

c) VERIFY WORKTREE
   - Confirm worktree clean
   - Review sprint plan details
   - Prepare agent context/prompts

d) LAUNCH DEV AGENT
   - Task → <selected-dev-agent>
     context: sprint plan, requirements, acceptance criteria
   - Await completion (JSON result)

e) LAUNCH QA AGENT
   - Task → <selected-qa-agent>
     context: sprint plan, dev changes, test criteria
   - Await completion (JSON result with quality assessment)

f) EVALUATE QUALITY
   IF quality == "pass":
     - Commit/push if autoCommit enabled
     - Create PR if autoCreatePR enabled
     - Update checklist status
     - Update board via provider transition (kanban-transition or checklist agent) with gate results
     - On kanban provider, prepare for review→done scrubbing (PR merged, worktree removed, code clean)
     - Report success to PM
   
   IF quality == "minor_issues":
     - Task → dev agent (fix iteration)
     - GOTO (e)
   
   IF quality == "major_issues":
     - Prepare detailed report
     - Offer choice to PM/user:
       • Attempt fix (continue)
       • Abort sprint (escalate)
     - Await decision

g) CLEANUP (on completion or abort)
   - If merged: Task → sc-git-worktree-cleanup
   - If aborted: Task → sc-git-worktree-abort
   - Update roadmap-worktrees.json
```

### Parallel Scrum Master (Additional Responsibilities)

```
sc-pm-parallel-scrum coordinates multiple related worktrees:

1. Create all worktrees upfront
2. Launch dev agents in parallel (non-blocking Tasks)
3. Monitor progress across all branches
4. Coordinate merge sequence:
   - Identify merge order (dependency-aware)
   - Task → sc-pm-merge for each
   - Resolve conflicts if needed
5. Final integration QA on unified branch
```

### Competitive Scrum Master (A/B Solutions)

```
sc-pm-competitive-scrum runs same work on multiple approaches:

1. Create N worktrees for N approaches
2. Launch dev agents with different constraints/approaches
3. Run QA on all solutions
4. Prepare comparison report:
   - Quality metrics per solution
   - Performance characteristics
   - Code complexity comparison
   - Recommendation
5. Present options to PM/user for selection
6. Cleanup non-selected branches
```

---

## Dependencies

This skill depends on:
- **sc-git-worktree** (v0.5.2+): Worktree creation, scanning, cleanup, and abort operations
- **sc-kanban** (preferred): Transition/query gates, WIP enforcement, git/PR validation via shared YAML config
- **checklist-agent** (fallback): Markdown checklist read/update with same fenced JSON envelope when `provider=checklist`

---

## Questions Before Implementation

1. **Project docs location**: You mentioned "user defined location in the dev repo". Should this default to `.project/` at repo root, or should we require explicit configuration?

2. **Startup prompt scope**: Should `roadmap-startup.md` be auto-generated by the planner, or is it a template the user customizes? What key context should it contain?

3. **Status agent parallelism**: For `--deep-dive`, should the status agent spawn multiple background agents (one per worktree analysis), or handle sequentially?

4. **PR creation**: When scrum-master creates PR, should it:
   - Draft PR only (require manual review trigger)
   - Full PR with auto-request reviewers
   - Configurable per project?

5. **Package location**: Should this be created in your synaptic-canvas packages directory alongside sc-git-worktree?

---

## Implementation Order

Once questions are resolved:

1. `manifest.yaml` - Package definition
2. `SKILL.md` - Main skill documentation
3. Command handlers (project-init, project-resume, project-status)
4. Core agents (planner, manager, status)
5. Scrum master agents (standard, parallel, competitive)
6. Merge agent
7. Default dev/qa agents
8. Templates
9. README and supporting docs
