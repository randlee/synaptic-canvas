---
allowed-tools: Bash(python3 .claude/scripts/sc_codex_task.py*)
name: sc-codex
description: Run Codex tasks via the ai_cli runner (supports JSON input, background runs, and model selection).
version: 0.14.0
options:
  - name: --model
    args:
      - name: model
        description: Codex model alias (sol, astra, luna, terra, codex) or full id. See the sc-codex README table.
    description: Select the Codex model (default sol).
  - name: --effort
    args:
      - name: effort
        description: One of low, medium, high, xhigh, max, ultra (supported levels vary by model).
    description: Set reasoning effort. When omitted, the Codex CLI config (~/.codex/config.toml) applies.
  - name: --background
    description: Run in background mode (returns output_file). Default if not disabled.
  - name: --no-background
    description: Force blocking mode (waits for completion).
  - name: --json
    description: Treat remaining arguments as JSON Task Tool input.
  - name: --help
    description: Show usage.
---

# /sc-codex

Run a Codex task using the Task Tool-compatible runner.

Usage:
- `/sc-codex write a haiku about rain`
- `/sc-codex --model luna write a haiku about rain`
- `/sc-codex --model sol --effort low write a haiku about rain`
- `/sc-codex --background write a haiku about rain`
- `/sc-codex --json {"description":"Compose haiku","prompt":"compose a haiku","subagent_type":"sc-codex"}`

Flags:
- `--help` (show usage)
- `--model <alias|id>` (sol, astra, luna, terra, codex, or a full id; default `sol`)
- `--effort <level>` (low, medium, high, xhigh, max, ultra; omitted = Codex CLI config)
- `--background` (force background mode)
- `--no-background` (force blocking mode)
- `--json <object>` (Task Tool JSON input)

Models, aliases, and the efforts each model supports: see the table in the sc-codex
[README](../README.md#models-and-reasoning-effort). Unknown models and unsupported efforts are
rejected before launch with a message listing the valid choices.

## Context

Use the `codex-agent` skill to launch a Codex task **in background mode**.

Interpret arguments as follows:
- `--help`: print usage (with flags) and stop.
- `--model <alias|id>`: set `model` in the Task Tool JSON (or pass `--model` alongside `--json`).
- `--effort <level>`: set `reasoning_effort` in the Task Tool JSON (or pass `--effort` alongside `--json`).
- Natural language: "sc-codex with sol low" means `--model sol --effort low`; "luna high" means
  `--model luna --effort high`. `low`, `medium`, `high`, `xhigh`, `max`, `ultra` are always effort
  levels, never models; a bare level ("sc-codex high") means the default model with that effort.
- `--background`: force background mode (default for this command).
- `--no-background`: force blocking mode (explicit override).
- `--json <object>`: treat the remaining arguments as Task Tool JSON and pass through unchanged.
- Otherwise: treat the remaining arguments as the prompt string.

After the child task completes, preserve any caller-specified post-processing in the original prompt. If the caller asks for a grade, summary, or strict output shape after waiting on Codex, provide that instead of defaulting to a generic status summary.

When running:
1) Build Task Tool JSON with `description`, `prompt`, `subagent_type: "sc-codex"` (unless user provided one).
   Default `run_in_background` to true unless `--no-background` is provided.
   Include `"model"` and/or `"reasoning_effort"` only when the user asked for them, e.g.
   `{"description":"Compose haiku","prompt":"compose a haiku","subagent_type":"sc-codex","model":"sol","reasoning_effort":"low"}`.
2) Call the codex-agent runner as a Bash tool call using `--json`.
   Always use `python3 .claude/scripts/sc_codex_task.py --json '{...}'` (do not call other runner scripts).
   `--model`/`--effort` flags given alongside `--json` override payload fields.
   Do not invent flags like `--run_in_background`, `--description`, `--prompt`, or `--subagent_type`.
3) Poll the `output_file` for up to 8 seconds using Python (avoid `tail -f` and avoid `timeout`, which may be missing on macOS):

```bash
python3 - <<'PY'
import json, time
from pathlib import Path

path = Path("PATH_TO_OUTPUT_FILE")
deadline = time.time() + 8
while time.time() < deadline:
    if path.exists():
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if any('"type": "assistant"' in line for line in lines):
            print(path.read_text(encoding="utf-8"))
            break
    time.sleep(0.5)
else:
    print("STILL RUNNING")
PY
```

If the task is still running, return `agentId` and `output_file`.
4) If the child run fails, surface the error; do not retry with a different model.
5) Return the Codex output and the `agentId`. If the task is still running at timeout, return `agentId` and `output_file`
   and tell the user how to check status.
6) If a caller provides `resume` but the prior transcript cannot be reopened or does not contain usable assistant output, return a concise error and stop. Do not fabricate prior context or a synthetic refinement result.

## Response

Return a JSON object with:
- `agentId`
- `status` ("success" or "error")
- `output` (final Codex output if available)
- `output_file` (required when background mode is used)

If background mode was used and `output_file` is missing, treat that as an error.
If `resume` was requested but the transcript path is unavailable or unreadable, treat that as an error.
