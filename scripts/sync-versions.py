#!/usr/bin/env python3
"""
sync-versions.py - Synchronize version numbers across package artifacts

Usage:
  python3 scripts/sync-versions.py --package <name> --version <version> [--commit]
  python3 scripts/sync-versions.py --marketplace --version <version> [--commit]
  python3 scripts/sync-versions.py --all --version <version> [--commit]

Options:
  --package NAME       Update version for specific package
  --marketplace        Update marketplace platform version (version.yaml)
  --all                Update all packages to same version
  --version VERSION    Target version (SemVer: X.Y.Z)
  --commit             Create git commit after update
  --dry-run            Show changes without applying

Syncs versions in:
  - Package manifest (manifest.yaml)
  - All commands (commands/*.md)
  - All skills (skills/*/SKILL.md)
  - All agents (agents/*.md)
"""

import argparse
import os
import re
import sys
import subprocess
from pathlib import Path


class VersionSyncer:
    """Synchronize versions across a package."""

    def __init__(self, repo_root: str = None):
        """Initialize with repo root."""
        if repo_root is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.repo_root = repo_root
        self.changes = []

    def validate_version(self, version: str) -> bool:
        """Validate semantic version format."""
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))

    def extract_version(self, filepath: str) -> str:
        """Extract version from YAML frontmatter or manifest."""
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    if line.startswith('version:'):
                        # Extract quoted or unquoted version
                        match = re.search(r'version:\s*"?([^"\n]+)"?', line)
                        if match:
                            return match.group(1).strip()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
        return None

    def update_version_in_file(self, filepath: str, new_version: str, dry_run: bool = False) -> bool:
        """Update version in YAML file."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()

            # Match version line (quoted or unquoted) and replace
            # Using a lambda to avoid backslash interpretation issues
            new_content = re.sub(
                r'(version:\s*)"?[^"\n]+"?',
                lambda m: m.group(1) + new_version,
                content,
                count=1
            )

            if new_content == content:
                return False  # No change made

            if not dry_run:
                with open(filepath, 'w') as f:
                    f.write(new_content)

            self.changes.append(filepath)
            return True
        except Exception as e:
            print(f"Error updating {filepath}: {e}")
            return False

    def sync_package(self, package_name: str, new_version: str, dry_run: bool = False) -> bool:
        """Sync version for entire package."""
        package_dir = os.path.join(self.repo_root, 'packages', package_name)

        if not os.path.isdir(package_dir):
            print(f"Error: Package directory not found: {package_dir}")
            return False

        if not self.validate_version(new_version):
            print(f"Error: Invalid version format: {new_version}")
            print("Must be semantic version (X.Y.Z)")
            return False

        print(f"Syncing {package_name} to version {new_version}...")

        success = True
        updated_count = 0

        # Update manifest
        manifest = os.path.join(package_dir, 'manifest.yaml')
        if os.path.exists(manifest):
            if self.update_version_in_file(manifest, new_version, dry_run):
                print(f"  ✓ Updated: {manifest}")
                updated_count += 1

        # Update commands
        commands_dir = os.path.join(package_dir, 'commands')
        if os.path.isdir(commands_dir):
            for cmd_file in Path(commands_dir).glob('*.md'):
                if self.update_version_in_file(str(cmd_file), new_version, dry_run):
                    print(f"  ✓ Updated: {cmd_file}")
                    updated_count += 1

        # Update skills
        skills_dir = os.path.join(package_dir, 'skills')
        if os.path.isdir(skills_dir):
            for skill_file in Path(skills_dir).glob('*/SKILL.md'):
                if self.update_version_in_file(str(skill_file), new_version, dry_run):
                    print(f"  ✓ Updated: {skill_file}")
                    updated_count += 1

        # Update agents
        agents_dir = os.path.join(package_dir, 'agents')
        if os.path.isdir(agents_dir):
            for agent_file in Path(agents_dir).glob('*.md'):
                if self.update_version_in_file(str(agent_file), new_version, dry_run):
                    print(f"  ✓ Updated: {agent_file}")
                    updated_count += 1

        print(f"Updated {updated_count} file(s) in {package_name}")
        return success

    def sync_marketplace(self, new_version: str, dry_run: bool = False) -> bool:
        """Sync marketplace platform version."""
        version_file = os.path.join(self.repo_root, 'version.yaml')

        if not os.path.exists(version_file):
            print(f"Error: Version file not found: {version_file}")
            return False

        if not self.validate_version(new_version):
            print(f"Error: Invalid version format: {new_version}")
            return False

        print(f"Syncing marketplace to version {new_version}...")

        if self.update_version_in_file(version_file, new_version, dry_run):
            print(f"  ✓ Updated: {version_file}")
            return True
        else:
            print(f"  (No changes needed)")
            return True

    def sync_all_packages(self, new_version: str, dry_run: bool = False) -> bool:
        """Sync all packages to same version."""
        packages_dir = os.path.join(self.repo_root, 'packages')

        if not os.path.isdir(packages_dir):
            print(f"Error: Packages directory not found: {packages_dir}")
            return False

        if not self.validate_version(new_version):
            print(f"Error: Invalid version format: {new_version}")
            return False

        print(f"Syncing all packages to version {new_version}...")

        success = True
        for package_dir in Path(packages_dir).iterdir():
            if package_dir.is_dir():
                package_name = package_dir.name
                if not self.sync_package(package_name, new_version, dry_run):
                    success = False

        return success

    def create_commit(self, message: str = None) -> bool:
        """Create git commit for changes."""
        if not self.changes:
            print("No changes to commit")
            return False

        try:
            # Stage changes
            subprocess.run(['git', 'add'] + self.changes, cwd=self.repo_root, check=True)

            # Create commit
            if message is None:
                message = f"chore(versioning): sync versions across artifacts"

            subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.repo_root,
                check=True
            )
            print(f"✓ Created git commit: {message}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating commit: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Synchronize version numbers across package artifacts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--package', help='Package name to update')
    parser.add_argument('--marketplace', action='store_true', help='Update marketplace version')
    parser.add_argument('--all', action='store_true', help='Update all packages')
    parser.add_argument('--version', required=True, help='Target version (X.Y.Z)')
    parser.add_argument('--commit', action='store_true', help='Create git commit')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')

    args = parser.parse_args()

    # Validate arguments
    if sum([bool(args.package), args.marketplace, args.all]) != 1:
        print("Error: Must specify exactly one of --package, --marketplace, or --all")
        sys.exit(1)

    syncer = VersionSyncer()

    # Execute sync
    success = False
    if args.package:
        success = syncer.sync_package(args.package, args.version, args.dry_run)
    elif args.marketplace:
        success = syncer.sync_marketplace(args.version, args.dry_run)
    elif args.all:
        success = syncer.sync_all_packages(args.version, args.dry_run)

    if success and args.commit and not args.dry_run:
        syncer.create_commit()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
