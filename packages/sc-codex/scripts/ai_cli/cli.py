#!/usr/bin/env python3
"""CLI helpers for ai_cli tooling."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import ValidationError as SchemaValidationError
from jsonschema import validate as validate_schema

from ai_cli.logging import write_log
from ai_cli.task_runner import (
    run_background_child_with_payload,
    resolve_runner,
    run_task,
    resolve_model,
)
from ai_cli.task_tool import TaskToolInput, task_tool_input_schema


def _read_json(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("Expected JSON input on stdin or via --file")
    return json.loads(raw)


def cmd_schema(_: argparse.Namespace) -> int:
    print(json.dumps(task_tool_input_schema(), indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    data = _read_json(args.file)
    TaskToolInput.model_validate(data)
    print("OK")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    data = _read_json(args.file)
    payload = TaskToolInput.model_validate(data)
    runner = resolve_runner(args.runner)
    model = resolve_model(runner, args.model or payload.model)
    if args.background is None:
        run_in_background = bool(payload.run_in_background)
    else:
        run_in_background = args.background
    output = run_task(
        payload,
        runner=runner,
        model=model,
        run_in_background=run_in_background,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    output_dict = output.model_dump()
    schema_path = Path(__file__).resolve().parent / "task_tool.output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        validate_schema(instance=output_dict, schema=schema)
    except SchemaValidationError as exc:
        err = {
            "error": "OUTPUT_SCHEMA_INVALID",
            "message": "Task Tool output failed schema validation",
            "details": exc.message,
        }
        write_log(
            {
                "component": "ai_cli",
                "event": "output_schema_invalid",
                "runner": runner,
                "model": model,
                "agentId": output_dict.get("agentId"),
                "error": err,
            }
        )
        print(json.dumps(err, indent=2), file=sys.stderr)
        print(json.dumps(output_dict, indent=2))
        return 2
    else:
        print(json.dumps(output_dict, indent=2))
        return 0


def cmd_run_child(args: argparse.Namespace) -> int:
    data = _read_json(args.input_file)
    payload = TaskToolInput.model_validate(data)
    runner = resolve_runner(args.runner)
    model = resolve_model(runner, args.model or payload.model)
    run_background_child_with_payload(
        payload=payload,
        runner=runner,
        model=model,
        output_file=Path(args.output_file),
        agent_id=args.agent_id,
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="ai_cli tooling")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_schema = sub.add_parser("schema", help="Print Task Tool input JSON schema")
    p_schema.set_defaults(func=cmd_schema)

    p_validate = sub.add_parser("validate", help="Validate Task Tool input JSON")
    p_validate.add_argument("--file", help="Path to JSON file (defaults to stdin)")
    p_validate.set_defaults(func=cmd_validate)

    p_run = sub.add_parser("run", help="Execute Task Tool request via CLI runner")
    p_run.add_argument("--file", help="Path to JSON file (defaults to stdin)")
    p_run.add_argument("--runner", choices=["claude", "codex"], help="Override runner selection")
    p_run.add_argument("--model", help="Override model (default derived from runner or input)")
    bg_group = p_run.add_mutually_exclusive_group()
    bg_group.add_argument("--background", dest="background", action="store_true", help="Force background mode")
    bg_group.add_argument("--no-background", dest="background", action="store_false", help="Force blocking mode")
    p_run.set_defaults(background=None)
    p_run.add_argument("--output-dir", help="Override output directory for background runs")
    p_run.set_defaults(func=cmd_run)

    p_child = sub.add_parser("run-child", help=argparse.SUPPRESS)
    p_child.add_argument("--input-file", required=True, help=argparse.SUPPRESS)
    p_child.add_argument("--runner", choices=["claude", "codex"], help=argparse.SUPPRESS)
    p_child.add_argument("--model", required=True, help=argparse.SUPPRESS)
    p_child.add_argument("--agent-id", required=True, help=argparse.SUPPRESS)
    p_child.add_argument("--output-file", required=True, help=argparse.SUPPRESS)
    p_child.set_defaults(func=cmd_run_child)

    args = ap.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        write_log(
            {
                "component": "ai_cli",
                "event": "cli_exception",
                "error": str(exc),
            }
        )
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
