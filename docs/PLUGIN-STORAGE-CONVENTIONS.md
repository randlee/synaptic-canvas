# Plugin Storage Conventions

**Status:** Normative (enforced across all packages)
**Last Updated:** January 24, 2026
**Audience:** Plugin developers, package maintainers

All Synaptic Canvas plugins follow standardized storage conventions to ensure consistent behavior, troubleshooting, and observability across the ecosystem.

---

## Quick Reference

| Purpose | Location | Format | Scope | TTL |
|---------|----------|--------|-------|-----|
| **Runtime Logs** | `.claude/state/logs/<package>/` | JSON | Per-project | 14 days |
| **Shared Settings** | `.sc/shared-settings.yaml` | YAML | Per-repo (all packages) | Persistent |
| **Package Settings** | `.sc/<package>/settings.yaml` | YAML | Per-package | Persistent |
| **User Settings** | `~/.sc/<package>/settings.yaml` | YAML | User-global | Persistent |
| **Generated Output** | `.sc/<package>/output/` | Varied | Per-project | Persistent |
| **Session Start Scripts** | `scripts/<plugin>_session_start.py` | Python | Per-package | N/A |

---

## Logs: `.claude/state/logs/<package>/`

### Purpose
Runtime events, hook executions, validation errors, and audit trails for troubleshooting and observability.

### Format
- **Type:** JSON (newline-delimited or individual files)
- **Content:** Events with timestamp, level, context, and structured data
- **Searchability:** All fields queryable for post-execution analysis

### Examples

```yaml
# sc-codex
.claude/state/logs/sc-codex/
  ├── 2026-01-22-15-30-45-abc123.json
  └── 2026-01-22-15-35-12-def456.json

# sc-ci-automation
.claude/state/logs/ci-automation/
  ├── validation-2026-01-22.json
  └── build-2026-01-22.json

# sc-startup
.claude/state/logs/sc-startup/
  └── checklist-2026-01-22.json
```

### Retention Policy

- **Default TTL:** 14 days
- **Location:** `.claude/state/.gitignore` (ignore logs)
- **Cleanup:** Manual or via housekeeping agent
- **Never log:** Secrets, PII, credentials (validate in code)

### Implementation Checklist

- [ ] Package documents logs location in README under "Logs" section
- [ ] Implementation writes to `.claude/state/logs/<package>/`
- [ ] Each event includes: `timestamp`, `level`, `message`, `context`
- [ ] No secrets are logged (audit code for hardcoded values)
- [ ] `.gitignore` excludes `.claude/state/logs/`

---

## Shared Settings: `.sc/shared-settings.yaml`

### Purpose
Repository-wide configuration shared across all packages. Used for provider information, protected branches, and repository policies that should be configured once and used everywhere.

### Format
- **Type:** YAML (single file for entire repo)
- **Content:** Provider config (Azure/GitHub), protected branches, credential references
- **Scope:** Repository-wide (all packages read from this)

### Normative Schema

All packages MUST use these standardized field names when reading from shared settings:

| Field Path | Type | Required | Auto-detect from | Fallback |
|------------|------|----------|------------------|----------|
| `git.protected_branches` | array[string] | Yes | Git-flow config (`gitflow.branch.master`, `gitflow.branch.develop`) | Fail with error - user must define |

**Important:** Field names are case-sensitive and use snake_case.

### Auto-Detected Values (Do NOT Store)

These values are auto-detected on every run and should NOT be stored in shared-settings:

| What | How to Detect |
|------|---------------|
| **Provider type** (GitHub/Azure) | Parse `git remote get-url origin` |
| **Azure org/project/repo** | Parse from remote URL: `dev.azure.com/org/project/_git/repo` |
| **GitHub org/repo** | Parse from remote URL: `github.com/org/repo` |
| **Credentials** | Standard env vars: `GITHUB_TOKEN`, `AZURE_DEVOPS_PAT` |

### Protected Branches Detection Logic

Packages that need protected branch info should use this pattern in hooks:

