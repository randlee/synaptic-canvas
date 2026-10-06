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
- `model` (optional; alias or slug, see below)
- `reasoning_effort` (optional; see below)
- `run_in_background` (optional; defaults to true for `sc_codex_task.py`)

## Models and effort

| Alias | Model slug | Supported `--effort` levels |
|-------|------------|-----------------------------|
| `sol` | `gpt-6-sol` | low, medium, high, xhigh, max, ultra |
| `astra` (default; also `codex`) | `gpt-6-astra` | low, medium, high, xhigh, max, ultra |
| `luna` | `gpt-6-luna` | low, medium, high, xhigh, max |
| — | `gpt-5.6-sol` | low, medium, high, xhigh, max, ultra |
| `terra` | `gpt-5.6-terra` | low, medium, high, xhigh, max, ultra |
| — | `gpt-5.6-luna` | low, medium, high, xhigh, max |
| — | `gpt-5.5` | low, medium, high, xhigh |

`minimal` effort is not supported: no current model accepts it (all start at `low`), so it is rejected.

- Default model (no `model`, or `codex`): `gpt-6-astra`.
- Full slugs are accepted as-is. Unknown models (including the removed legacy aliases
  `gpt-5.2-codex`, `codex-max`/`max`, `codex-mini`/`mini`, `gpt-5`, `gpt-5.2`, `gtp-5`) are rejected.
- When `reasoning_effort` / `--effort` is omitted, no override is passed and the user's
  `~/.codex/config.toml` applies. Unsupported model/effort combinations are rejected before launch.
- Map natural-language requests to flags or JSON fields: "use sc-codex with sol low" means
  `--model sol --effort low` (or `"model":"sol","reasoning_effort":"low"` in the JSON payload);
  "luna high" means `--model luna --effort high`.
- Disambiguation: `low`, `medium`, `high`, `xhigh`, `max`, `ultra` are always effort levels, never
  models. `max` was a model alias before 0.14.0 and no longer is ("codex max" means
  `--effort max` on the default model). A bare level with no model (e.g. "sc-codex high") means the
  default model (`gpt-6-astra`) with that effort.
- `--model` / `--effort` flags given alongside `--json` override payload fields.

## Notes

- Background mode:
  - Default is background unless `--no-background` is provided (or the JSON sets `"run_in_background": false`).
  - Add `--background` to force background explicitly.
  - Add `--no-background` to force blocking mode.
  - The JSON output includes `output_file` (JSONL transcript path) and `agentId`.
  - Poll `output_file` via a short Python loop (avoid `tail -f` and avoid `timeout`, which may be missing on macOS).
- Blocking mode (`--no-background` or `"run_in_background": false`) returns `{ "output", "agentId" }`.
- The runner enforces schema validation and logs to `.claude/state/logs/<package-name>/`.
- If Codex rejects the model for a ChatGPT-account login, the runner retries once on `gpt-5.5`
  automatically (effort clamped to at most `xhigh`); do not retry manually.
- If `resume` is provided but the prior transcript cannot be reopened or does not contain usable assistant output, return a concise error instead of inventing missing context.
