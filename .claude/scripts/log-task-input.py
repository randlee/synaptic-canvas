#!/usr/bin/env python3
"""PreToolUse hook for Task tool that logs the input schema.

Reads the Task tool input from stdin JSON and logs it to a file so we can
inspect the schema and available fields for gating decisions.

Uses structured logging via hooks_logging module (generated from sc-logging template).

Exit codes:
- 0: Always allow (this is a logging hook, not a blocking hook)
"""

import json
import sys

# Import structured logging (generated from Jenga template)
from hooks_logging import log_hook_event


def main() -> int:
    """Log Task tool input using structured logging."""
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        print(f"ERROR: Failed to parse stdin: {e}", file=sys.stderr)
        return 0

    # Log using structured hook event logger
    # Logs to: .claude/state/logs/hooks/pretooluse-task.jsonl
    log_hook_event(
        event="PreToolUse-Task",
        hook_data=data,
        decision={"allowed": True, "reason": "Logging hook - always allow"}
    )

    print(f"✓ Logged Task input (structured logging)", file=sys.stderr)

    # Always allow
    return 0


if __name__ == "__main__":
    sys.exit(main())
