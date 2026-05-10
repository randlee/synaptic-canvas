#!/usr/bin/env python3
"""Shared helpers for sc-launch-term."""

from __future__ import annotations

from datetime import UTC, datetime
import os
import secrets
import shlex
import sys
from pathlib import Path


_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CROCKFORD_DECODE = {char: index for index, char in enumerate(_CROCKFORD)}


def quote_shell(value: str) -> str:
    return shlex.quote(value)


def quote_powershell(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def shell_mode_for_terminal(terminal: str) -> str:
    if terminal == "wt":
        return "powershell"
    return "posix"


def normalize_passthrough_args(args: list[str]) -> list[str]:
    if args and args[0] == "--":
        return args[1:]
    return args


def resolve_team() -> str | None:
    team = os.environ.get("ATM_TEAM", "").strip()
    return team or None


_ADJECTIVES = [
    "amber", "bold", "calm", "deft", "eager", "fleet", "gold", "hale",
    "iron", "jade", "keen", "lean", "mint", "nova", "opal", "prim",
    "quick", "rust", "sage", "teal", "umber", "vivid", "warm", "zeal",
]
_NOUNS = [
    "atlas", "birch", "coral", "dune", "ember", "flint", "grove", "hawk",
    "inlet", "junco", "kite", "lynx", "maple", "newt", "orca", "pike",
    "quill", "raven", "stone", "thorn", "umbra", "vole", "wren", "yak",
]


def generate_identity() -> str:
    import random
    return f"{random.choice(_ADJECTIVES)}-{random.choice(_NOUNS)}"


def resolve_identity(identity: str | None) -> str | None:
    if not identity:
        identity = generate_identity()
    return identity


def _encode_crockford(value: int, length: int) -> str:
    chars = ["0"] * length
    for index in range(length - 1, -1, -1):
        chars[index] = _CROCKFORD[value & 0x1F]
        value >>= 5
    return "".join(chars)


def _decode_crockford(value: str) -> int:
    decoded = 0
    for char in value.upper():
        decoded = (decoded << 5) | _CROCKFORD_DECODE[char]
    return decoded


def generate_ulid(now: datetime | None = None) -> str:
    timestamp = now or datetime.now(UTC)
    timestamp_ms = int(timestamp.timestamp() * 1000)
    entropy = int.from_bytes(secrets.token_bytes(10), "big")
    return _encode_crockford(timestamp_ms, 10) + _encode_crockford(entropy, 16)


def ulid_timestamp(launch_id: str) -> datetime:
    if len(launch_id) != 26:
        raise ValueError(f"Invalid ULID length: {launch_id}")
    timestamp_ms = _decode_crockford(launch_id[:10])
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)


def session_filename_from_launch_id(launch_id: str) -> str:
    timestamp = ulid_timestamp(launch_id)
    prefix = timestamp.strftime("%Y%m%d%H%M%S") + f"{int(timestamp.microsecond / 1000):03d}"
    return f"{prefix}-{launch_id}.json"


def build_session_record_path(project_dir: str | Path, tool: str, launch_id: str) -> Path:
    root = Path(project_dir).expanduser().resolve()
    return root / ".sc" / "sessions" / tool / session_filename_from_launch_id(launch_id)


def build_claude_session_record_path(project_dir: str | Path, launch_id: str) -> Path:
    return build_session_record_path(project_dir, "claude", launch_id)


def build_codex_session_record_path(project_dir: str | Path, launch_id: str) -> Path:
    return build_session_record_path(project_dir, "codex", launch_id)
