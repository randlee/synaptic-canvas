---
name: skill-create
version: 0.8.0
description: Generate command/skill/agent/reference stubs from an approved plan.
options:
  - name: --help
    description: Show usage.
---

# /skill-create command

Purpose: Accept an approved plan path and delegate stub generation to the skill-creation skill and agents. Keep logic thin.

## Behavior
- Positional arg: `<plan-path>` (required) pointing to an approved plan (e.g., `plans/<name>.md`).
- Validate path exists and plan status is Approved; otherwise prompt to approve or re-run planning.
- Delegate to the creation flow in `skill-creation` skill to generate stubs at version 0.1.0 following the naming convention (frontmatter name without slash; user invocation adds slash).
- Use `.claude/.prompts/` for transient scratch if needed.
