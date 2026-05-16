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


def normalize_steps(value: list[str] | list[list[str]]) -> list[list[str]]:
    if value and isinstance(value[0], str):
        return [value]
    return value


def main(argv: list[str]) -> int:
    try:
        config = load_config()
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    fmt_config = config.get("fmt", {})
    steps_by_mode = fmt_config.get("steps") or fmt_config.get("commands", {})
    mode = argv[1] if len(argv) > 1 else fmt_config.get("default_mode", "check")
    steps = steps_by_mode.get(mode)
    if steps is None:
        valid = ", ".join(steps_by_mode.keys())
        print("unknown fmt mode:", mode, file=sys.stderr)
        print(f"expected one of: {valid}", file=sys.stderr)
        return 2
    normalized_steps = normalize_steps(steps)
    if not normalized_steps:
        print(f"fmt mode {mode!r} is not configured", file=sys.stderr)
        return 2
    for command in normalized_steps:
        completed = subprocess.run(command, cwd=repo_root())
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
