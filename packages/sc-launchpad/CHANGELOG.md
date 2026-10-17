# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.14.0] - 2026-10-17
### Added
- `effort` payload field: claude `--effort`, codex `-c model_reasoning_effort=<level>`,
  validated per model (`VALIDATION.INVALID_EFFORT`); gemini returns `CAPABILITY.UNSUPPORTED`.
- Shared model table `scripts/agent_models.py` (with sc-launch-term and sc-codex).
- Structured output mode (`output_format: "json"`): `claude --print --output-format
  stream-json --verbose` and `codex exec --json`, returning `data.session_id` and
  `data.result_text`. Raw stdout is not repeated in the envelope
  (`data.stdout: null`); failures carry `error.details.stdout_tail`.
- `resume_session_id` to continue a claude or codex session; resumed turns must
  pass `isolation` explicitly to keep or relax it.
- `isolation` (`tools: "none"|"default"`, `cwd: "temp"|"given"`) with documented
  per-harness flag sets and guarantees; temp directories are returned as `data.cwd`.
- `timeout_seconds`, which kills the child process tree and returns `CLI.TIMEOUT`.
- Typed failure codes with `suggested_action` and `error.details` (stderr tail,
  searched PATH, reported error): `CLI.TIMEOUT`, `CLI.OUTPUT_UNPARSEABLE`,
  `CLI.SESSION_ID_MISSING`, `CLI.RESULT_MISSING`, `CLI.RESUME_SESSION_NOT_FOUND`,
  `CLI.AUTH_FAILED`, `CLI.REPORTED_ERROR`, `CLI.UNSUPPORTED_FLAG`,
  `CLI.LAUNCH_FAILED`, `CLI.UNSAFE_ARGUMENT`, `CAPABILITY.UNSUPPORTED` (gemini),
  `RUNTIME.INTERRUPTED`, `RUNTIME.CODEX_HOME_FAILED`, `ISOLATION.VIOLATED`.
  `CLI.UNSUPPORTED_FLAG` names the rejected flag/feature in `details.rejected`.
- `isolation.tools: "none"` is verified, not assumed: claude must report an init
  event with no tools and no MCP servers and no `tool_use`; codex may emit only
  message/reasoning/error/todo items. Anything else fails closed with
  `ISOLATION.VIOLATED` and no `result_text`.
- Isolated codex runs use a private `CODEX_HOME` holding only `auth.json`, so the
  user's global `AGENTS.md`, config, and session history never reach the child.
- `data.cleanup_paths`: everything the session leaves behind (temp cwd, private
  `CODEX_HOME`, claude transcripts of a temp cwd); the caller deletes these after
  the last turn. A temp cwd is removed automatically if no child started.
- `ephemeral: true` (claude `--no-session-persistence`, codex `--ephemeral`).
- One audit line per launch in `.claude/state/logs/sc-launchpad/launch.jsonl`
  (never the prompt).
- Documented direct script invocation for programs (`--json '<payload>'` or
  `--json -` from stdin) for parallel fan-out.

### Changed
- Defaults are the newest models: claude `fable` (`claude-fable-5-1`), codex `sol`
  (`gpt-6.1-sol`). The `codex` alias now means the Codex default (`gpt-6.1-sol`,
  was `gpt-5.6-terra`); `luna` is `gpt-6-luna`. Legacy codex aliases were removed.
  `data.model` is always the full model id.
- The runtime is split into modules (`launchpad_models`, `launchpad_commands`,
  `launchpad_process`, `launchpad_output`) behind the unchanged
  `sc_launchpad_task.py` entry point.
- claude and codex always receive the prompt on stdin, in text mode too (no
  Windows command-line length limit, nothing for a `.cmd` shim to reinterpret).
  On a `.cmd`/`.bat` shim, arguments containing cmd.exe metacharacters fail as
  `CLI.UNSAFE_ARGUMENT` instead of being passed through.
- Child processes never inherit the runtime's stdin and are resolved to an
  absolute path from PATH.
- SIGTERM/SIGINT/SIGHUP to the runtime kills the child process tree.
- `resume_session_id` is limited to `[A-Za-z0-9._:-]`.
- `cwd` is required unless `isolation.cwd` is `"temp"`, and forbidden with it.
- `isolation.tools: "none"` rejects `extra_args` and `atm_identity`.
- Stop signals are trapped before the child starts, so no signal can orphan it.

### Fixed
- The runtime imports on Python 3.9 (pydantic models no longer use `X | None`).

## [0.13.0] - 2026-09-22
### Added
- Added Claude Fable model aliases to the background launch runtime.
- Added Sol, Terra, and Luna Codex model aliases with Terra routing for deprecated `codex`.

### Fixed
- Use the installed Codex CLI's supported `--yolo` automation flag for background launches.

## [0.10.0] - 2026-04-25
### Added
- Initial `sc-launchpad` release with a background-launch skill and thin forwarding agent.
- Shared runtime helpers for teammate-mode normalization and roster registration.
- JSON-envelope runtime output for Claude, Codex, and Gemini child launches.
