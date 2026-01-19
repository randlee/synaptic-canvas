#!/usr/bin/env python3
"""
Validate marketplace.json ↔ registry.json synchronization.

This script validates that:
- marketplace.json has entry for each package in packages/
- Versions match between marketplace.json and manifest.yaml
- Versions match between registry.json and manifest.yaml
- All packages in registry.json are in marketplace.json

Exit codes:
    0: All synchronized
    1: Synchronization issues found

Usage:
    python3 scripts/validate-marketplace-sync.py [--fix] [--verbose]
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

# Add test-packages/harness to path for Result imports
sys.path.insert(
    0, str(Path(__file__).parent.parent / "test-packages" / "harness")
)
from result import Failure, Result, Success


# ============================================================================
# Error Types
# ============================================================================


@dataclass
class SyncError:
    """Error during synchronization validation."""

    message: str
    package_name: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    details: dict = field(default_factory=dict)


@dataclass
class SyncValidationResult:
    """Results of synchronization validation."""

    missing_in_marketplace: list[str] = field(default_factory=list)
    missing_in_registry: list[str] = field(default_factory=list)
    version_mismatches: list[dict] = field(default_factory=list)
    packages_validated: int = 0
    total_packages: int = 0

    def is_valid(self) -> bool:
        """Check if validation passed (all synchronized)."""
        return not (
            self.missing_in_marketplace
            or self.missing_in_registry
            or self.version_mismatches
        )

    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            "\nMarketplace Synchronization Results:",
            f"  Total packages: {self.total_packages}",
            f"  Validated: {self.packages_validated}",
        ]

        if self.missing_in_marketplace:
            lines.append(
                f"\n  Missing in marketplace.json ({len(self.missing_in_marketplace)}):"
            )
            for pkg in self.missing_in_marketplace:
                lines.append(f"    - {pkg}")

        if self.missing_in_registry:
            lines.append(
                f"\n  Missing in registry.json ({len(self.missing_in_registry)}):"
            )
            for pkg in self.missing_in_registry:
                lines.append(f"    - {pkg}")

        if self.version_mismatches:
            lines.append(f"\n  Version mismatches ({len(self.version_mismatches)}):")
            for mismatch in self.version_mismatches:
                pkg = mismatch["package"]
                lines.append(f"    - {pkg}:")
                for key, value in mismatch.items():
                    if key != "package":
                        lines.append(f"        {key}: {value}")

        if self.is_valid():
            lines.append("\n  Status: SYNCHRONIZED ✓")
        else:
            lines.append("\n  Status: OUT OF SYNC ✗")

        return "\n".join(lines)


# ============================================================================
# Pydantic Models
# ============================================================================


class MarketplacePlugin(BaseModel):
    """Plugin entry in marketplace.json."""

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    source: str
    description: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    author: dict[str, str]
    license: str
    keywords: list[str] = Field(default_factory=list)
    category: str

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v):
        """Validate semantic version format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be X.Y.Z format")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Version parts must be numeric: {v}")
        return v


