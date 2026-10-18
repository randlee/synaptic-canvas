#!/usr/bin/env python3
"""Generate/check the curated native Codex catalog from package manifests.

Only packages with verified host-independent entry points are advertised here.
Run after changing a selected package's metadata; --check is read-only for CI.
"""

import argparse
import json
from pathlib import Path

import yaml


PACKAGES = ("sc-manage", "sc-gh-stack")


def expected_files(root: Path) -> dict[Path, dict]:
    plugins = []
    files = {}
    for name in PACKAGES:
        package = root / "packages" / name
        manifest = yaml.safe_load((package / "manifest.yaml").read_text())
        if manifest["name"] != name or not list((package / "skills").glob("*/SKILL.md")):
            raise ValueError(f"Invalid Codex skill package: {name}")
        files[package / "plugin.json"] = {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": name,
            "version": manifest["version"],
            "description": manifest["description"].strip(),
            "author": {"name": str(manifest["author"])},
            "license": manifest["license"],
        }
        plugins.append({
            "name": name,
            "source": {"source": "local", "path": f"./packages/{name}"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        })
    files[root / ".agents/plugins/marketplace.json"] = {
        "name": "synaptic-canvas",
        "interface": {"displayName": "Synaptic Canvas"},
        "plugins": plugins,
    }
    return files


def sync(root: Path, *, check: bool) -> list[str]:
    changed = []
    for path, data in expected_files(root).items():
        expected = json.dumps(data, indent=2) + "\n"
        if not path.is_file() or path.read_text() != expected:
            changed.append(str(path.relative_to(root)))
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(expected)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = sync(Path(__file__).resolve().parents[1], check=args.check)
    for path in changed:
        print(f"{'OUT OF DATE' if args.check else 'Updated'}: {path}")
    return int(args.check and bool(changed))


if __name__ == "__main__":
    raise SystemExit(main())
