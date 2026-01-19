"""Lightweight structured logging for ai_cli."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _default_log_dir() -> Path:
    return Path.cwd() / ".claude" / "state" / "logs" / "ai-cli"


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
