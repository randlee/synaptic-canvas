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
    from .envelope import Envelope, ErrorCodes, Transcript
    from .worktree_shared import (
        check_remote_branch_exists,
        cleanup_empty_directories,
        count_unique_commits,
        delete_local_branch,
        delete_remote_branch,
        get_default_tracking_path,
        get_protected_branches,
        get_remote_ahead_count,
        get_repo_root,
        get_worktree_status,
        is_branch_merged,
        load_tracking_jsonl,
        reconcile_tracking,
        TrackingEntry,
        add_tracking_entry,
        remove_tracking_entry,
        remove_worktree,
        resolve_merge_base,
        run_git,
        update_tracking_entry,
    )
except ImportError:
    from envelope import Envelope, ErrorCodes, Transcript
    from worktree_shared import (
        check_remote_branch_exists,
        cleanup_empty_directories,
        count_unique_commits,
        delete_local_branch,
        delete_remote_branch,
        get_default_tracking_path,
        get_protected_branches,
        get_remote_ahead_count,
        get_repo_root,
        get_worktree_status,
        is_branch_merged,
        load_tracking_jsonl,
        reconcile_tracking,
        TrackingEntry,
        add_tracking_entry,
        remove_tracking_entry,
        remove_worktree,
        resolve_merge_base,
        run_git,
        update_tracking_entry,
    )


# =============================================================================
# Input Models
# =============================================================================


