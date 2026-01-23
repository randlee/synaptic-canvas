# Plugin Storage Conventions

**Status:** Normative (enforced across all packages)
**Last Updated:** January 22, 2026
**Audience:** Plugin developers, package maintainers

All Synaptic Canvas plugins follow standardized storage conventions to ensure consistent behavior, troubleshooting, and observability across the ecosystem.

---

## Quick Reference

| Purpose | Location | Format | Scope | TTL |
|---------|----------|--------|-------|-----|
| **Runtime Logs** | `.claude/state/logs/<package>/` | JSON | Per-project | 14 days |
| **Settings/Cache** | `.sc/<package>/settings.yaml` | YAML | Per-project | Persistent |
| **Generated Output** | `.sc/<package>/output/` | Varied | Per-project | Persistent |

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

## Settings & Cache: `.sc/<package>/settings.yaml`

### Purpose
Repository-specific configuration, cached values, and runtime state that persists across invocations.

### Format
- **Type:** YAML (single file per package)
- **Content:** Configuration, cached resolutions, defaults
- **Scope:** Project-local (not global)

### Examples

```yaml
# .sc/sc-roslyn-diff/settings.yaml
azure_devops:
  org: "myorg"
  project: "myproject"
  repo: "myrepo"
files_per_agent: 15

# .sc/sc-ci-automation/settings.yaml
build_command: "dotnet build"
test_command: "pytest"
allowed_agents:
  - ci-validate-agent
  - ci-build-agent

# .sc/sc-startup/settings.yaml
checklist_path: ".claude/master-checklist.md"
config_path: ".claude/sc-startup.yaml"
```

### Read/Write Patterns

**Reading (with fallback chain):**
```python
# 1. Project-local settings
paths = [
    Path(repo_root) / ".sc" / package_name / "settings.yaml",
    Path(repo_root) / ".sc" / package_name / "config.yaml",  # legacy
]
# 2. Use defaults if not found
settings = load_settings(paths) or defaults()
```

**Writing:**
```python
# Always write to primary location
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

- [ ] Settings stored in `.sc/<package>/settings.yaml` (not `.claude/`)
- [ ] Format is YAML (not JSON)
- [ ] Includes sensible defaults for unconfigured installations
- [ ] No credentials or secrets in defaults
- [ ] Documentation shows example configuration
- [ ] Code handles missing settings gracefully
- [ ] `.gitignore` excludes `.sc/` directory (optional but recommended)

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

### Global/User-Level Configuration

Some packages support global settings in `~/.sc/`:

```yaml
# ~/.sc/sc-github-issue/settings.yaml
github_token: <env var reference>
default_labels: ["bug", "enhancement"]
```

**Policy:**
- Use `.sc/<package>/settings.yaml` as primary (project-local)
- Fall back to `~/.sc/<package>/settings.yaml` (user-global)
- Never check credentials into git

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
- [ ] **Settings documented** in README or TROUBLESHOOTING
  - Location: `.sc/<package>/settings.yaml`
  - Example configuration shown
  - Default values documented
- [ ] **Code follows conventions**
  - Logs written to `.claude/state/logs/`
  - Settings read/written to `.sc/<package>/`
  - Outputs written to `.sc/<package>/output/`
- [ ] **No hardcoded paths** in source code
  - Derive package name programmatically
  - Use `Path.cwd()` as repo root reference
- [ ] **.gitignore configured**
  - `.claude/state/logs/` ignored
  - `.sc/` directory handling documented
- [ ] **Error handling**
  - Graceful fallback if settings missing
  - Clear error messages when directories can't be created

---

## Examples by Package

### sc-codex (Logs)
```markdown
## Logs

Runtime and hook events are written to:
- `.claude/state/logs/sc-codex/`

View recent events:
```bash
cat .claude/state/logs/sc-codex/latest.json | jq .
```
```

### sc-roslyn-diff (Settings + Output)
```markdown
## Configuration

Repository-specific settings are cached in:
```
.sc/sc-roslyn-diff/settings.yaml
```

Generated HTML reports are written to:
```
.sc/sc-roslyn-diff/output/
```
```

### sc-startup (Settings + Logs)
```markdown
## Configuration

Project settings:
```yaml
.claude/sc-startup.yaml       # Project config (created during init)
.sc/sc-startup/settings.yaml  # Cached resolved settings
```

Logs:
```bash
.claude/state/logs/sc-startup/
```
```

---

## FAQ

**Q: Why `.sc/` instead of `.claude/`?**
A: Separates user-managed CLI configuration (`.claude/`) from plugin-specific data (`.sc/`). Easier to manage, backup, and clean up.

**Q: Can I use JSON for settings instead of YAML?**
A: No. All plugins use YAML for consistency with the CLI ecosystem. JSON can be internal format, but persisted settings are YAML.

**Q: Where do I store secrets?**
A: Never in `.sc/` or `.claude/state/`. Use environment variables, `.claude/config.yaml` (user-only), or platform secret management. Document in troubleshooting guide.

**Q: How often should I clean up logs?**
A: Implement a background agent or document manual cleanup. 14-day default is reasonable for local development; adjust for your use case.

**Q: Can I use global settings (`~/.sc/`)?**
A: Yes, as a fallback. But primary location is always project-local `.sc/<package>/`. Document the fallback chain clearly.

---

## Related Documentation

- **[Architecture Guidelines](./claude-code-skills-agents-guidelines-0.4.md)** - State Management section
- **[PQA.md](../pm/PQA.md)** - Testing and observability
- **[Security Scanning Guide](./SECURITY-SCANNING-GUIDE.md)** - What not to log
