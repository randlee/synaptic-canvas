# sc-manage Troubleshooting Guide

This guide helps diagnose and resolve common issues with the sc-manage package for Synaptic Canvas.

## Quick Diagnostics

Run these commands to verify your setup:

```bash
# Verify Python 3 is available
python3 --version

# Check if sc-manage is installed (global)
ls -la ~/Documents/.claude/commands/sc-manage.md
ls -la ~/Documents/.claude/agents/sc-*.md

# Check if sc-manage is installed (local)
ls -la .claude/commands/sc-manage.md

# Verify git is available (required for local installs)
git --version

# List available packages
python3 tools/sc-install.py list

# Check agent registry
cat .claude/agents/registry.yaml 2>/dev/null || echo "No registry"
```

## Common Issues

### 1. Command Not Found: `/sc-manage` Not Recognized

**Problem:** When you run `/sc-manage`, Claude doesn't recognize the command.

**Symptoms:**
```
Unknown command: /sc-manage
```

**Root Causes:**
- Package not installed
- Installed in wrong scope (local vs global)
- Claude not detecting `.claude/commands/` directory

**Resolution:**

1. Verify installation location:
```bash
# For global use (recommended)
ls ~/Documents/.claude/commands/sc-manage.md

# For local use (inside repo)
ls .claude/commands/sc-manage.md
```

2. Install globally (recommended):
```bash
python3 tools/sc-install.py install sc-manage --dest ~/Documents/.claude
```

3. Or install locally (if in a repo):
```bash
python3 tools/sc-install.py install sc-manage --dest ./.claude
```

4. Restart Claude or refresh command index.

**Prevention:**
- Install globally for package management from anywhere
- Verify `~/Documents/.claude` exists and is writable

---

### 2. Package Discovery Failures

**Problem:** `/sc-manage --list` shows no packages or incomplete list.

**Symptoms:**
```
Available packages:

(empty list)
```
or
```
No packages found
```

**Root Causes:**
- Running from wrong directory
- Repository structure incorrect
- Missing manifest.yaml files

**Resolution:**

1. Verify you're in Synaptic Canvas repository:
```bash
# Should list package directories
ls packages/
# Expected: sc-delay-tasks/ sc-git-worktree/ sc-manage/ sc-repomix-nuget/
```

2. Check manifest files exist:
```bash
# Each package should have manifest.yaml
find packages/ -name "manifest.yaml"
```

3. If missing manifests:
```bash
# Clone/update repository
git pull origin main

# Verify structure
tree -L 2 packages/
```

4. Test package listing directly:
```bash
python3 tools/sc-install.py list
```

**Prevention:**
- Keep repository structure intact
- Don't move or delete package directories
- Pull latest changes regularly: `git pull`

---

### 3. Installation Permission Issues

**Problem:** Installation fails with permission errors.

**Symptoms:**
```
Permission denied: '/Users/username/Documents/.claude'
PermissionError: [Errno 13] Permission denied
```

**Root Causes:**
- Target directory not writable
- System-level permission restrictions
- Directory owned by different user

**Resolution:**

1. Check directory permissions:
```bash
ls -la ~/Documents/.claude
```

2. If directory doesn't exist, create it:
```bash
mkdir -p ~/Documents/.claude
```

3. If permission denied, fix ownership:
```bash
# Check ownership
ls -la ~/Documents/ | grep .claude

# Fix if needed (replace 'username' with your username)
sudo chown -R username:staff ~/Documents/.claude
```

4. Ensure write permissions:
```bash
chmod u+rwX ~/Documents/.claude
```

5. For local installs, verify repo permissions:
```bash
ls -la .claude/
chmod -R u+rwX .claude/
```

**Prevention:**
- Create `.claude` directory manually if needed
- Don't use sudo for installation (installs to user directory)
- Check permissions before installing

---

### 4. Version Conflicts

**Problem:** Package version doesn't match expected version.

**Symptoms:**
```
version mismatch for agent delay-once: frontmatter=0.3.0 repo=0.4.0
Error: Agent version conflict detected
```

**Root Causes:**
- Installing from different repository versions
- Mixed versions from multiple sources
- Cached old package files

**Resolution:**

