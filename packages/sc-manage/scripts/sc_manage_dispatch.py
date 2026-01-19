#!/usr/bin/env python3
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import subprocess


def main() -> int:
    raw_args = " ".join(sys.argv[1:]).strip()
    print(f"python3 scripts/sc_manage_dispatch.py '{raw_args}'" if raw_args else "python3 scripts/sc_manage_dispatch.py")

    tokens = shlex.split(raw_args) if raw_args else []

    wants_list = "--list" in tokens or not tokens
    wants_install = "--install" in tokens
    wants_uninstall = "--uninstall" in tokens
    wants_docs = "--docs" in tokens or "--doc" in tokens

    def _get_flag_value(flag: str) -> str | None:
        if flag in tokens:
            idx = tokens.index(flag)
            if idx + 1 < len(tokens):
                return tokens[idx + 1]
        return None

    scope = (
        "local"
        if "--local" in tokens or "--project" in tokens
        else "user"
        if "--user" in tokens
        else "global"
        if "--global" in tokens
        else None
    )

    script_dir = Path(__file__).resolve().parent
    python = sys.executable or "python3"

    def _run(script: str, payload: Dict[str, str]) -> int:
        cmd = [python, str(script_dir / script)]
        proc = subprocess.run(cmd, input=json.dumps(payload), text=True)
        return proc.returncode

    if wants_install:
        package = _get_flag_value("--install")
        if not package or not scope:
            print("Install requires --install <package> and --local|--project|--global|--user")
            return 0
        return _run("sc_manage_install.py", {"package": package, "scope": scope})

    if wants_uninstall:
        package = _get_flag_value("--uninstall")
        if not package or not scope:
            print("Uninstall requires --uninstall <package> and --local|--project|--global|--user")
            return 0
        return _run("sc_manage_uninstall.py", {"package": package, "scope": scope})

    if wants_docs:
        package = _get_flag_value("--docs") or _get_flag_value("--doc")
        if not package:
            print("Docs requires --docs <package>")
            return 0
        return _run("sc_manage_docs.py", {"package": package})

    if wants_list:
        return _run("sc_manage_list.py", {})

    print("No supported flags provided. Use --list, --install, --uninstall, or --docs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
