#!/usr/bin/env python3
"""Helpers shared by the sc-gh-stack scripts (stdlib only).

Installed next to ``gh_stack_view.py`` and ``gh_stack_chain_check.py`` under
``.claude/scripts/``.  Everything here is read-only: subprocess wrappers and
the git lookups both scripts need.  Never runs a ``gh stack`` write command.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Callable

GIT_TIMEOUT = 60
GH_TIMEOUT = 120


class ToolError(Exception):
    """A required external command is missing or failed; message is actionable."""


def run(cmd: list[str], *, check: bool = True, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    timeout = GH_TIMEOUT if cmd and cmd[0] == "gh" else GIT_TIMEOUT
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"{' '.join(cmd[:3])} timed out after {timeout}s; check network, `gh auth status`, or a hung prompt") from exc
    except FileNotFoundError as exc:
        missing = cmd[0] if exc.filename in (None, cmd[0]) else f"directory {exc.filename}"
        raise ToolError(f"cannot run {' '.join(cmd[:3])}: {missing} not found "
                        f"(install gh + gh-stack extension and git; prune stale worktrees with `git worktree prune`)") from exc
    except OSError as exc:
        raise ToolError(f"cannot run {' '.join(cmd[:3])}: {exc}") from exc
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        raise ToolError(f"{' '.join(cmd[:3])} failed (exit {proc.returncode}): {detail[-1] if detail else 'no output'}"
                        + hint_for(" ".join(detail)))
    return proc


def hint_for(text: str) -> str:
    """Append the next action for the failure signatures gh and git actually produce."""
    low = text.lower()
    if "rate limit" in low or "secondary" in low or "abuse" in low:
        return "; GitHub rate limit: stop all gh calls for 30 min, or use --no-pr for a local-only view"
    if "auth" in low or "401" in low or "token" in low or "not logged" in low:
        return "; run `gh auth status` / `gh auth login`"
    if "could not resolve host" in low or "network" in low or "timed out" in low or "connection" in low:
        return "; network problem: retry, or use --no-fetch/--no-pr for a local-only view"
    if "not a git repository" in low:
        return "; run from inside the repository or one of its worktrees"
    if "extension" in low and "not found" in low:
        return "; `gh extension install github/gh-stack`"
    return ""


def short(sha: str | None) -> str:
    return (sha or "")[:9] or "-"


def origin_sha(ref: str) -> str | None:
    """None when the branch is not on origin (unpushed or deleted after merge)."""
    proc = run(["git", "rev-parse", "--verify", "--quiet", f"origin/{ref}"], check=False)
    return proc.stdout.strip() or None


def is_ancestor(older: str, newer: str) -> bool:
    return run(["git", "merge-base", "--is-ancestor", older, newer], check=False).returncode == 0


def utf8_stdout() -> None:
    """Emoji in the tables must not raise on a non-UTF-8 console (Windows legacy code pages)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def guarded(tag: str, body: Callable[[], int]) -> int:
    """Run ``body``; every failure is one ``<tag>: ...`` line on stderr and exit 2, never a traceback."""
    utf8_stdout()
    try:
        return body()
    except ToolError as exc:
        sys.stderr.write(f"{tag}: {exc}\n")
        return 2
    except KeyboardInterrupt:
        sys.stderr.write(f"{tag}: interrupted\n")
        return 2
    except Exception as exc:  # noqa: BLE001 - the contract is "never a traceback"
        sys.stderr.write(f"{tag}: unexpected {type(exc).__name__}: {exc} (report this with the command you ran)\n")
        return 2
