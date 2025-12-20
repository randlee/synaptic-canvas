# Dependencies

Detailed explanation of `sc-github-issue` dependencies and integration requirements.

## Overview

`sc-github-issue` has both package dependencies (managed by Synaptic Canvas) and CLI dependencies (must be installed separately).

## Package Dependencies

### sc-git-worktree (>= 0.6.0)

**Required**: Yes
**Type**: Hard dependency
**Install Scope**: Local-only
**Auto-installed**: Yes

#### Purpose

The `sc-git-worktree` package provides isolated worktree management for the `--fix` workflow. When you run `/sc-github-issue --fix --issue 42`, it:

1. Creates an isolated worktree (`fix-issue-42`)
2. Implements the fix in that isolated environment
3. Commits and pushes from the worktree
4. Leaves your main working directory completely untouched

#### Why Worktree Isolation?

**Without worktrees:**
```bash
# Main directory gets contaminated
git checkout -b fix-issue-42  # Changes main directory
# Implement fix
git add . && git commit
git push
# Must switch back
git checkout main
```

**With worktrees:**
```bash
# Main directory stays clean
/sc-github-issue --fix --issue 42
# Creates ../worktrees/fix-issue-42
# All work happens there
# Main directory: no changes
```

**Benefits:**
- **No branch switching**: Main directory stays on current branch
- **No stashing**: Your work-in-progress is never disturbed
- **Parallel fixes**: Multiple fixes can run simultaneously
- **Clean environment**: Each fix has isolated dependencies

#### Version Requirement

- **Minimum**: 0.6.0
- **Reason**: v0.6.0 adds protected branch safeguards

**Protected Branch Features (v0.6.0+):**
- Prevents accidental deletion of `main`, `develop`, `master`
- Cleanup operations never delete protected branches
- Abort operations require explicit approval for protected branches
- Configuration via `git_flow` settings

#### Configuration

`sc-git-worktree` configuration in `.claude/config.yaml`:

```yaml
packages:
  sc-git-worktree:
    root: ../worktrees           # Where worktrees are created
    tracking:
      enabled: true              # Track worktree metadata
      file: .claude/state/worktrees.jsonl
    git_flow:
      enabled: true
      main_branch: "main"
      develop_branch: "develop"
    protected_branches:          # Never deleted
      - "main"
      - "develop"
      - "master"
```

#### Integration Points

**Create Worktree:**
```bash
# sc-github-issue invokes:
Task(
  subagent_type="sc-worktree-create",
  prompt={
    "branch": "fix-issue-42",
    "base_branch": "main",
    "create_branch": true
  }
)
```

**Cleanup After Merge:**
```bash
# User runs manually after PR merge:
/sc-git-worktree --cleanup --worktree fix-issue-42
```

#### Troubleshooting

**Issue**: Worktree creation fails
```bash
# Check sc-git-worktree is installed
sc-manage list

# Install if missing
sc-manage install sc-git-worktree

# Verify version
cat .claude/packages/sc-git-worktree/manifest.yaml | grep version
```

**Issue**: Protected branch error
```yaml
# Ensure protected branches configured
packages:
  sc-git-worktree:
    protected_branches: ["main", "develop", "master"]
```

---

## CLI Dependencies

### GitHub CLI (gh)

**Required**: Yes
**Minimum Version**: 2.0
**Type**: External CLI tool

#### Installation

**macOS:**
```bash
brew install gh
```

**Linux:**
```bash
# Debian/Ubuntu
sudo apt install gh

# Fedora/RHEL
sudo dnf install gh

# Arch
sudo pacman -S github-cli
```

**Windows:**
```powershell
winget install --id GitHub.cli
```

**Verify installation:**
```bash
gh --version
# Should output: gh version 2.0.0 or higher
```

#### Authentication

**First-time setup:**
```bash
gh auth login
```

**Options:**
1. **GitHub.com** or **GitHub Enterprise**
2. **HTTPS** or **SSH**
3. **Login with browser** or **paste token**

**Verify:**
```bash
gh auth status

# Output should show:
# ✓ Logged in to github.com as username
# ✓ Token: *******************
```

#### Required Permissions

The `gh` token needs these scopes:
- `repo`: Full repository access (read/write issues, PRs)
- `workflow`: Workflow management (if using CI/CD)

**Refresh scopes:**
```bash
gh auth refresh --scopes repo,workflow
```

#### Usage in sc-github-issue

**List Issues:**
```bash
gh issue list \
  --repo owner/repo \
  --state open \
  --json number,title,labels,assignees
```

**Create Issue:**
```bash
gh issue create \
  --repo owner/repo \
  --title "Issue title" \
  --body "Description" \
  --label bug,enhancement
```

**Create PR:**
```bash
gh pr create \
  --repo owner/repo \
  --base main \
  --head fix-issue-42 \
  --title "Fix #42: Title" \
  --body "Fixes #42"
```

#### Troubleshooting

**Issue**: `gh: command not found`
```bash
# Install gh CLI
brew install gh  # or apt/dnf/pacman

# Verify
which gh
```

**Issue**: Authentication error
```bash
# Re-authenticate
gh auth logout
gh auth login

# Check status
gh auth status
```

**Issue**: Insufficient permissions
```bash
# Refresh with correct scopes
gh auth refresh --scopes repo,workflow
```

**Issue**: Rate limit exceeded
```bash
# Check rate limit
gh api rate_limit

# Wait for reset or use authenticated requests
```

