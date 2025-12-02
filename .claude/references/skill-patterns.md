# Skill Patterns (starter archetypes)

## 1) GitHub Issue Skill
- Purpose: read/prioritize issues, generate fixes, open PRs.
- Command UX: one `/github-issue` command with flags:
  - `--list` (list issues)
  - `--fix --issue <id/url>` (automated fix), uses manage-worktree skill to create worktree from dev branch, then fix and open PR
  - `--yolo` (auto-pick easiest issue and run `--fix`)
  - `--repo` (default current)
  - `--create` (open issue)
  - `--update <id/description>` (update issue fields/body)
  - `--help`
- Agents:
  - `gh-issue-intake-agent`: fetch metadata/comments, summarize blockers.
  - `gh-issue-fix-agent`: propose/code a fix; returns fenced JSON with patch summary, risk, tests.
  - `gh-issue-pr-agent`: open PR with branch naming guardrails; ensures clean worktree via manage-worktree skill.
- Data contracts: fenced JSON minimal envelope; include `risk`, `tests`, `patch_summary`.
- Safety: no pushes without confirmation; branch/PR naming policies; worktree hygiene via manage-worktree skill.
- References: API schema snippets and response examples in separate reference files; keep SKILL.md lean.

## 2) Scaffolding Skill (template-driven software delivery)
- Purpose: scaffold an entire deliverable using templates/generators per chosen architecture.
- Command UX: `/scaffold-plan`, `/scaffold-generate`, `/scaffold-review`; options for `--arch`, `--template`, `--output`, `--dry-run`, `--help`.
- Agents:
  - `arch-select-agent`: validates requested architecture, lists supported stacks.
  - `template-apply-agent`: applies templates/generators, returns file operations and next steps.
  - `scaffold-review-agent`: checks generated structure against architecture rules.
- Data contracts: fenced JSON with `operations` (create/overwrite), `warnings`, `followups`.
- Safety: dry-run default; confirm overwrites; write outputs under user-specified path.
- Progressive disclosure: keep SKILL instructions short; detailed template guidance and architecture matrices live in references.
