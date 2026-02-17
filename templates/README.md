# Jenga Templates for SC Packages

**Jenga templates** provide reusable, self-contained code for Synaptic Canvas packages. Templates use variable substitution (`{{VARIABLE}}`) to customize functionality for each package without code duplication.

## Available Templates

### 1. **sc-logging.jenga.py** - Structured Logging
Pydantic-validated structured logging with environment variable support.

**Features**:
- ISO 8601 timestamps with timezone
- Pydantic v2 validation
- Package-specific log directories (`.claude/state/logs/<package>/`)
- Environment variable helpers (`get_project_dir()`, `get_plugin_root()`)
- Hook event logging (`log_hook_event()`)
- Security validation (no secrets in logs)
- 4-level fallback chain for project root discovery

**Jenga Variables**:
- `{{PACKAGE_NAME}}` - Package identifier (e.g., "sc-git-worktree")
- `{{EXTRA_IMPORTS}}` - Package-specific imports (optional)
- `{{EXTRA_FIELDS}}` - Package-specific Pydantic fields (optional)

### 2. **sc-shared.jenga.py** - Agent Runner
Registry-based agent validation with SHA-256 integrity checking.

**Features**:
- 5-stage agent validation pipeline
- SHA-256 integrity verification
- Registry-based version checking
- Audit logging integration
- Pydantic v2 models for type safety
- YAML parsing with fallback (no dependencies)

**Jenga Variables**:
- `{{PACKAGE_NAME}}` - Package identifier
- `{{AGENT_TYPES}}` - Optional agent type list
- `{{CUSTOM_VALIDATION_HOOKS}}` - Package-specific validation
- `{{REGISTRY_DEFAULT}}` - Override registry path
- `{{LOGS_DIR}}` - Override logs directory

---

## Quick Start

### Automated Expansion (Recommended)

Use the expansion script to automatically generate package-specific files:

```bash
# Expand templates for a package
python3 scripts/expand-jenga-templates.py packages/sc-git-worktree

# Creates:
#   packages/sc-git-worktree/scripts/sc_git_worktree_logging.py
#   packages/sc-git-worktree/scripts/sc_git_worktree_shared.py
```

**Why automated?**
- ✅ Prevents filename collisions during installation
- ✅ Automatic package name detection
- ✅ Replaces all Jenga variables
- ✅ Cleans up template comments
- ✅ Consistent naming conventions

### Manual Expansion (Not Recommended)

If you must expand manually:

```bash
# Copy with package-specific filename
cp templates/sc-logging.jenga.py packages/my-pkg/scripts/my_pkg_logging.py

# Replace {{PACKAGE_NAME}}
sed -i '' 's/{{PACKAGE_NAME}}/my-pkg/g' packages/my-pkg/scripts/my_pkg_logging.py

# Clean up Jenga comments
sed -i '' '/{{EXTRA_IMPORTS}}/d' packages/my-pkg/scripts/my_pkg_logging.py
sed -i '' '/{{EXTRA_FIELDS}}/d' packages/my-pkg/scripts/my_pkg_logging.py
```

⚠️ **Manual expansion is error-prone** - use the automation script instead.

---

## Package-Specific Naming Convention

**Critical**: To prevent installation collisions, expanded templates MUST use package-specific filenames.

### ❌ Wrong (Causes Collisions)
```
packages/sc-git-worktree/scripts/sc_logging.py
packages/sc-github-issue/scripts/sc_logging.py
```

When installed to customer repos:
```
.claude/scripts/sc_logging.py  ❌ OVERWRITE COLLISION!
```

### ✅ Correct (No Collisions)
```
packages/sc-git-worktree/scripts/sc_git_worktree_logging.py
packages/sc-github-issue/scripts/sc_github_issue_logging.py
```

When installed to customer repos:
```
.claude/scripts/sc_git_worktree_logging.py  ✅ Unique
.claude/scripts/sc_github_issue_logging.py  ✅ Unique
```

**Naming Format**:
```
<package-name-with-underscores>_<template-type>.py
```

Examples:
- `sc-git-worktree` → `sc_git_worktree_logging.py`
- `sc-github-issue` → `sc_github_issue_logging.py`
- `sc-commit-push-pr` → `sc_commit_push_pr_logging.py`

---

## Using sc-logging Template

### 1. Expand Template

