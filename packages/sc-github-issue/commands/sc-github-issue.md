---
name: sc-github-issue
version: 0.7.0
description: Manage GitHub issues - list, create, update, and fix with automated workflows
---

# GitHub Issue Management

Unified command for GitHub issue lifecycle operations: listing, creating, updating, fixing (with worktree isolation), and PR creation.

## Usage

```
/sc-github-issue [options]

Options:
  --list                    List open issues in repository
  --fix --issue <id/url>   Fix specified issue in isolated worktree
  --yolo                   Skip confirmation prompts (use with --fix)
  --repo <owner/repo>      Target repository (default: current repo)
  --create                 Create new issue interactively
  --update <id>            Update existing issue
  --help                   Show this help message

Examples:
  /sc-github-issue --list
  /sc-github-issue --list --repo owner/repo
  /sc-github-issue --fix --issue 42
  /sc-github-issue --fix --issue https://github.com/owner/repo/issues/42 --yolo
  /sc-github-issue --create
  /sc-github-issue --update 42
```

## Behavior

### No flags or --help
Display help text with examples and usage information.

### --list
List open issues in the repository with numbers, titles, labels, and assignees.
- Uses `sc-github-issue-intake` agent with operation=list
- Supports `--repo` to specify target repository
- Detects current repo from `gh repo view` if not specified

### --create
Create a new issue interactively:
1. Prompt for title (required)
2. Prompt for body/description
3. Prompt for labels (comma-separated)
4. Prompt for assignees (comma-separated)
5. Create issue using `sc-github-issue-mutate` agent
6. Display created issue URL

### --update <id>
Update an existing issue interactively:
1. Fetch current issue details
2. Prompt for fields to update (title, body, labels, assignees, state)
3. Update issue using `sc-github-issue-mutate` agent
4. Display confirmation

### --fix --issue <id/url>
Full fix workflow with worktree isolation:

**Phase 1: Intake & Confirmation**
1. Fetch issue details using `sc-github-issue-intake` agent
2. Display issue summary (number, title, body, labels)
3. If not `--yolo`, prompt: "Proceed with fix for issue #42? (y/n)"
4. Load configuration from manifest options (base-branch, branch-pattern, auto-pr)

**Phase 2: Worktree Setup**
5. Generate branch name from pattern (e.g., `fix-issue-42`)
6. Invoke `sc-worktree-create` via sc-git-worktree skill
7. Verify worktree created successfully

**Phase 3: Implementation**
8. Invoke `sc-github-issue-fix` agent with issue details and worktree path
9. Agent implements fix, runs tests (if configured), commits, and pushes

**Phase 4: PR Creation**
10. Invoke `sc-github-issue-pr` agent to create PR from fix branch
11. Display PR URL

**Phase 5: Summary**
12. Show summary: issue number, branch, commits, test results, PR URL
13. Remind user about worktree cleanup (manual via `/sc-git-worktree --cleanup`)

## Configuration

Configuration is read from the package manifest options. Defaults:

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

Users can override in their project's `.claude/config.yaml`:

```yaml
packages:
  sc-github-issue:
    base-branch: develop
    branch-pattern: "hotfix/{number}"
    auto-pr: false
```

Additional GitHub settings (optional):

```yaml
github:
  test_command: "npm test"
  pr_template: |
    ## Summary
    Fixes #{issue_number}
```

## Safety & Approval Gates

### Pre-flight Checks
- Verify `gh` CLI installed and authenticated
- Validate repository access
- Confirm working directory clean
- Verify sc-git-worktree dependency available

### Approval Gates
1. **Before fix** (unless `--yolo`): Display issue details and prompt for confirmation
2. **If tests fail**: Display output and prompt "Tests failed. Proceed anyway? (y/n)"
3. **Before PR**: Confirm all changes committed and pushed

### Error Handling
- Authentication failure → guide to `gh auth login`
- Rate limit → display reset time
- Permission denied → verify repo access
- Worktree conflicts → suggest cleanup
- Push failure → display git error
- Missing dependency → guide to `sc-manage install sc-git-worktree`

## Integration

- **Agents**: sc-github-issue-intake, sc-github-issue-mutate, sc-github-issue-fix, sc-github-issue-pr
- **Skills**: sc-git-worktree (for worktree operations)
- **CLI**: GitHub CLI (`gh`) for all operations
- **References**:
  - `references/github-issue-apis.md` (API patterns)
  - `references/github-issue-checklists.md` (workflow checklists)

## Notes

- All agents return fenced JSON with minimal envelope structure (v0.4 format)
- Use `--yolo` for automated workflows (CI/CD)
- Worktree cleanup is manual - use `/sc-git-worktree --cleanup` when PR is merged
- Repository detection uses `gh repo view --json nameWithOwner`
- This package requires sc-git-worktree >= 0.6.0 for worktree isolation
