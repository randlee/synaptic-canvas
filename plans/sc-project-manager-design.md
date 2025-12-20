# Project Manager Skill - Revised Design Document

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
│   ├── sc-pm-planner.md          # Creates initial project structure
│   ├── sc-pm-manager.md          # Foreground PM (user-facing)
│   ├── sc-pm-status.md           # Status analysis agent
│   ├── sc-pm-scrum-master.md     # Standard sprint coordinator
│   ├── sc-pm-parallel-scrum.md   # Multi-worktree coordinator
│   ├── sc-pm-competitive-scrum.md # A/B solution coordinator
│   ├── sc-pm-merge.md            # Branch merge specialist
│   ├── sc-pm-dev-default.md      # Default dev agent (fallback)
│   └── sc-pm-qa-default.md       # Default QA agent (fallback)
└── templates/
    ├── master-checklist.md
    ├── project-settings.json
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

### Master Checklist Structure (roadmap.md)

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
│  2. Load project settings                                        │
│  3. Task → sc-pm-status (background)                            │
│  4. Read startup prompt                                          │
│  5. Task → sc-pm-manager (foreground handoff)                   │
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

b) CREATE WORKTREE
   - Task → sc-git-worktree-create
     branch: <project-branch>/<sprint-id>-<sprint-name>
     base: <base-branch>
     purpose: <sprint-description>
   - Update roadmap-worktrees.json

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
