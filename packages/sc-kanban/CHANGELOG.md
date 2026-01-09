# Changelog

All notable changes to sc-kanban will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-01-XX

### Added
- Three-file lifecycle (backlog.json → board.json → done.json) with automatic card movement
- Shared board config (.project/board.config.yaml) with Pydantic v2 strict validation
- Provider abstraction supporting kanban (full features) and checklist (markdown fallback)
- **kanban-transition** agent with pr_url gate enforcement and status transitions
- **kanban-query** agent for filtering cards by status, sprint_id, or worktree
- **kanban-card** agent for create/update operations on cards
- **checklist-agent** fallback for markdown-based workflows (roadmap.md + prompts/)
- Automatic card scrubbing on review → done transition (preserves sprint_id, title, pr_url, completed_at, actual_cycles)
- WIP enforcement per column with configurable limits (active, review)
- v0.5 compliance: fenced JSON envelopes, versioned frontmatter, registry attestation
- Card schema with lean (backlog/done) and rich (board) variants
- Execution field tracking: pr_url, status_report, actual_cycles, started_at, completed_at, base_branch, max_retries
- Integration with sc-git-worktree via worktree naming conventions (`<project-branch>/<sprint-id>-<sprint-name>`)
- Core operations module: src/sc_kanban/board.py (scrub_card, transition_card, load/save operations)
- Board config models: src/sc_cli/board_config.py with Pydantic v2 validation
- Comprehensive test suite: test_board_config, test_kanban_board, test_checklist_agent, test_integration_provider_switch (85-95% coverage)
- Board config example template with all execution fields documented
- Command scaffolding: /kanban init, create, move, archive, list, status
- Skill orchestration: skills/sc-kanban/SKILL.md
- Agent documentation: kanban-transition.md, kanban-query.md, kanban-card.md, checklist-agent.md

### Changed
- N/A (initial v0.7.0 release)

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- Input validation via Pydantic v2 strict mode with `extra="forbid"` prevents field injection
- Path safety in file operations (backlog/board/done files)
- Fail-closed on config validation errors (invalid schema blocks all operations)
- Board config version enforcement (rejects mismatched versions)

## [Unreleased]

### Planned for v0.7.1
- Full gate execution suite: PR state validation, git cleanliness checks, worktree validation
- Enhanced error codes: GIT.DIRTY, GIT.NOT_PUSHED, PR.NOT_MERGED, WORKTREE.MISSING
- Parallel gate runner with timeout and concurrency controls
- Advanced query operations: rollups, dependency tracking, velocity metrics
- Template scaffolding wizard for initial board setup
- scripts/run_gates.py orchestration for comprehensive gate checks
- scripts/validate_worktrees.py for worktree existence verification
- scripts/validate_pr_state.py for PR merge status validation
