#!/usr/bin/env python3
"""
Agent Runner CLI

Usage examples:
  python3 tools/agent-runner.py validate --agent sc-worktree-create
  python3 tools/agent-runner.py invoke --agent sc-worktree-create \
      --param branch=feature-x --param base=main --timeout 120

This CLI does not launch Claude's Task tool. It validates and prepares a
"task_prompt" for the skill to pass to the Task tool. It also writes a
redacted audit record.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict

# Allow `python3 tools/agent-runner.py` to import local package
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from agent_runner.runner import (
    REGISTRY_DEFAULT,
    invoke as runner_invoke,
    validate_only as runner_validate,
)


def parse_params(values) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise SystemExit(f"Invalid --param '{item}', expected key=value")
        k, v = item.split("=", 1)
        out[k] = v
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Agent Runner CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate agent path/version against registry")
    p_val.add_argument("--agent", required=True, help="Agent name (as in registry)")
    p_val.add_argument("--registry", default=REGISTRY_DEFAULT, help="Path to registry.yaml")

    p_inv = sub.add_parser("invoke", help="Prepare Task tool prompt and write audit")
    p_inv.add_argument("--agent", required=True, help="Agent name (as in registry)")
    p_inv.add_argument("--registry", default=REGISTRY_DEFAULT, help="Path to registry.yaml")
    p_inv.add_argument("--param", action="append", default=[], help="key=value (repeatable)")
    p_inv.add_argument("--timeout", type=int, default=120, help="Per-task timeout in seconds")

    args = ap.parse_args()

    try:
        if args.cmd == "validate":
            res = runner_validate(agent_name=args.agent, registry_path=args.registry)
            print(json.dumps(res, indent=2))
            return 0
        elif args.cmd == "invoke":
            params = parse_params(args.param)
            res = runner_invoke(agent_name=args.agent, params=params, registry_path=args.registry, timeout_s=args.timeout)
            print(json.dumps(res, indent=2))
            return 0
        else:
            ap.error("Unknown command")
    except Exception as e:
        err = {"ok": False, "error": str(e)}
        print(json.dumps(err, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