class CleanupInput(BaseModel):
    """Input schema for worktree cleanup."""

    branch: Optional[str] = Field(None, description="Branch to clean up (if omitted, clean all merged)")
    protected_branches: Optional[List[str]] = Field(None, description="List of protected branch names (auto-detected if omitted)")
    path: Optional[str] = Field(None, description="Worktree path")
    merged: Optional[bool] = Field(None, description="Whether branch is merged")
    require_clean: bool = Field(True, description="Require clean worktree (set false to force)")
    repo_root: Optional[str] = Field(None, description="Repo root directory")
    tracking_enabled: bool = Field(True, description="Whether to update tracking doc")
    tracking_path: Optional[str] = Field(None, description="Path to tracking document")
    worktree_base: Optional[str] = Field(None, description="Base directory for worktrees")
    cache_protected_branches: bool = Field(True, description="Cache protected branches to shared settings")

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.strip():
            raise ValueError("branch name cannot be empty string")
        return v.strip()

    @field_validator("protected_branches")
    @classmethod
    def validate_protected_branches(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [b.strip() for b in v if b.strip()]




# =============================================================================
# Worktree Scanning (for batch mode)
# =============================================================================


def get_all_worktrees(repo_root: Path) -> List[Dict[str, Any]]:
    """Get list of all worktrees using git worktree list --porcelain."""
    result = run_git(["worktree", "list", "--porcelain"], cwd=repo_root, check=True)

    worktrees = []
    current: Dict[str, Any] = {}

    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            if current.get("path"):
                worktrees.append(current)
            current = {}
            continue

        if line.startswith("worktree "):
            current["path"] = line[9:]
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
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

    # Don't forget last entry
    if current.get("path"):
        worktrees.append(current)

    return worktrees


# =============================================================================
# Batch Cleanup Logic
# =============================================================================


def cleanup_all_merged(input_data: CleanupInput) -> Envelope:
    """Clean up all merged worktrees, report dirty/unmerged for follow-up."""
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

        # Get protected branches
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

        # Resolve merge base for merge detection (fail closed if not found)
        merge_base = resolve_merge_base(
            cwd=repo_root,
            user_provided=protected_branches,
            cache_shared=input_data.cache_protected_branches,
            log_fn=lambda msg: transcript.step_ok(step="protected branches", message=msg),
        )
        if merge_base:
            transcript.step_ok(
                step="resolve merge base",
                message=f"using {merge_base}",
            )
        else:
            transcript.step_failed(
                step="resolve merge base",
                error="no protected branch found locally or remotely",
            )
            return Envelope.error_response(
                code=ErrorCodes.CONFIG_PROTECTED_BRANCH_NOT_SET,
                message="Cannot determine merge base: no protected branch found",
                recoverable=False,
                suggested_action="Ensure main, master, or develop branch exists locally or on remote",
                transcript=transcript,
            )

        # Determine worktree base
        if input_data.worktree_base:
            worktree_base = Path(input_data.worktree_base).resolve()
        else:
            worktree_base = repo_root.parent / f"{repo_name}-worktrees"

        # Determine tracking path (JSONL format)
        if input_data.tracking_enabled:
            if input_data.tracking_path:
                tracking_path = Path(input_data.tracking_path).resolve()
            else:
                tracking_path = get_default_tracking_path(worktree_base)
        else:
            tracking_path = None

        # Reconcile tracking with git before making decisions
        if tracking_path:
            try:
                reconcile_result = reconcile_tracking(
                    tracking_path=tracking_path,
                    repo_root=repo_root,
                    discover_all=False,
                    protected_branches=protected_branches,
                )
                transcript.step_ok(
                    step="reconcile tracking",
                    message=f"updated {reconcile_result.get('updated', 0)} entries",
                )
            except Exception as e:
                transcript.step_failed(
                    step="reconcile tracking",
                    error=str(e),
                )
                return Envelope.error_response(
                    code=ErrorCodes.GIT_ERROR,
                    message=f"Failed to reconcile tracking: {str(e)}",
                    recoverable=False,
                    transcript=transcript,
                )

        # Get all worktrees (used to capture rogue/untracked worktrees)
        all_worktrees = get_all_worktrees(repo_root)
        transcript.step_ok(
            step="git worktree list --porcelain",
            message=f"{len(all_worktrees)} worktree(s)",
        )

        # Filter out bare/detached and main repo
        worktrees = [
            wt for wt in all_worktrees
            if not wt.get("bare")
            and not wt.get("detached")
            and wt.get("path") != str(repo_root)
        ]

        # Ensure tracking includes any untracked local worktrees (rogue agent safety)
        if tracking_path:
            tracking_entries = load_tracking_jsonl(tracking_path)
            tracked_branches = {entry.branch for entry in tracking_entries}
            added = 0
            now = datetime.now(timezone.utc).isoformat()

            for wt in worktrees:
                branch = wt.get("branch", "")
                wt_path = Path(wt.get("path", ""))
                if not branch or branch in tracked_branches:
                    continue

                remote_exists = check_remote_branch_exists(branch, cwd=repo_root)
                remote_ahead = get_remote_ahead_count(branch, cwd=repo_root) if remote_exists else 0

                entry = TrackingEntry(
                    branch=branch,
                    path=str(wt_path),
                    base="unknown",
                    owner="unknown",
                    purpose="",
                    created=now,
                    status="discovered",
                    last_checked=now,
                    remote_exists=remote_exists,
                    local_worktree=True,
                    remote_ahead=remote_ahead if remote_ahead > 0 else 0,
                )
                add_tracking_entry(tracking_path, entry)
                tracked_branches.add(branch)
                added += 1

            if added:
                transcript.step_ok(
                    step="add untracked worktrees",
                    message=f"added {added} tracking entries",
                )

        cleaned = []
        dirty = []
        unmerged = []
        protected_skipped = []
        orphaned_remotes = []

        # Drive cleanup decisions from tracking entries (JSONL)
        tracking_entries = load_tracking_jsonl(tracking_path) if tracking_path else []

        # If tracking is disabled, fall back to current worktree list
        if not tracking_entries and not tracking_path:
            now = datetime.now(timezone.utc).isoformat()
            tracking_entries = []
            for wt in worktrees:
                branch = wt.get("branch", "")
                wt_path = wt.get("path", "")
                if not branch or not wt_path:
                    continue
                tracking_entries.append(
                    TrackingEntry(
                        branch=branch,
                        path=str(wt_path),
                        base="unknown",
                        owner="unknown",
                        purpose="",
                        created=now,
                        status="active",
                        last_checked=now,
                        remote_exists=False,
                        local_worktree=True,
                        remote_ahead=0,
                    )
                )

        for entry in tracking_entries:
            branch = entry.branch
            wt_path = Path(entry.path)

            if not entry.local_worktree or not wt_path.exists():
                if entry.remote_exists:
                    orphaned_remotes.append({
                        "branch": branch,
                        "path": entry.path,
                        "reason": "no local worktree",
                    })
                continue

            # Skip protected branches
            if branch in protected_branches:
                protected_skipped.append({"branch": branch, "reason": "protected"})
                continue

            # Check if worktree is clean
            is_clean, dirty_files = get_worktree_status(wt_path)

            if not is_clean:
                dirty.append({
                    "branch": branch,
                    "path": str(wt_path),
                    "files": dirty_files,
                })
                transcript.step_ok(
                    step=f"git -C {wt_path} status --porcelain",
                    message=f"dirty: {len(dirty_files)} file(s)",
                )
                continue

            # Check merge state (using protected base, not HEAD)
            is_merged = is_branch_merged(branch, base=merge_base, cwd=repo_root)
            unique_commits = count_unique_commits(branch, base=merge_base, cwd=repo_root)

            # Fail closed: if we can't determine merge state, skip cleanup
            if unique_commits < 0:
                unmerged.append({
                    "branch": branch,
                    "path": str(wt_path),
                    "unique_commits": None,
                    "reason": "unable to determine merge state",
                })
                transcript.step_ok(
                    step=f"git rev-list --count {merge_base}..{branch}",
                    message="unknown (fail closed)",
                )
                continue

            if not is_merged and unique_commits > 0:
                unmerged.append({
                    "branch": branch,
                    "path": str(wt_path),
                    "unique_commits": unique_commits,
                })
                transcript.step_ok(
                    step=f"git rev-list --count {merge_base}..{branch}",
                    message=f"unmerged: {unique_commits} commit(s)",
                )
                continue

            # Clean + merged → auto-cleanup
            transcript.step_ok(
                step=f"git -C {wt_path} status --porcelain",
                message="clean + merged",
            )

            # Remove worktree
            success = remove_worktree(wt_path, force=False, cwd=repo_root)
            if not success:
                transcript.step_failed(
                    step=f"git worktree remove {wt_path}",
                    error="failed to remove",
                )
                continue

            transcript.step_ok(
                step=f"git worktree remove {wt_path}",
                message="removed",
            )

            # Delete local branch
            branch_deleted_local = delete_local_branch(branch, cwd=repo_root)
            if branch_deleted_local:
                transcript.step_ok(
                    step=f"git branch -d {branch}",
                    message="deleted",
                )

            # Check remote_ahead before deleting remote branch
            remote_ahead = get_remote_ahead_count(branch, cwd=repo_root)
            branch_deleted_remote = False
            remote_msg = ""

            if remote_ahead > 0:
                # Remote has unpulled commits - don't delete
                transcript.step_ok(
                    step=f"git rev-list --count {branch}..origin/{branch}",
                    message=f"remote ahead by {remote_ahead} commit(s) - preserved",
                )
                remote_msg = f"preserved (remote ahead by {remote_ahead})"
            else:
                # Safe to delete remote
                branch_deleted_remote, remote_msg = delete_remote_branch(branch, cwd=repo_root)
                if branch_deleted_remote:
                    transcript.step_ok(
                        step=f"git push origin --delete {branch}",
                        message="deleted",
                    )

            # Update tracking (JSONL) - preserve until both local + remote gone
            if tracking_path:
                # Check current remote status
                remote_still_exists = check_remote_branch_exists(branch, cwd=repo_root)

                if not remote_still_exists:
                    # Both local worktree and remote are gone - remove entry
                    remove_tracking_entry(tracking_path, branch)
                    transcript.step_ok(
                        step=f"remove from {tracking_path.name}",
                        message=f"{branch} (fully cleaned)",
                    )
                else:
                    # Remote still exists - update entry to track orphaned remote
                    update_tracking_entry(tracking_path, branch, {
                        "local_worktree": False,
                        "remote_exists": True,
                    })
                    transcript.step_ok(
                        step=f"update {tracking_path.name}",
                        message=f"{branch} (orphaned remote)",
                    )

            cleaned.append({
                "branch": branch,
                "path": str(wt_path),
                "branch_deleted_local": branch_deleted_local,
                "branch_deleted_remote": branch_deleted_remote,
                "remote_ahead": remote_ahead if remote_ahead > 0 else None,
            })

        # Clean up empty directories
        removed_dirs = cleanup_empty_directories(worktree_base)
        if removed_dirs:
            transcript.step_ok(
                step="cleanup empty directories",
                message=f"removed {len(removed_dirs)} empty folder(s)",
            )

        return Envelope.success_response(
            data={
                "action": "cleanup_all",
                "cleaned": cleaned,
                "dirty": dirty,
                "unmerged": unmerged,
                "orphaned_remotes": orphaned_remotes if orphaned_remotes else None,
                "protected_skipped": protected_skipped if protected_skipped else None,
                "removed_directories": removed_dirs if removed_dirs else None,
                "summary": {
                    "cleaned": len(cleaned),
                    "dirty": len(dirty),
                    "unmerged": len(unmerged),
                    "orphaned_remotes": len(orphaned_remotes),
                    "protected_skipped": len(protected_skipped),
                    "empty_dirs_removed": len(removed_dirs),
                },
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


# =============================================================================
# Single Branch Cleanup Logic
# =============================================================================


def cleanup_single_branch(input_data: CleanupInput) -> Envelope:
    """Main worktree cleanup logic."""
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

        # Resolve merge base for merge detection (fail closed if not found)
        merge_base = resolve_merge_base(
            cwd=repo_root,
            user_provided=protected_branches,
            cache_shared=input_data.cache_protected_branches,
            log_fn=lambda msg: transcript.step_ok(step="protected branches", message=msg),
        )
        if merge_base:
            transcript.step_ok(
                step="resolve merge base",
                message=f"using {merge_base}",
            )
        else:
            transcript.step_failed(
                step="resolve merge base",
                error="no protected branch found locally or remotely",
            )
            return Envelope.error_response(
                code=ErrorCodes.CONFIG_PROTECTED_BRANCH_NOT_SET,
                message="Cannot determine merge base: no protected branch found",
                recoverable=False,
                suggested_action="Ensure main, master, or develop branch exists locally or on remote",
                transcript=transcript,
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

        if not is_clean and input_data.require_clean:
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_DIRTY,
                message="Worktree has uncommitted changes",
                recoverable=True,
                suggested_action="Commit/stash changes or set require_clean: false",
                data={"dirty_files": dirty_files},
                transcript=transcript,
            )

        # Check merge state (using protected base, not HEAD)
        if input_data.merged is not None:
            is_merged = input_data.merged
            transcript.step_skipped(step="git branch --merged", message="provided by caller")
        else:
            is_merged = is_branch_merged(input_data.branch, base=merge_base, cwd=repo_root)
            transcript.step_ok(
                step=f"git branch --merged {merge_base} | grep {input_data.branch}",
                message=str(is_merged),
            )

        unique_commits = count_unique_commits(input_data.branch, base=merge_base, cwd=repo_root)

        # Fail closed: if we can't determine merge state, refuse to cleanup
        if unique_commits < 0:
            transcript.step_ok(
                step=f"git rev-list --count {merge_base}..{input_data.branch}",
                message="unknown (fail closed)",
            )
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_UNMERGED,
                message="Cannot determine merge state; refusing cleanup",
                recoverable=False,
                suggested_action="Check branch existence and git state",
                data={"unique_commits": None, "reason": "unable to determine"},
                transcript=transcript,
            )

        transcript.step_ok(
            step=f"git rev-list --count {merge_base}..{input_data.branch}",
            message=str(unique_commits),
        )

        # If not merged and not protected, require explicit approval
        if not is_merged and not is_protected:
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_UNMERGED,
                message="Branch has unmerged commits; explicit approval required",
                recoverable=True,
                suggested_action="Merge branch or provide merged: true to force cleanup",
                data={"unique_commits": unique_commits},
                transcript=transcript,
            )

        # Remove worktree
        force = not input_data.require_clean
        force_flag = " --force" if force else ""
        with transcript.timed_step(f"git worktree remove{force_flag} {worktree_path}") as t:
            success = remove_worktree(worktree_path, force=force, cwd=repo_root)
            if not success:
                raise RuntimeError(f"Failed to remove worktree at: {worktree_path}")
            t.message = "removed"

        # Handle branch deletion
        branch_deleted_local = False
        branch_deleted_remote = False
        remote_message = ""
        remote_ahead = 0

        if is_protected:
            # Never delete protected branches
            message = "worktree removed, branch preserved (protected)"
            transcript.step_skipped(step="git branch -d", message="protected")
        else:
            # Delete non-protected branch if merged
            if is_merged or unique_commits == 0:
                branch_deleted_local = delete_local_branch(input_data.branch, cwd=repo_root)
                transcript.step_ok(
                    step=f"git branch -d {input_data.branch}",
                    message="deleted" if branch_deleted_local else "not found",
                )

                # Check remote_ahead before deleting remote branch
                remote_ahead = get_remote_ahead_count(input_data.branch, cwd=repo_root)
                if remote_ahead > 0:
                    # Remote has unpulled commits - don't delete
                    transcript.step_ok(
                        step=f"git rev-list --count {input_data.branch}..origin/{input_data.branch}",
                        message=f"remote ahead by {remote_ahead} commit(s) - preserved",
                    )
                    remote_message = f"preserved (remote ahead by {remote_ahead})"
                    message = "worktree removed, local branch deleted, remote preserved (has unpulled commits)"
                else:
                    # Safe to delete remote
                    branch_deleted_remote, remote_message = delete_remote_branch(input_data.branch, cwd=repo_root)
                    transcript.step_ok(
                        step=f"git push origin --delete {input_data.branch}",
                        message="deleted" if branch_deleted_remote else remote_message,
                    )
                    message = "worktree and branch removed"
            else:
                message = "worktree removed, branch preserved (unmerged)"
                transcript.step_skipped(step="git branch -d", message="unmerged")

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

        # Clean up empty directories
        removed_dirs = cleanup_empty_directories(worktree_base)
        if removed_dirs:
            transcript.step_ok(
                step="cleanup empty directories",
                message=f"removed {len(removed_dirs)} empty folder(s)",
            )

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
            "remote_ahead": remote_ahead if remote_ahead > 0 else None,
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


# =============================================================================
# Router
# =============================================================================


def cleanup_worktree_main(input_data: CleanupInput) -> Envelope:
    """Route to single-branch or batch cleanup based on input."""
    if input_data.branch:
        return cleanup_single_branch(input_data)
    else:
        return cleanup_all_merged(input_data)


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> int:
    """Main entry point."""
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    else:
        input_json = sys.stdin.read()

    # Handle empty input as batch mode
    if not input_json.strip():
        input_json = "{}"

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
