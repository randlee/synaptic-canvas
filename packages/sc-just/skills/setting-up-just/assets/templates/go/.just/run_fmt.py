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


def fmt_paths(config: dict) -> list[str]:
    paths = config.get("fmt", {}).get("paths", ["."])
    return paths or ["."]


def run_check(paths: list[str]) -> int:
    completed = subprocess.run(
        ["gofmt", "-l", *paths],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="", file=sys.stderr)
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode

    output = completed.stdout.strip()
    if not output:
        return 0

    print(output)
    return 1


def run_write(paths: list[str]) -> int:
    completed = subprocess.run(["gofmt", "-w", *paths], cwd=repo_root(), check=False)
    return completed.returncode


def main(argv: list[str]) -> int:
    try:
        config = load_config()
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    fmt_config = config.get("fmt", {})
    mode = argv[1] if len(argv) > 1 else fmt_config.get("default_mode", "check")
    paths = fmt_paths(config)

    if mode == "check":
        return run_check(paths)
    if mode in {"write", "apply"}:
        return run_write(paths)

    print("unknown fmt mode:", mode, file=sys.stderr)
    print("expected one of: check, write, apply", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
