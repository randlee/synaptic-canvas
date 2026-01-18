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

## Slash Commands vs Agents

**Agents:** Hooks in frontmatter are supported and can validate tool calls before they run.

**Slash commands:** Frontmatter hooks are **not** supported. Use `!` pre-exec lines in the command body to run scripts before the model prompt, and `allowed-tools` to permit those commands.

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

## Notes

- Hooks validate tool input/output; they do not change agent responses.
- Always fence JSON in agent inputs and outputs for consistent parsing.
- Prefer Python hooks for portability; avoid shell-specific syntax.