---

## Git

**Required**: Yes
**Minimum Version**: 2.25 (for worktree support)
**Type**: System dependency

#### Installation

Usually pre-installed on most systems. If not:

**macOS:**
```bash
brew install git
```

**Linux:**
```bash
sudo apt install git  # Debian/Ubuntu
sudo dnf install git  # Fedora/RHEL
```

**Verify:**
```bash
git --version
# Should output: git version 2.25.0 or higher
```

#### Required Git Configuration

```bash
# User identity (required for commits)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Default branch (recommended)
git config --global init.defaultBranch main

# Worktree prune (optional but recommended)
git config --global gc.worktreePruneExpire "30.days.ago"
```

---

## Optional Dependencies

### Node.js / npm (for test_command)

If using `test_command: "npm test"`:

**Installation:**
```bash
# macOS
brew install node

# Linux
sudo apt install nodejs npm
```

**Verify:**
```bash
node --version
npm --version
```

### Python / pytest (for test_command)

If using `test_command: "pytest"`:

**Installation:**
```bash
pip install pytest
```

### Other Test Frameworks

Configure according to your project:
```yaml
github:
  test_command: "cargo test"     # Rust
  test_command: "go test ./..."  # Go
  test_command: "mvn test"       # Java/Maven
  test_command: "./run-tests.sh" # Custom script
```

---

## Dependency Version Matrix

| Dependency | Minimum | Recommended | Required |
|------------|---------|-------------|----------|
| sc-git-worktree | 0.6.0 | 0.6.0+ | Yes |
| gh (GitHub CLI) | 2.0 | Latest | Yes |
| git | 2.25 | Latest | Yes |
| Node.js/npm | Any | LTS | Optional |
| Python/pytest | Any | Latest | Optional |

---

## Dependency Installation Script

Complete setup script:

```bash
#!/bin/bash
# install-sc-github-issue-deps.sh

set -e

echo "Installing sc-github-issue dependencies..."

# 1. Check git
if ! command -v git &> /dev/null; then
  echo "Installing git..."
  brew install git  # Adjust for your OS
fi
git --version

# 2. Check gh CLI
if ! command -v gh &> /dev/null; then
  echo "Installing GitHub CLI..."
  brew install gh  # Adjust for your OS
fi
gh --version

# 3. Authenticate gh
echo "Authenticating GitHub CLI..."
gh auth login

# 4. Install sc-git-worktree (if not already)
echo "Installing sc-git-worktree..."
sc-manage install sc-git-worktree

# 5. Install sc-github-issue
echo "Installing sc-github-issue..."
sc-manage install sc-github-issue

echo "✓ All dependencies installed!"
echo ""
echo "Next steps:"
echo "1. Configure .claude/config.yaml"
echo "2. Run: /sc-github-issue --list"
```

---

## Dependency Verification

Quick verification checklist:

```bash
# 1. Package dependencies
sc-manage list | grep sc-github-issue  # Should show v0.6.0
sc-manage list | grep sc-git-worktree  # Should show v0.6.0

# 2. CLI dependencies
gh --version    # >= 2.0
git --version   # >= 2.25

# 3. Authentication
gh auth status  # Should show logged in

# 4. Configuration
cat .claude/config.yaml  # Verify package config exists

# 5. Test installation
/sc-github-issue --list  # Should list issues or show auth error
```

---

## Upgrading Dependencies

### Upgrade Package Dependencies

```bash
# Update sc-git-worktree
sc-manage upgrade sc-git-worktree

# Update sc-github-issue
sc-manage upgrade sc-github-issue
```

### Upgrade CLI Dependencies

```bash
# Upgrade gh
brew upgrade gh  # macOS
sudo apt update && sudo apt upgrade gh  # Linux

# Upgrade git
brew upgrade git  # macOS
sudo apt update && sudo apt upgrade git  # Linux
```

---

## Removing Dependencies

### Uninstall Package

```bash
# Uninstall sc-github-issue
sc-manage uninstall sc-github-issue

# sc-git-worktree remains (may be used by other packages)
# To remove it too:
sc-manage uninstall sc-git-worktree
```

### CLI Dependencies

```bash
# GitHub CLI (optional - may be used by other tools)
brew uninstall gh  # macOS
sudo apt remove gh  # Linux

# Git (NOT recommended - system dependency)
```

---

## Integration Testing

Test full dependency chain:

```bash
# 1. Test git
git status

# 2. Test gh
gh auth status
gh repo view

# 3. Test sc-git-worktree
/sc-git-worktree --scan

# 4. Test sc-github-issue
/sc-github-issue --list

# 5. Test full workflow
/sc-github-issue --fix --issue <number> --yolo
```

---

## Dependency Conflicts

### Version Conflicts

If you have older versions:

```bash
# Check installed versions
sc-manage list

# Upgrade to v0.6.0
sc-manage upgrade sc-git-worktree
sc-manage upgrade sc-github-issue
```

### Path Conflicts

If `gh` command not found:

```bash
# Add to PATH
export PATH="/usr/local/bin:$PATH"

# Or use full path
/usr/local/bin/gh --version
```

---

## Support

For dependency issues:
- **Package dependencies**: File issue at [Synaptic Canvas](https://github.com/randlee/synaptic-canvas/issues)
- **GitHub CLI**: See [gh documentation](https://cli.github.com/manual/)
- **Git**: See [git documentation](https://git-scm.com/doc)
