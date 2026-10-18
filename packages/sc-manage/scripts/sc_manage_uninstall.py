#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from sc_manage_common import (
    default_sc_repo_path,
    normalize_scope,
    parse_manifest,
    read_json_stdin,
    resolve_dest,
    run_uninstall,
    report_error,
    selected_targets,
    target_roots,
    valid_package,
)


def main() -> int:
    params = read_json_stdin()
    try:
        targets = selected_targets(params)
    except ValueError as exc:
        return report_error("INPUT_INVALID", str(exc))
    package = params.get("package")
    scope = params.get("scope")
    sc_repo_path = Path(params.get("sc_repo_path", default_sc_repo_path()))

    scope = normalize_scope(scope) if isinstance(scope, str) else scope

    if not valid_package(package) or scope not in {"local", "global", "user"}:
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
    if (install_scope == "local-only" and scope in {"global", "user"}) or (install_scope == "global-only" and scope == "local"):
        print(
            json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "SCOPE_NOT_ALLOWED",
                        "message": f"Package '{package}' does not allow {scope} uninstallation",
                        "recoverable": False,
                        "suggested_action": "Use --local scope",
                    },
                }
            )
        )
        return 1

    destinations = {}
    for target in targets:
        dest, err = resolve_dest(scope, *target_roots(params, target), target)
        if dest is None:
            return report_error("DEST_INVALID", err or "Failed to resolve destination")
        destinations[target] = dest
    if len({dest.resolve() for dest in destinations.values()}) != len(destinations):
        return report_error("DEST_INVALID", "Selected targets must use distinct destination directories")
    completed = []
    for target, dest in destinations.items():
        code, stdout, stderr = run_uninstall(sc_repo_path, package, dest, target)
        if code != 0:
            return report_error("UNINSTALL_FAILED", stderr.strip() or stdout.strip() or "Uninstall failed",
                                data={"completed_targets": completed, "failed_target": target})
        completed.append(target)

    print(
        json.dumps(
            {
                "success": True,
                "data": {"package": package, "scope": scope,
                         "dest": str(next(iter(destinations.values()))) if len(targets) == 1 else None,
                         "targets": targets, "destinations": {key: str(value) for key, value in destinations.items()}},
                "error": None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
