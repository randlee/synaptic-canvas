---
name: sc-refactor-plan
version: 0.1.0
description: Prepare or execute a rule-backed refactor plan using the named teammates.
---

# /sc-refactor-plan

User-facing entrypoint for plan-driven execution.

This command is backed by the named teammates:

- `refactor-orchestrator`
- `quality-manager`

Policy:

- every plan item must be backed by approved `.refactor/` rules
- dev waves make only authorized changes
- QA waves verify 100% compliance
- only QA-approved waves are committable
