#!/usr/bin/env python3
"""Background launch runtime for Claude, Codex, and Gemini."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from launchpad_shared import build_child_env, resolve_teammate_mode


ToolName = Literal["claude", "codex", "gemini"]
ClaudeModel = Literal["sonnet", "haiku", "opus"]
CodexModel = Literal[
    "codex",
    "codex-max",
    "max",
    "codex-mini",
    "mini",
    "gpt-5",
    "gpt-5.2-codex",
    "gpt-5.1-codex-max",
    "gpt-5.1-codex-mini",
    "gpt-5.2",
]

CODEX_MODEL_MAP = {
    "codex": "gpt-5.2-codex",
    "gpt-5.2-codex": "gpt-5.2-codex",
    "codex-max": "gpt-5.1-codex-max",
    "max": "gpt-5.1-codex-max",
    "gpt-5.1-codex-max": "gpt-5.1-codex-max",
    "codex-mini": "gpt-5.1-codex-mini",
    "mini": "gpt-5.1-codex-mini",
    "gpt-5.1-codex-mini": "gpt-5.1-codex-mini",
    "gpt-5": "gpt-5.2",
    "gpt-5.2": "gpt-5.2",
}

CLAUDE_MODEL_MAP = {
    "sonnet": "sonnet",
    "haiku": "haiku",
    "opus": "opus",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5": "haiku",
    "claude-opus-4-1": "opus",
}


class LaunchpadInput(BaseModel):
    description: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    tool: ToolName
    model: str | None = None
    cwd: str = Field(min_length=1)
    atm_identity: str | None = None
    extra_args: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


LaunchpadInput.model_rebuild()


class LaunchpadError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        recoverable: bool = True,
        suggested_action: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.recoverable = recoverable
        self.suggested_action = suggested_action


def success_response(data: dict) -> dict:
    return {"success": True, "data": data, "error": None}


def error_response(error: LaunchpadError, data: dict | None = None) -> dict:
    return {
        "success": False,
        "data": data,
        "error": {
            "code": error.code,
            "message": error.message,
            "recoverable": error.recoverable,
            "suggested_action": error.suggested_action,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Treat remaining args as JSON payload")
    parser.add_argument("args", nargs="*", help="JSON payload")
    return parser.parse_args()


def load_payload(raw: str) -> LaunchpadInput:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LaunchpadError(
            "VALIDATION.INVALID_JSON",
            f"Invalid JSON payload: {exc}",
            suggested_action="Pass one valid JSON object to --json.",
        ) from exc
    try:
        return LaunchpadInput.model_validate(data)
    except ValidationError as exc:
        raise LaunchpadError(
            "VALIDATION.INVALID_PAYLOAD",
            f"Invalid launch payload: {exc}",
            suggested_action="Provide required fields: description, prompt, tool, and cwd.",
        ) from exc


def resolve_cwd(cwd: str) -> Path:
    path = Path(cwd).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise LaunchpadError(
            "VALIDATION.INVALID_CWD",
            f"Working directory does not exist: {path}",
            suggested_action="Pass an existing directory in the `cwd` field.",
        )
    return path


def normalize_tool_model(payload: LaunchpadInput) -> str | None:
    if payload.tool == "claude":
        if payload.model is None:
            return "sonnet"
        normalized = CLAUDE_MODEL_MAP.get(payload.model)
        if normalized is None:
            raise LaunchpadError(
                "VALIDATION.INVALID_MODEL",
                f"Unsupported Claude model: {payload.model}",
                suggested_action="Use one of: sonnet, haiku, opus.",
            )
        return normalized
    if payload.tool == "codex":
        if payload.model is None:
            return "gpt-5.2-codex"
        normalized = CODEX_MODEL_MAP.get(payload.model)
        if normalized is None:
            raise LaunchpadError(
                "VALIDATION.INVALID_MODEL",
                f"Unsupported Codex model: {payload.model}",
                suggested_action="Use codex, max, mini, gpt-5, or a known Codex model alias.",
            )
        return normalized
    return payload.model


def roster_model(payload: LaunchpadInput, normalized_model: str | None) -> str:
    if payload.tool == "claude":
        return normalized_model or "sonnet"
    return payload.tool


def ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        raise LaunchpadError(
            "CLI.NOT_FOUND",
            f"Required CLI is not available on PATH: {name}",
            suggested_action=f"Install `{name}` or adjust PATH before launching.",
        )


def maybe_add_member(
    parent_env: dict[str, str],
    teammate_mode: bool,
    team: str | None,
    identity: str | None,
    payload: LaunchpadInput,
    normalized_model: str | None,
    cwd: Path,
) -> None:
    if not teammate_mode:
        return
    ensure_command("atm")
    command = [
        "atm",
        "teams",
        "add-member",
        team or "",
        identity or "",
        "--model",
        roster_model(payload, normalized_model),
        "--cwd",
        str(cwd),
    ]
    # TODO: When pane-aware launchpad mode exists, append `--pane-id <pane-id>` here.
    result = subprocess.run(command, text=True, capture_output=True, env=parent_env)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "atm teams add-member failed"
        raise LaunchpadError(
            "ATM.ADD_MEMBER_FAILED",
            message,
            suggested_action="Ensure the team exists and the identity can be added before retrying.",
        )


def build_command(payload: LaunchpadInput, normalized_model: str | None) -> list[str]:
    extra = list(payload.extra_args)
    if payload.tool == "claude":
        command = ["claude", "--dangerously-skip-permissions", "--print"]
        if normalized_model:
            command.extend(["--model", normalized_model])
        command.extend(extra)
        command.append(payload.prompt)
        return command
    if payload.tool == "codex":
        command = ["codex", "exec", "--full-auto"]
        if normalized_model:
            command.extend(["--model", normalized_model])
        command.extend(extra)
        command.append(payload.prompt)
        return command
    command = ["gemini", "--yolo", "--prompt", payload.prompt]
    if normalized_model:
        command.extend(["--model", normalized_model])
    command.extend(extra)
    return command


def run_payload(payload: LaunchpadInput, parent_env: dict[str, str]) -> dict:
    cwd = resolve_cwd(payload.cwd)
    ensure_command(payload.tool)
    normalized_model = normalize_tool_model(payload)
    teammate_mode, team, identity = resolve_teammate_mode(parent_env, payload.atm_identity)
    maybe_add_member(parent_env, teammate_mode, team, identity, payload, normalized_model, cwd)
    child_env = build_child_env(parent_env, teammate_mode, team, identity)
    command = build_command(payload, normalized_model)
    result = subprocess.run(
        command,
        cwd=str(cwd),
        env=child_env,
        text=True,
        capture_output=True,
    )
    data = {
        "tool": payload.tool,
        "model": normalized_model,
        "cwd": str(cwd),
        "teammate_mode": teammate_mode,
        "atm_team": team,
        "atm_identity": identity,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if result.returncode == 0:
        return success_response(data)
    return error_response(
        LaunchpadError(
            "CLI.NON_ZERO_EXIT",
            f"{payload.tool} exited with code {result.returncode}",
            suggested_action="Inspect stdout/stderr in the returned payload and retry with adjusted prompt or args.",
        ),
        data,
    )


def main() -> int:
    args = parse_args()
    raw = " ".join(args.args).strip()
    if not raw:
        print(
            json.dumps(
                error_response(
                    LaunchpadError(
                        "VALIDATION.MISSING_INPUT",
                        "No launch payload was provided.",
                        suggested_action="Pass a JSON object with --json.",
                    )
                ),
                indent=2,
            )
        )
        return 0

    try:
        payload = load_payload(raw)
        response = run_payload(payload, dict(os.environ))
    except LaunchpadError as exc:
        response = error_response(exc)
    except Exception as exc:  # pragma: no cover - safety net
        response = error_response(
            LaunchpadError(
                "RUNTIME.UNEXPECTED",
                str(exc),
                recoverable=False,
            )
        )

    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
