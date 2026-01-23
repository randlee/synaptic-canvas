---
name: skill-plan
version: 0.8.0
description: Start or resume a Claude Code skill plan using the planning wizard and agents while enforcing v0.5 guidelines.
options:
  - name: --name
    description: Plan name (default: inferred from target skill or folder).
  - name: --from
    description: Seed the plan from an existing skill/command/agent path or existing plan file.
  - name: --template
    description: Optional plan template file to pre-fill sections (overrides default skeleton).
  - name: --help
    description: Show usage.
---

# /skill-plan command

Purpose: Collect minimal inputs and launch the skill planner. Keep logic thin—delegate to the `skill-creation` skill and `skill-planning-agent`.

## Behavior
- If a path argument is provided and exists, open/resume that plan; otherwise prompt for destination (`plans/<name>.md` by default).
- Do not create artifacts during planning; only write/update a plan file (Preliminary → Proposed → Approved).
- If `--from` is provided, read the referenced file(s) to seed context (skill/command/agent or plan) before handing off.
- If `--template` is provided, load it as the initial plan skeleton; otherwise use the default sections in the skill.
- Always show concise `--help` output when requested.
- Do not embed business logic; just validate inputs and invoke the skill with gathered parameters.

## Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| Plan not found | Path argument doesn't exist | Create new plan or check path |
| Invalid template | `--template` file malformed | Fix template YAML/markdown structure |
| Artifact not found | `--from` references missing file | Verify path exists |
| Agent failure | Planning agent returned error | Check agent error message, retry |
