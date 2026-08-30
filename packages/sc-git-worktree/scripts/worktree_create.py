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
    from .envelope import Envelope, ErrorCodes, Transcript
    from .worktree_scan import parse_worktree_list_porcelain
    from .worktree_shared import (
        TrackingEntry,
        add_tracking_entry,
        check_branch_exists_local,
        check_branch_exists_remote,
        check_gh_stack_tracked,
        check_remote_branch_exists,
        create_tracking_branch,
        get_default_tracking_path,
        get_protected_branches,
        get_repo_root,
        get_worktree_status,
        is_branch_merged,
        resolve_merge_base,
        run_git,
    )
except ImportError:
    from envelope import Envelope, ErrorCodes, Transcript
    from worktree_scan import parse_worktree_list_porcelain
    from worktree_shared import (
        TrackingEntry,
        add_tracking_entry,
        check_branch_exists_local,
        check_branch_exists_remote,
        check_gh_stack_tracked,
        check_remote_branch_exists,
        create_tracking_branch,
        get_default_tracking_path,
        get_protected_branches,
        get_repo_root,
        get_worktree_status,
        is_branch_merged,
        resolve_merge_base,
        run_git,
    )


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
    flat: bool = Field(
        False,
        description=(
            "Explicit override to bypass the need-based stacking guard and force a "
            "flat create even when the base branch is neither protected nor merged "
            "into trunk. Use only for a base that is genuinely independent despite "
            "being unmerged (e.g. a long-lived integration branch)."
        ),
    )
    protected_branches: Optional[List[str]] = Field(
        None, description="List of protected branch names (auto-detected if omitted)"
    )
    cache_protected_branches: bool = Field(
        True, description="Cache protected branches to shared settings"
    )

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

    @field_validator("protected_branches")
    @classmethod
    def validate_protected_branches(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [b.strip() for b in v if b.strip()]




# =============================================================================
# Need-based stacking guard
# =============================================================================


def _slugify_branch(branch: str) -> str:
    """Convert a branch name to the worktree-directory slug convention (/ -> -)."""
    return branch.replace("/", "-")


def _find_worktree_for_branch(branch: str, repo_root: Path) -> Optional[Path]:
    """Find the worktree path (if any) that currently has `branch` checked out."""
    result = run_git(["worktree", "list", "--porcelain"], cwd=repo_root, check=False)
    if result.returncode != 0:
        return None
    for wt in parse_worktree_list_porcelain(result.stdout):
        if wt.branch == branch:
            return Path(wt.path)
    return None


def _is_base_merged(
    base: str,
    trunk: Optional[str],
    base_exists_local: bool,
    cwd: Path,
) -> bool:
    """Check whether `base` is merged into `trunk`.

    Mirrors the pattern used elsewhere in this package (resolve_merge_base +
    is_branch_merged), extended to also check remote-tracking branches when
    the base only exists on the remote (is_branch_merged only looks at local
    branch names).
    """
    if not trunk:
        return False
    if base_exists_local:
        return is_branch_merged(base, base=trunk, cwd=cwd)

    # Base exists remotely only - check remote-tracking branches instead.
    result = run_git(["branch", "-r", "--merged", trunk], cwd=cwd, check=False)
    if result.returncode != 0:
        return False
    merged = [b.strip().lstrip("*+ ") for b in result.stdout.strip().split("\n")]
    return f"origin/{base}" in merged


def check_needs_stack_guard(
    input_data: CreateInput,
    repo_root: Path,
    base_exists_local: bool,
    transcript: Transcript,
) -> Optional[Envelope]:
    """Enforce "a worktree must be stacked iff the base branch requires it".

    Returns an error Envelope (CREATE.NEEDS_STACK) if a flat create must be
    refused, or None if the caller may proceed with a flat create.
    """
    if input_data.flat:
        transcript.step_skipped(
            step="needs_stack_guard",
            message="flat=true override - proceeding with flat create",
        )
        return None

    base = input_data.base

    try:
        protected_branches = get_protected_branches(
            cwd=repo_root,
            user_provided=input_data.protected_branches,
            cache_shared=input_data.cache_protected_branches,
            log_fn=lambda msg: transcript.step_ok(step="protected branches", message=msg),
        )
    except ValueError:
        # Create has never required protected-branch config; fail OPEN so the
        # historical flat-create path keeps working in unconfigured repos. The
        # guard re-activates once protected branches are configured or cached
        # (scan/cleanup do that).
        transcript.step_skipped(
            step="needs_stack_guard",
            message="protected branches not configured - guard skipped (flat create)",
        )
        return None

    base_protected = base in protected_branches

    trunk = resolve_merge_base(
        cwd=repo_root,
        user_provided=protected_branches,
        cache_shared=input_data.cache_protected_branches,
    )

    base_merged = False
    if not base_protected:
        base_merged = _is_base_merged(base, trunk, base_exists_local, repo_root)

    transcript.step_ok(
        step="needs_stack_guard",
        message=(
            f"base={base} base_protected={base_protected} "
            f"base_merged={base_merged} trunk={trunk}"
        ),
    )

    if base_protected or base_merged:
        # Flat create proceeds exactly as today.
        return None

    # Base is neither protected nor merged into trunk: refuse the flat
    # create and route toward stacking (fail direction on ambiguity).
    base_worktree = _find_worktree_for_branch(base, repo_root)
    gh_stack_tracked: Optional[bool] = None
    stack_worktree_path: Optional[Path] = None

    if base_worktree is not None:
        gh_stack_tracked = check_gh_stack_tracked(base_worktree)
        if gh_stack_tracked:
            stack_worktree_path = base_worktree

    base_slug = _slugify_branch(base)
    if input_data.worktree_base:
        worktree_base = Path(input_data.worktree_base).resolve()
    else:
        worktree_base = repo_root.parent / f"{repo_root.name}-worktrees"
    suggested_stack_path = worktree_base / "stack" / base_slug
    trunk_display = trunk.removeprefix("origin/") if trunk else base

    if gh_stack_tracked:
        suggested_action = (
            f"base '{base}' is a layer of a tracked stack - create the new branch as "
            f"a layer in that stack's worktree ({stack_worktree_path}); do not create "
            "a separate worktree"
        )
    else:
        suggested_action = (
            f"base '{base}' is unmerged: create a stack worktree at "
            f"{suggested_stack_path} and `gh stack init --base {trunk_display} "
            f"{base} {input_data.branch}` (install sc-gh-stack for the full workflow)"
        )

    transcript.step_failed(
        step="needs_stack_guard",
        error=f"base '{base}' is neither protected nor merged into trunk '{trunk_display}'",
    )

    return Envelope.error_response(
        code=ErrorCodes.CREATE_NEEDS_STACK,
        message=(
            f"Base branch '{base}' is neither protected nor merged into trunk - "
            "new work on it depends on unmerged work and must be a stack layer, "
            "not a flat worktree"
        ),
        recoverable=True,
        suggested_action=suggested_action,
        data={
            "base": base,
            "base_merged": base_merged,
            "base_protected": base_protected,
            "gh_stack_tracked": gh_stack_tracked,
            "suggested_worktree_path": str(
                stack_worktree_path if stack_worktree_path is not None else suggested_stack_path
            ),
        },
        transcript=transcript,
    )


# =============================================================================
# Main Logic
# =============================================================================


def create_worktree_main(input_data: CreateInput) -> Envelope:
    """Main worktree creation logic.

    Args:
        input_data: Validated input

    Returns:
        Envelope with success/error response including operation transcript
    """
    transcript = Transcript()

    try:
        # Determine repo root
        if input_data.repo_root:
            repo_root = Path(input_data.repo_root).resolve()
        else:
            repo_root = get_repo_root()

        if not repo_root.exists():
            transcript.step_failed(
                step="detect_repo",
                error=f"Repository root does not exist: {repo_root}",
            )
            return Envelope.error_response(
                code=ErrorCodes.GIT_NOT_REPO,
                message=f"Repository root does not exist: {repo_root}",
                recoverable=False,
                transcript=transcript,
            )

        repo_name = repo_root.name
        transcript.step_ok(
            step="git rev-parse --show-toplevel",
            message=str(repo_root),
            value={"repo_name": repo_name},
        )

        # Determine worktree base
        if input_data.worktree_base:
            worktree_base = Path(input_data.worktree_base).resolve()
        else:
            worktree_base = repo_root.parent / f"{repo_name}-worktrees"

        # Ensure worktree base exists
        worktree_base.mkdir(parents=True, exist_ok=True)
        transcript.step_ok(
            step=f"mkdir -p {worktree_base}",
            message="created" if not worktree_base.exists() else "exists",
        )

        # Determine tracking path (JSONL format)
        if input_data.tracking_enabled:
            if input_data.tracking_path:
                tracking_path = Path(input_data.tracking_path).resolve()
            else:
                tracking_path = get_default_tracking_path(worktree_base)

            tracking_existed = tracking_path.exists()
            transcript.step_ok(
                step=f"init {tracking_path}",
                message="exists" if tracking_existed else "will create",
            )
        else:
            tracking_path = None
            transcript.step_skipped(step="init_tracking", message="disabled")

        # Fetch all remotes
        with transcript.timed_step("git fetch --all --prune") as t:
            run_git(["fetch", "--all", "--prune"], cwd=repo_root)

        # Check if base branch exists (local)
        base_local_result = run_git(["branch", "--list", input_data.base], cwd=repo_root, check=False)
        base_exists_local = bool(base_local_result.stdout.strip())

        # Check if base branch exists (remote)
        base_remote_result = run_git(["branch", "-r", "--list", f"origin/{input_data.base}"], cwd=repo_root, check=False)
        base_exists_remote = bool(base_remote_result.stdout.strip())

        if not base_exists_local and not base_exists_remote:
            transcript.step_failed(
                step=f"git branch --list {input_data.base}",
                error="not found locally or remotely",
            )
            return Envelope.error_response(
                code=ErrorCodes.BRANCH_NOT_FOUND,
                message=f"Base branch '{input_data.base}' not found",
                recoverable=False,
                suggested_action="Verify the base branch exists locally or remotely",
                transcript=transcript,
            )

        transcript.step_ok(
            step=f"git branch --list {input_data.base}",
            message=f"local={base_exists_local} remote={base_exists_remote}",
        )

        # Need-based stacking guard: a worktree must be stacked iff the base
        # branch requires it. Runs before any worktree/branch mutation.
        guard_error = check_needs_stack_guard(
            input_data=input_data,
            repo_root=repo_root,
            base_exists_local=base_exists_local,
            transcript=transcript,
        )
        if guard_error is not None:
            return guard_error

        # Determine worktree path
        worktree_path = worktree_base / input_data.branch

        # Check if path already exists
        if worktree_path.exists():
            transcript.step_failed(
                step="check_path",
                error=f"Worktree path already exists: {worktree_path}",
            )
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_EXISTS,
                message=f"Worktree path already exists: {worktree_path}",
                recoverable=False,
                suggested_action="Remove existing worktree or choose different branch name",
                transcript=transcript,
            )

        # Check if branch exists (local or remote)
        branch_local_result = run_git(["branch", "--list", input_data.branch], cwd=repo_root, check=False)
        branch_exists_local = bool(branch_local_result.stdout.strip())

        branch_remote_result = run_git(["branch", "-r", "--list", f"origin/{input_data.branch}"], cwd=repo_root, check=False)
        branch_exists_remote = bool(branch_remote_result.stdout.strip())

        transcript.step_ok(
            step=f"git branch --list {input_data.branch}",
            message=f"local={branch_exists_local} remote={branch_exists_remote}",
        )

        # Determine creation strategy
        if branch_exists_local:
            # Branch exists locally, just add worktree
            git_cmd = f"git worktree add {worktree_path} {input_data.branch}"
            with transcript.timed_step(git_cmd) as t:
                run_git(["worktree", "add", str(worktree_path), input_data.branch], cwd=repo_root)
                t.message = f"Preparing worktree ({worktree_path})"
            needs_new_branch = False
        elif branch_exists_remote:
            # Branch exists on remote only - create local tracking branch first
            transcript.step_ok(
                step=f"git branch --track {input_data.branch} origin/{input_data.branch}",
                message="creating local tracking branch",
            )
            if not create_tracking_branch(input_data.branch, cwd=repo_root):
                # Fallback: let git worktree add handle it (may auto-create tracking)
                transcript.step_ok(
                    step="tracking branch fallback",
                    message="using git worktree add directly",
                )
            git_cmd = f"git worktree add {worktree_path} {input_data.branch}"
            with transcript.timed_step(git_cmd) as t:
                run_git(["worktree", "add", str(worktree_path), input_data.branch], cwd=repo_root)
                t.message = f"Preparing worktree ({worktree_path})"
            needs_new_branch = False
        else:
            # New branch, create from base
            # Determine the actual base ref to use (local or remote)
            if base_exists_local:
                base_ref = input_data.base
            elif base_exists_remote:
                base_ref = f"origin/{input_data.base}"
                transcript.step_ok(
                    step="resolve base",
                    message=f"using remote base: {base_ref}",
                )
            else:
                # Neither local nor remote base exists - error handled earlier
                base_ref = input_data.base

            git_cmd = f"git worktree add -b {input_data.branch} {worktree_path} {base_ref}"
            with transcript.timed_step(git_cmd) as t:
                run_git(["worktree", "add", "-b", input_data.branch, str(worktree_path), base_ref], cwd=repo_root)
                t.message = f"Preparing worktree ({worktree_path})"
            needs_new_branch = True

        # Verify worktree is clean
        is_clean, dirty_files = get_worktree_status(worktree_path)
        transcript.step_ok(
            step=f"git -C {worktree_path} status --porcelain",
            message="clean" if is_clean else "\n".join(dirty_files),
        )

        if not is_clean:
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_DIRTY,
                message="Worktree has uncommitted changes after creation",
                recoverable=False,
                suggested_action="Investigate worktree state; manual cleanup may be required",
                data={"dirty_files": dirty_files},
                transcript=transcript,
            )

        # Create tracking entry (JSONL format with remote sync fields)
        now = datetime.now(timezone.utc).isoformat()
        remote_exists = check_remote_branch_exists(input_data.branch, cwd=repo_root)
        tracking_entry = TrackingEntry(
            branch=input_data.branch,
            path=str(worktree_path),
            base=input_data.base,
            purpose=input_data.purpose,
            owner=input_data.owner,
            created=now,
            status="active",
            last_checked=now,
            notes="",
            remote_exists=remote_exists,
            local_worktree=True,
            remote_ahead=0,  # Just created, local is up to date
        )

        # Update tracking document (JSONL)
        tracking_updated = False
        if tracking_path:
            add_tracking_entry(tracking_path, tracking_entry)
            tracking_updated = True
            transcript.step_ok(
                step=f"append {tracking_path.name}",
                message=input_data.branch,
            )
        else:
            transcript.step_skipped(step="update_tracking", message="disabled")

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
                "tracking_entry": tracking_entry.model_dump(),
                "tracking_updated": tracking_updated,
            },
            transcript=transcript,
        )

    except subprocess.CalledProcessError as e:
        cmd = " ".join(e.cmd) if isinstance(e.cmd, list) else str(e.cmd)
        error_output = e.stderr or e.stdout or str(e)
        transcript.step_failed(
            step=cmd,
            error=error_output,
        )

        # Detect specific error conditions
        if "is already checked out at" in error_output:
            return Envelope.error_response(
                code=ErrorCodes.WORKTREE_BRANCH_IN_USE,
                message=f"Branch '{input_data.branch}' is already checked out in another worktree",
                recoverable=False,
                suggested_action="Use the existing worktree or choose a different branch name",
                transcript=transcript,
            )

        return Envelope.error_response(
            code=ErrorCodes.GIT_ERROR,
            message=f"Git command failed: {error_output}",
            recoverable=False,
            transcript=transcript,
        )
    except Exception as e:
        transcript.step_failed(
            step="unexpected",
            error=str(e),
        )
        return Envelope.error_response(
            code=ErrorCodes.GIT_ERROR,
            message=f"Unexpected error: {str(e)}",
            recoverable=False,
            transcript=transcript,
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
