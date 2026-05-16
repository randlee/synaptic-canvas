#!/usr/bin/env python3
# sc-just-template-version: 0.1.0
from __future__ import annotations

import sys
import tomllib

from task_runner import load_config
from task_runner import run_steps


def main() -> int:
    try:
        config = load_config()
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return run_steps("test", config.get("test", {}).get("steps", []))


if __name__ == "__main__":
    raise SystemExit(main())
