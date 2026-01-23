#!/usr/bin/env python3
"""Create a git worktree with optional tracking.

This script creates a new worktree (and branch if needed) using the mandated
sibling folder layout. It handles tracking document updates when enabled.

Usage:
    python worktree_create.py '<json-input>'
    echo '<json-input>' | python worktree_create.py

Input JSON:
    {
        "branch": "feature/my-feature",
        "base": "main",
        "purpose": "implement login feature",
        "owner": "claude-haiku",
        "repo_root": "/path/to/repo",  # optional, defaults to cwd
        "tracking_enabled": true,       # optional, defaults to true
        "worktree_base": null,          # optional, derived from repo name
        "tracking_path": null           # optional, derived from worktree_base
    }

Exit Codes:
    0: Worktree created successfully
    1: Error during creation
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Support both relative import (when used as package) and absolute import (when used standalone)
try:
    from .envelope import Envelope, ErrorCodes
except ImportError:
    from envelope import Envelope, ErrorCodes


# =============================================================================
# Input Models
# =============================================================================


class CreateInput(BaseModel):
    """Input schema for worktree creation."""

    branch: str = Field(..., description="Branch name to use/create")
    base: str = Field(..., description="Base branch to create from")
    purpose: str = Field(..., description="Short reason for this worktree")
    owner: str = Field(..., description="Agent name or user handle")
    repo_root: Optional[str] = Field(None, description="Repo root directory")
    tracking_enabled: bool = Field(True, description="Whether to update tracking doc")
    worktree_base: Optional[str] = Field(None, description="Base directory for worktrees")
    tracking_path: Optional[str] = Field(None, description="Path to tracking document")

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        """Validate branch name is not empty and has no invalid characters."""
        if not v or not v.strip():
            raise ValueError("branch name cannot be empty")
        # Basic validation - git will do more thorough validation
        invalid_chars = [" ", "~", "^", ":", "\\", "*", "?", "["]
        for char in invalid_chars:
            if char in v:
                raise ValueError(f"branch name cannot contain '{char}'")
        return v.strip()

    @field_validator("base")
    @classmethod
    def validate_base(cls, v: str) -> str:
        """Validate base branch name."""
        if not v or not v.strip():
            raise ValueError("base branch cannot be empty")
        return v.strip()


class TrackingRow(BaseModel):
    """A row in the tracking document."""

    branch: str
    path: str
    base: str
    purpose: str
    owner: str
    created: str
    status: str = "active"
    last_checked: str
    notes: str = ""


# =============================================================================
# Git Operations
# =============================================================================


def run_git(args: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Execute a git command.

    Args:
        args: Git command arguments (without 'git' prefix)
        cwd: Working directory for the command
        check: Whether to raise on non-zero exit

    Returns:
        CompletedProcess with stdout/stderr

    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
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


def branch_exists(branch: str, cwd: Optional[Path] = None) -> bool:
    """Check if a branch exists locally or remotely."""
    # Check local
    result = run_git(["branch", "--list", branch], cwd=cwd, check=False)
    if result.stdout.strip():
        return True

    # Check remote
    result = run_git(["branch", "-r", "--list", f"origin/{branch}"], cwd=cwd, check=False)
    return bool(result.stdout.strip())


def fetch_all(cwd: Optional[Path] = None) -> None:
    """Fetch all remotes and prune."""
    run_git(["fetch", "--all", "--prune"], cwd=cwd)


def create_worktree(
    branch: str,
    path: Path,
    base: Optional[str] = None,
    create_branch: bool = False,
    cwd: Optional[Path] = None,
) -> None:
    """Create a git worktree.

    Args:
        branch: Branch name
        path: Path for the worktree
        base: Base branch (required if create_branch=True)
        create_branch: Whether to create a new branch
        cwd: Working directory
    """
    args = ["worktree", "add"]
    if create_branch:
        if not base:
            raise ValueError("base branch required when creating new branch")
        args.extend(["-b", branch, str(path), base])
    else:
        args.extend([str(path), branch])

    run_git(args, cwd=cwd)


def get_worktree_status(path: Path) -> tuple[bool, List[str]]:
    """Check if worktree is clean.

    Returns:
        Tuple of (is_clean, list of dirty files)
    """
    result = run_git(["status", "--short"], cwd=path, check=False)
    if result.returncode != 0:
        return False, [f"git status failed: {result.stderr}"]

    dirty_files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    return len(dirty_files) == 0, dirty_files


# =============================================================================
# Tracking Document
# =============================================================================


def ensure_tracking_doc(tracking_path: Path, repo_name: str) -> None:
    """Ensure tracking document exists with headers."""
    if tracking_path.exists():
        return

    # Create parent directory if needed
    tracking_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    content = f"""---
repo: {repo_name}
tracking_enabled: true
created: {now}
---

# Worktree Tracking