1. Check repository version:
```bash
cat version.yaml
# Should show current version (e.g., 0.4.0)
```

2. Verify installed agent versions:
```bash
# Global
grep "version:" ~/Documents/.claude/agents/*.md

# Local
grep "version:" .claude/agents/*.md
```

3. Uninstall and reinstall to sync versions:
```bash
# Uninstall old version
python3 tools/sc-install.py uninstall sc-delay-tasks --dest ~/Documents/.claude

# Pull latest changes
cd /path/to/synaptic-canvas
git pull origin main

# Reinstall
python3 tools/sc-install.py install sc-delay-tasks --dest ~/Documents/.claude
```

4. Force reinstall (overwrites existing):
```bash
python3 tools/sc-install.py install sc-delay-tasks \
  --dest ~/Documents/.claude --force
```

**Prevention:**
- Keep Synaptic Canvas repository updated
- Use `--force` flag when updating packages
- Check version.yaml after pulling changes

---

### 5. Registry Connectivity Problems

**Problem:** Cannot read or update agent registry.

**Symptoms:**
```
Could not parse registry: .claude/agents/registry.yaml
Warning: Could not write registry
Registry update failed
```

**Root Causes:**
- Corrupt YAML in registry file
- File permissions prevent writing
- Missing PyYAML library (degraded to simple parser)

**Resolution:**

1. Check if registry exists and is valid YAML:
```bash
# View registry
cat .claude/agents/registry.yaml

# Validate YAML syntax (if PyYAML installed)
python3 -c "import yaml; yaml.safe_load(open('.claude/agents/registry.yaml'))"
```

2. If corrupted, backup and regenerate:
```bash
# Backup
cp .claude/agents/registry.yaml .claude/agents/registry.yaml.backup

# Delete corrupt file
rm .claude/agents/registry.yaml

# Reinstall packages to regenerate
python3 tools/sc-install.py install sc-delay-tasks --dest ./.claude --force
```

3. Check file permissions:
```bash
ls -la .claude/agents/registry.yaml
chmod u+rw .claude/agents/registry.yaml
```

4. Install PyYAML for better parsing (optional):
```bash
pip3 install pyyaml
```

5. If using simple parser (no PyYAML), ensure format:
```yaml
agents:
  delay-once:
    version: 0.4.0
    path: .claude/agents/delay-once.md
  delay-poll:
    version: 0.4.0
    path: .claude/agents/delay-poll.md
```

**Prevention:**
- Don't manually edit registry.yaml
- Install PyYAML for robust parsing: `pip3 install pyyaml`
- Backup registry before major operations

---

### 6. Local vs Global Scope Issues

**Problem:** Package installed in wrong scope or not accessible where needed.

**Symptoms:**
```
Command works globally but not in this repo
Command works in repo but not globally
Package not found in current scope
```

**Root Causes:**
- Misunderstanding scope requirements
- Package policy restrictions (sc-git-worktree is local-only)
- Installation path confusion

**Resolution:**

1. **Understand package scopes:**

| Package | Global | Local | Recommended |
|---------|--------|-------|-------------|
| sc-delay-tasks | Yes | Yes | Global |
| sc-git-worktree | No | Yes | Local-only |
| sc-manage | Yes | Yes | Global |
| sc-repomix-nuget | No | Yes | Local-only |

2. **For sc-git-worktree (local-only):**
```bash
# WRONG - sc-git-worktree cannot be global
python3 tools/sc-install.py install sc-git-worktree --dest ~/Documents/.claude
# Error: sc-git-worktree is local-only

# CORRECT
cd /path/to/your/repo
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude
```

3. **For global packages:**
```bash
# Install to global .claude
python3 tools/sc-install.py install sc-manage --dest ~/Documents/.claude
```

4. **Check where package is installed:**
```bash
# Global
ls ~/Documents/.claude/commands/

# Local (from repo root)
ls .claude/commands/
```

5. **Verify package policy:**
```bash
# Check manifest for scope restrictions
cat packages/sc-git-worktree/manifest.yaml | grep -i scope
# Output: Scope: Local-only
```

**Prevention:**
- Read package README for scope requirements
- Use global for utility packages (sc-delay-tasks, sc-manage)
- Use local for repo-specific packages (sc-git-worktree, sc-repomix-nuget)

