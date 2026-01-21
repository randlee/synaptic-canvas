#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from sc_manage_common import (
    any_artifact_installed,
    artifacts_from_manifest,
    default_global_claude_dir,
    default_sc_repo_path,
    list_manifests,
    manifest_scope,
    parse_manifest,
    read_json_stdin,
    resolve_repo_root,
)


def main() -> int:
    params = read_json_stdin()
    sc_repo_path = Path(params.get("sc_repo_path", default_sc_repo_path()))
    global_claude_dir = Path(params.get("global_claude_dir", default_global_claude_dir()))

    repo_root = resolve_repo_root()
    local_claude_dir = repo_root / ".claude" if repo_root else None

    packages: List[Dict[str, Any]] = []

    for manifest_path in list_manifests(sc_repo_path):
        manifest = parse_manifest(manifest_path)
        name = manifest.get("name")
        description = (manifest.get("description") or "").split("\n", 1)[0].strip()
        scope = manifest_scope(manifest)
        artifacts = artifacts_from_manifest(manifest)

        local_installed = False
        global_installed = False
        if local_claude_dir and artifacts:
            local_installed = any_artifact_installed(local_claude_dir, artifacts)
        if artifacts:
            global_installed = any_artifact_installed(global_claude_dir, artifacts)

        if local_installed and global_installed:
            installed = "both"
        elif local_installed:
            installed = "local"
        elif global_installed:
            installed = "global"
        else:
            installed = "no"

        packages.append(
            {
                "name": name,
                "description": description,
                "installable_scopes": scope,
                "installed": installed,
            }
        )

    print(
        json.dumps(
            {
                "success": True,
                "data": {"packages": sorted(packages, key=lambda p: p.get("name") or "")},
                "error": None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
