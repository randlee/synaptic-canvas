#!/usr/bin/env python3
"""
Update registry.json based on package manifests.

This script reads all packages/*/manifest.yaml files and updates registry.json
with current versions, metadata counts, and timestamps.

Usage:
    python3 scripts/update-registry.py --all [--dry-run]
    python3 scripts/update-registry.py --package <name> [--version <version>] [--dry-run]
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

# Add test-packages/harness to path for Result imports
sys.path.insert(0, str(Path(__file__).parent.parent / "test-packages" / "harness"))
from result import Failure, Result, Success


@dataclass
class RegistryError:
    """Error during registry operations."""
    message: str
    file_path: str = ""
    details: dict = field(default_factory=dict)


class PackageMetadata(BaseModel):
    """Package metadata structure."""

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str
    author: str
    license: str
    keywords: list[str] = Field(default_factory=list)
    category: str
    lastUpdated: Optional[str] = None

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate semantic version format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be X.Y.Z format")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Version parts must be numeric: {v}")
        return v


class RegistrySchema(BaseModel):
    """Registry.json schema."""

    name: str
    version: str
    description: str
    author: dict[str, str]
    packages: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated: str
    lastUpdated: str


def load_manifest(package_dir: Path) -> Result[dict[str, Any], RegistryError]:
    """Load and validate manifest.yaml file."""
    manifest_path = package_dir / "manifest.yaml"
    if not manifest_path.exists():
        return Failure(
            error=RegistryError(
                message="manifest.yaml not found",
                file_path=str(manifest_path),
            )
        )

    try:
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
        return Success(value=data)
    except yaml.YAMLError as e:
        return Failure(
            error=RegistryError(
                message=f"Invalid YAML syntax: {e}",
                file_path=str(manifest_path),
                details={"yaml_error": str(e)}
            )
        )
    except Exception as e:
        return Failure(
            error=RegistryError(
                message=f"Failed to load manifest: {e}",
                file_path=str(manifest_path),
            )
        )


def load_registry(registry_path: Path) -> Result[dict[str, Any], RegistryError]:
    """Load registry.json file."""
    if not registry_path.exists():
        return Failure(
            error=RegistryError(
                message="Registry file not found",
                file_path=str(registry_path),
            )
        )

    try:
        with open(registry_path) as f:
            data = json.load(f)
        return Success(value=data)
    except json.JSONDecodeError as e:
        return Failure(
            error=RegistryError(
                message=f"Invalid JSON syntax: {e}",
                file_path=str(registry_path),
                details={"json_error": str(e)}
            )
        )
    except Exception as e:
        return Failure(
            error=RegistryError(
                message=f"Failed to load registry: {e}",
                file_path=str(registry_path),
            )
        )


def find_packages(packages_dir: Path) -> list[Path]:
    """Find all package directories."""
    if not packages_dir.exists():
        return []
    return sorted([d for d in packages_dir.iterdir() if d.is_dir()])


def extract_package_info(manifest: dict[str, Any], package_dir: Path) -> dict[str, Any]:
    """Extract package information from manifest."""
    if not manifest:
        return {}

    # Count artifacts
    commands_count = len(manifest.get("artifacts", {}).get("commands", []))
    skills_count = len(manifest.get("artifacts", {}).get("skills", []))
    agents_count = len(manifest.get("artifacts", {}).get("agents", []))
    scripts_count = len(manifest.get("artifacts", {}).get("scripts", []))

    return {
        "name": manifest.get("name", ""),
        "version": manifest.get("version", ""),
        "description": manifest.get("description", ""),
        "author": manifest.get("author", ""),
        "license": manifest.get("license", "MIT"),
        "keywords": manifest.get("keywords", []),
        "category": manifest.get("category", "tools"),
        "artifacts": {
            "commands": commands_count,
            "skills": skills_count,
            "agents": agents_count,
            "scripts": scripts_count,
        },
        "lastUpdated": datetime.now().isoformat(),
    }


def calculate_metadata(packages: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate aggregate metadata for registry."""
    total_commands = sum(p.get("artifacts", {}).get("commands", 0) for p in packages)
    total_skills = sum(p.get("artifacts", {}).get("skills", 0) for p in packages)
    total_agents = sum(p.get("artifacts", {}).get("agents", 0) for p in packages)
    total_scripts = sum(p.get("artifacts", {}).get("scripts", 0) for p in packages)

    return {
        "totalPackages": len(packages),
        "totalCommands": total_commands,
        "totalSkills": total_skills,
        "totalAgents": total_agents,
        "totalScripts": total_scripts,
    }