---

### 7. Package Policy Enforcement Errors

**Problem:** Attempting to install package in prohibited scope.

**Symptoms:**
```
Error: sc-git-worktree is local-only, cannot install globally
Error: Package policy violation
```

**Root Causes:**
- Trying to install local-only package globally
- Package manifest restrictions
- Scope validation in installer

**Resolution:**

1. Check package requirements:
```bash
# View package README
cat packages/sc-git-worktree/README.md | head -10
# Shows: Scope: Local-only
```

2. Install in correct scope:
```bash
# For local-only packages
cd /path/to/your/repo
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude

# For global packages
python3 tools/sc-install.py install sc-manage --dest ~/Documents/.claude
```

3. If you need functionality globally:
```bash
# Some packages just can't be global (e.g., sc-git-worktree)
# They require repo context
# Install locally in each repo where needed
```

**Prevention:**
- Always check package scope in README first
- Use `/sc-manage --docs <package>` to review requirements
- Follow recommended installation scope

---

### 8. Missing Git for Local Installations

**Problem:** Local installation fails because git is not available.

**Symptoms:**
```
git: command not found
Error: Cannot detect REPO_NAME - git not available
Token expansion failed
```

**Root Causes:**
- Git not installed
- Git not in PATH
- Not in a git repository (for local installs)

**Resolution:**

1. Verify git is installed:
```bash
git --version
# Should show: git version 2.x.x
```

2. If not installed:

**macOS:**
```bash
brew install git
# or
xcode-select --install
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install git
```

