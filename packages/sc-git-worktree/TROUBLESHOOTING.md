# sc-git-worktree Troubleshooting Guide

This guide helps diagnose and resolve common issues with the sc-git-worktree package for Synaptic Canvas.

## Quick Diagnostics

Run these commands to verify your setup:

```bash
# Verify git version (requires >= 2.20)
git --version

# Check if sc-git-worktree package is installed
ls -la .claude/commands/sc-git-worktree.md
ls -la .claude/skills/sc-managing-worktrees/

# List existing worktrees
git worktree list

# Check tracking document (if enabled)
ls -la ../$(basename $(git rev-parse --show-toplevel))-worktrees/worktree-tracking.md

# Verify repo name token expansion
basename $(git rev-parse --show-toplevel)

# Check agent registry
cat .claude/agents/registry.yaml | grep worktree
```

## Common Issues

### 1. Command Not Found: `/sc-git-worktree` Not Recognized

**Problem:** When you run `/sc-git-worktree`, Claude doesn't recognize the command.

**Symptoms:**
```
Unknown command: /sc-git-worktree
```

**Root Causes:**
- Package only installed globally (requires local installation)
- Not inside a git repository
- Installation path incorrect

**Resolution:**

1. Verify you're in a git repository:
```bash
git rev-parse --git-dir
# Should output: .git
```

2. Install locally (sc-git-worktree is local-only):
```bash
# WRONG - global install not supported
python3 tools/sc-install.py install sc-git-worktree --dest ~/Documents/.claude

# CORRECT - local install
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude
```

3. Verify installation:
```bash
ls .claude/commands/sc-git-worktree.md
ls .claude/agents/worktree-*.md
```

4. If missing, reinstall:
```bash
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude
```

**Prevention:**
- sc-git-worktree is local-only by design (repo-specific operations)
- Always install in the repository's `.claude` directory

---

### 2. Tracking File Corruption

**Problem:** Tracking document becomes corrupted or contains invalid data.

**Symptoms:**
```
Error: Cannot parse tracking document
Tracking row format invalid
Duplicate branch entries in tracking
```

**Root Causes:**
- Manual edits breaking Markdown table format
- Concurrent updates from multiple agents
- Partial writes due to interruption

**Resolution:**

1. **Check tracking file format:**
```bash
TRACKING_FILE="../$(basename $(git rev-parse --show-toplevel))-worktrees/worktree-tracking.md"
cat "$TRACKING_FILE"
```

Expected format:
```markdown
# Worktree Tracking

| Branch | Path | Base | Purpose | Owner | Created | Status | LastChecked | Notes |
|--------|------|------|---------|-------|---------|--------|-------------|-------|
| feature-x | ../repo-worktrees/feature-x | main | Feature X | user | 2025-12-02T10:00:00Z | active | 2025-12-02T10:00:00Z | |
```

2. **Fix formatting issues:**
```bash
# Backup first
cp "$TRACKING_FILE" "$TRACKING_FILE.backup"

# Manually edit to fix table alignment
# Ensure all rows have 9 pipe-separated columns
nano "$TRACKING_FILE"
```

3. **Remove duplicates:**
```bash
# Find duplicate branches
awk -F'|' 'NR>2 {print $2}' "$TRACKING_FILE" | sort | uniq -d
```

4. **Regenerate if severely corrupted:**
```bash
# Backup and remove
mv "$TRACKING_FILE" "$TRACKING_FILE.old"

# Scan worktrees to rebuild
/sc-git-worktree --scan
```

**Prevention:**
- Don't manually edit tracking file during agent operations
- Use `/sc-git-worktree --scan` to rebuild from actual worktrees
- Enable tracking only if you need audit trail

---

### 3. Worktree Lock Issues

**Problem:** Cannot create or remove worktree due to locks.

**Symptoms:**
```
fatal: 'worktrees/feature-x' is already locked
fatal: another git process seems to be running in this repository
```

**Root Causes:**
- Previous git operation crashed or was interrupted
- Stale lock files from abnormal termination
- Concurrent git operations in same worktree

**Resolution:**

