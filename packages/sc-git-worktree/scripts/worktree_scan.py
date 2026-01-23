#!/usr/bin/env python3
"""Batch worktree scan for sc-git-worktree.

This script efficiently scans all worktrees and their status in a single
invocation, minimizing git process spawns.

Usage:
    python worktree_scan.py [--worktree-base PATH] [--tracking-path PATH] [--no-tracking]

Exit Codes:
    0: Scan completed successfully
    1: Error during scan
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Support both relative import (when used as package) and absolute import (when used standalone)
try:
    from .envelope import Envelope, ErrorCodes
except ImportError:
    from envelope import Envelope, ErrorCodes


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WorktreeInfo:
    """Information about a single worktree."""

    path: str
    branch: str
    head: str
    is_bare: bool = False
    is_detached: bool = False
    is_locked: bool = False
    lock_reason: Optional[str] = None
    prunable: bool = False
    prunable_reason: Optional[str] = None


@dataclass
class WorktreeStatus:
    """Status information for a worktree."""

    path: str
    branch: str
    status: str  # "clean", "dirty", "error"
    dirty_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    tracked: bool = False
    tracking_row: Optional[Dict[str, Any]] = None
    issues: List[str] = field(default_factory=list)


@dataclass
class TrackingRow:
    """A row from the tracking document."""

    branch: str
    path: str
    base: Optional[str] = None
    purpose: Optional[str] = None
    owner: Optional[str] = None
    created: Optional[str] = None
    status: Optional[str] = None
    last_checked: Optional[str] = None
    notes: Optional[str] = None


# =============================================================================
# Git Operations
# =============================================================================


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


def get_repo_name() -> str:
    """Get the repository name from the root directory."""
    return get_repo_root().name


def parse_worktree_list_porcelain(output: str) -> List[WorktreeInfo]:
    """Parse git worktree list --porcelain output.

    The porcelain format uses blank lines to separate worktrees.
    Each worktree has:
      - worktree <path>
      - HEAD <sha>
      - branch refs/heads/<name> OR detached
      - Optional: bare, locked [<reason>], prunable [<reason>]

    Args:
        output: Raw output from git worktree list --porcelain

    Returns:
        List of WorktreeInfo objects
    """
    worktrees = []
    current: Dict[str, Any] = {}

    for line in output.strip().split("\n"):
        line = line.strip()

        if not line:
            # Blank line = end of worktree entry
            if current.get("path"):
                worktrees.append(
                    WorktreeInfo(
                        path=current.get("path", ""),
                        branch=current.get("branch", ""),
                        head=current.get("head", ""),
                        is_bare=current.get("bare", False),
                        is_detached=current.get("detached", False),
                        is_locked=current.get("locked", False),
                        lock_reason=current.get("lock_reason"),
                        prunable=current.get("prunable", False),
                        prunable_reason=current.get("prunable_reason"),
                    )
                )
            current = {}
            continue

        if line.startswith("worktree "):
            current["path"] = line[9:]
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            # Extract branch name from refs/heads/<name>
            ref = line[7:]
            if ref.startswith("refs/heads/"):
                current["branch"] = ref[11:]
            else:
                current["branch"] = ref
        elif line == "detached":
            current["detached"] = True
            current["branch"] = "(detached)"
        elif line == "bare":
            current["bare"] = True
        elif line.startswith("locked"):
            current["locked"] = True
            if " " in line:
                current["lock_reason"] = line.split(" ", 1)[1]
        elif line.startswith("prunable"):
            current["prunable"] = True
            if " " in line:
                current["prunable_reason"] = line.split(" ", 1)[1]

    # Don't forget the last entry (if no trailing newline)
    if current.get("path"):
        worktrees.append(
            WorktreeInfo(
                path=current.get("path", ""),
                branch=current.get("branch", ""),
                head=current.get("head", ""),
                is_bare=current.get("bare", False),
                is_detached=current.get("detached", False),
                is_locked=current.get("locked", False),
                lock_reason=current.get("lock_reason"),
                prunable=current.get("prunable", False),
                prunable_reason=current.get("prunable_reason"),
            )
        )

    return worktrees


def get_worktree_list() -> List[WorktreeInfo]:
    """Get list of all worktrees using git worktree list --porcelain.

    Returns:
        List of WorktreeInfo objects

    Raises:
        RuntimeError: If git command fails
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return parse_worktree_list_porcelain(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to list worktrees: {e.stderr}") from e


def batch_get_worktree_statuses(worktrees: List[WorktreeInfo]) -> Dict[str, Tuple[str, List[str], Optional[str]]]:
    """Get status for all worktrees in a batched manner.

    This function runs git status for each worktree but does so efficiently
    by collecting all results in a single pass.

    Args:
        worktrees: List of worktrees to check

    Returns:
        Dict mapping path to (status, dirty_files, error_message)
        where status is "clean", "dirty", or "error"
    """
    results: Dict[str, Tuple[str, List[str], Optional[str]]] = {}

    for wt in worktrees:
        if wt.is_bare:
            results[wt.path] = ("clean", [], None)
            continue

        if not Path(wt.path).exists():
            results[wt.path] = ("error", [], f"Worktree path does not exist: {wt.path}")
            continue

        try:
            result = subprocess.run(
                ["git", "-C", wt.path, "status", "--short", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,  # 10 second timeout per worktree
            )

            output = result.stdout.strip()
            if output:
                # Has uncommitted changes
                dirty_files = [line for line in output.split("\n") if line.strip()]
                results[wt.path] = ("dirty", dirty_files, None)
            else:
                results[wt.path] = ("clean", [], None)

        except subprocess.TimeoutExpired:
            results[wt.path] = ("error", [], f"Status check timed out for {wt.path}")
        except subprocess.CalledProcessError as e:
            results[wt.path] = ("error", [], f"Git status failed: {e.stderr.strip()}")
        except Exception as e:
            results[wt.path] = ("error", [], f"Unexpected error: {str(e)}")

    return results


# =============================================================================
# Tracking Document Operations
# =============================================================================


def parse_tracking_document(content: str) -> List[TrackingRow]:
    """Parse the markdown tracking document.

    Expected format is a markdown table with headers:
    | Branch | Path | Base | Purpose | Owner | Created | Status | LastChecked | Notes |

    Args:
        content: Raw content of the tracking document

    Returns:
        List of TrackingRow objects
    """
    rows = []
    lines = content.strip().split("\n")

    # Find the table (look for | at start of line)
    in_table = False
    headers: List[str] = []

    for line in lines:
        line = line.strip()

        if not line.startswith("|"):
            in_table = False
            continue

        # Parse table row
        cells = [c.strip() for c in line.split("|")[1:-1]]  # Remove first/last empty cells

        if not in_table:
            # This is the header row
            headers = [h.lower().replace(" ", "_") for h in cells]
            in_table = True
            continue

        # Skip separator row (contains only dashes and colons)
        if all(re.match(r"^[-:]+$", c) for c in cells):
            continue

        # Data row - map cells to headers
        row_data = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                row_data[headers[i]] = cell if cell else None

        if row_data.get("branch"):
            rows.append(
                TrackingRow(
                    branch=row_data.get("branch", ""),
                    path=row_data.get("path", ""),
                    base=row_data.get("base"),
                    purpose=row_data.get("purpose"),
                    owner=row_data.get("owner"),
                    created=row_data.get("created"),
                    status=row_data.get("status"),
                    last_checked=row_data.get("lastchecked") or row_data.get("last_checked"),
                    notes=row_data.get("notes"),
                )
            )

    return rows


def load_tracking_document(tracking_path: Path) -> Optional[List[TrackingRow]]:
    """Load and parse the tracking document.

    Args:
        tracking_path: Path to the tracking document

    Returns:
        List of TrackingRow objects, or None if file doesn't exist
    """
    if not tracking_path.exists():
        return None

    try:
        content = tracking_path.read_text(encoding="utf-8")
        return parse_tracking_document(content)
    except Exception:
        return None


# =============================================================================
# Main Scan Logic
# =============================================================================


def scan_worktrees(
    worktree_base: Optional[str] = None,
    tracking_enabled: bool = True,
    tracking_path: Optional[str] = None,
) -> Envelope:
    """Scan all worktrees and cross-check against tracking document.

    Args:
        worktree_base: Base directory for worktrees (default: ../<repo-name>-worktrees)
        tracking_enabled: Whether to check tracking document
        tracking_path: Path to tracking document (default: <worktree_base>/worktree-tracking.md)

    Returns:
        Envelope with scan results
    """
    try:
        repo_root = get_repo_root()
        repo_name = repo_root.name
    except RuntimeError as e:
        return Envelope.error_response(
            code=ErrorCodes.GIT_NOT_REPO,
            message=str(e),
            recoverable=False,
            suggested_action="Run this command from within a git repository",
        )

    # Resolve worktree base path
    if worktree_base:
        wt_base = Path(worktree_base)
    else:
        wt_base = repo_root.parent / f"{repo_name}-worktrees"

    # Resolve tracking path
    if tracking_enabled:
        if tracking_path:
            track_path = Path(tracking_path)
        else:
            track_path = wt_base / "worktree-tracking.md"
    else:
        track_path = None

    # Get worktree list
    try:
        worktrees = get_worktree_list()
    except RuntimeError as e:
        return Envelope.error_response(
            code=ErrorCodes.GIT_ERROR,
            message=str(e),
            recoverable=False,
        )

    # Filter to non-bare worktrees (exclude main repo)
    non_bare_worktrees = [wt for wt in worktrees if not wt.is_bare]

    # Batch get statuses
    statuses = batch_get_worktree_statuses(non_bare_worktrees)

    # Load tracking document if enabled
    tracking_rows: List[TrackingRow] = []
    tracking_missing_rows: List[Dict[str, str]] = []
    tracking_extra_rows: List[Dict[str, str]] = []

    if tracking_enabled and track_path:
        loaded_rows = load_tracking_document(track_path)
        if loaded_rows is None:
            # Tracking doc doesn't exist - report but don't fail
            tracking_missing_rows.append({
                "issue": "tracking_document_missing",
                "path": str(track_path),
            })
        else:
            tracking_rows = loaded_rows

    # Build worktree path set for cross-reference
    worktree_paths = {wt.path for wt in non_bare_worktrees}
    worktree_branches = {wt.branch for wt in non_bare_worktrees}

    # Cross-reference tracking with actual worktrees
    tracked_branches = set()
    for row in tracking_rows:
        tracked_branches.add(row.branch)
        # Check if tracked worktree actually exists
        if row.branch not in worktree_branches:
            tracking_extra_rows.append({
                "branch": row.branch,
                "path": row.path or "",
                "issue": "tracking_row_has_no_worktree",
            })

    # Check for worktrees not in tracking
    for wt in non_bare_worktrees:
        if tracking_enabled and wt.branch not in tracked_branches:
            # Skip main repo worktree (usually the first one)
            if wt.path != str(repo_root):
                tracking_missing_rows.append({
                    "branch": wt.branch,
                    "path": wt.path,
                    "issue": "worktree_not_tracked",
                })

    # Build results
    worktree_results: List[Dict[str, Any]] = []
    recommendations: List[str] = []

    for wt in non_bare_worktrees:
        status, dirty_files, error_msg = statuses.get(wt.path, ("error", [], "Status not found"))

        # Find matching tracking row
        tracking_row_data = None
        for row in tracking_rows:
            if row.branch == wt.branch:
                tracking_row_data = {
                    "branch": row.branch,
                    "path": row.path,
                    "base": row.base,
                    "purpose": row.purpose,
                    "owner": row.owner,
                    "created": row.created,
                    "status": row.status,
                    "last_checked": row.last_checked,
                    "notes": row.notes,
                }
                break

        issues = []
        if status == "dirty":
            issues.append("uncommitted_changes")
        if status == "error":
            issues.append(f"status_error: {error_msg}")
        if wt.is_locked:
            issues.append(f"locked: {wt.lock_reason or 'no reason given'}")
        if wt.prunable:
            issues.append(f"prunable: {wt.prunable_reason or 'worktree may be stale'}")

        worktree_results.append({
            "branch": wt.branch,
            "path": wt.path,
            "head": wt.head[:8] if wt.head else "",
            "status": status,
            "dirty_files": dirty_files if dirty_files else None,
            "tracked": wt.branch in tracked_branches,
            "tracking_row": tracking_row_data,
            "issues": issues if issues else None,
            "is_detached": wt.is_detached,
            "is_locked": wt.is_locked,
            "prunable": wt.prunable,
        })

    # Generate recommendations
    dirty_count = sum(1 for wt in worktree_results if wt["status"] == "dirty")
    if dirty_count > 0:
        recommendations.append(f"commit or stash changes in {dirty_count} dirty worktree(s)")

    if tracking_extra_rows:
        recommendations.append(f"remove {len(tracking_extra_rows)} stale tracking row(s)")

    if tracking_missing_rows:
        missing_wt_count = sum(1 for r in tracking_missing_rows if r.get("issue") == "worktree_not_tracked")
        if missing_wt_count > 0:
            recommendations.append(f"add tracking for {missing_wt_count} untracked worktree(s)")

    prunable_count = sum(1 for wt in non_bare_worktrees if wt.prunable)
    if prunable_count > 0:
        recommendations.append(f"run 'git worktree prune' to clean {prunable_count} stale reference(s)")

    return Envelope.success_response({
        "action": "scan",
        "repo_root": str(repo_root),
        "worktree_base": str(wt_base),
        "worktrees": worktree_results,
        "tracking_enabled": tracking_enabled,
        "tracking_path": str(track_path) if track_path else None,
        "tracking_missing_rows": tracking_missing_rows if tracking_missing_rows else None,
        "tracking_extra_rows": tracking_extra_rows if tracking_extra_rows else None,
        "recommendations": recommendations if recommendations else None,
        "summary": {
            "total_worktrees": len(non_bare_worktrees),
            "clean": sum(1 for wt in worktree_results if wt["status"] == "clean"),
            "dirty": dirty_count,
            "errors": sum(1 for wt in worktree_results if wt["status"] == "error"),
            "tracked": sum(1 for wt in worktree_results if wt["tracked"]),
            "untracked": sum(1 for wt in worktree_results if not wt["tracked"]),
        },
    })


# =============================================================================
# CLI Interface
# =============================================================================


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Scan git worktrees and cross-check tracking document"
    )
    parser.add_argument(
        "--worktree-base",
        type=str,
        default=None,
        help="Base directory for worktrees (default: ../<repo-name>-worktrees)",
    )
    parser.add_argument(
        "--tracking-path",
        type=str,
        default=None,
        help="Path to tracking document (default: <worktree-base>/worktree-tracking.md)",
    )
    parser.add_argument(
        "--no-tracking",
        action="store_true",
        help="Disable tracking document cross-check",
    )

    args = parser.parse_args()

    result = scan_worktrees(
        worktree_base=args.worktree_base,
        tracking_enabled=not args.no_tracking,
        tracking_path=args.tracking_path,
    )

    # Output fenced JSON
    print(result.to_fenced_json())

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
