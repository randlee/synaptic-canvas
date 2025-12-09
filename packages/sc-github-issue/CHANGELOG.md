# Changelog

All notable changes to the sc-github-issue package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2025-12-08

### Added - Initial Marketplace Release

This is the first marketplace release of `sc-github-issue`, migrated from project-level implementation (v0.1.0).

#### Features
- **Issue Operations**: List, create, update GitHub issues
- **Fix Workflow**: Automated fix implementation with worktree isolation
  - Fetch issue details
  - Create isolated worktree via `sc-git-worktree`
  - Implement fix with code analysis
  - Run tests (if configured)
  - Commit and push changes
  - Create PR with auto-linking
- **Four Specialized Agents**:
  - `sc-github-issue-intake`: List/fetch operations
  - `sc-github-issue-mutate`: Create/update operations
  - `sc-github-issue-fix`: Fix implementation
  - `sc-github-issue-pr`: PR creation
- **Safety Features**:
  - Pre-flight authentication checks
  - Approval gates (with `--yolo` bypass)
  - Test failure prompts
  - Protected branch integration
- **Configuration**: Manifest-based options (base-branch, branch-pattern, auto-pr)

#### Technical Details
- v0.4 fenced JSON output format with structured errors
- Install scope: `local-only` (project-specific)
- Dependencies:
  - `sc-git-worktree >= 0.6.0`
  - `gh >= 2.0`
- Naming conventions:
  - Command: `sc-github-issue` (gerund form)
  - Skill: `sc-managing-github-issues`
  - Agents: `sc-github-issue-*` prefix

#### Documentation
- Comprehensive README with examples
- TROUBLESHOOTING guide
- USE-CASES with practical workflows
- DEPENDENCIES explanation
- Reference files for GitHub CLI patterns and checklists

### Changed

- **Renamed from v0.1.0**:
  - Command: `github-issue` → `sc-github-issue`
  - Skill: `github-issue` → `sc-managing-github-issues`
  - Agents: `issue-*-agent` → `sc-github-issue-*`
- **Configuration Migration**:
  - From: `.claude/config.yaml` (global)
  - To: Manifest options with optional `.claude/config.yaml` overrides
- **Worktree Integration**:
  - Now uses `sc-git-worktree` skill (was `sc-managing-worktrees`)
  - Hard dependency on `sc-git-worktree >= 0.6.0`
  - Protected branch awareness

### Migration from v0.1.0

If you were using the project-level `github-issue` skill:

1. **Install package**: `sc-manage install sc-github-issue`
2. **Update command invocation**: `/github-issue` → `/sc-github-issue`
3. **Configuration**: Move settings from `.claude/config.yaml` to package-specific config:
   ```yaml
   packages:
     sc-github-issue:
       base-branch: "main"
       branch-pattern: "fix-issue-{number}"
   ```
4. **Remove old files** (optional):
   ```bash
   rm -rf .claude/commands/github-issue.md
   rm -rf .claude/skills/github-issue/
   rm -rf .claude/agents/issue-*-agent.md
   rm -rf .claude/references/github-issue-*.md
   ```

### Dependencies

- `sc-git-worktree`: Updated to v0.6.0 (includes protected branch safeguards)
- All Synaptic Canvas packages aligned at v0.6.0:
  - `sc-delay-tasks`: 0.6.0
  - `sc-manage`: 0.6.0
  - `sc-git-worktree`: 0.6.0
  - `sc-repomix-nuget`: 0.6.0

## [0.1.0] - 2025-12-03 (Project-Level Only)

### Added
- Initial implementation as project-level skill
- Basic issue operations (list, create, update)
- Fix workflow with worktree isolation
- Four agents for specialized operations
- GitHub CLI integration

### Notes
- This version was never released to the marketplace
- Served as proof of concept for v0.6.0 marketplace release
- Archived plans available in `plans/.archive/github-issue-skill*.md`

---

## Version Alignment

As of v0.6.0, all Synaptic Canvas packages follow unified versioning:

| Package | Version | Status |
|---------|---------|--------|
| sc-github-issue | 0.6.0 | ✅ Released |
| sc-git-worktree | 0.6.0 | ✅ Released |
| sc-delay-tasks | 0.6.0 | ✅ Released |
| sc-manage | 0.6.0 | ✅ Released |
| sc-repomix-nuget | 0.6.0 | ✅ Released |

## Future Plans

See [project roadmap](../../pm/plans/2025-12-04-ongoing-maintenance-backlog.md) for upcoming features and improvements.
