#!/usr/bin/env python3
"""
Synchronize marketplace.json with registry.json.

This script keeps marketplace.json in sync with registry.json by:
- Using registry.json as the source of truth
- Updating marketplace.json with matching versions and descriptions
- Adding any missing packages
- Validating structure

Usage:
    python3 scripts/sync-marketplace-json.py [--dry-run]
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# Add test-packages/harness to path for Result imports
sys.path.insert(0, str(Path(__file__).parent.parent / "test-packages" / "harness"))
from result import Failure, Result, Success


@dataclass
class SyncError:
    """Error during sync operations."""
    message: str
    file_path: str = ""
    details: dict = field(default_factory=dict)


class PackageEntry(BaseModel):
    """Single package entry in marketplace/registry."""

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
    def validate_semver(cls, v: str) -> str:
        """Validate semantic version format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be X.Y.Z format")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Version parts must be numeric: {v}")
        return v


class MarketplaceSchema(BaseModel):
    """Marketplace/registry JSON schema."""

    name: str
    owner: Optional[dict[str, str]] = None
    metadata: Optional[dict[str, Any]] = None
    plugins: list[dict[str, Any]] = Field(default_factory=list)


def load_json(path: Path) -> Result[dict[str, Any], SyncError]:
    """Load JSON file."""
    if not path.exists():
        return Failure(
            error=SyncError(
                message=f"File not found: {path}",
                file_path=str(path),
            )
        )

    try:
        with open(path) as f:
            data = json.load(f)
        return Success(value=data)
    except json.JSONDecodeError as e:
        return Failure(
            error=SyncError(
                message=f"Invalid JSON syntax: {e}",
                file_path=str(path),
                details={"json_error": str(e)}
            )
        )
    except Exception as e:
        return Failure(
            error=SyncError(
                message=f"Error loading {path}: {e}",
                file_path=str(path),
            )
        )


def normalize_author(author: Any) -> dict[str, str]:
    """Normalize author field to object format required by schema."""
    if isinstance(author, dict):
        return author
    if isinstance(author, str):
        return {"name": author}
    return {"name": "unknown"}


def find_package(packages: list[dict[str, Any]], name: str) -> Optional[dict[str, Any]]:
    """Find package by name in list."""
    for pkg in packages:
        if pkg.get("name") == name:
            return pkg
    return None


def sync_marketplace(
    registry_path: Path,
    marketplace_path: Path,
    dry_run: bool = False,
) -> Result[bool, SyncError]:
    """Synchronize marketplace.json with registry.json."""
    # Load both files
    registry_result = load_json(registry_path)
    if isinstance(registry_result, Failure):
        return registry_result

    marketplace_result = load_json(marketplace_path)
    if isinstance(marketplace_result, Failure):
        return marketplace_result

    registry = registry_result.value
    marketplace = marketplace_result.value

    registry_packages = registry.get("packages", [])
    marketplace_plugins = marketplace.get("plugins", [])

    changes_made = False

    # Process each package in registry
    for reg_pkg in registry_packages:
        pkg_name = reg_pkg.get("name")
        mkt_pkg = find_package(marketplace_plugins, pkg_name)

        if mkt_pkg:
            # Update existing package
            old_version = mkt_pkg.get("version")
            new_version = reg_pkg.get("version")

            if old_version != new_version:
                print(f"Updating {pkg_name}: {old_version} → {new_version}")
                mkt_pkg["version"] = new_version
                changes_made = True

            # Update description if different
            if mkt_pkg.get("description") != reg_pkg.get("description"):
                old_desc = mkt_pkg.get("description")
                new_desc = reg_pkg.get("description")
                print(f"Updating description for {pkg_name}")
                mkt_pkg["description"] = new_desc
                changes_made = True

            # Update other fields
            for field_name in ["license", "keywords", "category"]:
                if field_name in reg_pkg and mkt_pkg.get(field_name) != reg_pkg.get(field_name):
                    mkt_pkg[field_name] = reg_pkg[field_name]
                    changes_made = True

            # author must always be an object
            new_author = normalize_author(reg_pkg.get("author", mkt_pkg.get("author", {})))
            if mkt_pkg.get("author") != new_author:
                mkt_pkg["author"] = new_author
                changes_made = True

        else:
            # Add missing package
            new_pkg = {
                "name": pkg_name,
                "source": reg_pkg.get("source", f"./packages/{pkg_name}"),
                "description": reg_pkg.get("description", ""),
                "version": reg_pkg.get("version", ""),
                "author": normalize_author(reg_pkg.get("author", {"name": "randlee"})),
                "license": reg_pkg.get("license", "MIT"),
                "keywords": reg_pkg.get("keywords", []),
                "category": reg_pkg.get("category", "tools"),
            }
            print(f"Adding missing package: {pkg_name}")
            marketplace_plugins.append(new_pkg)
            changes_made = True

    # Check for packages in marketplace that aren't in registry
    for mkt_pkg in marketplace_plugins:
        pkg_name = mkt_pkg.get("name")
        if not find_package(registry_packages, pkg_name):
            print(f"Warning: {pkg_name} in marketplace but not in registry")

    if dry_run:
        if changes_made:
            print("\n[DRY RUN] Changes that would be made:")
            print(json.dumps(marketplace, indent=2))
        else:
            print("[DRY RUN] No changes needed")
        return Success(value=True)

    if changes_made:
        try:
            with open(marketplace_path, "w") as f:
                json.dump(marketplace, f, indent=2)
            print(f"\nMarketplace synchronized: {marketplace_path}")
            return Success(value=True)
        except Exception as e:
            return Failure(
                error=SyncError(
                    message=f"Error writing marketplace: {e}",
                    file_path=str(marketplace_path),
                )
            )
    else:
        print("Marketplace already synchronized")
        return Success(value=True)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Synchronize marketplace.json with registry.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Sync marketplace with registry:
    python3 scripts/sync-marketplace-json.py

  Dry run (preview changes):
    python3 scripts/sync-marketplace-json.py --dry-run
""",
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
        "--marketplace",
        type=Path,
        default=Path(".claude-plugin/marketplace.json"),
        help="Path to marketplace.json (default: .claude-plugin/marketplace.json)",
    )

    args = parser.parse_args()

    result = sync_marketplace(
        registry_path=args.registry,
        marketplace_path=args.marketplace,
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
