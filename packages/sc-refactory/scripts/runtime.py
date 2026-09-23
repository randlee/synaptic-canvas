#!/usr/bin/env python3
"""Shared runtime helpers for refactor scripts."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def find_repo_root(anchor: Path | None = None) -> Path:
    if anchor is not None:
        candidate = anchor.resolve()
        search = [candidate] + list(candidate.parents)
        for parent in search:
            if (parent / ".refactor" / "scripts").is_dir():
                return parent

    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return Path(root)
    except subprocess.CalledProcessError:
        return Path.cwd()


def resolve_oxigraph() -> Path | None:
    path = shutil.which("oxigraph")
    if path:
        return Path(path)

    candidates = [
        Path("/opt/homebrew/bin/oxigraph"),
        Path("/usr/local/bin/oxigraph"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def logs_dir(root: Path) -> Path:
    return root / ".refactor" / "logs"


def append_log(root: Path, log_name: str, message: str) -> None:
    log_dir = logs_dir(root)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_name
    timestamp = datetime.now(timezone.utc).isoformat()
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def append_json_log(root: Path, log_name: str, payload: dict) -> None:
    log_dir = logs_dir(root)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_name
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
