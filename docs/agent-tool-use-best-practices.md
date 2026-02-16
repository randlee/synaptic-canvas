# Agent Tool Use Best Practices

This guide captures learned patterns for using fenced JSON, tool calls, and hooks to validate and gate agent behavior.

**Scope:** Primarily focused on **Claude Code**. Codex users see "Hooks: Where They Actually Work" section for ai_cli differences.

## Key Principles

- Use fenced JSON for all agent inputs and outputs.
- Validate inputs early with hooks before a tool runs (via settings.json in Claude Code).
- Use Python hooks for cross-platform compatibility.
- Prefer schema validation (pydantic) over ad-hoc parsing.
- Keep tool outputs machine-readable; avoid mixed prose + JSON.

## Script Dependency Standards

- Always declare runtime dependencies in `manifest.yaml` under `requires`.
- Use a structured `requires` object:
  - `cli`: command-line tools (e.g., `python3`, `codex`, `git`)
  - `python`: pip-installable packages required by scripts (e.g., `pydantic`, `pyyaml`)
- `sc-manage` installs `requires.python` during package install (prefers venv; otherwise uses `pip --user`).
- If a script imports a package, it must be listed in `requires.python` and mentioned in the package README.

## Fenced JSON Everywhere

### Agent input

````markdown
```json
{
  "message": "hello",
  "count": 3
}
```
````

### Agent output (minimal envelope)

````markdown
```json
{
  "success": true,
  "data": { "result": "ok" },
  "error": null
}
```
````

## PreToolUse Hook Pattern (Python)

Hooks run before a tool executes. They receive a JSON payload on stdin with fields like:
- `tool_input.command` (for Bash)
- `tool` (tool name)
- `event` (hook event type)

Use this to validate or block tool usage.

### Example: Subagent hook in frontmatter

```yaml
---
name: echo-agent
description: Echo a message N times
version: 0.1.0
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/validate_echo_hook.py"
---
```

### Example: Python hook validator (stdlib only)

```python
#!/usr/bin/env python3
import json
import re
import sys

payload = json.load(sys.stdin)
command = (payload.get("tool_input") or {}).get("command", "")

match = re.search(r"\{.*\}", command, re.DOTALL)
if not match:
    print("Expected JSON payload in command", file=sys.stderr)
    sys.exit(2)

try:
    data = json.loads(match.group(0))
except Exception:
    print("Invalid JSON payload in command", file=sys.stderr)
    sys.exit(2)

if not isinstance(data.get("message"), str) or not isinstance(data.get("count"), int):
    print("Expected JSON with string 'message' and int 'count'", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
```

Exit code `2` blocks the tool and returns the error message to Claude.

## Allowed Path Validation (Claude + Codex)

When an agent needs to validate file paths, use the allowed directories from the runtime settings instead of assuming repo-root-only access.

Key sources:
- `cwd` (always allowed)
- `$CLAUDE_PROJECT_DIR` (Claude project root)
- `$CODEX_PROJECT_DIR` (Codex project root)
- `~/.claude/settings.json`
- `<project>/.claude/settings.json`
- `~/.codex/settings.json`
- `<project>/.codex/settings.json`
- `$CODEX_HOME/settings.json` (if set)

Example hook helper (stdlib only):

```python
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

hook_input = json.load(sys.stdin)
cwd = Path(hook_input.get("cwd") or os.getcwd()).resolve()
project_dir = os.getenv("CLAUDE_PROJECT_DIR") or os.getenv("CODEX_PROJECT_DIR")
codex_home = os.getenv("CODEX_HOME")

allowed = {cwd}
if project_dir:
    allowed.add(Path(project_dir).expanduser().resolve())

settings_paths = [
    Path("~/.claude/settings.json").expanduser(),
    Path(project_dir or "") / ".claude" / "settings.json",
    Path("~/.codex/settings.json").expanduser(),
    Path(project_dir or "") / ".codex" / "settings.json",
]
if codex_home:
    settings_paths.append(Path(codex_home) / "settings.json")

for path in settings_paths:
    if not path.exists():
        continue
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        continue
    extra = data.get("permissions", {}).get("additionalDirectories", [])
    if isinstance(extra, list):
        for entry in extra:
            if isinstance(entry, str) and entry.strip():
                allowed.add(Path(entry).expanduser().resolve())

def is_allowed(target: Path) -> bool:
    target = target.resolve()
    return any(target.is_relative_to(base) for base in allowed)
```