```bash
python3 scripts/expand-jenga-templates.py packages/my-package --template logging
```

### 2. Import in Your Scripts

```python
# In packages/my-package/scripts/my_script.py
from my_package_logging import log_event, get_project_dir, log_hook_event

# Basic event logging
log_event(
    event="worktree_create",
    level="info",
    branch="feature-x",
    outcome="success"
)

# Hook event logging
log_hook_event(
    event="PreToolUse-Task",
    hook_data=hook_payload,
    decision={"allowed": True, "reason": "Validation passed"}
)

# Get project directory (4-level fallback)
project_dir = get_project_dir()
config_file = project_dir / ".sc" / "my-package" / "settings.yaml"
```

### 3. Add Custom Fields (Optional)

Edit the expanded file to add package-specific fields:

```python
# In packages/my-package/scripts/my_package_logging.py
from typing import Literal, Optional
from pydantic import Field

class LogEntry(BaseLogEntry):
    """Extended log entry with my-package specific fields."""

    # Custom fields
    session_id: Optional[str] = Field(default=None, description="Session ID")
    operation: Optional[Literal["create", "update", "delete"]] = None
    duration_ms: Optional[int] = None

    # Custom validators
    @field_validator("session_id", mode="before")
    @classmethod
    def validate_session_id(cls, v):
        if v is not None and not isinstance(v, str):
            raise ValueError("session_id must be string")
        return v
```

### 4. Write Tests

```python
# In packages/my-package/tests/test_logging.py
from tests.logging.test_base import LoggingTestCase
from scripts.my_package_logging import LogEntry, log_event

class TestMyPackageLogging(LoggingTestCase):
    def test_logging_works(self):
        log_event(event="test", level="info", session_id="abc123")

        self.assert_log_file_exists("my-package", "test")
        entries = self.read_log_entries("my-package", "test")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["event"], "test")
        self.assertEqual(entries[0]["session_id"], "abc123")
```

---

## Using sc-shared Template

### 1. Expand Template

```bash
python3 scripts/expand-jenga-templates.py packages/my-package --template shared
```

### 2. Import Agent Runner

```python
# In packages/my-package/scripts/my_agent_invoker.py
from my_package_shared import (
    AgentInvokeRequest,
    invoke_agent_runner,
    get_project_dir
)

# Invoke agent with registry validation
request = AgentInvokeRequest(
    agent="my-agent-create",
    params={"branch": "feature-x", "upstream": "origin"},
    registry_path=".claude/agents/registry.yaml"
)

result = invoke_agent_runner(request)

if result.ok:
    # Pass task_prompt to Task tool
    print(result.task_prompt)
    print(f"Audit: {result.audit_path}")
else:
    print(f"Error: {result.error}")
```

### 3. Customize Validation (Optional)

Add package-specific validation hooks:

```python
# In packages/my-package/scripts/my_package_shared.py

# Add to {{CUSTOM_VALIDATION_HOOKS}} section
def validate_agent_type(agent_name: str) -> None:
    """Validate agent type is in allowed list."""
    allowed_types = ["create", "scan", "cleanup", "abort"]
    if agent_name not in allowed_types:
        raise ValueError(f"Invalid agent type: {agent_name}")

def validate_branch_params(params: Dict[str, Any]) -> None:
    """Validate branch parameters."""
    required = ["branch", "upstream"]
    for field in required:
        if field not in params:
            raise ValueError(f"Missing required parameter: {field}")
```

---

## Environment Variable Availability

Templates include robust environment variable helpers with 4-level fallback:

### Fallback Chain

1. **CLAUDE_PROJECT_DIR** (Claude Code hook context)
2. **CODEX_PROJECT_DIR** (Codex compatibility)
3. **Project marker search** (`.git/`, `.claude/`, `.sc/`)
4. **Path.cwd()** (last resort)

### Context Availability Matrix

| Context | CLAUDE_PROJECT_DIR | CLAUDE_PLUGIN_ROOT | Uses Fallback |
|---------|-------------------|-------------------|---------------|
| PreToolUse Hook | ✅ Available | ✅ Available | No |
| PostToolUse Hook | ✅ Available | ✅ Available | No |
| Bash Tool | ❌ Not Available | ❌ Not Available | Yes |
| Background Agent | ❌ Not Available | ❌ Not Available | Yes |
| Agent Scripts | ⚠️ Unknown | ⚠️ Unknown | Yes (safe) |

