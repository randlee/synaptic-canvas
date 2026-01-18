#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from sc_manage_common import default_sc_repo_path, parse_manifest, read_json_stdin


def main() -> int:
    params = read_json_stdin()
    package = params.get("package")
    sc_repo_path = Path(params.get("sc_repo_path", default_sc_repo_path()))

    if not package:
        print(
            json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "INPUT_INVALID",
                        "message": "Missing package",
                        "recoverable": True,
                        "suggested_action": "Provide a package name",
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
    readme_path = sc_repo_path / "packages" / package / "README.md"
    if not readme_path.exists():
        print(
            json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "README_NOT_FOUND",
                        "message": f"README not found for '{package}'",
                        "recoverable": False,
                        "suggested_action": "Open package directory manually",
                    },
                }
            )
        )
        return 1

    size_bytes = readme_path.stat().st_size
    print(
        json.dumps(
            {
                "success": True,
                "data": {
                    "package": manifest.get("name"),
                    "readme_path": str(readme_path),
                    "size_bytes": size_bytes,
                },
                "error": None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
