# Validation Quick Reference

A comprehensive guide to the Synaptic Canvas validation system, providing quick access to all validation scripts, their purposes, and common troubleshooting steps.

## Overview

The Synaptic Canvas validation system ensures consistency, quality, and security across all marketplace artifacts. Validators run both locally during development and automatically in CI/CD pipelines to catch issues before they reach production.

**Key Benefits:**
- Consistent version management across packages
- Security vulnerability detection
- Frontmatter schema compliance
- Cross-reference integrity
- Manifest artifact verification

## Validation Scripts

All validation scripts are located in the `scripts/` directory and follow consistent patterns for exit codes and output formatting.

### Script Reference Table

| Script | Purpose | Exit Codes |
|--------|---------|------------|
| `audit-versions.py` | Check version consistency across the codebase | 0=pass, 1=fail |
| `compare-versions.py` | Compare versions across packages and detect mismatches | 0=pass, 1=fail |
| `validate-agents.py` | Validate agent registry entries and configurations | 0=pass, 1=fail |
| `security-scan.py` | Security scanning for vulnerabilities and sensitive data | 0=pass, 1=warn, 2=fail |
| `validate-manifest-artifacts.py` | Verify manifest artifacts match declared files | 0=pass, 1=fail |
| `validate-marketplace-sync.py` | Check marketplace synchronization status | 0=pass, 1=fail |
| `validate-frontmatter-schema.py` | Validate frontmatter against JSON schemas | 0=pass, 1=fail |
| `validate-script-references.py` | Check that script references resolve correctly | 0=pass, 1=fail |
| `validate-cross-references.py` | Validate cross-references between artifacts | 0=pass, 1=fail |
| `validate-all.py` | Run all validators in sequence | 0=pass, 1=fail |
| `generate-validation-report.py` | Generate comprehensive HTML validation report | 0=success |

### Detailed Script Descriptions

#### audit-versions.py
Scans the codebase for version declarations and ensures consistency.

```bash
python scripts/audit-versions.py [--verbose] [--fix]
```

**Options:**
- `--verbose`: Show detailed output for each version check
- `--fix`: Automatically fix minor version inconsistencies

#### compare-versions.py
Compares version numbers across multiple packages and configuration files.

```bash
python scripts/compare-versions.py [--baseline VERSION]
```

**Options:**
- `--baseline`: Compare against a specific baseline version

#### validate-agents.py
Validates agent registry entries for required fields and proper formatting.

```bash
python scripts/validate-agents.py [--registry PATH]
```

**Options:**
- `--registry`: Path to agent registry file (default: `.claude-plugin/agents/`)

#### security-scan.py
Performs security scanning for vulnerabilities, secrets, and sensitive data exposure.

```bash
python scripts/security-scan.py [--severity LEVEL] [--exclude PATTERN]
```

**Options:**
- `--severity`: Minimum severity to report (low, medium, high, critical)
- `--exclude`: Glob pattern to exclude files from scanning

**Exit Codes:**
- `0`: No security issues found
- `1`: Warnings found (non-blocking)
- `2`: Critical issues found (blocking)

#### validate-manifest-artifacts.py
Verifies that all artifacts declared in manifests exist and are properly configured.

```bash
python scripts/validate-manifest-artifacts.py [--manifest PATH]
```

**Options:**
- `--manifest`: Path to manifest file (default: auto-detect)

#### validate-marketplace-sync.py
Checks that marketplace entries are synchronized with local artifacts.

```bash
python scripts/validate-marketplace-sync.py [--check-remote]
```

**Options:**
- `--check-remote`: Also verify against remote marketplace registry

#### validate-frontmatter-schema.py
Validates frontmatter in all markdown artifacts against JSON schemas.

```bash
python scripts/validate-frontmatter-schema.py [--type TYPE] [--path PATH]
```

**Options:**
- `--type`: Artifact type to validate (command, skill, agent, reference)
- `--path`: Specific path to validate

#### validate-script-references.py
Ensures all script references in artifacts resolve to existing files.

```bash
python scripts/validate-script-references.py [--fix-paths]
```

**Options:**
- `--fix-paths`: Attempt to fix broken path references

#### validate-cross-references.py
Validates cross-references between artifacts, ensuring all links resolve.

```bash
python scripts/validate-cross-references.py [--include-external]
```

**Options:**
- `--include-external`: Also check external URL references

#### validate-all.py
Master script that runs all validators in the correct sequence.

```bash
python scripts/validate-all.py [--stop-on-failure] [--report]
```

**Options:**
- `--stop-on-failure`: Stop immediately on first validation failure
- `--report`: Generate HTML report after validation

#### generate-validation-report.py
Generates a comprehensive HTML report of all validation results.

```bash
python scripts/generate-validation-report.py [--output PATH] [--format FORMAT]
```

