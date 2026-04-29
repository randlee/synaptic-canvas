---
name: sc-refactor-lookup
version: 0.1.0
description: Look up whether a trigger maps to an approved refactor rule before editing.
options:
  - name: --signal
    args:
      - name: value
        description: Trigger value such as a type, namespace, assembly, file, or error code.
    description: Required trigger value to look up.
  - name: --kind
    args:
      - name: type
        description: "Optional kind: type, namespace, assembly, string, or error."
    description: Optional trigger kind.
---

# /sc-refactor-lookup

Thin entrypoint for the `refactor-lookup` skill.

Use before editing when a known trigger appears in build errors, CI output,
source files, or project files.
