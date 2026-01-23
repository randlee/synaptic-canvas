---
name: skill-review
version: 0.8.0
description: Review a skill/command/agent against v0.5 guidelines using the skill-reviewing skill and its three specialized agents.
options:
  - name: --scope
    description: Scope of review: command|skill|agent|all (default: all).
  - name: --fix
    description: Propose fixes and updated snippets where safe (no writes).
  - name: --include-agents
    description: When reviewing a skill, also review all agents it references.
  - name: --help
    description: Show usage.
---

# /skill-review command

Purpose: Validate artifacts with minimal command logic. Delegate to the `skill-reviewing` skill which orchestrates three specialized review agents.

## Behavior
- Accept target as positional name/path. Resolve relative paths; if name is given, prefer registry paths when present.
- Invoke the `skill-reviewing` skill with collected parameters.
- The skill runs three agents in parallel:
  - `skill-metadata-storage-review` — Frontmatter & storage conventions
  - `skill-implementation-review` — Code mechanics & security
  - `skill-architecture-review` — Design patterns & structure
- Aggregated results are presented to the user with severity levels (error/warn/info).
- Keep command thin; the skill handles orchestration and reporting.