```python
def get_protected_branches(repo_root: Path) -> list[str]:
    """Get protected branches with detection and caching."""
    import subprocess
    import yaml

    # 1. Check if already in shared settings
    shared_path = repo_root / ".sc" / "shared-settings.yaml"
    if shared_path.exists():
        settings = yaml.safe_load(shared_path.read_text())
        if branches := settings.get("git", {}).get("protected_branches"):
            return branches

    # 2. Try git-flow detection
    protected = []
    try:
        master = subprocess.run(
            ["git", "config", "--get", "gitflow.branch.master"],
            cwd=repo_root, capture_output=True, text=True, check=False
        ).stdout.strip()
        develop = subprocess.run(
            ["git", "config", "--get", "gitflow.branch.develop"],
            cwd=repo_root, capture_output=True, text=True, check=False
        ).stdout.strip()

        if master:
            protected.append(master)
        if develop:
            protected.append(develop)
    except Exception:
        pass

    # 3. Auto-populate if found
    if protected:
        shared_path.parent.mkdir(parents=True, exist_ok=True)
        shared_path.write_text(yaml.dump({"git": {"protected_branches": protected}}))
        return protected

    # 4. Not found - fail with instructions
    raise ValueError(
        "Protected branches not configured.\n\n"
        "Please create .sc/shared-settings.yaml with:\n"
        "git:\n"
        "  protected_branches: [main, develop]\n\n"
        "List all branches that require PR workflow (no direct push)."
    )
```

### What Goes in Shared Settings

**Use shared settings for:**
- Protected branch lists (workflow-critical)
- Repository-wide policies that can't be auto-detected

**Don't store (auto-detect instead):**
- Provider info (parse from git remote)
- Credential env var names (use standard names)
- Default branches (query from git-flow or provider API)

**Example:**
```yaml
# .sc/shared-settings.yaml
git:
  protected_branches:
    - main
    - develop
```

That's it. Everything else is auto-detected.

### Extending the Schema

Most things should be auto-detected, not stored. Before adding a new shared setting:

1. **Can it be auto-detected?** (from git config, remote URL, or API)
2. **Is it truly repository-scoped?** (same value for all packages and users)
3. **Is it workflow-critical?** (like protected branches)

If yes to all three, propose addition to normative schema table.

**Do NOT add to shared settings:**
- Anything that can be parsed from git remote or git config
- Package-specific thresholds (use package settings)
- Cached runtime state (use package settings)
- User preferences (use user-global settings)

### Reading Shared Settings

Packages read shared settings using a **fallback chain**:

```python
# Priority order:
# 1. Package-specific settings (.sc/<package>/settings.yaml)
# 2. Shared settings (.sc/shared-settings.yaml)  ← NEW
# 3. User-global settings (~/.sc/<package>/settings.yaml)
# 4. Hardcoded defaults

def get_setting(key: str, package: str, default=None):
    # Try package-specific first
    package_path = f".sc/{package}/settings.yaml"
    if value := deep_get(load_yaml(package_path), key):
        return value

    # Try shared settings
    if value := deep_get(load_yaml(".sc/shared-settings.yaml"), key):
        return value

    # Try user-global
    user_path = f"~/.sc/{package}/settings.yaml"
    if value := deep_get(load_yaml(user_path), key):
        return value

    return default

# Usage
azure_org = get_setting("provider.azure_devops.org", "sc-commit-push-pr")
protected = get_setting("git.protected_branches", "sc-commit-push-pr", ["main"])
```

### Writing Shared Settings

**Auto-population from hooks is ALLOWED** for git-flow detection only.

**From SubAgentStart hooks (allowed):**
```python
# ✓ CORRECT: Auto-populate from git-flow in hooks
if git_flow_branches := detect_from_gitflow():
    Path(".sc/shared-settings.yaml").write_text(
        yaml.dump({"git": {"protected_branches": git_flow_branches}})
    )
```

**From agents/commands (not allowed):**
```python
# ✗ WRONG: Don't write from agent execution
def commit_push_agent():
    # Don't do this inside agent:
    write_shared_settings(...)  # NO!
```

