---
name: codex-agent
description: Run Codex tasks via the ai_cli Task Tool runner.
version: 0.14.0
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

Use `sc_codex_task.py` only (do not call other runner script names).
Do not invent flags like `--run_in_background`, `--description`, `--prompt`, or `--subagent_type`.

## Input

Provide Task Tool input JSON with:
- `description`
- `prompt`
- `subagent_type` (defaults to `sc-codex` if not provided by the caller)
- `model` (optional; alias or full id)
- `reasoning_effort` (optional; low, medium, high, xhigh, max, ultra)
- `run_in_background` (optional; defaults to true for `sc_codex_task.py`)

## Models and effort

The model/effort table (aliases, ids, supported efforts, defaults) lives in the sc-codex
[README](../../README.md#models-and-reasoning-effort). Default model: `sol`.

- Map requests to JSON fields (or flags): "use sc-codex with sol low" means
  `"model":"sol","reasoning_effort":"low"` (`--model sol --effort low`); "luna high" means
  `"model":"luna","reasoning_effort":"high"`.
- `low`, `medium`, `high`, `xhigh`, `max`, `ultra` are always effort levels, never models. A bare
  level ("sc-codex high") means the default model with that effort.
- Omit `reasoning_effort` when the user did not ask for one; the Codex CLI config then applies.
- `--model` / `--effort` flags given alongside `--json` override payload fields.
- Unknown models and unsupported efforts are rejected before launch with the valid choices.

## Notes

- Background mode:
  - Default is background unless `--no-background` is provided (or the JSON sets `"run_in_background": false`).
  - Add `--background` to force background explicitly.
  - Add `--no-background` to force blocking mode.
  - The JSON output includes `output_file` (JSONL transcript path) and `agentId`.
  - Poll `output_file` via a short Python loop (avoid `tail -f` and avoid `timeout`, which may be missing on macOS).
- Blocking mode (`--no-background` or `"run_in_background": false`) returns `{ "output", "agentId" }`.
- The runner enforces schema validation and logs to `.claude/state/logs/<package-name>/`.
- If the run fails, surface the error; do not retry with a different model.
- If `resume` is provided but the prior transcript cannot be reopened or does not contain usable assistant output, return a concise error instead of inventing missing context.