### Usage Pattern

```python
from my_package_logging import get_project_dir, get_plugin_root

# Always works - uses fallback chain
project_dir = get_project_dir()  # Never returns None
plugin_root = get_plugin_root()  # Never returns None

# Use for all path construction
logs_dir = project_dir / ".claude" / "state" / "logs" / "my-package"
config_file = project_dir / ".sc" / "my-package" / "settings.yaml"
```

---

## Testing Templates

### Base Test Infrastructure

Use `LoggingTestCase` for consistent testing:

```python
from tests.logging.test_base import LoggingTestCase
from tests.logging.schemas import StandardLogEntry

class TestMyPackageLogging(LoggingTestCase):
    def test_log_entry_valid(self):
        """Test log entry validates against schema."""
        entry_json = '{"timestamp":"2026-02-11T10:00:00Z","event":"test","package":"my-pkg","level":"info"}'
        entry = self.assert_log_entry_valid(entry_json, StandardLogEntry)
        self.assertEqual(entry.package, "my-pkg")

    def test_no_secrets(self):
        """Test no secrets logged."""
        self.write_log_entry("my-pkg", "test", {"password": "safe"})
        # Should not raise (field name "password" alone is OK, pattern looks for "password=value")
        self.assert_no_secrets_logged()
```

---

## Best Practices

### 1. Always Use Automation Script
```bash
# ✅ Do this
python3 scripts/expand-jenga-templates.py packages/my-package

# ❌ Don't do this
cp templates/sc-logging.jenga.py packages/my-package/scripts/sc_logging.py
```

### 2. Package-Specific Filenames
```python
# ✅ Correct
from my_package_logging import log_event

# ❌ Wrong (causes collisions)
from sc_logging import log_event
```

### 3. Use Fallback Helpers Everywhere
```python
# ✅ Correct (works in all contexts)
project_dir = get_project_dir()

# ❌ Wrong (breaks in background agents)
project_dir = Path(os.getenv("CLAUDE_PROJECT_DIR"))
```

### 4. Validate with Pydantic
```python
# ✅ Correct (type-safe)
log_event(event="test", level="info", count=5)

# ❌ Wrong (no validation)
log_file.write(json.dumps({"event": "test", "count": "not-a-number"}))
```

### 5. Test with LoggingTestCase
```python
# ✅ Correct (reusable test infrastructure)
class TestMyLogging(LoggingTestCase):
    def test_it(self):
        self.assert_log_file_exists("pkg", "event")

# ❌ Wrong (reinventing the wheel)
class TestMyLogging(unittest.TestCase):
    def test_it(self):
        log_file = Path(".claude/state/logs/...")  # Manual setup
```

---

## Troubleshooting

### Issue: Import Error
```
ImportError: cannot import name 'log_event' from 'sc_logging'
```

**Cause**: Using generic name instead of package-specific name

**Solution**:
```python
# Change from:
from sc_logging import log_event

# To:
from my_package_logging import log_event
```

### Issue: File Collision During Installation
```
Warning: File .claude/scripts/sc_logging.py already exists
```

**Cause**: Multiple packages trying to install to same filename

**Solution**: Use automation script which creates package-specific filenames

### Issue: Environment Variables Not Available
```
TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'
```

**Cause**: Assuming `CLAUDE_PROJECT_DIR` exists without fallback

**Solution**: Use `get_project_dir()` which has 4-level fallback

---

## Template Updates

When templates are updated in this repository:

1. **Check changelog** - Review what changed
2. **Re-expand templates** - Run expansion script again
3. **Preserve customizations** - Merge your custom fields/validators
4. **Update imports** - If function signatures changed
5. **Test thoroughly** - Run full test suite

---

## Support

**Questions?** See:
- [Architecture Guidelines](../docs/claude-code-skills-agents-guidelines-0.4.md)
- [Tool Use Best Practices](../docs/agent-tool-use-best-practices.md)
- [Plugin Storage Conventions](../docs/PLUGIN-STORAGE-CONVENTIONS.md)

**Issues?** Check:
- Automation script: `scripts/expand-jenga-templates.py --help`
- Test infrastructure: `tests/logging/test_base.py`
- Example implementations: `packages/sc-git-worktree/`
