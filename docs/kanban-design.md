# Kanban System Design

A configurable state machine for task card management. Provides validated state storage with no opinions on consumption or workflow orchestration.

## Overview

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Card CRUD | Who calls it |
| Schema validation | Why they call it |
| State transitions | Workflow orchestration |
| WIP enforcement | Agent coordination |
| Board queries | Dependency resolution |

### Design Principles

- **Pure state machine**: Kanban agents manage state, not workflow
- **Configuration-driven**: Board structure defined per-repo, not hardcoded
- **Consumer-agnostic**: Works with any PM/dev agent system
- **JSON interface**: Agents accept/return fenced JSON blocks

---

## File Structure

```
.kanban/
├── config.json         # Board configuration, columns, rules, transitions
├── backlog.md          # Aggregate file for backlog cards
├── done.md             # Aggregate file for archived cards (scrubbed)
├── planned/            # Directory for planned cards
├── active/             # Directory for in-progress cards
└── review/             # Directory for cards awaiting acceptance
```

---

## Configuration

### `config.json`

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
      "wip": 5
    },
    "active": {
      "type": "directory",
      "wip": 3
    },
    "review": {
      "type": "directory",
      "wip": 3
    },
    "done": {
      "type": "aggregate",
      "file": "done.md",
      "wip": null,
      "scrub": ["worktree", "branch", "assignee", "log"]
    }
  },
  "transitions": {
    "backlog → planned": {
      "preconditions": [],
      "postconditions": []
    },
    "planned → active": {
      "preconditions": [
        { "rule": "field_required", "field": "worktree" },
        { "rule": "field_required", "field": "branch" }
      ],
      "postconditions": [
        { "rule": "worktree_exists", "field": "worktree" }
      ]
    },
    "active → review": {
      "preconditions": [
        { "rule": "field_required", "field": "pr_url" },
        { "rule": "tasks_complete" }
      ],
      "postconditions": []
    },
    "review → active": {
      "preconditions": [
        { "rule": "field_required", "field": "rejection_reason" }
      ],
      "postconditions": []
    },
    "review → done": {
      "preconditions": [
        { "rule": "pr_merged", "field": "pr_url" }
      ],
      "postconditions": [
        { "rule": "worktree_removed", "field": "worktree" },
        { "rule": "branch_deleted", "field": "branch" }
      ]
    }
  },
  "rules": {
    "field_required": {
      "description": "Field must be non-empty"
    },
    "tasks_complete": {
      "description": "All tasks in card marked complete"
    },
    "worktree_exists": {
      "description": "Worktree path exists on filesystem"
    },
    "worktree_removed": {
      "description": "Worktree has been deleted"
    },
    "branch_deleted": {
      "description": "Branch no longer exists in remote"
    },
    "pr_merged": {
      "description": "PR at URL shows merged status"
    }
  },
  "fields": {
    "worktree": { "type": "path", "transient": true },
    "branch": { "type": "string", "transient": true },
    "pr_url": { "type": "url", "transient": true },
    "assignee": { "type": "string", "transient": true },
    "rejection_reason": { "type": "string", "transient": true },
    "project": { "type": "string", "transient": false },
    "sprint": { "type": "string", "transient": false },
    "title": { "type": "string", "transient": false }
  }
}
```

### Column Types

| Type | Storage | Use Case |
|------|---------|----------|
| `aggregate` | Single file, cards as sections | High-volume, low-churn (backlog, done) |
| `directory` | File per card | Active work, frequent updates |

### Rule Categories

| Category | Validates | Examples |
|----------|-----------|----------|
| `field_required` | Card data | worktree, branch, pr_url |
| `tasks_complete` | Card state | All checkboxes marked |
| `external_state` | Filesystem/API | worktree_exists, pr_merged |

### Transient Fields

Fields marked `transient: true` are scrubbed when archiving to `done`.

---

## Alternative Board Configurations

### Simple 4-State (No Review)

```json
{
  "columns": ["backlog", "planned", "active", "done"],
  "transitions": {
    "backlog → planned": {},
    "planned → active": {},
    "active → done": {
      "preconditions": [{ "rule": "tasks_complete" }]
    }
  }
}
```

### 6-State (With QA)

```json
{
  "columns": ["backlog", "planned", "active", "code-review", "qa", "done"],
  "transitions": {
    "active → code-review": {
      "preconditions": [{ "rule": "field_required", "field": "pr_url" }]
    },
    "code-review → qa": {
      "preconditions": [{ "rule": "pr_approved" }]
    },
    "qa → done": {
      "preconditions": [{ "rule": "qa_passed" }]
    }
  }
}
```

---

## Card Formats

### Card in Directory Column (`planned/`, `active/`, `review/`)

Filename: `{project}-{sprint}.md`

```markdown
---
project: synaptic-canvas
sprint: "1.1"
title: Skill Registry
status: active
created: 2024-12-10
worktree: /worktrees/synaptic-canvas-sprint-1.1
branch: feature/skill-registry
assignee: agent/dotnet-dev
pr_url: null
---

