#!/usr/bin/env python3
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
from typing import List, Literal, Optional, Tuple

import yaml

from ai_cli.logging import write_log
from ai_cli.task_tool import TaskToolInput, TaskToolOutputBackground, TaskToolOutputForeground

from .agent_models import (
    DEFAULT_ALIAS,
    EFFORTS,  # noqa: F401  (re-exported for the CLIs)
    MODELS,
    ModelError,  # noqa: F401  (re-exported for the CLIs)
    model_choices,
    model_flags,
    resolve_effort,
)
from .agent_models import resolve_model as resolve_model_spec

RunnerType = Literal["claude", "codex"]


def model_help(tool: RunnerType = "codex") -> str:
    """``--model`` help text, generated from the shared model table."""
    default = resolve_model_spec(tool)
    return (
        f"{tool} model alias or full id: {', '.join(model_choices(tool))} "
        f"(default: {DEFAULT_ALIAS[tool]} -> {default.id})"
    )


def effort_help(*tools: RunnerType) -> str:
    """``--effort`` help text for ``tools`` (default: both), generated from the shared model table."""
    per_model = "; ".join(
        f"{spec.id}: {spec.efforts[0]}..{spec.efforts[-1]}"
        for tool in (tools or ("codex", "claude"))
        for spec in MODELS[tool].values()
    )
    return (
        "Reasoning effort (overrides the payload's reasoning_effort). When omitted, no effort "
        "flag is passed and the CLI's own config applies."
        f" Supported per model: {per_model}."
    )


def _runner_executable(runner: RunnerType) -> str:
    """Full path of the CLI. On Windows npm installs ``codex.cmd``/``claude.cmd``, which
    only ``shutil.which`` finds; a bare-name subprocess call fails there."""
    path = shutil.which(runner)
    if path is None:
        raise FileNotFoundError(f"{runner} not found on PATH")
    return path


@lru_cache(maxsize=None)
def _check_runner_available(runner: RunnerType) -> str:
    res = subprocess.run([_runner_executable(runner), "--version"], text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or f"{runner} --version failed")
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
    """Alias or full id (None = the runner's default) -> full model id.

    Raises ``agent_models.ModelError`` (a ``ValueError``) listing the valid choices.
    """
    return resolve_model_spec(runner, model).id


def resolve_reasoning_effort(runner: RunnerType, model: str, effort: Optional[str]) -> Optional[str]:
    """Validate ``effort`` for ``model``; None means pass no effort flag."""
    return resolve_effort(resolve_model_spec(runner, model), effort)


def apply_cli_overrides(data: dict, model: Optional[str] = None, effort: Optional[str] = None) -> dict:
    """Return a copy of the raw payload with command-line ``--model``/``--effort`` applied.

    Runs before validation, so a flag wins even over an invalid payload value.
    """
    data = dict(data)
    if model is not None:
        data["model"] = model
    if effort is not None:
        data["reasoning_effort"] = effort
    return data


def prepare_payload(
    data: dict, runner: RunnerType, model: Optional[str] = None, effort: Optional[str] = None
) -> Tuple[TaskToolInput, str]:
    """Apply CLI overrides, validate the payload, and resolve model and effort.

    The resolved full model id is written back into the payload, so background runs and logs
    record what actually runs. Raises ``ModelError`` for an unknown model or an effort the model
    does not support, and pydantic ``ValidationError`` for a malformed payload.
    """
    payload = TaskToolInput.model_validate(apply_cli_overrides(data, model, effort))
    model_id = resolve_model(runner, payload.model)
    resolve_reasoning_effort(runner, model_id, payload.reasoning_effort)
    payload.model = model_id
    return payload, model_id


def build_command(runner: RunnerType, executable: str, model: str, effort: Optional[str]) -> List[str]:
    """CLI argv. The prompt is not in argv: it goes on stdin (``codex exec -`` reads stdin;
    ``claude --print`` with no prompt argument reads stdin)."""
    spec = resolve_model_spec(runner, model)
    flags = model_flags(runner, spec, resolve_effort(spec, effort))
    if runner == "codex":
        return [executable, "exec", "--yolo", *flags, "-"]
    return [executable, *flags, "--print"]


