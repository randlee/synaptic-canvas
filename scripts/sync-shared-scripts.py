#!/usr/bin/env python3
"""
Sync shared script into every package's scripts directory.

Usage:
  python3 scripts/sync-shared-scripts.py
  python3 scripts/sync-shared-scripts.py --packages-dir packages
"""

import argparse
import sys
from pathlib import Path
from typing import Iterable

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


def iter_packages(packages_dir: Path) -> Iterable[Path]:
    for path in sorted(packages_dir.iterdir()):
        if path.is_dir() and not path.name.startswith("."):
            yield path


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def package_uses_scripts(package_dir: Path) -> bool:
    """Return True if the package declares scripts in its manifest artifacts."""
    manifest = package_dir / "manifest.yaml"
    if not manifest.exists():
        return True  # no manifest — assume scripts needed (safe default)
    if not _YAML_AVAILABLE:
        return True  # can't parse — assume scripts needed
    try:
        data = yaml.safe_load(manifest.read_text())
        artifacts = (data or {}).get("artifacts", {})
        return bool(artifacts.get("scripts"))
    except Exception:
        return True  # parse error — assume scripts needed


def sync_shared_script(canonical: Path, packages_dir: Path) -> list[str]:
    changed = []
    canonical_bytes = read_bytes(canonical)

    for package_dir in iter_packages(packages_dir):
        if package_dir.name == "shared":
            continue
        if not package_uses_scripts(package_dir):
            continue
        scripts_dir = package_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        target = scripts_dir / "sc_shared.py"
        if target.exists() and target.read_bytes() == canonical_bytes:
            continue
        target.write_bytes(canonical_bytes)
        changed.append(package_dir.name)

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync shared script into packages")
    parser.add_argument(
        "--packages-dir",
        type=Path,
        default=Path("packages"),
        help="Path to packages directory (default: packages)",
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=Path("packages/shared/scripts/sc_shared.py"),
        help="Path to canonical shared script",
    )
    args = parser.parse_args()

    if not args.canonical.exists():
        print(f"Error: canonical shared script not found: {args.canonical}")
        return 1
    if not args.packages_dir.exists():
        print(f"Error: packages directory not found: {args.packages_dir}")
        return 1

    changed = sync_shared_script(args.canonical, args.packages_dir)
    if changed:
        print("Updated sc_shared.py in:")
        for name in changed:
            print(f"  - {name}")
    else:
        print("All packages already synchronized")
    return 0


if __name__ == "__main__":
    sys.exit(main())
