#!/usr/bin/env python3
"""Rebuild `.refactor/db` from committed rule files by reusing session_start."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild the local refactor DB")
    parser.add_argument("--repo-root", default=".")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    script = repo_root / ".refactor" / "scripts" / "session_start.py"
    result = subprocess.run(
        ["python3", str(script), "--mode", "startup"],
        cwd=repo_root,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