def update_registry(
    packages_dir: Path,
    registry_path: Path,
    package_name: Optional[str] = None,
    dry_run: bool = False,
) -> Result[bool, RegistryError]:
    """Update registry.json with package information."""
    # Load current registry
    registry_result = load_registry(registry_path)
    if isinstance(registry_result, Failure):
        return registry_result

    registry = registry_result.value

    # Find packages to update
    if package_name:
        package_dirs = [packages_dir / package_name]
        if not package_dirs[0].exists():
            return Failure(
                error=RegistryError(
                    message=f"Package not found: {package_name}",
                    file_path=str(package_dirs[0]),
                )
            )
    else:
        package_dirs = find_packages(packages_dir)

    # Update package information
    for package_dir in package_dirs:
        manifest_result = load_manifest(package_dir)
        if isinstance(manifest_result, Failure):
            print(f"No manifest.yaml found in {package_dir.name}, skipping", file=sys.stderr)
            continue

        manifest = manifest_result.value
        pkg_info = extract_package_info(manifest, package_dir)
        pkg_name = pkg_info["name"]

        # Find existing package or add new one
        existing = None
        for pkg in registry.get("packages", []):
            if pkg.get("name") == pkg_name:
                existing = pkg
                break

        if existing:
            existing.update(pkg_info)
            print(f"Updated package: {pkg_name}")
        else:
            registry["packages"].append(pkg_info)
            print(f"Added package: {pkg_name}")

    # Update metadata
    registry["metadata"] = calculate_metadata(registry.get("packages", []))
    registry["generated"] = datetime.now().isoformat()
    registry["lastUpdated"] = datetime.now().isoformat()

    if dry_run:
        print("\n[DRY RUN] Would write to registry.json:")
        print(json.dumps(registry, indent=2))
        return Success(value=True)

    # Write updated registry
    try:
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)
        print(f"\nRegistry updated: {registry_path}")
        return Success(value=True)
    except Exception as e:
        return Failure(
            error=RegistryError(
                message=f"Error writing registry: {e}",
                file_path=str(registry_path),
            )
        )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update registry.json based on package manifests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Update all packages:
    python3 scripts/update-registry.py --all

  Update specific package:
    python3 scripts/update-registry.py --package sc-delay-tasks

  Dry run (preview changes):
    python3 scripts/update-registry.py --all --dry-run
""",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Update all packages from manifests",
    )
    parser.add_argument(
        "--package",
        type=str,
        help="Update specific package",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(".claude-plugin/registry.json"),
        help="Path to registry.json (default: .claude-plugin/registry.json)",
    )
    parser.add_argument(
        "--packages-dir",
        type=Path,
        default=Path("packages"),
        help="Path to packages directory (default: packages)",
    )

    args = parser.parse_args()

    if not args.all and not args.package:
        parser.print_help()
        return 1

    result = update_registry(
        packages_dir=args.packages_dir,
        registry_path=args.registry,
        package_name=args.package,
        dry_run=args.dry_run,
    )

    if isinstance(result, Success):
        return 0
    else:
        print(f"Error: {result.error.message}", file=sys.stderr)
        if result.error.file_path:
            print(f"File: {result.error.file_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