Use `is_allowed()` before reading/writing user-supplied paths and return a clear error if the path is outside the allowed set.

## Pydantic Validation (Recommended)

Use pydantic for robust schema checks and clear error messages.

```python
#!/usr/bin/env python3
import json
import re
import sys
from pydantic import BaseModel, ValidationError

class EchoInput(BaseModel):
    message: str
    count: int

payload = json.load(sys.stdin)
command = (payload.get("tool_input") or {}).get("command", "")

match = re.search(r"\{.*\}", command, re.DOTALL)
if not match:
    print("Expected JSON payload in command", file=sys.stderr)
    sys.exit(2)

try:
    data = json.loads(match.group(0))
    EchoInput.model_validate(data)
except ValidationError as exc:
    print(exc, file=sys.stderr)
    sys.exit(2)

sys.exit(0)
```

## Hooks: Where They Actually Work

### Critical Clarification

**Agent frontmatter hooks are NOT supported in Claude Code.** They are designed for **Codex integration via ai_cli** (see below).

For Claude Code, use **settings.json hooks** to validate agent spawns (see "Gating Agents" section).

### Claude Code

**Supported:** PreToolUse hooks in `settings.json` (or `~/.claude/settings.json`)
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task",
        "hooks": [{"type": "command", "command": "python3 .claude/scripts/validate.py"}]
      }
    ]
  }
}
```

**NOT Supported:** PreToolUse or SubAgentStart hooks in agent frontmatter
```yaml
---
name: my-agent
hooks:
  PreToolUse:  # ❌ This does NOT fire in Claude Code
    - matcher: "Bash"
      hooks: [...]
---
```

### Codex Integration (ai_cli)

Agent frontmatter hooks **are** supported in Codex via the `ai_cli` runner:

```yaml
---
name: my-agent
hooks:
  PreToolUse:  # ✅ This DOES fire in Codex via ai_cli
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/validate_hook.py"
---
```

**How ai_cli processes hooks:**
1. Parses agent frontmatter `hooks: PreToolUse`
2. Before agent execution, runs `type: command` hooks with stdin JSON
3. Exit 0 = allow agent to proceed
4. Exit 2 = block agent execution
5. Logs hook execution with `hook_start`/`hook_end` events

**Agent resolution order (Codex):**
1. If `subagent_type` is a file path → use directly
2. Search upward: `.claude/agents/<name>.md`
3. Fallback: `~/.claude/agents/<name>.md`
4. Not found:
   - **Codex**: Error (fail fast)
   - **Claude Code**: Skip hooks (assumes built-in agent)

See: `packages/sc-codex/scripts/ai_cli/README.md` (lines 103-118)

### Slash Commands

**Frontmatter hooks are NOT supported.** Use `!` pre-exec lines in the command body to run scripts before the model prompt, and `allowed-tools` to permit those commands.

### Example: `/git-pr` with `!` pre-exec

Command frontmatter (abridged):

```yaml
---
allowed-tools: Bash(python3 .claude/scripts/git-pr-status.py*)
name: git-pr
version: 0.6.0
description: Show outstanding PRs and their CI status in a formatted table.
---
```

Command body (abridged):

```
## Context
- PR status: !`python3 .claude/scripts/git-pr-status.py $ARGUMENTS`
```

The `$ARGUMENTS` token allows users to pass arbitrary text; the script should extract flags it understands and ignore the rest. This preserves user instructions for Claude while still enabling deterministic script behavior.

Example usage with mixed intent:

```
/git-pr review all --open PRs and --fix failures
/git-pr review latest --open PR and --fix if it is failing
```

In this pattern:
- `--open` is consumed by the Python script.
- `--fix` is interpreted by Claude per the command markdown.
- The surrounding text remains available as natural-language guidance.

### Argument handling pattern (simplified)

```python
args = sys.argv[1:]
raw_args = " ".join(args)
if "--all" in raw_args:
    mode = "all"
