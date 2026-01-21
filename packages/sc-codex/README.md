# sc-codex (v0.7.0)

Run Codex agents via a Task Tool-compatible runner with hook emulation and
background execution support. Provides a CLI wrapper plus JSON schemas for
input/output validation.

## Badges
- Status: pre-release (0.7.0)
- Compatibility: Synaptic Canvas 0.7.x
- Safety: hook commands are explicit and logged

## Installation
```bash
/marketplace install sc-codex --local
```

## Quick Start
```bash
# Run a task via the runner
python3 packages/sc-codex/scripts/sc_codex_task.py \
  --runner codex \
  --file /path/to/input.json

# Use ai_cli directly
PYTHONPATH=packages/sc-codex/scripts python3 -m ai_cli run --file /path/to/input.json
```

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
