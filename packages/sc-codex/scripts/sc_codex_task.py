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

from pydantic import ValidationError  # noqa: E402

from ai_cli.task_runner import (  # noqa: E402
    EFFORTS,
    ModelError,
    effort_help,
    model_help,
    prepare_payload,
    resolve_runner,
    run_task,
)


def _load_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception as exc:
        raise SystemExit(f"Invalid JSON: {exc}") from exc


def _build_payload(prompt: str, subagent_type: str) -> dict:
    return {
        "description": "Codex task",
        "prompt": prompt,
        "subagent_type": subagent_type,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Codex tasks via ai_cli", add_help=True)
    ap.add_argument("--model", help=model_help("codex"))
    ap.add_argument("--effort", choices=EFFORTS, help=effort_help("codex"))
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
    else:
        data = _build_payload(raw, "sc-codex")

    runner = resolve_runner("codex")
    try:
        # CLI flags override payload fields; model and effort are validated before launch.
        payload, model = prepare_payload(data, runner, args.model, args.effort)
    except ValidationError as exc:
        raise SystemExit(f"Invalid Task Tool input: {exc}") from exc
    except ModelError as exc:
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
