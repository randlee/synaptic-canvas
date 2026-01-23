#!/usr/bin/env python3
"""
set-package-version.py - Single source of truth for version management.

Sets package versions across all artifacts and regenerates registry files.

Usage:
    python3 scripts/set-package-version.py <package> <version>
    python3 scripts/set-package-version.py --all <version>
    python3 scripts/set-package-version.py --all --marketplace <version>

Examples:
    python3 scripts/set-package-version.py sc-delay-tasks 0.8.0
    python3 scripts/set-package-version.py --all 0.8.0
    python3 scripts/set-package-version.py --all --marketplace 0.8.0

Options:
    <package>       Package name to update (e.g., sc-delay-tasks)
    <version>       Target version in SemVer format (X.Y.Z)
    --all           Update all packages to the same version
    --marketplace   Also update marketplace platform version (version.yaml)
    --dry-run       Show what would be changed without making changes
    --force         Allow version decrement (use with caution)

Files updated per package:
    - packages/<package>/manifest.yaml
    - packages/<package>/.claude-plugin/plugin.json
    - packages/<package>/commands/*.md
    - packages/<package>/skills/*/SKILL.md
    - packages/<package>/agents/*.md

Registry files regenerated:
    - .claude-plugin/marketplace.json
    - .claude-plugin/registry.json
    - docs/registries/nuget/registry.json

If --marketplace:
    - version.yaml
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml


# ============================================================================
# Version Utilities
# ============================================================================


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse semver string to tuple."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version)
    if not match:
        raise ValueError(f"Invalid version format: {version}. Must be X.Y.Z")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def version_to_string(version: tuple[int, int, int]) -> str:
    """Convert version tuple to string."""
    return f"{version[0]}.{version[1]}.{version[2]}"


def compare_versions(v1: str, v2: str) -> int:
    """Compare two versions. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
    t1 = parse_version(v1)
    t2 = parse_version(v2)
    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    return 0


# ============================================================================
# File Update Functions
# ============================================================================


def update_yaml_version(filepath: Path, new_version: str, dry_run: bool = False) -> bool:
    """Update version in YAML file (manifest or frontmatter)."""
    if not filepath.exists():
        return False

    content = filepath.read_text(encoding='utf-8')

    # Match version line (quoted or unquoted)
    new_content = re.sub(
        r'(version:\s*)"?([0-9]+\.[0-9]+\.[0-9]+)"?',
        lambda m: f'{m.group(1)}"{new_version}"' if '"' in m.group(0) else f'{m.group(1)}{new_version}',
        content,
        count=1
    )

    if new_content == content:
        return False

    if not dry_run:
        filepath.write_text(new_content, encoding='utf-8')

    return True


def update_json_version(filepath: Path, new_version: str, dry_run: bool = False) -> bool:
    """Update version field in JSON file."""
    if not filepath.exists():
        return False

    content = filepath.read_text(encoding='utf-8')
    data = json.loads(content)

    if 'version' not in data or data['version'] == new_version:
        return False

    data['version'] = new_version

    if not dry_run:
        filepath.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

    return True


def get_current_version(manifest_path: Path) -> Optional[str]:
    """Extract current version from manifest.yaml."""
    if not manifest_path.exists():
        return None

    content = manifest_path.read_text(encoding='utf-8')
    match = re.search(r'version:\s*"?([0-9]+\.[0-9]+\.[0-9]+)"?', content)
    return match.group(1) if match else None


# ============================================================================
# Package Update
# ============================================================================


@dataclass
class UpdateResult:
    """Result of updating a package."""
    package_name: str
    new_version: str
    old_version: Optional[str] = None
    files_updated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: bool = False


