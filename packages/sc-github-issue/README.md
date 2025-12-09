# sc-github-issue

GitHub issue lifecycle management with worktree isolation for Claude Code.

## Overview

`sc-github-issue` provides a complete workflow for managing GitHub issues - from listing and creating issues to implementing fixes in isolated worktrees and creating pull requests. It integrates with `sc-git-worktree` to ensure fixes are implemented safely without affecting your main working directory.

## Features

- **List Issues**: Browse open/closed issues with filtering
- **Create/Update Issues**: Interactive issue management
- **Fix Workflow**: Automated fix implementation with:
  - Isolated worktree creation
  - Code analysis and implementation
  - Automated testing
  - Commit and push automation
  - Pull request creation with auto-linking
- **Safety Gates**: Approval prompts and pre-flight checks
- **Template Support**: Customizable PR templates

## Installation

### Prerequisites

- Claude Code CLI
- GitHub CLI (`gh`) version 2.0 or higher
- `sc-git-worktree` package (auto-installed as dependency)

### Install Package

```bash
sc-manage install sc-github-issue
```

This installs locally to your project (`.claude/packages/sc-github-issue/`).

## Usage

### List Issues

```bash
/sc-github-issue --list
/sc-github-issue --list --repo owner/repo
```

### Create Issue

```bash
/sc-github-issue --create
```

Prompts for title, body, labels, and assignees.

### Update Issue

```bash
/sc-github-issue --update 42
```

### Fix Issue (Full Workflow)

```bash
/sc-github-issue --fix --issue 42
/sc-github-issue --fix --issue https://github.com/owner/repo/issues/42
/sc-github-issue --fix --issue 42 --yolo  # Skip confirmation prompts
```

**Workflow steps:**
1. Fetches issue details and displays summary
2. Prompts for confirmation (unless `--yolo`)
3. Creates isolated worktree (`fix-issue-42`)
4. Implements fix, runs tests, commits
5. Pushes changes to remote
6. Creates pull request with auto-linking
7. Displays summary and PR URL

## Configuration

Configuration via manifest options (defaults shown):

```yaml
packages:
  sc-github-issue:
    base-branch: "main"              # Base branch for fix branches
    branch-pattern: "fix-issue-{number}"  # Branch naming pattern
    auto-pr: true                    # Auto-create PR after fix
```

Additional GitHub settings:

```yaml
github:
  test_command: "npm test"           # Optional: Command to run tests
  pr_template: |                     # Optional: PR body template
    ## Summary
    Fixes #{issue_number}

    ## Changes
    {commits}
```

## Architecture

### Agents

- **sc-github-issue-intake**: Read-only operations (list, fetch)
- **sc-github-issue-mutate**: Write operations (create, update)
- **sc-github-issue-fix**: Implement fixes in isolated worktrees
- **sc-github-issue-pr**: Create pull requests with auto-linking

### Dependencies

- `sc-git-worktree >= 0.6.0`: Worktree isolation
- `gh >= 2.0`: GitHub CLI for all operations

## Why Worktree Isolation?

The `--fix` workflow uses `sc-git-worktree` to create isolated worktrees:

**Benefits:**
- Main working directory remains clean
- No need to stash changes
- Safe parallel development
- Branch-specific environment

**Example:**
```
main/                    # Your main working directory (untouched)
worktrees/
  └── fix-issue-42/     # Isolated fix environment
```

After PR is merged, clean up with:
```bash
/sc-git-worktree --cleanup --worktree fix-issue-42
```

## Examples

### Fix Bug Report

```bash
# List bugs
/sc-github-issue --list

# Fix issue #42
/sc-github-issue --fix --issue 42

# Output:
# ✓ Issue #42: Application crashes on startup
# ✓ Worktree created: fix-issue-42
# ✓ Fix implemented
# ✓ Tests passed (15/15)
# ✓ Committed: abc123def
# ✓ PR created: https://github.com/owner/repo/pull/123
```

### Automated Workflow (CI/CD)

```bash
# Skip confirmation prompts
/sc-github-issue --fix --issue $ISSUE_NUMBER --yolo
```

## Safety Features

- **Pre-flight checks**: Validates `gh` auth, repo access, clean working tree
- **Approval gates**: Prompts before fix (unless `--yolo`)
- **Test failure prompts**: Asks for approval if tests fail
- **Protected branches**: Integrates with `sc-git-worktree` protected branch safeguards
- **Error recovery**: Actionable error messages with suggested fixes

## Error Handling

Common errors and solutions:

### Authentication Required
```
Error: GH.AUTH.REQUIRED
Solution: Run `gh auth login`
```

### Rate Limit Exceeded
```
Error: GH.RATE_LIMIT
Solution: Wait for rate limit reset or use authenticated requests
```

### Worktree Conflicts
```
Error: WORKTREE.DIRTY
Solution: Commit or stash changes, or use sc-git-worktree to clean up
```

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for more details.

## Version History

See [CHANGELOG.md](./CHANGELOG.md) for version history and migration notes.

## Support

- [Documentation](https://github.com/randlee/synaptic-canvas)
- [Issues](https://github.com/randlee/synaptic-canvas/issues)
- [Synaptic Canvas Marketplace](https://github.com/randlee/synaptic-canvas/tree/main/packages)

## License

MIT License - See repository root for details.
