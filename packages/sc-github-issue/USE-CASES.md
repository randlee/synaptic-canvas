# Use Cases

Practical examples and workflows for using `sc-github-issue`.

## Use Case 1: Bug Triage and Fix

**Scenario**: You have a backlog of bug reports and need to systematically triage and fix them.

### Workflow

```bash
# 1. List all open bugs
/sc-github-issue --list

# Output shows:
# #42: Application crashes on startup [bug, priority-high]
# #43: Memory leak in data processor [bug]
# #44: UI flicker on refresh [bug, ui]

# 2. Fix high-priority bug
/sc-github-issue --fix --issue 42

# Claude will:
# - Fetch issue #42 details
# - Display summary and ask for confirmation
# - Create worktree: fix-issue-42
# - Analyze code and implement fix
# - Run tests
# - Commit: "Fix #42: Application crashes on startup"
# - Push to remote
# - Create PR with auto-link to issue

# 3. Review PR and merge in GitHub UI

# 4. Clean up worktree after merge
/sc-git-worktree --cleanup --worktree fix-issue-42

# 5. Move to next bug
/sc-github-issue --fix --issue 43
```

### Benefits
- Isolated environments prevent cross-contamination
- Consistent commit messages and PR format
- Automated testing before push
- Clear audit trail from issue → PR → merge

## Use Case 2: Feature Request Implementation

**Scenario**: User requests a new feature via GitHub issue.

### Workflow

```bash
# 1. User creates feature request issue #50

# 2. Review and add labels
/sc-github-issue --update 50
# Prompt: Which fields to update? labels
# Input: enhancement, needs-design

# 3. After design approval, implement
/sc-github-issue --fix --issue 50

# 4. PR is created with:
# Title: Fix #50: Add dark mode support
# Body: References issue, lists changes
# Auto-links to issue #50

# 5. After review and merge, issue auto-closes
```

### Benefits
- Seamless transition from feature request to implementation
- Issue auto-closes on PR merge (via "Fixes #50")
- Clear traceability between feature request and code changes

## Use Case 3: Batch Issue Creation

**Scenario**: You've identified multiple issues during code review and need to create them quickly.

### Workflow

```bash
# Create multiple issues interactively
/sc-github-issue --create
# Title: Fix memory leak in UserService
# Labels: bug, performance
# Assignees: developer1

/sc-github-issue --create
# Title: Add input validation to API endpoints
# Labels: security, enhancement
# Assignees: developer2

/sc-github-issue --create
# Title: Update outdated dependencies
# Labels: maintenance, dependencies
# Assignees: developer1
```

### Benefits
- Quick issue creation from command line
- Consistent labeling and assignment
- Integrated with existing workflow

## Use Case 4: CI/CD Integration

**Scenario**: Automated fix workflow triggered by monitoring alerts.

### Workflow

```bash
#!/bin/bash
# automated-fix.sh

# Triggered by monitoring system detecting issue

ISSUE_NUMBER=$1
REPO="owner/repo"

# Skip confirmation prompts with --yolo
/sc-github-issue --fix --issue "$ISSUE_NUMBER" --yolo --repo "$REPO"

# Exit code 0 on success, non-zero on failure
if [ $? -eq 0 ]; then
  echo "Fix succeeded, PR created"
  # Notify team
else
  echo "Fix failed, manual intervention needed"
  # Alert on-call engineer
fi
```

### Benefits
- Fully automated fix workflow
- No human intervention required
- Clear success/failure signals
- Integrates with existing CI/CD pipelines

## Use Case 5: Parallel Bug Fixing

**Scenario**: Multiple developers working on different bugs simultaneously.

### Workflow

**Developer 1:**
```bash
/sc-github-issue --fix --issue 42
# Creates worktree: ../worktrees/fix-issue-42
# Works in isolation
```

**Developer 2 (same repository):**
```bash
/sc-github-issue --fix --issue 43
# Creates worktree: ../worktrees/fix-issue-43
# Also works in isolation
```

**Main working directory:**
```bash
cd /main/repo
git status
# Clean - no changes from either fix workflow
```

### Benefits
- Main working directory never contaminated
- Multiple fixes in progress simultaneously
- No branch switching in main directory
- Each developer has isolated environment

## Use Case 6: Hotfix Production Issue

**Scenario**: Critical bug in production needs immediate fix.

### Configuration

```yaml
# .claude/config.yaml
packages:
  sc-github-issue:
    base-branch: "main"
    branch-pattern: "hotfix-{number}"
    auto-pr: true

github:
  test_command: "npm run test:critical"  # Only critical tests
  pr_template: |
    ## 🚨 HOTFIX
    Fixes #{issue_number}

    ## Changes
    {commits}

    ## Testing
    Critical tests passed

    **Priority**: Merge immediately after review
```

### Workflow