# synaptic-canvas / Sprint 1.1: Skill Registry

## Tasks

| ID    | Title                        | Status      |
|-------|------------------------------|-------------|
| 1.1.1 | Define skill manifest schema | in-progress |
| 1.1.2 | Implement discovery endpoint | blocked     |

## Task Details

### 1.1.1: Define skill manifest schema

**Acceptance Criteria**
- [ ] JSON schema defined
- [ ] Validation tests passing
- [ ] Documentation updated

**Context**
Reference existing skill format in `/docs/skills.md`.

---

### 1.1.2: Implement discovery endpoint

**Acceptance Criteria**
- [ ] GET /skills returns registered skills
- [ ] Filtering by category

**Blockers**
- Waiting on 1.1.1 completion

---

## Log

| Timestamp           | Actor            | Action                          |
|---------------------|------------------|---------------------------------|
| 2024-12-10 14:30    | pm               | Promoted from planned           |
| 2024-12-10 14:32    | pm               | Assigned worktree + agents      |
| 2024-12-10 15:00    | agent/dotnet-dev | Started 1.1.1                   |
```

### Card in Aggregate Column (`backlog.md`)

```markdown
# Backlog

## synaptic-canvas

### Phase 1: Core Platform

#### Sprint 1.1: Skill Registry
- [ ] 1.1.1: Define skill manifest schema
  - priority: high
  - estimate: 2h
- [ ] 1.1.2: Implement discovery endpoint

#### Sprint 1.2: Agent Marketplace
- [ ] 1.2.1: Design agent packaging format

---

## teams-bot

### Phase 1: MVP

#### Sprint 1.1: Auth Flow
- [ ] 1.1.1: Azure AD integration
```

### Archived Card (`done.md`)

Transient fields scrubbed. Collapsed for reference.

```markdown
# Completed Work

## 2024-12

### synaptic-canvas / Sprint 0.1: Proof of Concept ✓

| Field      | Value            |
|------------|------------------|
| Completed  | 2024-12-08       |
| Duration   | 3 sessions       |
| Tasks      | 4/4              |

<details>
<summary>Tasks</summary>

| ID    | Title                    | Completed  |
|-------|--------------------------|------------|
| 0.1.1 | Initial prototype        | 2024-12-07 |
| 0.1.2 | Basic skill loading      | 2024-12-08 |

</details>

