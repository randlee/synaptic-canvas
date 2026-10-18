#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

from sc_manage_common import TARGETS, report_error


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def main() -> int:
    parser = Parser(description="Manage Synaptic Canvas packages for explicit agent targets.", allow_abbrev=False)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--list", action="store_true")
    actions.add_argument("--install", metavar="PACKAGE")
    actions.add_argument("--uninstall", metavar="PACKAGE")
    actions.add_argument("--docs", "--doc", metavar="PACKAGE")
    scopes = parser.add_mutually_exclusive_group()
    scopes.add_argument("--local", "--project", dest="scope", action="store_const", const="local")
    scopes.add_argument("--global", dest="scope", action="store_const", const="global")
    scopes.add_argument("--user", dest="scope", action="store_const", const="user")
    for target in TARGETS:
        parser.add_argument(f"--{target}", action="store_true")
    try:
        argv = sys.argv[1:]
        # Accept normal argv and a single quoted slash-command $ARGUMENTS
        # string without discarding quoting within ordinary argv values.
        if len(argv) == 1:
            argv = shlex.split(argv[0])
        args = parser.parse_args(argv)
        targets = [target for target in TARGETS if getattr(args, target)] or ["claude"]
        if (args.install or args.uninstall) and not args.scope:
            raise ValueError("Install/uninstall requires --local/--project, --global, or --user")
        if args.docs and (args.scope or any(getattr(args, target) for target in TARGETS)):
            raise ValueError("--docs does not accept scope or target flags")
        if args.scope and not (args.install or args.uninstall):
            raise ValueError("Scope flags apply to install/uninstall only")
    except ValueError as exc:
        return report_error("INPUT_INVALID", str(exc))

    payload = {"targets": targets}
    if args.install or args.uninstall:
        script = "sc_manage_install.py" if args.install else "sc_manage_uninstall.py"
        payload.update(package=args.install or args.uninstall, scope=args.scope)
    elif args.docs:
        script = "sc_manage_docs.py"
        payload = {"package": args.docs}
    else:
        script = "sc_manage_list.py"
    cmd = [sys.executable or "python3", str(Path(__file__).resolve().parent / script)]
    return subprocess.run(cmd, input=json.dumps(payload), text=True).returncode


if __name__ == "__main__":
    raise SystemExit(main())
