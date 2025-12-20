# Troubleshooting Guide

Common issues and solutions for `sc-github-issue`.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Authentication Errors](#authentication-errors)
- [Permission Errors](#permission-errors)
- [Worktree Issues](#worktree-issues)
- [Git Operation Failures](#git-operation-failures)
- [Test Failures](#test-failures)
- [PR Creation Failures](#pr-creation-failures)
- [Rate Limiting](#rate-limiting)
- [Configuration Issues](#configuration-issues)

---

## Installation Issues

### Package Not Found

**Error:**
```
Error: Package sc-github-issue not found in registry
```

**Solution:**
1. Ensure you have the latest registry:
   ```bash
   sc-manage update
   ```
2. Verify package exists:
   ```bash
   sc-manage list-available
   ```
3. Check marketplace URL in config

### Dependency Installation Failed

**Error:**
```
Error: Failed to install dependency sc-git-worktree
```

**Solution:**
1. Install dependency manually:
   ```bash
   sc-manage install sc-git-worktree
   ```
2. Then retry:
   ```bash
   sc-manage install sc-github-issue
   ```

### Already Installed (Different Version)

**Error:**
```
Error: sc-github-issue v0.1.0 already installed (project-level)
```

**Solution:**
1. Remove old project-level files:
   ```bash
   rm -rf .claude/commands/github-issue.md
   rm -rf .claude/skills/github-issue/
   rm -rf .claude/agents/issue-*-agent.md
   ```
2. Install marketplace package:
   ```bash
   sc-manage install sc-github-issue
   ```

---

## Authentication Errors

### GH.AUTH.REQUIRED

**Error:**
```json
{
  "error": {
    "code": "GH.AUTH.REQUIRED",
    "message": "GitHub CLI not authenticated"
  }
}
```

**Solution:**
```bash
# Check authentication status
gh auth status

# If not authenticated
gh auth login

# Select authentication method (browser or token)
# Follow prompts to complete authentication

# Verify success
gh auth status
```

### GH.AUTH.EXPIRED

**Error:**
```
Error: token expired
```

**Solution:**
```bash
# Refresh authentication
gh auth refresh

# If refresh fails, re-authenticate
gh auth logout
gh auth login
```

### GH.AUTH.INSUFFICIENT_SCOPE

**Error:**
```
Error: token lacks required scopes
```

**Solution:**
```bash
# Refresh with required scopes
gh auth refresh --scopes repo,workflow

# Verify scopes
gh auth status
```

---

## Permission Errors

### GH.PERMISSION_DENIED

**Error:**
```json
{
  "error": {
    "code": "GH.PERMISSION_DENIED",
    "message": "No write access to repository owner/repo"
  }
}
```

**Solution:**
1. Verify you have write access:
   ```bash
   gh repo view owner/repo --json viewerPermission
   ```
2. Request access from repository owner
3. Check if repository is archived (no writes allowed)
4. Verify you're using correct account:
   ```bash
   gh auth status
   ```

### GH.ISSUE.NOT_FOUND

**Error:**
```
Error: Issue #42 not found
```

**Possible Causes:**
- Issue number doesn't exist
- Issue is in different repository
- No read access to repository

**Solution:**
```bash
# Verify issue exists
gh issue view 42 --repo owner/repo

# Check repository
gh repo view

# Specify repository explicitly
/sc-github-issue --fix --issue 42 --repo owner/repo
```

---

## Worktree Issues

### WORKTREE.DIRTY

**Error:**
```json
{
  "error": {
    "code": "WORKTREE.DIRTY",
    "message": "Uncommitted changes in worktree"
  }
}
```

**Solution:**
```bash
# Check status
git status

# Option 1: Commit changes
git add .
git commit -m "WIP: save progress"

# Option 2: Stash changes
git stash save "Temporary stash"

# Option 3: Discard changes (CAUTION)
git reset --hard HEAD

# Then retry fix
/sc-github-issue --fix --issue 42
```

### WORKTREE.ALREADY_EXISTS

**Error:**
```
Error: Worktree fix-issue-42 already exists
```

**Solution:**
```bash
# Option 1: Clean up existing worktree
/sc-git-worktree --cleanup --worktree fix-issue-42

# Option 2: Remove manually
git worktree remove ../worktrees/fix-issue-42 --force

# Then retry fix
/sc-github-issue --fix --issue 42
```

### WORKTREE.NOT_FOUND

**Error:**
```
Error: Worktree path does not exist
```

**Solution:**
1. Check worktree configuration:
   ```yaml
   packages:
     sc-git-worktree:
       root: ../worktrees  # Verify path
   ```
2. Create worktree root if missing:
   ```bash
   mkdir -p ../worktrees
   ```
3. Retry operation

### WORKTREE.CREATE_FAILED

**Error:**
```
Error: Failed to create worktree
```

**Solution:**
1. Check disk space:
   ```bash
   df -h
   ```
2. Verify parent directory exists and is writable
3. Check for branch name conflicts:
   ```bash
   git branch --list "fix-issue-42"
   ```
4. Review git worktree logs:
   ```bash
   git worktree list
   ```

---

## Git Operation Failures

### GIT.COMMIT_FAILED

**Error:**
```
Error: Git commit failed
```

**Possible Causes:**
- No changes to commit
- Commit message invalid
- Pre-commit hooks failing

**Solution:**
```bash
# Check if there are changes
git status

# Check pre-commit hooks
ls .git/hooks/pre-commit

# Bypass hooks if needed (CAUTION)
git commit --no-verify -m "message"

# Review commit error details
git commit -v
```

### GIT.PUSH_FAILED

**Error:**
```
Error: Git push failed
```

**Possible Causes:**
- Network issues
- Branch protection rules
- Force push required
- Authentication issues

**Solution:**
```bash
# Check remote configuration
git remote -v

# Verify branch tracking
git branch -vv

# Check for conflicts
git pull --rebase origin main

# Retry push
git push -u origin branch-name

# If force push needed (CAUTION)
git push --force-with-lease origin branch-name
```

### GIT.BRANCH_EXISTS

**Error:**
```
Error: Branch fix-issue-42 already exists
```

**Solution:**
```bash
# Check existing branch
git branch --list "fix-issue-42"

# Option 1: Delete old branch
git branch -D fix-issue-42
git push origin --delete fix-issue-42

# Option 2: Use different branch name
/sc-github-issue --fix --issue 42
# (Configure branch-pattern in config)
```

---

## Test Failures

### EXEC.TEST_FAILED

**Error:**
```
Error: Tests failed and user aborted
```

**When Tests Fail:**

1. **Review test output** in the error message
2. **Options:**
   - Fix the failing tests
   - Answer "y" to proceed anyway
   - Investigate root cause

**Solution:**
```bash
# Run tests manually to debug
npm test

# Run specific test
npm test -- path/to/test.spec.js

# If tests are flaky, retry
/sc-github-issue --fix --issue 42

# Skip test failures (CAUTION)
# Answer "y" when prompted
# Or use --yolo to skip all prompts
```

### Test Command Not Found

**Error:**
```
Error: npm: command not found
```

**Solution:**
1. Verify test command in config:
   ```yaml
   github:
     test_command: "npm test"  # Ensure correct
   ```
2. Check command exists:
   ```bash
   which npm
   ```
3. Update test command if needed:
   ```yaml
   github:
     test_command: "./run-tests.sh"
   ```

---

## PR Creation Failures

### GH.BRANCH.NOT_PUSHED

**Error:**
```json
{
  "error": {
    "code": "GH.BRANCH.NOT_PUSHED",
    "message": "Branch fix-issue-42 not found on remote"
  }
}
```

**Solution:**
```bash
# Push branch to remote
git push -u origin fix-issue-42

# Then retry PR creation
/sc-github-issue --fix --issue 42
```

### GH.PR.ALREADY_EXISTS

**Error:**
```
Error: Pull request already exists for branch
```

**Solution:**
```bash
# View existing PR
gh pr view fix-issue-42

# Option 1: Use existing PR (success case)
# Option 2: Close old PR and create new
gh pr close fix-issue-42
gh pr create --base main --head fix-issue-42
```

### GH.VALIDATION_FAILED

**Error:**
```
Error: Validation failed - No commits between main and fix-issue-42
```

**Solution:**
1. Verify commits exist:
   ```bash
   git log main..fix-issue-42
   ```
2. If no commits, make changes and commit
3. Ensure branch is ahead of base:
   ```bash
   git fetch origin main
   git log origin/main..HEAD
   ```

---

## Rate Limiting

### GH.RATE_LIMIT

**Error:**
```json
{
  "error": {
    "code": "GH.RATE_LIMIT",
    "message": "API rate limit exceeded"
  }
}
```

**Solution:**
1. Check rate limit status:
   ```bash
   gh api rate_limit
   ```
2. Wait for reset time shown in error
3. Use authenticated requests (higher limit):
   ```bash
   gh auth status  # Verify authenticated
   ```
4. Implement delays between operations

**Rate Limits:**
- Authenticated: 5,000 requests/hour
- Unauthenticated: 60 requests/hour

---

## Configuration Issues

### Invalid Configuration

**Error:**
```
Error: Invalid configuration value
```

**Solution:**
1. Validate YAML syntax:
   ```bash
   yamllint .claude/config.yaml
   ```
2. Check for required fields:
   ```yaml
   packages:
     sc-github-issue:
       base-branch: "main"     # Required
       branch-pattern: "fix-issue-{number}"  # Required
   ```
3. Verify option types match manifest

### Configuration Not Found

**Error:**
```
Warning: Using default configuration
```

**Solution:**
1. Create config file:
   ```bash
   touch .claude/config.yaml
   ```
2. Add package configuration:
   ```yaml
   packages:
     sc-github-issue:
       base-branch: "main"
       branch-pattern: "fix-issue-{number}"
       auto-pr: true
   ```

### Missing Dependency Configuration

**Error:**
```
Error: sc-git-worktree configuration missing
```

**Solution:**
```yaml
packages:
  sc-git-worktree:
    root: ../worktrees
    tracking:
      enabled: true
    git_flow:
      enabled: true
      main_branch: "main"
```

---

## Debugging Tips

### Enable Verbose Output

```bash
# Set environment variable
export CLAUDE_DEBUG=1

# Run command
/sc-github-issue --fix --issue 42

# Review detailed logs
```

### Check Agent Logs

```bash
# Agent output is shown in real-time
# Review for specific error codes and messages
```

### Validate GitHub CLI

```bash
# Check gh version
gh --version  # Should be >= 2.0

# Upgrade if needed
brew upgrade gh  # macOS
apt upgrade gh   # Linux
```

### Verify Repository State

```bash
# Clean state check
git status
git worktree list
git branch -a
gh repo view
```

---

## Getting Help

If issues persist:

1. **Check documentation**: [README.md](./README.md), [USE-CASES.md](./USE-CASES.md)
2. **Review logs**: Look for error codes and messages
3. **File an issue**: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
4. **Include context**:
   - Error message (full JSON)
   - Command executed
   - Configuration (sanitized)
   - Environment (OS, gh version, git version)

---

## Quick Reference

| Error Code | Quick Fix |
|------------|-----------|
| GH.AUTH.REQUIRED | `gh auth login` |
| WORKTREE.DIRTY | `git stash` or `git commit` |
| GH.RATE_LIMIT | Wait for reset |
| GH.BRANCH.NOT_PUSHED | `git push -u origin branch` |
| WORKTREE.ALREADY_EXISTS | `/sc-git-worktree --cleanup` |
| GH.PERMISSION_DENIED | Check repo access |
| TEST_FAILED | Review test output, answer "y" |
| GH.PR.ALREADY_EXISTS | Use existing PR or close and recreate |
