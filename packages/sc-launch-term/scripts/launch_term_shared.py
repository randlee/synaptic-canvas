#!/usr/bin/env python3
"""Shared helpers for sc-launch-term."""

from __future__ import annotations

import os
import shlex
import sys


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


def resolve_identity(identity: str | None) -> str | None:
    team = os.environ.get("ATM_TEAM", "").strip()
    if team and not identity:
        print(
            f"ATM_TEAM is set to '{team}'; supply --identity <name> for this launch",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return identity
