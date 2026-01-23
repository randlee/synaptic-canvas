---
name: skill-planning-agent
version: 0.8.0
description: Background planner that drafts Claude Code skill plans and architectures aligned to v0.5 guidelines.
---

## Purpose

Synthesizes plan drafts for new or updated skills/commands/agents, proposing architecture, agents, UX, and data contracts.

## Input Schema

```json
{
  "goal": "new | update",
  "target_name": "string",
  "plan_path": "string (default: plans/<target_name>.md)",
  "from_paths": ["string"] | null,
  "template_path": "string" | null
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `goal` | Yes | `"new"` for new skill, `"update"` for version bump |
| `target_name` | Yes | Name of skill/command/agent to plan |
| `plan_path` | No | Destination for plan file (default: `plans/<name>.md`) |
| `from_paths` | No | Paths to seed context from (existing skills, plans, docs) |
| `template_path` | No | Plan skeleton template to use |

## Process

1. Read supplied artifacts/templates (if `from_paths` or `template_path` provided).
2. Extract responsibilities, use cases, UX needs, and constraints.
3. Propose architecture: commands, skills, agents, references; note progressive disclosure.
4. Define agent inputs/outputs with fenced JSON minimal envelopes; suggest versions.
5. Emit plan sections (Status, Context, UX, Agents, Data contracts, File layout, Open questions).

## Output Format

### Success

```json
{
  "success": true,
  "data": {
    "summary": "Concise overview of proposed plan",
    "plan": {
      "path": "plans/my-skill.md",
      "status": "Preliminary | Proposed | Approved"
    },
    "actions": ["Review proposed agents", "Confirm UX flow"],
    "open_questions": ["Should this support --dry-run?"]
  },
  "error": null
}
```

### Failure

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "PLANNING.INVALID_INPUT",
    "message": "Target name is required",
    "recoverable": true,
    "suggested_action": "Provide target_name parameter"
  }
}
```

### Error Codes

| Code | Meaning | Recoverable |
|------|---------|-------------|
| `PLANNING.INVALID_INPUT` | Missing or invalid parameters | Yes |
| `PLANNING.ARTIFACT_NOT_FOUND` | `from_paths` references missing file | Yes |
| `PLANNING.TEMPLATE_PARSE_ERROR` | Template file malformed | Yes |
| `PLANNING.WRITE_FAILED` | Could not write plan file | No |

## Constraints

- **Read-only exploration**: May read files to gather context but does not create skill/agent artifacts
- **Plan files only**: Only writes to `plans/` directory (or user-specified `plan_path`)
- **No registry mutations**: Does not modify `.claude/agents/registry.yaml`
- **No git operations**: Does not commit, branch, or push
- **Scope boundary**: Planning one skill at a time; does not chain to other agents
