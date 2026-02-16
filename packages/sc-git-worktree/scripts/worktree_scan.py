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
    from .envelope import Envelope, ErrorCodes, Transcript
    from .worktree_shared import (
        TrackingEntry,
        get_default_tracking_path,
        get_protected_branches,
        get_repo_name,
        get_repo_root,
        load_tracking_jsonl,
        reconcile_tracking,
        run_git,
    )
except ImportError:
    from envelope import Envelope, ErrorCodes, Transcript
    from worktree_shared import (
        TrackingEntry,
        get_default_tracking_path,
        get_protected_branches,
        get_repo_name,
        get_repo_root,
        load_tracking_jsonl,
        reconcile_tracking,
        run_git,
    )


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




# =============================================================================
# Git Operations
# =============================================================================


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
# Main Scan Logic
# =============================================================================


def scan_worktrees(
    worktree_base: Optional[str] = None,
    tracking_enabled: bool = True,
    tracking_path: Optional[str] = None,
    discover_all: bool = False,
    owner_filter: Optional[str] = None,
    cache_protected_branches: bool = True,
) -> Envelope:
    """Scan all worktrees and reconcile tracking with git state.

    Args:
        worktree_base: Base directory for worktrees (default: ../<repo-name>-worktrees)
        tracking_enabled: Whether to check tracking document
        tracking_path: Path to tracking document (default: <worktree_base>/worktree-tracking.jsonl)
        discover_all: If True, also discover untracked remote branches
        owner_filter: If set, only show branches by this owner

    Returns:
        Envelope with scan results
    """
    transcript = Transcript()

    try:
        repo_root = get_repo_root()
        repo_name = repo_root.name
        transcript.step_ok(
            step="git rev-parse --show-toplevel",
            message=str(repo_root),
        )
    except RuntimeError as e:
        transcript.step_failed(
            step="git rev-parse --show-toplevel",
            error=str(e),
        )
        return Envelope.error_response(
            code=ErrorCodes.GIT_NOT_REPO,
            message=str(e),
            recoverable=False,
            suggested_action="Run this command from within a git repository",
            transcript=transcript,
        )

    # Resolve worktree base path
    if worktree_base:
        wt_base = Path(worktree_base)
    else:
        wt_base = repo_root.parent / f"{repo_name}-worktrees"

    # Resolve tracking path (JSONL format)
    if tracking_enabled:
        if tracking_path:
            track_path = Path(tracking_path)
        else:
            track_path = get_default_tracking_path(wt_base)
    else:
        track_path = None

    # Get worktree list
    try:
        worktrees = get_worktree_list()
        transcript.step_ok(
            step="git worktree list --porcelain",
            message=f"{len(worktrees)} worktree(s)",
        )
    except RuntimeError as e:
        transcript.step_failed(
            step="git worktree list --porcelain",
            error=str(e),
        )
        return Envelope.error_response(
            code=ErrorCodes.GIT_ERROR,
            message=str(e),
            recoverable=False,
            transcript=transcript,
        )

    # Filter to non-bare worktrees (exclude main repo)
    non_bare_worktrees = [wt for wt in worktrees if not wt.is_bare]

    # Batch get statuses
    statuses = batch_get_worktree_statuses(non_bare_worktrees)
    clean_count = sum(1 for s in statuses.values() if s[0] == "clean")
    dirty_count = sum(1 for s in statuses.values() if s[0] == "dirty")
    transcript.step_ok(
        step="git status --porcelain (batch)",
        message=f"clean={clean_count} dirty={dirty_count}",
    )

    # Reconcile tracking with git state
    tracking_entries: List[TrackingEntry] = []
    reconcile_result: Dict[str, Any] = {}
    remote_warnings: List[Dict[str, Any]] = []
    discovered_branches: List[Dict[str, Any]] = []
    removed_branches: List[str] = []

    if tracking_enabled and track_path:
        # Get protected branches for reconciliation
        try:
            protected = get_protected_branches(
                repo_root,
                cache_shared=cache_protected_branches,
                log_fn=lambda msg: transcript.step_ok(step="protected branches", message=msg),
            )
        except ValueError as e:
            transcript.step_failed(
                step="resolve protected branches",
                error=str(e),
            )
            return Envelope.error_response(
                code=ErrorCodes.CONFIG_PROTECTED_BRANCH_NOT_SET,
                message=str(e),
                recoverable=False,
                suggested_action="Configure git.protected_branches in .sc/shared-settings.yaml",
                transcript=transcript,
            )

        # Reconcile tracking with git (always runs fetch)
        reconcile_result = reconcile_tracking(
            tracking_path=track_path,
            repo_root=repo_root,
            discover_all=discover_all,
            protected_branches=protected,
        )

        transcript.step_ok(
            step="git fetch --all --prune",
            message=f"reconciled {reconcile_result['total']} entries",
        )

        if reconcile_result.get("removed"):
            removed_branches = reconcile_result["removed"]
            transcript.step_ok(
                step="prune tracking",
                message=f"removed {len(removed_branches)} stale entries",
            )

        if reconcile_result.get("discovered"):
            discovered_branches = reconcile_result["discovered"]
            transcript.step_ok(
                step="discover branches",
                message=f"found {len(discovered_branches)} new branches",
            )

        remote_warnings = reconcile_result.get("warnings", [])

        # Load reconciled entries
        tracking_entries = load_tracking_jsonl(track_path)

        # Apply owner filter if specified
        if owner_filter:
            tracking_entries = [e for e in tracking_entries if e.owner == owner_filter]
            transcript.step_ok(
                step=f"filter owner={owner_filter}",
                message=f"{len(tracking_entries)} entries match",
            )
    else:
        transcript.step_skipped(step="reconcile_tracking", message="disabled")

    # Build sets for cross-reference
    worktree_branches = {wt.branch for wt in non_bare_worktrees}
    tracked_branches = {entry.branch for entry in tracking_entries}

    # Find orphaned remotes (tracked but no local worktree)
    orphaned_remotes = [
        {"branch": e.branch, "owner": e.owner, "remote_exists": e.remote_exists}
        for e in tracking_entries
        if not e.local_worktree and e.remote_exists
    ]

    # Find untracked local worktrees
    untracked_worktrees = [
        wt.branch for wt in non_bare_worktrees
        if wt.branch not in tracked_branches and wt.path != str(repo_root)
    ]

    # Build results
    worktree_results: List[Dict[str, Any]] = []
    recommendations: List[str] = []

    for wt in non_bare_worktrees:
        status, dirty_files, error_msg = statuses.get(wt.path, ("error", [], "Status not found"))

        # Find matching tracking entry
        tracking_entry_data = None
        remote_ahead = 0
        for entry in tracking_entries:
            if entry.branch == wt.branch:
                tracking_entry_data = {
                    "branch": entry.branch,
                    "path": entry.path,
                    "base": entry.base,
                    "purpose": entry.purpose,
                    "owner": entry.owner,
                    "created": entry.created,
                    "status": entry.status,
                    "last_checked": entry.last_checked,
                    "notes": entry.notes,
                    "remote_exists": entry.remote_exists,
                    "local_worktree": entry.local_worktree,
                    "remote_ahead": entry.remote_ahead,
                }
                remote_ahead = entry.remote_ahead
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
        if remote_ahead > 0:
            issues.append(f"remote_ahead: {remote_ahead} commit(s)")

        worktree_results.append({
            "branch": wt.branch,
            "path": wt.path,
            "head": wt.head[:8] if wt.head else "",
            "status": status,
            "dirty_files": dirty_files if dirty_files else None,
            "tracked": wt.branch in tracked_branches,
            "tracking_entry": tracking_entry_data,
            "issues": issues if issues else None,
            "is_detached": wt.is_detached,
            "is_locked": wt.is_locked,
            "prunable": wt.prunable,
            "remote_ahead": remote_ahead if remote_ahead > 0 else None,
        })

    # Generate recommendations
    dirty_count = sum(1 for wt in worktree_results if wt["status"] == "dirty")
    if dirty_count > 0:
        recommendations.append(f"commit or stash changes in {dirty_count} dirty worktree(s)")

    if orphaned_remotes:
        recommendations.append(f"run cleanup to delete {len(orphaned_remotes)} orphaned remote branch(es)")

    if untracked_worktrees:
        recommendations.append(f"{len(untracked_worktrees)} worktree(s) not in tracking")

    prunable_count = sum(1 for wt in non_bare_worktrees if wt.prunable)
    if prunable_count > 0:
        recommendations.append(f"run 'git worktree prune' to clean {prunable_count} stale reference(s)")

    # Warn about remote-ahead branches
    remote_ahead_count = sum(1 for wt in worktree_results if wt.get("remote_ahead"))
    if remote_ahead_count > 0:
        recommendations.append(f"pull changes in {remote_ahead_count} branch(es) where remote is ahead")

    return Envelope.success_response(
        data={
            "action": "scan",
            "repo_root": str(repo_root),
            "worktree_base": str(wt_base),
            "worktrees": worktree_results,
            "tracking_enabled": tracking_enabled,
            "tracking_path": str(track_path) if track_path else None,
            "orphaned_remotes": orphaned_remotes if orphaned_remotes else None,
            "untracked_worktrees": untracked_worktrees if untracked_worktrees else None,
            "discovered_branches": discovered_branches if discovered_branches else None,
            "removed_entries": removed_branches if removed_branches else None,
            "remote_warnings": remote_warnings if remote_warnings else None,
            "recommendations": recommendations if recommendations else None,
            "summary": {
                "total_worktrees": len(non_bare_worktrees),
                "clean": sum(1 for wt in worktree_results if wt["status"] == "clean"),
                "dirty": dirty_count,
                "errors": sum(1 for wt in worktree_results if wt["status"] == "error"),
                "tracked": sum(1 for wt in worktree_results if wt["tracked"]),
                "untracked": len(untracked_worktrees),
                "orphaned_remotes": len(orphaned_remotes),
                "remote_ahead": remote_ahead_count,
            },
        },
        transcript=transcript,
    )


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
        help="Path to tracking document (default: <worktree-base>/worktree-tracking.jsonl)",
    )
    parser.add_argument(
        "--no-tracking",
        action="store_true",
        help="Disable tracking document cross-check",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Discover all remote branches (feature/*, hotfix/*, etc.) and add to tracking",
    )
    parser.add_argument(
        "--owner",
        type=str,
        default=None,
        help="Filter results to branches created by this owner",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not cache protected branches to shared settings",
    )

    args = parser.parse_args()

    result = scan_worktrees(
        worktree_base=args.worktree_base,
        tracking_enabled=not args.no_tracking,
        tracking_path=args.tracking_path,
        discover_all=args.all,
        owner_filter=args.owner,
        cache_protected_branches=not args.no_cache,
    )

    # Output fenced JSON
    print(result.to_fenced_json())

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
