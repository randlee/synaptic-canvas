---
name: codex-agent
description: Run Codex tasks via the ai_cli Task Tool runner.
version: 0.7.0
---

# Codex Agent

Use this skill to run Codex tasks via the ai_cli runner. This is intended for Claude
to delegate work to Codex when appropriate, including long-running background tasks
that can be monitored while other work continues.

## Invocation

Call the runner script (installed path in projects is `.claude/scripts`):

```bash
python3 .claude/scripts/sc_codex_task.py --json '{...}'
```

## Input

Provide Task Tool input JSON with:
- `description`
- `prompt`
- `subagent_type` (defaults to `sc-codex` if not provided by the caller)

## Notes

- Model flags (aliases and full names are accepted):
  - `--model codex` (default: gpt-5.2-codex)
  - `--model codex-max` or `--model max` (maps to gpt-5.1-codex-max)
  - `--model codex-mini` or `--model mini` (maps to gpt-5.1-codex-mini)
  - `--model gpt-5` (maps to gpt-5.2)
- Background mode:
  - Default is background unless `--no-background` is provided.
  - Add `--background` to force background explicitly.
  - Add `--no-background` to force blocking mode.
  - The JSON output includes `output_file` (JSONL transcript path) and `agentId`.
  - Use `tail -f <output_file>` to monitor progress, then read the final output.
- Blocking mode (default without `--background`) returns `{ "output", "agentId" }`.
- The runner enforces schema validation and logs to `.claude/state/logs/<package-name>/`.