**Manual user editing (encouraged):**
```yaml
# User can edit .sc/shared-settings.yaml directly
git:
  protected_branches: [main, staging, production]
```

### Hook Pattern for Auto-Population

Packages should detect and populate protected branches in SubAgentStart hooks:

**When hook runs:**
1. Check if `.sc/shared-settings.yaml` exists with `git.protected_branches`
2. If not, try git-flow detection
3. If found via git-flow, auto-create `.sc/shared-settings.yaml`
4. If not found, fail with clear error message

**Example hook (commit_push_agent_start_hook.py):**
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
import subprocess
import yaml

repo_root = Path.cwd()
shared_path = repo_root / ".sc" / "shared-settings.yaml"

# Check for protected branches
protected = None

if shared_path.exists():
    settings = yaml.safe_load(shared_path.read_text())
    protected = settings.get("git", {}).get("protected_branches")

if not protected:
    # Try git-flow
    try:
        master = subprocess.run(
            ["git", "config", "--get", "gitflow.branch.master"],
            capture_output=True, text=True, check=False
        ).stdout.strip()
        develop = subprocess.run(
            ["git", "config", "--get", "gitflow.branch.develop"],
            capture_output=True, text=True, check=False
        ).stdout.strip()

        protected = [b for b in [master, develop] if b]
    except Exception:
        pass

if protected:
    # Auto-populate
    shared_path.parent.mkdir(parents=True, exist_ok=True)
    shared_path.write_text(yaml.dump({"git": {"protected_branches": protected}}))
    sys.exit(0)  # Allow

# Not found - fail with instructions
print("ERROR: Protected branches not configured.", file=sys.stderr)
print("", file=sys.stderr)
print("Create .sc/shared-settings.yaml with:", file=sys.stderr)
print("git:", file=sys.stderr)
print("  protected_branches: [main, develop]", file=sys.stderr)
sys.exit(2)  # Block
```

### Retention Policy

- **Default TTL:** Persistent
- **Version Control:** Usually committed to git (team-wide config)
- **Never store:** Actual credentials/tokens (only env var references)

---

## Package Settings: `.sc/<package>/settings.yaml`

### Purpose
Package-specific configuration, cached values, and runtime state. Used for settings that are unique to one package or override shared settings.

### Format
- **Type:** YAML (single file per package)
- **Content:** Package-specific config, feature flags, cached state
- **Scope:** Per-package (not shared)

### What Goes in Package Settings

**Use package settings for:**
- Package-specific thresholds, limits, timeouts
- Feature flags specific to this package
- Cached state unique to this package
- Overrides of shared settings (rare)

**Don't duplicate shared settings here** - use the fallback chain to read from shared settings.

### Examples

```yaml
# .sc/sc-roslyn-diff/settings.yaml
# Package-specific settings only (provider info comes from shared)
files_per_agent: 15
max_file_size_kb: 1024
enable_html_reports: true

# .sc/sc-ci-automation/settings.yaml
# Package-specific build/test config
build_command: "dotnet build"
test_command: "pytest"
allowed_agents:
  - ci-validate-agent
  - ci-build-agent

# .sc/sc-commit-push-pr/settings.yaml
# Package-specific commit/PR preferences
commit:
  auto_stage_important_files: true
pr:
  draft_by_default: false
```

### Read/Write Patterns

**Reading (with fallback chain):**
```python
def get_setting(key: str, package_name: str, repo_root: Path, default=None):
    """Read setting with fallback: package → shared → user → default"""

    # 1. Package-specific (highest priority)
    package_path = repo_root / ".sc" / package_name / "settings.yaml"
    if package_path.exists():
        if value := deep_get(yaml.safe_load(package_path.read_text()), key):
            return value

    # 2. Shared repository settings
    shared_path = repo_root / ".sc" / "shared-settings.yaml"
    if shared_path.exists():
        if value := deep_get(yaml.safe_load(shared_path.read_text()), key):
            return value

    # 3. User-global settings
    user_path = Path.home() / ".sc" / package_name / "settings.yaml"
    if user_path.exists():
        if value := deep_get(yaml.safe_load(user_path.read_text()), key):
            return value

    # 4. Default
    return default

