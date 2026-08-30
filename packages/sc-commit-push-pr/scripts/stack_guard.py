#!/usr/bin/env python3
"""gh-stack awareness for sc-commit-push-pr.

sc-commit-push-pr is the general-purpose commit/push/PR package. The
sc-gh-stack package (managing-gh-stacks skill, `gh stack` CLI extension) is
the sole authority for stacked-branch operations: rebasing layers, syncing a
stack, and submitting/pushing a layer's PR. This module encodes the boundary
between the two:

1. **Hard, unconditional prerequisite.** sc-commit-push-pr is the critical
   junction where a stack-unaware commit/pull/merge/push or PR creation can
   corrupt gh-stack linearity, so the full gh-stack toolchain (the `gh` CLI,
   the `gh-stack` extension, and the managing-gh-stacks skill) is now
   required for *every* invocation of this package -- regardless of whether
   the current branch happens to be a stack layer, and regardless of
   provider (GitHub or Azure DevOps). A mixed-provider org gets one uniform
   prerequisite set. See `check_stack_prerequisites()`.

2. **State-based stack-layer detection.** `check_gh_stack_marker()` detects
   whether the *current* worktree is a layer of a gh stack, the same way
   `gh stack` itself does: a `gh-stack` marker file under the worktree's
   private git-dir. Detection is positive-signal and fails closed -- any
   error probing git resolves to "not a stack worktree" so a probe failure
   can never silently unlock a merge/push that should have been refused.

This module intentionally duplicates the small detection primitives that
also exist in packages/sc-git-worktree/scripts/worktree_shared.py
(`check_gh_stack_tracked`, `check_gh_cli_available`, etc.) rather than
importing them: sc-commit-push-pr must not import from another package. The
duplication is small and deliberate.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

PathLike = Union[str, "Path"]


# =============================================================================
# Hard prerequisite gate (unconditional)
# =============================================================================


def _home_dir() -> Path:
    return Path.home()


def get_repo_root(cwd: Optional[PathLike] = None) -> Path:
    """Best-effort repo root resolution.

    Falls back to `cwd` (or the process cwd) on any error so callers never
    have to handle an exception just to run the prerequisite gate.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except Exception:
        return Path(cwd) if cwd is not None else Path.cwd()