def update_package(
    repo_root: Path,
    package_name: str,
    new_version: str,
    dry_run: bool = False,
    force: bool = False
) -> UpdateResult:
    """Update all version references in a package."""
    result = UpdateResult(package_name=package_name, new_version=new_version)
    package_dir = repo_root / 'packages' / package_name

    if not package_dir.exists():
        result.errors.append(f"Package directory not found: {package_dir}")
        return result

    # Get current version
    manifest_path = package_dir / 'manifest.yaml'
    result.old_version = get_current_version(manifest_path)

    # Check for version decrement
    if result.old_version and not force:
        if compare_versions(new_version, result.old_version) < 0:
            result.errors.append(
                f"Version decrement not allowed: {result.old_version} -> {new_version}. "
                "Use --force to override."
            )
            return result

    # Skip if already at target version
    if result.old_version == new_version:
        result.skipped = True
        return result

    # Update manifest.yaml
    if update_yaml_version(manifest_path, new_version, dry_run):
        result.files_updated.append(str(manifest_path.relative_to(repo_root)))

    # Update plugin.json
    plugin_json = package_dir / '.claude-plugin' / 'plugin.json'
    if update_json_version(plugin_json, new_version, dry_run):
        result.files_updated.append(str(plugin_json.relative_to(repo_root)))

    # Update commands
    commands_dir = package_dir / 'commands'
    if commands_dir.exists():
        for cmd_file in commands_dir.glob('*.md'):
            if update_yaml_version(cmd_file, new_version, dry_run):
                result.files_updated.append(str(cmd_file.relative_to(repo_root)))

    # Update skills
    skills_dir = package_dir / 'skills'
    if skills_dir.exists():
        for skill_file in skills_dir.glob('*/SKILL.md'):
            if update_yaml_version(skill_file, new_version, dry_run):
                result.files_updated.append(str(skill_file.relative_to(repo_root)))

    # Update agents
    agents_dir = package_dir / 'agents'
    if agents_dir.exists():
        for agent_file in agents_dir.glob('*.md'):
            if update_yaml_version(agent_file, new_version, dry_run):
                result.files_updated.append(str(agent_file.relative_to(repo_root)))

    return result


# ============================================================================
# Registry Regeneration
# ============================================================================


def count_artifacts(package_dir: Path) -> dict[str, int]:
    """Count artifacts in a package directory."""
    counts = {
        'commands': 0,
        'skills': 0,
        'agents': 0,
        'scripts': 0,
        'schemas': 0
    }

    commands_dir = package_dir / 'commands'
    if commands_dir.exists():
        counts['commands'] = len(list(commands_dir.glob('*.md')))

    skills_dir = package_dir / 'skills'
    if skills_dir.exists():
        counts['skills'] = len(list(skills_dir.glob('*/SKILL.md')))

    agents_dir = package_dir / 'agents'
    if agents_dir.exists():
        counts['agents'] = len(list(agents_dir.glob('*.md')))

    scripts_dir = package_dir / 'scripts'
    if scripts_dir.exists():
        counts['scripts'] = len(list(scripts_dir.glob('*.py'))) + len(list(scripts_dir.glob('*.sh')))

    schemas_dir = package_dir / 'schemas'
    if schemas_dir.exists():
        counts['schemas'] = len(list(schemas_dir.glob('*.json')))

    return counts


def load_manifest(package_dir: Path) -> Optional[dict]:
    """Load and parse manifest.yaml."""
    manifest_path = package_dir / 'manifest.yaml'
    if not manifest_path.exists():
        return None

    with open(manifest_path) as f:
        return yaml.safe_load(f)


def regenerate_marketplace_json(repo_root: Path, dry_run: bool = False) -> list[str]:
    """Regenerate .claude-plugin/marketplace.json from package manifests."""
    updated_files = []
    marketplace_path = repo_root / '.claude-plugin' / 'marketplace.json'

    if not marketplace_path.exists():
        return updated_files

    with open(marketplace_path) as f:
        marketplace = json.load(f)

    packages_dir = repo_root / 'packages'

    # Get marketplace version from first package or keep existing
    first_manifest = None
    for pkg_dir in sorted(packages_dir.iterdir()):
        if not pkg_dir.is_dir() or pkg_dir.name == "shared":
            continue
        manifest = load_manifest(pkg_dir)
        if manifest:
            first_manifest = manifest
            break

    if first_manifest:
        marketplace['metadata']['version'] = first_manifest.get('version', marketplace['metadata'].get('version'))

    # Update each plugin entry
    for plugin in marketplace.get('plugins', []):
        pkg_name = plugin.get('name')
        if not pkg_name:
            continue

        pkg_dir = packages_dir / pkg_name
        manifest = load_manifest(pkg_dir)

        if manifest:
            plugin['version'] = manifest.get('version', plugin.get('version'))
            plugin['description'] = manifest.get('description', plugin.get('description', ''))
            plugin['author'] = manifest.get('author', plugin.get('author', ''))
            plugin['license'] = manifest.get('license', plugin.get('license', 'MIT'))

    if not dry_run:
        with open(marketplace_path, 'w') as f:
            json.dump(marketplace, f, indent=2)
            f.write('\n')

    updated_files.append(str(marketplace_path.relative_to(repo_root)))
    return updated_files


