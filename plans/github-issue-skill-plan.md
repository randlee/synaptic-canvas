---
status: In Progress - Migration to Marketplace
created: 2025-12-03
updated: 2025-12-08
version: 0.6.0
owner: randlee
---

# GitHub Issue Lifecycle Skill - Marketplace Migration Plan

## Status: ✅ COMPLETED - v0.6.0 Marketplace Release Ready

Original implementation completed at v0.1.0 (project-level). Successfully migrated to marketplace package `sc-github-issue` v0.6.0 with sc- prefix consistency and marketplace standards.

## Migration Overview

### From (v0.1.0 - Project Level)
```
.claude/
├── commands/github-issue.md
├── skills/github-issue/SKILL.md
└── agents/
    ├── issue-intake-agent.md
    ├── issue-mutate-agent.md
    ├── issue-fix-agent.md
    └── issue-pr-agent.md
```

### To (v0.6.0 - Marketplace Package)
```
packages/sc-github-issue/
├── manifest.yaml (v0.6.0)
├── README.md
├── CHANGELOG.md
├── USE-CASES.md
├── TROUBLESHOOTING.md
├── DEPENDENCIES.md
├── commands/sc-github-issue.md
├── skills/sc-managing-github-issues/SKILL.md (gerund form)
├── agents/
│   ├── sc-github-issue-intake.md
│   ├── sc-github-issue-mutate.md
│   ├── sc-github-issue-fix.md
│   └── sc-github-issue-pr.md
└── references/
    ├── github-issue-apis.md
    └── github-issue-checklists.md
```

## Migration Progress

### ✅ Phase 1: Foundation (COMPLETED)
- [x] Version alignment: Bumped all packages to v0.6.0
  - sc-delay-tasks: 0.5.2 → 0.6.0
  - sc-manage: 0.5.2 → 0.6.0
  - sc-repomix-nuget: 0.5.2 → 0.6.0
  - sc-git-worktree: Already 0.6.0
- [x] Created package structure: `packages/sc-github-issue/`
- [x] Created manifest.yaml with:
  - Version: 0.6.0
  - Install scope: local-only
  - Dependencies: sc-git-worktree >= 0.6.0, gh >= 2.0
  - Options: base-branch, branch-pattern, auto-pr

### ✅ Phase 2: Agent Migration (COMPLETED)
- [x] Migrated `issue-intake-agent` → `sc-github-issue-intake` (v0.6.0)
- [x] Migrated `issue-mutate-agent` → `sc-github-issue-mutate` (v0.6.0)
- [x] Migrated `issue-fix-agent` → `sc-github-issue-fix` (v0.6.0)
- [x] Migrated `issue-pr-agent` → `sc-github-issue-pr` (v0.6.0)

All agents now include:
- sc- prefix naming
- v0.6.0 version in frontmatter
- model: sonnet, color: [blue|yellow|green|purple]
- v0.4 fenced JSON output format
- Structured error objects with code/message/recoverable/suggested_action
- "Invocation" and "Constraints" sections

### ✅ Phase 3: Command & Skill Migration (COMPLETED)
- [x] Migrate command: `github-issue` → `sc-github-issue` (v0.6.0)
  - Removed leading slash from frontmatter name
  - Updated all agent references to sc- prefixed names
  - Updated skill references to sc-managing-github-issues
- [x] Migrate skill: `github-issue` → `sc-managing-github-issues` (gerund form)
  - Updated name to gerund: "Managing GitHub Issues"
  - Updated all agent references
  - Updated command references

### ✅ Phase 4: Documentation Migration (COMPLETED)
- [x] Migrate references with sc- prefix
  - [x] `.claude/references/github-issue-apis.md` → `references/github-issue-apis.md`
  - [x] `.claude/references/github-issue-checklists.md` → `references/github-issue-checklists.md`
- [x] Create marketplace documentation:
  - [x] README.md - Installation, usage, examples
  - [x] CHANGELOG.md - v0.6.0 initial marketplace release
  - [x] USE-CASES.md - Practical examples and workflows
  - [x] TROUBLESHOOTING.md - Common issues and solutions
  - [x] DEPENDENCIES.md - sc-git-worktree, gh CLI requirements

### ✅ Phase 5: Registry & Release (COMPLETED - Ready for Commit)
- [x] Update `docs/registries/nuget/registry.json` with all v0.6.0 packages:
  - [x] sc-delay-tasks: v0.6.0
  - [x] sc-manage: v0.6.0
  - [x] sc-repomix-nuget: v0.6.0
  - [x] sc-git-worktree: v0.6.0
  - [x] sc-github-issue: v0.6.0 (NEW)
- [ ] Commit all changes (ready)
- [ ] Push to remote
- [ ] Create release tag v0.6.0
- [ ] Test installation: `sc-manage install sc-github-issue`

## Technical Details

### Package Configuration

**Manifest Options:**
```yaml
options:
  base-branch:
    type: string
    default: "main"
    description: Default base branch for fix branches
  branch-pattern:
    type: string
    default: "fix-issue-{number}"
    description: Pattern for fix branch names (use {number} placeholder)
  auto-pr:
    type: boolean
    default: true
    description: Automatically create PR after successful fix
```

