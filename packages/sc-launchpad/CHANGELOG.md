# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.14.0] - 2026-10-17
### Added
- Structured output mode (`output_format: "json"`): `claude --print --output-format json`
  and `codex exec --json`, returning `data.session_id` and `data.result_text`
  separately from raw stdout.
- `resume_session_id` to continue a claude or codex session; resumed turns must
  pass `isolation` explicitly to keep or relax it.
- `isolation` (`tools: "none"|"default"`, `cwd: "temp"|"given"`) with documented
  per-harness flag sets and guarantees; temp directories are returned as `data.cwd`.
- `timeout_seconds`, which kills the child process tree and returns `CLI.TIMEOUT`.
- Typed failure codes with `suggested_action` and `error.details` (stderr tail,
  searched PATH, reported error): `CLI.TIMEOUT`, `CLI.OUTPUT_UNPARSEABLE`,
  `CLI.SESSION_ID_MISSING`, `CLI.RESULT_MISSING`, `CLI.RESUME_SESSION_NOT_FOUND`,
  `CLI.AUTH_FAILED`, `CLI.REPORTED_ERROR`, `CLI.UNSUPPORTED_FLAG`,
  `CLI.LAUNCH_FAILED`, `CAPABILITY.UNSUPPORTED` (gemini).
- Documented direct script invocation for programs (`--json '<payload>'` or
  `--json -` from stdin) for parallel fan-out.

### Changed
- Internal control flow uses a `Result` discriminated union (frozen `Ok`/`Err`).
- Child processes get an empty stdin and are resolved to an absolute path from PATH.
- `cwd` is optional only when `isolation.cwd` is `"temp"`.

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
