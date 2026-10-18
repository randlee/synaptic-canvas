#!/usr/bin/env python3
"""`env_file` support: find a dotenv file, parse it, and merge it over the inherited env.

A shell alias that sources `.env` before starting `claude` or `codex` does nothing for
launchpad, which starts the binary directly. `env_file` makes that loading explicit.

Values never appear in errors, results, or the audit log: only the file path and the
variable names do.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from launchpad_models import LaunchFailure

KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DOUBLE_QUOTED_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}


def _git_roots(start: Path) -> Tuple[Optional[Path], Optional[Path]]:
    """(repository root, main worktree root) for ``start``; read from `.git`, no subprocess.

    In the main checkout both are the same directory. In a linked worktree `.git` is a
    file (``gitdir: <main>/.git/worktrees/<name>``) whose `commondir` names the shared
    `.git`; the main worktree is its parent.
    """
    for directory in (start, *start.parents):
        dot_git = directory / ".git"
        if dot_git.is_dir():
            return directory, directory
        if not dot_git.is_file():
            continue
        try:
            line = dot_git.read_text(encoding="utf-8").strip()
        except OSError:
            return directory, None
        if not line.startswith("gitdir:"):
            return directory, None
        gitdir = (directory / line[len("gitdir:"):].strip()).resolve()
        try:
            common = (gitdir / (gitdir / "commondir").read_text(encoding="utf-8").strip()).resolve()
        except OSError:
            return directory, None  # a submodule or a bare layout: no main worktree to fall back to
        return directory, common.parent if common.name == ".git" else None
    return None, None


def find_env_file(env_file: str, base: Path) -> Path:
    """Resolve ``env_file``. Absolute (or ``~``) paths are used as given; a relative path is
    looked up in ``base``, then the repository root, then the main worktree root, and the
    first that exists wins (an untracked `.env` usually lives only in the main checkout)."""
    path = Path(env_file).expanduser()
    if path.is_absolute():
        candidates = [path]
    else:
        repo_root, main_root = _git_roots(base)
        candidates = []
        for root in (base, repo_root, main_root):
            if root is not None and (root / path) not in candidates:
                candidates.append(root / path)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise LaunchFailure(
        "VALIDATION.ENV_FILE_NOT_FOUND",
        f"env_file '{env_file}' was not found.",
        "Create the file, or pass an absolute path in `env_file`.",
        details={"searched": [str(c) for c in candidates]},
    )


def _invalid(path: Path, number: int, problem: str) -> LaunchFailure:
    # Line number and problem only: the line itself may hold a credential.
    return LaunchFailure(
        "VALIDATION.INVALID_ENV_FILE",
        f"{path}, line {number}: {problem}",
        "Use KEY=value lines (optionally `export KEY=value`, quoted values, # comments).",
        details={"env_file": str(path), "line": number},
    )


def _double_quoted(body: str) -> Optional[Tuple[str, str]]:
    """(value, rest after the closing quote) for text after an opening `"`; None if unclosed."""
    out: List[str] = []
    i = 0
    while i < len(body):
        char = body[i]
        if char == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            out.append(DOUBLE_QUOTED_ESCAPES.get(nxt, "\\" + nxt))
            i += 2
            continue
        if char == '"':
            return "".join(out), body[i + 1:]
        out.append(char)
        i += 1
    return None


def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse dotenv syntax: ``KEY=value`` lines, optional ``export``, ``#`` comments, single
    quotes (literal), double quotes (``\\n \\r \\t \\" \\\\`` escapes). Values are literal: no
    ``$VAR`` expansion, no multi-line values. A repeated key keeps its last value."""
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise LaunchFailure(
            "VALIDATION.INVALID_ENV_FILE",
            f"Could not read env_file {path}: {type(exc).__name__}",
            "Check that the file is readable UTF-8 text.",
            details={"env_file": str(path)},
        )
    values: Dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export") and line[6:7].isspace():
            line = line[6:].lstrip()
        key, sep, rest = line.partition("=")
        key, rest = key.strip(), rest.strip()
        if not sep:
            raise _invalid(path, number, "expected KEY=value")
        if not KEY.match(key):
            raise _invalid(path, number, "the variable name is not a valid identifier")
        if rest.startswith("'"):
            end = rest.find("'", 1)
            if end < 0:
                raise _invalid(path, number, "unterminated single-quoted value")
            value, after = rest[1:end], rest[end + 1:]
        elif rest.startswith('"'):
            parsed = _double_quoted(rest[1:])
            if parsed is None:
                raise _invalid(path, number, "unterminated double-quoted value")
            value, after = parsed
        else:
            value, after = re.split(r"\s+#", rest, maxsplit=1)[0].rstrip(), ""
        if after.strip() and not after.strip().startswith("#"):
            raise _invalid(path, number, "unexpected text after the closing quote")
        values[key] = value
    return values


def merge_env(inherited: Dict[str, str], overrides: Dict[str, str], case_insensitive: bool) -> Dict[str, str]:
    """``inherited`` with ``overrides`` on top. Windows variable names are case-insensitive,
    so there a file's ``Path`` replaces the inherited ``PATH`` instead of duplicating it."""
    env = dict(inherited)
    if case_insensitive:
        upper = {key.upper() for key in overrides}
        env = {key: value for key, value in env.items() if key.upper() not in upper}
    env.update(overrides)
    return env


def load_env_file(
    env_file: str, base: Path, inherited: Dict[str, str]
) -> Tuple[Dict[str, str], Path, List[str]]:
    """(merged env, resolved file, sorted variable names) for one launch."""
    path = find_env_file(env_file, base)
    values = parse_env_file(path)
    return merge_env(inherited, values, case_insensitive=os.name == "nt"), path, sorted(values)
