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
        "tracking_path": null,          # optional, derived from worktree_base
        "stack": {                      # optional: cut a gh-stack layer from a PUSHED parent
            "trunk": "develop",         #   the branch the stack's bottom PR targets
            "above": null               #   layer currently stacked on `base` (mid-stack insert only)
        }
    }

Stack mode (`stack` present) cuts `branch` from `origin/<base>` with --no-track,
records the parent SHA, and returns a `stack_handoff` block for the worktree's
writer. Plain mode branches from the local base ref when one exists.

Exit Codes:
    0: Worktree created successfully
    1: Error during creation
"""

import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Support both relative import (when used as package) and absolute import (when used standalone)
try:
    from .envelope import Envelope, ErrorCodes, Transcript
    from .worktree_shared import (
        TrackingEntry,
        add_tracking_entry,
        check_branch_exists_local,
        check_branch_exists_remote,
        check_remote_branch_exists,
        create_tracking_branch,
        find_stack_children,
        get_default_tracking_path,
        get_repo_root,
        get_worktree_status,
        is_ancestor,
        load_tracking_jsonl,
        rev_parse,
        run_git,
    )
except ImportError:
    from envelope import Envelope, ErrorCodes, Transcript
    from worktree_shared import (
        TrackingEntry,
        add_tracking_entry,
        check_branch_exists_local,
        check_branch_exists_remote,
        check_remote_branch_exists,
        create_tracking_branch,
        find_stack_children,
        get_default_tracking_path,
        get_repo_root,
        get_worktree_status,
        is_ancestor,
        load_tracking_jsonl,
        rev_parse,
        run_git,
    )


# =============================================================================
# Input Models
# =============================================================================


class StackInput(BaseModel):
    """Stack-layer inputs: the worktree is a gh-stack layer cut from a pushed parent (`base`)."""

    trunk: str = Field(..., description="Stack trunk: the branch the bottom PR of the stack targets")
    above: Optional[str] = Field(
        None,
        description="Layer currently stacked directly on `base`; set only when inserting mid-stack",
    )

    @field_validator("trunk")
    @classmethod
    def validate_trunk(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("stack.trunk cannot be empty")
        return v.strip()

    @field_validator("above")
    @classmethod
    def validate_above(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


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
    stack: Optional[StackInput] = Field(None, description="Present when the worktree is a gh-stack layer")

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




# =============================================================================
# Stack layers (gh-stack)
# =============================================================================


def check_stack_preconditions(
    input_data: CreateInput,
    repo_root: Path,
    transcript: Transcript,
    *,
    branch_exists_local: bool,
    branch_exists_remote: bool,
    tracking_entries: Optional[list] = None,
) -> tuple:
    """Validate a stack cut. Returns (stack_info, None) or (None, error Envelope).

    Rules (from the gh-stack field playbook): a layer is always a new branch cut
    from its parent's PUSHED head; the parent sits on the trunk and is not already
    landed; when inserting, the layer above must actually be stacked on the parent.
    """
    stack = input_data.stack
    base = input_data.base
    trunk = stack.trunk
    above = stack.above

    def fail(code: str, message: str, action: str, **data: Any) -> tuple:
        transcript.step_failed(step="stack preconditions", error=message)
        return None, Envelope.error_response(
            code=code,
            message=message,
            recoverable=True,
            suggested_action=action,
            data=data or None,
            transcript=transcript,
        )

    if branch_exists_local or branch_exists_remote:
        return fail(
            ErrorCodes.STACK_LAYER_EXISTS,
            f"Branch '{input_data.branch}' already exists; a stack layer is always a new branch cut from its parent's pushed head",
            "Choose a new layer name, or omit `stack` to open a worktree on the existing branch",
        )

    parent_sha = rev_parse(f"origin/{base}", cwd=repo_root)
    if not parent_sha:
        return fail(
            ErrorCodes.STACK_PARENT_NOT_PUSHED,
            f"Stack parent '{base}' is not on origin; layers are cut from pushed heads only",
            f"Push the parent first (git push -u origin {base}) and retry",
        )

    trunk_sha = rev_parse(f"origin/{trunk}", cwd=repo_root)
    if not trunk_sha:
        return fail(
            ErrorCodes.BRANCH_NOT_FOUND,
            f"Stack trunk '{trunk}' not found on origin",
            "Pass the branch the stack's bottom PR targets (for example develop) as stack.trunk",
        )

    if above is not None and above in (base, input_data.branch):
        return fail(
            ErrorCodes.STACK_ABOVE_INVALID,
            f"stack.above '{above}' must name the layer currently stacked on '{base}', not the parent or the new layer",
            "Read the layer above the parent from /sc-gh-stack-view and pass that name",
        )

    parent_behind_trunk = 0
    if base != trunk:
        if is_ancestor(f"origin/{base}", f"origin/{trunk}", cwd=repo_root):
            return fail(
                ErrorCodes.STACK_PARENT_LANDED,
                f"Stack parent '{base}' is already contained in trunk '{trunk}'; cutting from it would start the layer behind the trunk",
                f"Cut from '{trunk}' (bottom layer) or from the current top shown by /sc-gh-stack-view",
            )
        mb = run_git(["merge-base", f"origin/{trunk}", f"origin/{base}"], cwd=repo_root, check=False)
        if mb.returncode != 0:
            return fail(
                ErrorCodes.STACK_PARENT_OFF_TRUNK,
                f"origin/{base} and origin/{trunk} share no history",
                "Check stack.trunk; the parent must be a layer stacked on that trunk",
            )
        if not is_ancestor(f"origin/{trunk}", f"origin/{base}", cwd=repo_root):
            behind = run_git(["rev-list", "--count", f"origin/{base}..origin/{trunk}"], cwd=repo_root, check=False)
            parent_behind_trunk = int(behind.stdout.strip() or 0) if behind.returncode == 0 else -1
            transcript.step_ok(
                step=f"git merge-base --is-ancestor origin/{trunk} origin/{base}",
                message=f"parent behind trunk by {parent_behind_trunk} commit(s); allowed (stack bottom note, not a blocker)",
            )

    if above is not None:
        above_sha = rev_parse(f"origin/{above}", cwd=repo_root)
        if not above_sha:
            return fail(
                ErrorCodes.STACK_ABOVE_INVALID,
                f"stack.above '{above}' is not on origin",
                "Pass the pushed layer that is stacked on the parent, or omit `above` when cutting from the top",
            )
        if not is_ancestor(f"origin/{base}", f"origin/{above}", cwd=repo_root):
            return fail(
                ErrorCodes.STACK_ABOVE_INVALID,
                f"origin/{above} does not contain origin/{base}, so it is not stacked on '{base}'",
                "Read the real layer above the parent from /sc-gh-stack-view, or omit `above`",
            )

    if above is None and tracking_entries:
        # Appending: the parent must be the top. A live layer already on it means this cut
        # would fork the stack (two layers sharing a parent), which cannot be linked linearly.
        existing = find_stack_children(tracking_entries, base, cwd=repo_root)
        if existing:
            return fail(
                ErrorCodes.STACK_PARENT_HAS_CHILD,
                f"'{base}' already has live layer(s) on it: {', '.join(existing)}; cutting another from it would fork the stack",
                f"Cut from the current top ({existing[-1]}) instead, or pass stack.above = '{existing[-1]}' to insert under it",
                existing_children=existing,
            )

    local_base_sha = rev_parse(base, cwd=repo_root)
    if local_base_sha and local_base_sha != parent_sha:
        transcript.step_ok(
            step=f"git rev-parse {base}",
            message=f"local {base} ({local_base_sha[:8]}) differs from origin ({parent_sha[:8]}); cutting from origin",
        )

    transcript.step_ok(
        step=f"git rev-parse origin/{base}",
        message=f"parent_sha={parent_sha}",
    )

    stack_info = {
        "trunk": trunk,
        "parent": base,
        "parent_sha": parent_sha,
        "above": above,
        "position": "insert" if above else "top",
        "parent_behind_trunk": parent_behind_trunk,
    }
    return stack_info, None


def build_stack_handoff(
    branch: str,
    purpose: str,
    worktree_path: Path,
    stack_info: Dict[str, Any],
    repo_root: Path,
) -> Dict[str, Any]:
    """The information needed to stack this layer, split by role.

    `writer` is for the single agent that works in the worktree; `stack_writer` is for
    the one agent that runs gh stack write commands and opens PRs (never the layer's
    writer). Everything derives from the gh-stack field playbook (sc-gh-stack).
    Angle-bracket placeholders are read from /sc-gh-stack-view or gh output.
    """
    trunk = stack_info["trunk"]
    parent = stack_info["parent"]
    sha = stack_info["parent_sha"]
    above = stack_info.get("above")
    chain_check = repo_root / ".claude" / "scripts" / "gh_stack_chain_check.py"
    chain_check_available = chain_check.exists()
    wt = shlex.quote(str(worktree_path))
    bottom = parent == trunk
    # Layers below the parent, as PR-number and branch-name placeholders. A layer cut
    # from the trunk is the stack bottom: nothing sits below it.
    lower_prs = "" if bottom else f"<bottom-pr#> ... <pr# of {parent}> "
    lower_names = "" if bottom else f"<bottom> ... {parent} "

    pr_base_rule = f"The PR base is {parent}" + ("" if bottom else f", never {trunk}") + "."
    writer_rules = [
        f"You are the only writer of {branch}. Never edit, rebase, or force-push any layer below it.",
        f"Make a WIP commit within minutes and push it; the stack writer opens the PR and links it on that first push, never 'once it is green'. {pr_base_rule}",
        (
            f"Rebase at most once per task, at the start, only while this layer has no children: "
            f"git fetch origin && git rebase --onto origin/{parent} {sha} {branch} && git push --force-with-lease. "
            f"Between tasks the layer does not move."
        ),
        f"Never run gh stack write commands (link, unstack, sync, rebase, merge) or open PRs from this worktree; report to the stack writer.",
        f"The next layer is cut from origin/{branch} after it is pushed, never from a local ref.",
    ]
    writer_commands = [
        f"git -C {wt} commit --allow-empty -m {shlex.quote('wip: ' + purpose[:60])}   # first WIP commit now; a PR needs at least one",
        f"git -C {wt} push -u origin {branch}",
    ]

    pr_body = f"Parent: {parent} @ {sha}\nTask: {purpose}\nFence: <paths this layer may touch>"
    pr_create = (
        f"gh pr create --base {parent} --head {branch} --title \"<title>\" --body \"$(cat <<'B'\n"
        f"Parent: {parent} @ {sha}\nTask: {purpose}\nFence: <paths this layer may touch>\nB\n)\""
    )
    stack_writer_commands = [
        f"# after the writer's first push of {branch}:",
        pr_create,
        f"cd {wt} && gh stack checkout <stack#>   # import tracking into this new worktree; skip only when no stack exists yet",
    ]
    if above:
        stack_writer_commands += [
            f"# every layer above {parent}, bottom to top, carries the layer below it forward with ONE merge commit each",
            f"# (never a rebase, never a force-push), starting with the writer of {above}:",
            f"git -C <worktree of {above}> fetch origin && git -C <worktree of {above}> merge --no-ff origin/{branch} && git -C <worktree of {above}> push",
            f"# then the layer above {above} merges origin/{above}, and so on up to the top",
            "gh stack unstack <stack#>                       # PRs and branches untouched; confirm with the user first",
            f"gh pr edit <pr# of {above}> --base {branch}",
        ]
        if chain_check_available:
            stack_writer_commands.append(
                f"python3 .claude/scripts/gh_stack_chain_check.py --trunk {trunk} {lower_names}{branch} {above} ... <top>   # must print LINKABLE"
            )
        stack_writer_commands += [
            f"gh stack link --base {trunk} {lower_prs}<pr# of {branch}> <pr# of {above}> ... <top-pr#>",
            "# every other stack worktree: gh stack unstack --local && gh stack checkout <new stack#>",
            "/sc-gh-stack-view",
        ]
    else:
        if chain_check_available:
            stack_writer_commands.append(
                f"python3 .claude/scripts/gh_stack_chain_check.py --trunk {trunk} {lower_names}{branch}   # must print LINKABLE"
            )
        stack_writer_commands += [
            f"gh stack link <stack#> <pr# of {branch}>          # append: only if {parent} is the top row in /sc-gh-stack-view",
            f"gh stack link --base {trunk} {lower_prs}<pr# of {branch}>   # first link, or full relink",
            "/sc-gh-stack-view",
        ]

    return {
        "position": stack_info["position"],
        "trunk": trunk,
        "parent": parent,
        "parent_sha": sha,
        "above": above,
        "pr_base": parent,
        "pr_body": pr_body,
        "writer": {
            "audience": f"the single agent working in {worktree_path}",
            "rules": writer_rules,
            "commands": writer_commands,
        },
        "stack_writer": {
            "audience": "the one agent that opens PRs and runs gh stack write commands (not the layer's writer)",
            "commands": stack_writer_commands,
        },
        "chain_check_available": chain_check_available,
        "reference": (
            "sc-gh-stack references/recipe-restack.md section 1 (insert)"
            if above
            else "sc-gh-stack references/recipe-link.md section A (first push)"
        ),
    }


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

        # Stack layer: validate the cut before touching anything
        stack_info: Optional[Dict[str, Any]] = None
        if input_data.stack is not None:
            stack_info, stack_error = check_stack_preconditions(
                input_data,
                repo_root,
                transcript,
                branch_exists_local=branch_exists_local,
                branch_exists_remote=branch_exists_remote,
                tracking_entries=load_tracking_jsonl(tracking_path) if tracking_path else None,
            )
            if stack_error is not None:
                return stack_error

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
            if stack_info is not None:
                # Stack layers are always cut from the parent's PUSHED head
                base_ref = f"origin/{input_data.base}"
                transcript.step_ok(
                    step="resolve base",
                    message=f"stack layer: cutting from pushed head {base_ref}",
                )
            elif base_exists_local:
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

            # A branch started from a remote-tracking ref must not inherit it as
            # upstream: otherwise `git push` / `--force-with-lease` target the base.
            add_args = ["worktree", "add"]
            if base_ref.startswith("origin/"):
                add_args.append("--no-track")
            add_args += ["-b", input_data.branch, str(worktree_path), base_ref]
            git_cmd = "git " + " ".join(add_args)
            with transcript.timed_step(git_cmd) as t:
                run_git(add_args, cwd=repo_root)
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
            stack=(
                {k: stack_info[k] for k in ("trunk", "parent", "parent_sha", "above", "position")}
                if stack_info
                else None
            ),
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
        data: Dict[str, Any] = {
            "action": "create",
            "branch": input_data.branch,
            "base": input_data.base,
            "path": str(worktree_path),
            "repo_name": repo_name,
            "status": "clean",
            "branch_created": needs_new_branch,
            "tracking_entry": tracking_entry.model_dump(),
            "tracking_updated": tracking_updated,
        }
        if stack_info is not None:
            data["stack"] = tracking_entry.stack
            data["stack_handoff"] = build_stack_handoff(
                input_data.branch, input_data.purpose, worktree_path, stack_info, repo_root
            )
        return Envelope.success_response(data=data, transcript=transcript)

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
