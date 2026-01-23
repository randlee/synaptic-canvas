#!/usr/bin/env python3
"""
Settings fallback pattern for Synaptic Canvas packages.

Implements three-tier fallback: package → shared → user → default

Usage:
    from pathlib import Path
    from settings_fallback_pattern import get_setting

    # In your package code - use exact field names from normative schema

    # Get provider type (required field)
    provider_type = get_setting(
        "provider.type",
        package_name="sc-commit-push-pr",
        repo_root=Path.cwd()
    )

    # Get Azure DevOps org (if type is azuredevops)
    azure_org = get_setting(
        "provider.azure_devops.org",
        package_name="sc-commit-push-pr",
        repo_root=Path.cwd()
    )

    # Get GitHub org (if type is github)
    github_org = get_setting(
        "provider.github.org",
        package_name="sc-commit-push-pr",
        repo_root=Path.cwd()
    )

    # Get protected branches (optional field with default)
    protected = get_setting(
        "git.protected_branches",
        package_name="sc-commit-push-pr",
        repo_root=Path.cwd(),
        default=["main", "master"]
    )

    # Get credential env var name
    github_token_var = get_setting(
        "credentials.github_token",
        package_name="sc-commit-push-pr",
        repo_root=Path.cwd(),
        default="GITHUB_TOKEN"
    )
"""

from pathlib import Path
from typing import Any, Optional
import yaml


def get_setting(
    key: str,
    package_name: str,
    repo_root: Path,
    default: Any = None
) -> Any:
    """
    Get setting using fallback chain: package → shared → user → default

    Args:
        key: Setting key in dot notation (e.g., "provider.azure_devops.org")
        package_name: Package identifier (e.g., "sc-commit-push-pr")
        repo_root: Repository root path
        default: Default value if not found

    Returns:
        Setting value or default
    """
    # 1. Package-specific (highest priority)
    package_path = repo_root / ".sc" / package_name / "settings.yaml"
    if package_path.exists():
        if value := _deep_get(_load_yaml(package_path), key):
            return value

    # 2. Shared repository settings
    shared_path = repo_root / ".sc" / "shared-settings.yaml"
    if shared_path.exists():
        if value := _deep_get(_load_yaml(shared_path), key):
            return value

    # 3. User-global settings
    user_path = Path.home() / ".sc" / package_name / "settings.yaml"
    if user_path.exists():
        if value := _deep_get(_load_yaml(user_path), key):
            return value

    # 4. Default
    return default


def _load_yaml(path: Path) -> Optional[dict]:
    """Load YAML file, return None if error."""
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return None


def _deep_get(d: Optional[dict], key: str) -> Optional[Any]:
    """Get nested key using dot notation: 'provider.azure_devops.org'"""
    if d is None:
        return None
    for k in key.split('.'):
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return None
    return d


def write_package_settings(
    settings: dict,
    package_name: str,
    repo_root: Path
) -> Path:
    """Write package-specific settings (safe to call anytime)."""
    path = repo_root / ".sc" / package_name / "settings.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(settings, sort_keys=False))
    return path


def write_shared_settings(
    settings: dict,
    repo_root: Path,
    user_confirmed: bool = False
) -> Path:
    """
    Write shared repository settings.
    ONLY call from initialization commands with user confirmation.
    """
    if not user_confirmed:
        raise ValueError(
            "Shared settings require user confirmation. "
            "Set user_confirmed=True only in initialization commands."
        )

    path = repo_root / ".sc" / "shared-settings.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing if present
    existing = {}
    if path.exists():
        existing = _load_yaml(path) or {}

    merged = {**existing, **settings}
    path.write_text(yaml.dump(merged, sort_keys=False))
    return path
