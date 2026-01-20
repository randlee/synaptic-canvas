"""
Task Tool runner for Claude/Codex CLI.

This is a lightweight, human-friendly wrapper that:
- Validates Task Tool input payloads (pydantic)
- Executes claude --print or codex exec
- Returns Task Tool-compatible JSON output
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import yaml

from ai_cli.logging import write_log
from ai_cli.task_tool import TaskToolInput, TaskToolOutputBackground, TaskToolOutputForeground

RunnerType = Literal["claude", "codex"]

_CODEX_MODEL_MAP = {
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
    "gtp-5": "gpt-5.2",
}

_CLAUDE_MODELS = {"haiku", "sonnet", "opus"}


@lru_cache(maxsize=None)
def _check_runner_available(runner: RunnerType) -> str:
    binary = "codex" if runner == "codex" else "claude"
    if shutil.which(binary) is None:
        raise FileNotFoundError(f"{binary} not found on PATH")
    res = subprocess.run([binary, "--version"], text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or f"{binary} --version failed")
    return res.stdout.strip() or res.stderr.strip()


def resolve_runner(preferred: Optional[str]) -> RunnerType:
    if preferred in ("claude", "codex"):
        _check_runner_available(preferred)
        return preferred
    try:
        _check_runner_available("claude")
        return "claude"
    except Exception:
        _check_runner_available("codex")
        return "codex"


def resolve_model(runner: RunnerType, model: Optional[str]) -> str:
    if runner == "claude":
        if model is None:
            return "sonnet"
        if model not in _CLAUDE_MODELS:
            raise ValueError(f"Unsupported Claude model: {model}")
        return model
    if model is None:
        return "gpt-5.2-codex"
    resolved = _CODEX_MODEL_MAP.get(model)
    if resolved is None:
        raise ValueError(f"Unsupported Codex model: {model}")
    return resolved


def build_prompt(payload: TaskToolInput) -> str:
    return "\n".join(
        [
            f"You are a specialized agent of type '{payload.subagent_type}'.",
            f"Description: {payload.description}",
            f"Task: {payload.prompt}",
            "",
            "Return your result as plain text.",
        ]
    )


def _preview(text: str, limit: int = 200) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def run_sync(runner: RunnerType, model: str, prompt: str) -> str:
    _check_runner_available(runner)
    if runner == "codex":
        cmd = ["codex", "exec", "--model", model, prompt]
    else:
        cmd = ["claude", "--model", model, "--print", prompt]
    res = subprocess.run(cmd, text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or f"{runner} exited with code {res.returncode}")
    return res.stdout.strip()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_branch() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def _jsonl_entry(agent_id: str, role: str, content: str, parent_uuid: Optional[str]) -> dict:
    entry_uuid = str(uuid.uuid4())
    return {
        "parentUuid": parent_uuid,
        "isSidechain": False,
        "userType": "user",
        "cwd": os.getcwd(),
        "sessionId": agent_id,
        "version": "ai_cli-0.1",
        "gitBranch": _git_branch(),
        "agentId": agent_id,
        "type": role,
        "message": {"role": role, "content": content},
        "uuid": entry_uuid,
        "timestamp": _timestamp(),
        "slug": "final" if role == "assistant" else "",
        "requestId": entry_uuid if role == "assistant" else "",
    }


def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _default_output_dir(runner: RunnerType) -> Path:
    if runner == "codex":
        codex_home = os.environ.get("CODEX_HOME")
        if codex_home:
            return Path(codex_home) / "sessions"
    return Path.cwd() / ".sc" / "sessions"


def resolve_agent_path(subagent_type: str, runner: RunnerType) -> Optional[Path]:
    candidate = Path(subagent_type).expanduser()
    if candidate.is_file():
        return candidate.resolve()
    name = Path(subagent_type).name
    if not name.endswith(".md"):
        name = f"{name}.md"
    current = Path.cwd().resolve()
    for parent in [current, *current.parents]:
        path = parent / ".claude" / "agents" / name
        if path.is_file():
            return path.resolve()
    home_path = Path.home() / ".claude" / "agents" / name
    if home_path.is_file():
        return home_path.resolve()
    if runner == "codex":
        raise FileNotFoundError(f"Agent not found for '{subagent_type}'")
    return None


def _extract_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    lines = text.splitlines()
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "\n".join(lines[1:idx])
    return ""


def run_pretool_hooks(agent_path: Optional[Path], payload: TaskToolInput) -> None:
    if agent_path is None:
        return
    text = agent_path.read_text(encoding="utf-8")
    fm_text = _extract_frontmatter(text)
    if not fm_text:
        return
    meta = yaml.safe_load(fm_text) or {}
    hooks = (meta.get("hooks") or {}).get("PreToolUse") or []
    if not hooks:
        return
    hook_payload = {
        "event": "PreToolUse",
        "tool": "Bash",
        "tool_input": {"command": payload.model_dump_json()},
        "cwd": str(Path.cwd()),
    }
    for entry in hooks:
        for hook in entry.get("hooks") or []:
            if hook.get("type") != "command":
                continue
            command = hook.get("command")
            if not command:
                continue
            write_log(
                {
                    "component": "ai_cli",
                    "event": "hook_start",
                    "hook_type": "PreToolUse",
                    "agent_path": str(agent_path),
                    "command": command,
                    "params": payload.model_dump(),
                }
            )
            res = subprocess.run(
                command,
                shell=True,
                text=True,
                input=json.dumps(hook_payload),
                capture_output=True,
            )
            if res.returncode != 0:
                msg = res.stderr.strip() or res.stdout.strip() or "PreToolUse hook failed"
                write_log(
                    {
                        "component": "ai_cli",
                        "event": "hook_end",
                        "hook_type": "PreToolUse",
                        "agent_path": str(agent_path),
                        "command": command,
                        "status": "error",
                        "error": msg,
                    }
                )
                raise RuntimeError(msg)
            write_log(
                {
                    "component": "ai_cli",
                    "event": "hook_end",
                    "hook_type": "PreToolUse",
                    "agent_path": str(agent_path),
                    "command": command,
                    "status": "success",
                }
            )


def run_background(payload: TaskToolInput, runner: RunnerType, model: str, output_dir: Path) -> TaskToolOutputBackground:
    _check_runner_available(runner)
    agent_id = str(uuid.uuid4())
    _ensure_output_dir(output_dir)
    output_file = output_dir / f"{agent_id}.jsonl"
    payload_file = output_dir / f"{agent_id}.input.json"

    user_entry = _jsonl_entry(agent_id, "user", payload.prompt, None)
    output_file.write_text(json.dumps(user_entry) + "\n", encoding="utf-8")
    payload_file.write_text(payload.model_dump_json(), encoding="utf-8")
    try:
        agent_path = resolve_agent_path(payload.subagent_type, runner)
        run_pretool_hooks(agent_path, payload)
    except Exception as exc:
        write_log(
            {
                "component": "ai_cli",
                "event": "hook_failure",
                "mode": "background",
                "runner": runner,
                "model": model,
                "agentId": agent_id,
                "error": str(exc),
            }
        )
        raise
    write_log(
        {
            "component": "ai_cli",
            "event": "task_start",
            "mode": "background",
            "runner": runner,
            "model": model,
            "agentId": agent_id,
            "output_file": str(output_file),
            "prompt_preview": _preview(payload.prompt),
            "params": payload.model_dump(),
        }
    )

    cmd = [
        sys.executable,
        "-m",
        "ai_cli.cli",
        "run-child",
        "--runner",
        runner,
        "--model",
        model,
        "--agent-id",
        agent_id,
        "--output-file",
        str(output_file),
        "--input-file",
        str(payload_file),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if proc.poll() is not None:
        raise RuntimeError("Failed to start background process")

    return TaskToolOutputBackground(
        output="Async agent launched successfully.",
        agentId=agent_id,
        output_file=str(output_file),
    )


def run_background_child_with_payload(
    payload: TaskToolInput, runner: RunnerType, model: str, output_file: Path, agent_id: str
) -> None:
    start = time.monotonic()
    try:
        agent_path = resolve_agent_path(payload.subagent_type, runner)
        run_pretool_hooks(agent_path, payload)
        output = run_sync(runner, model, build_prompt(payload))
        assistant_entry = _jsonl_entry(agent_id, "assistant", output, None)
        write_log(
            {
                "component": "ai_cli",
                "event": "task_end",
                "mode": "background",
                "runner": runner,
                "model": model,
                "agentId": agent_id,
                "output_file": str(output_file),
                "status": "success",
                "duration_ms": int((time.monotonic() - start) * 1000),
            }
        )
    except Exception as exc:
        assistant_entry = _jsonl_entry(agent_id, "assistant", f"ERROR: {exc}", None)
        assistant_entry["is_error"] = True
        write_log(
            {
                "component": "ai_cli",
                "event": "task_end",
                "mode": "background",
                "runner": runner,
                "model": model,
                "agentId": agent_id,
                "output_file": str(output_file),
                "status": "error",
                "error": str(exc),
                "duration_ms": int((time.monotonic() - start) * 1000),
            }
        )
    with output_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(assistant_entry) + "\n")


def run_task(
    payload: TaskToolInput,
    runner: RunnerType,
    model: str,
    run_in_background: bool,
    output_dir: Optional[Path] = None,
    raise_on_error: bool = True,
) -> TaskToolOutputForeground | TaskToolOutputBackground:
    if run_in_background:
        return run_background(payload, runner, model, output_dir or _default_output_dir(runner))
    agent_id = str(uuid.uuid4())
    write_log(
        {
            "component": "ai_cli",
            "event": "task_start",
            "mode": "blocking",
            "runner": runner,
            "model": model,
            "agentId": agent_id,
            "prompt_preview": _preview(payload.prompt),
            "params": payload.model_dump(),
        }
    )
    start = time.monotonic()
    try:
        agent_path = resolve_agent_path(payload.subagent_type, runner)
        run_pretool_hooks(agent_path, payload)
        output = run_sync(runner, model, build_prompt(payload))
        write_log(
            {
                "component": "ai_cli",
                "event": "task_end",
                "mode": "blocking",
                "runner": runner,
                "model": model,
                "agentId": agent_id,
                "status": "success",
                "duration_ms": int((time.monotonic() - start) * 1000),
            }
        )
        return TaskToolOutputForeground(output=output, agentId=agent_id)
    except Exception as exc:
        write_log(
            {
                "component": "ai_cli",
                "event": "task_end",
                "mode": "blocking",
                "runner": runner,
                "model": model,
                "agentId": agent_id,
                "status": "error",
                "error": str(exc),
                "duration_ms": int((time.monotonic() - start) * 1000),
            }
        )
        if raise_on_error:
            raise
        return TaskToolOutputForeground(output=f"ERROR: {exc}", agentId=agent_id)
