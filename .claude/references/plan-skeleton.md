# Skill Plan Skeleton (v0.4-aligned)

## Status
- Preliminary | Proposed | Approved

## Context & Goals
- Purpose: 
- Scope (new skill vs update/version bump): 
- Success criteria:

## Use Cases
- Primary scenarios:
- Variants/edge cases:

## Command UX
- Slash commands and options (`--help` required):
- Defaults (e.g., plan name, paths):
- Inputs/outputs expectations:

## Agents
- Planned agents (name, version placeholder, purpose):
- Registry entries needed:
- Agent contracts (inputs/outputs, fenced JSON envelope):

## Data Contracts
- Minimal envelope example:
```json
{ "success": true, "data": { "summary": "", "actions": [] }, "error": null }
```
- Schema notes:

## File Layout
- Commands: `.claude/commands/...`
- Skills: `.claude/skills/<name>/SKILL.md`
- Agents: `.claude/agents/...`
- References/templates: `.claude/references/...`
- Plans: `plans/<name>.md`
- Reports: `reports/skill-reviews/...` (fallback: `.tmp/skill-reviews/`)

## Progressive Disclosure
- What stays in SKILL.md:
- What moves to references:

## Safety & Validation
- Versioning/registry requirements:
- Fenced JSON outputs:
- Destructive actions require confirmation?

## Open Questions
- 

## Next Actions
- 
