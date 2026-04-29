# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.10.0] - 2026-04-25
### Added
- Initial `sc-launch-term` release with `/sc:sonnet`, `/sc:haiku`, `/sc:opus`, `/sc:codex`, and `/sc:gemini`.
- Shared `sc-term-launch.py` launcher with terminal autodetect.
- macOS support for iTerm2, Ghostty, WezTerm, Warp, and Terminal.app.
- Windows support for Windows Terminal and Warp.

### Notes
- `--tmux` depends on a local `tmux` executable.
- Warp launch automation opens a new window; scripted new-tab launches are not supported there.
