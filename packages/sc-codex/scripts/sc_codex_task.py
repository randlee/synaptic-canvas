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

from ai_cli.task_runner import (  # noqa: E402
    REASONING_EFFORTS,
    codex_model_help,
    effort_help,
    resolve_model,
    resolve_reasoning_effort,
    resolve_runner,
    run_task,
)
from ai_cli.task_tool import TaskToolInput  # noqa: E402
from pydantic import ValidationError  # noqa: E402


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
    ap.add_argument("--model", help=codex_model_help())
    ap.add_argument("--effort", choices=REASONING_EFFORTS, help=effort_help())
    bg_group = ap.add_mutually_exclusive_group()
    bg_group.add_argument("--background", dest="background", action="store_true", help="Run in background mode")
    bg_group.add_argument("--no-background", dest="background", action="store_false", help="Run in blocking mode")
    ap.set_defaults(background=None)
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
        try:
            payload = TaskToolInput.model_validate(data)
        except ValidationError as exc:
            raise SystemExit(f"Invalid Task Tool input: {exc}") from exc
    else:
        payload = _build_payload(raw, "sc-codex")

    if args.effort:
        payload = payload.model_copy(update={"reasoning_effort": args.effort})

    runner = resolve_runner("codex")
    try:
        model = resolve_model(runner, args.model or payload.model)
        resolve_reasoning_effort(model, payload.reasoning_effort)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.background is None:
        run_in_background = True if payload.run_in_background is None else bool(payload.run_in_background)
    else:
        run_in_background = args.background
    result = run_task(
        payload,
        runner=runner,
        model=model,
        run_in_background=run_in_background,
        raise_on_error=False,
    )
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
