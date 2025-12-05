---
status: Approved
created: 2025-12-03
version: 0.1.0
owner: TBD
---

# GitHub Issue Lifecycle Skill - Implementation Plan

## Status: Approved

This plan defines the implementation for a GitHub issue lifecycle skill that manages issues from listing to fixing to PR creation, with clean worktree isolation via the manage-worktree skill.

## Context

### Goal
Create a new skill package (`github-issue`) version 0.1.0 that provides a unified command interface for GitHub issue operations: listing, creating, updating, fixing (with worktree isolation), and PR creation.

### Source Materials
- Request document: `/Users/randlee/Documents/github/synaptic-canvas/plans/github-issue-skill-request-v2.md`
- References:
  - `.claude/references/github-issue-apis.md` (GitHub CLI commands and API patterns)
  - `.claude/references/github-issue-checklists.md` (workflow checklists and best practices)
- Dependencies: `sc-managing-worktrees` skill (version 0.x) for branch/worktree operations

### Constraints
- Version 0.1.0 for all components (command, skill, agents)
- Minimal agent set (4 agents: intake/list, create/update, fix, PR)
- Lean SKILL.md (<2KB); delegate details to references
- Fenced JSON outputs with minimal envelope
- Configuration from `.claude/config.yaml` (base_branch, worktree_root)
- Reports to `.claude/reports/skill-reviews/` (fallback `.claude/.tmp/skill-reviews/`)

## User Experience

### Command Interface

**File**: `.claude/commands/github-issue.md`
**Frontmatter name**: `github-issue`
**User invocation**: `/github-issue`
**Version**: 0.1.0

#### Flags and Arguments

```
/github-issue [options]

Options:
  --list                    List open issues in repository
  --fix --issue <id/url>   Fix specified issue in isolated worktree
  --yolo                   Skip confirmation prompts (use with --fix)
  --repo <owner/repo>      Target repository (default: current repo)
  --create                 Create new issue interactively
  --update <id>            Update existing issue
  --help                   Show this help message

Examples:
  /github-issue --list
  /github-issue --list --repo owner/repo
  /github-issue --fix --issue 42
  /github-issue --fix --issue https://github.com/owner/repo/issues/42 --yolo
  /github-issue --create
  /github-issue --update 42
```

#### Default Behavior
- No flags or `--help`: display help text with examples
- `--list`: show open issues with numbers, titles, labels, assignees
- `--fix`: full workflow (fetch issue → confirm → create worktree → implement → test → commit → push → create PR)
- `--create`: interactive prompts for title, body, labels, assignees
- `--update`: interactive prompts for fields to update

### Configuration Integration

Load from `.claude/config.yaml`:
```yaml
base_branch: main                    # Base branch for worktrees (default: main)
worktree_root: ../worktrees          # Worktree root directory (default: ../repo-name-worktrees)

github:
  default_labels: []                 # Optional default labels for new issues
  auto_assign: false                 # Optional auto-assign to current user
  branch_pattern: "fix-issue-{number}"  # Branch naming pattern
  test_command: null                 # Optional test command (e.g., "npm test")
  pr_template: |                     # Optional PR body template
    ## Summary
    Fixes #{issue_number}
```

If `.claude/config.yaml` doesn't exist, use defaults:
- `base_branch`: `main`
- `worktree_root`: `../<repo-name>-worktrees`

## Architecture

### Agent Set (Minimal)

1. **issue-intake-agent** (v0.1.0)
   - Role: List issues, fetch single issue details
   - Operations: --list, initial fetch for --fix

2. **issue-mutate-agent** (v0.1.0)
   - Role: Create and update issues
   - Operations: --create, --update

3. **issue-fix-agent** (v0.1.0)
   - Role: Implement fix in isolated worktree
   - Operations: --fix workflow (setup → implement → test → commit)

4. **issue-pr-agent** (v0.1.0)
   - Role: Create PR from fix branch
   - Operations: Final step of --fix workflow

### Agent Delegation Pattern

Use Agent Runner with registry resolution:
```
Invoke Agent Runner with:
  agent: "<agent-name>"
  registry: .claude/agents/registry.yaml
  params: { ... }
```

### Skill Dependencies

In `.claude/agents/registry.yaml`:
```yaml
skills:
  github-issue:
    depends_on:
      issue-intake-agent: 0.x
      issue-mutate-agent: 0.x
      issue-fix-agent: 0.x
      issue-pr-agent: 0.x
      sc-managing-worktrees: 0.x
```

## Data Contracts

### Minimal Envelope Structure

All agents return fenced JSON with minimal envelope:
```json
{
  "success": true|false,
  "data": { /* agent-specific data */ },
  "error": null|"error message"
}
```

### Agent Inputs/Outputs

#### 1. issue-intake-agent

**Input**:
```json
{
  "operation": "list|fetch",
  "repo": "owner/repo",
  "issue_number": null|42,
  "filters": {
    "state": "open|closed|all",
    "labels": [],
    "assignee": null
  }
}
```

