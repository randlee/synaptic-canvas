# sc-codex

Run Codex agents via a Task Tool-compatible runner with hook emulation and
background execution support. Provides a CLI wrapper plus JSON schemas for
input/output validation.

## Badges
- Status: pre-release (see `manifest.yaml` for the current version)
- Safety: hook commands are explicit and logged

## Installation
```bash
/marketplace install sc-codex --local
```

## Quick Start
```bash
# Run a prompt (background by default; prints agentId + output_file)
python3 packages/sc-codex/scripts/sc_codex_task.py "write a haiku about rain"

# Pick model and reasoning effort, blocking mode
python3 packages/sc-codex/scripts/sc_codex_task.py --model sol --effort low --no-background \
  "write a haiku about rain"

# Task Tool JSON input
python3 packages/sc-codex/scripts/sc_codex_task.py --json \
  '{"description":"Compose haiku","prompt":"compose a haiku","model":"luna","reasoning_effort":"medium"}'

# Use ai_cli directly (blocking by default)
PYTHONPATH=packages/sc-codex/scripts python3 -m ai_cli run --runner codex --file /path/to/input.json
```

## Models and reasoning effort

This is the one model/effort table for sc-codex; the other docs link here. It mirrors
`scripts/ai_cli/agent_models.py` (a synced copy of the shared
`packages/shared/scripts/agent_models.py`), and `tests/test_ai_cli_task_runner.py` fails if
the two differ.

| Tool | Model id | Aliases | Supported efforts | Model's default effort | Default model |
|------|----------|---------|-------------------|------------------------|---------------|
| codex | `gpt-6.1-sol` | `sol`, `codex` | low, medium, high, xhigh, max, ultra | low | yes |
| codex | `gpt-6-astra` | `astra` | low, medium, high, xhigh, max, ultra | medium | |
| codex | `gpt-6-sol` | - | low, medium, high, xhigh, max, ultra | medium | |
| codex | `gpt-6-luna` | `luna` | low, medium, high, xhigh, max | medium | |
| codex | `gpt-5.6-sol` | - | low, medium, high, xhigh, max, ultra | low | |
| codex | `gpt-5.6-terra` | `terra` | low, medium, high, xhigh, max, ultra | medium | |
| codex | `gpt-5.6-luna` | - | low, medium, high, xhigh, max | medium | |
| claude | `claude-fable-5-1` | `fable` | low, medium, high, xhigh, max | CLI default | yes |
| claude | `claude-opus-5-5` | `opus` | low, medium, high, xhigh, max | CLI default | |
| claude | `claude-sonnet-5-5` | `sonnet` | low, medium, high, xhigh, max | CLI default | |
| claude | `claude-haiku-5-5` | `haiku` | low, medium, high, xhigh, max | CLI default | |

- Model: `--model` or JSON `model`, as an alias or a full id. Defaults: `sol` (`gpt-6.1-sol`)
  for Codex, `fable` (`claude-fable-5-1`) for the Claude runner of `ai_cli run`. The resolved
  full id is written back into the payload, so background runs and logs show what ran.
- Effort: `--effort` or JSON `reasoning_effort`. Passed as `-c model_reasoning_effort=<level>`
  to Codex and `--effort <level>` to Claude. When omitted, no flag is passed and the CLI's own
  configuration applies (for Codex, `~/.codex/config.toml`), which is the "Model's default
  effort" above unless you configured otherwise.
- Command-line flags override the JSON payload.
- An unknown model, or an effort the model does not support, fails before anything launches,
  with a message listing the valid choices.
- `low`, `medium`, `high`, `xhigh`, `max`, `ultra` are always effort levels, never models.
  A request like "sc-codex with sol low" means `--model sol --effort low`; a bare level
  ("sc-codex high") means the default model with that effort.

## Schemas
- Input schema: `packages/sc-codex/schemas/task_tool.schema.json`
- Output schema: `packages/sc-codex/schemas/task_tool.output.schema.json`

## Logs
Runtime and hook events are written to:
- `.claude/state/logs/sc-codex/`

## Security
- Hook commands are executed as configured in agent frontmatter; review them before running.
- JSON schemas should be treated as untrusted input validation aids, not execution controls.
- Background outputs are written to `.sc/sessions` or `$CODEX_HOME/sessions`; avoid storing secrets there.
- The launched `codex`/`claude` process inherits the caller's environment except `ATM_IDENTITY`, which is dropped so the child never takes on the caller's ATM identity. `ATM_TEAM` is kept.

## Changelog
See `CHANGELOG.md`.

## License
MIT, see `LICENSE`.
