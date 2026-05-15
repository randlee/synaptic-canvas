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
from typing import Iterable, NamedTuple

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


class SharedScriptMapping(NamedTuple):
    canonical: Path
    target: Path


def load_manifest_data(package_dir: Path) -> dict:
    manifest = package_dir / "manifest.yaml"
    if not manifest.exists() or not _YAML_AVAILABLE:
        return {}
    try:
        return yaml.safe_load(manifest.read_text()) or {}
    except Exception:
        return {}


def package_uses_scripts(package_dir: Path) -> bool:
    """Return True if the package manifest declares scripts artifacts."""
    data = load_manifest_data(package_dir)
    if not data:
        return True  # No manifest: assume scripts are used
    artifacts = data.get("artifacts", {})
    return bool(artifacts.get("scripts"))


def has_package_specific_shared(package_dir: Path) -> bool:
    """Check if package has migrated to package-specific shared module."""
    scripts_dir = package_dir / "scripts"
    if not scripts_dir.exists():
        return False

    # Look for any *_shared.py that's not sc_shared.py
    for script in scripts_dir.glob("*_shared.py"):
        if script.name != "sc_shared.py":
            return True
    return False


def explicit_shared_script_mappings(package_dir: Path, repo_root: Path) -> list[SharedScriptMapping]:
    data = load_manifest_data(package_dir)
    entries = data.get("shared_scripts")
    if not isinstance(entries, list):
        return []

    mappings: list[SharedScriptMapping] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        target = entry.get("target")
        if not isinstance(source, str) or not source.strip():
            continue
        if not isinstance(target, str) or not target.strip():
            continue
        mappings.append(
            SharedScriptMapping(
                canonical=(repo_root / source).resolve(),
                target=package_dir / target,
            )
        )
    return mappings


def shared_script_mappings(package_dir: Path, repo_root: Path, default_canonical: Path) -> list[SharedScriptMapping]:
    explicit = explicit_shared_script_mappings(package_dir, repo_root)
    if explicit:
        return explicit

    if not package_uses_scripts(package_dir):
        return []

    if has_package_specific_shared(package_dir):
        return []

    return [
        SharedScriptMapping(
            canonical=default_canonical.resolve(),
            target=package_dir / "scripts" / "sc_shared.py",
        )
    ]


def describe_mapping(package_dir: Path, target: Path) -> str:
    rel_target = target.relative_to(package_dir)
    return f"{package_dir.name}:{rel_target.as_posix()}"


def compare_shared_script(canonical: Path, packages_dir: Path) -> tuple[list[str], list[str], list[str]]:
    mismatched = []
    missing = []
    invalid_sources = []
    repo_root = packages_dir.parent

    for package_dir in iter_packages(packages_dir):
        if package_dir.name == "shared":
            continue

        for mapping in shared_script_mappings(package_dir, repo_root, canonical):
            if not mapping.canonical.exists():
                invalid_sources.append(f"{describe_mapping(package_dir, mapping.target)} -> {mapping.canonical}")
                continue

            canonical_bytes = read_bytes(mapping.canonical)
            if not mapping.target.exists():
                missing.append(describe_mapping(package_dir, mapping.target))
                continue
            if mapping.target.read_bytes() != canonical_bytes:
                mismatched.append(describe_mapping(package_dir, mapping.target))

    return mismatched, missing, invalid_sources


def sync_shared_script(canonical: Path, packages_dir: Path) -> list[str]:
    changed = []
    repo_root = packages_dir.parent

    for package_dir in iter_packages(packages_dir):
        if package_dir.name == "shared":
            continue

        for mapping in shared_script_mappings(package_dir, repo_root, canonical):
            if not mapping.canonical.exists():
                continue
            canonical_bytes = read_bytes(mapping.canonical)
            mapping.target.parent.mkdir(parents=True, exist_ok=True)
            if mapping.target.exists() and mapping.target.read_bytes() == canonical_bytes:
                continue
            mapping.target.write_bytes(canonical_bytes)
            changed.append(describe_mapping(package_dir, mapping.target))

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

    mismatched, missing, invalid_sources = compare_shared_script(args.canonical, args.packages_dir)
    initial_mismatched = list(mismatched)
    initial_missing = list(missing)
    initial_invalid_sources = list(invalid_sources)

    if args.check:
        changed = []
    else:
        changed = sync_shared_script(args.canonical, args.packages_dir)
        # Re-check to report any remaining mismatches after sync
        mismatched, missing, invalid_sources = compare_shared_script(args.canonical, args.packages_dir)

    issues = []
    if missing:
        issues.append(f"Missing shared script targets: {', '.join(missing)}")
    if mismatched:
        issues.append(f"Mismatched shared script targets: {', '.join(mismatched)}")
    if invalid_sources:
        issues.append(f"Missing shared script sources: {', '.join(invalid_sources)}")

    if changed:
        print("Synchronized shared scripts:")
        for mapping in changed:
            print(f"  - {mapping}")

    if issues:
        print("\nShared script validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    if not args.check and (changed or initial_mismatched or initial_missing or initial_invalid_sources):
        print("\nShared script validation failed: files were out of sync and were updated.")
        return 1

    print("Shared script validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