1. **Check for lock files:**
```bash
# Main repo locks
ls -la .git/*.lock
ls -la .git/worktrees/*/locked

# Worktree-specific locks
WORKTREE_PATH="../$(basename $(git rev-parse --show-toplevel))-worktrees/feature-x"
ls -la "$WORKTREE_PATH/.git"
```

2. **Remove stale locks (CAUTION):**
```bash
# Only if you're SURE no git operations are running
rm -f .git/*.lock
rm -f .git/worktrees/*/locked

# For specific worktree
rm -f .git/worktrees/feature-x/locked
```

3. **Check for running git processes:**
```bash
ps aux | grep git
```

4. **If worktree administrative entry is locked:**
```bash
# Unlock specific worktree
git worktree unlock feature-x

# Or by path
git worktree unlock ../repo-worktrees/feature-x
```

5. **Force unlock if necessary:**
```bash
# Use with caution
rm -f .git/worktrees/*/locked
```

**Prevention:**
- Always let git operations complete
- Don't Ctrl+C during git commands
- Use `/sc-git-worktree --abort` for safe cancellation

---

### 4. Path Already Exists Error

**Problem:** Cannot create worktree because target path exists.

**Symptoms:**
```
fatal: 'path/to/worktree' already exists
Error: worktree path exists with content
```

**Root Causes:**
- Previous worktree not cleaned up properly
- Directory created manually
- Partial cleanup from failed operation

**Resolution:**

1. **Check what exists at the path:**
```bash
WORKTREE_PATH="../$(basename $(git rev-parse --show-toplevel))-worktrees/feature-x"
ls -la "$WORKTREE_PATH"
```

2. **If it's a valid worktree:**
```bash
# List all worktrees
git worktree list

# If listed, use existing worktree
cd "$WORKTREE_PATH"

# Or remove properly
/sc-git-worktree --cleanup feature-x
```

3. **If it's not registered but directory exists:**
```bash
# Check git's worktree registry
git worktree list | grep feature-x

# If not listed, it's orphaned - safe to remove manually
rm -rf "$WORKTREE_PATH"
```

4. **If it's a different branch's worktree:**
```bash
# List what branch it contains
cd "$WORKTREE_PATH"
git branch --show-current

# If wrong branch, go back to main repo and prune
cd -
git worktree prune
```

5. **Force cleanup (CAUTION - data loss risk):**
```bash
# Backup first
cp -r "$WORKTREE_PATH" "$WORKTREE_PATH.backup"

# Remove directory
rm -rf "$WORKTREE_PATH"

# Remove git's tracking
git worktree prune
```

**Prevention:**
- Always use `/sc-git-worktree --cleanup` or `--abort` to remove worktrees
- Never manually delete worktree directories without `git worktree remove`
- Check path before creating: `ls -la ../repo-worktrees/`

---

### 5. Branch Protection Conflicts

**Problem:** Cannot push or modify protected branches in worktree.

**Symptoms:**
```
remote: error: GH006: Protected branch update failed
! [remote rejected] main -> main (protected branch hook declined)
```

**Root Causes:**
- Attempting to push directly to protected branch (main, master, develop)
- Branch protection rules on remote repository
- Creating worktree from protected branch base

**Resolution:**

1. **Check branch protection status:**
```bash
# Via GitHub CLI (if available)
gh api repos/:owner/:repo/branches/main/protection

# Or check remote rules
git ls-remote --heads origin
```

2. **Never commit directly to protected branches:**
```bash
# WRONG - creating worktree for main
/sc-git-worktree --create main main

# CORRECT - create feature branch from main
/sc-git-worktree --create feature-x main
```

3. **If accidentally in protected branch:**
```bash
cd worktree-path
git checkout -b feature-x  # Create new branch
git push origin feature-x  # Push to new branch
```

4. **Use proper workflow:**
```bash
# Create feature branches from protected base
/sc-git-worktree --create feature-123 main
/sc-git-worktree --create hotfix-456 release/1.0
```

