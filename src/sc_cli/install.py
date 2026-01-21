#!/usr/bin/env python3
"""
Python rewrite of tools/sc-install.sh

Commands:
  list
  info <package>
  install <package> --dest <path/to/.claude> [--force] [--no-expand]
  install <package> --global [--force] [--no-expand]
  install <package> --local [--force] [--no-expand]
  install <package> --user [--force] [--no-expand]
  install <package> --project [--force] [--no-expand]
  uninstall <package> --dest <path/to/.claude>
  registry add <name> <url> [--path <path>]
  registry list
  registry remove <name>

Config Schema (~/.claude/config.yaml):
  marketplaces:
    default: synaptic-canvas
    registries:
      synaptic-canvas:
        url: https://github.com/randlee/synaptic-canvas
        path: docs/registries/nuget/registry.json
        status: active
        added_date: 2025-12-04
      custom-registry:
        url: https://github.com/org/marketplace
        status: active
        added_date: 2025-12-05

Notes:
- Uses YAML if PyYAML is installed; otherwise falls back to a simple line parser
  compatible with the existing manifest patterns.
- Token expansion: replaces {{REPO_NAME}} when variables.REPO_NAME.auto == git-repo-basename
- Scripts are made executable on install (artifacts under scripts/*)
- Config file manages marketplace registries with metadata (url, path, status, added_date)
- Phase 1: Basic registry commands (add, list, remove) and config persistence
- Phase 2: Config schema validation, metadata management, and advanced features
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Optional YAML support
try:  # pragma: no cover - exercised in environment when available
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def info(msg: str) -> None:
    print(f"{GREEN}✓{NC} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}⚠{NC} {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"{RED}✗{NC} {msg}", file=sys.stderr)


# Determine repository root robustly (supports src/ layout)
_THIS_FILE = Path(__file__).resolve()
REPO_ROOT = next(
    (p for p in [_THIS_FILE.parent] + list(_THIS_FILE.parents) if (p / "packages").exists()),
    _THIS_FILE.parents[2] if len(_THIS_FILE.parents) >= 3 else _THIS_FILE.parents[1],
)
PACKAGES_DIR = REPO_ROOT / "packages"


@dataclass
class Manifest:
    name: str
    path: Path
    description: str
    artifacts: Dict[str, List[str]]
    variables: Dict[str, Dict[str, str]]


def _read_file(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _parse_manifest(pkg_dir: Path) -> Manifest:
    manifest_path = pkg_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise SystemExit(f"No manifest.yaml in {pkg_dir.name}")

    if yaml is not None:
        data = yaml.safe_load(_read_file(manifest_path)) or {}
        artifacts = (data.get("artifacts") or {})
        variables = (data.get("variables") or {})
        desc = (data.get("description") or "").strip()
        return Manifest(
            name=data.get("name") or pkg_dir.name,
            path=pkg_dir,
            description=desc,
            artifacts={k: list(v or []) for k, v in artifacts.items()},
            variables=variables,
        )

    # Fallback: minimal line parser for artifacts sections
    artifacts: Dict[str, List[str]] = {"commands": [], "skills": [], "agents": [], "scripts": []}
    current: Optional[str] = None
    for line in _read_file(manifest_path).splitlines():
        line = line.rstrip()
        if line.strip().endswith(":"):
            key = line.strip()[:-1]
            if key in artifacts:
                current = key
            else:
                current = None
            continue
        if current and line.strip().startswith("- "):
            item = line.split("- ", 1)[1].strip()
            artifacts[current].append(item)
    # Best-effort description: not critical
    return Manifest(name=pkg_dir.name, path=pkg_dir, description="", artifacts=artifacts, variables={})


def _available_packages() -> Iterable[Path]:
    if not PACKAGES_DIR.exists():
        return []
    return sorted(p for p in PACKAGES_DIR.iterdir() if p.is_dir())


# ============================================================================
# Phase 1 & 2: Config and Registry Management
# ============================================================================

def _get_config_path() -> Path:
    """Return path to marketplace config file (~/.claude/config.yaml)."""
    return Path.home() / ".claude" / "config.yaml"


def _validate_url(url: str) -> bool:
    """Check if URL has valid format (https:// or http://)."""
    if not url:
        return False
    return url.startswith("https://") or url.startswith("http://")


def _validate_config_schema(config: Dict) -> Dict:
    """Validate and initialize config schema with required sections.

    Phase 2 Task 1: Config Schema Validation
    - Validate structure has required keys: marketplaces, default, registries
    - Initialize missing sections with defaults
    """
    if not isinstance(config, dict):
        config = {}

    # Initialize marketplaces section
    if "marketplaces" not in config:
        config["marketplaces"] = {}

    marketplaces = config["marketplaces"]
    if not isinstance(marketplaces, dict):
        config["marketplaces"] = {}
        marketplaces = config["marketplaces"]

    # Initialize registries dict
    if "registries" not in marketplaces:
        marketplaces["registries"] = {}

    if not isinstance(marketplaces["registries"], dict):
        marketplaces["registries"] = {}

    # Initialize default marketplace (Phase 2 Task 2)
    if "default" not in marketplaces:
        marketplaces["default"] = "synaptic-canvas"

    return config


# ==============================================================================
# Phase 3: Remote Registry Fetching
# ==============================================================================

def _fetch_registry_json(url: str, path: str = "") -> Optional[Dict]:
    """Fetch registry.json from remote URL.
    
    Phase 3 Task 1: Remote Registry Fetching
    - Fetch registry.json from remote URL
    - Support optional path (e.g., "docs/registries/nuget/registry.json")
    - Handle HTTP errors gracefully
    - Return dict or None on failure
    
    Args:
        url: Base URL of the registry (e.g., https://github.com/org/repo)
        path: Optional path to registry.json (e.g., "docs/registries/nuget/registry.json")
    
    Returns:
        Dictionary containing registry data, or None on failure
    """
    try:
        import urllib.request
        import json
        
        # Construct full URL
        if path:
            full_url = f"{url.rstrip('/')}/{path.lstrip('/')}"
        else:
            full_url = f"{url.rstrip('/')}/registry.json"
        
        # Handle GitHub URLs - convert to raw content URL
        if "github.com" in full_url and "/blob/" not in full_url and "raw.githubusercontent.com" not in full_url:
            # Convert github.com URL to raw.githubusercontent.com
            full_url = full_url.replace("github.com", "raw.githubusercontent.com")
            full_url = full_url.replace("/tree/", "/")

        # Insert branch name if missing (for raw.githubusercontent.com URLs)
        if "raw.githubusercontent.com" in full_url:
            parts = full_url.split("/")
            # Expected: https://raw.githubusercontent.com/owner/repo/branch/path...
            # If parts[5] looks like a path (not a branch), insert 'main'
            if len(parts) >= 6 and not parts[5] in ["main", "master", "develop"]:
                # Insert 'main' as default branch between repo and path
                full_url = "/".join(parts[:5]) + "/main/" + "/".join(parts[5:])
        
        # Fetch with timeout
        req = urllib.request.Request(full_url, headers={"User-Agent": "sc-install/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    
    except urllib.request.URLError as e:
        warn(f"Network error fetching registry: {e}")
        return None
    except json.JSONDecodeError as e:
        warn(f"Failed to parse registry JSON: {e}")
        return None
    except Exception as e:
        warn(f"Error fetching registry: {e}")
        return None


def _parse_registry_metadata(registry_data: Dict) -> Dict:
    """Extract packages from registry.json.

    Phase 3 Task 1: Parse Registry Metadata
    - Extract packages from registry.json
    - Return simplified metadata: {package_name: {version, description, tier}}
    - Handle missing fields gracefully
    - Return empty dict if structure unrecognized
    - Support both dict and list formats for backward compatibility

    Args:
        registry_data: Dictionary from registry.json

    Returns:
        Dictionary mapping package names to metadata
    """
    packages = {}

    try:
        packages_data = registry_data.get("packages", {})

        # Handle dict format: {"package-name": {...metadata...}}
        if isinstance(packages_data, dict):
            for name, pkg in packages_data.items():
                if not isinstance(pkg, dict):
                    continue

                packages[name] = {
                    "version": pkg.get("version", "unknown"),
                    "description": pkg.get("description", "No description available"),
                    "tier": pkg.get("tier", "community"),
                    "author": pkg.get("author", ""),
                    "source": pkg.get("source", ""),
                    "download_url": pkg.get("download_url", ""),
                    "dependencies": pkg.get("dependencies", []),
                }

        # Handle list format: [{"name": "...", ...metadata...}]
        elif isinstance(packages_data, list):
            for pkg in packages_data:
                if not isinstance(pkg, dict):
                    continue

                name = pkg.get("name", pkg.get("id", ""))
                if not name:
                    continue

                packages[name] = {
                    "version": pkg.get("version", "unknown"),
                    "description": pkg.get("description", "No description available"),
                    "tier": pkg.get("tier", "community"),
                    "author": pkg.get("author", ""),
                    "source": pkg.get("source", ""),
                    "download_url": pkg.get("download_url", ""),
                    "dependencies": pkg.get("dependencies", []),
                }

    except Exception as e:
        warn(f"Error parsing registry metadata: {e}")
        return {}

    return packages


def _search_packages(name_query: str, registry_data: Dict) -> List[Dict]:
    """Search packages by name (case-insensitive substring match).
    
    Phase 3 Task 1: Package Search
    - Search packages by name (case-insensitive substring match)
    - Return list of matching packages with metadata
    - Support tag-based filtering (future enhancement)
    
    Args:
        name_query: Search query string
        registry_data: Parsed registry metadata
    
    Returns:
        List of matching package dictionaries
    """
    if not name_query:
        # Return all packages if no query
        return [{"name": k, **v} for k, v in registry_data.items()]
    
    query_lower = name_query.lower()
    matches = []
    
    for pkg_name, metadata in registry_data.items():
        if query_lower in pkg_name.lower():
            matches.append({"name": pkg_name, **metadata})
        elif query_lower in metadata.get("description", "").lower():
            matches.append({"name": pkg_name, **metadata})
    
    return matches


def _load_config() -> Dict:
    """Load marketplace config from YAML.

    Phase 2 enhancements:
    - Auto-create ~/.claude directory on first use
    - Handle YAML parse errors gracefully
    - Initialize missing sections with defaults
    - Support config merging

    Returns empty dict if file doesn't exist or on parse error.
    """
    try:
        config_path = _get_config_path()

        # Auto-create directory (Phase 2 Task 1)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        if not config_path.exists():
            # Return validated empty config
            return _validate_config_schema({})

        if yaml is not None:
            content = _read_file(config_path)
            data = yaml.safe_load(content) or {}
            # Validate and initialize schema
            return _validate_config_schema(data if isinstance(data, dict) else {})
        else:
            # Without YAML library, return empty validated config
            return _validate_config_schema({})
    except PermissionError as ex:
        warn(f"Permission denied accessing config: {ex}")
        # Return validated empty config on permission error
        return _validate_config_schema({})
    except Exception as ex:
        warn(f"Could not parse config file: {ex}")
        # Return validated empty config on error
        return _validate_config_schema({})


def _save_config(config: Dict) -> int:
    """Write config to YAML file.

    Phase 2 enhancements:
    - Validate schema before saving
    - Preserve registry order
    - Auto-create ~/.claude directory

    Returns:
        0 on success, 1 on error
    """
    config_path = _get_config_path()

    try:
        # Ensure directory exists (Phase 2 Task 1)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate schema before saving
        config = _validate_config_schema(config)

        if yaml is not None:
            # sort_keys=False preserves insertion order (Phase 2 Task 5)
            content = yaml.safe_dump(config, sort_keys=False, default_flow_style=False)
        else:
            # Minimal YAML emit without PyYAML
            lines = []
            marketplaces = config.get("marketplaces", {})
            if marketplaces:
                lines.append("marketplaces:")

                # Default field
                if "default" in marketplaces:
                    lines.append(f"  default: {marketplaces['default']}")

                # Registries
                if "registries" in marketplaces and marketplaces["registries"]:
                    lines.append("  registries:")
                    for name, data in marketplaces["registries"].items():
                        lines.append(f"    {name}:")
                        for key in ["url", "path", "status", "added_date"]:
                            if key in data:
                                value = data[key]
                                lines.append(f"      {key}: {value}")

            content = "\n".join(lines) + "\n" if lines else ""

        config_path.write_text(content, encoding="utf-8")
        return 0
    except PermissionError:
        error(f"Permission denied writing to: {config_path}")
        return 1
    except Exception as ex:
        error(f"Could not write config: {ex}")
        return 1


def cmd_registry_add(name: str, url: str, path: str = "") -> int:
    """Add or update a marketplace registry.

    Phase 1: Basic registry add command
    Phase 2 Task 3: Registry metadata management
    - Store added_date in ISO format (YYYY-MM-DD)
    - Preserve added_date when updating existing registry
    - Store status field (active/disabled/archived)
    - Support optional path field for custom registry.json locations
    - Validate path is relative URL-like string

    Args:
        name: Registry name (alphanumeric, dash, underscore only)
        url: Registry URL (must start with https:// or http://)
        path: Optional path within registry

    Returns:
        0 on success, 1 on error
    """
    # Validate URL
    if not _validate_url(url):
        error(f"Invalid URL format: {url} (must start with https:// or http://)")
        return 1

    # Validate name - alphanumeric, dash, underscore only
    if not name:
        error("Registry name cannot be empty")
        return 1

    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        error(f"Invalid registry name: {name} (only alphanumeric, dash, underscore allowed)")
        return 1

    # Load config
    config = _load_config()

    # Initialize registries if needed
    if "registries" not in config["marketplaces"]:
        config["marketplaces"]["registries"] = {}

    registries = config["marketplaces"]["registries"]

    # Track if updating existing registry (preserve added_date - Phase 2 Task 3)
    existing_entry = registries.get(name, {})
    added_date = existing_entry.get("added_date", "")
    is_update = name in registries

    # If not updating, set current date (Phase 2 Task 3: ISO format)
    if not added_date:
        from datetime import datetime
        added_date = datetime.now().strftime("%Y-%m-%d")

    # Remove trailing slash from URL
    url = url.rstrip("/")

    # Phase 2 Task 2: Auto-register synaptic-canvas if first registry
    if not registries and name != "synaptic-canvas":
        # Add synaptic-canvas as default marketplace
        from datetime import datetime
        registries["synaptic-canvas"] = {
            "url": "https://github.com/randlee/synaptic-canvas",
            "path": "docs/registries/nuget/registry.json",
            "status": "active",
            "added_date": datetime.now().strftime("%Y-%m-%d"),
        }

    # Add/update registry entry (Phase 2 Task 3: All metadata fields)
    entry = {
        "url": url,
        "status": existing_entry.get("status", "active"),  # Preserve status
        "added_date": added_date,
    }

    # Only add path if provided (Phase 2 Task 3: Optional field)
    if path:
        entry["path"] = path

    registries[name] = entry

    # Phase 2 Task 3: Config merging (preserves other registries)
    # Save config
    rc = _save_config(config)
    if rc != 0:
        return rc

    action = "Updated" if is_update else "Added"
    info(f"{action} registry: {name} -> {url}")
    return 0


def cmd_registry_list() -> int:
    """List all configured marketplace registries.

    Phase 1: Basic registry list command
    Phase 2: Shows all metadata fields

    Returns:
        0 on success
    """
    config = _load_config()
    registries = config.get("marketplaces", {}).get("registries", {})
    default = config.get("marketplaces", {}).get("default", "")

    if not registries:
        print("No registries configured.")
        print()
        print("Add a registry with: sc-install registry add <name> <url>")
        return 0

    print("Configured registries:\n")

    # Phase 2 Task 5: Registry ordering (maintain order)
    for name in registries.keys():
        data = registries[name]
        url = data.get("url", "")
        path = data.get("path", "")
        status = data.get("status", "")
        added = data.get("added_date", "")

        # Mark default marketplace
        marker = "*" if name == default else " "
        print(f"{marker} {name:<20} {url}")
        if path:
            print(f"  {'path:':<20} {path}")
        if status:
            print(f"  {'status:':<20} {status}")
        if added:
            print(f"  {'added:':<20} {added}")
        print()

    return 0


def cmd_registry_remove(name: str) -> int:
    """Remove a marketplace registry.

    Phase 1: Basic registry remove command
    Phase 2: Preserves other registries (config merging)

    Args:
        name: Registry name to remove

    Returns:
        0 on success, 1 on error
    """
    config = _load_config()
    registries = config.get("marketplaces", {}).get("registries", {})

    if name not in registries:
        error(f"Registry not found: {name}")
        return 1

    # Remove registry (Phase 2: Other registries preserved)
    del registries[name]

    # Save config
    rc = _save_config(config)
    if rc != 0:
        return rc

    info(f"Removed registry: {name}")
    return 0


# ============================================================================
# Original Package Commands
# ============================================================================

def cmd_list(registry: Optional[str] = None, all_registries: bool = False, search: Optional[str] = None) -> int:
    """List available packages from local or remote registries.
    
    Phase 3 Enhancement: Remote Registry Support
    - Support --registry flag to query specific registry
    - Support --all-registries flag to query all registered registries
    - Support --search flag to filter packages
    """
    # If remote registry specified
    if registry or all_registries:
        config = _load_config()
        registries_to_query = []
        
        if all_registries:
            # Query all registered registries
            registries_to_query = list(config.get("marketplaces", {}).get("registries", {}).keys())
        elif registry:
            # Query specific registry
            if registry not in config.get("marketplaces", {}).get("registries", {}):
                error(f"Registry not found: {registry}")
                error("Use 'sc-install registry list' to see available registries")
                return 1
            registries_to_query = [registry]
        
        # Fetch and display remote packages
        all_packages = []
        for reg_name in registries_to_query:
            reg_info = config["marketplaces"]["registries"][reg_name]
            url = reg_info.get("url", "")
            path = reg_info.get("path", "")
            
            print(f"\nRegistry: {reg_name} ({url})")
            print("=" * 60)
            
            registry_json = _fetch_registry_json(url, path)
            if registry_json is None:
                warn(f"Failed to fetch registry: {reg_name}")
                continue
            
            packages = _parse_registry_metadata(registry_json)
            if search:
                matches = _search_packages(search, packages)
            else:
                matches = [{"name": k, **v} for k, v in packages.items()]
            
            if not matches:
                print("  No packages found")
            else:
                for pkg in sorted(matches, key=lambda x: x["name"]):
                    desc_first = pkg.get("description", "").splitlines()[0] if pkg.get("description") else "(no description)"
                    version = pkg.get("version", "unknown")
                    print(f"  {pkg['name']:<20} v{version:<10} {desc_first[:50]}")
                    all_packages.extend(matches)
        
        return 0
    
    # Default: list local packages
    print("Available packages:\n")
    for pkg_dir in _available_packages():
        m = _parse_manifest(pkg_dir)
        desc_first = m.description.splitlines()[0] if m.description else "(no manifest)"
        
        # Apply search filter if specified
        if search:
            if search.lower() not in pkg_dir.name.lower() and search.lower() not in desc_first.lower():
                continue
        
        print(f"  {pkg_dir.name:<20} {desc_first[:60]}")
    
    return 0



def cmd_search(query: str, registry: Optional[str] = None) -> int:
    """Search for packages across registered registries.
    
    Phase 3 Task 2: Search Command
    - Search across registered registries
    - Display results with source registry
    - Show package details
    
    Args:
        query: Search query string
        registry: Optional specific registry to search (None = all registries)
    
    Returns:
        0 on success, 1 on error
    """
    if not query:
        error("Search query cannot be empty")
        return 1
    
    config = _load_config()
    registries = config.get("marketplaces", {}).get("registries", {})
    
    if not registries:
        error("No registries configured. Use 'sc-install registry add' to add a registry")
        return 1
    
    # Determine which registries to search
    if registry:
        if registry not in registries:
            error(f"Registry not found: {registry}")
            error("Use 'sc-install registry list' to see available registries")
            return 1
        registries_to_search = {registry: registries[registry]}
    else:
        registries_to_search = registries
    
    print(f"Searching for '{query}' across {len(registries_to_search)} registr{'y' if len(registries_to_search) == 1 else 'ies'}...\n")
    
    total_matches = 0
    for reg_name, reg_info in registries_to_search.items():
        url = reg_info.get("url", "")
        path = reg_info.get("path", "")
        
        registry_json = _fetch_registry_json(url, path)
        if registry_json is None:
            warn(f"Failed to fetch registry: {reg_name}")
            continue
        
        packages = _parse_registry_metadata(registry_json)
        matches = _search_packages(query, packages)
        
        if matches:
            print(f"Registry: {reg_name}")
            print("-" * 60)
            for pkg in sorted(matches, key=lambda x: x["name"]):
                desc_first = pkg.get("description", "").splitlines()[0] if pkg.get("description") else "(no description)"
                version = pkg.get("version", "unknown")
                tier = pkg.get("tier", "community")
                print(f"  {pkg['name']:<20} v{version:<10} [{tier}]")
                print(f"    {desc_first[:70]}")
            print()
            total_matches += len(matches)
    
    if total_matches == 0:
        print(f"No packages found matching '{query}'")
        print("\nTry:")
        print("  - Using different search terms")
        print("  - Checking registry status with 'sc-install registry list'")
        return 0
    
    print(f"Found {total_matches} package{'s' if total_matches != 1 else ''} matching '{query}'")
    return 0


def cmd_info(pkg: str, registry: Optional[str] = None) -> int:
    """Display information about a package.
    
    Phase 3 Enhancement: Remote Registry Support
    - Support --registry flag to get info from remote registry
    - Fall back to local package if registry not specified
    
    Args:
        pkg: Package name
        registry: Optional registry name to query
    
    Returns:
        0 on success, 1 on error
    """
    # If registry specified, fetch from remote
    if registry:
        config = _load_config()
        registries = config.get("marketplaces", {}).get("registries", {})
        
        if registry not in registries:
            error(f"Registry not found: {registry}")
            error("Use 'sc-install registry list' to see available registries")
            return 1
        
        reg_info = registries[registry]
        url = reg_info.get("url", "")
        path = reg_info.get("path", "")
        
        registry_json = _fetch_registry_json(url, path)
        if registry_json is None:
            error(f"Failed to fetch registry: {registry}")
            return 1
        
        packages = _parse_registry_metadata(registry_json)
        
        if pkg not in packages:
            error(f"Package not found in registry '{registry}': {pkg}")
            return 1
        
        metadata = packages[pkg]
        print(f"Package: {pkg}")
        print(f"Registry: {registry}")
        print(f"Version: {metadata.get('version', 'unknown')}")
        print(f"Tier: {metadata.get('tier', 'community')}")
        if metadata.get('author'):
            print(f"Author: {metadata['author']}")
        print()
        print(f"Description:")
        print(f"  {metadata.get('description', 'No description available')}")
        
        if metadata.get('dependencies'):
            print()
            print("Dependencies:")
            for dep in metadata['dependencies']:
                print(f"  - {dep}")
        
        if metadata.get('source'):
            print()
            print(f"Source: {metadata['source']}")
        
        return 0
    
    # Default: show local package info
    pkg_dir = PACKAGES_DIR / pkg
    if not pkg_dir.is_dir():
        error(f"Package not found: {pkg}")
        return 1
    manifest_path = pkg_dir / "manifest.yaml"
    if not manifest_path.exists():
        error(f"No manifest.yaml in {pkg}")
        return 1
    print(f"Package: {pkg}")
    print(f"Path: {pkg_dir}")
    print()
    sys.stdout.write(_read_file(manifest_path))
    if not _read_file(manifest_path).endswith("\n"):
        print()
    return 0


def _git_repo_basename(dest_dir: Path) -> str:
    try:
        # Determine toplevel from parent of dest (.claude lives under repo)
        toplevel = (
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=dest_dir.parent,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            ).stdout.strip()
            or ""
        )
        return Path(toplevel).name if toplevel else ""
    except Exception:
        return ""


def _iter_artifacts(m: Manifest) -> Iterable[str]:
    order = ["commands", "skills", "agents", "scripts"]
    for key in order:
        for item in m.artifacts.get(key, []):
            yield item


def _ensure_executable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def _read_repo_version() -> Optional[str]:
    """Read version from repo root version.yaml if present."""
    p = REPO_ROOT / "version.yaml"
    if not p.exists():
        return None
    try:
        if yaml is not None:
            data = yaml.safe_load(_read_file(p)) or {}
            v = data.get("version")
            return str(v) if v is not None else None
        # Fallback: naive parse
        for line in _read_file(p).splitlines():
            if line.strip().startswith("version:"):
                return line.split(":", 1)[1].strip().strip('"')
    except Exception:
        return None
    return None


def _parse_frontmatter_simple(md_path: Path) -> Dict[str, str]:
    """Parse YAML frontmatter at top of a Markdown file (best-effort)."""
    text = _read_file(md_path)
    if not text.startswith("---"):
        return {}
    parts = text.split("\n---\n", 1)
    if len(parts) < 2:
        return {}
    # Extract lines between first '---' and the next '---' occurrence
    lines = text.splitlines()
    fm_lines: List[str] = []
    started = False
    for line in lines:
        if line.strip() == "---" and not started:
            started = True
            continue
        if line.strip() == "---" and started:
            break
        if started:
            fm_lines.append(line)
    fm_text = "\n".join(fm_lines)
    if yaml is not None:
        try:
            data = yaml.safe_load(fm_text) or {}
            return {k: str(v) for k, v in data.items() if isinstance(k, str)}
        except Exception:
            pass
    # naive parse key: value
    out: Dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def _resolve_install_dest(
    global_flag: bool = False,
    local_flag: bool = False,
    user_flag: bool = False,
    project_flag: bool = False,
    dest: Optional[str] = None,
) -> Optional[Path]:
    """Resolve installation destination from --global/--local/--user/--project/--dest flags.

    Phase 1: Support for --global, --local, --user, and --project flags

    Returns:
        Path to .claude directory, or None if invalid combination
    """
    # Count how many flags are set
    flags_set = sum([global_flag, local_flag, user_flag, project_flag, dest is not None])

    if flags_set == 0:
        error("Must specify one of: --global, --local, --user, --project, or --dest")
        return None

    if flags_set > 1:
        error("Cannot combine --global, --local, --user, --project, and --dest flags")
        return None

    if global_flag or user_flag:
        return Path.home() / ".claude"

    if local_flag or project_flag:
        return Path.cwd() / ".claude"

    # dest flag
    if dest:
        if ".claude" not in dest:
            error("--dest must point to a .claude directory")
            return None
        return Path(dest).expanduser().resolve()

    return None


def _update_registry(dest_path: Path, agent_rel_paths: List[str]) -> int:
    """Create or merge .claude/agents/registry.yaml with installed agents and versions.
    Returns 0 on success, 1 on hard validation error.
    """
    if not agent_rel_paths:
        return 0
    registry_dir = dest_path / "agents"
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry_path = registry_dir / "registry.yaml"

    # Load existing registry
    registry: Dict[str, Dict[str, Dict[str, str]]] = {"agents": {}}
    if registry_path.exists():
        try:
            if yaml is not None:
                loaded = yaml.safe_load(_read_file(registry_path)) or {}
                if isinstance(loaded, dict):
                    registry.update(loaded)
            else:
                # naive, ignore existing if no yaml lib
                pass
        except Exception:
            warn(f"Could not parse registry: {registry_path}")

    root_version = _read_repo_version()

    # Merge entries
    for rel in agent_rel_paths:
        if not rel.startswith("agents/"):
            continue
        name = Path(rel).stem
        installed_md = dest_path / rel
        fm = _parse_frontmatter_simple(installed_md)
        ver = fm.get("version") or ""
        if root_version and ver and ver != root_version:
            error(
                f"version mismatch for agent {name}: frontmatter={ver} repo={root_version}"
            )
            return 1
        registry.setdefault("agents", {})[name] = {
            "version": ver or (root_version or ""),
            "path": f".claude/{rel}",
        }

    # Write registry
    try:
        if yaml is not None:
            content = yaml.safe_dump(registry, sort_keys=True)
        else:
            # minimal YAML emit
            lines = ["agents:"]
            for k, v in sorted(registry.get("agents", {}).items()):
                lines.append(f"  {k}:")
                lines.append(f"    version: {v.get('version','')}")
                lines.append(f"    path: {v.get('path','')}")
            content = "\n".join(lines) + "\n"
        registry_path.write_text(content, encoding="utf-8")
        info(f"Updated registry: {registry_path}")
    except Exception as ex:
        warn(f"Could not write registry: {ex}")
        return 1
    return 0


def cmd_install(
    pkg: str,
    dest: Optional[str] = None,
    *,
    force: bool = False,
    expand: bool = True,
    global_flag: bool = False,
    local_flag: bool = False,
    user_flag: bool = False,
    project_flag: bool = False,
    registry: Optional[str] = None,
) -> int:
    """Install a package to a .claude directory.
    
    Phase 3 Enhancement: Remote Registry Support
    - Support --registry flag to install from remote registry
    - Prefer local packages (backward compatible)
    - Fall back to remote if not found locally

    Args:
        pkg: Package name
        dest: Explicit destination path
        force: Overwrite existing files
        expand: Perform token expansion
        global_flag: Install to ~/.claude
        local_flag: Install to ./.claude
        user_flag: Alias for --global
        project_flag: Alias for --local
        registry: Optional registry name to install from
    """
    # Check local package first (backward compatible)
    pkg_dir = PACKAGES_DIR / pkg
    local_exists = pkg_dir.is_dir()
    
    # If registry specified or local doesn't exist, try remote
    if registry or not local_exists:
        if registry:
            config = _load_config()
            registries = config.get("marketplaces", {}).get("registries", {})
            
            if registry not in registries:
                error(f"Registry not found: {registry}")
                error("Use 'sc-install registry list' to see available registries")
                return 1
            
            reg_info = registries[registry]
            url = reg_info.get("url", "")
            path = reg_info.get("path", "")
            
            registry_json = _fetch_registry_json(url, path)
            if registry_json is None:
                error(f"Failed to fetch registry: {registry}")
                return 1
            
            packages = _parse_registry_metadata(registry_json)
            
            if pkg not in packages:
                error(f"Package not found in registry '{registry}': {pkg}")
                return 1
            
            # TODO: Implement remote download and installation
            # For now, just report that remote installation is not yet fully implemented
            warn(f"Remote installation from registry '{registry}' is not yet fully implemented")
            warn("For now, please install packages locally or use manual download")
            return 1
    
    if not local_exists:
        error(f"Package not found: {pkg}")
        return 1

    # Resolve destination (Phase 1: Support --global/--local/--user/--project)
    dest_path = _resolve_install_dest(global_flag, local_flag, user_flag, project_flag, dest)
    if dest_path is None:
        return 1

    # track installed agent files relative to dest_path
    installed_agents: List[str] = []
    dest_path.mkdir(parents=True, exist_ok=True)

    manifest = _parse_manifest(pkg_dir)

    repo_name = ""
    if expand and manifest.variables.get("REPO_NAME", {}).get("auto") == "git-repo-basename":
        repo_name = _git_repo_basename(dest_path)

    info(f"Installing {pkg} to {dest_path}")
    if repo_name:
        info(f"REPO_NAME={repo_name}")

    def install_one(rel_file: str) -> None:
        src = (pkg_dir / rel_file).resolve()
        dst = (dest_path / rel_file).resolve()
        if not src.exists():
            warn(f"Source not found: {src}")
            return
        if dst.exists() and not force:
            warn(f"Skip (exists): {dst}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        # executable for scripts/*
        if rel_file.startswith("scripts/"):
            _ensure_executable(dst)
        # track agents for registry
        if rel_file.startswith("agents/"):
            # store relative to .claude (dest_path)
            installed_agents.append(rel_file)
        # token expansion
        if expand and repo_name:
            try:
                text = dst.read_text(encoding="utf-8", errors="ignore")
                text = text.replace("{{REPO_NAME}}", repo_name)
                dst.write_text(text, encoding="utf-8")
            except Exception:
                # Ignore binary/non-text failures
                pass
        info(f"Installed: {rel_file}")

    for rel in _iter_artifacts(manifest):
        install_one(rel)

    # Update registry.yaml (agents only)
    rc = _update_registry(dest_path, installed_agents)
    if rc != 0:
        return rc

    info(f"Done installing {pkg}")
    return 0


def cmd_uninstall(pkg: str, dest: str) -> int:
    pkg_dir = PACKAGES_DIR / pkg
    if not pkg_dir.is_dir():
        error(f"Package not found: {pkg}")
        return 1
    if not dest:
        error("--dest is required")
        return 1
    dest_path = Path(dest).expanduser().resolve()
    manifest = _parse_manifest(pkg_dir)
    info(f"Uninstalling {pkg} from {dest_path}")

    for rel in _iter_artifacts(manifest):
        dst = dest_path / rel
        if dst.exists():
            try:
                dst.unlink()
                info(f"Removed: {rel}")
            except Exception:
                warn(f"Could not remove: {rel}")
    info(f"Done uninstalling {pkg}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sc-install", add_help=True)
    sub = p.add_subparsers(dest="cmd")

    # Phase 3: Enhanced list command with remote registry support
    p_list = sub.add_parser("list")
    p_list.add_argument("--registry", help="Query specific registry")
    p_list.add_argument("--all-registries", action="store_true", help="Query all registries")
    p_list.add_argument("--search", help="Filter packages by name")

    # Phase 3: Enhanced info command with remote registry support
    p_info = sub.add_parser("info")
    p_info.add_argument("package")
    p_info.add_argument("--registry", help="Get info from remote registry")

    # Phase 3: New search command
    p_search = sub.add_parser("search")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--registry", help="Search specific registry (default: all)")

    # Phase 3: Enhanced install command with remote registry support
    p_install = sub.add_parser("install")
    p_install.add_argument("package")
    # Phase 1: Mutually exclusive destination flags
    dest_group = p_install.add_mutually_exclusive_group(required=True)
    dest_group.add_argument("--dest")
    dest_group.add_argument("--global", dest="global_flag", action="store_true")
    dest_group.add_argument("--user", dest="user_flag", action="store_true")
    dest_group.add_argument("--local", dest="local_flag", action="store_true")
    dest_group.add_argument("--project", dest="project_flag", action="store_true")
    p_install.add_argument("--force", action="store_true")
    p_install.add_argument("--no-expand", action="store_true")
    p_install.add_argument("--registry", help="Install from remote registry")

    p_uninstall = sub.add_parser("uninstall")
    p_uninstall.add_argument("package")
    p_uninstall.add_argument("--dest", required=True)

    # Phase 1: Registry commands
    p_registry = sub.add_parser("registry")
    registry_sub = p_registry.add_subparsers(dest="registry_cmd")

    p_registry_add = registry_sub.add_parser("add")
    p_registry_add.add_argument("name")
    p_registry_add.add_argument("url")
    p_registry_add.add_argument("--path", default="")

    registry_sub.add_parser("list")

    p_registry_remove = registry_sub.add_parser("remove")
    p_registry_remove.add_argument("name")

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    
    # Phase 3: Enhanced list command with remote registry support
    if args.cmd == "list":
        return cmd_list(
            registry=getattr(args, 'registry', None),
            all_registries=getattr(args, 'all_registries', False),
            search=getattr(args, 'search', None),
        )
    
    # Phase 3: Enhanced info command with remote registry support
    if args.cmd == "info":
        return cmd_info(args.package, registry=getattr(args, 'registry', None))
    
    # Phase 3: New search command
    if args.cmd == "search":
        return cmd_search(args.query, registry=getattr(args, 'registry', None))
    
    # Phase 3: Enhanced install command with remote registry support
    if args.cmd == "install":
        return cmd_install(
            args.package,
            args.dest if hasattr(args, 'dest') else None,
            force=args.force,
            expand=not args.no_expand,
            global_flag=getattr(args, 'global_flag', False),
            local_flag=getattr(args, 'local_flag', False),
            user_flag=getattr(args, 'user_flag', False),
            project_flag=getattr(args, 'project_flag', False),
            registry=getattr(args, 'registry', None),
        )
    
    if args.cmd == "uninstall":
        return cmd_uninstall(args.package, args.dest)
    
    if args.cmd == "registry":
        if args.registry_cmd == "add":
            return cmd_registry_add(args.name, args.url, args.path)
        if args.registry_cmd == "list":
            return cmd_registry_list()
        if args.registry_cmd == "remove":
            return cmd_registry_remove(args.name)
        # No registry subcommand
        build_parser().parse_args(["registry", "-h"])
        return 1
    
    # Default: if user passed legacy style without subcommand, show help
    build_parser().print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
