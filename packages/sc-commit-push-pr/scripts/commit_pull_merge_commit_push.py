#!/usr/bin/env python3
"""Commit/Pull/Merge/Push pipeline for sc-commit-push-pr.

This script handles the complete commit/push pipeline:
1. Resolve source and destination branches (default: current branch -> protected branch)
2. Check staged changes (skip commit if none, continue pipeline)
3. Fetch and pull+merge from destination branch
4. If merge conflicts: return GIT.MERGE_CONFLICT error with list of conflicting files
5. If no conflicts: commit merge if needed, push
6. Check existing PR and return status + URL

Usage:
    python commit_pull_merge_commit_push.py [--source BRANCH] [--destination BRANCH]
    echo '{"source": "feature-x", "destination": "main"}' | python commit_pull_merge_commit_push.py
"""

import argparse
import json
import subprocess
import sys
from typing import List, Optional

from pydantic import BaseModel

# Support both relative import (when used as package) and absolute import (when used standalone)
try:
    from .envelope import Envelope, ErrorCodes
    from .provider_detect import detect_provider, get_remote_url, ProviderInfo
    from .pr_provider import get_provider, PullRequestInfo, PrProviderError
    from .preflight_utils import load_shared_settings, get_protected_branches
except ImportError:
    from envelope import Envelope, ErrorCodes
    from provider_detect import detect_provider, get_remote_url, ProviderInfo
    from pr_provider import get_provider, PullRequestInfo, PrProviderError
    from preflight_utils import load_shared_settings, get_protected_branches


# =============================================================================
# Input/Output Models
# =============================================================================

class CommitPushInput(BaseModel):
    """Input parameters for the commit/push pipeline."""
    source: Optional[str] = None      # Source branch (default: current)
    destination: Optional[str] = None  # Destination branch (default: from settings)


class CommitPushData(BaseModel):
    """Data payload for successful commit/push operations."""
    pr_exists: bool
    pr: Optional[PullRequestInfo] = None
    needs_pr_text: bool = False
    context: Optional[dict] = None  # diff summary, branch info
    conflicts: Optional[List[str]] = None


# =============================================================================
# Git Operations
# =============================================================================

def run_git_command(
    args: List[str],
    check: bool = True,
    capture_output: bool = True
) -> subprocess.CompletedProcess:
    """Run a git command with standardized options.

    Args:
        args: Git command arguments (without 'git' prefix)
        check: Whether to raise on non-zero exit code
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess result
    """
    cmd = ["git"] + args
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        check=check
    )


def get_current_branch() -> str:
    """Get the current branch name.

    Returns:
        Current branch name

    Raises:
        RuntimeError: If not on a branch (detached HEAD or error)
    """
    try:
        result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        branch = result.stdout.strip()
        if branch == "HEAD":
            raise RuntimeError("Detached HEAD state - not on a branch")
        return branch
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get current branch: {e.stderr}")


def has_staged_changes() -> bool:
    """Check if there are staged changes.

    Returns:
        True if there are staged changes, False otherwise
    """
    result = run_git_command(["diff", "--cached", "--quiet"], check=False)
    # Exit code 0 = no changes, 1 = changes exist
    return result.returncode != 0


def fetch_branch(branch: str) -> None:
    """Fetch a branch from origin.

    Args:
        branch: Branch name to fetch

    Raises:
        RuntimeError: If fetch fails
    """
    try:
        run_git_command(["fetch", "origin", branch])
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to fetch branch '{branch}': {e.stderr}")


def merge_branch(branch: str) -> tuple[bool, List[str]]:
    """Merge a branch from origin.

    Args:
        branch: Branch name to merge (will merge origin/<branch>)

    Returns:
        Tuple of (success, conflict_files)
        - success: True if merge succeeded, False if conflicts
        - conflict_files: List of files with conflicts (empty if success)
    """
    result = run_git_command(
        ["merge", f"origin/{branch}"],
        check=False
    )

    if result.returncode == 0:
        return True, []

    # Check for merge conflicts
    conflict_result = run_git_command(
        ["diff", "--name-only", "--diff-filter=U"],
        check=False
    )

    conflict_files = [
        f.strip() for f in conflict_result.stdout.strip().split("\n")
        if f.strip()
    ]

    if conflict_files:
        return False, conflict_files

    # Merge failed for another reason
    raise RuntimeError(f"Merge failed: {result.stderr}")