**Windows:**
- Download from [git-scm.com](https://git-scm.com/downloads)

3. Verify you're in a git repository (for local installs):
```bash
git rev-parse --show-toplevel
# Should show repo path
```

4. If not a git repo, initialize:
```bash
git init
```

5. Retry installation:
```bash
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude
```

**Prevention:**
- Keep git in PATH
- Initialize git repo before local installations
- Use global scope for non-repo contexts

---

## Installation & Setup Issues

### Tools Directory Not Found

**Problem:**
```bash
python3 tools/sc-install.py list
# python3: can't open file 'tools/sc-install.py': [Errno 2] No such file or directory
```

**Resolution:**

1. Ensure you're in Synaptic Canvas repository root:
```bash
# Should show: packages/ src/ tools/ README.md
ls -la

# Find repository root
find . -name "sc-install.py" -type f
```

2. Navigate to correct directory:
```bash
cd /path/to/synaptic-canvas
ls tools/sc-install.py  # Verify
```

3. Or use absolute path:
```bash
python3 /path/to/synaptic-canvas/tools/sc-install.py list
```

---

### Installation Script Import Errors

**Problem:**
```bash
python3 tools/sc-install.py list
# ImportError: cannot import name 'install' from 'sc_cli'
```

**Resolution:**

1. Ensure repository structure is intact:
```bash
ls -la src/sc_cli/install.py
```

2. Python path should auto-detect, but verify:
```bash
cd /path/to/synaptic-canvas
python3 -c "import sys; sys.path.insert(0, 'src'); from sc_cli import install; print('OK')"
```

3. If missing src files:
```bash
git pull origin main
git status  # Check for missing files
```

---

### Incomplete Installation

**Problem:** Some files installed but not all.

**Symptoms:**
```bash
ls .claude/commands/delay.md  # exists
ls .claude/agents/delay-once.md  # missing
```

**Resolution:**

1. Check for warnings during installation:
```bash
python3 tools/sc-install.py install sc-delay-tasks --dest ./.claude
# Look for "Skip (exists)" or "Source not found" messages
```

2. Use `--force` to overwrite existing files:
```bash
python3 tools/sc-install.py install sc-delay-tasks --dest ./.claude --force
```

3. Verify manifest lists all files:
```bash
cat packages/sc-delay-tasks/manifest.yaml
```

4. Check source files exist:
```bash
ls packages/sc-delay-tasks/commands/
ls packages/sc-delay-tasks/agents/
ls packages/sc-delay-tasks/scripts/
```

---

## Configuration Issues

### Token Expansion Not Working

**Problem:** Variables like `{{REPO_NAME}}` not replaced during installation.

**Symptoms:**
```bash
cat .claude/agents/worktree-create.md | grep REPO_NAME
# Shows: {{REPO_NAME}} (not expanded)
```

**Resolution:**

1. Ensure installation uses expansion (default):
```bash
# Don't use --no-expand
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude
```

2. Verify git repository detection:
```bash
basename $(git rev-parse --show-toplevel)
# Should output your repo name
```

3. Reinstall with forced expansion:
```bash
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude --force
```

4. Check installed files:
```bash
grep -r "{{REPO_NAME}}" .claude/
# Should return nothing if properly expanded
```

---

### Wrong Destination Directory

**Problem:** Installed to wrong `.claude` location.

**Resolution:**

1. Understand destination paths:
```bash
# Global (user-level)
~/Documents/.claude

# Local (repo-level)
/path/to/repo/.claude
```

2. Verify where you want packages:
```bash
# For sc-manage (global recommended)
--dest ~/Documents/.claude

# For sc-git-worktree (local required)
--dest ./.claude  # (from repo root)
```

3. Check installed location:
```bash
# Find where package was installed
find ~ -name "sc-manage.md" -type f
```

4. Reinstall to correct location:
```bash
# Uninstall from wrong location
python3 tools/sc-install.py uninstall sc-manage --dest /wrong/path/.claude

# Install to correct location
python3 tools/sc-install.py install sc-manage --dest ~/Documents/.claude
```

---

## Integration Issues

### Using `/sc-manage` from Different Directories

**Problem:** `/sc-manage --list` behaves differently based on current directory.

**Explanation:** This is expected behavior:
- Package discovery requires being in Synaptic Canvas repository
- Installation/uninstallation works from anywhere (if globally installed)

**Resolution:**

1. For listing packages:
```bash
cd /path/to/synaptic-canvas
/sc-manage --list
```

2. For installation (works globally if sc-manage is global):
```bash
# Can run from anywhere
cd /any/directory
/sc-manage --install sc-delay-tasks --global
```

---

### Managing Multiple Package Versions

**Problem:** Want to test new package version without removing old.

**Resolution:**

1. **Not supported natively** - sc-manage installs latest from repo.

2. Workaround using git branches:
```bash
# Clone Synaptic Canvas to different locations
git clone <url> ~/synaptic-canvas-stable
git clone <url> ~/synaptic-canvas-dev
cd ~/synaptic-canvas-dev
git checkout develop

# Install from different versions
python3 ~/synaptic-canvas-stable/tools/sc-install.py install sc-delay-tasks --dest ~/Documents/.claude
# vs
python3 ~/synaptic-canvas-dev/tools/sc-install.py install sc-delay-tasks --dest ~/Documents/.claude
```

3. Or use local vs global:
```bash
# Stable version globally
python3 tools/sc-install.py install sc-delay-tasks --dest ~/Documents/.claude

# Dev version locally in test repo
cd ~/test-repo
python3 tools/sc-install.py install sc-delay-tasks --dest ./.claude
```

---

### Using with CI/CD

**Problem:** Automating package installation in CI pipelines.

**Resolution:**

1. Clone Synaptic Canvas in CI:
```yaml
# GitHub Actions example
- name: Setup Synaptic Canvas packages
  run: |
    git clone https://github.com/randlee/synaptic-canvas.git ~/sc
    python3 ~/sc/tools/sc-install.py install sc-delay-tasks --dest ./.claude
```

2. Or use as submodule:
```bash
git submodule add https://github.com/randlee/synaptic-canvas.git .synaptic-canvas
git submodule update --init --recursive
python3 .synaptic-canvas/tools/sc-install.py install sc-delay-tasks --dest ./.claude
```

3. Cache installations:
```yaml
- name: Cache Claude packages
  uses: actions/cache@v3
  with:
    path: .claude
    key: claude-packages-${{ hashFiles('.claude/**') }}
```

---

## Performance & Timeout Issues

### Slow Package Listing

**Problem:** `/sc-manage --list` takes long time.

**Root Causes:**
- Many packages in repository
- Slow filesystem (network drives)
- Parsing large manifest files

**Resolution:**

1. Use direct script for speed:
```bash
python3 tools/sc-install.py list
```

2. Check filesystem performance:
```bash
time ls -la packages/
# Should be nearly instant
```

3. For large repos, list specific package:
```bash
python3 tools/sc-install.py info sc-delay-tasks
```

---

### Installation Timeout

**Problem:** Installation hangs or times out.

**Resolution:**

1. Check for prompts or errors:
```bash
# Run with explicit output
python3 tools/sc-install.py install sc-delay-tasks --dest ./.claude
# Watch for any prompts or error messages
```

2. Verify destination is writable:
```bash
touch .claude/test && rm .claude/test
```

3. Check for filesystem locks:
```bash
lsof +D .claude/
```

---

## Platform-Specific Issues

### macOS Catalina+ Security

**Problem:** macOS blocks execution of scripts.

**Symptoms:**
```
"sc-install.py" cannot be opened because it is from an unidentified developer
```

**Resolution:**

1. Allow in Security & Privacy:
```bash
# System Preferences > Security & Privacy > General
# Click "Allow Anyway" for sc-install.py
```

2. Or use Python directly:
```bash
python3 tools/sc-install.py list
```

---

### Windows Path Issues

**Problem:** Paths with backslashes cause issues.

**Resolution:**

1. Use forward slashes:
```bash
# WRONG
python3 tools\sc-install.py install sc-delay-tasks --dest C:\Users\username\Documents\.claude

# CORRECT
python3 tools/sc-install.py install sc-delay-tasks --dest C:/Users/username/Documents/.claude
```

2. Or use WSL:
```bash
wsl python3 tools/sc-install.py install sc-delay-tasks --dest /mnt/c/Users/username/Documents/.claude
```

---

### Linux Snap Python

**Problem:** Python installed via snap has restricted filesystem access.

**Resolution:**

1. Use system Python instead:
```bash
# Install system Python
sudo apt install python3

# Use explicit path
/usr/bin/python3 tools/sc-install.py list
```

2. Or grant snap permissions:
```bash
sudo snap connect python3:home
```

---

## Getting Help

### When to Escalate

Escalate to GitHub issues if you encounter:

- Package installation repeatedly fails
- Registry corruption that can't be resolved
- Version conflicts after clean installation
- Permission errors that persist after fixes
- Scope policy errors that seem incorrect

### How to Report Bugs

Include the following information:

1. **Environment details:**
```bash
python3 --version
git --version
uname -a  # or systeminfo on Windows
echo $HOME
```

2. **Installation attempt:**
```bash
# Full command and output
python3 tools/sc-install.py install sc-delay-tasks --dest ~/Documents/.claude
```

3. **Current state:**
```bash
# Show installed files
ls -la ~/Documents/.claude/commands/
ls -la ~/Documents/.claude/agents/
cat ~/Documents/.claude/agents/registry.yaml
```

4. **Repository info:**
```bash
cd /path/to/synaptic-canvas
git status
cat version.yaml
ls packages/
```

5. **Manifest contents:**
```bash
cat packages/sc-delay-tasks/manifest.yaml
```

### Debug Information to Collect

**Basic diagnostics:**
```bash
# Python environment
python3 --version
which python3
pip3 list | grep -i yaml

# Git environment
git --version
which git

# Filesystem
ls -la ~/Documents/
ls -la ~/Documents/.claude/
ls -la .claude/  # If in repo

# Repository structure
cd /path/to/synaptic-canvas
ls -la packages/
ls -la src/sc_cli/
ls -la tools/
```

**For installation issues:**
```bash
# Try installation with verbose output
python3 -v tools/sc-install.py install sc-delay-tasks --dest ./.claude

# Check manifest parsing
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, 'src')
from sc_cli.install import _parse_manifest
m = _parse_manifest(Path('packages/sc-delay-tasks'))
print(f'Name: {m.name}')
print(f'Artifacts: {m.artifacts}')
"
```

**For registry issues:**
```bash
# Check registry format
cat .claude/agents/registry.yaml

# Validate YAML
python3 -c "
import yaml
with open('.claude/agents/registry.yaml') as f:
    data = yaml.safe_load(f)
    print(data)
"
```

---

## FAQ

### Q: What's the difference between installing globally vs locally?

**A:**

**Global installation** (`~/Documents/.claude`):
- Available in all projects and contexts
- Suitable for utility packages (sc-delay-tasks, sc-manage)
- Shared across all repositories

**Local installation** (`/path/to/repo/.claude`):
- Specific to one repository
- Required for repo-specific packages (sc-git-worktree, sc-repomix-nuget)
- Isolated per project

---

### Q: Can I install the same package in both global and local?

**A:** Yes, but local takes precedence:
- Claude checks local `.claude/` first
- Then checks global `~/Documents/.claude/`
- Useful for testing new versions locally

---

### Q: How do I know which packages are installed?

**A:**
```bash
# Global
ls ~/Documents/.claude/commands/

# Local
ls .claude/commands/

# Via sc-manage (if globally installed)
/sc-manage --list
```

---

### Q: What happens if I install without `--force` and files exist?

**A:** Installation skips existing files:
```
Skip (exists): commands/delay.md
Skip (exists): agents/delay-once.md
```

Use `--force` to overwrite:
```bash
python3 tools/sc-install.py install sc-delay-tasks --dest ./.claude --force
```

---

### Q: Can I use sc-manage to install from other repositories?

**A:** No, sc-manage only installs packages from the Synaptic Canvas repository where `sc-install.py` is located.

For other packages:
1. Clone their repository
2. Use their installation method
3. Or manually copy files to `.claude/`

---

### Q: What is the agent registry used for?

**A:** The registry (`agents/registry.yaml`) tracks:
- Installed agents
- Agent versions
- Agent file paths

Claude Code uses this for:
- Version management
- Dependency checking
- Agent discovery

---

### Q: Can I manually edit manifest.yaml?

**A:** Yes, but:
- Used by `sc-install.py` to determine what to install
- Changes affect installation behavior
- Keep format valid YAML
- Test with: `python3 tools/sc-install.py info <package>`

---

### Q: How do I uninstall all packages at once?

**A:**
```bash
# List all installed
python3 tools/sc-install.py list

# Uninstall each (no bulk uninstall)
python3 tools/sc-install.py uninstall sc-delay-tasks --dest ~/Documents/.claude
python3 tools/sc-install.py uninstall sc-manage --dest ~/Documents/.claude
python3 tools/sc-install.py uninstall sc-git-worktree --dest ./.claude

# Or remove directory (nuclear option)
rm -rf ~/Documents/.claude
rm -rf .claude/
```

---

### Q: What if PyYAML is not installed?

**A:** sc-install.py works without PyYAML:
- Falls back to simple line parser
- Supports basic manifest format
- May miss complex YAML features

Install PyYAML for full support:
```bash
pip3 install pyyaml
```

---

### Q: Can I rename or move installed packages?

**A:** Not recommended:
- Breaks registry tracking
- Commands may not be found
- Reinstall instead:
```bash
python3 tools/sc-install.py uninstall <package> --dest <old-location>
python3 tools/sc-install.py install <package> --dest <new-location>
```

---

### Q: How do I update sc-manage itself?

**A:**
```bash
# Navigate to Synaptic Canvas repo
cd /path/to/synaptic-canvas

# Pull latest
git pull origin main

# Uninstall old version
python3 tools/sc-install.py uninstall sc-manage --dest ~/Documents/.claude

# Reinstall
python3 tools/sc-install.py install sc-manage --dest ~/Documents/.claude
```

---

## Additional Resources

- **Package README:** `packages/sc-manage/README.md`
- **Use Cases:** (Coming soon)
- **Changelog:** `packages/sc-manage/CHANGELOG.md`
- **Skill Documentation:** `packages/sc-manage/skills/managing-sc-packages/SKILL.md`
- **Agent Specifications:**
  - `packages/sc-manage/agents/sc-packages-list.md`
  - `packages/sc-manage/agents/sc-package-install.md`
  - `packages/sc-manage/agents/sc-package-uninstall.md`
  - `packages/sc-manage/agents/sc-package-docs.md`
- **Installation Script:** `tools/sc-install.py`
- **Repository:** https://github.com/randlee/synaptic-canvas
- **Issues:** https://github.com/randlee/synaptic-canvas/issues
