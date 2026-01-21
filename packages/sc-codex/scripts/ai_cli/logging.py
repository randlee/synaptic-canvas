#!/usr/bin/env python3
"""Lightweight structured logging for ai_cli."""
from __future__ import annotations

import inspect
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _derive_package_name() -> str:
    env_name = os.getenv("AI_CLI_PACKAGE_NAME") or os.getenv("SC_PACKAGE_NAME")
    if env_name:
        return env_name.strip()

    candidates = [Path(sys.argv[0]).resolve(), Path(__file__).resolve()]
    for path in candidates:
        parts = path.parts
        if "packages" in parts:
            idx = parts.index("packages")
            if idx + 1 < len(parts):
                return parts[idx + 1]

    for frame in inspect.stack():
        frame_path = frame.filename
        if not frame_path:
            continue
        path = Path(frame_path).resolve()
        parts = path.parts
        if "packages" in parts:
            idx = parts.index("packages")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        name = path.name
        if name.startswith("sc_") and name.endswith(".py"):
            base = name[:-3]
            for suffix in ("_task", "_run", "_runner", "_script"):
                if base.endswith(suffix):
                    base = base[: -len(suffix)]
                    break
            return base.replace("_", "-")

    return "ai-cli"


def _default_log_dir() -> Path:
    package_name = _derive_package_name()
    return Path.cwd() / ".claude" / "state" / "logs" / package_name


def write_log(event: Dict[str, Any], log_dir: Optional[Path] = None) -> str:
    log_dir = log_dir or _default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    record = {
        "timestamp": ts,
        "pid": os.getpid(),
        **event,
    }
    fname = f"ai-cli-{ts.replace(':','').replace('-','').replace('T','_')}.json"
    path = log_dir / fname
    if path.exists():
        suffix = datetime.now(timezone.utc).strftime("%f")
        path = log_dir / f"{path.stem}-{suffix}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return str(path)
