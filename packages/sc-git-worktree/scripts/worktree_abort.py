#!/usr/bin/env python3
"""Abandon a git worktree with protected branch safeguards.

This script removes a worktree and optionally deletes the branch (for non-protected
branches only, with explicit approval). It handles tracking document updates.

Usage:
    python worktree_abort.py '<json-input>'
    echo '<json-input>' | python worktree_abort.py

Exit Codes:
    0: Abort completed successfully
    1: Error during abort
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

try:
    from .envelope import Envelope, ErrorCodes, Transcript
    from .worktree_shared import (
        check_remote_branch_exists,
        delete_local_branch,
        delete_remote_branch,
        get_default_tracking_path,
        get_protected_branches,
        get_repo_root,
        get_worktree_status,
        remove_tracking_entry,
        remove_worktree,
        update_tracking_entry,
    )
except ImportError:
    from envelope import Envelope, ErrorCodes, Transcript
    from worktree_shared import (
        check_remote_branch_exists,
        delete_local_branch,
        delete_remote_branch,
        get_default_tracking_path,
        get_protected_branches,
        get_repo_root,
        get_worktree_status,
        remove_tracking_entry,
        remove_worktree,
        update_tracking_entry,
    )


# =============================================================================
# Input Models
# =============================================================================


class AbortInput(BaseModel):
    """Input schema for worktree abort."""

    branch: str = Field(..., description="Branch/worktree name to abandon")
    protected_branches: Optional[List[str]] = Field(None, description="List of protected branch names (auto-detected if omitted)")
    path: Optional[str] = Field(None, description="Worktree path")
    allow_delete_branch: bool = Field(False, description="Approval to delete branch")
    allow_force: bool = Field(False, description="Approval to force-remove dirty worktree")
    repo_root: Optional[str] = Field(None, description="Repo root directory")
    tracking_enabled: bool = Field(True, description="Whether to update tracking doc")
    tracking_path: Optional[str] = Field(None, description="Path to tracking document")
    worktree_base: Optional[str] = Field(None, description="Base directory for worktrees")
    cache_protected_branches: bool = Field(True, description="Cache protected branches to shared settings")

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("branch name cannot be empty")
        return v.strip()

    @field_validator("protected_branches")
    @classmethod
    def validate_protected_branches(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [b.strip() for b in v if b.strip()]




# =============================================================================
# Main Logic
# =============================================================================


def abort_worktree_main(input_data: AbortInput) -> Envelope:
    """Main worktree abort logic."""
    transcript = Transcript()

    try:
        # Determine repo root
        if input_data.repo_root:
            repo_root = Path(input_data.repo_root).resolve()
        else:
            repo_root = get_repo_root()

        repo_name = repo_root.name
        transcript.step_ok(
            step="git rev-parse --show-toplevel",
            message=str(repo_root),
        )

        # Get protected branches (auto-detect if not provided)
        try:
            protected_branches = get_protected_branches(
                repo_root,
                user_provided=input_data.protected_branches,
                cache_shared=input_data.cache_protected_branches,
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
        is_protected = input_data.branch in protected_branches
        transcript.step_ok(
            step="git config --get gitflow.branch.*",
            message=f"{protected_branches} (is_protected={is_protected})",
        )

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
            transcript.step_failed(
                step="check_worktree_exists",
                error=f"Worktree not found at: {worktree_path}",
            )
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_NOT_FOUND,
                message=f"Worktree not found at: {worktree_path}",
                recoverable=False,
                transcript=transcript,
            )

        transcript.step_ok(
            step=f"test -d {worktree_path}",
            message="exists",
        )

        # Check if worktree is clean
        is_clean, dirty_files = get_worktree_status(worktree_path)
        transcript.step_ok(
            step=f"git -C {worktree_path} status --porcelain",
            message="clean" if is_clean else "\n".join(dirty_files),
        )

        if not is_clean and not input_data.allow_force:
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_DIRTY,
                message="Worktree has uncommitted changes; force approval required",
                recoverable=True,
                suggested_action="Set allow_force: true to force-remove, or commit/stash changes",
                data={"dirty_files": dirty_files},
                transcript=transcript,
            )

        # Remove worktree
        force_flag = " --force" if input_data.allow_force else ""
        with transcript.timed_step(f"git worktree remove{force_flag} {worktree_path}") as t:
            success = remove_worktree(worktree_path, force=input_data.allow_force, cwd=repo_root)
            if not success:
                raise RuntimeError(f"Failed to remove worktree at: {worktree_path}")
            t.message = "removed"

        # Handle branch deletion
        branch_deleted_local = False
        branch_deleted_remote = False
        remote_message = ""

        if is_protected:
            # Never delete protected branches (remote or local by default)
            message = "worktree removed, branch preserved (protected)"
            transcript.step_skipped(step="git branch -D", message="protected")
        elif input_data.allow_delete_branch:
            # Delete non-protected branch with explicit approval
            branch_deleted_local = delete_local_branch(input_data.branch, force=True, cwd=repo_root)
            transcript.step_ok(
                step=f"git branch -D {input_data.branch}",
                message="deleted" if branch_deleted_local else "not found",
            )

            branch_deleted_remote, remote_message = delete_remote_branch(input_data.branch, cwd=repo_root)
            transcript.step_ok(
                step=f"git push origin --delete {input_data.branch}",
                message="deleted" if branch_deleted_remote else remote_message,
            )
            message = "worktree and branch removed"
        else:
            message = "worktree removed, branch preserved (no delete approval)"
            transcript.step_skipped(step="git branch -D", message="no approval")

        # Update tracking (JSONL) - preserve until both local + remote gone
        tracking_updated = False
        if input_data.tracking_enabled:
            if input_data.tracking_path:
                tracking_path = Path(input_data.tracking_path).resolve()
            else:
                tracking_path = get_default_tracking_path(worktree_base)

            if tracking_path.exists():
                # Check current remote status
                remote_still_exists = check_remote_branch_exists(input_data.branch, cwd=repo_root)

                if not remote_still_exists:
                    # Both local worktree and remote are gone - remove entry
                    tracking_updated = remove_tracking_entry(tracking_path, input_data.branch)
                    transcript.step_ok(
                        step=f"remove from {tracking_path.name}",
                        message=f"{input_data.branch} (fully cleaned)" if tracking_updated else "not found",
                    )
                else:
                    # Remote still exists - update entry to track orphaned remote
                    tracking_updated = update_tracking_entry(tracking_path, input_data.branch, {
                        "local_worktree": False,
                        "remote_exists": True,
                    })
                    transcript.step_ok(
                        step=f"update {tracking_path.name}",
                        message=f"{input_data.branch} (orphaned remote)" if tracking_updated else "not found",
                    )
            else:
                transcript.step_skipped(step="update_tracking", message="file not found")
        else:
            transcript.step_skipped(step="update_tracking", message="disabled")

        # Build response
        data = {
            "action": "abort",
            "branch": input_data.branch,
            "path": str(worktree_path),
            "repo_name": repo_name,
            "is_protected": is_protected,
            "worktree_removed": True,
            "branch_deleted_local": branch_deleted_local,
            "branch_deleted_remote": branch_deleted_remote,
            "tracking_updated": tracking_updated,
            "message": message,
        }

        if remote_message and remote_message != "deleted":
            data["remote_note"] = remote_message

        return Envelope.success_response(data=data, transcript=transcript)

    except subprocess.CalledProcessError as e:
        cmd = " ".join(e.cmd) if isinstance(e.cmd, list) else str(e.cmd)
        transcript.step_failed(step=cmd, error=e.stderr or e.stdout or str(e))
        return Envelope.error_response(
            code=ErrorCodes.GIT_ERROR,
            message=f"Git command failed: {e.stderr or e.stdout or str(e)}",
            recoverable=False,
            transcript=transcript,
        )
    except Exception as e:
        transcript.step_failed(step="unexpected", error=str(e))
        return Envelope.error_response(
            code=ErrorCodes.GIT_ERROR,
            message=f"Unexpected error: {str(e)}",
            recoverable=False,
            transcript=transcript,
        )


def main() -> int:
    """Main entry point."""
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    else:
        input_json = sys.stdin.read()

    try:
        input_dict = json.loads(input_json)
        input_data = AbortInput(**input_dict)
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

    envelope = abort_worktree_main(input_data)
    print(envelope.to_fenced_json())
    return 0 if envelope.success else 1


if __name__ == "__main__":
    sys.exit(main())
