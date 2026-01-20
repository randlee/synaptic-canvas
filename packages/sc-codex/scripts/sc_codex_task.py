#!/usr/bin/env python3
"""Slash command entry point for /sc-codex."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ai_cli.task_runner import resolve_model, resolve_runner, run_task  # noqa: E402
from ai_cli.task_tool import TaskToolInput  # noqa: E402


def _load_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception as exc:
        raise SystemExit(f"Invalid JSON: {exc}") from exc


def _build_payload(prompt: str, subagent_type: str) -> TaskToolInput:
    return TaskToolInput(
        description="Codex task",
        prompt=prompt,
        subagent_type=subagent_type,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Codex tasks via ai_cli", add_help=True)
    ap.add_argument("--model", help="Codex model or alias (codex, max, mini, gpt-5)")
    ap.add_argument("--background", action="store_true", help="Run in background mode")
    ap.add_argument("--json", action="store_true", help="Treat remaining args as JSON Task Tool input")
    ap.add_argument("args", nargs="*", help="Prompt or JSON input")
    args = ap.parse_args()

    raw = " ".join(args.args).strip()
    if not raw:
        ap.print_help()
        return 1

    if args.json or raw.startswith("{"):
        data = _load_json(raw)
        if "subagent_type" not in data:
            data["subagent_type"] = "sc-codex"
        payload = TaskToolInput.model_validate(data)
    else:
        payload = _build_payload(raw, "sc-codex")

    runner = resolve_runner("codex")
    model = resolve_model(runner, args.model or payload.model)
    result = run_task(
        payload,
        runner=runner,
        model=model,
        run_in_background=args.background or bool(payload.run_in_background),
        raise_on_error=False,
    )
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
