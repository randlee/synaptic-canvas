#!/usr/bin/env python3
# sc-just-template-version: 0.1.0
from __future__ import annotations

import sys
import tomllib

from task_runner import load_config
from task_runner import render_help


def main() -> int:
    try:
        print(render_help(load_config()), end="")
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