elif "--merged" in raw_args:
    mode = "merged"
else:
    mode = "open"

print(f"python3 .claude/scripts/git-pr-status.py '{raw_args}'")
```

Notes:
- Echoing the executed command helps users re-run it manually.
- `string.contains` style matching keeps the script resilient to extra text.

## Error Handling (Hooks + Commands)

### Fail-fast (exit 2)

- Use when the tool should not run at all.
- The slash command stops immediately; no message reaches Anthropic beyond the tool error.
- Best for unsafe or clearly invalid operations.

Example (hook or command validator):

```python
if "--danger" in raw_args:
    print("Illegal argument: --danger. Use --open, --all, or --merged.", file=sys.stderr)
    sys.exit(2)
```

### Soft-fail with guidance (exit 0)

- Use when you want Claude to respond with guidance and possibly retry.
- The tool prints a helpful message and returns success.

Example:

```python
if "--danger" in raw_args:
    print("Illegal argument: --danger. Use --open, --all, or --merged.")
    return
```

Guidelines:
- Use clear, actionable error messages.
- Recommend corrected usage in the error text.
- When blocked by a hook (fail-fast), the user must fix the input and retry.
- When soft-failing, Claude can infer intent and retry with corrected args.

Example error message:
```
Count value too high; must be < 10. Try count=9.
```

## Robust Hook Paths: Avoiding CWD Pitfalls

**Critical Issue:** Relative paths in hooks fail when Claude Code changes the current working directory (CWD) during a session.

### Why This Happens

Hooks execute when subagents enter subdirectories or when the working context shifts. A relative path like `./scripts/validate.py` works if the hook runs from the project root but **fails** if CWD has changed to a subdirectory.

### Recommended: Use Environment Variables

Always use absolute paths via environment variables:

```python
#!/usr/bin/env python3
import os
import subprocess
import sys

# ✅ CORRECT: Use environment variables
project_root = os.getenv("CLAUDE_PROJECT_DIR") or os.getcwd()
hook_script = os.path.join(project_root, ".claude", "scripts", "validate.py")

result = subprocess.run(["python3", hook_script], ...)
```

**Available Environment Variables:**
- `$CLAUDE_PROJECT_DIR` - Project root (where Claude Code was launched)
- `$CLAUDE_PLUGIN_ROOT` - Plugin's root directory (for bundled scripts)
- `$CODEX_PROJECT_DIR` - Codex equivalent (if using Codex)

### Bad Pattern (Relative Paths)

```bash
# ❌ WRONG: Fails if CWD changes
command: "python3 .claude/scripts/validate.py"

# ❌ WRONG: Relative paths are fragile
command: "./scripts/validate.py"
```

### Good Pattern (Absolute Paths)

```bash
# ✅ CORRECT: Uses project root
command: "python3 ${CLAUDE_PROJECT_DIR}/.claude/scripts/validate.py"
```

In Python hooks:
```python
#!/usr/bin/env python3
import os
from pathlib import Path