**Options:**
- `--output`: Output file path (default: `validation-report.html`)
- `--format`: Output format (html, json, markdown)

## When to Run Each Script

### During Development

| Scenario | Script(s) to Run |
|----------|-----------------|
| Creating a new command | `validate-frontmatter-schema.py`, `validate-manifest-artifacts.py` |
| Creating a new skill | `validate-frontmatter-schema.py`, `validate-script-references.py` |
| Creating a new agent | `validate-agents.py`, `validate-frontmatter-schema.py` |
| Updating versions | `audit-versions.py`, `compare-versions.py` |
| Before committing | `validate-all.py` |
| Before PR submission | `validate-all.py`, `security-scan.py` |

### Before Release

Run the full validation suite:

```bash
python scripts/validate-all.py --report
python scripts/security-scan.py --severity high
```

### CI/CD Pipeline Triggers

| Pipeline Stage | Scripts Run |
|----------------|-------------|
| Pull Request | `validate-all.py`, `security-scan.py` |
| Merge to develop | `validate-all.py`, `security-scan.py --severity medium` |
| Release branch | Full suite with `--strict` flags |
| Production deploy | `validate-all.py`, `security-scan.py --severity low` |

## Common Validation Errors

### Version Mismatch Errors

**Error:** `Version mismatch: package.json (1.2.0) != pyproject.toml (1.1.0)`

**Fix:**
1. Determine the correct version
2. Update all version declarations to match
3. Run `audit-versions.py --fix` for automatic correction

### Frontmatter Schema Errors

**Error:** `Missing required field 'entry_point' in skill frontmatter`

**Fix:**
1. Open the skill file
2. Add the missing `entry_point` field to frontmatter
3. Ensure the path starts with `/`

**Error:** `Invalid value for 'model': expected one of [sonnet, opus, haiku]`

**Fix:**
1. Check the `model` field in agent frontmatter
2. Use only allowed values: `sonnet`, `opus`, or `haiku`

### Manifest Artifact Errors

**Error:** `Declared artifact 'commands/my-command.md' not found`

**Fix:**
1. Verify the file exists at the declared path
2. Check for typos in the manifest entry
3. Create the missing file if needed

### Cross-Reference Errors

**Error:** `Broken reference: skill 'data-processing' references non-existent command 'parse-data'`

**Fix:**
1. Create the missing referenced artifact
2. Or update the reference to point to an existing artifact
3. Or remove the invalid reference

### Security Scan Errors

**Error:** `[HIGH] Potential secret detected in config.py line 42`

**Fix:**
1. Remove the hardcoded secret
2. Use environment variables or secret management
3. Add the file to `.gitignore` if it contains local-only secrets

## CI/CD Integration

### GitHub Actions Integration

The validation suite is integrated into GitHub Actions workflows:

```yaml
# .github/workflows/validate.yml
name: Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run validation suite
        run: python scripts/validate-all.py --report

      - name: Run security scan
        run: python scripts/security-scan.py --severity medium

      - name: Upload validation report
        uses: actions/upload-artifact@v4
        with:
          name: validation-report
          path: validation-report.html
```

### Pre-commit Hook

Add validation to pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-frontmatter
        name: Validate Frontmatter
        entry: python scripts/validate-frontmatter-schema.py
        language: python
        types: [markdown]
```

### Exit Code Handling

All validators return consistent exit codes:

- `0`: Validation passed
- `1`: Validation failed (or warnings for security-scan)
- `2`: Critical failure (security-scan only)

CI pipelines should fail on any non-zero exit code from validators.

## Troubleshooting

### Script Not Found

**Problem:** `python: can't open file 'scripts/validate-all.py'`

**Solution:**
1. Ensure you're running from the repository root
2. Check that scripts directory exists
3. Verify script permissions: `chmod +x scripts/*.py`

### Missing Dependencies

**Problem:** `ModuleNotFoundError: No module named 'jsonschema'`

**Solution:**
```bash
pip install -r requirements.txt
# Or for specific packages:
pip install jsonschema pyyaml
```

### Schema Validation Failures on Valid Files

**Problem:** Frontmatter appears correct but validation fails

**Solution:**
1. Check for invisible characters (copy-paste issues)
2. Verify YAML indentation (spaces, not tabs)
3. Ensure quotes around special characters
4. Run with `--verbose` for detailed error messages

### Slow Validation

**Problem:** Validation takes too long

**Solution:**
1. Use `--path` to validate specific files
2. Use `--type` to validate specific artifact types
3. Run individual validators instead of `validate-all.py`

### False Positives in Security Scan

**Problem:** Security scan flags legitimate code

**Solution:**
1. Add false positives to `.security-ignore`
2. Use `--exclude` to skip specific patterns
3. Add inline comments: `# nosec` (if supported)

