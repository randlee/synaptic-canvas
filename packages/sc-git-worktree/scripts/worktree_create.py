#!/usr/bin/env python3
"""Create a git worktree with optional tracking.

This script is a FACTORY producing exactly one of three products for every
create request (see DESIGN.md "Worktree factory decision model"):

    A. Flat worktree   - legacy, unchanged: `git worktree add <wt_base>/<branch>
                          -b <branch> <base>`.
    B. New stack        - identical to A (same path, no `stack/` prefix), plus
                          `git config rerere.enabled true` and `gh stack init`
                          in the new worktree.
    C. Stack layer      - no new worktree; the new branch is added as a layer
                          in the base's existing stack worktree via
                          `git checkout -b` + `gh stack add`.

`resolve_product()` implements the decision precedence: Intent (`flat`) >
Dependency (is the base a layer of unmerged work?) > Policy (`always_stack`)
> default A. It is evaluated lazily so that a stack-inactive repo never pays
for (or sees transcript noise from) any of the stacking machinery.

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
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        check_stack_prerequisites,
        create_tracking_branch,
        get_always_stack_setting,
        get_default_tracking_path,
        get_protected_branches,
        get_repo_root,
        get_stack_root_setting,
        get_worktree_status,
        is_branch_merged,
        resolve_merge_base,
        resolve_stack_root,
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
        check_stack_prerequisites,
        create_tracking_branch,
        get_always_stack_setting,
        get_default_tracking_path,
        get_protected_branches,
        get_repo_root,
        get_stack_root_setting,
        get_worktree_status,
        is_branch_merged,
        resolve_merge_base,
        resolve_stack_root,
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
            "Explicit intent override: force product A (a plain flat worktree) "
            "regardless of dependency or policy signals. Nothing else is "
            "evaluated when this is set - no settings are read, no prerequisite "
            "check runs, no stacking transcript steps are recorded. Use only "
            "for a base that is genuinely independent despite being unmerged "
            "(e.g. a long-lived integration branch)."
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
# Factory decision model helpers
# =============================================================================


def _slugify_branch(branch: str) -> str:
    """Convert a branch name to the slug convention (/ -> -) used only in
    *suggestions* (a not-yet-existing worktree path named in a refusal)."""
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

    Extended to also check remote-tracking branches when the base only
    exists on the remote (is_branch_merged only looks at local branch names).
    """
    if not trunk:
        return False
    if base_exists_local:
        return is_branch_merged(base, base=trunk, cwd=cwd)

    result = run_git(["branch", "-r", "--merged", trunk], cwd=cwd, check=False)
    if result.returncode != 0:
        return False
    merged = [b.strip().lstrip("*+ ") for b in result.stdout.strip().split("\n")]
    return f"origin/{base}" in merged


def _rebase_in_progress(path: Path) -> bool:
    """True if `path`'s worktree has a rebase in progress. Fail closed to False."""
    try:
        result = run_git(["rev-parse", "--git-dir"], cwd=path, check=False)
    except OSError:
        return False
    if result.returncode != 0:
        return False
    git_dir_raw = result.stdout.strip()
    if not git_dir_raw:
        return False
    git_dir = Path(git_dir_raw)
    if not git_dir.is_absolute():
        git_dir = (path / git_dir).resolve()
    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def _probe_stack_active(repo_root: Path) -> Tuple[bool, bool]:
    """Cheap, unconditional, fail-closed-to-inactive stack-activity probe.

    A repo is stack-active iff `git.always_stack` is truthy, OR any existing
    worktree carries gh-stack tracking. Any error probing either signal
    resolves to "not stack-active" (positive-signal rule: every indeterminate
    input resolves to product A).

    Returns:
        (stack_active, always_stack_setting)
    """
    try:
        always_stack = bool(get_always_stack_setting(repo_root))
    except Exception:
        always_stack = False

    if always_stack:
        return True, True

    try:
        result = run_git(["worktree", "list", "--porcelain"], cwd=repo_root, check=False)
        if result.returncode != 0:
            return False, always_stack
        for wt in parse_worktree_list_porcelain(result.stdout):
            if check_gh_stack_tracked(Path(wt.path)):
                return True, always_stack
    except Exception:
        return False, always_stack

    return False, always_stack


