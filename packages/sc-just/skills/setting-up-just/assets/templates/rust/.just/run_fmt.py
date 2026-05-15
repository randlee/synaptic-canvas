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

    fmt_config = config.get("fmt", {})
    commands = fmt_config.get("commands", {})
    mode = argv[1] if len(argv) > 1 else fmt_config.get("default_mode", "check")
    command = commands.get(mode)
    if command is None:
        valid = ", ".join(commands.keys())
        print("unknown fmt mode:", mode, file=sys.stderr)
        print(f"expected one of: {valid}", file=sys.stderr)
        return 2
    completed = subprocess.run(command, cwd=repo_root())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
