#!/usr/bin/env python3
# sc-just-template-version: 0.1.0
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tomllib


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config() -> dict:
    path = repo_root() / ".just" / "config.toml"
    if not path.exists():
        raise FileNotFoundError(f"missing config file: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    try:
        config = load_config()
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    lint_config = config.get("lint", {})
    targets = lint_config.get("steps_by_target") or lint_config.get("targets", {})
    target = argv[1] if len(argv) > 1 else lint_config.get("default_target", "all")
    commands = targets.get(target)
    if commands is None:
        valid = ", ".join(targets.keys())
        print("unknown lint target:", target, file=sys.stderr)
        print(f"expected one of: {valid}", file=sys.stderr)
        return 2
    if not commands:
        print(f"lint target {target!r} is not configured", file=sys.stderr)
        return 2

    for command in commands:
        completed = subprocess.run(command, cwd=repo_root())
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