def push_branch(branch: str) -> None:
    """Push a branch to origin.

    Args:
        branch: Branch name to push

    Raises:
        RuntimeError: If push fails
    """
    try:
        run_git_command(["push", "origin", branch])
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to push branch '{branch}': {e.stderr}")


def get_diff_stat(destination: str, source: str) -> str:
    """Get diff statistics between branches.

    Args:
        destination: Destination branch name
        source: Source branch name

    Returns:
        Diff stat output as string
    """
    try:
        result = run_git_command(
            ["diff", "--stat", f"{destination}..{source}"],
            check=False
        )
        return result.stdout.strip()
    except Exception:
        return ""


def has_merge_commit_needed() -> bool:
    """Check if there's a merge commit that needs to be committed.

    Returns:
        True if there's a merge in progress that needs committing
    """
    # Check for MERGE_HEAD file which indicates an ongoing merge
    result = run_git_command(
        ["rev-parse", "--verify", "MERGE_HEAD"],
        check=False
    )
    return result.returncode == 0


def commit_merge() -> None:
    """Commit the current merge.

    Raises:
        RuntimeError: If commit fails
    """
    try:
        # Use --no-edit to accept the default merge message
        run_git_command(["commit", "--no-edit"])
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to commit merge: {e.stderr}")


def abort_merge() -> None:
    """Abort the current merge.

    Raises:
        RuntimeError: If abort fails
    """
    try:
        run_git_command(["merge", "--abort"])
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to abort merge: {e.stderr}")


# =============================================================================
# Branch Resolution
# =============================================================================

def resolve_destination_branch(explicit: Optional[str] = None) -> str:
    """Resolve the destination branch.

    Args:
        explicit: Explicitly provided destination branch

    Returns:
        Destination branch name

    Raises:
        RuntimeError: If no destination can be determined
    """
    if explicit:
        return explicit

    # Try to get from shared settings
    settings = load_shared_settings()
    protected = get_protected_branches(settings)

    if protected:
        # Return first protected branch as default destination
        return protected[0]

    raise RuntimeError(
        "No destination branch specified and no protected branches configured. "
        "Set destination explicitly or configure git.protected_branches in .sc/shared-settings.yaml"
    )


def resolve_source_branch(explicit: Optional[str] = None) -> str:
    """Resolve the source branch.

    Args:
        explicit: Explicitly provided source branch

    Returns:
        Source branch name

    Raises:
        RuntimeError: If no source can be determined
    """
    if explicit:
        return explicit

    return get_current_branch()


# =============================================================================
# Main Pipeline
# =============================================================================