**Output**:
```json
{
  "success": true,
  "data": {
    "operation": "list|fetch",
    "issues": [
      {
        "number": 42,
        "title": "Issue title",
        "state": "open",
        "labels": ["bug"],
        "assignees": ["user1"],
        "url": "https://github.com/owner/repo/issues/42"
      }
    ]
  },
  "error": null
}
```

#### 2. issue-mutate-agent

**Input**:
```json
{
  "operation": "create|update",
  "repo": "owner/repo",
  "issue_number": null|42,
  "fields": {
    "title": "Issue title",
    "body": "Description",
    "labels": ["bug"],
    "assignees": ["user1"],
    "state": "open|closed"
  }
}
```

**Output**:
```json
{
  "success": true,
  "data": {
    "operation": "create|update",
    "issue_number": 42,
    "url": "https://github.com/owner/repo/issues/42",
    "updated_fields": ["title", "labels"]
  },
  "error": null
}
```

#### 3. issue-fix-agent

**Input**:
```json
{
  "issue_number": 42,
  "repo": "owner/repo",
  "yolo": false,
  "config": {
    "base_branch": "main",
    "worktree_root": "../worktrees",
    "branch_pattern": "fix-issue-{number}",
    "test_command": null|"npm test"
  }
}
```

**Output**:
```json
{
  "success": true,
  "data": {
    "issue_number": 42,
    "branch": "fix-issue-42",
    "worktree_path": "/path/to/worktree",
    "commits": [
      {
        "sha": "abc123",
        "message": "Fix #42: Issue title"
      }
    ],
    "tests_passed": true,
    "files_changed": ["src/file.ts", "tests/file.test.ts"]
  },
  "error": null
}
```

#### 4. issue-pr-agent

**Input**:
```json
{
  "issue_number": 42,
  "repo": "owner/repo",
  "branch": "fix-issue-42",
  "base_branch": "main",
  "pr_template": null|"## Summary\nFixes #{issue_number}"
}
```

**Output**:
```json
{
  "success": true,
  "data": {
    "pr_number": 123,
    "url": "https://github.com/owner/repo/pull/123",
    "title": "Fix #42: Issue title",
    "state": "open",
    "draft": false
  },
  "error": null
}
```

## File Layout

```
.claude/
├── commands/
│   └── github-issue.md                     # Command interface (v0.1.0)
├── skills/
│   └── github-issue/
│       └── SKILL.md                         # Skill definition (v0.1.0, <2KB)
├── agents/
│   ├── registry.yaml                        # Updated with new agents + dependency
│   ├── issue-intake-agent.md               # v0.1.0
│   ├── issue-mutate-agent.md               # v0.1.0
│   ├── issue-fix-agent.md                  # v0.1.0
│   └── issue-pr-agent.md                   # v0.1.0
├── references/
│   ├── github-issue-apis.md                # Already exists
│   └── github-issue-checklists.md          # Already exists
├── reports/
│   └── skill-reviews/                       # Review reports (create if missing)
└── .tmp/
    └── skill-reviews/                       # Fallback for reports

.claude/.prompts/                            # Scratch/prompt files (create if missing)
```

## Implementation Workflows

### --list Workflow
1. Command validates `--repo` or detects current repo
2. Invokes `issue-intake-agent` with operation=list
3. Agent executes `gh issue list --json ...`
4. Returns fenced JSON with issue list
5. Command formats and displays issues

### --create Workflow
1. Command prompts for title (required), body, labels, assignees
2. Invokes `issue-mutate-agent` with operation=create
3. Agent executes `gh issue create ...`
4. Returns fenced JSON with created issue
5. Command displays issue URL

### --update Workflow
1. Command prompts for fields to update
2. Invokes `issue-mutate-agent` with operation=update
3. Agent executes `gh issue edit ...`
4. Returns fenced JSON with updated fields
5. Command displays confirmation

### --fix Workflow (Full Lifecycle)

**Phase 1: Intake & Confirmation**
1. Invoke `issue-intake-agent` to fetch issue details
2. Display issue summary to user
3. If not `--yolo`, prompt for confirmation
4. Load config from `.claude/config.yaml` (or use defaults)

**Phase 2: Worktree Setup**
5. Generate branch name from pattern (e.g., `fix-issue-42`)
6. Invoke `sc-worktree-create` agent from `sc-managing-worktrees` skill:
   ```json
   {
     "branch": "fix-issue-42",
     "base": "main",
     "path": null
   }
   ```
7. Verify worktree created successfully

**Phase 3: Implementation**
8. Invoke `issue-fix-agent` with:
   - Issue details
   - Worktree path
   - Test command (if configured)
9. Agent:
   - Changes to worktree directory
   - Analyzes issue and identifies affected files
   - Implements fix using code tools
   - Runs tests if configured
   - Stages changes: `git add .`
   - Commits with message: `Fix #42: <issue title>`
   - Pushes to remote: `git push -u origin <branch>`

**Phase 4: PR Creation**
10. Invoke `issue-pr-agent` with:
    - Issue number
    - Branch name
    - Base branch
    - PR template (if configured)
11. Agent executes `gh pr create ...`
12. Returns fenced JSON with PR URL

