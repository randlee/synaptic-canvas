#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from sc_manage_common import (
    default_global_claude_dir,
    default_user_claude_dir,
    default_sc_repo_path,
    normalize_scope,
    parse_manifest,
    read_json_stdin,
    resolve_dest,
    run_install,
)


def main() -> int:
    params = read_json_stdin()
    package = params.get("package")
    scope = params.get("scope")
    sc_repo_path = Path(params.get("sc_repo_path", default_sc_repo_path()))
    global_claude_dir = Path(params.get("global_claude_dir", default_global_claude_dir()))
    user_claude_dir = Path(params.get("user_claude_dir", default_user_claude_dir()))

    scope = normalize_scope(scope) if isinstance(scope, str) else scope

    if not package or scope not in {"local", "global", "user"}:
        print(
            json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "INPUT_INVALID",
                        "message": "Missing package or scope",
                        "recoverable": True,
                        "suggested_action": "Provide package and scope (local|project|global|user)",
                    },
                }
            )
        )
        return 1

    manifest_path = sc_repo_path / "packages" / package / "manifest.yaml"
    if not manifest_path.exists():
        print(
            json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "PACKAGE_NOT_FOUND",
                        "message": f"Package '{package}' not found",
                        "recoverable": False,
                        "suggested_action": "Use --list to see available packages",
                    },
                }
            )
        )
        return 1

    manifest = parse_manifest(manifest_path)
    install_scope = (manifest.get("install") or {}).get("scope", "both")
    if install_scope == "local-only" and scope in {"global", "user"}:
        print(
            json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "SCOPE_NOT_ALLOWED",
                        "message": f"Package '{package}' may only be installed locally",
                        "recoverable": False,
                        "suggested_action": "Use --local scope",
                    },
                }
            )
        )
        return 1

    dest, err = resolve_dest(scope, global_claude_dir, user_claude_dir)
    if dest is None:
        print(
            json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "DEST_INVALID",
                        "message": err or "Failed to resolve destination",
                        "recoverable": False,
                        "suggested_action": "Run inside a git repo for local installs",
                    },
                }
            )
        )
        return 1

    code, stdout, stderr = run_install(sc_repo_path, package, dest)
    if code != 0:
        print(
            json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "INSTALL_FAILED",
                        "message": stderr.strip() or stdout.strip() or "Install failed",
                        "recoverable": True,
                        "suggested_action": "Check permissions and retry",
                    },
                }
            )
        )
        return 1

    print(
        json.dumps(
            {
                "success": True,
                "data": {"package": package, "scope": scope, "dest": str(dest)},
                "error": None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
