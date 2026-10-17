#!/usr/bin/env python3
"""Command lines, isolation flags, and per-session paths for the sc-launchpad runtime."""

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

from launchpad_models import LaunchFailure, LaunchpadInput

TEMP_PREFIX = "sc-launchpad-"
CODEX_HOME_PREFIX = "sc-launchpad-codex-home-"

# Verified against claude 2.1.302 and codex-cli 0.162.1 (README "Isolation
# guarantees"). A rejected flag fails as CLI.UNSUPPORTED_FLAG; nothing is dropped.
CLAUDE_NO_TOOLS_FLAGS = [
    # `--tools` is variadic; the prompt is on stdin, so nothing positional follows it.
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
# Bare `-c` values (no TOML quotes) are taken literally by codex and contain no
# characters a Windows `.cmd` shim would reinterpret.
CODEX_NO_TOOLS_FLAGS = [
    "--ignore-user-config",
    "--ignore-rules",
    "-c",
    "sandbox_mode=read-only",
    "-c",
    "web_search=disabled",
] + [flag for name in CODEX_DISABLED_FEATURES for flag in ("--disable", name)]

# cmd.exe re-parses the arguments of a `.cmd`/`.bat` file; Python cannot escape them.
BATCH_UNSAFE = re.compile(r'["%!^&|<>\r\n]')


class LaunchCommand(NamedTuple):
    argv: List[str]
    stdin: Optional[str]


def isolation_flags(payload: LaunchpadInput) -> List[str]:
    if payload.isolation is None:
        return []
    if payload.tool == "claude":
        return list(CLAUDE_NO_TOOLS_FLAGS) if payload.no_tools else []
    if payload.tool == "codex":
        # Isolated working directories are usually not git repositories.
        return ["--skip-git-repo-check"] + (list(CODEX_NO_TOOLS_FLAGS) if payload.no_tools else [])
    return []


def build_command(payload: LaunchpadInput, model: Optional[str]) -> LaunchCommand:
    """Build argv and the stdin text. claude/codex always read the prompt from stdin."""
    model_args = ["--model", model] if model else []
    if payload.tool == "gemini":
        return LaunchCommand(
            ["gemini", "--yolo", "--prompt", payload.prompt, *model_args, *payload.extra_args],
            None,
        )
    automation = [] if payload.no_tools else (
        ["--dangerously-skip-permissions"] if payload.tool == "claude" else ["--yolo"]
    )
    if payload.tool == "claude":
        argv = ["claude", "--print"]
        if payload.structured:
            argv += ["--output-format", "stream-json", "--verbose"]
        argv += automation + model_args
        if payload.resume_session_id:
            argv += ["--resume", payload.resume_session_id]
        if payload.ephemeral:
            argv.append("--no-session-persistence")
        argv += isolation_flags(payload) + payload.extra_args
        return LaunchCommand(argv, payload.prompt)
    argv = ["codex", "exec"]
    if payload.resume_session_id:
        argv.append("resume")
    if payload.structured:
        argv.append("--json")
    argv += automation + model_args
    if payload.ephemeral:
        argv.append("--ephemeral")
    argv += isolation_flags(payload) + payload.extra_args + ["--"]
    if payload.resume_session_id:
        argv.append(payload.resume_session_id)
    argv.append("-")  # read the prompt from stdin
    return LaunchCommand(argv, payload.prompt)


def check_batch_shim(executable: str, argv: List[str]) -> None:
    if Path(executable).suffix.lower() not in (".cmd", ".bat"):
        return
    unsafe = [arg for arg in argv[1:] if BATCH_UNSAFE.search(arg)]
    if unsafe:
        raise LaunchFailure(
            "CLI.UNSAFE_ARGUMENT",
            f"{executable} is a batch shim; cmd.exe would reinterpret {len(unsafe)} argument(s)",
            "Remove \" % ! ^ & | < > and newlines from model/extra_args (gemini: also the "
            "prompt), or put a native executable first on PATH.",
            recoverable=False,
            details={"executable": executable, "unsafe_arguments": [arg[:200] for arg in unsafe]},
        )


def create_temp_cwd() -> Path:
    try:
        return Path(tempfile.mkdtemp(prefix=TEMP_PREFIX)).resolve()
    except OSError as exc:
        raise LaunchFailure(
            "RUNTIME.TEMP_CWD_FAILED",
            f"Could not create a temporary working directory: {exc}",
            "Check TMPDIR permissions and free space.",
        )


def is_launchpad_temp(path: Path) -> bool:
    return path.parent == Path(tempfile.gettempdir()).resolve() and path.name.startswith(TEMP_PREFIX)


def codex_private_home(cwd: Path, env: Dict[str, str]) -> Path:
    """A CODEX_HOME holding only the login, keyed by cwd so resumed turns find the thread.

    Keeps the user's AGENTS.md, config, and session history out of isolated runs.
    """
    digest = hashlib.sha256(str(cwd).encode("utf-8")).hexdigest()[:16]
    home = Path(tempfile.gettempdir()).resolve() / f"{CODEX_HOME_PREFIX}{digest}"
    auth_source = Path(env.get("CODEX_HOME") or Path.home() / ".codex") / "auth.json"
    auth_target = home / "auth.json"
    try:
        home.mkdir(mode=0o700, exist_ok=True)
        if auth_source.is_file() and not os.path.lexists(auth_target):
            try:
                auth_target.symlink_to(auth_source)
            except OSError:  # Windows without symlink privilege
                os.link(auth_source, auth_target)
    except OSError as exc:
        raise LaunchFailure(
            "RUNTIME.CODEX_HOME_FAILED",
            f"Could not prepare the isolated CODEX_HOME {home}: {exc}",
            "Check TMPDIR permissions; isolation is never weakened by falling back to ~/.codex.",
        )
    return home


def claude_project_dir(cwd: Path, env: Dict[str, str]) -> Path:
    """Where claude stores transcripts for sessions run in ``cwd``."""
    config = Path(env.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return config / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(cwd))