def _run_gh(args: List[str], cwd: Optional[PathLike] = None) -> Optional[subprocess.CompletedProcess]:
    """Run a `gh` command, fail closed (return None) if gh is unavailable."""
    try:
        return subprocess.run(
            ["gh", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return None


def check_gh_cli_available() -> bool:
    """True if the `gh` CLI is installed and runnable."""
    result = _run_gh(["--version"])
    return result is not None and result.returncode == 0


def check_gh_stack_extension_installed() -> bool:
    """True if the `gh-stack` extension is registered with `gh extension list`."""
    result = _run_gh(["extension", "list"])
    if result is None or result.returncode != 0:
        return False
    return "gh-stack" in (result.stdout or "")


def check_sc_gh_stack_skill(repo_root: Optional[PathLike] = None) -> bool:
    """True if the managing-gh-stacks skill is installed under the repo or user home.

    Checks the canonical path first, then falls back to a bounded, pure-Python
    walk (no shelling out to `find`) of `<root>/.claude` for any
    `*/managing-gh-stacks/SKILL.md`.
    """
    home = _home_dir()

    direct_candidates = []
    if repo_root is not None:
        direct_candidates.append(
            Path(repo_root) / ".claude" / "skills" / "managing-gh-stacks" / "SKILL.md"
        )
    direct_candidates.append(home / ".claude" / "skills" / "managing-gh-stacks" / "SKILL.md")
    for candidate in direct_candidates:
        try:
            if candidate.is_file():
                return True
        except OSError:
            continue

    search_roots = []
    if repo_root is not None:
        search_roots.append(Path(repo_root) / ".claude")
    search_roots.append(home / ".claude")

    max_depth = 6
    for root in search_roots:
        try:
            if not root.exists():
                continue
            base_depth = len(root.resolve().parts)
            for match in root.rglob("SKILL.md"):
                try:
                    if match.parent.name != "managing-gh-stacks":
                        continue
                    if len(match.resolve().parts) - base_depth > max_depth:
                        continue
                    return True
                except OSError:
                    continue
        except (OSError, RecursionError):
            continue

    return False


def check_stack_prerequisites(repo_root: Optional[PathLike] = None) -> Dict[str, bool]:
    """Unconditional hard prerequisite gate for sc-commit-push-pr.

    Fail closed on every sub-check: any error probing gh or the filesystem
    resolves to False. Callers must refuse to proceed (commit/pull/merge/
    push/PR-create) when `ok` is False, on every branch -- not just gh-stack
    layers -- and for every provider.
    """
    gh_cli = check_gh_cli_available()
    gh_stack_extension = check_gh_stack_extension_installed()
    sc_gh_stack_skill = check_sc_gh_stack_skill(repo_root)
    return {
        "gh_cli": gh_cli,
        "gh_stack_extension": gh_stack_extension,
        "sc_gh_stack_skill": sc_gh_stack_skill,
        "ok": gh_cli and gh_stack_extension and sc_gh_stack_skill,
    }


def missing_prereq_actions(prereqs: Dict[str, bool]) -> List[str]:
    """Build the exact install/setup steps for whichever prerequisites are missing."""
    actions: List[str] = []
    if not prereqs.get("gh_cli"):
        actions.append("install GitHub CLI (https://cli.github.com)")
    if not prereqs.get("gh_stack_extension"):
        actions.append("gh extension install github/gh-stack")
    if not prereqs.get("sc_gh_stack_skill"):
        actions.append(
            "/plugin marketplace add randlee/synaptic-canvas && "
            "/plugin install sc-gh-stack@synaptic-canvas"
        )
    return actions


# =============================================================================
# Stack-layer detection (state-based, per-worktree)
# =============================================================================


def check_gh_stack_marker(path: PathLike) -> bool:
    """Detect whether `path`'s worktree carries gh-stack tracking state.

    Mirrors `check_gh_stack_tracked()` in
    packages/sc-git-worktree/scripts/worktree_shared.py: gh-stack keeps
    per-worktree stack state in a `gh-stack` marker under the worktree's
    git-dir (a linked worktree's private gitdir, not the shared repo
    `.git`). Detection is repository state, not configuration.

    Fail closed: any error probing git resolves to False, so callers must
    not assume a branch is a plain (non-stack) branch when detection is
    merely inconclusive -- they should treat False as "not confirmed to be
    a stack layer" only in the sense that no special handling applies.

    Args:
        path: Worktree working directory to probe.

    Returns:
        True if a `gh-stack` marker exists under the worktree's git-dir.
    """
    # A prunable/hand-deleted worktree directory makes subprocess raise
    # before git runs (cwd missing) -- the fail-closed contract covers that.
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    if result.returncode != 0:
        return False
    git_dir_raw = result.stdout.strip()
    if not git_dir_raw:
        return False
    git_dir = Path(git_dir_raw)
    if not git_dir.is_absolute():
        git_dir = (Path(path) / git_dir).resolve()
    return (git_dir / "gh-stack").exists()


# =============================================================================
# Shared refusal text
# =============================================================================

STACK_USE_GH_STACK_SUGGESTED_ACTION = (
    "this branch is a layer of a gh stack (worktree carries gh-stack "
    "tracking); push and PR creation are owned by `gh stack submit "
    "--auto` -- use the managing-gh-stacks skill (package sc-gh-stack). "
    "Commit succeeded; nothing was pushed."
)

STACK_PREREQS_MISSING_MESSAGE = (
    "sc-commit-push-pr requires the gh-stack toolchain (gh CLI, gh-stack "
    "extension, managing-gh-stacks skill) to be installed before it will "
    "commit, pull, merge, push, or create PRs -- this package is the "
    "critical junction where a stack-unaware operation can corrupt gh "
    "stack linearity."
)
