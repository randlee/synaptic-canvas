# sc-kanban Package Design Document

**Version:** 0.1.0
**Status:** Design Complete - Ready for Implementation
**Created:** 2025-12-11
**Target Release:** v0.7.0 (Marketplace)

---

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [Architecture](#architecture)
4. [File Structure](#file-structure)
5. [Configuration Schema](#configuration-schema)
6. [Phase & Sprint Numbering](#phase--sprint-numbering)
7. [Field Structure](#field-structure)
8. [Card Formats](#card-formats)
9. [State Transition & Gates](#state-transition--gates)
10. [Multi-Agent Support](#multi-agent-support)
11. [Templates](#templates)
12. [Query Operations](#query-operations)
13. [Integration Points](#integration-points)
14. [Implementation Plan](#implementation-plan)
15. [Success Criteria](#success-criteria)

---

## Overview

### Purpose

sc-kanban provides a **pure state machine** for task card management. It validates state transitions, enforces gates, and maintains card lifecycle without dictating workflow or agent orchestration.

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Card CRUD operations | Who calls kanban agents |
| Schema validation | Why transitions happen |
| State transitions with gates | Workflow orchestration |
| WIP limit enforcement | Agent coordination |
| Phase/sprint organization | Dependency resolution |
| Multi-agent sprint tracking | PR creation/merging |
| Board queries and filters | Worktree creation |

### Key Insight

**Kanban is infrastructure, not application logic.** PM/Scrum Master agents orchestrate work and use kanban to enforce gates and maintain state. Kanban validates "can this transition happen?" but doesn't decide "should it happen?"

---

## Design Principles

### 1. Pure State Machine
- Kanban agents manage state transitions only
- No workflow decisions or orchestration
- Gates enforce "must-have" conditions
- Checks provide "should-have" recommendations

### 2. Configuration-Driven
- Board structure defined per-repo in `config.json`
- No hardcoded columns or transitions
- Templates provide starting points
- Users customize for their workflow

### 3. Consumer-Agnostic
- Works with any PM/dev agent system
- JSON interface for all operations
- No opinions on agent coordination
- Extensible for different workflows

### 4. Gate Enforcement
- **Gates (blocking):** Transition fails if not satisfied
- **Checks (advisory):** Transition succeeds with warnings
- External state validation (worktree exists, PR merged)
- Clear error messages with suggested actions

### 5. Multi-Agent Native
- Single-agent sprints: scalar fields (worktree, pr_url)
- Multi-agent sprints: array fields (worktrees[])
- Hybrid support for flexibility
- ALL worktrees/PRs validated (strict enforcement)

---

## Architecture

### Components

```
sc-kanban/
├── Command:  /kanban <action>           # User-facing interface
├── Skill:    sc-kanban/SKILL.md         # Orchestration layer
└── Agents:   4 focused agents           # Execution layer
    ├── kanban-init                      # Setup: wizard, migration
    ├── kanban-card                      # CRUD: create, update
    ├── kanban-transition                # State: move, archive
    └── kanban-query                     # Read: list, filter, validate
```

### Agent Responsibilities

| Agent | Purpose | Complexity | Size |
|-------|---------|------------|------|
| **kanban-init** | Board setup, Q&A wizard, checklist migration | High (wizard) | 4-6KB |
| **kanban-card** | Create/update cards (field mutations only) | Low (CRUD) | 2-3KB |
| **kanban-transition** | Move between columns, validate gates, archive | High (gates) | 5-7KB |
| **kanban-query** | Parse/filter cards, validate board, statistics | Medium (parsing) | 3-4KB |

### Command Operations

```bash
# Setup
/kanban init                    # Start Q&A wizard
/kanban migrate <file>          # Import existing checklist

# Card operations
/kanban create <details>        # Create new card
/kanban update <card> <fields>  # Update card fields
/kanban move <card> <column>    # Transition with validation
/kanban archive <card>          # Complete and archive

# Queries
/kanban list                    # Show all cards
/kanban list active             # Cards in specific column
/kanban list phase:1            # Filter by phase
/kanban list project:foo        # Filter by project
/kanban status --by-phase       # Phase-level rollup
```

### Skill Orchestration

The skill layer (`SKILL.md`) translates user intent to agent invocations:

```
User: /kanban move synaptic-canvas-1.1 active

Skill:
  1. Parse: action=move, card=synaptic-canvas-1.1, to=active
  2. Invoke: kanban-transition agent
  3. Receive: { success: false, error: { code: "GATE_VIOLATION", ... } }
  4. Format: "Cannot move to active: worktree not created. Create worktree first."
```

---

## File Structure

### Directory Layout

```
.kanban/
├── config.json         # Board configuration (columns, gates, rules)
├── backlog.md          # Aggregate file for backlog cards
├── done.md             # Aggregate file for archived cards (scrubbed)
├── planned/            # Directory for planned cards
│   ├── project-1.1.md
│   └── project-1.2.md
├── active/             # Directory for in-progress cards
│   ├── project-1.1.md
│   └── project-1.2a.md
└── review/             # Directory for cards awaiting acceptance
    └── project-1.3.md
```

### Column Types

| Type | Storage | Use Case | Access Pattern |
|------|---------|----------|----------------|
| **aggregate** | Single file, cards as markdown sections | High-volume, low-churn (backlog, done) | Sequential reads |
| **directory** | File per card | Active work, frequent updates | Random access |

**Optimization Strategy:**
- Backlog: Aggregate (many cards, rarely modified individually)
- Active columns: Directory (few cards, frequent updates)
- Done: Aggregate (append-only archive, rarely accessed)

---

## Configuration Schema

### config.json Structure

```json
{
  "version": "1.0",
  "board": {
    "name": "Project Board",
    "columns": ["backlog", "planned", "active", "review", "done"]
  },
  "columns": {
    "backlog": {
      "type": "aggregate",
      "file": "backlog.md",
      "wip": null
    },
    "planned": {
      "type": "directory",
      "wip": 5,
      "wip_enforcement": "blocking"
    },
    "active": {
      "type": "directory",
      "wip": 3,
      "wip_enforcement": "blocking"
    },
    "review": {
      "type": "directory",
      "wip": 3,
      "wip_enforcement": "blocking"
    },
    "done": {
      "type": "aggregate",
      "file": "done.md",
      "wip": null,
      "scrub": ["worktree", "worktrees", "branch", "assignee", "log"]
    }
  },
  "transitions": {
    "backlog → planned": {
      "gates": [],
      "checks": []
    },
    "planned → active": {
      "gates": [
        { "rule": "field_required", "field": "worktree", "enforcement": "blocking" },
        { "rule": "worktree_exists", "field": "worktree", "enforcement": "blocking" }
      ],
      "checks": [
        { "rule": "field_required", "field": "assignee", "enforcement": "warning" }
      ]
    },
    "active → review": {
      "gates": [
        { "rule": "field_required", "field": "pr_url", "enforcement": "blocking" }
      ],
      "checks": [
        { "rule": "tasks_complete", "enforcement": "warning" }
      ]
    },
    "review → done": {
      "gates": [
        { "rule": "pr_merged", "field": "pr_url", "enforcement": "blocking" },
        { "rule": "worktree_removed", "field": "worktree", "enforcement": "blocking" }
      ],
      "checks": [
        { "rule": "branch_deleted", "field": "branch", "enforcement": "warning" }
      ]
    }
  },
  "rules": {
    "field_required": {
      "description": "Field must be non-empty",
      "category": "validation"
    },
    "tasks_complete": {
      "description": "All tasks in card marked complete",
      "category": "validation"
    },
    "worktree_exists": {
      "description": "Worktree path exists on filesystem",
      "category": "external_state",
      "requires": "filesystem_access"
    },
    "worktree_removed": {
      "description": "Worktree has been deleted",
      "category": "external_state",
      "requires": "filesystem_access"
    },
    "branch_deleted": {
      "description": "Branch no longer exists in remote",
      "category": "external_state",
      "requires": "git"
    },
    "pr_merged": {
      "description": "PR at URL shows merged status",
      "category": "external_state",
      "requires": "gh"
    }
  },
  "fields": {
    "project": { "type": "string", "required": true, "transient": false },
    "phase": {
      "type": "string",
      "required": true,
      "transient": false,
      "pattern": "^[0-9]+[a-z]*$"
    },
    "sprint": {
      "type": "string",
      "required": true,
      "transient": false,
      "pattern": "^[0-9]+[a-z]*\\.[0-9]+[a-z]*$"
    },
    "title": { "type": "string", "required": true, "transient": false },
    "worktree": { "type": "path", "transient": true },
    "worktrees": { "type": "array", "items": "object", "transient": true },
    "branch": { "type": "string", "transient": true },
    "pr_url": { "type": "url", "transient": true },
    "assignee": { "type": "string", "transient": true }
  },
  "validation": {
    "sprint_matches_phase": true
  }
}
```

### WIP Enforcement Levels

```json
"wip_enforcement": "blocking"  // Default: transition fails if WIP exceeded
"wip_enforcement": "warning"   // Transition succeeds, logs warning
```

---

## Phase & Sprint Numbering

### Grammar (from sc-project-manager)

```
Phase:  <number>[<letter>]*          → 1, 2, 3a, 3b, 12, 3ab
Sprint: <phase>.<number>[<letter>]*  → 1.1, 3a.2, 3b.2a, 3b.2b
```

### Examples

**Simple progression:**
- Phase 1 → Sprints: 1.1, 1.2, 1.3
- Phase 2 → Sprints: 2.1, 2.2

**Parallel sprints (letter suffix):**
- Phase 1 → Sprints: 1.1, 1.2a, 1.2b (1.2a and 1.2b run in parallel)

**Phase expansion:**
- Original Phase 3 splits into Phase 3a and Phase 3b
- Phase 3a → Sprints: 3a.1, 3a.2
- Phase 3b → Sprints: 3b.1, 3b.2

**Multi-level parallel:**
- Phase 3a → Sprints: 3a.2a, 3a.2b (parallel within expanded phase)

### Validation Rules

```python
def validate_sprint_matches_phase(card):
    phase = card.get("phase")
    sprint = card.get("sprint")

    # Sprint must start with phase followed by '.'
    if not sprint.startswith(f"{phase}."):
        return {
            "valid": False,
            "error": f"Sprint '{sprint}' must start with phase '{phase}.'"
        }
    return {"valid": True}
```

### Use Cases

**Phase organization:**
```bash
/kanban list phase:1           # All Phase 1 sprints
/kanban status --by-phase      # Progress per phase
```

**Query examples:**
- `phase:1` → Sprints 1.1, 1.2, 1.2a, 1.2b
- `phase:3a` → Sprints 3a.1, 3a.2, 3a.2a, 3a.2b
- `sprint:1.2a` → Exact sprint match

---

## Field Structure

### Hybrid Scalar/Array Support

**Single-agent sprint (scalar fields):**
```yaml
project: synaptic-canvas
phase: "1"
sprint: "1.1"
title: Project Setup
worktree: /worktrees/synaptic-canvas-1-1-project-setup
branch: main/1-1-project-setup
assignee: agent/dotnet-dev
pr_url: https://github.com/org/repo/pull/123
```

**Multi-agent sprint (array fields):**
```yaml
project: synaptic-canvas
phase: "2"
sprint: "2.1"
title: Authentication Service
worktrees:
  - path: /worktrees/synaptic-canvas-2-1-backend
    branch: main/2-1-auth-backend
    assignee: agent/dotnet-dev
    pr_url: https://github.com/org/repo/pull/124
  - path: /worktrees/synaptic-canvas-2-1-frontend
    branch: main/2-1-auth-frontend
    assignee: agent/react-dev
    pr_url: https://github.com/org/repo/pull/125
  - path: /worktrees/synaptic-canvas-2-1-tests
    branch: main/2-1-auth-tests
    assignee: agent/qa
    pr_url: https://github.com/org/repo/pull/126
```

### Field Definitions

```json
{
  "fields": {
    "project": {
      "type": "string",
      "required": true,
      "transient": false,
      "description": "Project name"
    },
    "phase": {
      "type": "string",
      "required": true,
      "transient": false,
      "pattern": "^[0-9]+[a-z]*$",
      "description": "Phase number with optional letter suffix (e.g., 1, 3a)"
    },
    "sprint": {
      "type": "string",
      "required": true,
      "transient": false,
      "pattern": "^[0-9]+[a-z]*\\.[0-9]+[a-z]*$",
      "description": "Sprint identifier: <phase>.<number>[letter] (e.g., 1.1, 3a.2b)"
    },
    "title": {
      "type": "string",
      "required": true,
      "transient": false
    },
    "worktree": {
      "type": "path",
      "transient": true,
      "description": "Single worktree path (single-agent)"
    },
    "worktrees": {
      "type": "array",
      "items": {
        "path": { "type": "path", "required": true },
        "branch": { "type": "string", "required": true },
        "assignee": { "type": "string" },
        "pr_url": { "type": "url" }
      },
      "transient": true,
      "description": "Multiple worktrees (multi-agent)"
    },
    "branch": { "type": "string", "transient": true },
    "pr_url": { "type": "url", "transient": true },
    "assignee": { "type": "string", "transient": true }
  }
}
```

### Transient vs Permanent Fields

**Transient fields** (scrubbed on archive):
- `worktree` / `worktrees`: Temporary development paths
- `branch`: Feature branch names
- `pr_url`: PR links (merged PRs don't need links in archive)
- `assignee`: Agent assignments (not relevant after completion)
- `log`: Detailed activity log

**Permanent fields** (retained in archive):
- `project`: Essential for organization
- `phase`: Grouping and rollups
- `sprint`: Identification and reference
- `title`: What was accomplished
- Completion metadata: duration, outcomes

---

## Card Formats

### Backlog Card (Aggregate)

**File:** `.kanban/backlog.md`

```markdown
# Backlog

## synaptic-canvas

### Phase 1: Foundation

#### Sprint 1.1: Project Setup
- project: synaptic-canvas
- phase: 1
- sprint: 1.1
- priority: high
- estimate: 2 days

**Tasks:**
- [ ] Initialize solution structure
- [ ] Configure CI/CD pipeline
- [ ] Setup development environment

---

#### Sprint 1.2: Database Schema
- project: synaptic-canvas
- phase: 1
- sprint: 1.2
- priority: high
- estimate: 3 days
```

### Active Card (Directory, Single-Agent)

**File:** `.kanban/active/synaptic-canvas-1.1.md`

```yaml
---
project: synaptic-canvas
phase: "1"
sprint: "1.1"
title: Project Setup
status: active
created: 2025-12-10T14:00:00Z
started: 2025-12-10T15:30:00Z
worktree: /Users/dev/worktrees/synaptic-canvas-1-1-project-setup
branch: main/1-1-project-setup
assignee: agent/dotnet-dev
pr_url: null
---

# synaptic-canvas / Phase 1, Sprint 1.1: Project Setup

## Phase Context
**Phase 1: Foundation** - Establish core infrastructure

## Tasks
- [x] Initialize solution structure
- [ ] Configure CI/CD pipeline
- [ ] Setup development environment

## Log
| Timestamp           | Actor            | Action                    |
|---------------------|------------------|---------------------------|
| 2025-12-10 14:00:00 | pm               | Created from backlog      |
| 2025-12-10 15:30:00 | pm               | Moved to active           |
```

### Active Card (Directory, Multi-Agent)

**File:** `.kanban/active/synaptic-canvas-2.1.md`

```yaml
---
project: synaptic-canvas
phase: "2"
sprint: "2.1"
title: Authentication Service
status: active
created: 2025-12-12T10:00:00Z
started: 2025-12-12T11:00:00Z
worktrees:
  - path: /Users/dev/worktrees/synaptic-canvas-2-1-auth-backend
    branch: main/2-1-auth-backend
    assignee: agent/dotnet-dev
    pr_url: null
  - path: /Users/dev/worktrees/synaptic-canvas-2-1-auth-frontend
    branch: main/2-1-auth-frontend
    assignee: agent/react-dev
    pr_url: null
  - path: /Users/dev/worktrees/synaptic-canvas-2-1-auth-tests
    branch: main/2-1-auth-tests
    assignee: agent/qa
    pr_url: null
---

# synaptic-canvas / Phase 2, Sprint 2.1: Authentication Service

## Phase Context
**Phase 2: Core Implementation** - First major feature sprint

## Work Distribution

### Backend (agent/dotnet-dev) ⏳
**Worktree:** `/Users/dev/worktrees/synaptic-canvas-2-1-auth-backend`
- [x] Implement JWT token generation
- [ ] Setup OAuth2 providers
- [ ] Add refresh token logic

### Frontend (agent/react-dev)
**Worktree:** `/Users/dev/worktrees/synaptic-canvas-2-1-auth-frontend`
- [ ] Login/logout UI
- [ ] Token storage
- [ ] Protected route wrapper

### QA (agent/qa)
**Worktree:** `/Users/dev/worktrees/synaptic-canvas-2-1-auth-tests`
- [ ] Auth flow E2E tests
- [ ] Security audit
```

### Archived Card (Aggregate, Scrubbed)

**File:** `.kanban/done.md`

```markdown
# Completed Work

## 2025-12

### synaptic-canvas / Phase 1, Sprint 1.1: Project Setup ✅

**Summary:**
| Field      | Value                        |
|------------|------------------------------|
| Project    | synaptic-canvas              |
| Phase      | 1                            |
| Sprint     | 1.1                          |
| Completed  | 2025-12-10 18:00:00          |
| Duration   | 2.5 hours                    |
| Tasks      | 3/3 complete                 |

**Deliverables:**
- Solution structure initialized
- CI/CD pipeline configured
- Development environment ready

**Outcomes:**
- PR #123 merged
- All tests passing

<details>
<summary>Task Details (3)</summary>

| ID  | Title                          | Completed           |
|-----|--------------------------------|---------------------|
| 1   | Initialize solution structure  | 2025-12-10 16:00:00 |
| 2   | Configure CI/CD pipeline       | 2025-12-10 17:00:00 |
| 3   | Setup development environment  | 2025-12-10 18:00:00 |

</details>

---
```

**Note:** Transient fields scrubbed (worktree, branch, assignee, pr_url, log).

---

## State Transition & Gates

### Gates vs Checks

**Gates (blocking):**
- Transition FAILS if gate not satisfied
- Returns error with code `GATE_VIOLATION`
- User/PM must remediate before proceeding
- Examples: PR not merged, worktree not created

**Checks (advisory):**
- Transition SUCCEEDS with warnings
- Returns success with `warnings` array
- User sees recommendations
- Examples: Tasks not complete, branch not deleted

### Gate Validation Flow

```
┌──────────────────────────────────────────────────────────────┐
│  /kanban move active/sprint-1.1 review                       │
├──────────────────────────────────────────────────────────────┤
│  1. kanban-transition loads config.json                      │
│  2. Validate transition "active → review" exists             │
│  3. Check gates (BLOCKING):                                  │
│     ├─ field_required(pr_url) → card.pr_url != null          │
│     └─ If FAIL: return GATE_VIOLATION error                  │
│  4. Check checks (ADVISORY):                                 │
│     ├─ tasks_complete → all tasks checked                    │
│     └─ If FAIL: add to warnings array                        │
│  5. Perform move (write to dest, delete from source)         │
│  6. Return success with warnings (if any)                    │
└──────────────────────────────────────────────────────────────┘
```

### Gate Validators

**Built-in validators:**

1. **field_required** (validation)
   - Check field is non-empty
   - No external dependencies

2. **tasks_complete** (validation)
   - Parse task list in card markdown
   - Count checked vs total tasks

3. **worktree_exists** (external_state)
   - Primary: Check filesystem (path exists)
   - Enhanced: Call sc-git-worktree-scan if available
   - Returns: true if worktree directory exists

4. **worktree_removed** (external_state)
   - Check filesystem (path does NOT exist)
   - Returns: true if worktree deleted

5. **branch_deleted** (external_state)
   - Requires: git
   - Check: `git ls-remote --heads origin <branch>`
   - Returns: true if branch not found

6. **pr_merged** (external_state)
   - Primary: Call `gh pr view <url> --json state`
   - Fallback: User attestation if gh not available
   - Returns: true if state == "MERGED"

### External Validation Fallbacks

**Graceful degradation:**

```python
def validate_pr_merged(pr_url):
    # Try gh CLI (preferred)
    if command_exists("gh"):
        result = run_command(f"gh pr view {pr_url} --json state")
        return result.state == "MERGED"

    # Fallback: user attestation
    response = prompt_user(
        f"Cannot verify PR status (gh CLI not found). "
        f"Has {pr_url} been merged? [y/n]"
    )
    return response.lower() == "y"
```

**Principle:** Keep gates enforced even without integrations.

### Error Responses

**Gate violation (single-agent):**
```json
{
  "success": false,
  "error": {
    "code": "GATE_VIOLATION",
    "message": "Cannot move to active: worktree not created",
    "failed_gates": [
      {
        "rule": "worktree_exists",
        "field": "worktree",
        "message": "Worktree not found: /worktrees/sprint-1.1"
      }
    ],
    "suggested_action": "Create worktree before moving to active"
  }
}
```

**Gate violation (multi-agent):**
```json
{
  "success": false,
  "error": {
    "code": "GATE_VIOLATION",
    "message": "Cannot move to done: 2 PRs not merged",
    "failed_gates": [
      {
        "rule": "field_required",
        "field": "worktrees[0].pr_url",
        "assignee": "agent/dotnet-dev",
        "message": "PR URL missing for backend worktree"
      },
      {
        "rule": "pr_merged",
        "field": "worktrees[1].pr_url",
        "assignee": "agent/react-dev",
        "pr_url": "https://github.com/org/repo/pull/125",
        "pr_status": "open",
        "message": "PR not merged: #125 (status: open)"
      }
    ],
    "suggested_action": "1) Create PR for backend, 2) Wait for PR #125 merge"
  }
}
```

**Success with warnings:**
```json
{
  "success": true,
  "data": {
    "action": "move",
    "from": "active/sprint-1.1.md",
    "to": "review/sprint-1.1.md",
    "warnings": [
      {
        "rule": "tasks_complete",
        "message": "2 tasks incomplete (documentation pending)",
        "severity": "warning"
      }
    ]
  },
  "error": null
}
```

---

## Multi-Agent Support

### Design Rationale

**Scenario:** PM deploys 3 agents to work on Sprint 2.1 (backend, frontend, QA)
- Each agent works in separate worktree
- Each agent creates separate PR
- All PRs must merge before sprint is complete

**Requirements:**
1. Track multiple worktrees per card
2. Validate ALL worktrees exist (planned → active)
3. Validate ALL PRs merged (review → done)
4. Support both single and multi-agent patterns

### Hybrid Field Support

**Gate validators handle both:**

```python
def validate_worktree_exists(card):
    # Single-agent pattern
    if "worktree" in card and card["worktree"]:
        if not check_path_exists(card["worktree"]):
            return {
                "valid": False,
                "failed_gates": [{
                    "rule": "worktree_exists",
                    "field": "worktree",
                    "message": f"Worktree not found: {card['worktree']}"
                }]
            }
        return {"valid": True}

    # Multi-agent pattern
    if "worktrees" in card and card["worktrees"]:
        failed = []
        for i, wt in enumerate(card["worktrees"]):
            if not check_path_exists(wt["path"]):
                failed.append({
                    "rule": "worktree_exists",
                    "field": f"worktrees[{i}].path",
                    "assignee": wt.get("assignee"),
                    "message": f"Worktree not found: {wt['path']}"
                })

        if failed:
            return {"valid": False, "failed_gates": failed}
        return {"valid": True}

    return {
        "valid": False,
        "failed_gates": [{
            "rule": "field_required",
            "field": "worktree or worktrees",
            "message": "No worktree information in card"
        }]
    }
```

### Strict Validation

**ALL worktrees must be created:**
- planned → active: Check every worktree path exists
- Transition fails if ANY worktree missing

**ALL PRs must be merged:**
- review → done: Check every PR URL shows merged
- Transition fails if ANY PR not merged or missing

### WIP Counting

**One card = WIP of 1, regardless of worktrees**

**Example:**
- Card A: 1 worktree (single-agent) = WIP 1
- Card B: 3 worktrees (multi-agent) = WIP 1
- WIP limit = 3 → Can have 3 cards in active (A, B, and one more)

**Rationale:** Card is unit of work from PM perspective, not individual agent assignments.

---

## Templates

### Template 1: Solo Dev (Simple 4-State)

**Use case:** Individual developer, simple workflow, no team coordination

```json
{
  "version": "1.0",
  "board": {
    "name": "Solo Dev Board",
    "columns": ["backlog", "planned", "active", "done"]
  },
  "columns": {
    "backlog": { "type": "aggregate", "file": "backlog.md", "wip": null },
    "planned": { "type": "directory", "wip": null },
    "active": { "type": "directory", "wip": null },
    "done": { "type": "aggregate", "file": "done.md", "wip": null, "scrub": [] }
  },
  "transitions": {
    "backlog → planned": { "gates": [], "checks": [] },
    "planned → active": { "gates": [], "checks": [] },
    "active → done": {
      "gates": [],
      "checks": [
        { "rule": "tasks_complete", "enforcement": "warning" }
      ]
    }
  },
  "fields": {
    "project": { "type": "string", "required": true, "transient": false },
    "phase": { "type": "string", "required": true, "transient": false },
    "sprint": { "type": "string", "required": true, "transient": false },
    "title": { "type": "string", "required": true, "transient": false }
  }
}
```

**Characteristics:**
- No gates (simple workflow)
- No WIP limits
- No worktree/PR tracking
- Minimal fields

---

### Template 2: Team Sprint (Standard 5-State)

**Use case:** Team development, worktree isolation, PR-based workflow

```json
{
  "version": "1.0",
  "board": {
    "name": "Team Sprint Board",
    "columns": ["backlog", "planned", "active", "review", "done"]
  },
  "columns": {
    "backlog": { "type": "aggregate", "file": "backlog.md", "wip": null },
    "planned": { "type": "directory", "wip": 5 },
    "active": { "type": "directory", "wip": 3 },
    "review": { "type": "directory", "wip": 3 },
    "done": {
      "type": "aggregate",
      "file": "done.md",
      "wip": null,
      "scrub": ["worktree", "worktrees", "branch", "assignee", "pr_url", "log"]
    }
  },
  "transitions": {
    "backlog → planned": { "gates": [], "checks": [] },
    "planned → active": {
      "gates": [
        { "rule": "field_required", "field": "worktree", "enforcement": "blocking" },
        { "rule": "worktree_exists", "field": "worktree", "enforcement": "blocking" }
      ],
      "checks": [
        { "rule": "field_required", "field": "assignee", "enforcement": "warning" }
      ]
    },
    "active → review": {
      "gates": [
        { "rule": "field_required", "field": "pr_url", "enforcement": "blocking" }
      ],
      "checks": [
        { "rule": "tasks_complete", "enforcement": "warning" }
      ]
    },
    "review → active": {
      "gates": [
        { "rule": "field_required", "field": "rejection_reason", "enforcement": "blocking" }
      ],
      "checks": []
    },
    "review → done": {
      "gates": [
        { "rule": "pr_merged", "field": "pr_url", "enforcement": "blocking" },
        { "rule": "worktree_removed", "field": "worktree", "enforcement": "blocking" }
      ],
      "checks": [
        { "rule": "branch_deleted", "field": "branch", "enforcement": "warning" }
      ]
    }
  },
  "fields": {
    "project": { "type": "string", "required": true, "transient": false },
    "phase": { "type": "string", "required": true, "transient": false },
    "sprint": { "type": "string", "required": true, "transient": false },
    "title": { "type": "string", "required": true, "transient": false },
    "worktree": { "type": "path", "transient": true },
    "worktrees": { "type": "array", "items": "object", "transient": true },
    "branch": { "type": "string", "transient": true },
    "pr_url": { "type": "url", "transient": true },
    "assignee": { "type": "string", "transient": true },
    "rejection_reason": { "type": "string", "transient": true }
  },
  "validation": {
    "sprint_matches_phase": true
  }
}
```

**Characteristics:**
- **Worktree gates:** Must exist before moving to active
- **PR merge gates:** Must be merged before completion
- **Worktree cleanup gates:** Must be removed before archival
- **WIP limits:** Prevent overloading columns
- **Hybrid support:** Works for both single and multi-agent sprints
- **Transient fields scrubbed** at archival

---

### Template 3: QA Pipeline (Advanced 6-State)

**Use case:** Team with dedicated QA, code-review → QA → done flow

```json
{
  "version": "1.0",
  "board": {
    "name": "QA Pipeline Board",
    "columns": ["backlog", "planned", "active", "code-review", "qa", "done"]
  },
  "columns": {
    "backlog": { "type": "aggregate", "file": "backlog.md", "wip": null },
    "planned": { "type": "directory", "wip": 5 },
    "active": { "type": "directory", "wip": 2 },
    "code-review": { "type": "directory", "wip": 3 },
    "qa": { "type": "directory", "wip": 2 },
    "done": {
      "type": "aggregate",
      "file": "done.md",
      "wip": null,
      "scrub": ["worktree", "worktrees", "branch", "assignee", "qa_assignee", "log"]
    }
  },
  "transitions": {
    "backlog → planned": { "gates": [], "checks": [] },
    "planned → active": {
      "gates": [
        { "rule": "worktree_exists", "enforcement": "blocking" }
      ]
    },
    "active → code-review": {
      "gates": [
        { "rule": "field_required", "field": "pr_url", "enforcement": "blocking" }
      ]
    },
    "code-review → qa": {
      "gates": [
        { "rule": "pr_approved", "field": "pr_url", "enforcement": "blocking" }
      ],
      "checks": [
        { "rule": "field_required", "field": "qa_assignee", "enforcement": "warning" }
      ]
    },
    "code-review → active": {
      "gates": [
        { "rule": "field_required", "field": "rejection_reason", "enforcement": "blocking" }
      ]
    },
    "qa → done": {
      "gates": [
        { "rule": "pr_merged", "field": "pr_url", "enforcement": "blocking" },
        { "rule": "worktree_removed", "enforcement": "blocking" },
        { "rule": "field_required", "field": "qa_passed", "enforcement": "blocking" }
      ]
    },
    "qa → code-review": {
      "gates": [
        { "rule": "field_required", "field": "qa_rejection_reason", "enforcement": "blocking" }
      ]
    }
  },
  "fields": {
    "project": { "type": "string", "required": true, "transient": false },
    "phase": { "type": "string", "required": true, "transient": false },
    "sprint": { "type": "string", "required": true, "transient": false },
    "title": { "type": "string", "required": true, "transient": false },
    "worktree": { "type": "path", "transient": true },
    "worktrees": { "type": "array", "items": "object", "transient": true },
    "branch": { "type": "string", "transient": true },
    "pr_url": { "type": "url", "transient": true },
    "assignee": { "type": "string", "transient": true },
    "qa_assignee": { "type": "string", "transient": true },
    "qa_passed": { "type": "boolean", "transient": true },
    "rejection_reason": { "type": "string", "transient": true },
    "qa_rejection_reason": { "type": "string", "transient": true }
  }
}
```

**Characteristics:**
- **Two review stages:** code-review and QA
- **PR approval gate:** Must be approved before QA
- **QA gate:** Must pass QA before completion
- **Bidirectional flow:** Can reject from QA back to code-review
- **Stricter WIP limits:** active=2, qa=2 (smaller batches)

---

## Query Operations

### Filter Syntax

```bash
# By column
/kanban list active
/kanban list review,done

# By project
/kanban list project:synaptic-canvas

# By phase
/kanban list phase:1
/kanban list phase:3a,3b

# By sprint
/kanban list sprint:1.2a

# Combined filters
/kanban list project:synaptic-canvas phase:1 column:active
```

### Phase Rollup

```bash
/kanban status --by-phase

Output:
synaptic-canvas Project Status

Phase 1: Foundation
  Status: In Progress (2/3 sprints complete)
  ├── ✅ Sprint 1.1: Project Setup (done)
  ├── 🔄 Sprint 1.2a: Database Schema (active, 60% complete)
  └── 🔄 Sprint 1.2b: API Contracts (active, 40% complete)

Phase 2: Core Implementation
  Status: Not Started (0/4 sprints)
  └── ⏳ Sprint 2.1: Authentication (blocked by 1.2a, 1.2b)

Phase 3a: Performance Optimization
  Status: In Progress (1/2 sprints)
  ├── 🔄 Sprint 3a.1: Caching Layer (active)
  └── ⏳ Sprint 3a.2: Query Optimization (planned)
```

### Query Response Format

```json
{
  "success": true,
  "data": {
    "cards": [
      {
        "file": "active/synaptic-canvas-1.2a.md",
        "project": "synaptic-canvas",
        "phase": "1",
        "sprint": "1.2a",
        "title": "Database Schema",
        "column": "active",
        "worktree": "/worktrees/synaptic-canvas-1-2a-database-schema",
        "assignee": "agent/dotnet-dev"
      }
    ],
    "summary": {
      "total": 1,
      "by_column": { "active": 1 },
      "by_phase": { "1": 1 },
      "by_project": { "synaptic-canvas": 1 }
    }
  }
}
```

---

## Integration Points

### sc-git-worktree (Optional Enhancement)

**Purpose:** Enhanced worktree validation

**Integration:**
```python
def validate_worktree_exists(worktree_path):
    # Try sc-git-worktree integration (if available)
    if command_exists("sc-git-worktree"):
        try:
            result = invoke_agent("sc-git-worktree-scan")
            return worktree_path in [wt["path"] for wt in result.worktrees]
        except:
            pass  # Fall through to filesystem check

    # Fallback: filesystem check
    return os.path.exists(worktree_path) and os.path.isdir(worktree_path)
```

**Benefits:**
- Richer validation (worktree status, branch info)
- Consistent with sc-git-worktree semantics

**Standalone capability:**
- Works without sc-git-worktree
- Filesystem checks sufficient for basic validation

---

### sc-github-issue (Optional Enhancement)

**Purpose:** PR status validation

**Integration:**
```python
def validate_pr_merged(pr_url):
    # Try gh CLI (preferred)
    if command_exists("gh"):
        result = run_command(f"gh pr view {pr_url} --json state")
        return result.state == "MERGED"

    # Fallback: user attestation
    response = prompt_user(
        f"Cannot verify PR status (gh CLI not found). "
        f"Has {pr_url} been merged? [y/n]"
    )
    return response.lower() == "y"
```

**Benefits:**
- Automated PR merge validation
- Supports pr_approved gate for QA pipeline

**Standalone capability:**
- User attestation fallback
- Works without gh CLI

---

### PM/Scrum Master Workflow

**Kanban's role:** Gate enforcement only

**PM/Scrum Master responsibilities:**
1. Create cards with worktree plan
2. Deploy agents to worktrees
3. Monitor agent progress
4. Ensure PRs created before moving to review
5. If kanban refuses transition: Re-deploy agents to fix

**Example flow:**
```
1. PM creates card with worktree plan
2. PM deploys agents to create worktrees
3. PM tries: planned → active
   → Kanban validates: ALL worktrees exist?
   → If no: "Gate violation: worktree not found"
   → PM fixes and retries
4. Agents work in parallel
5. PM tries: active → review
   → Kanban validates: ALL PRs present?
   → If no: "Gate violation: PR missing"
   → PM re-deploys agents to create PRs
6. PRs reviewed/merged
7. PM tries: review → done
   → Kanban validates: ALL PRs merged? Worktrees removed?
   → If no: "Gate violation: PR not merged"
   → PM waits or escalates
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

**Days 1-2: Config Templates & Schema**
- Design 3 starter templates (Solo, Team Sprint, QA Pipeline)
- Implement config.json parser with gates/checks distinction
- Validate template configs
- Create wizard Q&A flow
- Add phase/sprint validation

**Day 3: kanban-init Agent**
- Interactive Q&A wizard
- Template selection
- Board scaffold creation
- Migration option in wizard

**Day 4: kanban-migrate Agent**
- Parse markdown checklists
- Identify completed/in-progress/pending tasks
- Extract metadata (project, phase, sprint from headers)
- Create cards in appropriate columns
- Test with existing Synaptic Canvas checklists

### Phase 2: Core Operations (Week 1-2)

**Day 5: kanban-card Agent**
- Create + update operations
- Handle hybrid field support (scalar/array)
- Validate worktrees array structure
- Field validation per config

**Day 6: kanban-query Agent**
- Parse aggregate + directory columns
- Filter by project, phase, sprint, column
- Phase rollup statistics
- Board validation

### Phase 3: Transitions & Gates (Week 2)

**Days 7-8: kanban-transition Agent (Most Complex)**
- Load transition rules from config
- Distinguish gates (blocking) vs checks (warnings)
- Validate gates with enforcement levels
- WIP limit checking
- External validation (worktree, PR)
- Graceful degradation for missing tools
- Handle aggregate ↔ directory transitions
- Archive with field scrubbing (special case)
- Test all transition types and gate violations

### Phase 4: Integration & External Validation (Week 2-3)

**Day 9: Worktree Validation**
- Implement worktree_exists gate validator
- Implement worktree_removed gate validator
- Integration with sc-git-worktree (optional)
- Fallback: filesystem checks
- Test with and without sc-git-worktree

**Day 10: PR Validation**
- Implement pr_merged gate validator
- Implement pr_approved gate validator
- Integration with gh CLI (optional)
- Fallback: user attestation
- Test with and without gh CLI

**Day 11: Command & Skill**
- `/kanban` command routing
- Parse action from user intent
- SKILL.md orchestration
- User-friendly error formatting
- Phase-based query routing

### Phase 5: Testing & Documentation (Week 3)

**Days 12-13: Integration Testing**
- Test with sc-git-worktree
- Test with sc-github-issue
- Test migration from existing checklists
- Test full sprint workflow (single-agent)
- Test multi-agent sprint workflow
- Test gate enforcement
- Test phase/sprint validation
- Test all templates

**Days 14-15: Documentation**
- README with quick start and templates
- USE-CASES (3 templates + workflows)
- TROUBLESHOOTING (gate violations, config errors)
- INTEGRATION (how PM agents use kanban)
- CHANGELOG (v0.1.0 initial release)

**Day 16: Polish & Release**
- Update registry.json
- Add sc-kanban agents to registry
- Version bump marketplace to v0.7.0
- Create PR with complete package
- Marketplace publish

---

## Success Criteria

### v0.1.0 MVP Features (Must Have)

✅ **Setup & Migration:**
- Interactive init wizard with 3 starter templates
- Migration from existing checklists (completed items → done, pending → backlog)

✅ **Core Operations:**
- Create, update, query cards
- Transition between columns with gate enforcement
- Archive with field scrubbing

✅ **Phase & Sprint:**
- Phase/sprint numbering support (1, 3a, 1.1, 3a.2b)
- Phase-based queries and rollups
- Sprint validation (must match phase prefix)

✅ **Gate System:**
- Gates vs checks distinction
- Strict gate enforcement (transition fails if gates not met)
- Clear error messages with suggested actions

✅ **Multi-Agent:**
- Hybrid scalar/array field support
- Track multiple worktrees per card
- Validate ALL worktrees exist (planned → active)
- Validate ALL PRs merged (review → done)

✅ **External Validation:**
- **Worktree gates enforced** (worktree_exists, worktree_removed)
- **PR gates enforced** (pr_merged, pr_approved)
- Graceful degradation (works without sc-git-worktree or gh CLI)

✅ **WIP & Validation:**
- WIP limit enforcement (configurable: blocking/warning)
- Column type support (aggregate vs directory)
- Field scrubbing on archive

✅ **Documentation:**
- Comprehensive README (quick start, templates)
- USE-CASES (board configurations, workflows)
- TROUBLESHOOTING (common errors)
- INTEGRATION (PM agent usage patterns)

✅ **v0.4 Compliance:**
- Fenced JSON responses with standard envelope
- YAML frontmatter with version in agents
- Registry-based version validation
- 4 focused agents following single-responsibility

### Deferred to v0.2.0

⏭️ **Advanced Features:**
- Custom rule extensibility
- Performance optimization for large boards (indexing)
- Concurrent access (file locking)
- Bidirectional sync with GitHub Projects
- Sub-task status tracking
- Advanced query DSL

⏭️ **Enhancements:**
- Configurable postcondition enforcement policy
- Card templates per phase
- Automated metrics collection
- Dashboard views

---

## Validation Tests

### Critical Test Scenarios

**1. State Transition Validation:**
- ✅ Move with satisfied gates → success
- ✅ Move with failed gate → GATE_VIOLATION error with failed_gates
- ✅ Move exceeding WIP limit → WIP_EXCEEDED error
- ✅ Check failure → success with warnings

**2. Phase/Sprint Validation:**
- ✅ Valid phase formats: 1, 12, 3a, 3ab
- ✅ Valid sprint formats: 1.1, 3a.2, 3b.2a
- ✅ Sprint matches phase: 3a.2 valid for phase 3a
- ✅ Sprint mismatch: 2.1 invalid for phase 1 → error

**3. Storage Type Transitions:**
- ✅ Aggregate (backlog) → Directory (planned)
- ✅ Directory (active) → Directory (review)
- ✅ Directory (review) → Aggregate (done)

**4. Field Scrubbing:**
- ✅ Archive card with transient fields → verify scrubbed
- ✅ Archive card with permanent fields → verify retained

**5. Multi-Agent Gates:**
- ✅ Single-agent: worktree exists → validates scalar field
- ✅ Multi-agent: ALL worktrees exist → validates array (strict)
- ✅ Multi-agent: 1 PR missing → GATE_VIOLATION with details
- ✅ Multi-agent: ALL PRs merged → success

**6. External State Checks:**
- ✅ With gh CLI → pr_merged validates
- ✅ Without gh CLI → user attestation fallback
- ✅ With filesystem → worktree_exists validates
- ✅ Without sc-git-worktree → filesystem check sufficient

**7. Edge Cases:**
- ✅ Empty backlog
- ✅ Malformed config.json
- ✅ Card file missing required frontmatter
- ✅ Duplicate card IDs
- ✅ Moving to non-existent column
- ✅ Invalid phase format (3.1 instead of 3a)

---

## Package Structure

```
packages/sc-kanban/
├── manifest.yaml              # v0.1.0, marketplace metadata
├── agents/
│   ├── kanban-init.md         # Setup: wizard, migration (4-6KB)
│   ├── kanban-card.md         # CRUD: create, update (2-3KB)
│   ├── kanban-transition.md   # State: move, archive (5-7KB)
│   └── kanban-query.md        # Read: list, filter, validate (3-4KB)
├── skills/
│   └── kanban/
│       └── SKILL.md           # Orchestration layer
├── commands/
│   └── kanban.md              # /kanban command
├── templates/
│   ├── solo-dev.json          # 4-state, no gates
│   ├── team-sprint.json       # 5-state, worktree/PR gates
│   └── qa-pipeline.json       # 6-state, code-review + QA
├── docs/
│   ├── README.md              # Quick start, overview
│   ├── CHANGELOG.md           # v0.1.0 initial release
│   ├── USE-CASES.md           # Board configurations & workflows
│   ├── TROUBLESHOOTING.md     # Common issues, gate violations
│   └── INTEGRATION.md         # Using with PM/dev agents
└── tests/
    └── fixtures/               # Test board configurations
```

---

## Dependencies

### Required
- None (works standalone)

### Optional (Enhanced Features)
- **sc-git-worktree** (v0.6.0+): Enhanced worktree validation
- **gh CLI**: PR status validation
- **sc-github-issue** (v0.6.0+): PR approval checks

### Graceful Degradation
- Works without integrations
- Filesystem checks for worktree validation
- User attestation for PR validation

---

## Version & Changelog

**v0.1.0** (Initial Release)
- Initial kanban state machine implementation
- 4 agents: init, card, transition, query
- 3 starter templates: Solo Dev, Team Sprint, QA Pipeline
- Phase/sprint numbering system
- Gates vs checks distinction
- Multi-agent support (hybrid scalar/array fields)
- External validation with fallbacks
- Checklist migration
- v0.4 architecture compliant

**Future (v0.2.0+)**
- Custom rule extensibility
- Performance optimization for large boards
- Advanced query DSL
- Dashboard views
- Sub-task status tracking

---

## References

- **v0.4 Guidelines:** `/docs/claude-code-skills-agents-guidelines-0.4.md`
- **sc-project-manager Design:** `/plans/sc-project-manager-design.md` (phase/sprint grammar)
- **Backlog:** `/pm/plans/2025-12-04-ongoing-maintenance-backlog.md` (section 4.4)
- **sc-ci-automation:** `packages/sc-ci-automation/` (v0.4 reference example)
- **sc-git-worktree:** `packages/sc-git-worktree/` (integration reference)

---

**Document Status:** ✅ Design Complete - Ready for Implementation
**Next Step:** Create package structure and begin Phase 1 implementation
**Estimated Timeline:** 3 weeks (16 days)
**Target Release:** Marketplace v0.7.0