def deep_get(d: dict, key: str):
    """Get nested key using dot notation: 'provider.azure_devops.org'"""
    for k in key.split('.'):
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return None
    return d
```

**Writing (package settings only):**
```python
# Packages write to their own settings, never to shared
settings_path = Path(repo_root) / ".sc" / package_name / "settings.yaml"
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(yaml.dump(settings))
```

### Retention Policy

- **Default TTL:** Persistent
- **Backup:** User responsibility (part of `.sc/` tree)
- **Version Control:** Recommend `.gitignore` for sensitive settings
- **Never store:** Credentials, API keys, secrets (use `.claude/config.yaml` for user secrets)

### Implementation Checklist

- [ ] Read settings using fallback chain (package → shared → user → default)
- [ ] Package settings in `.sc/<package>/settings.yaml`
- [ ] Shared settings in `.sc/shared-settings.yaml` (if using provider/repo config)
- [ ] Format is YAML (not JSON)
- [ ] Includes sensible defaults for unconfigured installations
- [ ] No credentials or secrets in settings (only env var references)
- [ ] Documentation shows shared vs package settings clearly
- [ ] Code handles missing settings gracefully
- [ ] Provide initialization command if shared settings required

---

## Generated Outputs: `.sc/<package>/output/`

### Purpose
Generated artifacts, reports, and temporary files produced during plugin execution.

### Format
- **Type:** Varied (HTML, JSON, text, patch files, etc.)
- **Content:** User-facing results, analysis, diffs
- **Organization:** Subdirectories by output type

### Examples

```
.sc/sc-roslyn-diff/
  ├── settings.yaml
  ├── output/
  │   ├── Old__New.html          # HTML diff report
  │   ├── report-2026-01-22.json # Summary
  │   └── ...
  └── temp/
      ├── diff-1.txt             # Temporary text diff
      └── diff-1.patch           # Temporary git patch

.sc/sc-ci-automation/
  ├── settings.yaml
  └── output/
      ├── build-report-2026-01-22.json
      └── test-results-2026-01-22.json
```

### Retention Policy

- **Default TTL:** Persistent (user-managed cleanup)
- **Cleanup:** User deletes manually or via `rm -rf .sc/<package>/output/`
- **Size:** Recommend regular archival for large outputs
- **Version Control:** Exclude from git (add to `.gitignore`)

### Implementation Checklist

- [ ] Outputs written to `.sc/<package>/output/` (or documented alternative)
- [ ] Subdirectories used for organization
- [ ] Descriptive filenames with timestamps where relevant
- [ ] Successful operations create output, failed ones don't leave corrupted files
- [ ] Documentation shows typical output locations

---

## Special Cases

### Settings Fallback Summary

Settings are resolved in this priority order:
1. **Package settings** (`.sc/<package>/settings.yaml`) - Highest priority
2. **Shared settings** (`.sc/shared-settings.yaml`) - Repository-wide
3. **User settings** (`~/.sc/<package>/settings.yaml`) - User-global
4. **Defaults** - Hardcoded in package code

**Guidelines:**
- Read from all tiers using the fallback chain
- Write package settings freely
- Write shared settings only during initialization (with user confirmation)
- Never store actual credentials (only env var references)

### Temporary/Session Data

For runtime state that shouldn't be persisted:

```python
# Use .claude/state/ (not .sc/)
from pathlib import Path
import tempfile

session_dir = Path.cwd() / ".claude" / "state" / "sessions" / correlation_id
session_dir.mkdir(parents=True, exist_ok=True)
```

**Policy:**
- Temporary data goes to `.claude/state/`
- Include `expires_at` timestamp
- Implement TTL-based cleanup

### Background/Async Outputs

For long-running operations that produce async results:

```
.sc/sc-codex/
  ├── settings.yaml
  └── sessions/
      ├── task-abc123/
      │   ├── status.json
      │   ├── output.json
      │   └── log.jsonl
      └── task-def456/
          └── ...