# Resolve to absolute path using project root
project_dir = Path(os.getenv("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
script = project_dir / ".claude" / "scripts" / "validate.py"

# Use absolute path
subprocess.run(["python3", str(script)], ...)
```

## Environment Variables: Availability by Context

**Critical Finding:** Claude Code environment variables are NOT available in all contexts. Understanding where they work is essential for writing portable code.

### Availability Matrix

| Context Type | CLAUDE_PROJECT_DIR | CLAUDE_PLUGIN_ROOT | Evidence | Fallback Pattern |
|--------------|-------------------|-------------------|----------|------------------|
| **PreToolUse Hook** | ✅ YES | ✅ YES | [test-hook-env-vars.py](../.claude/scripts/tests/test-hook-env-vars.py) | Direct access via `os.getenv()` |
| **PostToolUse Hook** | ✅ YES | ✅ YES | Same as PreToolUse | Direct access via `os.getenv()` |
| **Bash Tool** | ❌ NO | ❌ NO | [test-shell-env-vars.sh](../.claude/scripts/tests/test-shell-env-vars.sh) | Use `Path.cwd()` or pass via args |
| **Background Agent** | ❌ NO | ❌ NO | [test-bg-agent-env-vars.md](../.claude/agents/test-bg-agent-env-vars.md) | Use `get_project_dir()` fallback |
| **Frontmatter Hook** | ❓ UNTESTED | ❓ UNTESTED | Needs testing | Assume NO, use fallback |
| **Named Teammate** | ❓ UNTESTED | ❓ UNTESTED | Needs testing | Assume NO, use fallback |

**Key Insight:** Only **hook contexts** (PreToolUse, PostToolUse) have access to Claude Code environment variables. All other contexts require fallback patterns.

### Recommended Helper Function Pattern

Use this pattern in all package scripts for maximum compatibility:

```python
#!/usr/bin/env python3
import os
from pathlib import Path
from typing import Optional

def _normalize_path(value: Optional[str | Path]) -> Optional[Path]:
    """Normalize path by expanding user and resolving to absolute."""
    if value is None:
        return None
    return Path(value).expanduser().resolve()

def find_project_root(start: Optional[Path] = None) -> Optional[Path]:
    """Find project root by searching upward for marker files/directories.

    Args:
        start: Starting directory (default: Path.cwd())

    Returns:
        Project root Path or None if not found

    Searches upward for:
        - .git directory (git repository)
        - .claude directory (Claude Code project)
        - .sc directory (Synaptic Canvas project)
    """
    current = Path(start or Path.cwd()).resolve()

    # Search upward through parent directories
    for parent in [current, *current.parents]:
        # Check for project markers
        if any([
            (parent / ".git").exists(),
            (parent / ".claude").exists(),
            (parent / ".sc").exists(),
        ]):
            return parent

    return None


def get_project_dir() -> Path:
    """Get project directory with robust fallback chain.

    Returns:
        Project directory Path (never None)

    Fallback order:
        1. CLAUDE_PROJECT_DIR (Claude Code hook context)
        2. CODEX_PROJECT_DIR (Codex compatibility)
        3. Search upward for .git/.claude/.sc markers
        4. Path.cwd() (last resort)

    Note:
        Environment variables are ONLY available in hook contexts.
        Background agents, Bash tool, and teammates use marker search fallback.
    """
    # Try environment variables first (available in hook contexts)
    project_dir = os.getenv("CLAUDE_PROJECT_DIR") or os.getenv("CODEX_PROJECT_DIR")
    if project_dir:
        return _normalize_path(project_dir)

    # Try to find project root by searching for markers
    found_root = find_project_root()
    if found_root:
        return found_root

    # Last resort: current working directory
    return Path.cwd()

def get_plugin_root() -> Path:
    """Get plugin root directory with fallback.

    Returns:
        Plugin root Path (never None)

    Environment Variable:
        - CLAUDE_PLUGIN_ROOT (Claude Code hook context)
        - Fallback: Derive from current file location
    """
    plugin_root = os.getenv("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        return _normalize_path(plugin_root)
    # Fallback: assume we're in packages/<package>/scripts/
    return Path(__file__).parent.parent.parent

# Usage in logging configuration
LOGS_DIR = get_project_dir() / ".claude" / "state" / "logs" / "my-package"
```

### Context-Specific Patterns

#### 1. PreToolUse/PostToolUse Hooks (Variables Available)

```python
#!/usr/bin/env python3
import os
from pathlib import Path

# ✅ Direct access works in hook context
project_dir = Path(os.getenv("CLAUDE_PROJECT_DIR")).resolve()
plugin_root = Path(os.getenv("CLAUDE_PLUGIN_ROOT")).resolve()

# Validate they exist (defensive programming)
if not project_dir:
    raise ValueError("CLAUDE_PROJECT_DIR not set (hook context required)")
```

#### 2. Background Agents & Bash Tool (Variables NOT Available)

```python
#!/usr/bin/env python3
import os
from pathlib import Path

# ❌ These will be None in background agent context
project_dir_raw = os.getenv("CLAUDE_PROJECT_DIR")  # None
plugin_root_raw = os.getenv("CLAUDE_PLUGIN_ROOT")  # None

# ✅ Use fallback pattern
def get_project_dir():
    return Path(os.getenv("CLAUDE_PROJECT_DIR") or os.getcwd())

project_dir = get_project_dir()  # Falls back to Path.cwd()
```

#### 3. Agent Scripts (Unknown Context)

Agent scripts may run in ANY context (hook, background, teammate), so always use fallback:

```python
#!/usr/bin/env python3
from pathlib import Path
import os

# ✅ Works in ALL contexts
def get_project_dir():
    """Get project directory with fallback for all contexts."""
    return Path(os.getenv("CLAUDE_PROJECT_DIR") or
                os.getenv("CODEX_PROJECT_DIR") or
                os.getcwd())

# Use the helper
LOGS_DIR = get_project_dir() / ".claude" / "state" / "logs" / "my-package"
SETTINGS_FILE = get_project_dir() / ".sc" / "my-package" / "settings.yaml"
```

### Testing Environment Variable Availability

To test if env vars are available in a new context:

```python
#!/usr/bin/env python3
import os
import json

def test_env_vars():
    """Capture environment variables for testing."""
    result = {
        "CLAUDE_PROJECT_DIR": os.getenv("CLAUDE_PROJECT_DIR"),
        "CLAUDE_PLUGIN_ROOT": os.getenv("CLAUDE_PLUGIN_ROOT"),
        "CODEX_PROJECT_DIR": os.getenv("CODEX_PROJECT_DIR"),
        "PWD": os.getenv("PWD"),
        "cwd": str(Path.cwd())
    }
    print(json.dumps(result, indent=2))

    # Conclusion
    has_vars = result["CLAUDE_PROJECT_DIR"] or result["CLAUDE_PLUGIN_ROOT"]
    print(f"\nEnvironment variables: {'AVAILABLE' if has_vars else 'NOT AVAILABLE'}")

if __name__ == "__main__":
    test_env_vars()
```

Run this in different contexts:
- ✅ PreToolUse hook: Variables present
- ❌ Bash tool: Variables absent (null)
- ❌ Background agent: Variables absent (null)

### Security Considerations

1. **Never hardcode project paths** - Always use environment variables or fallbacks
2. **Validate paths exist** - Check `path.exists()` before using
3. **Use Path.resolve()** - Convert to absolute paths to avoid CWD issues
4. **Test fallback logic** - Ensure code works when env vars are missing

### Template Integration

The `sc-logging.jenga.py` and `sc-shared.jenga.py` templates include these helper functions by default. When expanding templates:

```python
# templates/sc-logging.jenga.py includes:
def get_project_dir() -> Path:
    """Get project directory with fallback."""
    project_dir = os.getenv("CLAUDE_PROJECT_DIR") or os.getenv("CODEX_PROJECT_DIR")
    return _normalize_path(project_dir) or Path.cwd()

# Used automatically in LOGS_DIR initialization
LOGS_DIR = get_project_dir() / ".claude" / "state" / "logs" / PACKAGE_NAME
```

This ensures all packages using Jenga templates have consistent, portable environment variable handling.

## Gating Agents with PreToolUse Hooks

Use PreToolUse hooks on the **Task** tool to enforce agent constraints at runtime. This pattern is useful for:
- Blocking agents from running in certain contexts (e.g., background execution)
- Enforcing naming conventions (e.g., named teammates only)
- Restricting agent types by directory or permission mode
- Validating preconditions before agent spawn

### Configuration

Define the hook in **`settings.json`** (preferred for project-wide policy):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/scripts/gate-agents.py"
          }
        ]
      }
    ]
  }
}
```

**Alternative locations** (same schema):
- **`~/.claude/settings.json`** - Global user-level policy
- **`.claude/settings.local.json`** - Repository-specific override (for testing)

### Task Tool Input Schema

The PreToolUse hook receives a JSON payload on stdin with the following structure:

```json
{
  "session_id": "8f47703d-9317-4270-a13a-3c2ae3c02670",
  "transcript_path": "/Users/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "PreToolUse",
  "tool_name": "Task",
  "tool_input": {
    "description": "Task description text",
    "prompt": "Full task prompt",
    "subagent_type": "Explore",
    "name": "optional-teammate-name",
    "run_in_background": true,
    "team_name": "optional-team-name"
  },
  "tool_use_id": "toolu_..."
}
```

### Available Fields for Gating Decisions

| Field | Type | Purpose |
|-------|------|---------|
| `tool_input.subagent_type` | string | Agent type (e.g., `"Explore"`, `"rust-developer"`, `"scrum-master"`) |
| `tool_input.name` | string | Named teammate identifier (optional) |
| `tool_input.run_in_background` | boolean | Whether spawned as background agent |
| `tool_input.team_name` | string | Team context (for orchestration) |
| `permission_mode` | string | Execution mode (e.g., `"bypassPermissions"`, `"default"`) |
| `cwd` | string | Current working directory |

### Example: Enforce Named Teammates

Block agents like `scrum-master` from running in background without a name:

```python
#!/usr/bin/env python3
"""Enforce named teammates for certain agent types.

Blocks agents that MUST be launched as named teammates within a team context.
Allows them to run standalone or with a name parameter.

Exit codes:
- 0: Allow
- 2: Block
"""

import json
import sys

# Agent types that MUST be launched as named teammates
GATED_AGENTS = {"scrum-master", "rust-developer"}

def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = data.get("tool_input", {})
    agent_type = tool_input.get("subagent_type", "")
    name = tool_input.get("name", "")
    run_in_background = tool_input.get("run_in_background", False)

    # Only gate if running in background without a name
    if agent_type not in GATED_AGENTS:
        return 0

    if name or not run_in_background:
        # Named teammates or foreground execution allowed
        return 0

    # Block: gated agent in background with no name
    sys.stderr.write(
        f"BLOCKED: '{agent_type}' must be launched as a named teammate.\n"
        f"\n"
        f"Correct (with team and name):\n"
        f'  Task(subagent_type="{agent_type}", name="sm-sprint-1", team_name="dev-team", run_in_background=true)\n'
        f"\n"
        f"Also allowed (standalone):\n"
        f'  Task(subagent_type="{agent_type}")  # foreground, no team needed\n'
        f"\n"
        f"Not allowed:\n"
        f'  Task(subagent_type="{agent_type}", run_in_background=true)  # no name, no team\n'
    )

    return 2


if __name__ == "__main__":
    sys.exit(main())
```

### Use Cases

**1. Prevent sidechain execution:**
```python
# Block spawn without team_name for orchestrator agents
if agent_type == "scrum-master" and not tool_input.get("team_name"):
    return 2
```

**2. Restrict by directory:**
```python
# Allow rust-developer only in /projects/rust-*
if agent_type == "rust-developer":
    cwd = data.get("cwd", "")
    if "/rust-" not in cwd:
        return 2
```

**3. Block from certain permission modes:**
```python
# Dangerous agents only allowed with explicit permissions
if agent_type == "system-admin" and data.get("permission_mode") != "bypassPermissions":
    return 2
```

**4. Log all Task spawns (allow everything):**
```python
# Always allow, but log for audit
log_entry = {
    "timestamp": datetime.now().isoformat(),
    "agent": tool_input.get("subagent_type"),
    "name": tool_input.get("name"),
    "cwd": data.get("cwd")
}
# Write to audit log
return 0
```

### Exit Codes

- **0** = Allow the Task tool call (agent spawn proceeds)
- **2** = Block the Task tool call (agent is not spawned)

## Notes

- Hooks validate tool input/output; they do not change agent responses.
- Always fence JSON in agent inputs and outputs for consistent parsing.
- Prefer Python hooks for portability; avoid shell-specific syntax.
