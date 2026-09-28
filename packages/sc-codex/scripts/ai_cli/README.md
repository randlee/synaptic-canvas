# ai_cli

Python/pydantic utilities for CLI integration and tool schemas.

## Task Tool schema

Input schema (JSON) lives in `packages/sc-codex/schemas/task_tool.schema.json`
and is mirrored by the pydantic model in `packages/sc-codex/scripts/ai_cli/task_tool.py`.
Output schema (JSON) lives in `packages/sc-codex/schemas/task_tool.output.schema.json`.

Foreground output (run_in_background: false or omitted):
- Object with `output` and `agentId`.

Background output (run_in_background: true):
- Object with `output`, `agentId`, and `output_file` (JSONL transcript path).

### Input example

```json
{
  "description": "Summarize issue",
  "prompt": "Summarize the latest GitHub issue thread",
  "subagent_type": "sc-codex",
  "model": "sol",
  "reasoning_effort": "low",
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

Run a task (blocking by default). Without `--runner`, the runner auto-selects (Claude first if
installed), so pass `--runner codex` for Codex models such as `sol`:

```bash
PYTHONPATH=packages/sc-codex/scripts python3 -m ai_cli run --runner codex --file /path/to/input.json
```

Run in background with Codex and custom output directory:

```bash
PYTHONPATH=packages/sc-codex/scripts python3 -m ai_cli run --runner codex --background --output-dir .sc/sessions --file /path/to/input.json
```

Background outputs default to `.sc/sessions` (gitignored). For Codex, if `CODEX_HOME` is set,
the default becomes `$CODEX_HOME/sessions`. Use `--output-dir` to override.

Override model and reasoning effort from the command line (flags override the JSON payload):

```bash
PYTHONPATH=packages/sc-codex/scripts python3 -m ai_cli run --runner codex --model sol --effort low --file /path/to/input.json
# -> codex exec --yolo --model gpt-6-sol -c 'model_reasoning_effort="low"' <prompt>
```

Model defaults:
- Claude defaults to `sonnet`
- Codex defaults to `gpt-6-astra`

Codex models (the catalog is defined once in `ai_cli/task_tool.py`; `CODEX_MODEL_ALIASES`,
`CODEX_MODEL_EFFORTS`, `REASONING_EFFORTS`):

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

Full slugs are accepted as-is; unknown names raise an error listing valid aliases and slugs.

Reasoning effort (`reasoning_effort` in JSON, `--effort` on the CLI):
- Levels: `low`, `medium`, `high`, `xhigh`, `max`, `ultra`; unsupported levels for the model are rejected.
- When unset, no `-c model_reasoning_effort` override is passed, so `~/.codex/config.toml` applies.
- Carried in the payload, so background runs keep it.
- Ignored by the Claude runner (`claude --print` has no equivalent).

ChatGPT-account fallback: if Codex reports the model is "not supported when using Codex with a
ChatGPT account", the runner retries once with `gpt-5.5` (effort clamped to `xhigh` if higher)
and logs a `model_fallback` event.

## Logs

Errors and schema validation failures are logged to:
- `.claude/state/logs/<package-name>/` (derived from the runner script path)

Task start/end events are also logged with `agentId`, `runner`, `model`, `reasoning_effort`, and parameters.
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
