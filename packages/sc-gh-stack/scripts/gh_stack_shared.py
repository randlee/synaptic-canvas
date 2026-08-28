#!/usr/bin/env python3
"""Shared helpers for sc-gh-stack scripts.

Stdlib only. Provides subprocess wrappers for git/gh, ancestry and branch
queries, and the fenced-JSON response envelope used by every script.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

PR_NUMBER = re.compile(r"^[0-9]+$")


def run(cmd: Sequence[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a command, capturing output; never raises on non-zero exit."""
    return subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, check=False)


def git(args: Sequence[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return run(["git", *args], cwd=cwd)


def gh(args: Sequence[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return run(["gh", *args], cwd=cwd)


def git_ok(args: Sequence[str], cwd: Optional[Path] = None) -> bool:
    return git(args, cwd=cwd).returncode == 0


def git_out(args: Sequence[str], cwd: Optional[Path] = None) -> str:
    return git(args, cwd=cwd).stdout.strip()


# --- repository queries ----------------------------------------------------

def in_git_repo(cwd: Optional[Path] = None) -> bool:
    return git_ok(["rev-parse", "--is-inside-work-tree"], cwd=cwd)


def git_dir(cwd: Optional[Path] = None) -> Path:
    return Path(git_out(["rev-parse", "--git-dir"], cwd=cwd))


def config_get(key: str, cwd: Optional[Path] = None) -> str:
    return git_out(["config", "--get", key], cwd=cwd)


def remotes(cwd: Optional[Path] = None) -> List[str]:
    out = git_out(["remote"], cwd=cwd)
    return [r for r in out.splitlines() if r.strip()]


def resolve_remote(cwd: Optional[Path] = None) -> Optional[str]:
    """remote.pushDefault if set, else the first remote, else None."""
    push_default = config_get("remote.pushDefault", cwd=cwd)
    if push_default:
        return push_default
    names = remotes(cwd=cwd)
    return names[0] if names else None


def ref_exists(ref: str, cwd: Optional[Path] = None) -> bool:
    return git_ok(["show-ref", "--verify", "--quiet", ref], cwd=cwd)


def local_branch_exists(branch: str, cwd: Optional[Path] = None) -> bool:
    return ref_exists(f"refs/heads/{branch}", cwd=cwd)


def remote_branch_exists(remote: str, branch: str, cwd: Optional[Path] = None) -> bool:
    return ref_exists(f"refs/remotes/{remote}/{branch}", cwd=cwd)


def is_ancestor(ancestor: str, descendant: str, cwd: Optional[Path] = None) -> bool:
    return git_ok(["merge-base", "--is-ancestor", ancestor, descendant], cwd=cwd)


def working_tree_clean(cwd: Optional[Path] = None) -> bool:
    return git_out(["status", "--porcelain"], cwd=cwd) == ""


def rebase_in_progress(cwd: Optional[Path] = None) -> bool:
    d = git_dir(cwd=cwd)
    base = d if d.is_absolute() else (cwd or Path.cwd()) / d
    return (base / "rebase-merge").is_dir() or (base / "rebase-apply").is_dir()


def conflicted_files(cwd: Optional[Path] = None) -> List[str]:
    out = git_out(["diff", "--name-only", "--diff-filter=U"], cwd=cwd)
    return [f for f in out.splitlines() if f.strip()]


def resolve_pr_branch(pr_number: str, cwd: Optional[Path] = None) -> Optional[str]:
    """Head branch name for a PR number via gh, or None if it cannot be resolved."""
    result = gh(["pr", "view", pr_number, "--json", "headRefName", "-q", ".headRefName"], cwd=cwd)
    if result.returncode != 0:
        return None
    name = result.stdout.strip()
    return name or None


# --- response envelope -----------------------------------------------------

def error_obj(code: str, message: str, recoverable: bool, suggested_action: str) -> Dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "recoverable": recoverable,
        "suggested_action": suggested_action,
    }


def envelope(success: bool, data: Optional[Dict[str, Any]] = None,
             error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"success": success, "data": data, "error": None if success else error}


def emit(payload: Dict[str, Any]) -> None:
    """Print the envelope as fenced JSON (guidelines: skills parse fenced JSON only)."""
    print("```json")
    print(json.dumps(payload, indent=2))
    print("```")
