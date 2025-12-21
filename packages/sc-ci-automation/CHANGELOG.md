# Changelog

All notable changes to sc-ci-automation will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.0] - 2025-12-21

### Changed
- Version synchronized with marketplace v0.7.0 release
- Part of coordinated marketplace release

### Notes
- No functional changes from v0.1.0
- Synchronized versioning for consistency across all packages

## [0.1.0] - 2025-12-09

### Added
- Initial release of sc-ci-automation package
- `/sc-ci-automation` command with comprehensive flag support
- 7 specialized CI agents:
  - `ci-validate-agent`: Pre-flight checks (clean repo, config, auth)
  - `ci-pull-agent`: Pull target branch and handle merge conflicts
  - `ci-build-agent`: Run build and classify failures
  - `ci-test-agent`: Run tests and classify failures/warnings
  - `ci-fix-agent`: Apply straightforward fixes for build/test issues
  - `ci-root-cause-agent`: Analyze unresolved failures and recommend actions
  - `ci-pr-agent`: Commit, push, and create PR when gates pass
- Command flags:
  - `--build`: Pull + build only (skip tests/PR)
  - `--test`: Pull + build + test (skip commit/push/PR)
  - `--dest <branch>`: Override target branch for PR
  - `--src <branch>`: Override source branch/worktree
  - `--allow-warnings`: Allow warnings to pass quality gates
  - `--patch`: Increment patch version before building
  - `--yolo`: Auto-commit/push/PR after gates pass
  - `--help`: Show usage and examples
- Configuration file support (`.claude/ci-automation.yaml`)
- Auto-detection of project stack (.NET/Python/Node)
- Safety features:
  - Conservative mode by default (manual PR approval)
  - No force-push, respects protected branches
  - Warning gates block PR by default
  - Explicit confirmation for PRs to main/master
  - Audit logging via Agent Runner
- Comprehensive documentation:
  - README.md with quick start and examples
  - USE-CASES.md with practical workflows
  - TROUBLESHOOTING.md with common issues and solutions
- Integration with Agent Runner for registry-enforced, audited agent invocations

### Security
- All agent invocations logged to `.claude/state/logs/ci-automation/`
- No hardcoded credentials (uses environment variables)
- Safe defaults prevent accidental force-push or protected branch violations

[Unreleased]: https://github.com/randlee/synaptic-canvas/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/randlee/synaptic-canvas/releases/tag/v0.1.0
