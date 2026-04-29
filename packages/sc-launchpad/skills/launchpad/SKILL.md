---
name: launchpad
version: 0.11.0
description: "Use when another workflow must launch Claude, Codex, or Gemini as a separate background sub-agent without opening a terminal. Spawns the `launchpad` agent with fenced JSON input and `run_in_background: true`."
---

# Launchpad Skill

Use this skill for pure background-agent launches. This skill is intentionally separate from any visible terminal launcher flow.

## Purpose

- Start Claude, Codex, or Gemini in a separate background sub-agent runtime.
- Keep the caller responsive by spawning `launchpad` with `run_in_background: true`.
- Normalize ATM teammate mode safely so parent identity does not leak into the child process.

## Invocation Contract

Spawn the `launchpad` agent with `run_in_background: true`.

- Do not run the runtime script inline in the main session.
- Do not open a terminal window.
- Do not pass half-configured ATM state through implicitly.

The `launchpad` agent accepts fenced JSON only. Provide one JSON object with:

```json
{
  "description": "Short launch description",
  "prompt": "Task text for the child CLI",
  "tool": "claude",
  "model": "haiku",
  "cwd": "/abs/path/to/repo",
  "atm_identity": "reviewer-1",
  "extra_args": ["--append-system-prompt", "Focus on tests first"]
}
```

Required fields:
- `description`
- `prompt`
- `tool`
- `cwd`

Optional fields:
- `model`
- `atm_identity`
- `extra_args`

## ATM Rules

Teammate mode is enabled only when both conditions are true:

1. The parent environment contains `ATM_TEAM`
2. The JSON payload includes `atm_identity`

Then the runtime:
- runs `atm teams add-member <team> <identity> --model <tool-or-model> --cwd <cwd>`
- launches the child with both `ATM_TEAM` and `ATM_IDENTITY` set

Otherwise the runtime:
- clears `ATM_TEAM`
- clears `ATM_IDENTITY`
- launches as a plain background agent

All other parent environment variables are preserved for the child process.

## Output Contract

The `launchpad` agent returns the runtime stdout exactly as-is. The runtime prints a JSON envelope:

```json
{
  "success": true,
  "data": {
    "tool": "claude",
    "model": "haiku",
    "cwd": "/abs/path/to/repo",
    "teammate_mode": true,
    "atm_team": "annotations-test",
    "atm_identity": "reviewer-1",
    "exit_code": 0,
    "stdout": "child stdout",
    "stderr": ""
  },
  "error": null
}
```

Errors use the same envelope with `success: false` and a populated `error` object.
