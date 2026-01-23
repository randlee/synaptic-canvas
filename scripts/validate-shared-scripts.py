#!/usr/bin/env python3
"""
Validate (and optionally sync) shared script across packages.

By default, this script syncs the shared file and fails if any package was out
of sync. Use --check for a read-only validation.

Usage:
  python3 scripts/validate-shared-scripts.py
  python3 scripts/validate-shared-scripts.py --check
"""

import argparse
import sys
from pathlib import Path
from typing import Iterable, Tuple


def iter_packages(packages_dir: Path) -> Iterable[Path]:
    for path in sorted(packages_dir.iterdir()):
        if path.is_dir() and not path.name.startswith("."):
            yield path


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def compare_shared_script(canonical: Path, packages_dir: Path) -> Tuple[list[str], list[str]]:
    mismatched = []
    missing = []
    canonical_bytes = read_bytes(canonical)

    for package_dir in iter_packages(packages_dir):
        if package_dir.name == "shared":
            continue
        target = package_dir / "scripts" / "sc_shared.py"
        if not target.exists():
            missing.append(package_dir.name)
            continue
        if target.read_bytes() != canonical_bytes:
            mismatched.append(package_dir.name)

    return mismatched, missing


def sync_shared_script(canonical: Path, packages_dir: Path) -> list[str]:
    changed = []
    canonical_bytes = read_bytes(canonical)

    for package_dir in iter_packages(packages_dir):
        if package_dir.name == "shared":
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
    parser = argparse.ArgumentParser(description="Validate shared scripts")
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
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check only; do not sync",
    )
    args = parser.parse_args()

    if not args.canonical.exists():
        print(f"Error: canonical shared script not found: {args.canonical}")
        return 1
    if not args.packages_dir.exists():
        print(f"Error: packages directory not found: {args.packages_dir}")
        return 1

    mismatched, missing = compare_shared_script(args.canonical, args.packages_dir)
    initial_mismatched = list(mismatched)
    initial_missing = list(missing)

    if args.check:
        changed = []
    else:
        changed = sync_shared_script(args.canonical, args.packages_dir)
        # Re-check to report any remaining mismatches after sync
        mismatched, missing = compare_shared_script(args.canonical, args.packages_dir)

    issues = []
    if missing:
        issues.append(f"Missing sc_shared.py: {', '.join(missing)}")
    if mismatched:
        issues.append(f"Mismatched sc_shared.py: {', '.join(mismatched)}")

    if changed:
        print("Synchronized sc_shared.py in:")
        for name in changed:
            print(f"  - {name}")

    if issues:
        print("\nShared script validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    if not args.check and (changed or initial_mismatched or initial_missing):
        print("\nShared script validation failed: files were out of sync and were updated.")
        return 1

    print("Shared script validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