| Branch | Path | Base | Purpose | Owner | Created | Status | Last Checked | Notes |
|--------|------|------|---------|-------|---------|--------|--------------|-------|
"""
    tracking_path.write_text(content)


def add_tracking_row(tracking_path: Path, row: TrackingRow) -> None:
    """Add a row to the tracking document."""
    content = tracking_path.read_text()

    # Build markdown table row
    table_row = (
        f"| {row.branch} | {row.path} | {row.base} | {row.purpose} | "
        f"{row.owner} | {row.created} | {row.status} | {row.last_checked} | {row.notes} |"
    )

    # Append to file
    if not content.endswith("\n"):
        content += "\n"
    content += table_row + "\n"

    tracking_path.write_text(content)


# =============================================================================
# Main Logic
# =============================================================================


def create_worktree_main(input_data: CreateInput) -> Envelope:
    """Main worktree creation logic.

    Args:
        input_data: Validated input

    Returns:
        Envelope with success/error response
    """
    try:
        # Determine repo root
        if input_data.repo_root:
            repo_root = Path(input_data.repo_root).resolve()
        else:
            repo_root = get_repo_root()

        if not repo_root.exists():
            return Envelope.error_response(
                code=ErrorCodes.GIT_NOT_REPO,
                message=f"Repository root does not exist: {repo_root}",
                recoverable=False,
            )

        repo_name = get_repo_name(repo_root)

        # Determine worktree base
        if input_data.worktree_base:
            worktree_base = Path(input_data.worktree_base).resolve()
        else:
            worktree_base = repo_root.parent / f"{repo_name}-worktrees"

        # Ensure worktree base exists
        worktree_base.mkdir(parents=True, exist_ok=True)

        # Determine tracking path
        if input_data.tracking_enabled:
            if input_data.tracking_path:
                tracking_path = Path(input_data.tracking_path).resolve()
            else:
                tracking_path = worktree_base / "worktree-tracking.md"

            # Ensure tracking document exists
            ensure_tracking_doc(tracking_path, repo_name)
        else:
            tracking_path = None

        # Fetch all remotes
        fetch_all(cwd=repo_root)

        # Check if base branch exists
        if not branch_exists(input_data.base, cwd=repo_root):
            return Envelope.error_response(
                code=ErrorCodes.BRANCH_NOT_FOUND,
                message=f"Base branch '{input_data.base}' not found",
                recoverable=False,
                suggested_action="Verify the base branch exists locally or remotely",
            )

        # Determine worktree path
        worktree_path = worktree_base / input_data.branch

        # Check if path already exists
        if worktree_path.exists():
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_EXISTS,
                message=f"Worktree path already exists: {worktree_path}",
                recoverable=False,
                suggested_action="Remove existing worktree or choose different branch name",
            )

        # Create worktree
        needs_new_branch = not branch_exists(input_data.branch, cwd=repo_root)
        create_worktree(
            branch=input_data.branch,
            path=worktree_path,
            base=input_data.base if needs_new_branch else None,
            create_branch=needs_new_branch,
            cwd=repo_root,
        )

        # Verify worktree is clean
        is_clean, dirty_files = get_worktree_status(worktree_path)
        if not is_clean:
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_DIRTY,
                message="Worktree has uncommitted changes after creation",
                recoverable=False,
                suggested_action="Investigate worktree state; manual cleanup may be required",
                data={"dirty_files": dirty_files},
            )

        # Create tracking row
        now = datetime.now(timezone.utc).isoformat()
        tracking_row = TrackingRow(
            branch=input_data.branch,
            path=str(worktree_path),
            base=input_data.base,
            purpose=input_data.purpose,
            owner=input_data.owner,
            created=now,
            status="active",
            last_checked=now,
            notes="",
        )

        # Update tracking document
        tracking_updated = False
        if tracking_path:
            add_tracking_row(tracking_path, tracking_row)
            tracking_updated = True

        # Build response
        return Envelope.success_response(
            data={
                "action": "create",
                "branch": input_data.branch,
                "base": input_data.base,
                "path": str(worktree_path),
                "repo_name": repo_name,
                "status": "clean",
                "branch_created": needs_new_branch,
                "tracking_row": tracking_row.model_dump(),
                "tracking_updated": tracking_updated,
            }
        )

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
    # Get input from argument or stdin
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    else:
        input_json = sys.stdin.read()

    # Parse and validate input
    try:
        input_dict = json.loads(input_json)
        input_data = CreateInput(**input_dict)
    except json.JSONDecodeError as e:
        envelope = Envelope.error_response(
            code=ErrorCodes.CONFIG_MISSING,
            message=f"Invalid JSON input: {str(e)}",
            recoverable=False,
            suggested_action="Provide valid JSON input",
        )
        print(envelope.to_fenced_json())
        return 1
    except Exception as e:
        envelope = Envelope.error_response(
            code=ErrorCodes.CONFIG_MISSING,
            message=f"Invalid input: {str(e)}",
            recoverable=False,
            suggested_action="Check input schema",
        )
        print(envelope.to_fenced_json())
        return 1

    # Execute main logic
    envelope = create_worktree_main(input_data)
    print(envelope.to_fenced_json())

    return 0 if envelope.success else 1


if __name__ == "__main__":
    sys.exit(main())
