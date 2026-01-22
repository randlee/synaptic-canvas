# Plugin Conventions

Standard directory structure and conventions for Synaptic Canvas plugins.

## Directory Structure Overview

```
.claude/                          # Claude Code standard directory
├── state/
│   └── logs/<package>/           # Plugin-specific logs
└── ...

.sc/                              # Synaptic Canvas state directory
├── shared-settings.yml           # Repository-wide shared settings
├── <package>/
│   ├── settings.yml              # Package-specific settings
│   ├── cache/                    # Cached data
│   └── output/                   # Generated artifacts
└── ...
```

---

## Shared Settings

**Location**: `.sc/shared-settings.yml`

Repository-wide settings shared across all plugins. This is the single source of truth for repository configuration.

### Schema

```yaml
# .sc/shared-settings.yml

# Git branch configuration
git:
  main_branch: main              # Primary branch (main or master)
  develop_branch: develop        # Development branch
  protected_branches:            # Branches that should never be deleted
    - main
    - master
    - develop
    - release/*

# Azure DevOps configuration (optional)
azure:
  organization: my-org           # Azure DevOps organization
  project: my-project            # Azure DevOps project
  repository: my-repo            # Repository name (if different from GitHub)

# GitHub configuration (optional, usually auto-detected)
github:
  owner: owner-name              # GitHub owner/org
  repo: repo-name                # Repository name

# CI/CD configuration
ci:
  build_command: dotnet build    # Default build command
  test_command: dotnet test      # Default test command
  timeout_minutes: 30            # Default timeout for CI operations
```

### Usage in Plugins

Plugins should read shared settings at startup:

```python
import yaml
from pathlib import Path

def load_shared_settings() -> dict:
    """Load repository-wide shared settings."""
    settings_path = Path(".sc/shared-settings.yml")
    if settings_path.exists():
        with open(settings_path) as f:
            return yaml.safe_load(f) or {}
    return {}

# Example: Get main branch name
settings = load_shared_settings()
main_branch = settings.get("git", {}).get("main_branch", "main")
```

### Azure DevOps URL Construction

With shared settings, plugins can construct Azure DevOps URLs:

```python
def get_azure_repo_url(settings: dict) -> str:
    """Construct Azure DevOps repository URL."""
    azure = settings.get("azure", {})
    org = azure.get("organization")
    project = azure.get("project")
    repo = azure.get("repository")

    if org and project and repo:
        return f"https://dev.azure.com/{org}/{project}/_git/{repo}"
    return None

def get_azure_pr_url(settings: dict, pr_id: int) -> str:
    """Construct Azure DevOps PR URL."""
    azure = settings.get("azure", {})
    org = azure.get("organization")
    project = azure.get("project")
    repo = azure.get("repository")

    if org and project and repo:
        return f"https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{pr_id}"
    return None
```

---

## Logs

**Location**: `.claude/state/logs/<package>/`

Plugin-specific logs for debugging and audit trails.

### Format

- **File format**: JSON Lines (`.jsonl`) or plain text (`.log`)
- **Naming**: `<operation>-<timestamp>.jsonl`
- **Rotation**: Plugins should manage their own log rotation

### Examples

```
.claude/state/logs/
├── sc-codex/
│   ├── run-2024-01-20T10-30-00.jsonl
│   └── run-2024-01-20T11-45-00.jsonl
├── sc-roslyn-diff/
│   └── diff-2024-01-20T09-15-00.jsonl
└── sc-ci-automation/
    └── build-2024-01-20T14-00-00.log
```

### Log Entry Schema

```json
{
  "timestamp": "2024-01-20T10:30:00Z",
  "level": "info",
  "event": "operation_started",
  "package": "sc-codex",
  "data": {}
}
```

---

## Package-Specific Settings

**Location**: `.sc/<package>/settings.yml`

Settings specific to a single package, cached values, and user preferences.

### Examples

```yaml
# .sc/sc-roslyn-diff/settings.yml
last_used_context: 3
default_output_format: html
azure_project_cache:
  resolved_at: 2024-01-20T10:00:00Z
  organization: my-org
  project: my-project
```

```yaml
# .sc/sc-ci-automation/settings.yml
auto_fix_enabled: true
max_retry_attempts: 3
preferred_pr_template: standard
```

---

## Cache

**Location**: `.sc/<package>/cache/`

Temporary cached data that can be regenerated.

### Guidelines

- Cache should be safe to delete at any time
- Include cache invalidation timestamps
- Respect `.gitignore` (cache directories should be ignored)

### Examples

```
.sc/sc-repomix-nuget/cache/
├── package-metadata/
│   ├── Newtonsoft.Json.json
│   └── Microsoft.Extensions.Logging.json
└── dependency-graph.json
```

---

## Output

**Location**: `.sc/<package>/output/`

Generated artifacts, reports, and results.

### Guidelines

- Output should be human-readable where possible
- Include timestamps in filenames for multiple runs
- Large outputs may use subdirectories

### Examples

```
.sc/sc-roslyn-diff/output/
├── diff-2024-01-20T10-30-00.html
├── diff-2024-01-20T10-30-00.json
└── reports/
    └── weekly-summary.html

.sc/sc-ci-automation/output/
├── build-report-2024-01-20.md
└── test-results-2024-01-20.xml
```

---

## Temporary Files

**Location**: `.sc/<package>/temp/`

Short-lived files that should be cleaned up after use.

### Guidelines

- Clean up temp files after operations complete
- Use unique filenames to avoid conflicts
- Consider using Python's `tempfile` module within this directory

---

## .gitignore Recommendations

Add to repository `.gitignore`:

```gitignore
# Synaptic Canvas state
.sc/*/cache/
.sc/*/temp/
.sc/*/output/

# Keep settings (optional - remove if settings should be shared)
# !.sc/shared-settings.yml
# !.sc/*/settings.yml
```

---

## Creating Shared Settings

For new repositories, create `.sc/shared-settings.yml`:

```bash
mkdir -p .sc
cat > .sc/shared-settings.yml << 'EOF'
# Synaptic Canvas Shared Settings
# Repository-wide configuration for all SC plugins

git:
  main_branch: main
  develop_branch: develop
  protected_branches:
    - main
    - develop

# Uncomment and configure for Azure DevOps
# azure:
#   organization: your-org
#   project: your-project
#   repository: your-repo
EOF
```

---

## Related Documentation

- [Marketplace Infrastructure](MARKETPLACE-INFRASTRUCTURE.md) - Registry and hosting
- [Skills/Agents Guidelines](claude-code-skills-agents-guidelines-0.4.md) - Plugin architecture
- [Versioning Strategy](versioning-strategy.md) - Version management
