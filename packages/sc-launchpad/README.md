# sc-launchpad

Launch Claude, Codex, or Gemini as a background sub-agent runtime without
opening a visible terminal window.

## Included Artifacts

- `skills/launchpad/SKILL.md`
- `agents/launchpad.md`
- `scripts/sc_launchpad_task.py`
- `scripts/launchpad_shared.py`

## What It Does

`sc-launchpad` is the background-runtime counterpart to `sc-launch-term`.

Use it when another workflow needs to:

- start Claude, Codex, or Gemini as a child runtime
- keep the parent session responsive
- normalize ATM teammate-mode state before spawning the child
- return a machine-readable launch envelope instead of interactive terminal output

## Invocation Model

The skill spawns the `launchpad` agent with `run_in_background: true`.

The agent forwards one JSON payload to the runtime script, which launches the
selected CLI and returns a JSON envelope describing success, exit code, stdout,
stderr, and teammate-mode state.

## ATM Teammate Mode

Teammate mode is enabled only when:

1. the parent environment includes `ATM_TEAM`
2. the payload includes `atm_identity`

When both are present, the runtime:

- runs `atm teams add-member <team> <identity> --model <tool-or-model> --cwd <cwd>`
- launches the child process with both `ATM_TEAM` and `ATM_IDENTITY` set

Otherwise, the runtime clears both ATM variables before spawning the child.

## Security and Runtime Notes

- `sc-launchpad` launches only locally installed `claude`, `codex`, or `gemini` executables.
- The runtime preserves most of the parent environment, but explicitly normalizes `ATM_TEAM` and `ATM_IDENTITY` to avoid leaking partial teammate state.
- The `launchpad` agent is intentionally thin: it should make one runtime call and return the runtime stdout exactly as emitted.
- The runtime expects absolute working-directory paths in launch payloads.
- This package depends on local Python 3 plus whichever AI CLI you are launching.

## Installation

```bash
/marketplace install sc-launchpad
```

This package is intended for local installation into a repository `.claude/`
surface where orchestrator skills or agents need background launch support.

## Example

```json
{
  "description": "Run a background code review",
  "prompt": "Review the changed files for risks and missing tests.",
  "tool": "codex",
  "cwd": "/abs/path/to/repo",
  "atm_identity": "reviewer-1",
  "extra_args": ["--model", "gpt-5.5"]
}
```
