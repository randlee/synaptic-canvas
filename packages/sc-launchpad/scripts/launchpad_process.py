#!/usr/bin/env python3
"""Run one CLI child with a timeout, killing its whole process tree on timeout or stop."""

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

from launchpad_models import LaunchFailure


class ProcessOutcome(NamedTuple):
    exit_code: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float


class _Terminated(Exception):
    """Raised from a signal handler when the runtime itself is asked to stop."""


def _raise_terminated(signum: int, frame: Any) -> None:
    raise _Terminated(signum)


def _install_stop_handlers() -> Dict[int, Any]:
    """Turn SIGTERM/SIGHUP/SIGBREAK into an exception so the child tree dies with us.

    The child runs in its own process group, so a caller that terminates this
    runtime would otherwise orphan it. Only possible on the main thread.
    """
    if threading.current_thread() is not threading.main_thread():
        return {}
    previous: Dict[int, Any] = {}
    for name in ("SIGTERM", "SIGHUP", "SIGBREAK"):
        signum = getattr(signal, name, None)
        if signum is not None:
            previous[signum] = signal.signal(signum, _raise_terminated)
    return previous


def _restore_handlers(previous: Dict[int, Any]) -> None:
    for signum, handler in previous.items():
        signal.signal(signum, handler)


def _kill_tree(proc: "subprocess.Popen[bytes]") -> None:
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


def _decode(raw: Optional[bytes]) -> str:
    text = (raw or b"").decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def run_process(
    argv: List[str],
    cwd: Path,
    env: Dict[str, str],
    timeout_seconds: Optional[float],
    stdin_text: Optional[str],
) -> ProcessOutcome:
    """Raises ``LaunchFailure`` (CLI.LAUNCH_FAILED, RUNTIME.INTERRUPTED); never orphans the child.

    Binary pipes keep the prompt byte-exact on Windows; the child never inherits
    this process's stdin.
    """
    kwargs: Dict[str, Any] = {
        "cwd": str(cwd),
        "env": env,
        "stdin": subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    started = time.monotonic()
    # Installed before Popen so a stop signal can never land between spawn and wait.
    previous = _install_stop_handlers()
    proc = None
    try:
        try:
            proc = subprocess.Popen(argv, **kwargs)
        except OSError as exc:
            raise LaunchFailure(
                "CLI.LAUNCH_FAILED",
                f"Could not start {argv[0]}: {exc}",
                "Check that the CLI is executable and the working directory is accessible.",
                details={"executable": argv[0]},
            )
        timed_out = False
        try:
            stdout, stderr = proc.communicate(
                stdin_text.encode("utf-8") if stdin_text is not None else None,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(proc)
            try:
                stdout, stderr = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - pipes held open
                stdout, stderr = b"", b""
    except (KeyboardInterrupt, _Terminated) as exc:
        if proc is not None:
            _kill_tree(proc)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover
                pass
        raise LaunchFailure(
            "RUNTIME.INTERRUPTED",
            "sc-launchpad was interrupted; the child process tree was killed",
            "Retry; bound run time with timeout_seconds instead of killing the runtime.",
            details={
                "signal": exc.args[0] if isinstance(exc, _Terminated) else None,
                "child_started": proc is not None,
                "duration_seconds": round(time.monotonic() - started, 3),
            },
        )
    finally:
        _restore_handlers(previous)
    return ProcessOutcome(
        proc.returncode,
        _decode(stdout),
        _decode(stderr),
        timed_out,
        round(time.monotonic() - started, 3),
    )
