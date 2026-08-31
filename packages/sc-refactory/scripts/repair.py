#!/usr/bin/env python3
"""Scripted local repair path for refactor skills."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from runtime import append_log, find_repo_root



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair local refactor skill environment")
    parser.add_argument(
        "--skill",
        default="refactor",
        choices=["refactor", "refactor-lookup", "refactor-write"],
    )
    return parser.parse_args()


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    args = parse_args()
    root = find_repo_root(Path(__file__))
    startup = root / ".refactor" / "scripts" / "session_start.py"
    preflight = root / ".refactor" / "scripts" / "preflight.py"
    append_log(root, "repair.log", f"start skill={args.skill}")

    if not startup.is_file() or not preflight.is_file():
        append_log(root, "repair.log", "failure missing startup or preflight script")
        print(
            "tools are not installed or working to use this skill. "
            "please read ./.refactor/docs/install-and-troubleshooting.md"
        )
        sys.exit(1)

    startup_result = run(
        ["python3", str(startup), "--mode", "startup"],
        cwd=root,
    )
    append_log(
        root,
        "repair.log",
        f"startup returncode={startup_result.returncode} stdout_lines={len(startup_result.stdout.splitlines())} stderr_lines={len(startup_result.stderr.splitlines())}",
    )
    if startup_result.returncode != 0:
        append_log(root, "repair.log", "failure startup returned non-zero")
        print(
            "tools are not installed or working to use this skill. "
            "please read ./.refactor/docs/install-and-troubleshooting.md"
        )
        sys.exit(1)

    preflight_result = run(
        ["python3", str(preflight), "--skill", args.skill],
        cwd=root,
    )
    append_log(
        root,
        "repair.log",
        f"preflight returncode={preflight_result.returncode} output='{preflight_result.stdout.strip()}'",
    )
    sys.stdout.write(preflight_result.stdout)
    if preflight_result.stderr:
        sys.stderr.write(preflight_result.stderr)
    sys.exit(preflight_result.returncode)


if __name__ == "__main__":
    main()