---
```

---

## Agents

### Agent Responsibilities

| Agent | Role |
|-------|------|
| **kanban-update** | Single writer. Validates transitions, updates cards, moves between columns |
| **kanban-query** | Read-only. Parses board state, answers questions |

### Commands

| Command   | Agent | Description |
|-----------|-------|-------------|
| init      | update | Initialize board scaffold |
| create    | update | Create new card |
| update    | update | Update card fields |
| move      | update | Move card between columns |
| archive   | update | Move to done with scrubbing |
| validate  | query | Check card/board schema compliance |
| query     | query | Search and filter cards |

---

## Agent Interface

All commands accept and return fenced JSON blocks.

### init

**Input**
```json
{
  "action": "init"
}
```

**Output**
```json
{
  "status": "ok",
  "created": [
    ".kanban/config.json",
    ".kanban/backlog.md",
    ".kanban/done.md",
    ".kanban/planned/",
    ".kanban/active/",
    ".kanban/review/"
  ]
}
```

### create

**Input**
```json
{
  "action": "create",
  "project": "synaptic-canvas",
  "sprint": "1.1",
  "title": "Skill Registry",
  "tasks": [
    { "id": "1.1.1", "title": "Define manifest schema" },
    { "id": "1.1.2", "title": "Implement endpoint" }
  ]
}
```

**Output**
```json
{
  "status": "ok",
  "file": "planned/synaptic-canvas-1.1.md"
}
```

### update

**Input**
```json
{
  "action": "update",
  "file": "active/synaptic-canvas-1.1.md",
  "fields": {
    "pr_url": "https://github.com/org/repo/pull/123"
  }
}
```

**Output**
```json
{
  "status": "ok",
  "file": "active/synaptic-canvas-1.1.md",
  "updated": ["pr_url"]
}
```

### move

**Input**
```json
{
  "action": "move",
  "file": "planned/synaptic-canvas-1.1.md",
  "to": "active"
}
```

**Output (success)**
```json
{
  "status": "ok",
  "action": "move",
  "from": "planned/synaptic-canvas-1.1.md",
  "to": "active/synaptic-canvas-1.1.md"
}
```

**Output (error)**
```json
{
  "status": "error",
  "code": "WIP_EXCEEDED",
  "message": "active column at limit (3)"
}
```

**Output (precondition failed)**
```json
{
  "status": "error",
  "code": "PRECONDITION_FAILED",
  "transition": "active → review",
  "failed_rules": [
    { "rule": "field_required", "field": "pr_url", "message": "pr_url is required" }
  ]
}
```

### archive

**Input**
```json
{
  "action": "archive",
  "file": "review/synaptic-canvas-1.1.md"
}
```

**Output**
```json
{
  "status": "ok",
  "action": "archive",
  "from": "review/synaptic-canvas-1.1.md",
  "to": "done.md",
  "scrubbed": ["worktree", "branch", "assignee", "log"]
}
```

**Output (with warnings)**
```json
{
  "status": "ok",
  "action": "archive",
  "from": "review/synaptic-canvas-1.1.md",
  "to": "done.md",
  "warnings": [
    { "rule": "worktree_removed", "field": "worktree", "message": "worktree still exists: /worktrees/foo" }
  ]
}
```

### validate

**Input**
```json
{
  "action": "validate",
  "file": "active/synaptic-canvas-1.1.md"
}
```

**Output**
```json
{
  "status": "ok",
  "valid": true
}
```

**Output (invalid)**
```json
{
  "status": "ok",
  "valid": false,
  "errors": [
    { "field": "project", "message": "required field missing" }
  ]
}
```

### query

**Input**
```json
{
  "action": "query",
  "filter": { "project": "synaptic-canvas" }
}
```

**Output**
```json
{
  "status": "ok",
  "cards": [
    { "file": "active/synaptic-canvas-1.1.md", "column": "active", "sprint": "1.1", "title": "Skill Registry" },
    { "file": "backlog.md#synaptic-canvas-1.2", "column": "backlog", "sprint": "1.2", "title": "Agent Marketplace" }
  ]
}
```

**Filter options**
```json
{
  "action": "query",
  "filter": {
    "project": "synaptic-canvas",
    "column": "active",
    "has_field": "pr_url",
    "missing_field": "assignee"
  }
}
```

---

## Validation Flow

```
┌─────────────────────────────────────────────────────────────┐
│  move { file: "active/foo.md", to: "review" }               │
├─────────────────────────────────────────────────────────────┤
│  1. Load config.json                                        │
│  2. Validate transition "active → review" exists            │
│  3. Check preconditions:                                    │
│     ├─ field_required(pr_url) → card.pr_url != null         │
│     └─ tasks_complete → all tasks checked                   │
│  4. If pass: move file, return success                      │
│  5. If fail: return error with failed rules                 │
│  6. After move: check postconditions (advisory/log)         │
└─────────────────────────────────────────────────────────────┘
```

---

## State Transition Protocol

To guarantee **write-before-read** ordering on moves:

```
┌─────────────────────────────────────────────────────────┐
│  MOVE: planned/sprint-1.1.md → active/sprint-1.1.md     │
├─────────────────────────────────────────────────────────┤
│  1. Kanban agent WRITES to active/sprint-1.1.md         │
│  2. Kanban agent DELETES planned/sprint-1.1.md          │
│  3. Consumers may now READ active/sprint-1.1.md         │
└─────────────────────────────────────────────────────────┘
```

If a crash occurs between steps 1 and 2, the document exists in **both** locations. Recovery: source is stale, destination is canonical.

---

## Skill Document

Minimal document for deploying and managing Kanban agents.

```markdown
# Kanban Skill

State management for task cards.

## Agents

- `kanban-update`: Write operations (create, update, move, archive)
- `kanban-query`: Read operations (list, filter, validate)

## Commands

| Command   | Input                              | Output                |
|-----------|------------------------------------|-----------------------|
| init      | `{ "action": "init" }`             | Board scaffold        |
| create    | `{ "action": "create", ... }`      | Card file path        |
| update    | `{ "action": "update", ... }`      | Updated card          |
| move      | `{ "action": "move", ... }`        | New file path         |
| archive   | `{ "action": "archive", ... }`     | Scrubbed to done.md   |
| validate  | `{ "action": "validate", ... }`    | Validation result     |
| query     | `{ "action": "query", ... }`       | Matching cards        |

## Configuration

See `config.json` in board root for column definitions, WIP limits, and transition rules.
```

---

## Migration Checklist

- [ ] Create `.kanban/config.json` with board configuration
- [ ] Create `.kanban/backlog.md` from existing checklist
- [ ] Create empty `.kanban/done.md`
- [ ] Create empty directories: `planned/`, `active/`, `review/`
- [ ] Implement `kanban-update` agent
- [ ] Implement `kanban-query` agent
- [ ] Test transition validations
- [ ] Test scrub rules for archival