### Permissions Errors

**Problem:** `Permission denied` when running scripts

**Solution:**
```bash
chmod +x scripts/*.py
# Or run with python explicitly:
python scripts/validate-all.py
```

## Dependency Validation

Synaptic Canvas has a minimal dependency footprint designed for maximum compatibility. This section documents all dependencies, how to validate them, and how to resolve issues.

### Dependency Philosophy

- **Minimal:** Only essential dependencies required
- **Standard:** Prefer standard tools (Git, Python, Bash)
- **Optional:** Advanced features have optional dependencies
- **Portable:** Work across macOS, Linux, and Windows (WSL)

### Dependency Hierarchy

```
Core (Required for all packages):
├─ Git >= 2.7.0
├─ Python 3 >= 3.6
└─ Bash/POSIX shell

Package-Specific (Optional):
├─ Node.js >= 18.0 (sc-repomix-nuget only)
├─ npm >= 8.0 (sc-repomix-nuget only)
└─ .NET SDK (sc-repomix-nuget, for C# projects)
```

### Global Dependencies

#### Git

**Purpose:** Version control and repository management

**Minimum Version:** 2.7.0 (for worktree support)

**Validation Command:**
```bash
git --version
# Check if version >= 2.7.0

# Test Git Worktree Support:
git worktree --help > /dev/null 2>&1 && echo "Worktree support available"
```

**Installation:**
- **macOS:** `brew install git`
- **Linux (Ubuntu/Debian):** `sudo apt-get install git`
- **Linux (RHEL/Fedora):** `sudo dnf install git`
- **Windows:** Download from https://git-scm.com/download/win or use WSL

#### Python 3

**Purpose:** Running utility scripts for version management and validation

**Minimum Version:** 3.6

**Used By:**
- `scripts/set-package-version.py` - Version management and registry regeneration
- `docs/registries/nuget/validate-registry.py` - Registry validation
- Various validation scripts

**Validation Command:**
```bash
python3 --version
# Check if version >= 3.6

# Check required modules:
python3 -c "import sys, os, re, json, pathlib, argparse, subprocess" && echo "Required modules available"

# Check optional modules:
python3 -c "import yaml" 2>/dev/null && echo "YAML module available"
python3 -c "import jsonschema" 2>/dev/null && echo "jsonschema module available"
```

**Installation:**
- **macOS:** `brew install python3`
- **Linux (Ubuntu/Debian):** `sudo apt-get install python3 python3-pip`
- **Linux (RHEL/Fedora):** `sudo dnf install python3 python3-pip`
- **Windows:** Download from https://python.org/downloads/ or use WSL

#### Bash/POSIX Shell

**Purpose:** Running shell scripts

**Minimum Version:** Bash 4.0 or compatible POSIX shell

**Validation Command:**
```bash
bash --version
echo "Current shell: $SHELL"
```

### Package-Specific Dependencies

| Package | Git | Python 3 | Bash | Node.js | npm | .NET SDK |
|---------|-----|----------|------|---------|-----|----------|
| **sc-delay-tasks** | Optional | Required | Required | - | - | - |
| **sc-git-worktree** | >= 2.7.0 | Required | Required | - | - | - |
| **sc-manage** | Required | Required | Required | - | - | - |
| **sc-repomix-nuget** | Optional | Optional | Required | >= 18 | >= 8 | Optional |

#### sc-git-worktree Dependencies

**Critical:** Requires Git >= 2.7.0 for worktree support.

**Platform Notes:**
- **Windows:** Worktrees work best in WSL. Git Bash may have path issues.

**Validation:**
```bash
git_version=$(git --version | awk '{print $3}')
required="2.7.0"
if [[ "$(printf '%s\n' "$required" "$git_version" | sort -V | head -n1)" = "$required" ]]; then
    echo "Git version sufficient for worktree (>= $required)"
fi

git worktree --help > /dev/null 2>&1 && echo "Git worktree command available"
```

#### sc-repomix-nuget Dependencies

**Required:**
- Node.js >= 18.0.0
- npm >= 8.0.0
- Bash or POSIX shell