@dataclass
class ProductDecision:
    """Result of resolving Dependency + Policy (stages 4-5 of the factory
    decision model). `product` is one of "A", "B", "C", or None (refused -
    `refusal` holds the ready-to-return Envelope)."""

    product: Optional[str]
    reason: str
    stack_worktree_path: Optional[Path] = None
    base: Optional[str] = None
    trunk: Optional[str] = None
    refusal: Optional[Envelope] = None


def resolve_product(
    input_data: CreateInput,
    repo_root: Path,
    base_exists_local: bool,
    always_stack: bool,
    transcript: Transcript,
) -> ProductDecision:
    """Resolve Dependency (stage 4) and Policy (stage 5) of the factory
    decision model.

    Preconditions (enforced by the caller): the repo is stack-active, intent
    (`flat`) has not already short-circuited to product A, and the mandatory
    stack-prerequisite gate (stage 3) has already passed.

    Dependency: base protected or merged into trunk -> independent; else
    dependent. Trunk/protected resolution failures treat the base as
    independent (positive-signal; this must never surface
    CONFIG.PROTECTED_BRANCH_NOT_SET from create).

    Dependent bases resolve to product C (a layer in the base's existing
    tracked stack worktree) unless that is not mechanically executable
    (a rebase in progress there, or no gh-stack tracking anywhere for the
    base - meaning there is no stack to join and a new 2-layer stack is a
    bigger operation than create handles) - both refuse CREATE.NEEDS_STACK.

    Independent bases resolve to B when `always_stack` is truthy, else A.
    """
    base = input_data.base

    try:
        protected_branches = get_protected_branches(
            cwd=repo_root,
            user_provided=input_data.protected_branches,
            cache_shared=input_data.cache_protected_branches,
            log_fn=lambda msg: transcript.step_ok(step="protected branches", message=msg),
        )
        base_protected = base in protected_branches
        trunk = resolve_merge_base(
            cwd=repo_root,
            user_provided=protected_branches,
            cache_shared=input_data.cache_protected_branches,
        )
        base_merged = False if base_protected else _is_base_merged(
            base, trunk, base_exists_local, repo_root
        )
        independent = base_protected or base_merged
    except ValueError:
        # Protected branches / trunk not configured/resolvable: treat the
        # base as independent (positive-signal rule).
        base_protected = False
        base_merged = False
        trunk = None
        independent = True

    transcript.step_ok(
        step="resolve_product",
        message=(
            f"base={base} base_protected={base_protected} "
            f"base_merged={base_merged} trunk={trunk} independent={independent}"
        ),
    )

    if independent:
        if always_stack:
            return ProductDecision(product="B", reason="independent base, always_stack policy")
        return ProductDecision(product="A", reason="independent base, policy off")

    # Dependent: base is neither protected nor merged into trunk.
    base_worktree = _find_worktree_for_branch(base, repo_root)
    gh_stack_tracked = check_gh_stack_tracked(base_worktree) if base_worktree is not None else False

    if input_data.worktree_base:
        worktree_base_for_suggestion = Path(input_data.worktree_base).resolve()
    else:
        worktree_base_for_suggestion = repo_root.parent / f"{repo_root.name}-worktrees"
    trunk_display = trunk.removeprefix("origin/") if trunk else base

    if gh_stack_tracked and base_worktree is not None:
        if _rebase_in_progress(base_worktree):
            transcript.step_failed(
                step="resolve_product",
                error=f"stack worktree {base_worktree} has a rebase in progress",
            )
            return ProductDecision(
                product=None,
                reason="rebase_in_progress",
                refusal=Envelope.error_response(
                    code=ErrorCodes.CREATE_NEEDS_STACK,
                    message=(
                        f"Base '{base}' stack worktree has a rebase in progress; "
                        "cannot add a new layer until it is resolved"
                    ),
                    recoverable=True,
                    suggested_action=(
                        f"resolve the in-progress rebase in {base_worktree} "
                        "(`gh stack sync`, or `git rebase --continue`/`--abort`) "
                        f"before adding '{input_data.branch}' as a new layer"
                    ),
                    data={
                        "base": base,
                        "base_protected": base_protected,
                        "base_merged": base_merged,
                        "gh_stack_tracked": True,
                        "stack_worktree_path": str(base_worktree),
                        "rebase_in_progress": True,
                    },
                    transcript=transcript,
                ),
            )
        return ProductDecision(
            product="C",
            reason="dependent base with tracked stack",
            stack_worktree_path=base_worktree,
            base=base,
            trunk=trunk,
        )

    # No stack to join: a new 2-layer stack is a bigger operation than create
    # handles - refuse and route toward it explicitly.
    suggested_stack_path = worktree_base_for_suggestion / _slugify_branch(base)
    suggested_action = (
        f"base '{base}' is unmerged and carries no gh-stack tracking - creating "
        f"'{input_data.branch}' here needs a new 2-layer stack: create a worktree "
        f"at {suggested_stack_path} on '{base}' and run `gh stack init --base "
        f"{trunk_display} {base} {input_data.branch}`; use the managing-gh-stacks "
        "skill (sc-gh-stack) for the full workflow"
    )
    transcript.step_failed(
        step="resolve_product",
        error=f"base '{base}' is unmerged with no gh-stack tracking to join",
    )
    return ProductDecision(
        product=None,
        reason="no_stack_to_join",
        refusal=Envelope.error_response(
            code=ErrorCodes.CREATE_NEEDS_STACK,
            message=(
                f"Base branch '{base}' is neither protected nor merged into trunk, "
                "and carries no gh-stack tracking to join as a layer - a new "
                "2-layer stack is required"
            ),
            recoverable=True,
            suggested_action=suggested_action,
            data={
                "base": base,
                "base_protected": base_protected,
                "base_merged": base_merged,
                "gh_stack_tracked": False,
                "suggested_worktree_path": str(suggested_stack_path),
            },
            transcript=transcript,
        ),
    )


