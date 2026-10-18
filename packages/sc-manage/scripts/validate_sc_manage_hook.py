#!/usr/bin/env python3
import json
import re
import sys

from sc_manage_common import selected_targets

payload = json.load(sys.stdin)
command = (payload.get("tool_input") or {}).get("command", "")

if "sc_manage_" not in command:
    sys.exit(0)

match = re.search(r"\{.*\}", command, re.DOTALL)
if not match:
    print("Expected JSON payload in command", file=sys.stderr)
    sys.exit(2)

try:
    data = json.loads(match.group(0))
except Exception:
    print("Invalid JSON payload in command", file=sys.stderr)
    sys.exit(2)

if "sc_manage_install.py" in command or "sc_manage_uninstall.py" in command:
    if not isinstance(data.get("package"), str):
        print("Missing 'package' string", file=sys.stderr)
        sys.exit(2)
    if data.get("scope") not in {"local", "project", "global", "user"}:
        print("Missing or invalid 'scope' (local|project|global|user)", file=sys.stderr)
        sys.exit(2)

if any(script in command for script in ("sc_manage_install.py", "sc_manage_uninstall.py", "sc_manage_list.py")):
    try:
        selected_targets(data)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

if "sc_manage_docs.py" in command:
    if not isinstance(data.get("package"), str):
        print("Missing 'package' string", file=sys.stderr)
        sys.exit(2)

sys.exit(0)
