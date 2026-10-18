---
name: launchpad
version: 0.14.3
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
- `cwd` (required, except it must be omitted when `isolation.cwd` is `"temp"`)

Optional fields:
- `model`: alias or full id (claude default `fable`, codex default `sol`; see README)
- `effort`: reasoning effort (claude `low`..`max`, codex `low`..`ultra`); omit for the CLI default
- `atm_identity`: the child's ATM identity; under an `ATM_TEAM` it is generated when omitted (see ATM Rules)
- `extra_args`
- `output_format`: `"text"` or `"json"` (structured mode; returns `session_id` and `result_text`)
- `resume_session_id`: continue a claude/codex session; requires an explicit `isolation` object
- `isolation`: `{"tools": "none"|"default", "cwd": "temp"|"given"}`
- `timeout_seconds`: kill the child and return `CLI.TIMEOUT` after this many seconds
- `ephemeral`: `true` to keep claude/codex from persisting the session
- `env_file`: dotenv file (e.g. `.env`) merged over the inherited environment; a relative
  path is looked up in `cwd`, the repo root, then the main worktree root (README `env_file`)

`output_format` defaults to `json` when `resume_session_id` or `isolation` is
present, otherwise `text`. Payloads without the new fields still validate, but
defaults and some behavior changed in 0.14.0 (newest-model defaults, the `codex`
alias, full ids in `data.model`, prompt on stdin); see the CHANGELOG "Changed"
section. Gemini returns `CAPABILITY.UNSUPPORTED` for `output_format: "json"`,
`resume_session_id`, `isolation`, `ephemeral`, and `effort`.

### Multi-turn isolated sessions

1. Turn 1: `"isolation": {"tools": "none", "cwd": "temp"}` (no `cwd`). Keep
   `data.session_id` and `data.cwd` from the envelope.
2. Turn 2..N: pass `"cwd": <data.cwd>`, `"resume_session_id": <data.session_id>`,
   and `"isolation": {"tools": "none", "cwd": "given"}` to keep isolation, or
   `{"tools": "default", "cwd": "given"}` to relax it explicitly.

claude and codex receive the prompt on stdin (no command-line length limit).
sc-launchpad never deletes what a session needs to resume: after the last turn
the caller deletes every path in `data.cleanup_paths` (temp cwd, private
`CODEX_HOME`, claude transcripts). `"ephemeral": true` keeps claude/codex from
persisting the session at all (it then cannot be resumed).

With `tools: "none"` the runtime checks the harness output for any tool
availability or use and fails closed with `ISOLATION.VIOLATED`.

See the package README for the exact per-harness flags and what each
isolation level guarantees.

Claude aliases: `fable`, `opus`, `sonnet`, `haiku`. Codex aliases: `sol`, `astra`,
`terra`, `luna`, `codex`. Full ids are also accepted; a claude alias or id with
`[1m]` appended selects the 1M-context variant. The README has the table.

## ATM Rules

Teammate mode is enabled when both conditions are true:

1. The parent environment contains `ATM_TEAM`
2. The launch has tools (`isolation.tools` is not `"none"`)

The identity is the payload's `atm_identity`, or, when it is omitted, a new identity
generated from the model family's name pool (same pools as sc-launch-term). A team
member therefore always launches a distinct agent that can receive messages and beads,
never one using the parent's identity. The identity is returned in `data.atm_identity`.

Then the runtime:
- runs `atm teams add-member <team> <identity> --model <tool-or-model> --cwd <cwd>`
- launches the child with both `ATM_TEAM` and `ATM_IDENTITY` set, and `BEADS_ACTOR` set to the same identity (so `bd` attributes the child's work to the child)

Otherwise (no `ATM_TEAM`, or `isolation.tools: "none"`) the runtime:
- generates and registers nothing
- clears `ATM_IDENTITY` and `BEADS_ACTOR` (the child must never take on the parent's identity)
- keeps an inherited `ATM_TEAM` (the child is still part of the parent's team)
- launches as a plain background agent, without registering a member

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
    "cleanup_paths": [],
    "teammate_mode": true,
    "atm_team": "annotations-test",
    "atm_identity": "reviewer-1",
    "exit_code": 0,
    "stdout": null,
    "stderr": "",
    "output_format": "json",
    "session_id": "646130d0-5d6a-434c-95ed-b8d500fdc35f",
    "result_text": "final assistant text",
    "resumed_session_id": null,
    "isolation": {"tools": "none", "cwd": "given", "flags": ["--tools", "", "--strict-mcp-config", "--safe-mode", "--disable-slash-commands"]},
    "timeout_seconds": 120,
    "timed_out": false,
    "duration_seconds": 3.4,
    "warnings": []
  },
  "error": null
}
```

In text mode `session_id` and `result_text` are `null` and `stdout` holds the
child's output. In JSON mode `stdout` is `null`; failures carry
`error.details.stdout_tail`.

Errors use the same envelope with `success: false` and a populated `error`
object: `code`, `message`, `recoverable`, `suggested_action`, and optional
`details` (for example `stderr_tail`, `searched_path`, `reported_error`).
Codes include `CLI.NOT_FOUND`, `CLI.NON_ZERO_EXIT`, `CLI.TIMEOUT`,
`CLI.OUTPUT_UNPARSEABLE`, `CLI.SESSION_ID_MISSING`, `CLI.RESULT_MISSING`,
`CLI.RESUME_SESSION_NOT_FOUND`, `CLI.AUTH_FAILED`, `CLI.REPORTED_ERROR`,
`CLI.UNSUPPORTED_FLAG` (names the rejected flag in `details.rejected`),
`CLI.UNSAFE_ARGUMENT`, `ISOLATION.VIOLATED`, `RUNTIME.INTERRUPTED`, and
`CAPABILITY.UNSUPPORTED`.

## Direct Script Invocation (programs only)

A program (not the main LLM session) may run
`python3 .claude/scripts/sc_launchpad_task.py --json '<payload>'` (plugin
install: `$CLAUDE_PLUGIN_ROOT/scripts/sc_launchpad_task.py`) (or
`--json -` with the payload on stdin) as a subprocess, for example to fan out
one prompt to several harnesses in parallel. It prints exactly one envelope on
stdout and exits 0; branch on `success`. LLM sessions keep using the
`launchpad` agent as described above.