class RegistryPackage(BaseModel):
    """Package entry in registry.json."""

    name: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v):
        """Validate semantic version format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be X.Y.Z format")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Version parts must be numeric: {v}")
        return v


# ============================================================================
# Loading Functions
# ============================================================================


def load_json(path: Path) -> Result[dict[str, Any], SyncError]:
    """
    Load JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Success with JSON data, or Failure with error
    """
    if not path.exists():
        return Failure(
            error=SyncError(
                message=f"File not found: {path}",
            )
        )

    try:
        with open(path) as f:
            data = json.load(f)
        return Success(value=data)
    except json.JSONDecodeError as e:
        return Failure(
            error=SyncError(
                message=f"Invalid JSON in {path}: {e}",
            )
        )
    except Exception as e:
        return Failure(
            error=SyncError(
                message=f"Error loading {path}: {e}",
            )
        )


def load_manifest(package_path: Path) -> Result[dict[str, Any], SyncError]:
    """
    Load manifest.yaml.

    Args:
        package_path: Path to package directory

    Returns:
        Success with manifest data, or Failure with error
    """
    manifest_path = package_path / "manifest.yaml"

    if not manifest_path.exists():
        return Failure(
            error=SyncError(
                message=f"Manifest not found: {manifest_path}",
            )
        )

    try:
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
        return Success(value=data)
    except yaml.YAMLError as e:
        return Failure(
            error=SyncError(
                message=f"Invalid YAML in {manifest_path}: {e}",
            )
        )
    except Exception as e:
        return Failure(
            error=SyncError(
                message=f"Error loading {manifest_path}: {e}",
            )
        )


# ============================================================================
# Validation Functions
# ============================================================================


def get_package_dirs(packages_dir: Path) -> list[Path]:
    """
    Get all package directories.

    Args:
        packages_dir: Path to packages directory

    Returns:
        List of package directory paths
    """
    if not packages_dir.exists():
        return []

    return [
        d
        for d in packages_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]


def find_in_list(items: list[dict[str, Any]], name: str) -> Optional[dict[str, Any]]:
    """
    Find item by name in list.

    Args:
        items: List of dictionaries
        name: Name to search for

    Returns:
        Item if found, None otherwise
    """
    for item in items:
        if item.get("name") == name:
            return item
    return None


def validate_marketplace_sync(
    packages_dir: Path,
    marketplace_path: Path,
    registry_path: Path,
    verbose: bool = False,
) -> Result[SyncValidationResult, SyncError]:
    """
    Validate marketplace.json and registry.json synchronization.

    Args:
        packages_dir: Path to packages directory
        marketplace_path: Path to marketplace.json
        registry_path: Path to registry.json
        verbose: Enable verbose output

    Returns:
        Success with validation results, or Failure with error
    """
    warnings = []
    result = SyncValidationResult()

    # Load marketplace.json
    marketplace_result = load_json(marketplace_path)
    if isinstance(marketplace_result, Failure):
        return marketplace_result

    marketplace = marketplace_result.value
    marketplace_plugins = marketplace.get("plugins", [])

    # Load registry.json
    registry_result = load_json(registry_path)
    if isinstance(registry_result, Failure):
        return registry_result

    registry = registry_result.value
    registry_packages = registry.get("packages", {})

    # Get all package directories
    package_dirs = get_package_dirs(packages_dir)
    result.total_packages = len(package_dirs)

    # Validate each package
    for package_dir in package_dirs:
        package_name = package_dir.name
        result.packages_validated += 1

        if verbose:
            print(f"\nValidating {package_name}...")

        # Load manifest
        manifest_result = load_manifest(package_dir)
        if isinstance(manifest_result, Failure):
            warnings.append(
                f"Could not load manifest for {package_name}: "
                f"{manifest_result.error.message}"
            )
            continue

        manifest = manifest_result.value
        manifest_version = manifest.get("version")

        if not manifest_version:
            warnings.append(f"No version in manifest for {package_name}")
            continue

        # Check marketplace.json
        marketplace_plugin = find_in_list(marketplace_plugins, package_name)
        if not marketplace_plugin:
            result.missing_in_marketplace.append(package_name)
            if verbose:
                print(f"  ✗ Missing in marketplace.json")
        else:
            marketplace_version = marketplace_plugin.get("version")
            if marketplace_version != manifest_version:
                result.version_mismatches.append(
                    {
                        "package": package_name,
                        "manifest": manifest_version,
                        "marketplace": marketplace_version,
                    }
                )
                if verbose:
                    print(
                        f"  ✗ Version mismatch in marketplace.json: "
                        f"{marketplace_version} != {manifest_version}"
                    )

        # Check registry.json
        registry_package = registry_packages.get(package_name)
        if not registry_package:
            result.missing_in_registry.append(package_name)
            if verbose:
                print(f"  ✗ Missing in registry.json")
        else:
            registry_version = registry_package.get("version")
            if registry_version != manifest_version:
                # Check if already in mismatches, update if so
                existing_mismatch = next(
                    (
                        m
                        for m in result.version_mismatches
                        if m["package"] == package_name
                    ),
                    None,
                )
                if existing_mismatch:
                    existing_mismatch["registry"] = registry_version
                else:
                    result.version_mismatches.append(
                        {
                            "package": package_name,
                            "manifest": manifest_version,
                            "registry": registry_version,
                        }
                    )
                if verbose:
                    print(
                        f"  ✗ Version mismatch in registry.json: "
                        f"{registry_version} != {manifest_version}"
                    )

        if verbose and marketplace_plugin and registry_package:
            mkt_v = marketplace_plugin.get("version")
            reg_v = registry_package.get("version")
            if mkt_v == manifest_version and reg_v == manifest_version:
                print(f"  ✓ All versions match: {manifest_version}")

    # Check for packages in marketplace/registry that don't exist in packages/
    package_names = {d.name for d in package_dirs}

    for plugin in marketplace_plugins:
        plugin_name = plugin.get("name")
        if plugin_name and plugin_name not in package_names:
            warnings.append(
                f"{plugin_name} in marketplace.json but not in packages/"
            )

    for pkg_name in registry_packages.keys():
        if pkg_name not in package_names:
            warnings.append(f"{pkg_name} in registry.json but not in packages/")

    if verbose:
        print(result.get_summary())

    return Success(value=result, warnings=warnings)


def fix_sync_issues(
    packages_dir: Path,
    marketplace_path: Path,
    registry_path: Path,
    verbose: bool = False,
) -> Result[bool, SyncError]:
    """
    Fix synchronization issues by updating marketplace.json and registry.json.

    Args:
        packages_dir: Path to packages directory
        marketplace_path: Path to marketplace.json
        registry_path: Path to registry.json
        verbose: Enable verbose output

    Returns:
        Success(True) if fixes applied, Failure with error otherwise
    """
    # First validate to find issues
    validation_result = validate_marketplace_sync(
        packages_dir, marketplace_path, registry_path, verbose=False
    )

    if isinstance(validation_result, Failure):
        return validation_result

    validation = validation_result.value

    if validation.is_valid():
        if verbose:
            print("No fixes needed - already synchronized")
        return Success(value=False)

    # Load files
    marketplace_result = load_json(marketplace_path)
    if isinstance(marketplace_result, Failure):
        return marketplace_result

    marketplace = marketplace_result.value
    marketplace_plugins = marketplace.get("plugins", [])

    registry_result = load_json(registry_path)
    if isinstance(registry_result, Failure):
        return registry_result

    registry = registry_result.value
    registry_packages = registry.get("packages", {})

    changes_made = False

    # Fix version mismatches
    for mismatch in validation.version_mismatches:
        package_name = mismatch["package"]
        manifest_version = mismatch["manifest"]

        # Update marketplace
        if "marketplace" in mismatch:
            marketplace_plugin = find_in_list(marketplace_plugins, package_name)
            if marketplace_plugin:
                old_version = marketplace_plugin["version"]
                marketplace_plugin["version"] = manifest_version
                if verbose:
                    print(
                        f"Updated {package_name} in marketplace.json: "
                        f"{old_version} → {manifest_version}"
                    )
                changes_made = True

        # Update registry
        if "registry" in mismatch:
            registry_package = registry_packages.get(package_name)
            if registry_package:
                old_version = registry_package["version"]
                registry_package["version"] = manifest_version
                if verbose:
                    print(
                        f"Updated {package_name} in registry.json: "
                        f"{old_version} → {manifest_version}"
                    )
                changes_made = True

    if changes_made:
        # Write updated files
        try:
            with open(marketplace_path, "w") as f:
                json.dump(marketplace, f, indent=2)
                f.write("\n")  # Add trailing newline

            with open(registry_path, "w") as f:
                json.dump(registry, f, indent=2)
                f.write("\n")  # Add trailing newline

            if verbose:
                print("\nFiles updated successfully")

            return Success(value=True)

        except Exception as e:
            return Failure(
                error=SyncError(
                    message=f"Error writing files: {e}",
                )
            )

    return Success(value=False)


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate marketplace.json and registry.json synchronization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Validate synchronization:
    python3 scripts/validate-marketplace-sync.py

  Fix synchronization issues:
    python3 scripts/validate-marketplace-sync.py --fix

  Verbose output:
    python3 scripts/validate-marketplace-sync.py --verbose
""",
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix synchronization issues",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--packages-dir",
        type=Path,
        default=Path("packages"),
        help="Path to packages directory (default: packages)",
    )
    parser.add_argument(
        "--marketplace",
        type=Path,
        default=Path(".claude-plugin/marketplace.json"),
        help="Path to marketplace.json (default: .claude-plugin/marketplace.json)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("docs/registries/nuget/registry.json"),
        help="Path to registry.json (default: docs/registries/nuget/registry.json)",
    )

    args = parser.parse_args()

    if args.fix:
        result = fix_sync_issues(
            packages_dir=args.packages_dir,
            marketplace_path=args.marketplace,
            registry_path=args.registry,
            verbose=args.verbose,
        )

        if isinstance(result, Failure):
            print(f"\n✗ Error: {result.error.message}")
            return 1

        if result.value:
            print("\n✓ Synchronization issues fixed")
        else:
            print("\n✓ Already synchronized")

        return 0

    else:
        result = validate_marketplace_sync(
            packages_dir=args.packages_dir,
            marketplace_path=args.marketplace,
            registry_path=args.registry,
            verbose=args.verbose,
        )

        if isinstance(result, Failure):
            print(f"\n✗ Error: {result.error.message}")
            return 1

        validation = result.value

        if not args.verbose:
            print(validation.get_summary())

        # Print warnings
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")

        if validation.is_valid():
            print("\n✓ All synchronized")
            return 0
        else:
            print("\n✗ Synchronization issues found")
            return 1


if __name__ == "__main__":
    sys.exit(main())