```bash
# 1. Create hotfix issue
/sc-github-issue --create
# Title: CRITICAL: Payment processing fails
# Labels: bug, critical, production

# 2. Implement fix immediately
/sc-github-issue --fix --issue 99 --yolo

# 3. PR is created with hotfix template
# 4. Reviewer merges immediately
# 5. Issue auto-closes
```

### Benefits
- Rapid response to production issues
- Hotfix branch naming (hotfix-99)
- Minimal testing (critical tests only)
- Clear labeling and priority

## Use Case 7: Issue Investigation

**Scenario**: Issue report is unclear, need to investigate before fixing.

### Workflow

```bash
# 1. Fetch detailed issue information
/sc-github-issue --list

# 2. Review issue #47
# Title: "Application slow"
# Body: Vague description

# 3. Add comment asking for more details (via GitHub UI)

# 4. Update issue with investigation label
/sc-github-issue --update 47
# Add labels: needs-info, investigating

# 5. After user provides details, update again
/sc-github-issue --update 47
# Remove label: needs-info
# Add label: ready-to-fix

# 6. Now implement fix
/sc-github-issue --fix --issue 47
```

### Benefits
- Clear issue state tracking
- Prevents premature fix attempts
- Documents investigation process
- User knows issue is being actively worked

## Use Case 8: Multi-Repository Management

**Scenario**: Managing issues across multiple repositories.

### Workflow

```bash
# Repository 1: Frontend
cd ~/projects/frontend
/sc-github-issue --list --repo owner/frontend
/sc-github-issue --fix --issue 10 --repo owner/frontend

# Repository 2: Backend
cd ~/projects/backend
/sc-github-issue --list --repo owner/backend
/sc-github-issue --fix --issue 5 --repo owner/backend

# Repository 3: From anywhere
/sc-github-issue --list --repo owner/docs
/sc-github-issue --fix --issue 3 --repo owner/docs
```

### Benefits
- Manage issues across multiple projects
- No need to switch repositories
- Consistent workflow regardless of repo
- `--repo` flag works from any directory

## Use Case 9: Test-Driven Bug Fixing

**Scenario**: Write tests first, then implement fix.

### Configuration

```yaml
github:
  test_command: "npm test"
```

### Workflow

```bash
# 1. Fix issue with TDD approach
/sc-github-issue --fix --issue 55

# Claude will:
# - Create worktree
# - Analyze issue
# - Write failing test first
# - Implement fix
# - Run tests (should now pass)
# - Commit both test and fix

# 2. If tests fail, Claude prompts:
# "Tests failed. Proceed anyway? (y/n)"
# Answer: n

# 3. Claude refines fix until tests pass
```

### Benefits
- Tests document expected behavior
- Prevents regression
- Clear verification of fix
- Test failures prevent premature commits

## Use Case 10: Issue Template Enforcement

**Scenario**: Ensure issues follow required format.

### Workflow

```bash
# 1. Create issue with required fields
/sc-github-issue --create

# Claude prompts:
# Title: [Required] Fix navigation bug
# Body: [Paste issue template here]
# Labels: bug, frontend
# Assignees: developer1

# 2. Issue created with proper format
# 3. Team can find issues easily via labels
```

### Benefits
- Consistent issue format
- Required fields enforced
- Easier triage and searching
- Clear ownership via assignees

## Common Patterns

### Pattern: Before/After Testing

```bash
# Before fix
npm test  # Some tests failing

# Implement fix
/sc-github-issue --fix --issue 42

# After fix (in worktree)
cd ../worktrees/fix-issue-42
npm test  # All tests passing

# Main directory unchanged
cd - && npm test  # Still fails (not yet merged)
```

### Pattern: Approval Workflow

```bash
# Reviewer workflow
gh pr list  # See new PRs
gh pr view 123  # Review changes
gh pr review 123 --approve
gh pr merge 123 --squash

# Issue auto-closes, worktree ready for cleanup
```

### Pattern: Multi-File Fixes

```bash
# Complex fix spanning multiple files
/sc-github-issue --fix --issue 60

# Claude will:
# - Identify all affected files
# - Make coordinated changes
# - Ensure consistency across files
# - Single commit for atomic change
```

## Best Practices

1. **Use descriptive issue titles**: "Fix crash" → "Fix NPE in UserService.getData()"
2. **Label consistently**: Use same labels across issues
3. **One fix per issue**: Don't bundle unrelated changes
4. **Clean up worktrees**: After PR merge, run cleanup
5. **Test before commit**: Let test_command catch issues early
6. **Review PRs promptly**: Reduces merge conflicts
7. **Use --yolo sparingly**: Only for trusted automated workflows

## Next Steps

- See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
- See [README.md](./README.md) for installation and configuration
- See [DEPENDENCIES.md](./DEPENDENCIES.md) for integration details
