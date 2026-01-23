#!/usr/bin/env python3
"""Shared utilities for preflight hook scripts.

Provides common functions for:
- Loading/saving shared settings
- Detecting git-flow branches
- Validating git authentication
- Logging preflight events
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


# Package name for logging
PACKAGE_NAME = "sc-commit-push-pr"


def get_repo_root() -> Path:
    """Get the repository root directory.

    Returns:
        Path to the repository root

    Raises:
        RuntimeError: If not in a git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Not in a git repository: {e.stderr}") from e


def load_shared_settings(repo_root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load shared settings with fallback to user-global settings.

    Args:
        repo_root: Repository root path. If None, auto-detects.

    Returns:
        Settings dictionary or None if not found
    """
    if repo_root is None:
        try:
            repo_root = get_repo_root()
        except RuntimeError:
            repo_root = Path.cwd()

    # Try repo-level shared settings first
    shared_path = repo_root / ".sc" / "shared-settings.yaml"
    if shared_path.exists():
        try:
            settings = yaml.safe_load(shared_path.read_text())
            if settings:
                return settings
        except Exception:
            pass

    # Fallback to user-global settings
    user_path = Path.home() / ".sc" / "shared-settings.yaml"
    if user_path.exists():
        try:
            settings = yaml.safe_load(user_path.read_text())
            if settings:
                return settings
        except Exception:
            pass

    return None


def get_protected_branches(settings: Optional[Dict[str, Any]]) -> Optional[List[str]]:
    """Extract protected branches from settings.

    Args:
        settings: Settings dictionary

    Returns:
        List of protected branch names, or None if not configured
    """
    if not settings:
        return None

    git_config = settings.get("git", {})
    if not isinstance(git_config, dict):
        return None

    branches = git_config.get("protected_branches")
    if isinstance(branches, list) and branches:
        return branches

    return None


def detect_gitflow_branches() -> Optional[List[str]]:
    """Detect protected branches from git-flow configuration.

    Returns:
        List of protected branches if git-flow is configured, None otherwise
    """
    protected = []

    try:
        # Check for git-flow master branch
        result = subprocess.run(
            ["git", "config", "--get", "gitflow.branch.master"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            protected.append(result.stdout.strip())
    except Exception:
        pass

    try:
        # Check for git-flow develop branch
        result = subprocess.run(
            ["git", "config", "--get", "gitflow.branch.develop"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            protected.append(result.stdout.strip())
    except Exception:
        pass

    return protected if protected else None


def save_shared_settings(
    settings: Dict[str, Any],
    repo_root: Optional[Path] = None
) -> Path:
    """Save shared settings to the repository.

    Args:
        settings: Settings dictionary to save
        repo_root: Repository root path. If None, auto-detects.

    Returns:
        Path to the saved settings file
    """
    if repo_root is None:
        repo_root = get_repo_root()

    shared_path = repo_root / ".sc" / "shared-settings.yaml"
    shared_path.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing settings if present
    existing = {}
    if shared_path.exists():
        try:
            existing = yaml.safe_load(shared_path.read_text()) or {}
        except Exception:
            pass

    # Deep merge: prioritize new settings
    merged = _deep_merge(existing, settings)
    shared_path.write_text(yaml.dump(merged, sort_keys=False, default_flow_style=False))

    return shared_path


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_git_auth() -> Tuple[bool, str]:
    """Validate git authentication by checking remote access.

    Returns:
        Tuple of (success, message)
    """
    try:
        # First check if we have a remote
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False, "No 'origin' remote configured"

        remote_url = result.stdout.strip()

        # Use git ls-remote to test auth without fetching data
        # This is the lightest way to verify credentials work
        result = subprocess.run(
            ["git", "ls-remote", "--exit-code", "origin", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,  # 30 second timeout
        )

        if result.returncode == 0:
            return True, "Git authentication successful"

        # Check for common auth errors
        stderr = result.stderr.lower()
        if "authentication" in stderr or "permission" in stderr or "denied" in stderr:
            return False, "Git authentication failed - check credentials"
        elif "could not resolve" in stderr or "unable to access" in stderr:
            return False, "Unable to access remote - check network connection"
        else:
            return False, f"Git remote access failed: {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return False, "Git remote access timed out"
    except Exception as e:
        return False, f"Git validation error: {str(e)}"


def get_log_dir(repo_root: Optional[Path] = None) -> Path:
    """Get the log directory for this package.

    Args:
        repo_root: Repository root path. If None, auto-detects.

    Returns:
        Path to the log directory
    """
    if repo_root is None:
        try:
            repo_root = get_repo_root()
        except RuntimeError:
            repo_root = Path.cwd()

    log_dir = repo_root / ".claude" / "state" / "logs" / PACKAGE_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def log_preflight(
    level: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None
) -> Path:
    """Log a preflight event to the standard log file.

    Args:
        level: Log level ("info", "error", "warn", "debug")
        message: Log message
        context: Optional additional context data
        repo_root: Repository root path. If None, auto-detects.

    Returns:
        Path to the log file
    """
    log_dir = get_log_dir(repo_root)

    # Create timestamp for both filename and log entry
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()

    # Log entry following the standard format
    log_entry = {
        "timestamp": timestamp,
        "level": level.lower(),
        "message": message,
        "context": context or {},
    }

    # Use date-based log file for aggregation
    log_file = log_dir / f"preflight-{now.strftime('%Y-%m-%d')}.jsonl"

    # Append to log file (newline-delimited JSON)
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return log_file


def run_preflight_check(hook_name: str) -> int:
    """Run the complete preflight check sequence.

    Args:
        hook_name: Name of the hook for logging purposes

    Returns:
        Exit code (0 = allow, 2 = block)
    """
    try:
        repo_root = get_repo_root()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Step 1: Check for protected branches in shared settings
    settings = load_shared_settings(repo_root)
    protected_branches = get_protected_branches(settings)

    if protected_branches:
        # Found in settings - log and continue
        log_preflight(
            level="info",
            message=f"Preflight check passed ({hook_name})",
            context={
                "hook": hook_name,
                "source": "shared_settings",
                "protected_branches": protected_branches,
            },
            repo_root=repo_root,
        )
    else:
        # Step 2: Try git-flow detection
        gitflow_branches = detect_gitflow_branches()

        if gitflow_branches:
            # Step 3: Auto-create shared settings with detected values
            save_shared_settings(
                {"git": {"protected_branches": gitflow_branches}},
                repo_root,
            )

            log_preflight(
                level="info",
                message=f"Auto-detected git-flow branches ({hook_name})",
                context={
                    "hook": hook_name,
                    "source": "gitflow_detection",
                    "protected_branches": gitflow_branches,
                },
                repo_root=repo_root,
            )

            protected_branches = gitflow_branches
        else:
            # Step 4: Not found anywhere - exit with error
            error_msg = (
                "ERROR: Protected branches not configured.\n\n"
                "Create .sc/shared-settings.yaml with:\n"
                "git:\n"
                "  protected_branches: [main, develop]"
            )
            print(error_msg, file=sys.stderr)

            log_preflight(
                level="error",
                message=f"Preflight check failed - no protected branches configured ({hook_name})",
                context={
                    "hook": hook_name,
                    "error": "CONFIG.PROTECTED_BRANCH_NOT_SET",
                },
                repo_root=repo_root,
            )

            return 2

    # Step 5: Validate git authentication
    auth_success, auth_message = validate_git_auth()

    if not auth_success:
        print(f"ERROR: {auth_message}", file=sys.stderr)

        log_preflight(
            level="error",
            message=f"Git authentication failed ({hook_name})",
            context={
                "hook": hook_name,
                "error": "GIT.AUTH",
                "details": auth_message,
            },
            repo_root=repo_root,
        )

        return 2

    # All checks passed
    log_preflight(
        level="info",
        message=f"All preflight checks passed ({hook_name})",
        context={
            "hook": hook_name,
            "protected_branches": protected_branches,
            "git_auth": "valid",
        },
        repo_root=repo_root,
    )

    return 0
