---
allowed-tools: Bash(python3 .claude/scripts/sc_codex_task.py*)
name: sc-codex
description: Run Codex tasks via the ai_cli runner (supports JSON input, background runs, and model selection).
version: 0.9.0
options:
  - name: --model
    args:
      - name: model
        description: Codex model or alias (e.g., codex, max, mini, gpt-5).
    description: Select the Codex model.
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
- `/sc-codex --model mini write a haiku about rain`
- `/sc-codex --background write a haiku about rain`
- `/sc-codex --json {"description":"Compose haiku","prompt":"compose a haiku","subagent_type":"sc-codex"}`

Flags:
- `--help` (show usage)
- `--model <alias|full>` (codex, codex-max/max, codex-mini/mini, gpt-5, or full model name)
- `--background` (force background mode)
- `--no-background` (force blocking mode)
- `--json <object>` (Task Tool JSON input)

## Context

Use the `codex-agent` skill to launch a Codex task **in background mode**.

Interpret arguments as follows:
- `--help`: print usage (with flags) and stop.
- `--model <alias|full>`: pass the model to the codex-agent runner.
- `--background`: force background mode (default for this command).
- `--no-background`: force blocking mode (explicit override).
- `--json <object>`: treat the remaining arguments as Task Tool JSON and pass through unchanged.
- Otherwise: treat the remaining arguments as the prompt string.

When running:
1) Build Task Tool JSON with `description`, `prompt`, `subagent_type: "sc-codex"` (unless user provided one).
   Default `run_in_background` to true unless `--no-background` is provided.
2) Call the codex-agent runner as a Bash tool call using `--json`.
   Always use `python3 .claude/scripts/sc_codex_task.py --json '{...}'` (do not call other runner scripts).
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
4) Return the Codex output and the `agentId`. If the task is still running at timeout, return `agentId` and `output_file`
   and tell the user how to check status.

## Response

Return a JSON object with:
- `agentId`
- `status` ("success" or "error")
- `output` (final Codex output if available)
- `output_file` (required when background mode is used)

If background mode was used and `output_file` is missing, treat that as an error.
