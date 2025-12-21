---
name: github-issue
version: 0.7.0
description: Manage GitHub issues - list, create, update, and fix with automated workflows
---

# GitHub Issue Management

Unified command for GitHub issue lifecycle operations: listing, creating, updating, fixing (with worktree isolation), and PR creation.

## Usage

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

## Behavior

### No flags or --help
Display help text with examples and usage information.

### --list
List open issues in the repository with numbers, titles, labels, and assignees.
- Uses `issue-intake-agent` with operation=list
- Supports `--repo` to specify target repository
- Detects current repo from `gh repo view` if not specified

### --create
Create a new issue interactively:
1. Prompt for title (required)
2. Prompt for body/description
3. Prompt for labels (comma-separated)
4. Prompt for assignees (comma-separated)
5. Create issue using `issue-mutate-agent`
6. Display created issue URL

### --update <id>
Update an existing issue interactively:
1. Fetch current issue details
2. Prompt for fields to update (title, body, labels, assignees, state)
3. Update issue using `issue-mutate-agent`
4. Display confirmation

### --fix --issue <id/url>
Full fix workflow with worktree isolation:

**Phase 1: Intake & Confirmation**
1. Fetch issue details using `issue-intake-agent`
2. Display issue summary (number, title, body, labels)
3. If not `--yolo`, prompt: "Proceed with fix for issue #42? (y/n)"
4. Load config from `.claude/config.yaml` (base_branch, worktree_root, github settings)

**Phase 2: Worktree Setup**
5. Generate branch name from pattern (e.g., `fix-issue-42`)
6. Invoke `sc-worktree-create` via sc-managing-worktrees skill (registry lookup)
7. Verify worktree created successfully

**Phase 3: Implementation**
8. Invoke `issue-fix-agent` with issue details and worktree path
9. Agent implements fix, runs tests (if configured), commits, and pushes

**Phase 4: PR Creation**
10. Invoke `issue-pr-agent` to create PR from fix branch
11. Display PR URL

**Phase 5: Summary**
12. Show summary: issue number, branch, commits, test results, PR URL
13. Remind user about worktree cleanup (manual via `/sc-git-worktree --cleanup`)

## Configuration

Reads from `.claude/config.yaml`:

```yaml
base_branch: main
worktree_root: ../worktrees

github:
  default_labels: []
  auto_assign: false
  branch_pattern: "fix-issue-{number}"
  test_command: null
  pr_template: |
    ## Summary
    Fixes #{issue_number}
```

Defaults if config missing:
- `base_branch`: `main`
- `worktree_root`: `../<repo-name>-worktrees`
- `branch_pattern`: `fix-issue-{number}`

## Safety & Approval Gates

### Pre-flight Checks
- Verify `gh` CLI installed and authenticated
- Validate repository access
- Confirm working directory clean

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

## Integration

- **Agents**: issue-intake-agent, issue-mutate-agent, issue-fix-agent, issue-pr-agent
- **Skills**: sc-managing-worktrees (for worktree operations)
- **CLI**: GitHub CLI (`gh`) for all operations
- **References**:
  - `.claude/references/github-issue-apis.md` (API patterns)
  - `.claude/references/github-issue-checklists.md` (workflow checklists)

## Notes

- All agents return fenced JSON with minimal envelope structure
- Use `--yolo` for automated workflows (CI/CD)
- Worktree cleanup is manual - use `/sc-git-worktree --cleanup` when PR is merged
- Repository detection uses `gh repo view --json nameWithOwner`
