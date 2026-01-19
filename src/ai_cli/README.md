# ai_cli

Python/pydantic utilities for CLI integration and tool schemas.

## Task Tool schema

Input schema (JSON) lives in `src/ai_cli/task_tool.schema.json` and is mirrored by
the pydantic model in `src/ai_cli/task_tool.py`.
Output schema (JSON) lives in `src/ai_cli/task_tool.output.schema.json`.

Foreground output (run_in_background: false or omitted):
- Object with `output` and `agentId`.

Background output (run_in_background: true):
- Object with `output`, `agentId`, and `output_file` (JSONL transcript path).

### Input example

```json
{
  "description": "Summarize issue",
  "prompt": "Summarize the latest GitHub issue thread",
  "subagent_type": "issue-summary",
  "model": "haiku",
  "run_in_background": false,
  "max_turns": 10
}
```

### Output examples

Blocking:

```json
{
  "output": "Agent result here",
  "agentId": "agent-123"
}
```

Background:

```json
{
  "output": "Async agent launched successfully.",
  "agentId": "agent-123",
  "output_file": "/path/to/agent.jsonl"
}
```

### Background JSONL format

Each line in `output_file` is a JSON object representing a message. Status is inferred
from message types and tool results that include `is_error: true`.

## CLI

Print schema:

```bash
python3 -m ai_cli schema
```

Validate input from file:

```bash
python3 -m ai_cli validate --file /path/to/input.json
```

Run a task (blocking by default, runner auto-selects based on availability):

```bash
python3 -m ai_cli run --file /path/to/input.json
```

Run in background with Codex and custom output directory:

```bash
python3 -m ai_cli run --runner codex --background --output-dir .sc/sessions --file /path/to/input.json
```

Background outputs default to `.sc/sessions` (gitignored). For Codex, if `CODEX_HOME` is set,
the default becomes `$CODEX_HOME/sessions`. Use `--output-dir` to override.

Model defaults:
- Claude defaults to `sonnet`
- Codex defaults to `gpt-5.2-codex`

Codex model aliases:
- `codex` -> `gpt-5.2-codex`
- `codex-max` or `max` -> `gpt-5.1-codex-max`
- `codex-mini` or `mini` -> `gpt-5.1-codex-mini`
- `gpt-5` or `gtp-5` -> `gpt-5.2`

## Logs

Errors and schema validation failures are logged to:
- `.claude/state/logs/ai-cli/`

Task start/end events are also logged with `agentId`, `runner`, `model`, and parameters.
Logs include `prompt_preview` and `duration_ms`.
