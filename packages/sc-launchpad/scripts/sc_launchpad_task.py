#!/usr/bin/env python3
"""Background launch runtime for Claude, Codex, and Gemini.

Invocation (agent path or direct subprocess)::

    python3 sc_launchpad_task.py --json '<payload JSON>'
    python3 sc_launchpad_task.py --json - < payload.json

The runtime always prints exactly one JSON envelope on stdout and exits 0;
callers must branch on ``success`` (see README "Direct script invocation").
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from launchpad_commands import (  # noqa: E402
    build_command,
    check_batch_shim,
    claude_project_dir,
    codex_private_home,
    create_temp_cwd,
    is_launchpad_temp,
    isolation_flags,
)
from launchpad_models import LaunchFailure, LaunchpadInput, normalize_tool_model, roster_model  # noqa: E402
from launchpad_output import classify, tail  # noqa: E402
from launchpad_process import run_process  # noqa: E402
from launchpad_shared import build_child_env, resolve_teammate_mode  # noqa: E402


def envelope(data: Optional[dict], failure: Optional[LaunchFailure] = None) -> dict:
    return {
        "success": failure is None,
        "data": data,
        "error": failure.to_error() if failure else None,
    }


def load_payload(raw: str) -> LaunchpadInput:
    try:
        return LaunchpadInput.model_validate(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise LaunchFailure(
            "VALIDATION.INVALID_JSON",
            f"Invalid JSON payload: {exc}",
            "Pass one valid JSON object to --json.",
        )
    except ValidationError as exc:
        raise LaunchFailure(
            "VALIDATION.INVALID_PAYLOAD",
            f"Invalid launch payload: {exc}",
            "Provide description, prompt, tool, and cwd (unless isolation.cwd='temp'); "
            "use only documented optional fields.",
        )


def check_capabilities(payload: LaunchpadInput) -> None:
    if payload.tool != "gemini":
        return
    requested = [
        name
        for name, present in (
            ("output_format='json'", payload.output_format == "json"),
            ("resume_session_id", payload.resume_session_id is not None),
            ("isolation", payload.isolation is not None),
            ("ephemeral", payload.ephemeral),
            ("effort", payload.effort is not None),
        )
        if present
    ]
    if requested:
        raise LaunchFailure(
            "CAPABILITY.UNSUPPORTED",
            "gemini does not support " + ", ".join(requested) + " in sc-launchpad",
            "Use tool 'claude' or 'codex' for session ids, resume, isolation, "
            "ephemeral sessions, and effort, or launch gemini in text mode without these fields.",
            recoverable=False,
            details={"tool": "gemini", "unsupported_fields": requested},
        )


def which(name: str, env: Dict[str, str]) -> str:
    found = shutil.which(name, path=env.get("PATH", ""))
    if found is None:
        raise LaunchFailure(
            "CLI.NOT_FOUND",
            f"Required CLI is not available on PATH: {name}",
            f"Install `{name}` or adjust PATH before launching.",
            details={"cli": name, "searched_path": [d for d in env.get("PATH", "").split(os.pathsep) if d]},
        )
    return found


def resolve_given_cwd(cwd: str) -> Path:
    path = Path(cwd).expanduser().resolve()
    if not path.is_dir():
        raise LaunchFailure(
            "VALIDATION.INVALID_CWD",
            f"Working directory does not exist: {path}",
            "Pass an existing directory in the `cwd` field.",
        )
    return path


def add_team_member(env: Dict[str, str], team: str, identity: str, model: str, cwd: Path) -> None:
    # TODO: When pane-aware launchpad mode exists, append `--pane-id <pane-id>`.
    command = [which("atm", env), "teams", "add-member", team, identity, "--model", model, "--cwd", str(cwd)]
    result = subprocess.run(command, text=True, capture_output=True, env=env, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise LaunchFailure(
            "ATM.ADD_MEMBER_FAILED",
            result.stderr.strip() or result.stdout.strip() or "atm teams add-member failed",
            "Ensure the team exists and the identity can be added before retrying.",
            details={"stderr_tail": tail(result.stderr)},
        )


def audit(env: Dict[str, str], payload: LaunchpadInput, response: dict, started: float) -> None:
    """Append one line per launch to the package log; never the prompt, never fatal."""
    data, error = response.get("data") or {}, response.get("error") or {}
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "launch",
        "package": "sc-launchpad",
        "level": "info" if response["success"] else "error",
        "tool": payload.tool,
        "model": data.get("model", payload.model),
        "effort": payload.effort,
        "output_format": "json" if payload.structured else "text",
        "isolation": payload.isolation.model_dump() if payload.isolation else None,
        "ephemeral": payload.ephemeral,
        "session_id": data.get("session_id"),
        "resumed_session_id": payload.resume_session_id,
        "exit_code": data.get("exit_code"),
        "error_code": error.get("code"),
        "duration_seconds": round(time.monotonic() - started, 3),
    }
    root = Path(env.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    log = root / ".claude" / "state" / "logs" / "sc-launchpad" / "launch.jsonl"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    except OSError:
        pass


def run_payload(payload: LaunchpadInput, parent_env: Dict[str, str]) -> dict:
    check_capabilities(payload)
    model = normalize_tool_model(payload)
    given_cwd = None if payload.temp_cwd else resolve_given_cwd(payload.cwd or "")
    command = build_command(payload, model)
    executable = which(payload.tool, parent_env)
    check_batch_shim(executable, [executable] + command.argv[1:])
    teammate_mode, team, identity = resolve_teammate_mode(parent_env, payload.atm_identity)

    cwd = given_cwd or create_temp_cwd()
    # Paths this launch's sessions leave behind; the caller deletes them after the last turn.
    cleanup_paths: List[Path] = [cwd] if is_launchpad_temp(cwd) else []
    child_started = False
    try:
        if teammate_mode:
            add_team_member(parent_env, team or "", identity or "", roster_model(payload, model), cwd)
        env = build_child_env(parent_env, teammate_mode, team, identity)
        if payload.tool == "codex" and payload.no_tools:
            env["CODEX_HOME"] = str(codex_private_home(cwd, parent_env))
            cleanup_paths.append(Path(env["CODEX_HOME"]))
        child_started = True
        outcome = run_process(
            [executable] + command.argv[1:], cwd, env, payload.timeout_seconds, command.stdin
        )
    except LaunchFailure as failure:
        if failure.code == "RUNTIME.INTERRUPTED":
            child_started = failure.details.get("child_started", False)
        if payload.temp_cwd and not child_started:
            # Nothing ran and nothing was reported: leave no trace.
            for path in cleanup_paths:
                shutil.rmtree(path, ignore_errors=True)
            raise
        failure.details.setdefault("cleanup_paths", [str(p) for p in cleanup_paths])
        raise

    if payload.tool == "claude" and is_launchpad_temp(cwd):
        transcripts = claude_project_dir(cwd, parent_env)
        if transcripts.exists():
            cleanup_paths.append(transcripts)
    data: Dict[str, Any] = {
        "tool": payload.tool,
        "model": model,
        "effort": payload.effort,
        "cwd": str(cwd),
        "cleanup_paths": [str(p) for p in cleanup_paths],
        "teammate_mode": teammate_mode,
        "atm_team": team,
        "atm_identity": identity,
        "output_format": "json" if payload.structured else "text",
        "isolation": (
            dict(payload.isolation.model_dump(), flags=isolation_flags(payload))
            if payload.isolation
            else None
        ),
        "ephemeral": payload.ephemeral,
        "exit_code": outcome.exit_code,
        # Structured runs carry the answer in result_text; raw output only in error details.
        "stdout": None if payload.structured else outcome.stdout,
        "stderr": tail(outcome.stderr) if payload.structured else outcome.stderr,
        "session_id": None,
        "result_text": None,
        "resumed_session_id": payload.resume_session_id,
        "timeout_seconds": payload.timeout_seconds,
        "timed_out": outcome.timed_out,
        "duration_seconds": outcome.duration_seconds,
        "warnings": [],
    }

    if not payload.structured:
        if outcome.timed_out or outcome.exit_code != 0:
            failure = LaunchFailure(
                "CLI.TIMEOUT" if outcome.timed_out else "CLI.NON_ZERO_EXIT",
                f"{payload.tool} did not finish within {payload.timeout_seconds}s and was killed"
                if outcome.timed_out
                else f"{payload.tool} exited with code {outcome.exit_code}",
                "Increase timeout_seconds or shorten the prompt."
                if outcome.timed_out
                else "Inspect data.stdout/data.stderr and retry with an adjusted prompt or args.",
                details={"stderr_tail": tail(outcome.stderr), "exit_code": outcome.exit_code},
            )
            return envelope(data, failure)
        return envelope(data)

    try:
        parsed, warnings = classify(payload, outcome)
    except LaunchFailure as failure:
        data["session_id"] = failure.details.get("session_id")
        return envelope(data, failure)
    data.update(session_id=parsed.session_id, result_text=parsed.result_text, warnings=warnings)
    return envelope(data)


def read_raw_payload(args: List[str]) -> str:
    raw = " ".join(args).strip()
    if raw == "-":
        # JSON is UTF-8 (RFC 8259); `utf-8-sig` drops a PowerShell BOM.
        return sys.stdin.buffer.read().decode("utf-8-sig", errors="replace").strip()
    return raw


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Treat remaining args as the JSON payload ('-' reads stdin)")
    parser.add_argument("args", nargs="*", help="JSON payload")
    raw = read_raw_payload(parser.parse_args(argv).args)
    started = time.monotonic()
    env = dict(os.environ)
    payload = None
    try:
        if not raw:
            raise LaunchFailure(
                "VALIDATION.MISSING_INPUT",
                "No launch payload was provided.",
                "Pass a JSON object with --json (or `--json -` to read stdin).",
            )
        payload = load_payload(raw)
        response = run_payload(payload, env)
    except LaunchFailure as failure:
        response = envelope(None, failure)
    except Exception as exc:  # pragma: no cover - safety net keeps the one-envelope contract
        response = envelope(None, LaunchFailure("RUNTIME.UNEXPECTED", str(exc), recoverable=False))
    if payload is not None:
        audit(env, payload, response, started)
    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
