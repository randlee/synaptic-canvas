# Agent Tool Use Best Practices

This guide captures learned patterns for using fenced JSON, tool calls, and PreToolUse hooks to validate and gate agent behavior.

## Key Principles

- Use fenced JSON for all agent inputs and outputs.
- Validate inputs early (PreToolUse hooks) before a tool runs.
- Use Python hooks for cross-platform compatibility.
- Prefer schema validation (pydantic) over ad-hoc parsing.
- Keep tool outputs machine-readable; avoid mixed prose + JSON.

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

## Command Example With Hooks

This example shows a command that runs `git pull` and only asks for help if a merge conflict occurs.

```yaml
---
name: sc-git-pull
version: 0.1.0
description: Pull latest changes and report merge conflicts.
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/validate_git_pull.py"
---
```

```markdown
# /sc-git-pull

1) Run: `git pull`
2) If success: respond with a short confirmation and no further action.
3) If conflicts: list conflicted files and propose resolution steps.
```

### Example validator (optional)

```python
#!/usr/bin/env python3
import json
import sys

payload = json.load(sys.stdin)
command = (payload.get("tool_input") or {}).get("command", "")

if command.strip() != "git pull":
    print("This command only allows 'git pull'", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
```

## Notes

- Hooks validate tool input/output; they do not change agent responses.
- Always fence JSON in agent inputs and outputs for consistent parsing.
- Prefer Python hooks for portability; avoid shell-specific syntax.