def run_pipeline(input_data: CommitPushInput) -> Envelope:
    """Run the commit/pull/merge/push pipeline.

    Args:
        input_data: Pipeline input parameters

    Returns:
        Envelope with result data or error
    """
    # Step 1: Resolve branches
    try:
        source_branch = resolve_source_branch(input_data.source)
    except RuntimeError as e:
        return Envelope.error_response(
            code=ErrorCodes.GIT_REMOTE,
            message=str(e),
            recoverable=False,
            suggested_action="Ensure you are on a valid branch."
        )

    try:
        destination_branch = resolve_destination_branch(input_data.destination)
    except RuntimeError as e:
        return Envelope.error_response(
            code=ErrorCodes.CONFIG_PROTECTED_BRANCH,
            message=str(e),
            recoverable=False,
            suggested_action="Configure protected branches or specify --destination."
        )

    # Step 2: Check staged changes (informational - we continue either way)
    staged = has_staged_changes()
    # Note: We don't commit here - the agent handles staging and committing
    # This pipeline focuses on pull/merge/push after any commits are done

    # Step 3: Detect provider and get remote URL
    remote_url = get_remote_url()
    if not remote_url:
        return Envelope.error_response(
            code=ErrorCodes.GIT_REMOTE,
            message="Could not get remote URL from git",
            recoverable=False,
            suggested_action="Ensure you are in a git repository with an 'origin' remote."
        )

    provider_result = detect_provider(remote_url)
    if not provider_result.success:
        return provider_result

    provider_info = ProviderInfo(**provider_result.data)

    # Step 4: Fetch destination branch
    try:
        fetch_branch(destination_branch)
    except RuntimeError as e:
        return Envelope.error_response(
            code=ErrorCodes.GIT_REMOTE,
            message=str(e),
            recoverable=True,
            suggested_action="Check network connectivity and try again."
        )

    # Step 5: Merge destination into current branch
    try:
        merge_success, conflict_files = merge_branch(destination_branch)
    except RuntimeError as e:
        return Envelope.error_response(
            code=ErrorCodes.GIT_REMOTE,
            message=str(e),
            recoverable=False,
            suggested_action="Check git status and resolve any issues."
        )

    if not merge_success:
        # Abort the merge so user can resolve manually
        try:
            abort_merge()
        except RuntimeError:
            pass  # Best effort abort

        return Envelope.error_response(
            code=ErrorCodes.GIT_MERGE_CONFLICT,
            message="Merge conflict detected when pulling destination branch.",
            recoverable=True,
            suggested_action="Resolve conflicts, stage important files, then re-run.",
            data=CommitPushData(
                pr_exists=False,
                conflicts=conflict_files
            ).model_dump()
        )

    # Step 6: Commit merge if needed (fast-forward merges don't need commit)
    if has_merge_commit_needed():
        try:
            commit_merge()
        except RuntimeError as e:
            return Envelope.error_response(
                code=ErrorCodes.GIT_REMOTE,
                message=str(e),
                recoverable=False,
                suggested_action="Check git status and resolve any issues."
            )

    # Step 7: Push source branch
    try:
        push_branch(source_branch)
    except RuntimeError as e:
        # Check if it's an auth error
        error_str = str(e).lower()
        if "authentication" in error_str or "permission" in error_str or "denied" in error_str:
            return Envelope.error_response(
                code=ErrorCodes.GIT_AUTH,
                message=str(e),
                recoverable=False,
                suggested_action="Check git credentials and permissions."
            )
        return Envelope.error_response(
            code=ErrorCodes.GIT_REMOTE,
            message=str(e),
            recoverable=True,
            suggested_action="Check network connectivity and try again."
        )

    # Step 8: Check for existing PR
    try:
        pr_provider = get_provider(provider_info)
        pr_check = pr_provider.check_pr_exists(source_branch, destination_branch)

        if pr_check.exists and pr_check.pr:
            return Envelope.success_response(
                CommitPushData(
                    pr_exists=True,
                    pr=pr_check.pr
                ).model_dump()
            )

    except PrProviderError as e:
        # PR check failed, but push succeeded - report success with needs_pr_text
        pass

    # Step 9: PR doesn't exist - return context for PR creation
    diff_summary = get_diff_stat(destination_branch, source_branch)

    return Envelope.success_response(
        CommitPushData(
            pr_exists=False,
            needs_pr_text=True,
            context={
                "source_branch": source_branch,
                "destination_branch": destination_branch,
                "diff_summary": diff_summary,
                "provider": provider_info.provider
            }
        ).model_dump()
    )


# =============================================================================
# CLI Entry Point
# =============================================================================

def parse_args() -> CommitPushInput:
    """Parse command line arguments and stdin.

    Returns:
        CommitPushInput with parsed values
    """
    parser = argparse.ArgumentParser(
        description="Commit/Pull/Merge/Push pipeline for sc-commit-push-pr"
    )
    parser.add_argument(
        "--source", "-s",
        help="Source branch (default: current branch)"
    )
    parser.add_argument(
        "--destination", "-d",
        help="Destination branch (default: from settings)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Read JSON input from stdin"
    )

    args = parser.parse_args()

    # Check for JSON input from stdin
    if args.json or not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                json_data = json.loads(stdin_data)
                return CommitPushInput(**json_data)
        except (json.JSONDecodeError, ValueError):
            pass  # Fall through to use CLI args

    return CommitPushInput(
        source=args.source,
        destination=args.destination
    )


def main(input_data: Optional[CommitPushInput] = None) -> Envelope:
    """Main entry point.

    Args:
        input_data: Optional input parameters. If None, parses from CLI/stdin.

    Returns:
        Envelope with result data or error
    """
    if input_data is None:
        input_data = parse_args()

    return run_pipeline(input_data)


if __name__ == "__main__":
    result = main()
    print(result.to_fenced_json())
