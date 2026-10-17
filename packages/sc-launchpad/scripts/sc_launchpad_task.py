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
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, Field, ValidationError, model_validator

sys.path.insert(0, str(Path(__file__).resolve().parent))

from launchpad_shared import build_child_env, resolve_teammate_mode


# ---------------------------------------------------------------------------
# Result<T, E>: discriminated union of frozen dataclasses (Python 3.9+)
# ---------------------------------------------------------------------------

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    kind: Literal["ok"] = "ok"


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E
    kind: Literal["err"] = "err"


Result = Union[Ok[T], Err[E]]


@dataclass(frozen=True)
class Failure:
    """Typed failure carried by ``Err`` and rendered into the envelope."""

    code: str
    message: str
    suggested_action: Optional[str] = None
    recoverable: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

CLI_NOT_FOUND = "CLI.NOT_FOUND"
CLI_LAUNCH_FAILED = "CLI.LAUNCH_FAILED"
CLI_NON_ZERO_EXIT = "CLI.NON_ZERO_EXIT"
CLI_TIMEOUT = "CLI.TIMEOUT"
CLI_OUTPUT_UNPARSEABLE = "CLI.OUTPUT_UNPARSEABLE"
CLI_SESSION_ID_MISSING = "CLI.SESSION_ID_MISSING"
CLI_RESULT_MISSING = "CLI.RESULT_MISSING"
CLI_RESUME_SESSION_NOT_FOUND = "CLI.RESUME_SESSION_NOT_FOUND"
CLI_AUTH_FAILED = "CLI.AUTH_FAILED"
CLI_REPORTED_ERROR = "CLI.REPORTED_ERROR"
CLI_UNSUPPORTED_FLAG = "CLI.UNSUPPORTED_FLAG"
CAPABILITY_UNSUPPORTED = "CAPABILITY.UNSUPPORTED"
TEMP_CWD_FAILED = "RUNTIME.TEMP_CWD_FAILED"
RUNTIME_INTERRUPTED = "RUNTIME.INTERRUPTED"

STDERR_TAIL_CHARS = 4000


# ---------------------------------------------------------------------------
# Models and aliases
# ---------------------------------------------------------------------------

