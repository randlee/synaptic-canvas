#!/usr/bin/env python3
import json
import re
import sys

payload = json.load(sys.stdin)
command = (payload.get("tool_input") or {}).get("command", "")

if "sc_git_diff.py" not in command:
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

has_refs = bool(data.get("base_ref")) and bool(data.get("head_ref"))
has_pr = bool(data.get("pr_url")) or bool(data.get("pr_number"))

if not (has_refs or has_pr):
    print("Provide base_ref/head_ref or pr_url/pr_number", file=sys.stderr)
    sys.exit(2)

if "files_per_agent" in data and not isinstance(data["files_per_agent"], int):
    print("'files_per_agent' must be an int", file=sys.stderr)
    sys.exit(2)

if "max_pairs" in data and not isinstance(data["max_pairs"], int):
    print("'max_pairs' must be an int", file=sys.stderr)
    sys.exit(2)

if "text_output" in data and not isinstance(data["text_output"], (str, bool)):
    print("'text_output' must be a string path or true/false", file=sys.stderr)
    sys.exit(2)

if "git_output" in data and not isinstance(data["git_output"], (str, bool)):
    print("'git_output' must be a string path or true/false", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