def regenerate_registry_json(repo_root: Path, dry_run: bool = False) -> list[str]:
    """Regenerate .claude-plugin/registry.json from package manifests."""
    updated_files = []
    registry_path = repo_root / '.claude-plugin' / 'registry.json'

    packages_dir = repo_root / 'packages'
    packages = []
    totals = {'commands': 0, 'skills': 0, 'agents': 0, 'scripts': 0, 'schemas': 0}
    marketplace_version = None

    for pkg_dir in sorted(packages_dir.iterdir()):
        if not pkg_dir.is_dir() or pkg_dir.name == "shared":
            continue

        manifest = load_manifest(pkg_dir)
        if not manifest:
            continue

        if marketplace_version is None:
            marketplace_version = manifest.get('version')

        counts = count_artifacts(pkg_dir)
        for key in totals:
            totals[key] += counts[key]

        packages.append({
            'name': manifest.get('name', pkg_dir.name),
            'version': manifest.get('version', '0.0.0'),
            'description': manifest.get('description', ''),
            'author': manifest.get('author', ''),
            'license': manifest.get('license', 'MIT'),
            'keywords': manifest.get('keywords', []),
            'category': manifest.get('category', 'tools'),
            'artifacts': counts,
            'lastUpdated': datetime.now(timezone.utc).isoformat()
        })

    registry = {
        'name': 'synaptic-canvas',
        'version': marketplace_version or '0.0.0',
        'description': 'A marketplace for Claude Code skills',
        'author': {'name': 'randlee'},
        'packages': packages,
        'metadata': {
            'totalPackages': len(packages),
            'totalCommands': totals['commands'],
            'totalSkills': totals['skills'],
            'totalAgents': totals['agents'],
            'totalScripts': totals['scripts'],
            'totalSchemas': totals['schemas']
        },
        'generated': datetime.now(timezone.utc).isoformat(),
        'lastUpdated': datetime.now(timezone.utc).isoformat()
    }

    if not dry_run:
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
            f.write('\n')

    updated_files.append(str(registry_path.relative_to(repo_root)))
    return updated_files


