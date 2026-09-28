---
allowed-tools: Bash(python3 .claude/scripts/sc_codex_task.py*)
name: sc-codex
description: Run Codex tasks via the ai_cli runner (supports JSON input, background runs, and model selection).
version: 0.14.0
options:
  - name: --model
    args:
      - name: model
        description: Codex model alias (sol, astra, luna, terra, codex) or full slug (e.g., gpt-6-sol, gpt-5.5).
    description: Select the Codex model (default gpt-6-astra).
  - name: --effort
    args:
      - name: effort
        description: One of low, medium, high, xhigh, max, ultra (supported levels vary by model).
    description: Set Codex reasoning effort. When omitted, the Codex CLI config (~/.codex/config.toml) applies.
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
- `--model <alias|slug>` (sol, astra, luna, terra, codex, or a full slug; default `gpt-6-astra`)
- `--effort <level>` (low, medium, high, xhigh, max, ultra; omitted = use `~/.codex/config.toml`)
- `--background` (force background mode)
- `--no-background` (force blocking mode)
- `--json <object>` (Task Tool JSON input)

Models and effort:

| Alias | Model slug | Supported `--effort` levels |
|-------|------------|-----------------------------|
| `sol` | `gpt-6-sol` | low, medium, high, xhigh, max, ultra |
| `astra` (default; also `codex`) | `gpt-6-astra` | low, medium, high, xhigh, max, ultra |
| `luna` | `gpt-6-luna` | low, medium, high, xhigh, max |
| — | `gpt-5.6-sol` | low, medium, high, xhigh, max, ultra |
| `terra` | `gpt-5.6-terra` | low, medium, high, xhigh, max, ultra |
| — | `gpt-5.6-luna` | low, medium, high, xhigh, max |
| — | `gpt-5.5` | low, medium, high, xhigh |

Legacy aliases (`gpt-5.2-codex`, `codex-max`/`max`, `codex-mini`/`mini`, `gpt-5`, `gpt-5.2`, `gtp-5`)
were removed in 0.14.0 and are rejected with an error listing the valid names.
An effort level the chosen model does not support is also rejected.

## Context

Use the `codex-agent` skill to launch a Codex task **in background mode**.

Interpret arguments as follows:
- `--help`: print usage (with flags) and stop.
- `--model <alias|slug>`: set `model` in the Task Tool JSON (or pass `--model` before `--json`).
- `--effort <level>`: set `reasoning_effort` in the Task Tool JSON (or pass `--effort` before `--json`).
  Natural language such as "use sc-codex with sol low" means `--model sol --effort low`.
- `--background`: force background mode (default for this command).
- `--no-background`: force blocking mode (explicit override).
- `--json <object>`: treat the remaining arguments as Task Tool JSON and pass through unchanged.
- Otherwise: treat the remaining arguments as the prompt string.

After the child task completes, preserve any caller-specified post-processing in the original prompt. If the caller asks for a grade, summary, or strict output shape after waiting on Codex, provide that instead of defaulting to a generic status summary.

When running:
1) Build Task Tool JSON with `description`, `prompt`, `subagent_type: "sc-codex"` (unless user provided one).
   Default `run_in_background` to true unless `--no-background` is provided.
   Include `"model"` and/or `"reasoning_effort"` when the user asked for them, e.g.
   `{"description":"Compose haiku","prompt":"compose a haiku","subagent_type":"sc-codex","model":"sol","reasoning_effort":"low"}`.
   Omit `reasoning_effort` when the user did not ask for one.
2) Call the codex-agent runner as a Bash tool call using `--json`.
   Always use `python3 .claude/scripts/sc_codex_task.py --json '{...}'` (do not call other runner scripts).
   `--model`/`--effort` flags placed before `--json` override the matching JSON fields.
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
4) If Codex rejects the model for a ChatGPT-account login, the runner already retries once on `gpt-5.5`
   (clamping effort to at most `xhigh`). Do not retry manually; surface any remaining error.
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