**Prevention:**
- Never create worktrees directly on protected branches
- Always branch from protected branches (main, master, develop, release/*)
- Follow repository's branching strategy

---

### 6. Dirty Worktree Preventing Operations

**Problem:** Cannot cleanup or abort because worktree has uncommitted changes.

**Symptoms:**
```
Error: worktree has uncommitted changes
fatal: worktree contains modified or untracked files
worktree.dirty: cannot proceed
```

**Root Causes:**
- Uncommitted changes in worktree
- Untracked files present
- Stash applied but not committed

**Resolution:**

1. **Check status:**
```bash
cd ../repo-worktrees/feature-x
git status
```

2. **Commit changes:**
```bash
git add .
git commit -m "WIP: feature progress"
git push origin feature-x
```

3. **Stash changes:**
```bash
git stash push -m "WIP feature-x"
# Note: stash is tied to this worktree
```

4. **Discard changes (CAUTION - data loss):**
```bash
# Discard uncommitted changes
git reset --hard HEAD

# Remove untracked files
git clean -fd
```

5. **Return to main repo and cleanup:**
```bash
cd -  # Back to main repo
/sc-git-worktree --cleanup feature-x
```

**Prevention:**
- Commit or stash before cleanup operations
- Use `git status` to check cleanliness
- Enable git hooks to prevent dirty commits

---

### 7. REPO_NAME Token Not Expanding

**Problem:** Token `{{REPO_NAME}}` not replaced during installation.

**Symptoms:**
```
Path created: ../{{REPO_NAME}}-worktrees/feature-x
Error: directory not found: ../{{REPO_NAME}}-worktrees
```

**Root Causes:**
- Installation used `--no-expand` flag
- Not inside git repository during installation
- Git not detecting repository name correctly

**Resolution:**

1. **Check if tokens are expanded:**
```bash
# Check installed files for tokens
grep -r "{{REPO_NAME}}" .claude/
```

2. **Verify repository detection:**
```bash
# Get repo name
basename $(git rev-parse --show-toplevel)

# Should output your repo name, e.g., "my-repo"
```

3. **Reinstall with expansion:**
```bash
# Ensure you're in the repo root
git rev-parse --show-toplevel

# Reinstall (expansion is default)
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude --force
```

4. **Manual fix (if needed):**
```bash
# Find actual repo name
REPO=$(basename $(git rev-parse --show-toplevel))

# Replace tokens in installed files
find .claude/ -type f -exec sed -i.bak "s/{{REPO_NAME}}/$REPO/g" {} \;

# Clean up backup files
find .claude/ -name "*.bak" -delete
```

**Prevention:**
- Always install from within the repository
- Don't use `--no-expand` flag
- Verify git is working: `git status`

---

### 8. Cleanup Failures

**Problem:** `/sc-git-worktree --cleanup` fails to remove worktree.

**Symptoms:**
```
Error: cannot remove worktree
fatal: validation failed, cannot remove working tree
Cleanup incomplete: worktree still exists
```

**Root Causes:**
- Worktree is locked
- Directory has open file handles
- Permission issues
- Worktree is dirty

**Resolution:**

1. **Check worktree status:**
```bash
git worktree list
```

2. **Navigate to worktree and check:**
```bash
cd ../repo-worktrees/feature-x
git status
lsof +D .  # Check for open files (macOS/Linux)
```

3. **Close all programs using the worktree:**
```bash
# Find processes
lsof +D ../repo-worktrees/feature-x

# Or on Linux
fuser -v ../repo-worktrees/feature-x
```

4. **Try cleanup again:**
```bash
cd -  # Back to main repo
/sc-git-worktree --cleanup feature-x
```

5. **Force cleanup (CAUTION):**
```bash
# Remove git's tracking first
git worktree remove --force feature-x

# Then remove directory if still exists
rm -rf ../repo-worktrees/feature-x

# Prune stale entries
git worktree prune
```

6. **Fix permissions if needed:**
```bash
# Grant permissions
chmod -R u+rwX ../repo-worktrees/feature-x

# Then retry cleanup
```

**Prevention:**
- Close editors and terminals before cleanup
- Commit or stash changes first
- Use `--abort` for safer cancellation during development

---

## Installation & Setup Issues

### Git Version Too Old

**Problem:**
```bash
git worktree: command not supported
fatal: unknown option: worktree
```

**Resolution:**

1. Check git version:
```bash
git --version
# Requires >= 2.20
```

2. Upgrade git:

**macOS:**
```bash
brew update
brew upgrade git
```

**Linux (Ubuntu/Debian):**
```bash
sudo add-apt-repository ppa:git-core/ppa
sudo apt update
sudo apt install git
```

**Windows:**
- Download latest from [git-scm.com](https://git-scm.com/downloads)

3. Verify upgrade:
```bash
git --version
git worktree --help
```

---

### Not in a Git Repository

**Problem:**
```bash
fatal: not a git repository (or any of the parent directories): .git
```

**Resolution:**

1. Verify you're in a git repo:
```bash
git status
```

2. If not initialized:
```bash
git init
```

3. Or navigate to correct directory:
```bash
cd /path/to/your/repo
git status  # Verify
```

---

### Installation Path Incorrect

**Problem:**
```bash
Package installed to ~/Documents/.claude but commands not found
```

**Resolution:**

sc-git-worktree is **local-only**:
```bash
# WRONG - global install
python3 tools/sc-install.py install sc-git-worktree --dest ~/Documents/.claude

# CORRECT - local install
cd /path/to/your/repo
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude
```

---

## Configuration Issues

### Worktree Base Directory Issues

**Problem:** Worktrees created in wrong location.

**Resolution:**

1. Default structure (automatic):
```
your-repo/              # Main repository
your-repo-worktrees/    # Worktree container (sibling)
  ├── feature-x/        # Individual worktrees
  ├── feature-y/
  └── worktree-tracking.md
```

2. Verify expected path:
```bash
REPO=$(basename $(git rev-parse --show-toplevel))
echo "../${REPO}-worktrees"
```

3. If worktrees in wrong location, you may have:
- Modified agent files manually
- Token expansion not applied
- See "REPO_NAME Token Not Expanding" above

---

### Tracking Disabled But File Exists

**Problem:** Tracking document exists but agents don't update it.

**Resolution:**

1. Check agent configuration:
```bash
grep -A5 "tracking_enabled" .claude/agents/worktree-*.md
```

2. Tracking is enabled by default. To disable:
```bash
# Edit agent invocation to pass tracking_enabled: false
# This requires modifying the skill or command
```

3. Or manually manage:
```bash
# Keep tracking file but manage manually
# Agents won't touch it if tracking_enabled=false
```

---

### Branch Naming Conflicts

**Problem:** Branch names conflict with filesystem paths.

**Resolution:**

Avoid problematic branch names:
```bash
# AVOID - filesystem conflicts
feature/new-thing  # Contains slash
main.backup        # Hidden file confusion
-hotfix            # Starts with dash

# PREFER
feature-new-thing
main-backup
hotfix-123
```

---

## Integration Issues

### Using with Remote Repositories

**Problem:** Worktrees not pushing to remote.

**Resolution:**

1. Each worktree is independent:
```bash
cd ../repo-worktrees/feature-x
git remote -v  # Should show same remotes as main repo
```

2. Push from worktree:
```bash
cd ../repo-worktrees/feature-x
git push origin feature-x
```

3. If remote missing, add:
```bash
git remote add origin <url>
```

---

### Using with Multiple Users

**Problem:** Tracking conflicts in shared repositories.

**Resolution:**

1. **Tracking is local** (not committed to git):
```bash
# tracking.md is in ../repo-worktrees/, not in repo
ls -la ../repo-worktrees/worktree-tracking.md
```

2. Each user has own tracking file.

3. For team coordination, commit to repo:
```bash
# Create team tracking in repo
mkdir -p .worktrees
touch .worktrees/team-tracking.md
git add .worktrees/team-tracking.md
git commit -m "docs: add team worktree tracking"
```

---

### Using with CI/CD

**Problem:** CI systems can't use worktrees effectively.

**Resolution:**

1. **Worktrees are for local development only**
   - Don't use in CI pipelines
   - CI should use fresh clones

2. For CI that needs multiple branches:
```bash
# Use separate clones, not worktrees
git clone <url> repo-main
git clone <url> repo-feature
```

---

## Performance & Timeout Issues

### Large Repositories

**Problem:** Worktree operations slow in large repos.

**Resolution:**

1. Use shallow clones:
```bash
# Initial clone
git clone --depth 1 <url>

# Worktrees inherit from main repo
# Performance improved via shared .git
```

2. Limit fetch operations:
```bash
# Don't fetch all remotes
git fetch origin

# Instead of
git fetch --all
```

3. Use sparse checkout if needed:
```bash
cd ../repo-worktrees/feature-x
git sparse-checkout init --cone
git sparse-checkout set src/
```

---

### Many Worktrees

**Problem:** Managing dozens of worktrees becomes unwieldy.

**Resolution:**

1. Regularly cleanup inactive worktrees:
```bash
# List all
git worktree list

# Remove unused
/sc-git-worktree --cleanup old-feature-1
/sc-git-worktree --cleanup old-feature-2
```

2. Use tracking to audit:
```bash
# Review tracking document
cat ../repo-worktrees/worktree-tracking.md
```

3. Prune stale entries:
```bash
git worktree prune -v
```

---

## Platform-Specific Issues

### macOS Issues

**Problem:** Case-insensitive filesystem causes conflicts.

**Resolution:**

1. Be careful with branch names:
```bash
# AVOID - seen as same on macOS default filesystem
feature-Test
feature-test
```

2. For case-sensitive needs:
```bash
# Create case-sensitive APFS volume
diskutil apfs addVolume disk1 "Case-sensitive APFS" RepoVolume
```

---

### Linux Issues

**Problem:** Permissions differ from macOS.

**Resolution:**

1. Ensure executable permissions:
```bash
chmod +x .claude/scripts/*.sh 2>/dev/null || true
```

2. Check ownership:
```bash
ls -la ../repo-worktrees/
# Should match your user
```

---

### Windows Issues

**Problem:** Path separators and Git Bash interactions.

**Resolution:**

1. Use Git Bash (comes with Git for Windows):
```bash
# Always use forward slashes
cd ../repo-worktrees/feature-x
```

2. Or use WSL:
```bash
# Better Linux compatibility
wsl
cd /mnt/c/path/to/repo
```

3. Watch for line endings:
```bash
git config core.autocrlf true
```

---

## Getting Help

### When to Escalate

Escalate to GitHub issues if you encounter:

- Tracking file corruption that can't be resolved
- Git worktree commands failing unexpectedly
- Token expansion not working after reinstall
- Data loss from cleanup operations
- Integration issues with git hooks or remotes

### How to Report Bugs

Include the following information:

1. **Environment details:**
```bash
git --version
python3 --version
uname -a  # or systeminfo on Windows
basename $(git rev-parse --show-toplevel)
```

2. **Installation details:**
```bash
ls -la .claude/commands/sc-git-worktree.md
ls -la .claude/agents/worktree-*.md
cat .claude/agents/registry.yaml | grep worktree
```

3. **Git worktree state:**
```bash
git worktree list
git branch -a
ls -la ../$(basename $(git rev-parse --show-toplevel))-worktrees/
```

4. **Command that failed:**
```bash
# Exact command
/sc-git-worktree --create feature-x main
```

5. **Error output:**
```
# Full error message
```

6. **Tracking document (if applicable):**
```bash
cat ../repo-worktrees/worktree-tracking.md
```

### Debug Information to Collect

**Basic diagnostics:**
```bash
# Git and repo info
git --version
git worktree list
git status
git remote -v

# Installation check
ls -la .claude/commands/sc-git-worktree.md
ls -la .claude/agents/worktree-*.md
ls -la .claude/skills/sc-managing-worktrees/

# Token expansion check
grep -r "{{REPO_NAME}}" .claude/ || echo "No tokens found (good)"
```

**For worktree issues:**
```bash
# List all worktrees
git worktree list

# Check specific worktree
cd ../repo-worktrees/feature-x
git status
git log --oneline -5
cd -

# Check git internals
ls -la .git/worktrees/
```

**For tracking issues:**
```bash
# Show tracking file
TRACKING="../$(basename $(git rev-parse --show-toplevel))-worktrees/worktree-tracking.md"
cat "$TRACKING"

# Verify format
head -5 "$TRACKING"
```

---

## FAQ

### Q: Can I use worktrees outside the default sibling folder?

**A:** The sc-git-worktree package enforces a standard layout for consistency:
```
parent/
  ├── your-repo/           # Main repo
  └── your-repo-worktrees/ # Worktrees container
```

For custom paths, use git commands directly:
```bash
git worktree add /custom/path/feature-x feature-x
```

But you'll lose tracking and agent management features.

---

### Q: What happens if I delete a worktree directory manually?

**A:**
- Git still tracks it: `git worktree list` shows it
- Path is broken
- Fix with: `git worktree prune`

**Always use:**
```bash
/sc-git-worktree --cleanup branch-name
# or
git worktree remove path/to/worktree
```

---

### Q: Can I move a worktree to a different location?

**A:** No, worktrees are tied to their path. To "move":
1. Commit and push all changes
2. Cleanup old worktree: `/sc-git-worktree --cleanup old-branch`
3. Create new worktree at new location (requires custom git commands)

Or just create a new worktree and delete the old one.

---

### Q: How do worktrees handle remotes?

**A:**
- Worktrees share the same `.git/` with main repo
- All remotes are identical
- Fetch in main repo updates all worktrees
- Push from any worktree affects the remote

---

### Q: Can I have the same branch in multiple worktrees?

**A:** No, git prevents this:
```bash
fatal: 'feature-x' is already checked out at '../repo-worktrees/feature-x'
```

One branch = one worktree (or main repo) at a time.

---

### Q: What's the difference between `--cleanup` and `--abort`?

**A:**
- `--cleanup`: Remove completed worktree (expects clean state, removes branch)
- `--abort`: Cancel in-progress work (handles dirty state, preserves branch)

Use `--cleanup` when done with a feature.
Use `--abort` when canceling exploratory work.

---

### Q: Do worktrees affect git performance?

**A:** Generally positive:
- Faster than cloning (shares objects)
- No network needed to switch contexts
- Minimal disk overhead

But many worktrees (>20) may slow down some operations.

---

### Q: Can I use sc-git-worktree for monorepos?

**A:** Yes, excellent for monorepos:
- Work on multiple features simultaneously
- Test integration locally
- Each worktree can have different build artifacts

But tracking may become verbose with many worktrees.

---

### Q: How do I update sc-git-worktree package?

**A:**
```bash
# Pull latest changes
cd /path/to/synaptic-canvas
git pull origin main

# Reinstall (force overwrites existing)
cd /path/to/your/repo
python3 /path/to/synaptic-canvas/tools/sc-install.py \
  install sc-git-worktree --dest ./.claude --force
```

---

### Q: Can I commit the worktree tracking file to git?

**A:** Not recommended:
- Tracking is in `../repo-worktrees/` (outside repo)
- Intended as local developer tool
- Conflicts if multiple devs use worktrees

For team coordination, create separate tracking in-repo:
```bash
mkdir .worktrees
# Add team tracking here
git add .worktrees/
```

---

## Additional Resources

- **Package README:** `packages/sc-git-worktree/README.md`
- **Use Cases:** `packages/sc-git-worktree/USE-CASES.md`
- **Changelog:** `packages/sc-git-worktree/CHANGELOG.md`
- **Skill Documentation:** `packages/sc-git-worktree/skills/sc-managing-worktrees/SKILL.md`
- **Agent Specifications:**
  - `packages/sc-git-worktree/agents/sc-worktree-create.md`
  - `packages/sc-git-worktree/agents/sc-worktree-scan.md`
  - `packages/sc-git-worktree/agents/sc-worktree-cleanup.md`
  - `packages/sc-git-worktree/agents/sc-worktree-abort.md`
- **Git Worktree Docs:** `git help worktree`
- **Repository:** https://github.com/randlee/synaptic-canvas
- **Issues:** https://github.com/randlee/synaptic-canvas/issues
