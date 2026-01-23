#!/usr/bin/env python3
"""Clean up a git worktree with protected branch safeguards.

This script removes a worktree and optionally deletes the branch (for non-protected
branches only). It handles tracking document updates when enabled.

Usage:
    python worktree_cleanup.py '<json-input>'
    echo '<json-input>' | python worktree_cleanup.py

Exit Codes:
    0: Cleanup completed successfully
    1: Error during cleanup
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

try:
    from .envelope import Envelope, ErrorCodes
except ImportError:
    from envelope import Envelope, ErrorCodes


# =============================================================================
# Input Models
# =============================================================================


class CleanupInput(BaseModel):
    """Input schema for worktree cleanup."""

    branch: str = Field(..., description="Branch/worktree name to clean up")
    protected_branches: List[str] = Field(..., description="List of protected branch names")
    path: Optional[str] = Field(None, description="Worktree path")
    merged: Optional[bool] = Field(None, description="Whether branch is merged")
    require_clean: bool = Field(True, description="Require clean worktree")
    repo_root: Optional[str] = Field(None, description="Repo root directory")
    tracking_enabled: bool = Field(True, description="Whether to update tracking doc")
    tracking_path: Optional[str] = Field(None, description="Path to tracking document")
    worktree_base: Optional[str] = Field(None, description="Base directory for worktrees")

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("branch name cannot be empty")
        return v.strip()

    @field_validator("protected_branches")
    @classmethod
    def validate_protected_branches(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("protected_branches list required but not provided")
        return [b.strip() for b in v if b.strip()]


# =============================================================================
# Git Operations
# =============================================================================


def run_git(args: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Execute a git command."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def get_repo_root(cwd: Optional[Path] = None) -> Path:
    """Get the repository root directory."""
    result = run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(result.stdout.strip())


def get_repo_name(repo_root: Path) -> str:
    """Get the repository name from its root path."""
    return repo_root.name


def get_worktree_status(path: Path) -> tuple[bool, List[str]]:
    """Check if worktree is clean."""
    result = run_git(["status", "--short"], cwd=path, check=False)
    if result.returncode != 0:
        return False, [f"git status failed: {result.stderr}"]
    dirty_files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    return len(dirty_files) == 0, dirty_files


def is_branch_merged(branch: str, base: str = "HEAD", cwd: Optional[Path] = None) -> bool:
    """Check if branch is merged into base."""
    result = run_git(["branch", "--merged", base], cwd=cwd, check=False)
    if result.returncode != 0:
        return False
    merged_branches = [b.strip().lstrip("* ") for b in result.stdout.strip().split("\n")]
    return branch in merged_branches


def count_unique_commits(branch: str, base: str = "HEAD", cwd: Optional[Path] = None) -> int:
    """Count commits in branch not in base."""
    result = run_git(["rev-list", "--count", f"{base}..{branch}"], cwd=cwd, check=False)
    if result.returncode != 0:
        return -1
    try:
        return int(result.stdout.strip())
    except ValueError:
        return -1


def remove_worktree(path: Path, force: bool = False, cwd: Optional[Path] = None) -> bool:
    """Remove a worktree."""
    args = ["worktree", "remove", str(path)]
    if force:
        args.append("--force")
    result = run_git(args, cwd=cwd, check=False)
    return result.returncode == 0


def delete_local_branch(branch: str, force: bool = False, cwd: Optional[Path] = None) -> bool:
    """Delete a local branch."""
    flag = "-D" if force else "-d"
    result = run_git(["branch", flag, branch], cwd=cwd, check=False)
    return result.returncode == 0


def delete_remote_branch(branch: str, cwd: Optional[Path] = None) -> tuple[bool, str]:
    """Delete a remote branch. Returns (success, message)."""
    result = run_git(["push", "origin", "--delete", branch], cwd=cwd, check=False)
    if result.returncode == 0:
        return True, "deleted"
    if "remote ref does not exist" in result.stderr:
        return True, "already absent"
    return False, result.stderr


# =============================================================================
# Tracking Document
# =============================================================================


def remove_tracking_row(tracking_path: Path, branch: str) -> bool:
    """Remove a row from the tracking document."""
    if not tracking_path.exists():
        return False

    content = tracking_path.read_text()
    lines = content.split("\n")
    new_lines = []
    removed = False

    for line in lines:
        # Check if this line is a table row for the branch
        if line.startswith("|") and f"| {branch} |" in line or f"|{branch}|" in line:
            removed = True
            continue
        new_lines.append(line)

    if removed:
        tracking_path.write_text("\n".join(new_lines))

    return removed


# =============================================================================
# Main Logic
# =============================================================================


def cleanup_worktree_main(input_data: CleanupInput) -> Envelope:
    """Main worktree cleanup logic."""
    try:
        # Determine repo root
        if input_data.repo_root:
            repo_root = Path(input_data.repo_root).resolve()
        else:
            repo_root = get_repo_root()

        repo_name = get_repo_name(repo_root)

        # Check if branch is protected
        is_protected = input_data.branch in input_data.protected_branches

        # Determine worktree base and path
        if input_data.worktree_base:
            worktree_base = Path(input_data.worktree_base).resolve()
        else:
            worktree_base = repo_root.parent / f"{repo_name}-worktrees"

        if input_data.path:
            worktree_path = Path(input_data.path).resolve()
        else:
            worktree_path = worktree_base / input_data.branch

        # Check if worktree exists
        if not worktree_path.exists():
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_NOT_FOUND,
                message=f"Worktree not found at: {worktree_path}",
                recoverable=False,
            )

        # Check if worktree is clean
        is_clean, dirty_files = get_worktree_status(worktree_path)
        if not is_clean and input_data.require_clean:
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_DIRTY,
                message="Worktree has uncommitted changes",
                recoverable=True,
                suggested_action="Commit/stash changes or set require_clean: false",
                data={"dirty_files": dirty_files},
            )

        # Check merge state
        if input_data.merged is not None:
            is_merged = input_data.merged
        else:
            is_merged = is_branch_merged(input_data.branch, cwd=repo_root)

        unique_commits = count_unique_commits(input_data.branch, cwd=repo_root)

        # If not merged and not protected, require explicit approval
        if not is_merged and not is_protected:
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_UNMERGED,
                message="Branch has unmerged commits; explicit approval required",
                recoverable=True,
                suggested_action="Merge branch or provide merged: true to force cleanup",
                data={"unique_commits": unique_commits},
            )

        # Remove worktree
        force = not input_data.require_clean
        if not remove_worktree(worktree_path, force=force, cwd=repo_root):
            return Envelope.error_response(
                code=ErrorCodes.GIT_ERROR,
                message=f"Failed to remove worktree at: {worktree_path}",
                recoverable=False,
            )

        # Handle branch deletion
        branch_deleted_local = False
        branch_deleted_remote = False
        remote_message = ""

        if is_protected:
            # Never delete protected branches
            message = "worktree removed, branch preserved (protected)"
        else:
            # Delete non-protected branch if merged
            if is_merged or unique_commits == 0:
                branch_deleted_local = delete_local_branch(input_data.branch, cwd=repo_root)
                branch_deleted_remote, remote_message = delete_remote_branch(input_data.branch, cwd=repo_root)
                message = "worktree and branch removed"
            else:
                message = "worktree removed, branch preserved (unmerged)"

        # Update tracking
        tracking_updated = False
        if input_data.tracking_enabled:
            if input_data.tracking_path:
                tracking_path = Path(input_data.tracking_path).resolve()
            else:
                tracking_path = worktree_base / "worktree-tracking.md"

            if tracking_path.exists():
                tracking_updated = remove_tracking_row(tracking_path, input_data.branch)

        # Build response
        data = {
            "action": "cleanup",
            "branch": input_data.branch,
            "path": str(worktree_path),
            "repo_name": repo_name,
            "is_protected": is_protected,
            "merged": is_merged,
            "unique_commits": unique_commits,
            "worktree_removed": True,
            "branch_deleted_local": branch_deleted_local,
            "branch_deleted_remote": branch_deleted_remote,
            "tracking_updated": tracking_updated,
            "message": message,
        }

        if remote_message and remote_message != "deleted":
            data["remote_note"] = remote_message

        return Envelope.success_response(data=data)

    except subprocess.CalledProcessError as e:
        return Envelope.error_response(
            code=ErrorCodes.GIT_ERROR,
            message=f"Git command failed: {e.stderr or e.stdout or str(e)}",
            recoverable=False,
        )
    except Exception as e:
        return Envelope.error_response(
            code=ErrorCodes.GIT_ERROR,
            message=f"Unexpected error: {str(e)}",
            recoverable=False,
        )


def main() -> int:
    """Main entry point."""
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    else:
        input_json = sys.stdin.read()

    try:
        input_dict = json.loads(input_json)
        input_data = CleanupInput(**input_dict)
    except json.JSONDecodeError as e:
        envelope = Envelope.error_response(
            code=ErrorCodes.CONFIG_MISSING,
            message=f"Invalid JSON input: {str(e)}",
            recoverable=False,
        )
        print(envelope.to_fenced_json())
        return 1
    except Exception as e:
        envelope = Envelope.error_response(
            code=ErrorCodes.CONFIG_MISSING,
            message=f"Invalid input: {str(e)}",
            recoverable=False,
        )
        print(envelope.to_fenced_json())
        return 1

    envelope = cleanup_worktree_main(input_data)
    print(envelope.to_fenced_json())
    return 0 if envelope.success else 1


if __name__ == "__main__":
    sys.exit(main())
