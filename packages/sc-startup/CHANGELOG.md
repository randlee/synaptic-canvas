# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.7.0] - 2025-12-21

### Changed
- Version synchronized with marketplace v0.7.0 release
- Part of coordinated marketplace release
- Updated dependencies:
  - sc-ci-automation >= 0.7.0 (was >= 0.1.0)
  - sc-git-worktree >= 0.7.0 (was >= 0.6.0)

### Notes
- No functional changes from v0.6.1
- Synchronized versioning for consistency across all packages

## [0.6.1] - 2025-12-20
### Changed
- Updated default config paths from `docs/` to `pm/` directory
- Enhanced sc-startup-init agent to scan `pm/` and `project*/` directories
- Added support for multiple candidate detection (startup prompts and checklists)
- Sort candidates by modification time (most recent first)
- Added ARCH-*.md pattern matching for startup prompts
- Expanded README with path detection documentation

### Improved
- Better alignment with Synaptic Canvas project structure
- More flexible file discovery
- Clearer candidate prioritization

## [0.6.0] - 2025-12-19
### Added
- Initial pre-release of `sc-startup` package (command, skill, checklist agent).
- Startup config example and smoke-test script.
- Dependency validation and readonly/fast modes.
- Package documentation (README, USE-CASES, TROUBLESHOOTING, LICENSE).