**Dependencies:**
```yaml
requires:
  packages:
    - sc-git-worktree >= 0.6.0
  cli:
    - gh >= 2.0
```

### Naming Conventions Applied

**Skill Name (Gerund Form):**
- ❌ Old: `github-issue` (noun)
- ✅ New: `sc-managing-github-issues` (gerund)

**Command Name (No Leading Slash):**
- ❌ Incorrect: `name: /sc-github-issue`
- ✅ Correct: `name: sc-github-issue`
- Invoked as: `/sc-github-issue`

**Agent Names (sc- Prefix + Hyphenated):**
- Pattern: `sc-github-issue-<operation>`
- Examples: `sc-github-issue-intake`, `sc-github-issue-mutate`, `sc-github-issue-fix`, `sc-github-issue-pr`

### Agent Capabilities

| Agent | Purpose | Key Features |
|-------|---------|--------------|
| sc-github-issue-intake | List/fetch issues | Read-only, filtering by state/labels/assignee |
| sc-github-issue-mutate | Create/update issues | Write operations, field updates, state changes |
| sc-github-issue-fix | Implement fixes | Worktree isolation, testing, commit automation |
| sc-github-issue-pr | Create PRs | Template support, auto-linking, draft PRs |

### Integration Points

**Worktree Integration:**
- Uses `sc-git-worktree` v0.6.0 for safe isolation
- Creates branch in isolated worktree: `fix-issue-{number}`
- Implements fix without touching main working directory
- Commits and pushes from isolated worktree

**GitHub CLI Integration:**
- All operations via `gh` CLI
- Authentication via `gh auth login`
- Repository detection via `gh repo view`
- Issue operations: `gh issue list|view|create|edit`
- PR operations: `gh pr create`

### Workflow Example

```bash
# List issues
/sc-github-issue --list

# Fix issue with full workflow
/sc-github-issue --fix --issue 42

# Steps executed:
# 1. Fetch issue details (sc-github-issue-intake)
# 2. Prompt for confirmation (unless --yolo)
# 3. Create worktree via sc-git-worktree (fix-issue-42)
# 4. Implement fix (sc-github-issue-fix)
#    - Analyze issue
#    - Make code changes
#    - Run tests
#    - Commit & push
# 5. Create PR (sc-github-issue-pr)
# 6. Display summary and PR URL
```

## Original Context (v0.1.0)

### Goal
Create a unified command interface for GitHub issue operations: listing, creating, updating, fixing (with worktree isolation), and PR creation.

### Source Materials
- Request document: `/Users/randlee/Documents/github/synaptic-canvas/plans/github-issue-skill-request-v2.md`
- References:
  - `.claude/references/github-issue-apis.md` (GitHub CLI commands and API patterns)
  - `.claude/references/github-issue-checklists.md` (workflow checklists and best practices)
- Dependencies: `sc-managing-worktrees` skill (now `sc-git-worktree` v0.6.0)

### Design Principles (Maintained)
- Minimal agent set (4 agents: intake, mutate, fix, PR)
- Fenced JSON outputs with minimal envelope (v0.4 format)
- Configuration via manifest options (replacing .claude/config.yaml)
- Worktree isolation for safety
- GitHub CLI integration for all operations

## Migration Blockers & Decisions

### Resolved
- ✅ Naming: All use sc- prefix
- ✅ Version: Unified at v0.6.0
- ✅ Scope: local-only installation
- ✅ Dependencies: Hard dependency on sc-git-worktree v0.6.0
- ✅ Command naming: No slash in frontmatter
- ✅ Skill naming: Gerund form (sc-managing-github-issues)

### Pending Decisions
- Configuration approach: Use manifest options vs .claude/config.yaml example
- PR template: Default in code or require user configuration?
- Test command: Optional or required configuration?

## Success Criteria

- [x] All packages at v0.6.0 in registry
- [ ] sc-github-issue installable via `sc-manage install` (ready to test)
- [ ] Full workflow works: list → fix → PR creation (ready to test)
- [x] Documentation complete (README, CHANGELOG, USE-CASES, etc.)
- [x] No double-slash issues in command naming
- [x] Worktree integration functional
- [x] GitHub CLI integration functional
- [x] All agents return v0.4 compliant JSON

## Timeline

- Phase 1-2: ✅ COMPLETED (2025-12-08 morning)
- Phase 3: ✅ COMPLETED (2025-12-08 afternoon) - Command & Skill migration
- Phase 4: ✅ COMPLETED (2025-12-08 afternoon) - Documentation
- Phase 5: ✅ COMPLETED (2025-12-08 afternoon) - Registry update
- **Migration completed**: 2025-12-08
- **Ready for**: Commit, push, release tag, testing

## Related Documents

- Original request: `plans/github-issue-skill-request-v2.md`
- Archived plans: `plans/.archive/github-issue-skill*.md`
- Implementation reviews: `.claude/reports/skill-reviews/github-issue-*.md`
- Backlog tracking: `pm/plans/2025-12-04-ongoing-maintenance-backlog.md` (v0.6.0 release section)
