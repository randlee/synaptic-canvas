# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]
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