# =============================================================================
# Product B: new stack (same path as A, plus rerere + gh stack init)
# =============================================================================


def create_stacked_worktree(
    input_data: CreateInput,
    repo_root: Path,
    repo_name: str,
    worktree_base: Path,
    tracking_path: Optional[Path],
    transcript: Transcript,
) -> Envelope:
    """Create product B: a new stack, branched off `stack_root` at the SAME
    path a flat worktree would use (no `stack/` prefix anywhere), plus
    `git config rerere.enabled true` and `gh stack init` in the new worktree.

    Called once the mandatory stack prerequisites have already been verified
    and the dependency/policy resolution has determined the base is
    independent and `always_stack` routes it to a new stack. A failed
    `gh stack init` does not roll back the worktree - creation still
    succeeds, with the failure surfaced via `data.stack_init`.
    """
    stack_root_setting = get_stack_root_setting(repo_root)
    stack_root = resolve_stack_root(repo_root, stack_root_setting)

    stack_root_exists_local = check_branch_exists_local(stack_root, cwd=repo_root)
    stack_root_exists_remote = check_branch_exists_remote(stack_root, cwd=repo_root)
    if not stack_root_exists_local and not stack_root_exists_remote:
        transcript.step_failed(
            step="resolve stack_root",
            error=f"stack_root branch '{stack_root}' not found locally or remotely",
        )
        return Envelope.error_response(
            code=ErrorCodes.BRANCH_NOT_FOUND,
            message=f"stack_root branch '{stack_root}' not found",
            recoverable=True,
            suggested_action=(
                "Configure git.stack_root in .sc/shared-settings.yaml to an "
                "existing branch, or create the branch"
            ),
            data={"stack_root": stack_root},
            transcript=transcript,
        )

    transcript.step_ok(
        step="resolve stack_root",
        message=(
            f"stack_root={stack_root} local={stack_root_exists_local} "
            f"remote={stack_root_exists_remote}"
        ),
    )

    if input_data.base != stack_root:
        transcript.step_ok(
            step="requested_base",
            message=(
                f"requested base '{input_data.base}' differs from stack_root "
                f"'{stack_root}' - new stack branches off stack_root"
            ),
        )

    # SAME path a flat worktree would use - no stack/ prefix anywhere.
    worktree_path = worktree_base / input_data.branch

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

    branch_local_result = run_git(["branch", "--list", input_data.branch], cwd=repo_root, check=False)
    branch_exists_local = bool(branch_local_result.stdout.strip())
    branch_remote_result = run_git(
        ["branch", "-r", "--list", f"origin/{input_data.branch}"], cwd=repo_root, check=False
    )
    branch_exists_remote = bool(branch_remote_result.stdout.strip())

    transcript.step_ok(
        step=f"git branch --list {input_data.branch}",
        message=f"local={branch_exists_local} remote={branch_exists_remote}",
    )

    if branch_exists_local:
        git_cmd = f"git worktree add {worktree_path} {input_data.branch}"
        with transcript.timed_step(git_cmd) as t:
            run_git(["worktree", "add", str(worktree_path), input_data.branch], cwd=repo_root)
            t.message = f"Preparing stacked worktree ({worktree_path})"
        needs_new_branch = False
    elif branch_exists_remote:
        if not create_tracking_branch(input_data.branch, cwd=repo_root):
            transcript.step_ok(
                step="tracking branch fallback",
                message="using git worktree add directly",
            )
        git_cmd = f"git worktree add {worktree_path} {input_data.branch}"
        with transcript.timed_step(git_cmd) as t:
            run_git(["worktree", "add", str(worktree_path), input_data.branch], cwd=repo_root)
            t.message = f"Preparing stacked worktree ({worktree_path})"
        needs_new_branch = False
    else:
        base_ref = stack_root if stack_root_exists_local else f"origin/{stack_root}"
        git_cmd = f"git worktree add -b {input_data.branch} {worktree_path} {base_ref}"
        with transcript.timed_step(git_cmd) as t:
            run_git(
                ["worktree", "add", "-b", input_data.branch, str(worktree_path), base_ref],
                cwd=repo_root,
            )
            t.message = f"Preparing stacked worktree ({worktree_path})"
        needs_new_branch = True

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

    # Enable rerere in the new stacked worktree - repeated rebases are the norm.
    rerere_result = run_git(["config", "rerere.enabled", "true"], cwd=worktree_path, check=False)
    transcript.step_ok(
        step="git config rerere.enabled true",
        message="ok" if rerere_result.returncode == 0 else (rerere_result.stderr or "failed"),
    )

    # Adopt the new branch into gh-stack. `init` can prompt on a TTY, so
    # stdin=DEVNULL prevents blocking. Failure here is recoverable: the
    # worktree itself was created successfully, so we do NOT roll it back.
    stack_init_step = f"gh stack init --base {stack_root} {input_data.branch}"
    try:
        stack_init_result = subprocess.run(
            ["gh", "stack", "init", "--base", stack_root, input_data.branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
    except OSError as exc:
        transcript.step_failed(step=stack_init_step, error=str(exc))
        stack_init_data: Dict[str, Any] = {
            "ok": False,
            "stderr": str(exc),
            "next_step": (
                f"run gh stack init --base {stack_root} {input_data.branch} in the worktree"
            ),
        }
    else:
        if stack_init_result.returncode == 0:
            transcript.step_ok(step=stack_init_step, message="ok")
            stack_init_data = {"ok": True}
        else:
            error_output = stack_init_result.stderr or stack_init_result.stdout
            transcript.step_failed(step=stack_init_step, error=error_output)
            stack_init_data = {
                "ok": False,
                "stderr": error_output,
                "next_step": (
                    f"run gh stack init --base {stack_root} {input_data.branch} in the worktree"
                ),
            }

    stack_shape = f"({stack_root}) <- {input_data.branch}"

    now = datetime.now(timezone.utc).isoformat()
    remote_exists = check_remote_branch_exists(input_data.branch, cwd=repo_root)
    tracking_entry = TrackingEntry(
        branch=input_data.branch,
        path=str(worktree_path),
        base=stack_root,
        purpose=input_data.purpose,
        owner=input_data.owner,
        created=now,
        status="active",
        last_checked=now,
        notes=f"stack: {stack_shape}",
        remote_exists=remote_exists,
        local_worktree=True,
        remote_ahead=0,
    )

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

    data = {
        "action": "create",
        "branch": input_data.branch,
        "base": stack_root,
        "path": str(worktree_path),
        "repo_name": repo_name,
        "status": "clean",
        "branch_created": needs_new_branch,
        "tracking_entry": tracking_entry.model_dump(),
        "tracking_updated": tracking_updated,
        "stacked": True,
        "product": "new_stack",
        "stack_root": stack_root,
        "stack_shape": stack_shape,
        "stack_init": stack_init_data,
    }
    if input_data.base != stack_root:
        data["requested_base"] = input_data.base

    return Envelope.success_response(data=data, transcript=transcript)


# =============================================================================
# Product C: stack layer (no new worktree)
# =============================================================================


def create_stack_layer(
    input_data: CreateInput,
    repo_root: Path,
    repo_name: str,
    stack_worktree_path: Path,
    base: str,
    tracking_path: Optional[Path],
    transcript: Transcript,
) -> Envelope:
    """Create product C: add `branch` as a new layer in the base's existing
    stack worktree. NO new worktree is created.

    `data.path` is the STACK worktree (not a new directory) - legacy callers
    that read `path` from output keep working unmodified against the layer.
    """
    branch = input_data.branch

    git_cmd = f"git -C {stack_worktree_path} checkout -b {branch} {base}"
    with transcript.timed_step(git_cmd) as t:
        run_git(["checkout", "-b", branch, base], cwd=stack_worktree_path)
        t.message = f"Adding layer to stack worktree ({stack_worktree_path})"

    # Adopt the new branch into the stack. `add` can prompt on a TTY, so
    # stdin=DEVNULL prevents blocking. Failure here is recoverable: the
    # branch/checkout already succeeded, so we do NOT roll it back.
    stack_add_step = f"gh stack add {branch}"
    try:
        stack_add_result = subprocess.run(
            ["gh", "stack", "add", branch],
            cwd=stack_worktree_path,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
    except OSError as exc:
        transcript.step_failed(step=stack_add_step, error=str(exc))
        stack_add_data: Dict[str, Any] = {
            "ok": False,
            "stderr": str(exc),
            "next_step": f"run gh stack add {branch} in {stack_worktree_path}",
        }
    else:
        if stack_add_result.returncode == 0:
            transcript.step_ok(step=stack_add_step, message="ok")
            stack_add_data = {"ok": True}
        else:
            error_output = stack_add_result.stderr or stack_add_result.stdout
            transcript.step_failed(step=stack_add_step, error=error_output)
            stack_add_data = {
                "ok": False,
                "stderr": error_output,
                "next_step": f"run gh stack add {branch} in {stack_worktree_path}",
            }

    stack_shape = f"({base}) <- {branch}"

    now = datetime.now(timezone.utc).isoformat()
    remote_exists = check_remote_branch_exists(branch, cwd=repo_root)
    tracking_entry = TrackingEntry(
        branch=branch,
        path=str(stack_worktree_path),
        base=base,
        purpose=input_data.purpose,
        owner=input_data.owner,
        created=now,
        status="active",
        last_checked=now,
        notes=f"stack layer: {stack_shape}",
        remote_exists=remote_exists,
        local_worktree=True,
        remote_ahead=0,
    )

    tracking_updated = False
    if tracking_path:
        add_tracking_entry(tracking_path, tracking_entry)
        tracking_updated = True
        transcript.step_ok(
            step=f"append {tracking_path.name}",
            message=branch,
        )
    else:
        transcript.step_skipped(step="update_tracking", message="disabled")

    return Envelope.success_response(
        data={
            "action": "create",
            "branch": branch,
            "base": base,
            "path": str(stack_worktree_path),
            "repo_name": repo_name,
            "status": "clean",
            "branch_created": True,
            "tracking_entry": tracking_entry.model_dump(),
            "tracking_updated": tracking_updated,
            "stacked": True,
            "product": "layer",
            "stack_shape": stack_shape,
            "stack_add": stack_add_data,
        },
        transcript=transcript,
    )


# =============================================================================
# Main Logic
# =============================================================================


def create_worktree_main(input_data: CreateInput) -> Envelope:
    """Main worktree creation logic - the factory entry point.

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

        # -------------------------------------------------------------------
        # Factory decision model, stages 1-2: Intent, then the stack-activity
        # probe. `flat: true` short-circuits to product A with NOTHING else
        # evaluated (stage 1). Otherwise probe cheaply for stack activity
        # (stage 2); a stack-inactive repo also resolves to product A
        # immediately, with the legacy flat-create path left structurally
        # untouched below (no settings beyond the one always_stack read, no
        # transcript entries about stacks).
        # -------------------------------------------------------------------
        if input_data.flat:
            stack_active = False
            always_stack = False
        else:
            stack_active, always_stack = _probe_stack_active(repo_root)

        # ---------------------------------------------------------------
        # Stage 3: mandatory stack-prerequisite gate. Only runs when the
        # repo is stack-active and intent hasn't already resolved to A.
        # This is the ONLY refusal that fires before product resolution,
        # and it runs before any mutation, including `git fetch`.
        # ---------------------------------------------------------------
        if stack_active:
            prereqs = check_stack_prerequisites(repo_root)
            transcript.step_ok(
                step="check_stack_prerequisites",
                message=(
                    f"gh_cli={prereqs['gh_cli']} "
                    f"gh_stack_extension={prereqs['gh_stack_extension']} "
                    f"sc_gh_stack_skill={prereqs['sc_gh_stack_skill']}"
                ),
            )
            if not prereqs["ok"]:
                missing_actions: List[str] = []
                if not prereqs["gh_cli"]:
                    missing_actions.append("install GitHub CLI (https://cli.github.com)")
                if not prereqs["gh_stack_extension"]:
                    missing_actions.append("gh extension install github/gh-stack")
                if not prereqs["sc_gh_stack_skill"]:
                    missing_actions.append(
                        "/plugin marketplace add randlee/synaptic-canvas && "
                        "/plugin install sc-gh-stack@synaptic-canvas"
                    )
                transcript.step_failed(
                    step="check_stack_prerequisites",
                    error="repo is stack-active but required stack tooling is missing",
                )
                return Envelope.error_response(
                    code=ErrorCodes.CREATE_STACK_PREREQS_MISSING,
                    message=(
                        "This repo is stack-active (git.always_stack, or an "
                        "existing gh-stack-tracked worktree) but the mandatory "
                        "gh-stack prerequisites are not all present"
                    ),
                    recoverable=True,
                    suggested_action="; ".join(missing_actions),
                    data={**prereqs, "always_stack": always_stack},
                    transcript=transcript,
                )
        # else: repo is not stack-active (or flat=true short-circuited to A) -
        # NOTHING about stacking is evaluated or logged here. This is the
        # positive-signal rule: the legacy flat-create path stays structurally
        # untouched, with a transcript byte-identical to the pre-guard package.

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

        # ---------------------------------------------------------------
        # Stages 4-5: Dependency then Policy. Only evaluated when the repo
        # is stack-active and flat hasn't already resolved to A - this is
        # the positive-signal rule: every indeterminate input resolves to A.
        # ---------------------------------------------------------------
        product = "A"
        decision: Optional[ProductDecision] = None
        if not input_data.flat and stack_active:
            decision = resolve_product(
                input_data=input_data,
                repo_root=repo_root,
                base_exists_local=base_exists_local,
                always_stack=always_stack,
                transcript=transcript,
            )
            if decision.product is None:
                return decision.refusal
            product = decision.product

        if product == "B":
            return create_stacked_worktree(
                input_data=input_data,
                repo_root=repo_root,
                repo_name=repo_name,
                worktree_base=worktree_base,
                tracking_path=tracking_path,
                transcript=transcript,
            )

        if product == "C":
            assert decision is not None and decision.stack_worktree_path is not None
            return create_stack_layer(
                input_data=input_data,
                repo_root=repo_root,
                repo_name=repo_name,
                stack_worktree_path=decision.stack_worktree_path,
                base=decision.base or input_data.base,
                tracking_path=tracking_path,
                transcript=transcript,
            )

        # -----------------------------------------------------------------
        # Product A: the legacy flat worktree, structurally unchanged.
        # -----------------------------------------------------------------

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
