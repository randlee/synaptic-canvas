#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from sc_manage_common import (
    any_artifact_installed,
    artifacts_from_manifest,
    default_sc_repo_path,
    list_manifests,
    manifest_scope,
    parse_manifest,
    read_json_stdin,
    resolve_repo_root,
    report_error,
    selected_targets,
    target_roots,
)


def main() -> int:
    params = read_json_stdin()
    try:
        targets = selected_targets(params)
    except ValueError as exc:
        return report_error("INPUT_INVALID", str(exc))
    sc_repo_path = Path(params.get("sc_repo_path", default_sc_repo_path()))

    repo_root = resolve_repo_root()

    packages: List[Dict[str, Any]] = []

    for manifest_path in list_manifests(sc_repo_path):
        manifest = parse_manifest(manifest_path)
        name = manifest.get("name")
        description = (manifest.get("description") or "").split("\n", 1)[0].strip()
        scope = manifest_scope(manifest)
        installed_by_target = {}
        for target in targets:
            artifacts = artifacts_from_manifest(manifest, target)
            global_dir, user_dir = target_roots(params, target)
            local_dir = repo_root / f".{target}" if repo_root else None
            local_installed = bool(local_dir and artifacts and any_artifact_installed(local_dir, artifacts))
            global_installed = bool(artifacts and (any_artifact_installed(global_dir, artifacts)
                                                  or any_artifact_installed(user_dir, artifacts)))
            installed_by_target[target] = ("both" if local_installed and global_installed else
                                           "local" if local_installed else "global" if global_installed else "no")
        states = set(installed_by_target.values())
        installed = next(iter(states)) if len(states) == 1 else "mixed"

        packages.append(
            {
                "name": name,
                "description": description,
                "installable_scopes": scope,
                "installed": installed,
                "installed_by_target": installed_by_target,
            }
        )

    print(
        json.dumps(
            {
                "success": True,
                "data": {"packages": sorted(packages, key=lambda p: p.get("name") or ""), "targets": targets},
                "error": None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
