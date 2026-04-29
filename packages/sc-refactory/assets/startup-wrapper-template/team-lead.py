#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / ".refactor" / "scripts" / "session_start.py"
    args = ["python3", str(script), *sys.argv[1:]]
    return subprocess.call(args, cwd=repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