```

---

## Session Start Hooks

Plugins installed globally (`~/.claude/`) often need per-session initialization when Claude Code launches in a new folder. The **session-start hook** system provides this capability.

**Full specification:** [Session Start Hook Design](./design/sc-session-start-design.md)

### Overview

When Claude Code starts a session, the `sc-manage` orchestrator:
1. Discovers all `sc-*` plugins (global and local)
2. Deduplicates (local takes precedence over global)
3. Fires each plugin's `session_start` script asynchronously
4. Exits immediately (non-blocking)

A detached watchdog enforces a 30-second timeout on all plugin scripts.

### Manifest Declaration

```yaml
# manifest.yaml
hooks:
  # Script MUST be named <plugin>_session_start.py to avoid conflicts
  session_start: scripts/sc_git_worktree_session_start.py

requires:
  packages:
    - sc-manage   # Required dependency
```

### Script Contract

| Argument | Description |
|----------|-------------|
| `--session-path` | Folder Claude was launched from (may not be a git repo) |
| `--plugin-path` | Plugin installation path |
| `--scope` | `global` or `local` |

**Required behavior:**
1. **Fast check first**: If `.sc/<package>/settings.yaml` exists, exit immediately
2. **Idempotent**: Safe to run every session
3. **Handle non-git folders**: Check for `.git`; record `git: "none"` if absent
4. **Self-logging**: Write to `.claude/state/logs/<package>/session-start.log`
5. **Complete within 10 seconds** or background heavy work

### Example Pattern

```python
#!/usr/bin/env python3
"""scripts/sc_example_session_start.py"""

import sys
from pathlib import Path

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-path", required=True, type=Path)
    parser.add_argument("--plugin-path", required=True, type=Path)
    parser.add_argument("--scope", required=True, choices=["global", "local"])
    args = parser.parse_args()

    # 1. Quick check: already initialized?
    settings_path = args.session_path / ".sc" / "sc-example" / "settings.yaml"
    if settings_path.exists():
        sys.exit(0)  # Already done

    # 2. Detect environment (git or not)
    is_git = (args.session_path / ".git").exists()

    # 3. Initialize settings
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    import yaml
    from datetime import datetime
    settings = {
        "initialized_at": datetime.now().isoformat(),
        "git": {"detected": True} if is_git else "none",
    }
    settings_path.write_text(yaml.dump(settings))

    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Prerequisite

The `sc-manage` package must be installed **globally** to register the `SessionStart` hook in `~/.claude/hooks/hooks.json`. Plugins using session-start hooks should declare `sc-manage` as a dependency.

---

## Migration Guide

If your package currently uses non-standard locations:

### From `.claude/` to `.sc/`

**Old:**
```yaml
.claude/ci-automation.yaml
.claude/config.yaml
```

**New:**
```yaml
.sc/sc-ci-automation/settings.yaml
```

**Migration Steps:**
1. Read settings from old location (with fallback)
2. Write settings to new location
3. Log migration event
4. Update README
5. Document in CHANGELOG

### From JSON to YAML

**Old:**
```json
.sc/roslyn-diff/settings.json
```

**New:**
```yaml
.sc/sc-roslyn-diff/settings.yaml
```

**Migration Steps:**
1. Convert JSON to YAML programmatically
2. Support reading both formats (with deprecation warning)
3. Always write to YAML format
4. Document in CHANGELOG

---

## Verification Checklist

Use this checklist when creating or updating a package:

- [ ] **Logs documented** in README under "Logs" section
  - Location: `.claude/state/logs/<package>/`
  - Example commands provided
- [ ] **Settings documented** in README
  - Shared settings usage (`.sc/shared-settings.yaml`) if applicable
  - Package settings location (`.sc/<package>/settings.yaml`)
  - Example configuration shown
  - Fallback chain explained
- [ ] **Code follows conventions**
  - Logs written to `.claude/state/logs/<package>/`
  - Settings read using fallback chain (package → shared → user → default)
  - Package settings written to `.sc/<package>/settings.yaml`
  - Shared settings only written during initialization
  - Outputs written to `.sc/<package>/output/`