ToolName = Literal["claude", "codex", "gemini"]
ClaudeModel = Literal["sonnet", "haiku", "opus", "fable"]
CodexModel = Literal[
    "codex",
    "sol",
    "terra",
    "luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.6",
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
    # `codex` remains a deprecated compatibility alias for Terra.
    "codex": "gpt-5.6-terra",
    "sol": "gpt-5.6-sol",
    "terra": "gpt-5.6-terra",
    "luna": "gpt-5.6-luna",
    "gpt-5.6-sol": "gpt-5.6-sol",
    "gpt-5.6-terra": "gpt-5.6-terra",
    "gpt-5.6-luna": "gpt-5.6-luna",
    "gpt-5.6": "gpt-5.6-sol",
    # Preserve explicit legacy model requests without using them as defaults.
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

CODEX_ROSTER_MODEL_MAP = {
    "gpt-5.6-sol": "sol",
    "gpt-5.6-terra": "terra",
    "gpt-5.6-luna": "luna",
}

CLAUDE_MODEL_MAP = {
    "sonnet": "sonnet",
    "haiku": "haiku",
    "opus": "opus",
    "fable": "fable",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5": "haiku",
    "claude-opus-4-1": "opus",
    "claude-fable-5": "fable",
    "claude-fable-5[1m]": "fable",
}

# Isolation flag sets, verified against claude 2.1.302 and codex-cli 0.162.1
# (see README "Isolation guarantees"). Unknown flags make the child exit
# non-zero, which is reported as CLI.UNSUPPORTED_FLAG, never silently dropped.
CLAUDE_NO_TOOLS_FLAGS = [
    # `--tools` is variadic: another option (never the prompt) must follow it.
    "--tools",
    "",
    "--strict-mcp-config",
    "--safe-mode",
    "--disable-slash-commands",
]
CODEX_DISABLED_FEATURES = [
    "shell_tool",
    "unified_exec",
    # Disabling the code-mode host makes the remaining `exec` tool fail closed.
    "code_mode_host",
    "apps",
    "plugins",
    "multi_agent",
    "image_generation",
    "computer_use",
    "browser_use",
    "in_app_browser",
    "view_image",
    "goals",
    "tool_suggest",
    "skill_search",
]
CODEX_NO_TOOLS_FLAGS = [
    "--ignore-user-config",
    "--ignore-rules",
    "-c",
    'sandbox_mode="read-only"',
    "-c",
    'web_search="disabled"',
] + [flag for name in CODEX_DISABLED_FEATURES for flag in ("--disable", name)]


class IsolationInput(BaseModel):
    """Isolation request for one launch (each turn states it explicitly).

    tools: "none" removes the harness tool surface (see README for the exact
    per-harness guarantee); "default" leaves the harness tool set unchanged.
    cwd: "temp" creates a fresh, empty temporary working directory for a new
    session; "given" uses the payload ``cwd``.
    """

    tools: Literal["default", "none"] = "default"
    cwd: Literal["given", "temp"] = "given"

    model_config = {"extra": "forbid"}


class LaunchpadInput(BaseModel):
    description: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    tool: ToolName
    model: Optional[str] = None
    cwd: Optional[str] = Field(default=None, min_length=1)
    atm_identity: Optional[str] = None
    extra_args: List[str] = Field(default_factory=list)
    output_format: Optional[Literal["text", "json"]] = None
    # Restricted charset: the id is passed on argv (possibly through a Windows
    # `.cmd` shim), and real claude/codex session ids are UUIDs.
    resume_session_id: Optional[str] = Field(
        default=None, min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"
    )
    isolation: Optional[IsolationInput] = None
    timeout_seconds: Optional[float] = Field(default=None, gt=0)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _check_cwd_and_resume(self) -> "LaunchpadInput":
        temp_cwd = self.isolation is not None and self.isolation.cwd == "temp"
        if self.resume_session_id is not None:
            if self.isolation is None:
                raise ValueError(
                    "resume_session_id requires an explicit `isolation` object so a "
                    "resumed turn never keeps or relaxes isolation implicitly"
                )
            if temp_cwd:
                raise ValueError(
                    "isolation.cwd='temp' only applies to a new session; to resume, pass "
                    "the previous envelope's data.cwd as `cwd` with isolation.cwd='given'"
                )
            if self.output_format == "text":
                raise ValueError("resume_session_id requires output_format='json'")
        if temp_cwd and self.cwd is not None:
            raise ValueError("omit `cwd` when isolation.cwd='temp'")
        if not temp_cwd and self.cwd is None:
            raise ValueError("`cwd` is required unless isolation.cwd='temp'")
        return self

    def resolved_output_format(self) -> str:
        if self.output_format is not None:
            return self.output_format
        if self.resume_session_id is not None or self.isolation is not None:
            return "json"
        return "text"


LaunchpadInput.model_rebuild()


class LaunchpadError(Exception):
    """Backward-compatible exception form of ``Failure``."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        recoverable: bool = True,
        suggested_action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.recoverable = recoverable
        self.suggested_action = suggested_action
        self.details = details or {}

    @classmethod
    def from_failure(cls, failure: Failure) -> "LaunchpadError":
        return cls(
            failure.code,
            failure.message,
            recoverable=failure.recoverable,
            suggested_action=failure.suggested_action,
            details=dict(failure.details),
        )

    def to_failure(self) -> Failure:
        return Failure(
            code=self.code,
            message=self.message,
            suggested_action=self.suggested_action,
            recoverable=self.recoverable,
            details=dict(self.details),
        )


def unwrap(result: "Result[T, Failure]") -> T:
    """Raise ``LaunchpadError`` for ``Err`` (compatibility helpers only)."""
    if isinstance(result, Err):
        raise LaunchpadError.from_failure(result.error)
    return result.value


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


def success_response(data: dict) -> dict:
    return {"success": True, "data": data, "error": None}


def error_response(
    error: Union[LaunchpadError, Failure], data: Optional[dict] = None
) -> dict:
    failure = error.to_failure() if isinstance(error, LaunchpadError) else error
    payload: Dict[str, Any] = {
        "code": failure.code,
        "message": failure.message,
        "recoverable": failure.recoverable,
        "suggested_action": failure.suggested_action,
    }
    if failure.details:
        payload["details"] = failure.details
    return {"success": False, "data": data, "error": payload}


def tail(text: Optional[str], limit: int = STDERR_TAIL_CHARS) -> str:
    if not text:
        return ""
    return text[-limit:]


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Treat remaining args as JSON payload ('-' reads the payload from stdin)",
    )
    parser.add_argument("args", nargs="*", help="JSON payload")
    return parser.parse_args(argv)


def load_payload_result(raw: str) -> "Result[LaunchpadInput, Failure]":
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return Err(
            Failure(
                "VALIDATION.INVALID_JSON",
                f"Invalid JSON payload: {exc}",
                suggested_action="Pass one valid JSON object to --json.",
            )
        )
    try:
        return Ok(LaunchpadInput.model_validate(data))
    except ValidationError as exc:
        return Err(
            Failure(
                "VALIDATION.INVALID_PAYLOAD",
                f"Invalid launch payload: {exc}",
                suggested_action=(
                    "Provide required fields: description, prompt, tool, and cwd (unless "
                    "isolation.cwd='temp'); use only documented optional fields."
                ),
            )
        )


def load_payload(raw: str) -> LaunchpadInput:
    return unwrap(load_payload_result(raw))


def resolve_cwd_result(cwd: str) -> "Result[Path, Failure]":
    path = Path(cwd).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        return Err(
            Failure(
                "VALIDATION.INVALID_CWD",
                f"Working directory does not exist: {path}",
                suggested_action="Pass an existing directory in the `cwd` field.",
            )
        )
    return Ok(path)


def resolve_cwd(cwd: str) -> Path:
    return unwrap(resolve_cwd_result(cwd))


def prepare_cwd(payload: LaunchpadInput) -> "Result[Path, Failure]":
    if payload.isolation is not None and payload.isolation.cwd == "temp":
        try:
            return Ok(Path(tempfile.mkdtemp(prefix="sc-launchpad-")).resolve())
        except OSError as exc:
            return Err(
                Failure(
                    TEMP_CWD_FAILED,
                    f"Could not create a temporary working directory: {exc}",
                    suggested_action="Check TMPDIR permissions and free space.",
                )
            )
    return resolve_cwd_result(payload.cwd or "")


def normalize_tool_model_result(
    payload: LaunchpadInput,
) -> "Result[Optional[str], Failure]":
    if payload.tool == "claude":
        if payload.model is None:
            return Ok("sonnet")
        normalized = CLAUDE_MODEL_MAP.get(payload.model)
        if normalized is None:
            return Err(
                Failure(
                    "VALIDATION.INVALID_MODEL",
                    f"Unsupported Claude model: {payload.model}",
                    suggested_action="Use one of: sonnet, haiku, opus, fable.",
                )
            )
        return Ok(normalized)
    if payload.tool == "codex":
        if payload.model is None:
            return Ok("gpt-5.6-terra")
        normalized = CODEX_MODEL_MAP.get(payload.model)
        if normalized is None:
            return Err(
                Failure(
                    "VALIDATION.INVALID_MODEL",
                    f"Unsupported Codex model: {payload.model}",
                    suggested_action="Use sol, terra, luna, codex (deprecated), or a known Codex model alias.",
                )
            )
        return Ok(normalized)
    return Ok(payload.model)


def normalize_tool_model(payload: LaunchpadInput) -> Optional[str]:
    return unwrap(normalize_tool_model_result(payload))


def roster_model(payload: LaunchpadInput, normalized_model: Optional[str]) -> str:
    if payload.tool == "claude":
        return normalized_model or "sonnet"
    if payload.tool == "codex":
        return CODEX_ROSTER_MODEL_MAP.get(
            normalized_model or "", normalized_model or "terra"
        )
    return payload.tool


def check_capabilities(payload: LaunchpadInput) -> "Result[None, Failure]":
    if payload.tool != "gemini":
        return Ok(None)
    requested = []
    if payload.output_format == "json":
        requested.append("output_format='json'")
    if payload.resume_session_id is not None:
        requested.append("resume_session_id")
    if payload.isolation is not None:
        requested.append("isolation")
    if not requested:
        return Ok(None)
    return Err(
        Failure(
            CAPABILITY_UNSUPPORTED,
            "gemini does not support " + ", ".join(requested) + " in sc-launchpad",
            suggested_action=(
                "Use tool 'claude' or 'codex' for session ids, resume, and isolation, "
                "or launch gemini in text mode without these fields."
            ),
            recoverable=False,
            details={"tool": "gemini", "unsupported_fields": requested},
        )
    )


# ---------------------------------------------------------------------------
# CLI resolution
# ---------------------------------------------------------------------------


def path_dirs(env: Dict[str, str]) -> List[str]:
    return [entry for entry in env.get("PATH", "").split(os.pathsep) if entry]


def which_result(
    name: str, env: Optional[Dict[str, str]] = None
) -> "Result[str, Failure]":
    env = dict(os.environ) if env is None else env
    found = shutil.which(name, path=env.get("PATH", ""))
    if found is None:
        return Err(
            Failure(
                CLI_NOT_FOUND,
                f"Required CLI is not available on PATH: {name}",
                suggested_action=f"Install `{name}` or adjust PATH before launching.",
                details={"cli": name, "searched_path": path_dirs(env)},
            )
        )
    return Ok(found)


def ensure_command(name: str) -> None:
    unwrap(which_result(name))


def maybe_add_member(
    parent_env: Dict[str, str],
    teammate_mode: bool,
    team: Optional[str],
    identity: Optional[str],
    payload: LaunchpadInput,
    normalized_model: Optional[str],
    cwd: Path,
) -> "Result[None, Failure]":
    if not teammate_mode:
        return Ok(None)
    atm = which_result("atm", parent_env)
    if isinstance(atm, Err):
        return atm
    command = [
        atm.value,
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
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        env=parent_env,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "atm teams add-member failed"
        )
        return Err(
            Failure(
                "ATM.ADD_MEMBER_FAILED",
                message,
                suggested_action="Ensure the team exists and the identity can be added before retrying.",
                details={"stderr_tail": tail(result.stderr)},
            )
        )
    return Ok(None)


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------


def isolation_flags(payload: LaunchpadInput) -> List[str]:
    """Flags added for the requested isolation (empty for claude tools='default')."""
    iso = payload.isolation
    if iso is None:
        return []
    if payload.tool == "claude":
        return list(CLAUDE_NO_TOOLS_FLAGS) if iso.tools == "none" else []
    if payload.tool == "codex":
        # Isolated working directories are usually not git repositories.
        flags = ["--skip-git-repo-check"]
        if iso.tools == "none":
            flags.extend(CODEX_NO_TOOLS_FLAGS)
        return flags
    return []


def build_command(
    payload: LaunchpadInput, normalized_model: Optional[str]
) -> List[str]:
    extra = list(payload.extra_args)
    structured = payload.resolved_output_format() == "json"
    no_tools = payload.isolation is not None and payload.isolation.tools == "none"
    if payload.tool == "claude":
        if not structured:
            command = ["claude", "--dangerously-skip-permissions", "--print"]
            if normalized_model:
                command.extend(["--model", normalized_model])
            command.extend(extra)
            command.append(payload.prompt)
            return command
        command = ["claude", "--print", "--output-format", "json"]
        if not no_tools:
            command.append("--dangerously-skip-permissions")
        if normalized_model:
            command.extend(["--model", normalized_model])
        if payload.resume_session_id:
            command.extend(["--resume", payload.resume_session_id])
        command.extend(isolation_flags(payload))
        command.extend(extra)
        # The prompt is written to stdin (see prompt_stdin): no positional prompt.
        return command
    if payload.tool == "codex":
        if not structured:
            command = ["codex", "exec", "--yolo"]
            if normalized_model:
                command.extend(["--model", normalized_model])
            command.extend(extra)
            command.append(payload.prompt)
            return command
        command = ["codex", "exec"]
        if payload.resume_session_id:
            command.append("resume")
        command.append("--json")
        if not no_tools:
            command.append("--yolo")
        if normalized_model:
            command.extend(["--model", normalized_model])
        command.extend(isolation_flags(payload))
        command.extend(extra)
        command.append("--")
        if payload.resume_session_id:
            command.append(payload.resume_session_id)
        # `-` makes codex read the prompt from stdin (see prompt_stdin).
        command.append("-")
        return command
    command = ["gemini", "--yolo", "--prompt", payload.prompt]
    if normalized_model:
        command.extend(["--model", normalized_model])
    command.extend(extra)
    return command


def prompt_stdin(payload: LaunchpadInput) -> Optional[str]:
    """Prompt text written to the child's stdin, or None when it is on argv.

    Structured (JSON) claude/codex launches deliver the prompt on stdin so large
    prompts never hit command-line length limits (about 32K characters on
    Windows) and never pass through a ``.cmd`` shim's argument parsing. Legacy
    text mode keeps the prompt on the command line, exactly as before.
    """
    if payload.tool in ("claude", "codex") and payload.resolved_output_format() == "json":
        return payload.prompt
    return None


# ---------------------------------------------------------------------------
# Process execution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessOutcome:
    exit_code: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float


def _kill_tree(proc: "subprocess.Popen[str]") -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    try:
        proc.kill()
    except OSError:
        pass


class _Terminated(Exception):
    """Raised from a signal handler when the runtime itself is asked to stop."""


def _raise_terminated(signum: int, frame: Any) -> None:
    raise _Terminated(signum)


def _install_stop_handlers() -> Dict[int, Any]:
    """Turn SIGTERM/SIGHUP into an exception so the child tree is killed too.

    The child runs in its own process group (needed to kill grandchildren on
    timeout), so a caller that terminates this runtime would otherwise orphan
    it. Only possible on the main thread; SIGKILL cannot be intercepted.
    """
    if threading.current_thread() is not threading.main_thread():
        return {}
    previous: Dict[int, Any] = {}
    for name in ("SIGTERM", "SIGHUP", "SIGBREAK"):
        signum = getattr(signal, name, None)
        if signum is None:
            continue
        try:
            previous[signum] = signal.signal(signum, _raise_terminated)
        except (OSError, ValueError):  # pragma: no cover - platform specific
            continue
    return previous


def _restore_handlers(previous: Dict[int, Any]) -> None:
    for signum, handler in previous.items():
        try:
            signal.signal(signum, handler)
        except (OSError, ValueError, TypeError):  # pragma: no cover
            pass


def run_process(
    command: List[str],
    cwd: Path,
    env: Dict[str, str],
    timeout_seconds: Optional[float],
    stdin_text: Optional[str] = None,
) -> "Result[ProcessOutcome, Failure]":
    # The child never inherits this process's stdin: it gets either the prompt
    # through a pipe or an empty stdin.
    popen_kwargs: Dict[str, Any] = {
        "cwd": str(cwd),
        "env": env,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "stdin": subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        # Own process group so a timeout kills the whole child tree.
        popen_kwargs["start_new_session"] = True
    started = time.monotonic()
    try:
        proc = subprocess.Popen(command, **popen_kwargs)
    except OSError as exc:
        return Err(
            Failure(
                CLI_LAUNCH_FAILED,
                f"Could not start {command[0]}: {exc}",
                suggested_action="Check that the CLI is executable and the working directory is accessible.",
                details={"executable": command[0]},
            )
        )
    timed_out = False
    previous_handlers = _install_stop_handlers()
    try:
        try:
            stdout, stderr = proc.communicate(input=stdin_text, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(proc)
            try:
                stdout, stderr = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - pipes held open
                stdout, stderr = "", ""
    except (KeyboardInterrupt, _Terminated) as exc:
        _kill_tree(proc)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover
            pass
        signum = exc.args[0] if isinstance(exc, _Terminated) and exc.args else None
        return Err(
            Failure(
                RUNTIME_INTERRUPTED,
                "sc-launchpad was interrupted; the child process tree was killed",
                suggested_action=(
                    "Retry the launch; use timeout_seconds instead of killing the runtime "
                    "to bound run time."
                ),
                details={
                    "signal": signum,
                    "duration_seconds": round(time.monotonic() - started, 3),
                },
            )
        )
    finally:
        _restore_handlers(previous_handlers)
    return Ok(
        ProcessOutcome(
            exit_code=proc.returncode,
            stdout=stdout or "",
            stderr=stderr or "",
            timed_out=timed_out,
            duration_seconds=round(time.monotonic() - started, 3),
        )
    )


# ---------------------------------------------------------------------------
# Structured output parsing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedOutput:
    session_id: Optional[str]
    result_text: Optional[str]
    reported_error: Optional[str]
    auth_hint: bool = False
    warnings: List[str] = field(default_factory=list)


AUTH_PATTERN = re.compile(
    r"invalid api key|invalid x-api-key|not logged in|please run /login|codex login|"
    r"unauthori[sz]ed|authentication (?:failed|error|required)|\b401\b|"
    r"oauth token (?:has )?expired|login required",
    re.IGNORECASE,
)
RESUME_NOT_FOUND_PATTERN = re.compile(
    r"no conversation found|no rollout found|session \S* ?not found|thread \S* ?not found",
    re.IGNORECASE,
)
UNSUPPORTED_FLAG_PATTERN = re.compile(
    r"unknown option|unknown feature flag|unexpected argument|unrecognized (?:option|argument)",
    re.IGNORECASE,
)
# Captures the rejected name: codex `Unknown feature flag: <name>` /
# `unexpected argument '<flag>'`, claude `unknown option '<flag>'`.
REJECTED_FLAG_PATTERN = re.compile(
    r"(?:unknown feature flag:?\s*|unknown option\s*|unexpected argument\s*|"
    r"unrecognized (?:option|argument):?\s*)['\"`]?([^'\"`\s]+)",
    re.IGNORECASE,
)


def unsupported_flag_failure(
    payload: "LaunchpadInput", stderr: str, base_details: Dict[str, Any]
) -> Failure:
    match = REJECTED_FLAG_PATTERN.search(stderr)
    rejected = match.group(1) if match else None
    details = dict(base_details, rejected=rejected)
    if rejected is not None:
        details["rejected_is_isolation_flag"] = rejected in isolation_flags(payload)
    name = f" `{rejected}`" if rejected else ""
    if rejected is not None and details["rejected_is_isolation_flag"]:
        action = (
            f"The installed {payload.tool} CLI does not accept isolation flag/feature{name}. "
            f"Run `{payload.tool} --version` and compare with the versions in the "
            "sc-launchpad README \"Isolation guarantees\"; upgrade the CLI or update "
            "sc-launchpad's isolation flag set. Isolation is never weakened automatically."
        )
    else:
        action = (
            f"Remove or fix{name or ' the offending flag'} in extra_args, or compare the "
            f"installed {payload.tool} CLI version with the versions in the sc-launchpad README."
        )
    return Failure(
        CLI_UNSUPPORTED_FLAG,
        f"{payload.tool} rejected command-line flag/feature{name or ' (unknown name)'}",
        suggested_action=action,
        details=details,
    )


def parse_claude_output(stdout: str) -> "Result[ParsedOutput, Failure]":
    text = stdout.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return Err(
            Failure(
                CLI_OUTPUT_UNPARSEABLE,
                f"claude --output-format json produced unparseable output: {exc}",
                suggested_action=(
                    "Check that extra_args do not override --output-format and that the "
                    "installed claude CLI supports --print --output-format json."
                ),
                details={"stdout_head": text[:1000]},
            )
        )
    if not isinstance(data, dict):
        return Err(
            Failure(
                CLI_OUTPUT_UNPARSEABLE,
                "claude JSON output was not an object",
                suggested_action="Upgrade claude or remove conflicting extra_args.",
                details={"stdout_head": text[:1000]},
            )
        )
    session_id = data.get("session_id")
    result_text = data.get("result")
    session_id = session_id if isinstance(session_id, str) and session_id else None
    result_text = result_text if isinstance(result_text, str) else None
    reported_error = None
    auth_hint = False
    if data.get("is_error") is True:
        reported_error = result_text or str(
            data.get("subtype") or "claude reported is_error=true"
        )
        auth_hint = data.get("api_error_status") in (401, 403)
    return Ok(
        ParsedOutput(
            session_id=session_id,
            result_text=result_text,
            reported_error=reported_error,
            auth_hint=auth_hint,
        )
    )


def parse_codex_output(stdout: str) -> "Result[ParsedOutput, Failure]":
    session_id: Optional[str] = None
    result_text: Optional[str] = None
    turn_failed: Optional[str] = None
    error_events: List[str] = []
    warnings: List[str] = []
    turn_completed = False
    events = 0
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            return Err(
                Failure(
                    CLI_OUTPUT_UNPARSEABLE,
                    f"codex exec --json produced a non-JSON line {line_no}: {exc}",
                    suggested_action=(
                        "Check that extra_args do not disable --json and that the installed "
                        "codex CLI emits JSONL events."
                    ),
                    details={"line": line[:1000], "line_number": line_no},
                )
            )
        if not isinstance(event, dict):
            continue
        events += 1
        etype = event.get("type")
        if etype == "thread.started" and isinstance(event.get("thread_id"), str):
            session_id = event["thread_id"] or None
        elif etype == "item.completed":
            item = event.get("item") or {}
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                result_text = item["text"]
            elif item.get("type") == "error" and item.get("message"):
                warnings.append(str(item["message"]))
        elif etype == "turn.completed":
            turn_completed = True
        elif etype == "turn.failed":
            error = event.get("error") or {}
            turn_failed = str(error.get("message") or "codex reported turn.failed")
        elif etype == "error":
            error_events.append(str(event.get("message") or "codex reported an error event"))
    if events == 0:
        return Err(
            Failure(
                CLI_OUTPUT_UNPARSEABLE,
                "codex exec --json produced no JSON events",
                suggested_action="Inspect stderr; the installed codex CLI may not support --json.",
                details={"stdout_head": stdout[:1000]},
            )
        )
    reported_error = turn_failed
    if reported_error is None and error_events and not turn_completed:
        reported_error = error_events[-1]
    elif turn_completed:
        # Transient error events (e.g. reconnects) before a completed turn.
        warnings.extend(error_events)
    return Ok(
        ParsedOutput(
            session_id=session_id,
            result_text=result_text,
            reported_error=reported_error,
            warnings=warnings,
        )
    )


def scan_partial_session_id(tool: str, stdout: str) -> Optional[str]:
    """Best-effort session id from output of a killed process (codex streams it first)."""
    if tool != "codex":
        return None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "thread.started":
            thread_id = event.get("thread_id")
            return thread_id if isinstance(thread_id, str) and thread_id else None
    return None


PARSERS: Dict[str, Callable[[str], "Result[ParsedOutput, Failure]"]] = {
    "claude": parse_claude_output,
    "codex": parse_codex_output,
}


def timeout_failure(payload: LaunchpadInput, outcome: ProcessOutcome) -> Failure:
    return Failure(
        CLI_TIMEOUT,
        f"{payload.tool} did not finish within {payload.timeout_seconds}s and was killed",
        suggested_action="Increase timeout_seconds or shorten the prompt.",
        details={
            "stderr_tail": tail(outcome.stderr),
            "timeout_seconds": payload.timeout_seconds,
            "partial_session_id": scan_partial_session_id(payload.tool, outcome.stdout),
        },
    )


def classify_structured(
    payload: LaunchpadInput, outcome: ProcessOutcome
) -> "Result[ParsedOutput, Failure]":
    """Turn a finished structured-mode process into parsed output or a typed failure."""
    tool = payload.tool
    if outcome.timed_out:
        return Err(timeout_failure(payload, outcome))

    base_details: Dict[str, Any] = {
        "stderr_tail": tail(outcome.stderr),
        "exit_code": outcome.exit_code,
    }
    parsed_result = PARSERS[tool](outcome.stdout) if outcome.stdout.strip() else None
    parsed = parsed_result.value if isinstance(parsed_result, Ok) else None
    reported = parsed.reported_error if parsed is not None else None
    if parsed is not None and parsed.session_id:
        base_details["session_id"] = parsed.session_id

    if outcome.exit_code != 0 or reported:
        if reported:
            base_details["reported_error"] = reported
        signal_text = "\n".join(p for p in (outcome.stderr, reported) if p)
        if payload.resume_session_id and RESUME_NOT_FOUND_PATTERN.search(signal_text):
            return Err(
                Failure(
                    CLI_RESUME_SESSION_NOT_FOUND,
                    f"{tool} could not find session {payload.resume_session_id}",
                    suggested_action=(
                        "Pass a session_id returned by a previous launch together with the "
                        "cwd that launch reported (data.cwd)."
                    ),
                    details=dict(base_details, resume_session_id=payload.resume_session_id),
                )
            )
        if (parsed is not None and parsed.auth_hint) or AUTH_PATTERN.search(signal_text):
            return Err(
                Failure(
                    CLI_AUTH_FAILED,
                    f"{tool} reported an authentication failure",
                    suggested_action=f"Re-authenticate the {tool} CLI (log in again) and retry.",
                    details=base_details,
                )
            )
        if outcome.exit_code != 0 and UNSUPPORTED_FLAG_PATTERN.search(outcome.stderr):
            return Err(unsupported_flag_failure(payload, outcome.stderr, base_details))
        if outcome.exit_code != 0:
            return Err(
                Failure(
                    CLI_NON_ZERO_EXIT,
                    f"{tool} exited with code {outcome.exit_code}",
                    suggested_action="Inspect stdout/stderr in the returned payload and retry with adjusted prompt or args.",
                    details=base_details,
                )
            )
        return Err(
            Failure(
                CLI_REPORTED_ERROR,
                f"{tool} exited 0 but reported an error: {reported}",
                suggested_action="Inspect data.stdout for the error and retry.",
                details=base_details,
            )
        )

    if parsed_result is None:
        return Err(
            Failure(
                CLI_OUTPUT_UNPARSEABLE,
                f"{tool} exited 0 but produced no structured output",
                suggested_action="Check that extra_args do not override the structured output mode.",
                details=base_details,
            )
        )
    if isinstance(parsed_result, Err):
        failure = parsed_result.error
        return Err(
            Failure(
                failure.code,
                failure.message,
                suggested_action=failure.suggested_action,
                details=dict(failure.details, **base_details),
            )
        )
    if not parsed_result.value.session_id:
        return Err(
            Failure(
                CLI_SESSION_ID_MISSING,
                f"{tool} structured output did not include a session id",
                suggested_action="Upgrade or check the CLI; the session id field/event may have been renamed.",
                details=base_details,
            )
        )
    if parsed_result.value.result_text is None:
        return Err(
            Failure(
                CLI_RESULT_MISSING,
                f"{tool} structured output did not include a final assistant message",
                suggested_action="Inspect data.stdout; the turn may have ended without a reply.",
                details=base_details,
            )
        )
    return parsed_result


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_payload(payload: LaunchpadInput, parent_env: Dict[str, str]) -> dict:
    capability = check_capabilities(payload)
    if isinstance(capability, Err):
        return error_response(capability.error)
    model_result = normalize_tool_model_result(payload)
    if isinstance(model_result, Err):
        return error_response(model_result.error)
    normalized_model = model_result.value
    if payload.isolation is None or payload.isolation.cwd != "temp":
        given_cwd = resolve_cwd_result(payload.cwd or "")
        if isinstance(given_cwd, Err):
            return error_response(given_cwd.error)
    executable = which_result(payload.tool, parent_env)
    if isinstance(executable, Err):
        return error_response(executable.error)
    cwd_result = prepare_cwd(payload)
    if isinstance(cwd_result, Err):
        return error_response(cwd_result.error)
    cwd = cwd_result.value

    teammate_mode, team, identity = resolve_teammate_mode(parent_env, payload.atm_identity)
    member = maybe_add_member(
        parent_env, teammate_mode, team, identity, payload, normalized_model, cwd
    )
    if isinstance(member, Err):
        if payload.isolation is not None and payload.isolation.cwd == "temp":
            # No child ran and the directory was never reported: remove it.
            shutil.rmtree(cwd, ignore_errors=True)
        return error_response(member.error)
    child_env = build_child_env(parent_env, teammate_mode, team, identity)
    command = build_command(payload, normalized_model)
    command[0] = executable.value

    output_format = payload.resolved_output_format()
    isolation = None
    if payload.isolation is not None:
        isolation = {
            "tools": payload.isolation.tools,
            "cwd": payload.isolation.cwd,
            "flags": isolation_flags(payload),
        }
    data: Dict[str, Any] = {
        "tool": payload.tool,
        "model": normalized_model,
        "cwd": str(cwd),
        # True when this launch created data.cwd (isolation.cwd="temp"). The
        # directory is kept so later turns can resume in it; the caller owns
        # deleting it after the last turn.
        "temp_cwd_created": bool(
            payload.isolation is not None and payload.isolation.cwd == "temp"
        ),
        "teammate_mode": teammate_mode,
        "atm_team": team,
        "atm_identity": identity,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "output_format": output_format,
        "session_id": None,
        "result_text": None,
        "resumed_session_id": payload.resume_session_id,
        "isolation": isolation,
        "timeout_seconds": payload.timeout_seconds,
        "timed_out": False,
        "duration_seconds": None,
        "warnings": [],
    }

    outcome_result = run_process(
        command, cwd, child_env, payload.timeout_seconds, prompt_stdin(payload)
    )
    if isinstance(outcome_result, Err):
        return error_response(outcome_result.error, data)
    outcome = outcome_result.value
    data.update(
        exit_code=outcome.exit_code,
        stdout=outcome.stdout,
        stderr=outcome.stderr,
        timed_out=outcome.timed_out,
        duration_seconds=outcome.duration_seconds,
    )

    if output_format == "text":
        if outcome.timed_out:
            return error_response(timeout_failure(payload, outcome), data)
        if outcome.exit_code == 0:
            return success_response(data)
        return error_response(
            Failure(
                CLI_NON_ZERO_EXIT,
                f"{payload.tool} exited with code {outcome.exit_code}",
                suggested_action="Inspect stdout/stderr in the returned payload and retry with adjusted prompt or args.",
                details={"stderr_tail": tail(outcome.stderr), "exit_code": outcome.exit_code},
            ),
            data,
        )

    classified = classify_structured(payload, outcome)
    if isinstance(classified, Err):
        details = classified.error.details
        data["session_id"] = details.get("partial_session_id") or details.get("session_id")
        return error_response(classified.error, data)
    parsed = classified.value
    data["session_id"] = parsed.session_id
    data["result_text"] = parsed.result_text
    data["warnings"] = list(parsed.warnings)
    if payload.resume_session_id and parsed.session_id != payload.resume_session_id:
        data["warnings"].append(
            f"resumed session {payload.resume_session_id} reported session id {parsed.session_id}"
        )
    return success_response(data)


def read_raw_payload(args: argparse.Namespace) -> str:
    raw = " ".join(args.args).strip()
    if raw == "-":
        # JSON is UTF-8 (RFC 8259); do not depend on the locale encoding
        # (cp1252 on many Windows hosts). `utf-8-sig` drops a PowerShell BOM.
        return sys.stdin.buffer.read().decode("utf-8-sig", errors="replace").strip()
    return raw


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    raw = read_raw_payload(args)
    if not raw:
        print(
            json.dumps(
                error_response(
                    Failure(
                        "VALIDATION.MISSING_INPUT",
                        "No launch payload was provided.",
                        suggested_action="Pass a JSON object with --json (or `--json -` to read stdin).",
                    )
                ),
                indent=2,
            )
        )
        return 0

    try:
        loaded = load_payload_result(raw)
        if isinstance(loaded, Err):
            response = error_response(loaded.error)
        else:
            response = run_payload(loaded.value, dict(os.environ))
    except Exception as exc:  # pragma: no cover - safety net
        response = error_response(
            Failure("RUNTIME.UNEXPECTED", str(exc), recoverable=False)
        )

    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