def _resume_context(payload: TaskToolInput, runner: RunnerType) -> Optional[str]:
    if not payload.resume:
        return None
    output_dir = _default_output_dir(runner)
    path = output_dir / f"{payload.resume}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Resume transcript not found: {path}")

    assistant_texts: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "assistant":
                continue
            content = entry.get("message", {}).get("content")
            if isinstance(content, str):
                assistant_texts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        assistant_texts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        assistant_texts.append(item)

    if not assistant_texts:
        return None

    return "\n".join(assistant_texts[-3:])


def build_prompt(payload: TaskToolInput, runner: RunnerType) -> str:
    resume_text = _resume_context(payload, runner)
    lines = [
        f"You are a specialized agent of type '{payload.subagent_type}'.",
        f"Description: {payload.description}",
    ]
    if resume_text:
        lines.extend(
            [
                "Previous assistant output:",
                resume_text,
            ]
        )
    lines.extend(
        [
            f"Task: {payload.prompt}",
            "",
            "Return your result as plain text.",
        ]
    )
    return "\n".join(lines)


def _preview(text: str, limit: int = 200) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def child_env() -> dict:
    """The runner's environment minus ATM_IDENTITY.

    The launched agent is a separate process and must never take on the caller's
    ATM identity. ATM_TEAM is kept: the child is still part of the caller's team.
    """
    env = os.environ.copy()
    env.pop("ATM_IDENTITY", None)
    return env


def run_sync(runner: RunnerType, model: str, prompt: str, reasoning_effort: Optional[str] = None) -> str:
    """Run one prompt to completion. The prompt is sent as UTF-8 bytes on stdin (binary
    mode, so newlines are never translated on Windows)."""
    _check_runner_available(runner)
    cmd = build_command(runner, _runner_executable(runner), model, reasoning_effort)
    res = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, env=child_env())
    stdout = res.stdout.decode("utf-8", errors="replace")
    stderr = res.stderr.decode("utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(stderr.strip() or f"{runner} exited with code {res.returncode}")
    return stdout.strip()


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
                "reasoning_effort": payload.reasoning_effort,
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
            "reasoning_effort": payload.reasoning_effort,
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
    env = os.environ.copy()
    scripts_dir = Path(__file__).resolve().parent.parent
    existing = env.get("PYTHONPATH", "")
    paths = [str(scripts_dir)]
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)

    stderr_path = output_file.with_suffix(".stderr")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=stderr_handle,
        env=env,
    )
    stderr_handle.close()
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
        output = run_sync(runner, model, build_prompt(payload, runner), payload.reasoning_effort)
        assistant_entry = _jsonl_entry(agent_id, "assistant", output, None)
        write_log(
            {
                "component": "ai_cli",
                "event": "task_end",
                "mode": "background",
                "runner": runner,
                "model": model,
                "reasoning_effort": payload.reasoning_effort,
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
                "reasoning_effort": payload.reasoning_effort,
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
    # Fail on an unknown model or unsupported effort before anything is launched.
    resolve_reasoning_effort(runner, model, payload.reasoning_effort)
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
            "reasoning_effort": payload.reasoning_effort,
            "agentId": agent_id,
            "prompt_preview": _preview(payload.prompt),
            "params": payload.model_dump(),
        }
    )
    start = time.monotonic()
    try:
        agent_path = resolve_agent_path(payload.subagent_type, runner)
        run_pretool_hooks(agent_path, payload)
        output = run_sync(runner, model, build_prompt(payload, runner), payload.reasoning_effort)
        write_log(
            {
                "component": "ai_cli",
                "event": "task_end",
                "mode": "blocking",
                "runner": runner,
                "model": model,
                "reasoning_effort": payload.reasoning_effort,
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
                "reasoning_effort": payload.reasoning_effort,
                "agentId": agent_id,
                "status": "error",
                "error": str(exc),
                "duration_ms": int((time.monotonic() - start) * 1000),
            }
        )
        if raise_on_error:
            raise
        return TaskToolOutputForeground(output=f"ERROR: {exc}", agentId=agent_id)