- [ ] **No hardcoded paths** in source code
  - Derive package name programmatically
  - Use `Path.cwd()` as repo root reference
- [ ] **.gitignore configured**
  - `.claude/state/logs/` ignored
  - `.sc/<package>/settings.yaml` ignored (cached state)
  - `.sc/shared-settings.yaml` usually committed
- [ ] **Error handling**
  - Graceful fallback if settings missing
  - Clear error messages when shared settings required but missing
  - Suggest initialization command if shared settings needed
- [ ] **Session start hook** (if per-session initialization needed)
  - Script named `scripts/<plugin>_session_start.py`
  - Declared in `manifest.yaml` under `hooks.session_start`
  - Fast initialization check (exit if already initialized)
  - Handles non-git folders (`git: "none"`)
  - Depends on `sc-manage`

---

## Examples by Package

### sc-commit-push-pr (Shared + Package Settings)
```markdown
## Configuration

This package reads protected branches from:
```yaml
.sc/shared-settings.yaml  # Protected branches (auto-detected from git-flow or manual)
```

Package-specific settings:
```yaml
.sc/sc-commit-push-pr/settings.yaml  # Commit/PR preferences (optional)
```

Provider info (Azure/GitHub org/project/repo) is auto-detected from git remote.

## Logs
```
.claude/state/logs/sc-commit-push-pr/
```
```

### sc-roslyn-diff (Package + Output)
```markdown
## Configuration

Provider info auto-detected from git remote (no storage needed).

Package settings:
```yaml
.sc/sc-roslyn-diff/settings.yaml  # files_per_agent, etc.
```

Generated HTML reports:
```
.sc/sc-roslyn-diff/output/
```
```

### sc-codex (Logs only)
```markdown
## Logs

Runtime and hook events:
```
.claude/state/logs/sc-codex/
```

View recent events:
```bash
cat .claude/state/logs/sc-codex/latest.json | jq .
```
```

---

## FAQ

**Q: Why `.sc/` instead of `.claude/`?**
A: Separates user-managed CLI configuration (`.claude/`) from plugin-specific data (`.sc/`). Easier to manage, backup, and clean up.

**Q: When should I use shared settings vs package settings?**
A: Use shared settings (`.sc/shared-settings.yaml`) only for workflow-critical repository-wide config (currently just protected branches). Most things should be auto-detected. Use package settings (`.sc/<package>/settings.yaml`) for package-specific config like thresholds, feature flags.

**Q: Can I use JSON for settings instead of YAML?**
A: No. All plugins use YAML for consistency with the CLI ecosystem. JSON can be internal format, but persisted settings are YAML.

**Q: Where do I store secrets?**
A: Never in `.sc/` files. Use environment variables and reference them by name in settings (e.g., `github_token: GITHUB_TOKEN`). Document in troubleshooting guide.

**Q: Should I commit `.sc/shared-settings.yaml` to git?**
A: Yes - it only contains protected branches. No secrets, no provider-specific info (that's auto-detected).

**Q: How often should I clean up logs?**
A: Implement a background agent or document manual cleanup. 14-day default is reasonable for local development; adjust for your use case.

**Q: Can packages write to shared settings automatically?**
A: Only from SubAgentStart hooks when auto-detecting git-flow configuration. Not from agent execution itself.

**Q: How do I add a new field to shared settings?**
A: First verify it can't be auto-detected and is truly workflow-critical for all packages. Then submit a PR updating the normative schema table. Most things should be auto-detected, not stored.

**Q: What if I don't use git-flow?**
A: Create `.sc/shared-settings.yaml` manually with your protected branches. Hooks will find it and use it.

---

## Related Documentation

- **[Architecture Guidelines](./claude-code-skills-agents-guidelines-0.4.md)** - State Management section
- **[PQA.md](../pm/PQA.md)** - Testing and observability
- **[Security Scanning Guide](./SECURITY-SCANNING-GUIDE.md)** - What not to log