def regenerate_nuget_registry(repo_root: Path, dry_run: bool = False) -> list[str]:
    """Regenerate docs/registries/nuget/registry.json from package manifests."""
    updated_files = []
    registry_path = repo_root / 'docs' / 'registries' / 'nuget' / 'registry.json'

    if not registry_path.exists():
        return updated_files

    with open(registry_path) as f:
        registry = json.load(f)

    packages_dir = repo_root / 'packages'
    marketplace_version = None

    # Update each package in the registry
    for pkg_dir in sorted(packages_dir.iterdir()):
        if not pkg_dir.is_dir() or pkg_dir.name == "shared":
            continue

        manifest = load_manifest(pkg_dir)
        if not manifest:
            continue

        pkg_name = manifest.get('name', pkg_dir.name)

        if marketplace_version is None:
            marketplace_version = manifest.get('version')

        if pkg_name in registry.get('packages', {}):
            pkg_entry = registry['packages'][pkg_name]
            pkg_entry['version'] = manifest.get('version', pkg_entry.get('version'))
            pkg_entry['description'] = manifest.get('description', pkg_entry.get('description', ''))

            counts = count_artifacts(pkg_dir)
            pkg_entry['artifacts'] = counts
            pkg_entry['lastUpdated'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Update marketplace version
    if marketplace_version and 'marketplace' in registry:
        registry['marketplace']['version'] = marketplace_version

    # Update generated timestamp
    registry['generated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    if not dry_run:
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
            f.write('\n')

    updated_files.append(str(registry_path.relative_to(repo_root)))
    return updated_files


def update_marketplace_version(repo_root: Path, new_version: str, dry_run: bool = False) -> list[str]:
    """Update version.yaml with new marketplace version."""
    updated_files = []
    version_path = repo_root / 'version.yaml'

    if not version_path.exists():
        return updated_files

    content = version_path.read_text(encoding='utf-8')

    # Update version line
    new_content = re.sub(
        r'(version:\s*)"?([0-9]+\.[0-9]+\.[0-9]+)"?',
        f'version: "{new_version}"',
        content
    )

    if new_content != content:
        if not dry_run:
            version_path.write_text(new_content, encoding='utf-8')
        updated_files.append('version.yaml')

    return updated_files


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description='Set package versions and regenerate registries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('package', nargs='?', help='Package name to update')
    parser.add_argument('version', nargs='?', help='Target version (X.Y.Z)')
    parser.add_argument('--all', action='store_true', help='Update all packages')
    parser.add_argument('--marketplace', action='store_true',
                       help='Also update marketplace platform version')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show changes without applying')
    parser.add_argument('--force', action='store_true',
                       help='Allow version decrement')

    args = parser.parse_args()

    # Validate arguments
    if args.all:
        if not args.version and not args.package:
            print("Error: Version required with --all")
            sys.exit(1)
        version = args.version or args.package  # Support: --all 0.8.0
    else:
        if not args.package or not args.version:
            print("Error: Package name and version required")
            print("Usage: set-package-version.py <package> <version>")
            print("       set-package-version.py --all <version>")
            sys.exit(1)
        version = args.version

    # Validate version format
    try:
        parse_version(version)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Find repo root
    repo_root = Path(__file__).parent.parent
    packages_dir = repo_root / 'packages'

    if not packages_dir.exists():
        print(f"Error: Packages directory not found: {packages_dir}")
        sys.exit(1)

    # Determine packages to update
    if args.all:
        package_names = [
            d.name for d in packages_dir.iterdir() if d.is_dir() and d.name != "shared"
        ]
    else:
        package_names = [args.package]

    # Update packages
    results = []
    total_files = 0
    has_errors = False

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Setting version to {version}\n")
    print("=" * 60)

    for pkg_name in sorted(package_names):
        result = update_package(repo_root, pkg_name, version, args.dry_run, args.force)
        results.append(result)

        if result.errors:
            has_errors = True
            print(f"\n{pkg_name}: ERROR")
            for error in result.errors:
                print(f"  ✗ {error}")
        elif result.skipped:
            print(f"\n{pkg_name}: already at {version} (skipped)")
        else:
            print(f"\n{pkg_name}: {result.old_version} -> {version}")
            for f in result.files_updated:
                print(f"  ✓ {f}")
            total_files += len(result.files_updated)

    if has_errors:
        print("\n" + "=" * 60)
        print("Errors occurred. Registry files not updated.")
        sys.exit(1)

    # Regenerate registry files
    print("\n" + "=" * 60)
    print("\nRegenerating registry files...")

    registry_files = []
    registry_files.extend(regenerate_marketplace_json(repo_root, args.dry_run))
    registry_files.extend(regenerate_registry_json(repo_root, args.dry_run))
    registry_files.extend(regenerate_nuget_registry(repo_root, args.dry_run))

    for f in registry_files:
        print(f"  ✓ {f}")
    total_files += len(registry_files)

    # Update marketplace version if requested
    if args.marketplace:
        print("\nUpdating marketplace platform version...")
        marketplace_files = update_marketplace_version(repo_root, version, args.dry_run)
        for f in marketplace_files:
            print(f"  ✓ {f}")
        total_files += len(marketplace_files)

    # Summary
    print("\n" + "=" * 60)
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Packages updated: {len([r for r in results if not r.skipped and not r.errors])}")
    print(f"  Packages skipped: {len([r for r in results if r.skipped])}")
    print(f"  Total files modified: {total_files}")

    if args.dry_run:
        print("\nNo changes made (dry run). Remove --dry-run to apply changes.")
    else:
        print("\nDone! Run validation to verify:")
        print("  python3 scripts/validate-all.py")


if __name__ == '__main__':
    main()
