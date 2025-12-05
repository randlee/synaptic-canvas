# GitHub Issue Workflow Checklists

Checklists and best practices for implementing GitHub issue operations.

## Pre-Flight Checklist

Before any GitHub operation:

- [ ] Verify GitHub CLI is installed: `which gh`
- [ ] Check authentication status: `gh auth status`
- [ ] Validate repository access: `gh repo view`
- [ ] Confirm working directory is correct

## Issue List Workflow

- [ ] Validate repository parameter or detect current repo
- [ ] Build `gh issue list` command with appropriate filters
- [ ] Execute and capture JSON output
- [ ] Handle empty results gracefully
- [ ] Format output for display
- [ ] Return fenced JSON response

## Issue Create Workflow

- [ ] Validate required inputs (title)
- [ ] Load defaults from configuration if available
- [ ] Build `gh issue create` command
- [ ] Execute and capture issue URL and number
- [ ] Handle label/assignee validation errors
- [ ] Return fenced JSON with created issue details
- [ ] Provide issue URL for user reference

## Issue Update Workflow

- [ ] Validate issue exists first
- [ ] Determine which fields to update
- [ ] Build `gh issue edit` command
- [ ] Handle state changes separately if needed
- [ ] Execute and verify update
- [ ] Fetch updated issue for confirmation
- [ ] Return fenced JSON with updated fields

## Issue Fix Workflow

### Phase 1: Setup

- [ ] Fetch issue details via `issue-fetch-agent`
- [ ] Display issue summary to user
- [ ] Get confirmation (unless `--yolo`)
- [ ] Invoke `sc-worktree-create` agent via Agent Runner
- [ ] Verify worktree created successfully

### Phase 2: Implementation

- [ ] Change to worktree directory
- [ ] Verify clean working tree: `git status --porcelain`
- [ ] Analyze issue and identify affected files
- [ ] Plan implementation approach
- [ ] Implement fix using appropriate tools
- [ ] Keep changes minimal and focused

### Phase 3: Testing

- [ ] Run tests if `test_command` configured
- [ ] Capture test results
- [ ] If tests fail, ask for approval to proceed
- [ ] Document test results in output

### Phase 4: Commit & Push

- [ ] Stage all changes: `git add .`
- [ ] Commit with proper message format
- [ ] Include issue reference in commit: `Fix #<number>`
- [ ] Push to remote: `git push -u origin <branch>`
- [ ] Capture commit SHA

### Phase 5: PR Creation

- [ ] Invoke `pr-create-agent` with fix details
- [ ] Ensure PR references issue properly
- [ ] Verify PR created successfully
- [ ] Provide PR URL to user

## PR Creation Workflow

- [ ] Validate branch exists on remote
- [ ] Fetch issue details for PR body
- [ ] Build PR title (default: `Fix #<issue>: <title>`)
- [ ] Generate PR body from template
- [ ] Ensure issue reference in title or body
- [ ] Execute `gh pr create`
- [ ] Enable auto-merge if requested
- [ ] Return fenced JSON with PR details

## Error Recovery

### Authentication Failure

1. Check auth status: `gh auth status`
2. Re-authenticate: `gh auth login`
3. Retry operation

### Rate Limit Exceeded

1. Check rate limit: `gh api rate_limit`
2. Wait for reset time
3. Implement exponential backoff

### Permission Denied

1. Verify repository access: `gh repo view owner/repo`
2. Check required permissions (read/write)
3. Request access or use different credentials

### Worktree Dirty

1. Check status: `git status`
2. Options:
   - Commit changes
   - Stash changes: `git stash`
   - Discard changes: `git reset --hard` (with caution)

### Push Failure

1. Check remote tracking: `git branch -vv`
2. Fetch latest: `git fetch origin`
3. Resolve conflicts if needed
4. Retry push

### Test Failure

1. Review test output
2. Options:
   - Fix failing tests
   - Update tests if behavior changed
   - Get approval to proceed (if acceptable)
   - Abort and investigate

## Safety Checks

### Before Creating Issues

- [ ] Validate title is not empty
- [ ] Check for duplicate issues
- [ ] Verify labels exist or can be created
- [ ] Confirm assignees are valid

### Before Updating Issues

- [ ] Verify issue exists
- [ ] Confirm at least one field changing
- [ ] Validate state transitions
- [ ] Check user has permission

### Before Fixing Issues

- [ ] Verify issue is still open
- [ ] Check issue is not assigned to someone else
- [ ] Ensure issue has enough detail to fix
- [ ] Confirm worktree is clean

### Before Creating PRs

- [ ] Verify branch pushed to remote
- [ ] Ensure branch has commits
- [ ] Check base branch is valid
- [ ] Confirm issue reference present
- [ ] Validate no conflicts with base

## Configuration Validation

Check `.claude/config.yaml` for:

```yaml
base_branch: main                # Required for worktree/PR operations
worktree_root: ../worktrees      # Required for worktree creation

github:
  default_labels: []             # Optional
  auto_assign: false             # Optional
  branch_pattern: "fix-issue-{number}"  # Optional
  test_command: null             # Optional (e.g., "npm test")
  pr_template: |                 # Optional
    ## Summary
    Fixes #{issue_number}
```

## Best Practices

### Commit Messages

Use conventional commit format:
```
Fix #42: Application crashes on startup

- Added null check in getUserData method
- Added validation for user input
- Updated error handling

Fixes #42
```

### Branch Naming

Follow pattern from config or use default:
- `fix-issue-42`
- `feature-issue-42`
- `bug-issue-42`

### PR Descriptions

Include:
1. Summary with issue reference
2. List of changes
3. Testing performed
4. Related issues

### Issue References

Use closing keywords to auto-close:
- `Fixes #42`
- `Closes #42`
- `Resolves #42`

Multiple issues:
- `Fixes #42, fixes #43`

## Rollback Procedures

### Undo Commit (Not Pushed)

```bash
git reset --soft HEAD~1  # Keep changes
git reset --hard HEAD~1  # Discard changes
```

### Undo Commit (Pushed)

```bash
git revert HEAD  # Create revert commit
git push origin <branch>
```

### Close PR

```bash
gh pr close <number> --repo owner/repo
```

### Reopen Issue

```bash
gh issue reopen <number> --repo owner/repo
```

### Delete Branch

```bash
git push origin --delete <branch>
git branch -D <branch>
```

## Audit Trail

Log all operations with:
- Operation type
- Issue number
- Repository
- Branch name
- User
- Timestamp
- Outcome (success/failure)
- Error details if applicable

Store in: `.claude/state/logs/github-issue-<timestamp>.json`
