# GitHub Issue Skill – Planning Request (v2)
Status: Draft
Owner: TBD
Last Updated: 2025-01-22

## Request
Generate a plan for a GitHub issue lifecycle skill that:
- Uses a single command `/github-issue` (frontmatter name `github-issue`, no leading slash) with default version 0.1.0 for command/skill/agents.
- Supports flags: `--list`, `--fix --issue <id/url>`, `--yolo`, `--repo <owner/repo>`, `--create`, `--update <id/description>`, `--help`.
- Uses manage-worktree for clean worktree creation/cleanup; base branch configurable via `.claude/config.yaml` (`base_branch`, `worktree_root`), default to `main` and repo-named worktree root if absent.
- Places reports at `.claude/reports/skill-reviews/` (fallback `.claude/.tmp/skill-reviews/`) and prompts/scratch at `.claude/.prompts/`.
- Requires references: `.claude/references/github-issue-apis.md`, `.claude/references/github-issue-checklists.md` (load on demand).
- Ensures fenced JSON outputs with minimal envelope; registry constraints include agents and manage-worktree dependency (`manage-worktree: "0.x"`).
- Keeps agent set minimal (intake/list, create/update, fix, PR) unless justified.

## Notes for /skill-plan
- Use the naming convention: file path `.claude/commands/<name>.md`, frontmatter name `<name>` (no slash), user invocation `/name`.
- Keep SKILL.md concise (<2KB) and lean on references.
- Do not create artifacts during planning; write a plan file only (Preliminary → Proposed → Approved).
- Plan status should transition after review; output 40–80 line overview with full plan path.