**Phase 5: Cleanup**
13. Return to original directory
14. Display summary: issue, branch, commits, tests, PR URL

## Safety and Approval Gates

### Pre-Flight Checks
- Verify `gh` CLI installed and authenticated
- Validate repository access
- Confirm working directory

### Approval Gates
1. **Before creating worktree** (unless `--yolo`):
   - Display issue title, body, labels
   - Prompt: "Proceed with fix for issue #42? (y/n)"

2. **If tests fail**:
   - Display test output
   - Prompt: "Tests failed. Proceed anyway? (y/n)"

3. **Before cleanup** (sc-worktree-cleanup):
   - Verify no uncommitted changes
   - Prompt for explicit approval if dirty

### Error Handling
- Authentication failure → guide user to `gh auth login`
- Rate limit → display reset time, suggest retry
- Permission denied → verify repo access
- Worktree dirty → abort and request cleanup
- Push failure → display git error, suggest manual resolution

## Integration Points

### sc-managing-worktrees Skill
- Use `sc-worktree-create` for branch/worktree setup
- Use `sc-worktree-cleanup` for post-PR cleanup (optional)
- Use `sc-worktree-abort` if user cancels mid-fix

### GitHub CLI
- All operations use `gh` CLI with `--json` flag
- Reference `.claude/references/github-issue-apis.md` for commands
- Follow checklists in `.claude/references/github-issue-checklists.md`

### Configuration
- Load `.claude/config.yaml` for base_branch, worktree_root, github settings
- Fall back to sensible defaults if config missing

## Success Criteria

### Functional Requirements
- [x] Single command `/github-issue` with all specified flags
- [x] List issues with filtering
- [x] Create and update issues interactively
- [x] Fix issues in isolated worktrees with full lifecycle
- [x] Create PRs with proper issue references
- [x] Support `--yolo` for automated workflows
- [x] Repository parameter (`--repo`) or auto-detect

### Quality Requirements
- [x] Fenced JSON outputs with minimal envelope
- [x] SKILL.md under 2KB (lean on references)
- [x] All agents return structured data
- [x] Progressive disclosure (help → list → fix)
- [x] Safety gates for destructive operations
- [x] Error handling with actionable messages

### Integration Requirements
- [x] manage-worktree dependency in registry
- [x] Configuration from `.claude/config.yaml`
- [x] Reports to `.claude/reports/skill-reviews/`
- [x] References loaded on demand

## Use Cases

### UC1: List Open Issues
```bash
/github-issue --list
# Displays: #42 [bug] Application crashes on startup (@user1)
```

### UC2: Fix Issue with Confirmation
```bash
/github-issue --fix --issue 42
# → Displays issue summary
# → Prompts for confirmation
# → Creates worktree: fix-issue-42
# → Implements fix
# → Runs tests
# → Commits: "Fix #42: Application crashes on startup"
# → Pushes to remote
# → Creates PR: "Fix #42: Application crashes on startup"
# → Displays PR URL
```

### UC3: Automated Fix (CI/CD)
```bash
/github-issue --fix --issue 42 --yolo
# → No confirmation prompts
# → Full workflow automated
# → Returns JSON with PR URL
```

### UC4: Create Issue
```bash
/github-issue --create
# → Prompts for title: "Add dark mode support"
# → Prompts for body: "Users request dark mode option in settings"
# → Prompts for labels: "enhancement"
# → Creates issue
# → Displays: Created #43: https://github.com/owner/repo/issues/43
```

### UC5: Update Issue
```bash
/github-issue --update 42
# → Prompts for fields to update
# → Updates title, labels, or assignees
# → Displays confirmation
```

## Open Questions

1. **Test failure handling**: If tests fail during --fix, should we:
   - Abort and clean up worktree?
   - Commit anyway with note in PR?
   - Create draft PR?
   - **Recommendation**: Prompt user with options (unless --yolo, then create draft PR)

2. **Multi-file fixes**: For complex issues spanning many files:
   - Should agent attempt full fix automatically?
   - Should it create skeleton/TODO comments for user to complete?
   - **Recommendation**: Attempt full fix; if uncertain, add TODO comments and mark PR as draft

3. **Issue assignment**: Should --fix auto-assign issue to current user?
   - **Recommendation**: Yes, if `github.auto_assign: true` in config

4. **Branch cleanup**: After PR merged, should we auto-cleanup worktree?
   - **Recommendation**: No, leave to manual `/sc-git-worktree --cleanup` or separate automation

5. **Repository detection**: How to detect current repo if `--repo` not provided?
   - **Recommendation**: Use `gh repo view --json nameWithOwner -q .nameWithOwner`

## Next Actions

1. Review plan with stakeholders
2. Transition status: Preliminary → Proposed → Approved
3. Once approved, run `/skill-create --plan plans/github-issue-skill-plan.md`
4. Create all artifacts per file layout
5. Update registry with agents and dependencies
6. Test workflows with sample issues
7. Review with `/skill-review --target github-issue`

## Version History

- **0.1.0** (2025-12-03): Initial plan created (Preliminary)
- **0.1.0** (2025-12-03): Plan approved after review
