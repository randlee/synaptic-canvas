# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.14.1] - 2026-10-17
### Fixed
- With no ATM team (`ATM_TEAM` unset), launches no longer generate, register
  (`atm teams add-member`) or export an `ATM_IDENTITY`. An inherited
  `ATM_IDENTITY` is cleared in the launched session (`unset ATM_IDENTITY` in
  POSIX shells, `Remove-Item Env:ATM_IDENTITY` in PowerShell for Windows
  Terminal) and dropped from the launcher's own environment, so no backend
  hands the parent's identity to the child (two agents sharing one identity).
  `ATM_TEAM` is never cleared. An explicit `--identity` without a team is ignored with a warning.
  Launches with `ATM_TEAM` set are unchanged.

## [0.14.0] - 2026-10-17
### Added
- `/sc:astra` (`gpt-6-astra`) with its own identity pool.
- `--effort <level>` on every Claude and Codex model command and on
  `launch-*-model` / `attach-pane-*-model` (claude `--effort`, codex
  `-c model_reasoning_effort=<level>`), validated per model.
- Model subcommands accept full model ids as well as aliases; the launch JSON
  reports `model` (alias), `model_id`, and `effort` for both tools.
- Added the `/sc:fable` Claude model command.
- Added cmux terminal/workspace-tab launching.
- Added shared `/sc:sol`, `/sc:terra`, and `/sc:luna` Codex model launchers.
- Added sci-fi/cyberpunk identity pools for the Sol, Terra, and Luna aliases.

### Changed
- Models come from the shared table `scripts/agent_models.py` (also used by
  sc-launchpad and sc-codex). Claude launches pass the full id
  (`claude --model claude-fable-5-1`). `sol` is `gpt-6.1-sol`, `luna` is
  `gpt-6-luna`, `terra` stays `gpt-5.6-terra`.
- `/sc:codex` now launches the Codex default model (`sol`, `gpt-6.1-sol`) with
  the Sol identity pool instead of Terra.

### Fixed
- Runs on Python 3.9 again (`datetime.timezone.utc` instead of 3.11-only `datetime.UTC`).
- Use Codex's supported `--yolo` automation flag and `--enable hooks` feature flag for model launches.

## [0.10.0] - 2026-04-25
### Added
- Initial `sc-launch-term` release with `/sc:sonnet`, `/sc:haiku`, `/sc:opus`, `/sc:codex`, and `/sc:gemini`.
- Shared `sc-term-launch.py` launcher with terminal autodetect.
- macOS support for iTerm2, Ghostty, WezTerm, Warp, and Terminal.app.
- Windows support for Windows Terminal and Warp.

### Notes
- `--tmux` depends on a local `tmux` executable.
- Warp launch automation opens a new window; scripted new-tab launches are not supported there.
