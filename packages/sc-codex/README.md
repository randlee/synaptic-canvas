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
# Run a prompt (background by default; returns agentId + output_file)
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

## Configuration

Models (`--model` or JSON `model`; default `gpt-6-astra`):

| Alias | Model slug | Supported `--effort` levels |
|-------|------------|-----------------------------|
| `sol` | `gpt-6-sol` | low, medium, high, xhigh, max, ultra |
| `astra` (default; also `codex`) | `gpt-6-astra` | low, medium, high, xhigh, max, ultra |
| `luna` | `gpt-6-luna` | low, medium, high, xhigh, max |
| — | `gpt-5.6-sol` | low, medium, high, xhigh, max, ultra |
| `terra` | `gpt-5.6-terra` | low, medium, high, xhigh, max, ultra |
| — | `gpt-5.6-luna` | low, medium, high, xhigh, max |
| — | `gpt-5.5` | low, medium, high, xhigh |

- Reasoning effort: `--effort` or JSON `reasoning_effort`. When omitted, no override is passed and
  your `~/.codex/config.toml` applies. Unsupported model/effort combinations are rejected.
- Command-line flags override the JSON payload.
- Breaking in 0.14.0: legacy aliases (`gpt-5.2-codex`, `codex-max`/`max`, `codex-mini`/`mini`,
  `gpt-5`, `gpt-5.2`, `gtp-5`) were removed.

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

## Changelog
See `CHANGELOG.md`.

## License
MIT, see `LICENSE`.
