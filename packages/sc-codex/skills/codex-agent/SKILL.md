---
name: codex-agent
description: Run Codex tasks via the ai_cli Task Tool runner.
version: 0.7.0
---

# Codex Agent

Use this skill to run Codex tasks via the ai_cli runner. This is intended for Claude
to delegate work to Codex when appropriate.

## Invocation

Call the runner script:

```bash
python3 scripts/sc_codex_task.py --json '{...}'
```

## Input

Provide Task Tool input JSON with:
- `description`
- `prompt`
- `subagent_type` (defaults to `sc-codex` if not provided by the caller)

## Notes

- The runner enforces schema validation and logs to `.claude/state/logs/ai-cli/`.
