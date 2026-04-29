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
    """Return True if the package declares scripts in its manifest artifacts."""
    data = load_manifest_data(package_dir)
    if not data:
        return True  # no manifest — assume scripts needed (safe default)
    artifacts = data.get("artifacts", {})
    return bool(artifacts.get("scripts"))


def has_package_specific_shared(package_dir: Path) -> bool:
    scripts_dir = package_dir / "scripts"
    if not scripts_dir.exists():
        return False
    return any(script.name != "sc_shared.py" for script in scripts_dir.glob("*_shared.py"))


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
        print("Updated shared scripts:")
        for mapping in changed:
            print(f"  - {mapping}")
    else:
        print("All packages already synchronized")
    return 0


if __name__ == "__main__":
    sys.exit(main())
