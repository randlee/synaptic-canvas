# GitHub Issue Lifecycle Skill – Plan
Status: Preliminary
Owner: TBD
Last Updated: 2025-12-03

## Context & Scope

Build a comprehensive GitHub issue lifecycle management skill that integrates with the existing `managing-worktrees` skill to provide a seamless developer workflow from issue discovery through fix implementation and PR creation.

### Goals

- Provide unified interface for GitHub issue operations: list, create, update, and fix
- Integrate cleanly with worktree management for isolated fix development
- Support both interactive and automated workflows (via `--yolo` flag)
- Enforce v0.4 guidelines with structured JSON outputs and registry-based agent resolution
- Enable progressive disclosure: lean command/skill, rich references loaded on demand

### Version Strategy

- Command: 0.1.0
- Skill: 0.1.0
- All agents: 0.1.0
- Registry constraints: depend on `managing-worktrees` skill agents (1.x)

## References

- Guidelines: `docs/claude-code-skills-agents-guidelines-0.4.md`
- Existing skill pattern: `.claude/skills/managing-worktrees/SKILL.md`
- GitHub CLI documentation: [https://cli.github.com/manual/gh_issue](https://cli.github.com/manual/gh_issue)
- GitHub REST API: [https://docs.github.com/en/rest/issues](https://docs.github.com/en/rest/issues)

## Use Cases

### UC1: List Issues
**User intent**: See what issues exist in the repository
**Command**: `/github-issue --list`
**Flow**:
1. User invokes command with `--list` flag
2. Skill delegates to `issue-list-agent` with repo context
3. Agent fetches issues via `gh` CLI
4. Returns structured JSON with issue list
5. Skill formats and presents table to user

**Output**: Table of issues with ID, title, state, labels, assignee

### UC2: Create Issue
**User intent**: Report a bug or request a feature
**Command**: `/github-issue --create`
**Flow**:
1. User invokes command with `--create` flag
2. Skill prompts for: title, body, labels (optional), assignees (optional)
3. Skill delegates to `issue-create-agent` with collected data
4. Agent creates issue via `gh` CLI
5. Returns structured JSON with new issue details
6. Skill confirms creation and shows issue URL

**Output**: Confirmation with issue number and URL

### UC3: Update Issue
**User intent**: Modify issue description, labels, or state
**Command**: `/github-issue --update 42 "Updated description"` or `/github-issue --update 42`
**Flow**:
1. User invokes with issue ID and optional description
2. If no description provided, prompt for what to update (title/body/state/labels)
3. Skill delegates to `issue-update-agent` with issue ID and changes
4. Agent updates via `gh` CLI
5. Returns structured JSON with updated issue details
6. Skill confirms update

**Output**: Confirmation with updated fields

### UC4: Fix Issue (Primary Workflow)
**User intent**: Implement a fix for an issue in isolated environment
**Command**: `/github-issue --fix --issue 42` or `/github-issue --fix --issue https://github.com/owner/repo/issues/42`
**Flow**:
1. User invokes with issue identifier (number or URL)
2. Skill fetches issue details via `issue-fetch-agent`
3. Skill displays issue summary and asks for confirmation (skip if `--yolo`)
4. Skill invokes `worktree-create` agent to create clean worktree
   - Branch name: `fix-issue-42` or user-specified
   - Base: from config (default: main) or user-specified
5. Skill delegates to `issue-fix-agent` with:
   - Issue details
   - Worktree path
   - Implementation guidelines
6. Agent implements fix, runs tests, commits changes
7. Agent returns structured JSON with fix summary
8. Skill delegates to `pr-create-agent` with:
   - Branch name
   - Issue reference
   - Fix summary
9. Agent creates PR via `gh` CLI with proper issue references (Fixes #42)
10. Skill presents PR URL and summary

**Output**: PR created with link, worktree location, next steps

### UC5: Quick Fix with Auto-Proceed
**User intent**: Fix simple issue without interactive prompts
**Command**: `/github-issue --fix --issue 42 --yolo`
**Flow**: Same as UC4 but skips all confirmation prompts

**Output**: Direct execution to PR creation

## Command UX Design

### Command Metadata

```yaml
---
name: github-issue
version: 0.1.0
description: >
  Manage GitHub issue lifecycle: list, create, update, and fix issues with
  integrated worktree management. Use when user mentions "github issue",
  "fix bug", "create issue", "update issue", or needs issue workflow automation.
---
```

### Flags and Arguments

#### Primary Operations (mutually exclusive)
- `--list`: List issues in repository
- `--create`: Create new issue (interactive)
- `--update <id> [description]`: Update existing issue
- `--fix --issue <id|url>`: Implement fix for issue in clean worktree

#### Modifiers
- `--issue <id|url>`: Issue identifier (required with `--fix`)
- `--repo <owner/repo>`: Target repository (default: current repo)
- `--yolo`: Skip all confirmation prompts, auto-proceed with safe defaults
- `--help`: Show help text with examples

#### Configuration (from `.claude/config.yaml`)
- `base_branch`: Default base branch (fallback: main)
- `worktree_root`: Worktree base path (fallback: `../<repo-name>-worktrees`)
- `github.default_labels`: Default labels for created issues
- `github.auto_assign`: Auto-assign issues to current user (default: false)

### Help Text

```
/github-issue - Manage GitHub issue lifecycle

Usage:
  /github-issue --list [--repo owner/repo]
  /github-issue --create
  /github-issue --update <id> [description]
  /github-issue --fix --issue <id|url> [--yolo]

Operations:
  --list              List open issues in repository
  --create            Create new issue (interactive)
  --update <id>       Update issue description, state, or labels
  --fix --issue <id>  Create worktree, implement fix, create PR

Options:
  --repo <owner/repo>  Target repository (default: current repo)
  --issue <id|url>     Issue identifier (number or full URL)
  --yolo               Skip confirmations, auto-proceed
  --help               Show this help

Examples:
  /github-issue --list
  /github-issue --create
  /github-issue --update 42 "Updated description"
  /github-issue --fix --issue 42
  /github-issue --fix --issue https://github.com/owner/repo/issues/42 --yolo

Configuration (.claude/config.yaml):
  base_branch: main           # Default base branch
  worktree_root: ../worktrees # Worktree base path
  github:
    default_labels: []        # Default labels for new issues
    auto_assign: false        # Auto-assign to current user
```

### Default Behavior (No Flags)

When invoked without flags: `/github-issue`
1. Display concise menu of operations
2. Present numbered choices: [1] List, [2] Create, [3] Update, [4] Fix
3. Collect required inputs for chosen operation
4. Proceed with operation

### Flag Validation

**Validation rules**:
- Exactly one primary operation flag required (--list, --create, --update, --fix)
- `--issue` required when using `--fix`
- `--update` requires issue ID as first argument
- `--repo` format must be `owner/repo` if provided
- `--yolo` only valid with `--fix` (ignored for other operations)

**Error messages**:
```
❌ Error: Exactly one operation (--list, --create, --update, --fix) required
❌ Error: --fix requires --issue <id|url>
❌ Error: --update requires issue ID: /github-issue --update <id>
❌ Error: Invalid repo format. Use: owner/repo
```

## Agent Architecture

### Agent Inventory

| Agent | Version | Responsibility | Returns |
|-------|---------|----------------|---------|
| `issue-list-agent` | 0.1.0 | Fetch and format issue list | JSON: issues array |
| `issue-fetch-agent` | 0.1.0 | Fetch single issue details | JSON: issue object |
| `issue-create-agent` | 0.1.0 | Create new issue | JSON: created issue |
| `issue-update-agent` | 0.1.0 | Update existing issue | JSON: updated issue |
| `issue-fix-agent` | 0.1.0 | Implement fix in worktree | JSON: fix summary |
| `pr-create-agent` | 0.1.0 | Create PR from branch | JSON: PR details |

### Agent Delegation Strategy

**Invocation pattern** (all agents):
```markdown
Use the Agent Runner to invoke `<agent-name>` as defined in
`.claude/agents/registry.yaml` with parameters:
- param1: value1
- param2: value2
```

### Agent 1: issue-list-agent

**Purpose**: Fetch and return list of issues from repository

**Inputs**:
- `repo` (string, optional): Repository in `owner/repo` format (default: current repo)
- `state` (string, optional): Issue state filter: "open", "closed", "all" (default: "open")
- `labels` (string[], optional): Filter by labels
- `limit` (integer, optional): Maximum issues to return (default: 30)

**Execution Steps**:
1. Validate repository context (use current if not specified)
2. Build `gh issue list` command with filters
3. Execute command and parse JSON output
4. Transform to standardized format
5. Return fenced JSON

**Output Format**:
```json
{
  "success": true,
  "data": {
    "repository": "owner/repo",
    "issues": [
      {
        "number": 42,
        "title": "Bug: Application crashes on startup",
        "state": "open",
        "labels": ["bug", "priority-high"],
        "assignees": ["user1"],
        "url": "https://github.com/owner/repo/issues/42",
        "created_at": "2025-12-01T10:00:00Z",
        "updated_at": "2025-12-02T15:30:00Z"
      }
    ],
    "count": 1
  },
  "error": null
}
```

**Error Handling**:
- **Handled**: Network timeouts (retry 2x), invalid repo (suggest correction)
- **Propagated**: Authentication failures, permission denied

**Constraints**:
- Read-only operation
- No modifications to repository state
- Respects GitHub rate limits

### Agent 2: issue-fetch-agent

**Purpose**: Fetch detailed information for a single issue

**Inputs**:
- `issue` (string, required): Issue number or full URL
- `repo` (string, optional): Repository in `owner/repo` format (default: current repo)

**Execution Steps**:
1. Parse issue identifier (extract number from URL if needed)
2. Validate repository context
3. Execute `gh issue view <number> --json <fields>`
4. Return fenced JSON

**Output Format**:
```json
{
  "success": true,
  "data": {
    "number": 42,
    "title": "Bug: Application crashes on startup",
    "body": "Detailed description...",
    "state": "open",
    "labels": ["bug", "priority-high"],
    "assignees": ["user1"],
    "milestone": "v1.2.0",
    "url": "https://github.com/owner/repo/issues/42",
    "created_at": "2025-12-01T10:00:00Z",
    "updated_at": "2025-12-02T15:30:00Z",
    "comments_count": 3
  },
  "error": null
}
```

**Error Handling**:
- **Handled**: Issue not found (suggest similar), invalid format (parse and retry)
- **Propagated**: Permission denied, repository not accessible

### Agent 3: issue-create-agent

**Purpose**: Create new issue in repository

**Inputs**:
- `title` (string, required): Issue title
- `body` (string, optional): Issue description
- `labels` (string[], optional): Labels to apply
- `assignees` (string[], optional): Users to assign
- `milestone` (string, optional): Milestone name or number
- `repo` (string, optional): Repository (default: current)

**Execution Steps**:
1. Validate required inputs (title)
2. Build `gh issue create` command with options
3. Execute command
4. Parse created issue details
5. Return fenced JSON

**Output Format**:
```json
{
  "success": true,
  "data": {
    "number": 43,
    "title": "Feature: Add dark mode",
    "url": "https://github.com/owner/repo/issues/43",
    "created_at": "2025-12-03T12:00:00Z"
  },
  "error": null
}
```

**Error Handling**:
- **Handled**: Invalid labels (create or skip), invalid assignees (skip)
- **Propagated**: Permission denied, repository read-only

**Constraints**:
- Requires write access to repository
- Validates labels exist or creates them
- No destructive operations

### Agent 4: issue-update-agent

**Purpose**: Update existing issue properties

**Inputs**:
- `issue` (string, required): Issue number
- `title` (string, optional): New title
- `body` (string, optional): New body
- `state` (string, optional): "open" or "closed"
- `labels` (string[], optional): Labels to set (replaces existing)
- `add_labels` (string[], optional): Labels to add
- `remove_labels` (string[], optional): Labels to remove
- `assignees` (string[], optional): Assignees to set
- `repo` (string, optional): Repository (default: current)

**Execution Steps**:
1. Validate issue exists
2. Build `gh issue edit` command with updates
3. Execute command
4. Fetch updated issue details
5. Return fenced JSON

**Output Format**:
```json
{
  "success": true,
  "data": {
    "number": 42,
    "updated_fields": ["body", "labels"],
    "url": "https://github.com/owner/repo/issues/42"
  },
  "error": null
}
```

**Error Handling**:
- **Handled**: Invalid labels (skip), issue already in target state (no-op)
- **Propagated**: Issue not found, permission denied

### Agent 5: issue-fix-agent

**Purpose**: Implement fix for issue in provided worktree

**Inputs**:
- `issue_number` (integer, required): Issue to fix
- `issue_title` (string, required): Issue title for context
- `issue_body` (string, required): Issue description for context
- `worktree_path` (string, required): Path to worktree for implementation
- `branch_name` (string, required): Branch name for commits
- `test_command` (string, optional): Command to run tests (default: none)
- `validate_only` (boolean, optional): Dry-run mode (default: false)

**Execution Steps**:
1. Validate worktree path exists and is clean
2. Change to worktree directory
3. Analyze issue and plan fix approach
4. Implement fix using appropriate tools
5. If `test_command` provided, run tests
6. Stage changes: `git add .`
7. Commit with message: `Fix #<issue_number>: <issue_title>`
8. Push branch: `git push -u origin <branch_name>`
9. Return fenced JSON with fix summary

**Output Format**:
```json
{
  "success": true,
  "data": {
    "issue_number": 42,
    "branch_name": "fix-issue-42",
    "worktree_path": "/path/to/worktrees/fix-issue-42",
    "files_changed": ["src/app.py", "tests/test_app.py"],
    "commit_sha": "abc123...",
    "tests_passed": true,
    "fix_summary": "Fixed null pointer exception by adding validation"
  },
  "error": null,
  "metadata": {
    "duration_ms": 45000,
    "tool_calls": 12,
    "retry_count": 0
  }
}
```

**Error Handling**:
- **Handled**: Test failures (report, don't commit), merge conflicts (report)
- **Propagated**: Worktree dirty, permission issues, push failures

**Constraints**:
- Never force-push
- Never commit to protected branches directly
- Requires clean worktree to start
- Must run in worktree context (not main repo)

**Safety**:
- Requires explicit approval if tests fail (unless `--yolo`)
- Reports but doesn't auto-fix complex issues
- Provides rollback instructions if push fails

### Agent 6: pr-create-agent

**Purpose**: Create pull request from branch with issue references

**Inputs**:
- `branch_name` (string, required): Branch containing changes
- `base_branch` (string, required): Target branch for PR
- `issue_number` (integer, required): Issue being fixed
- `title` (string, optional): PR title (default: "Fix #<issue>: <issue_title>")
- `body` (string, optional): PR description (default: generated from commits)
- `draft` (boolean, optional): Create as draft PR (default: false)
- `auto_merge` (boolean, optional): Enable auto-merge (default: false)
- `repo` (string, optional): Repository (default: current)

**Execution Steps**:
1. Validate branch exists and is pushed
2. Fetch issue details for reference
3. Build PR title and body with proper issue references
4. Execute `gh pr create` with options
5. If `auto_merge`, enable auto-merge
6. Return fenced JSON with PR details

**Output Format**:
```json
{
  "success": true,
  "data": {
    "pr_number": 123,
    "pr_url": "https://github.com/owner/repo/pull/123",
    "title": "Fix #42: Application crashes on startup",
    "state": "open",
    "draft": false,
    "auto_merge_enabled": false,
    "linked_issues": [42]
  },
  "error": null
}
```

**Error Handling**:
- **Handled**: No changes to PR (report), conflicts detected (report)
- **Propagated**: Branch not found, permission denied, base branch invalid

**Constraints**:
- Requires pushed branch
- Must reference issue in title or body
- No force-push after PR creation

## Data Contracts

### Common Response Envelope

All agents return minimal envelope for simple operations:

```json
{
  "success": true,
  "data": { /* agent-specific data */ },
  "error": null
}
```

For operations requiring metadata (fix-agent, pr-create-agent), use standard envelope:

```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": { /* agent-specific data */ },
  "error": null,
  "metadata": {
    "duration_ms": 0,
    "tool_calls": 0,
    "retry_count": 0
  }
}
```

### Error Response Format

```json
{
  "success": false,
  "canceled": false,
  "data": null,
  "error": {
    "code": "GITHUB.PERMISSION_DENIED",
    "message": "Insufficient permissions to create issue in repository",
    "recoverable": false,
    "suggested_action": "Request write access to repository or authenticate with gh auth login"
  }
}
```

### Error Code Taxonomy

**Namespace: GITHUB**
- `GITHUB.NOT_FOUND`: Issue/repo/branch not found
- `GITHUB.PERMISSION_DENIED`: Insufficient permissions
- `GITHUB.AUTHENTICATION_FAILED`: Not authenticated or token expired
- `GITHUB.RATE_LIMIT`: API rate limit exceeded
- `GITHUB.NETWORK_ERROR`: Network connectivity issues
- `GITHUB.INVALID_INPUT`: Malformed input data
- `GITHUB.CONFLICT`: Resource conflict (e.g., branch exists)

**Namespace: WORKTREE**
- `WORKTREE.DIRTY`: Worktree has uncommitted changes
- `WORKTREE.NOT_FOUND`: Worktree path doesn't exist
- `WORKTREE.CREATION_FAILED`: Failed to create worktree

**Namespace: EXECUTION**
- `EXECUTION.TIMEOUT`: Operation exceeded timeout
- `EXECUTION.TEST_FAILURE`: Tests failed during fix
- `EXECUTION.VALIDATION_FAILED`: Input validation failed

## File Layout

### Commands
```
.claude/commands/
└── github-issue.md          # Command definition with flags and help text
```

### Skills
```
.claude/skills/
└── github-issue/
    ├── SKILL.md             # Main skill orchestration (<2KB)
    └── workflows.md         # Detailed workflow documentation (optional reference)
```

### Agents
```
.claude/agents/
├── issue-list-agent.md      # List issues
├── issue-fetch-agent.md     # Fetch single issue
├── issue-create-agent.md    # Create issue
├── issue-update-agent.md    # Update issue
├── issue-fix-agent.md       # Implement fix
└── pr-create-agent.md       # Create PR
```

### References (load on demand)
```
.claude/references/
├── github-issue-apis.md            # GitHub CLI and API reference
└── github-issue-checklists.md      # Workflow checklists and best practices
```

### Configuration
```
.claude/config.yaml              # Repository configuration
```

Example config:
```yaml
base_branch: main
worktree_root: ../synaptic-canvas-worktrees

github:
  default_labels:
    - bug
    - enhancement
  auto_assign: false
  default_reviewers: []
  pr_template: |
    ## Summary
    Fixes #{issue_number}

    ## Changes
    - Change 1
    - Change 2

    ## Testing
    - [ ] Tests pass
    - [ ] Manual testing completed
```

### Reports and Logs
```
.claude/reports/skill-reviews/
└── github-issue-report.md       # Skill review report (when using /skill-review)

.claude/.tmp/skill-reviews/      # Fallback location

.claude/.prompts/                # Scratch/temp prompts
```

### Registry
```
.claude/agents/
└── registry.yaml                # Agent version registry + dependencies
```

## Registry Constraints

Update `.claude/agents/registry.yaml`:

```yaml
agents:
  # Existing agents
  skill-planning-agent:
    version: 0.1.0
    path: .claude/agents/skill-planning-agent.md
  skill-review-agent:
    version: 0.1.0
    path: .claude/agents/skill-review-agent.md

  # Worktree management agents (dependency)
  worktree-create:
    version: 1.0.0
    path: .claude/agents/worktree-create.md
  worktree-scan:
    version: 1.0.0
    path: .claude/agents/worktree-scan.md
  worktree-cleanup:
    version: 1.0.0
    path: .claude/agents/worktree-cleanup.md
  worktree-abort:
    version: 1.0.0
    path: .claude/agents/worktree-abort.md

  # GitHub issue agents (new)
  issue-list-agent:
    version: 0.1.0
    path: .claude/agents/issue-list-agent.md
  issue-fetch-agent:
    version: 0.1.0
    path: .claude/agents/issue-fetch-agent.md
  issue-create-agent:
    version: 0.1.0
    path: .claude/agents/issue-create-agent.md
  issue-update-agent:
    version: 0.1.0
    path: .claude/agents/issue-update-agent.md
  issue-fix-agent:
    version: 0.1.0
    path: .claude/agents/issue-fix-agent.md
  pr-create-agent:
    version: 0.1.0
    path: .claude/agents/pr-create-agent.md

skills:
  skill-creation:
    depends_on:
      skill-planning-agent: 0.x
      skill-review-agent: 0.x

  managing-worktrees:
    depends_on:
      worktree-create: 1.x
      worktree-scan: 1.x
      worktree-cleanup: 1.x
      worktree-abort: 1.x

  github-issue:
    depends_on:
      # GitHub issue operations
      issue-list-agent: 0.x
      issue-fetch-agent: 0.x
      issue-create-agent: 0.x
      issue-update-agent: 0.x
      issue-fix-agent: 0.x
      pr-create-agent: 0.x
      # Worktree management (for --fix workflow)
      worktree-create: 1.x
      worktree-cleanup: 1.x
```

## Progressive Disclosure

### SKILL.md Structure (~1.5KB)

Keep SKILL.md lean and focused on orchestration:

1. **Agent Delegation Table**: Quick reference for which agent handles what
2. **Basic Workflow**: High-level steps for each operation
3. **References**: Point to detailed documentation

Detailed content moved to references:
- `github-issue-apis.md`: GitHub CLI commands, API endpoints, authentication
- `github-issue-checklists.md`: Workflow checklists, error recovery, best practices

### Loading Strategy

- **Always loaded**: SKILL.md (table of contents)
- **Load on demand**:
  - `workflows.md` when user needs detailed workflow guidance
  - `github-issue-apis.md` when agent encounters API issues
  - `github-issue-checklists.md` when implementing fixes

## Safety & Validation

### Authentication
- Validate GitHub CLI authentication: `gh auth status`
- Fail fast if not authenticated
- Provide clear guidance: `gh auth login`

### Repository Validation
- Verify repository exists and is accessible
- Check write permissions for create/update/fix operations
- Respect repository settings (branch protection, required reviews)

### Worktree Safety
- Never create worktree in dirty state
- Validate base branch exists before creating worktree
- Clean up worktrees on error (with user approval)
- Respect `.claude/config.yaml` for worktree paths

### Destructive Operations
- `--yolo` flag:
  - Skips confirmations for SAFE operations (create worktree, commit, push)
  - NEVER skips confirmations for:
    - Branch deletion
    - Force operations
    - Dirty worktree cleanup
- Default behavior: prompt before any state changes

### Error Recovery
- Provide rollback instructions on failure
- Clean up partial state (worktrees, branches)
- Suggest next steps for user

### Audit Trail
- Use Agent Runner to log all operations
- Audit log location: `.claude/state/logs/github-issue-<timestamp>.json`
- Include: operation, issue number, branch, outcome, duration

## Implementation Phases

### Phase 1: Core Infrastructure (MVP)
**Deliverables**:
- Command stub: `.claude/commands/github-issue.md`
- Skill orchestrator: `.claude/skills/github-issue/SKILL.md`
- Basic agents: `issue-list-agent`, `issue-fetch-agent`
- Registry updates with dependency constraints
- Configuration schema in `.claude/config.yaml`

**Validation**:
- `/github-issue --list` works
- `/github-issue --help` displays help text
- Registry validation passes: `scripts/validate-agents.sh`

### Phase 2: CRUD Operations
**Deliverables**:
- Create agent: `issue-create-agent.md`
- Update agent: `issue-update-agent.md`
- Interactive workflows for create/update

**Validation**:
- Can create issue via `/github-issue --create`
- Can update issue via `/github-issue --update <id>`
- Proper error handling for permissions, invalid inputs

### Phase 3: Fix Workflow (Core Value)
**Deliverables**:
- Fix agent: `issue-fix-agent.md`
- PR agent: `pr-create-agent.md`
- Worktree integration via Agent Runner
- End-to-end fix workflow

**Validation**:
- `/github-issue --fix --issue 42` creates worktree, implements fix, creates PR
- Proper cleanup on error
- Tests run before commit (if configured)

### Phase 4: Polish & References
**Deliverables**:
- Reference documents: `github-issue-apis.md`, `github-issue-checklists.md`
- Enhanced error messages
- `--yolo` flag implementation
- Repository-specific configuration support

**Validation**:
- References load correctly on demand
- `--yolo` flag behavior correct (skips safe prompts, keeps critical ones)
- Works across different repository configurations

### Phase 5: Advanced Features (Future)
**Potential additions**:
- Issue templates support
- Milestone management
- Project board integration
- Batch operations (fix multiple issues)
- Issue search/filter
- Comment management

## Open Questions

1. **GitHub CLI vs API**: Should we use `gh` CLI exclusively, or mix with direct API calls for better control?
   - **Recommendation**: Start with `gh` CLI for simplicity, add API fallback if needed

2. **Test execution strategy**: How much autonomy should `issue-fix-agent` have in running tests?
   - **Recommendation**: Run tests if `test_command` provided in config, fail-safe if tests fail (don't commit)

3. **Branch naming convention**: Should branch names be configurable or follow fixed pattern?
   - **Recommendation**: Default `fix-issue-<number>`, allow override via config: `github.branch_pattern`

4. **PR auto-merge**: Should we support auto-merge for simple fixes with `--yolo`?
   - **Recommendation**: No for v0.1.0, consider for future version with safety checks

5. **Multi-repository support**: Should we support operating across multiple repositories in single invocation?
   - **Recommendation**: No for v0.1.0, single repo per invocation

6. **Worktree cleanup timing**: When should worktrees be cleaned up after PR creation?
   - **Recommendation**: Keep worktree after PR creation, user manually cleans up after PR merged using `/git-worktree --cleanup`

7. **Issue assignment**: Should `--fix` automatically assign issue to current user?
   - **Recommendation**: Only if `github.auto_assign: true` in config (default: false)

## Success Criteria

### Functional Requirements
- ✅ User can list issues in repository
- ✅ User can create new issues with title, body, labels
- ✅ User can update existing issues
- ✅ User can fix issue in isolated worktree
- ✅ System automatically creates PR after fix
- ✅ All agents return structured JSON with minimal envelope
- ✅ Integration with `managing-worktrees` skill works seamlessly

### Non-Functional Requirements
- ✅ SKILL.md under 2KB
- ✅ All agents have version in frontmatter
- ✅ Registry constraints properly defined
- ✅ Error messages are clear and actionable
- ✅ Help text is comprehensive but concise
- ✅ Configuration supports repository-specific settings

### User Experience
- ✅ Command feels natural and intuitive
- ✅ Progressive disclosure: simple commands for simple tasks
- ✅ Clear feedback at each step
- ✅ `--yolo` flag works for automation without compromising safety
- ✅ Error recovery guidance is helpful

### Quality Gates
- ✅ Registry validation passes: `scripts/validate-agents.sh`
- ✅ All agents return fenced JSON
- ✅ No destructive operations without confirmation (except with appropriate `--yolo` safeguards)
- ✅ Respects GitHub repository settings and permissions

## Next Steps

1. **Review and Approval**
   - Review plan with stakeholders
   - Confirm agent responsibilities and data contracts
   - Validate configuration schema
   - Mark status as "Proposed"

2. **Implementation (Phase 1)**
   - Create command stub
   - Create skill orchestrator
   - Implement basic agents (list, fetch)
   - Update registry

3. **Testing**
   - Validate with real GitHub repository
   - Test error scenarios
   - Verify worktree integration

4. **Documentation**
   - Create reference documents
   - Add examples to SKILL.md
   - Update main repo README with new command

5. **Iteration**
   - Gather user feedback
   - Refine workflows based on usage
   - Add advanced features as needed