**Optional:**
- .NET SDK (for C# projects)

**Validation:**
```bash
node --version  # Should be v18.0.0 or higher
npm --version   # Should be 8.0.0 or higher
dotnet --version  # Optional, for C# projects
```

**Node.js Installation (using nvm - Recommended):**
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc

# Install and use Node.js 18
nvm install 18
nvm use 18
nvm alias default 18
```

### Quick Dependency Check Script

**One-command check:**

```bash
#!/bin/bash
# quick-dep-check.sh

echo "=== Quick Dependency Check ==="

# Core dependencies
command -v git > /dev/null 2>&1 && echo "Git: OK" || echo "Git: MISSING"
command -v python3 > /dev/null 2>&1 && echo "Python 3: OK" || echo "Python 3: MISSING"
command -v bash > /dev/null 2>&1 && echo "Bash: OK" || echo "Bash: MISSING"

# Optional dependencies
command -v node > /dev/null 2>&1 && echo "Node.js: OK" || echo "Node.js: (optional)"
command -v npm > /dev/null 2>&1 && echo "npm: OK" || echo "npm: (optional)"
command -v dotnet > /dev/null 2>&1 && echo ".NET SDK: OK" || echo ".NET SDK: (optional)"
```

### Comprehensive Dependency Validation

For detailed validation with version checking:

```bash
#!/bin/bash
# check-all-deps.sh

ERRORS=0

# Check Git
echo "Checking Git..."
if command -v git > /dev/null 2>&1; then
    git_version=$(git --version | awk '{print $3}')
    required="2.7.0"
    if [[ "$(printf '%s\n' "$required" "$git_version" | sort -V | head -n1)" = "$required" ]]; then
        echo "  Git version OK: $git_version >= $required"
    else
        echo "  Git version too old: $git_version < $required"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  Git not found"
    ERRORS=$((ERRORS + 1))
fi

# Check Python 3
echo "Checking Python 3..."
if command -v python3 > /dev/null 2>&1; then
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    major=$(echo $python_version | cut -d. -f1)
    minor=$(echo $python_version | cut -d. -f2)
    if [[ $major -ge 3 ]] && [[ $minor -ge 6 ]]; then
        echo "  Python version OK: $python_version >= 3.6"
    else
        echo "  Python version too old: $python_version < 3.6"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  Python 3 not found"
    ERRORS=$((ERRORS + 1))
fi

# Check Bash
echo "Checking Bash..."
if command -v bash > /dev/null 2>&1; then
    bash_version=$(bash --version | head -1 | awk '{print $4}')
    echo "  Bash installed: $bash_version"
else
    echo "  Bash not found"
    ERRORS=$((ERRORS + 1))
fi

exit $ERRORS
```

### Dependency Conflicts

**Common conflict scenarios and resolutions:**

1. **Multiple Python versions:**
   ```bash
   which -a python python3 python3.11
   # Use pyenv to manage versions
   pyenv global 3.11
   ```

2. **Multiple Git installations:**
   ```bash
   which -a git
   # Use PATH priority or absolute paths
   export PATH="/usr/local/bin:$PATH"
   ```

3. **Node.js version conflicts:**
   ```bash
   # Use nvm to switch versions
   nvm use 18
   # Or create .nvmrc file
   echo "18" > .nvmrc
   ```

### Pre-Commit Hook for Dependencies

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "Running pre-commit dependency check..."

if ! command -v git > /dev/null 2>&1; then
    echo "Error: Git not found"
    exit 1
fi

if ! command -v python3 > /dev/null 2>&1; then
    echo "Error: Python 3 not found"
    exit 1
fi

echo "Dependency check passed"
exit 0
```

### Platform-Specific Notes

#### macOS
- Install Xcode Command Line Tools: `xcode-select --install`
- System Git may be outdated; use Homebrew: `brew install git`
- Use `python3` explicitly (macOS may have Python 2 as `python`)

#### Linux
- **Ubuntu/Debian:** Use `apt-get` or `apt`
- **RHEL/CentOS/Fedora:** Use `yum` or `dnf`; may need EPEL or NodeSource repos
- **Arch Linux:** `sudo pacman -S git python bash nodejs npm`

#### Windows
- **Recommended:** Use Windows Subsystem for Linux (WSL 2)
- **Alternative:** Git Bash + native Windows tools
- **WSL Setup:** `wsl --install` then follow Linux instructions
- **Line endings:** Configure with `git config --global core.autocrlf true`
- **Worktrees:** WSL 2 strongly recommended for worktree functionality

### Dependency Quick Reference

```bash
# Quick check
git --version && python3 --version && bash --version

# Comprehensive check
./check-all-deps.sh

# Installation (macOS)
brew install git python3 node

# Installation (Ubuntu/Debian)
sudo apt-get install git python3 nodejs npm

# Installation (RHEL/CentOS)
sudo yum install git python3 nodejs npm
```

## Related Documentation

- [FRONTMATTER-SCHEMA.md](./FRONTMATTER-SCHEMA.md) - Detailed frontmatter schema documentation
- [SECURITY-SCANNING-GUIDE.md](./SECURITY-SCANNING-GUIDE.md) - Security scanning deep dive
- [VERSION-CHECKING-GUIDE.md](./VERSION-CHECKING-GUIDE.md) - Version management guide
- [DIAGNOSTIC-TOOLS.md](./DIAGNOSTIC-TOOLS.md) - Diagnostic tools reference and workflows
