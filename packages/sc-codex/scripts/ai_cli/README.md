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
# runs: <path to codex> exec --yolo --model gpt-6.1-sol -c model_reasoning_effort=low -   (prompt on stdin)
```

Models, aliases, defaults, and per-model efforts come from `ai_cli/agent_models.py` (a synced
copy of `packages/shared/scripts/agent_models.py`; never edit it here). The table is in the
sc-codex [README](../../README.md#models-and-reasoning-effort).

- Unknown models (in `--model` or the JSON `model`) and efforts the model does not support fail
  before launch with a message listing the valid choices.
- The resolved full model id is written back into the payload, so background runs and logs show it.
- Effort applies to both runners: Codex gets `-c model_reasoning_effort=<level>`, Claude gets
  `--effort <level>`. When unset, no flag is passed and the CLI's own configuration applies.

Platforms (Windows, macOS, Linux; Python 3.9+): the CLI is started through the full path from
`shutil.which` (npm installs `codex.cmd`/`claude.cmd` on Windows), and the prompt is sent as UTF-8
bytes on stdin (`codex exec ... -`, `claude --print`), never in argv, so it is not mangled by
`.cmd` shims, quoting, or newline translation.

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
