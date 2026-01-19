# ai_cli

Python/pydantic utilities for CLI integration and tool schemas.

## Task Tool schema

Input schema (JSON) lives in `packages/sc-codex/scripts/ai_cli/task_tool.schema.json`
and is mirrored by the pydantic model in `packages/sc-codex/scripts/ai_cli/task_tool.py`.
Output schema (JSON) lives in `packages/sc-codex/scripts/ai_cli/task_tool.output.schema.json`.

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
PYTHONPATH=packages/sc-codex/scripts python3 -m ai_cli schema
```

Validate input from file:

```bash
PYTHONPATH=packages/sc-codex/scripts python3 -m ai_cli validate --file /path/to/input.json
```

Run a task (blocking by default, runner auto-selects based on availability):

```bash
PYTHONPATH=packages/sc-codex/scripts python3 -m ai_cli run --file /path/to/input.json
```

Run in background with Codex and custom output directory:

```bash
PYTHONPATH=packages/sc-codex/scripts python3 -m ai_cli run --runner codex --background --output-dir .sc/sessions --file /path/to/input.json
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

## Hook emulation

If `subagent_type` refers to a local agent (e.g., `.claude/agents/<name>.md`),
`ai_cli` will parse frontmatter `hooks: PreToolUse` and run `type: command` hooks
before executing the agent. This emulates Claude's input validation hooks for Codex.

Resolution order for agent files:
1. If `subagent_type` is a path and exists, use it directly.
2. Search upward from `cwd` for `.claude/agents/<name>.md`.
3. Fall back to `~/.claude/agents/<name>.md`.

If no agent file is found:
- `codex`: fail with an error
- `claude`: skip hooks (assumes built-in agent)

Hook executions are logged with `hook_start`/`hook_end` events (status + command).
