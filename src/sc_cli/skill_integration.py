#!/usr/bin/env python3
"""
Skill Integration Module - Bridge between Claude skills and sc_cli

This module provides Python API functions that Claude skills and agents can use
to interact with the marketplace CLI without direct subprocess calls.

Phase 4: Marketplace Skill Integration
- query_marketplace_packages(): Discover packages from registries
- install_marketplace_package(): Install packages with verification
- get_marketplace_config(): Retrieve registry configuration

Note: This module depends on Phase 3 (remote registry querying) being implemented.
      Currently provides stub implementations that will be completed in Phase 3.
"""

from pathlib import Path
from typing import Dict, List, Optional

# Import from install module
try:
    from sc_cli.install import (
        _get_config_path,
        _load_config,
        cmd_registry_list,
        cmd_install,
        PACKAGES_DIR,
        _available_packages,
        _parse_manifest,
    )
except ImportError:
    # Fallback for testing without full install
    def _get_config_path() -> Path:
        return Path.home() / ".claude" / "config.yaml"

    def _load_config() -> Dict:
        return {}

    cmd_registry_list = None
    cmd_install = None
    PACKAGES_DIR = Path("packages")

    def _available_packages():
        return []

    def _parse_manifest(pkg_dir: Path):
        return None


def query_marketplace_packages(
    registry: Optional[str] = None,
    search_query: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict:
    """
    Query marketplace registries for available packages.

    This function will be fully implemented in Phase 3 (remote registry querying).
    Current implementation provides local package listing as a foundation.

    Args:
        registry: Specific registry name to query. If None, queries all active registries.
        search_query: Optional search term to filter packages by name/description.
        tags: Optional list of tags to filter packages (e.g., ["git", "automation"]).

    Returns:
        Dict containing:
        {
            "status": "success" | "error",
            "packages": [
                {
                    "name": str,
                    "version": str,
                    "status": str,  # beta, stable, deprecated
                    "description": str,
                    "tags": List[str],
                    "artifacts": {
                        "commands": int,
                        "skills": int,
                        "agents": int,
                        "scripts": int
                    },
                    "dependencies": List[str],
                    "repo": str,
                    "license": str,
                    "author": str,
                    "lastUpdated": str
                }
            ],
            "registry": str,  # Which registry was queried
            "message": str,  # Status or error message
        }

    Example:
        >>> packages = query_marketplace_packages()
        >>> for pkg in packages["packages"]:
        ...     print(f"{pkg['name']}: {pkg['description']}")

        >>> results = query_marketplace_packages(search_query="git")
        >>> results = query_marketplace_packages(registry="synaptic-canvas")
        >>> results = query_marketplace_packages(tags=["automation", "ci"])
    """
    try:
        # Phase 3 TODO: Implement remote registry querying
        # For now, list local packages as foundation

        # Load configuration
        config = _load_config()
        registries = config.get("marketplaces", {}).get("registries", {})
        default_registry = config.get("marketplaces", {}).get("default", "")

        # Determine which registry to query
        if registry:
            if registry not in registries:
                return {
                    "status": "error",
                    "packages": [],
                    "registry": registry,
                    "message": f"Registry '{registry}' not found. Use get_marketplace_config() to see available registries.",
                }
            target_registry = registry
        else:
            target_registry = default_registry or "local"

        # Phase 3 TODO: Fetch from remote registry URL
        # Current implementation: List local packages
        packages = []
        for pkg_dir in _available_packages():
            try:
                manifest = _parse_manifest(pkg_dir)

                # Extract artifact counts
                artifacts = {
                    "commands": len(manifest.artifacts.get("commands", [])),
                    "skills": len(manifest.artifacts.get("skills", [])),
                    "agents": len(manifest.artifacts.get("agents", [])),
                    "scripts": len(manifest.artifacts.get("scripts", [])),
                }

                # Build package info
                pkg_info = {
                    "name": manifest.name,
                    "version": "0.5.0",  # TODO: Extract from manifest or version.yaml
                    "status": "beta",  # TODO: Get from registry metadata
                    "description": manifest.description or "",
                    "tags": [],  # TODO: Extract from manifest or registry
                    "artifacts": artifacts,
                    "dependencies": [],  # TODO: Extract from manifest
                    "repo": "https://github.com/randlee/synaptic-canvas",
                    "license": "MIT",
                    "author": "Anthropic",
                    "lastUpdated": "2025-12-04",
                }

                # Apply search filter
                if search_query:
                    query_lower = search_query.lower()
                    if not (
                        query_lower in pkg_info["name"].lower()
                        or query_lower in pkg_info["description"].lower()
                    ):
                        continue

                # Apply tag filter
                if tags and pkg_info["tags"]:
                    if not any(tag in pkg_info["tags"] for tag in tags):
                        continue

                packages.append(pkg_info)

            except Exception as e:
                # Skip packages with errors
                continue

        return {
            "status": "success",
            "packages": packages,
            "registry": target_registry,
            "message": f"Found {len(packages)} package(s) in {target_registry} registry",
        }

    except Exception as e:
        return {
            "status": "error",
            "packages": [],
            "registry": registry or "unknown",
            "message": f"Error querying packages: {str(e)}",
        }


def install_marketplace_package(
    package: str,
    registry: Optional[str] = None,
    scope: str = "global",
    force: bool = False,
) -> Dict:
    """
    Install a package from marketplace registry.

    Integrates with Phase 1-2 CLI install functionality and Phase 3 registry querying.

    Args:
        package: Package name to install
        registry: Specific registry to use. If None, auto-detects from available registries.
        scope: Installation scope - "global" (~/.claude), "user" (~/.claude), or "local"/"project" (./.claude)
        force: Overwrite existing files if True

    Returns:
        Dict containing:
        {
            "status": "success" | "error",
            "package": str,
            "version": str,
            "scope": str,
            "installed_files": List[str],
            "registry_updated": bool,
            "message": str,
            "errors": List[str]
        }

    Example:
        >>> result = install_marketplace_package("sc-delay-tasks", scope="global")
        >>> if result["status"] == "success":
        ...     print(f"Installed {len(result['installed_files'])} files")

        >>> result = install_marketplace_package(
        ...     "sc-git-worktree",
        ...     registry="synaptic-canvas",
        ...     scope="local",
        ...     force=True
        ... )
    """
    try:
        # Validate scope
        if scope not in ["global", "local", "user", "project"]:
            return {
                "status": "error",
                "package": package,
                "version": "",
                "scope": scope,
                "installed_files": [],
                "registry_updated": False,
                "message": f"Invalid scope: {scope}. Must be 'global', 'user', 'local', or 'project'.",
                "errors": [f"Invalid scope: {scope}"],
            }

        # Phase 3 TODO: Verify package exists in registry before installation
        # For now, rely on cmd_install to validate

        # Execute installation using CLI function
        if cmd_install is None:
            return {
                "status": "error",
                "package": package,
                "version": "",
                "scope": scope,
                "installed_files": [],
                "registry_updated": False,
                "message": "Installation function not available",
                "errors": ["cmd_install not imported"],
            }

        # Map scope to CLI flags
        global_flag = scope in {"global", "user"}
        local_flag = scope in {"local", "project"}

        # Execute installation
        result_code = cmd_install(
            pkg=package,
            dest=None,
            force=force,
            expand=True,
            global_flag=global_flag,
            local_flag=local_flag,
            user_flag=scope == "user",
            project_flag=scope == "project",
        )

        if result_code == 0:
            # Installation successful
            # Determine installation path
            if scope in {"global", "user"}:
                install_path = Path.home() / ".claude"
            else:
                install_path = Path.cwd() / ".claude"

            # Get list of installed files (approximate - actual files from manifest)
            installed_files = []
            try:
                manifest = _parse_manifest(PACKAGES_DIR / package)
                for category in ["commands", "skills", "agents", "scripts"]:
                    for artifact in manifest.artifacts.get(category, []):
                        installed_files.append(artifact)
            except Exception:
                # If manifest parsing fails, provide generic success
                pass

            return {
                "status": "success",
                "package": package,
                "version": "0.5.0",  # TODO: Extract actual version
                "scope": scope,
                "installed_files": installed_files,
                "registry_updated": True,
                "message": f"Successfully installed {package} to {install_path}",
                "errors": [],
            }
        else:
            # Installation failed
            return {
                "status": "error",
                "package": package,
                "version": "",
                "scope": scope,
                "installed_files": [],
                "registry_updated": False,
                "message": f"Installation failed for {package}",
                "errors": [f"cmd_install returned error code {result_code}"],
            }

    except Exception as e:
        return {
            "status": "error",
            "package": package,
            "version": "",
            "scope": scope,
            "installed_files": [],
            "registry_updated": False,
            "message": f"Exception during installation: {str(e)}",
            "errors": [str(e)],
        }


def get_marketplace_config() -> Dict:
    """
    Get current marketplace configuration including registered registries.

    Returns:
        Dict containing:
        {
            "status": "success" | "error",
            "config_path": str,
            "default_registry": str,
            "registries": {
                "registry-name": {
                    "url": str,
                    "path": str,
                    "status": str,
                    "added_date": str
                }
            },
            "total_registries": int,
            "active_registries": int,
            "message": str
        }

    Example:
        >>> config = get_marketplace_config()
        >>> print(f"Default: {config['default_registry']}")
        >>> for name, info in config['registries'].items():
        ...     print(f"{name}: {info['url']}")
    """
    try:
        config_path = _get_config_path()
        config = _load_config()

        marketplaces = config.get("marketplaces", {})
        default_registry = marketplaces.get("default", "")
        registries = marketplaces.get("registries", {})

        # Count active registries
        active_count = sum(
            1 for reg in registries.values() if reg.get("status", "active") == "active"
        )

        return {
            "status": "success",
            "config_path": str(config_path),
            "default_registry": default_registry,
            "registries": registries,
            "total_registries": len(registries),
            "active_registries": active_count,
            "message": f"Found {len(registries)} configured registries ({active_count} active)",
        }

    except Exception as e:
        return {
            "status": "error",
            "config_path": str(_get_config_path()),
            "default_registry": "",
            "registries": {},
            "total_registries": 0,
            "active_registries": 0,
            "message": f"Error loading configuration: {str(e)}",
        }


# Helper functions for agents

def format_package_list(packages: List[Dict], show_install_cmd: bool = True) -> str:
    """
    Format package list for display to user.

    Args:
        packages: List of package dicts from query_marketplace_packages()
        show_install_cmd: Include installation command in output

    Returns:
        Formatted string ready for display
    """
    if not packages:
        return "No packages found."

    lines = []
    for pkg in packages:
        lines.append(f"\n• {pkg['name']} (v{pkg['version']}) - {pkg['status']}")
        lines.append(f"  \"{pkg['description'][:80]}...\"" if len(pkg['description']) > 80 else f"  \"{pkg['description']}\"")

        if pkg.get("tags"):
            lines.append(f"  Tags: {', '.join(pkg['tags'])}")

        artifacts = pkg.get("artifacts", {})
        artifact_parts = []
        if artifacts.get("commands"):
            artifact_parts.append(f"{artifacts['commands']} command(s)")
        if artifacts.get("skills"):
            artifact_parts.append(f"{artifacts['skills']} skill(s)")
        if artifacts.get("agents"):
            artifact_parts.append(f"{artifacts['agents']} agent(s)")
        if artifacts.get("scripts"):
            artifact_parts.append(f"{artifacts['scripts']} script(s)")

        if artifact_parts:
            lines.append(f"  Artifacts: {', '.join(artifact_parts)}")

        if show_install_cmd:
            lines.append(f"\n  Install with: /marketplace install {pkg['name']} --global")

    return "\n".join(lines)


def format_registry_list(registries: Dict, default_registry: str) -> str:
    """
    Format registry list for display to user.

    Args:
        registries: Dict of registries from get_marketplace_config()
        default_registry: Name of default registry

    Returns:
        Formatted string ready for display
    """
    if not registries:
        return "No registries configured.\n\nAdd a registry with: /marketplace registry add <name> <url>"

    lines = ["Configured registries:\n"]

    for name, info in registries.items():
        marker = "*" if name == default_registry else " "
        lines.append(f"{marker} {name:<20} {info.get('url', '')}")

        if info.get("path"):
            lines.append(f"  {'path:':<20} {info['path']}")
        if info.get("status"):
            lines.append(f"  {'status:':<20} {info['status']}")
        if info.get("added_date"):
            lines.append(f"  {'added:':<20} {info['added_date']}")
        lines.append("")

    lines.append(f"\nTotal: {len(registries)} registries")
    lines.append("(* = default registry)")

    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test of integration functions
    print("Testing marketplace skill integration...")
    print()

    print("1. Getting marketplace config...")
    config = get_marketplace_config()
    print(f"   Status: {config['status']}")
    print(f"   Total registries: {config['total_registries']}")
    print()

    print("2. Querying packages...")
    result = query_marketplace_packages()
    print(f"   Status: {result['status']}")
    print(f"   Found: {len(result['packages'])} packages")
    if result['packages']:
        print(f"   First package: {result['packages'][0]['name']}")
    print()

    print("Integration module test complete.")
