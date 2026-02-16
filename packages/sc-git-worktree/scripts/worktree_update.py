#!/usr/bin/env python3
"""Update protected branches in their worktrees.

This script safely pulls latest changes for protected branches in their worktrees.
It handles merge conflicts by returning detailed error information.

Usage:
    python worktree_update.py '<json-input>'
    echo '<json-input>' | python worktree_update.py

Exit Codes:
    0: Update completed successfully
    1: Error during update (including merge conflicts)
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
        get_default_tracking_path,
        get_protected_branches,
        get_repo_root,
        get_worktree_status,
        run_git,
        update_tracking_entry,
    )
except ImportError:
    from envelope import Envelope, ErrorCodes, Transcript
    from worktree_shared import (
        get_default_tracking_path,
        get_protected_branches,
        get_repo_root,
        get_worktree_status,
        run_git,
        update_tracking_entry,
    )


# =============================================================================
# Input Models
# =============================================================================


class UpdateInput(BaseModel):
    """Input schema for worktree update."""

    protected_branches: Optional[List[str]] = Field(None, description="List of protected branch names (auto-detected if omitted)")
    branch: Optional[str] = Field(None, description="Specific branch to update (or all if omitted)")
    path: Optional[str] = Field(None, description="Worktree path")
    repo_root: Optional[str] = Field(None, description="Repo root directory")
    tracking_enabled: bool = Field(True, description="Whether to update tracking doc")
    tracking_path: Optional[str] = Field(None, description="Path to tracking document")
    worktree_base: Optional[str] = Field(None, description="Base directory for worktrees")
    cache_protected_branches: bool = Field(True, description="Cache protected branches to shared settings")

    @field_validator("protected_branches")
    @classmethod
    def validate_protected_branches(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [b.strip() for b in v if b.strip()]


# =============================================================================
# Git Operations (update-specific)
# =============================================================================


def get_current_commit(cwd: Path) -> str:
    """Get the current commit SHA."""
    result = run_git(["rev-parse", "--short", "HEAD"], cwd=cwd, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def fetch_branch(branch: str, cwd: Path) -> bool:
    """Fetch a branch from origin."""
    result = run_git(["fetch", "origin", branch], cwd=cwd, check=False)
    return result.returncode == 0


def pull_branch(branch: str, cwd: Path) -> tuple[bool, str, List[str]]:
    """Pull a branch from origin. Returns (success, message, conflicted_files)."""
    result = run_git(["pull", "origin", branch], cwd=cwd, check=False)

    if result.returncode == 0:
        return True, result.stdout.strip(), []

    # Check for merge conflicts
    if "CONFLICT" in result.stdout or "Automatic merge failed" in result.stdout:
        # Get conflicted files
        conflict_result = run_git(["diff", "--name-only", "--diff-filter=U"], cwd=cwd, check=False)
        conflicted_files = [f.strip() for f in conflict_result.stdout.strip().split("\n") if f.strip()]
        return False, "merge conflicts detected", conflicted_files

    return False, result.stderr or result.stdout, []


def count_commits_between(old_commit: str, new_commit: str, cwd: Path) -> int:
    """Count commits between two refs."""
    if old_commit == new_commit:
        return 0
    result = run_git(["rev-list", "--count", f"{old_commit}..{new_commit}"], cwd=cwd, check=False)
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0




# =============================================================================
# Main Logic
# =============================================================================


def update_single_branch(
    branch: str,
    worktree_path: Path,
    repo_root: Path,
    tracking_path: Optional[Path],
    transcript: Transcript,
) -> Dict[str, Any]:
    """Update a single branch and return result."""
    result = {
        "branch": branch,
        "path": str(worktree_path),
        "success": False,
        "commits_pulled": 0,
        "old_commit": "",
        "new_commit": "",
        "message": "",
        "conflicted_files": [],
    }

    # Check if worktree exists
    if not worktree_path.exists():
        result["error_code"] = ErrorCodes.WORKTREE_NOT_FOUND
        result["message"] = f"Worktree not found at: {worktree_path}"
        transcript.step_failed(
            step=f"check_worktree_{branch}",
            error=f"Worktree not found at: {worktree_path}",
        )
        return result

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

    if not is_clean:
        result["error_code"] = ErrorCodes.WORKTREE_DIRTY
        result["message"] = "Worktree has uncommitted changes"
        result["dirty_files"] = dirty_files
        return result

    # Get current commit
    old_commit = get_current_commit(worktree_path)
    result["old_commit"] = old_commit
    transcript.step_ok(
        step=f"git -C {worktree_path} rev-parse --short HEAD",
        message=old_commit,
    )

    # Fetch
    with transcript.timed_step(f"git -C {worktree_path} fetch origin {branch}") as t:
        if not fetch_branch(branch, worktree_path):
            result["error_code"] = ErrorCodes.GIT_ERROR
            result["message"] = f"Failed to fetch branch {branch}"
            t.status = "failed"
            t.error = f"fetch failed"
            return result

    # Pull
    with transcript.timed_step(f"git -C {worktree_path} pull origin {branch}") as t:
        success, message, conflicted_files = pull_branch(branch, worktree_path)
        t.message = message
        if not success:
            t.status = "failed"
            t.error = message

    if not success and conflicted_files:
        result["error_code"] = ErrorCodes.MERGE_CONFLICTS
        result["message"] = "Merge conflicts detected during pull"
        result["conflicted_files"] = conflicted_files
        return result

    if not success:
        result["error_code"] = ErrorCodes.GIT_ERROR
        result["message"] = message
        return result

    # Get new commit
    new_commit = get_current_commit(worktree_path)
    result["new_commit"] = new_commit

    # Count commits pulled
    commits_pulled = count_commits_between(old_commit, new_commit, worktree_path)
    result["commits_pulled"] = commits_pulled

    if commits_pulled == 0:
        result["message"] = "already up to date"
    else:
        result["message"] = f"pulled {commits_pulled} commits ({old_commit}..{new_commit})"

    # Update tracking (JSONL)
    if tracking_path and tracking_path.exists():
        now = datetime.now(timezone.utc).isoformat()
        update_tracking_entry(tracking_path, branch, {"last_checked": now})
        result["tracking_updated"] = True
        transcript.step_ok(
            step=f"update {tracking_path.name}",
            message=branch,
        )

    result["success"] = True
    return result


def update_worktree_main(input_data: UpdateInput) -> Envelope:
    """Main worktree update logic."""
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

        transcript.step_ok(
            step="git config --get gitflow.branch.*",
            message=str(protected_branches),
        )

        # Determine worktree base
        if input_data.worktree_base:
            worktree_base = Path(input_data.worktree_base).resolve()
        else:
            worktree_base = repo_root.parent / f"{repo_name}-worktrees"

        # Determine tracking path (JSONL format)
        tracking_path = None
        if input_data.tracking_enabled:
            if input_data.tracking_path:
                tracking_path = Path(input_data.tracking_path).resolve()
            else:
                tracking_path = get_default_tracking_path(worktree_base)

        # Determine which branches to update
        if input_data.branch:
            # Single branch specified
            if input_data.branch not in protected_branches:
                return Envelope.error_response(
                    code=ErrorCodes.BRANCH_NOT_PROTECTED,
                    message=f"Branch '{input_data.branch}' is not a protected branch",
                    recoverable=False,
                    suggested_action="Use --cleanup or --abort for non-protected branches. --update is only for protected branches.",
                    transcript=transcript,
                )
            target_branches = [input_data.branch]
        else:
            # Update all protected branches that have worktrees
            target_branches = [
                b for b in protected_branches
                if (worktree_base / b).exists()
            ]

        if not target_branches:
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_NOT_FOUND,
                message="No protected branch worktrees found to update",
                recoverable=False,
                transcript=transcript,
            )

        transcript.step_ok(
            step="git worktree list",
            message=str(target_branches),
        )

        # Update each branch
        results = {}
        conflicts = {}
        all_success = True

        for branch in target_branches:
            if input_data.path and len(target_branches) == 1:
                worktree_path = Path(input_data.path).resolve()
            else:
                worktree_path = worktree_base / branch

            result = update_single_branch(branch, worktree_path, repo_root, tracking_path, transcript)
            results[branch] = result

            if not result["success"]:
                all_success = False
                if result.get("conflicted_files"):
                    conflicts[branch] = result["conflicted_files"]

        # Build response
        if len(target_branches) == 1:
            # Single branch response
            branch = target_branches[0]
            result = results[branch]

            if result["success"]:
                return Envelope.success_response(
                    data={
                        "action": "update",
                        "branch": branch,
                        "path": result["path"],
                        "repo_name": repo_name,
                        "commits_pulled": result["commits_pulled"],
                        "old_commit": result["old_commit"],
                        "new_commit": result["new_commit"],
                        "message": result["message"],
                        "tracking_updated": result.get("tracking_updated", False),
                    },
                    transcript=transcript,
                )
            else:
                error_data = {
                    "worktree_path": result["path"],
                }
                if result.get("conflicted_files"):
                    error_data["conflicted_files"] = result["conflicted_files"]
                if result.get("dirty_files"):
                    error_data["dirty_files"] = result["dirty_files"]

                return Envelope.error_response(
                    code=result.get("error_code", ErrorCodes.GIT_ERROR),
                    message=result["message"],
                    recoverable=bool(result.get("conflicted_files") or result.get("dirty_files")),
                    suggested_action="Resolve conflicts or commit/stash changes, then retry",
                    data=error_data,
                    transcript=transcript,
                )
        else:
            # Multi-branch aggregate response
            if all_success:
                return Envelope.success_response(
                    data={
                        "action": "update",
                        "repo_name": repo_name,
                        "results": {
                            b: {
                                "commits_pulled": r["commits_pulled"],
                                "status": "updated" if r["commits_pulled"] > 0 else "up_to_date",
                            }
                            for b, r in results.items()
                        },
                        "conflicts": {},
                        "tracking_updated": True,
                    },
                    transcript=transcript,
                )
            else:
                return Envelope.error_response(
                    code=ErrorCodes.GIT_ERROR,
                    message="Some branches failed to update",
                    recoverable=bool(conflicts),
                    data={
                        "results": results,
                        "conflicts": conflicts,
                    },
                    transcript=transcript,
                )

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
        input_data = UpdateInput(**input_dict)
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

    envelope = update_worktree_main(input_data)
    print(envelope.to_fenced_json())
    return 0 if envelope.success else 1


if __name__ == "__main__":
    sys.exit(main())
