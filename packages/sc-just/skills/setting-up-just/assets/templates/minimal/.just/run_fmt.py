#!/usr/bin/env python3
# sc-just-template-version: 0.1.0
from __future__ import annotations

import sys
import tomllib

from task_runner import load_config
from task_runner import run_steps


def main(argv: list[str]) -> int:
    try:
        config = load_config()
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    fmt_config = config.get("fmt", {})
    steps_by_mode = fmt_config.get("steps", {})
    mode = argv[1] if len(argv) > 1 else fmt_config.get("default_mode", "check")
    steps = steps_by_mode.get(mode)
    if steps is None:
        valid = ", ".join(steps_by_mode.keys())
        print("unknown fmt mode:", mode, file=sys.stderr)
        print(f"expected one of: {valid}", file=sys.stderr)
        return 2
    return run_steps("fmt", steps)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
