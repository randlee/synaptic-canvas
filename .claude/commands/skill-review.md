---
name: skill-review
version: 0.7.0
description: Review a skill/command/agent (by name or path) against v0.4 guidelines using review agents.
options:
  - name: --scope
    description: Scope of review: command|skill|agent|all (default: all).
  - name: --fix
    description: Propose fixes and updated snippets where safe (no writes).
  - name: --help
    description: Show usage.
---

# /skill-review command

Purpose: Validate artifacts with minimal command logic. Delegate to the `skill-creation` skill and `skill-review-agent`.

## Behavior
- Accept target as positional name/path. Resolve relative paths; if name is given, prefer registry paths when present.
- Prompt for where to write the review report (default suggestion: `.claude/reports/skill-reviews/<name>-report.md`; fall back to `.claude/.tmp/skill-reviews/`).
- Ensure the report directory exists (create if missing) before writing.
- Invoke the review flow with scope and `--fix` preference; render concise results for the user.
- Keep command thin; avoid performing the review inline.
