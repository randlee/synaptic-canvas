# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.14.2] - 2026-10-17
### Changed
- A team member launching without `atm_identity` now gets a new agent: when the
  parent has `ATM_TEAM` and the launch has tools (`isolation.tools` is not
  `none`), the runtime generates an identity from the model family's name pool
  (the pools sc-launch-term uses, now shared as `agent_identity.py`), registers
  it with `atm teams add-member`, and runs the child in teammate mode
  (`ATM_TEAM`, `ATM_IDENTITY` and `BEADS_ACTOR` set). The identity is returned in
  `data.atm_identity`. Previously the child got the team but no identity. An
  explicit `atm_identity` works as before; `tools: none` and launches without a
  team generate and register nothing.

### Fixed
- `BEADS_ACTOR` now tracks the child's `ATM_IDENTITY` exactly. `bd` (beads)
  attributes audit-trail entries and slot holders to `$BEADS_ACTOR`, so a child
  that inherited the parent's value misattributed its work to the parent. In
  teammate mode `BEADS_ACTOR` is set to the registered identity; otherwise it is
  dropped alongside `ATM_IDENTITY` (also when it comes from `env_file`).
  `ATM_TEAM` is still never touched.

## [0.14.1] - 2026-10-17
### Fixed
- Outside teammate mode the child keeps an inherited `ATM_TEAM` and only
  `ATM_IDENTITY` is cleared: a child is still part of the parent's team but
  must never take on the parent's identity. Previously both were cleared.
  Teammate mode (`atm_identity` plus a parent `ATM_TEAM`) is unchanged. This
  also applies to `ATM_*` values loaded from `env_file`.

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
- `env_file`: a dotenv file merged over the inherited environment, for credentials a shell
  alias would otherwise load. Relative paths are found in `cwd`, the repo root, or the main
  worktree root; launchpad's own variables still win. Results and the audit log carry the
  path and variable names (`env_keys`), never values (`VALIDATION.ENV_FILE_NOT_FOUND`,
  `VALIDATION.INVALID_ENV_FILE`).
- One audit line per launch in `.claude/state/logs/sc-launchpad/launch.jsonl`
  (never the prompt).
- Documented direct script invocation for programs (`--json '<payload>'` or
  `--json -` from stdin) for parallel fan-out.

### Changed
- Defaults are the newest models: claude `fable` (`claude-fable-5-1`), codex `sol`
  (`gpt-6.1-sol`). The `codex` alias now means the Codex default (`gpt-6.1-sol`,
  was `gpt-5.6-terra`); `luna` is `gpt-6-luna`. Legacy codex aliases were removed.
  `data.model` is always the full model id. Claude ids outside the table (for example
  `claude-sonnet-4-6`, `claude-fable-5`) now fail with `VALIDATION.INVALID_MODEL`;
  append `[1m]` to any claude alias or id (`fable[1m]`) for the 1M-context variant.
  The ATM roster records the alias with the suffix (`fable[1m]`, was `fable`).
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
- Stop-signal handlers are installed before the child starts, so a stop request
  during launch kills the child instead of leaving it running.

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
