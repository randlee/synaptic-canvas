#!/usr/bin/env python3
"""Read-only environment gate for gh stack operations.

Usage: python3 gh_stack_preflight.py [--cwd PATH]

Emits a fenced JSON envelope. data.checks[] has one entry per check with
status "ok" | "fail" | "warn" and, for failures, the exact fix. Exit 0 when no
check failed, 1 otherwise. Nothing here modifies the repository.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gh_stack_shared as gs  # noqa: E402

INSTALL_DOC = "see references/installation-and-troubleshooting.md"


def _check(name: str, ok: bool, fix: str) -> Dict[str, Any]:
    return {"name": name, "status": "ok" if ok else "fail", "fix": None if ok else fix}


def _warn(name: str, note: str) -> Dict[str, Any]:
    return {"name": name, "status": "warn", "fix": note}


def run_checks(cwd: Optional[Path] = None) -> List[Dict[str, Any]]:
    """All checks, in order. Pure function of the environment; no side effects."""
    checks: List[Dict[str, Any]] = []

    checks.append(_check("gh_cli", gs.gh(["--version"], cwd=cwd).returncode == 0, INSTALL_DOC))
    ext = gs.gh(["extension", "list"], cwd=cwd)
    checks.append(_check("gh_stack_extension",
                         ext.returncode == 0 and "gh-stack" in ext.stdout,
                         "gh extension install github/gh-stack"))
    checks.append(_check("gh_auth", gs.gh(["auth", "status"], cwd=cwd).returncode == 0, "gh auth login"))

    checks.append(_check("rerere_enabled", gs.config_get("rerere.enabled", cwd=cwd) == "true",
                         "git config rerere.enabled true"))

    names = gs.remotes(cwd=cwd)
    if not names:
        checks.append(_check("remote", False, "git remote add origin <url>"))
    elif len(names) > 1 and not gs.config_get("remote.pushDefault", cwd=cwd):
        checks.append(_check("remote", False,
                             f"{len(names)} remotes and remote.pushDefault unset: git config remote.pushDefault origin"))
    else:
        checks.append(_check("remote", True, ""))

    checks.append(_check("working_tree_clean", gs.working_tree_clean(cwd=cwd),
                         "commit or stash before stack operations"))
    checks.append(_check("no_rebase_in_progress", not gs.rebase_in_progress(cwd=cwd),
                         "git rebase --continue after resolving (or git rebase --abort); "
                         "use gh stack rebase --continue if the rebase was started by gh stack"))

    checks.append(_warn("stacked_prs_enabled",
                        "no direct probe exists; `gh stack submit` exits 9 if the repository "
                        "does not have stacked PRs enabled — stop and tell the user"))
    return checks


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="gh stack preflight (read-only)")
    parser.add_argument("--cwd", type=Path, default=None, help="repository path (default: current dir)")
    args = parser.parse_args(argv)

    if not gs.in_git_repo(cwd=args.cwd):
        gs.emit(gs.envelope(False, None, gs.error_obj(
            "PREFLIGHT.NOT_A_REPO", "not inside a git repository", True, "cd into the repository")))
        return 1

    checks = run_checks(cwd=args.cwd)
    failed = [c for c in checks if c["status"] == "fail"]
    data = {"checks": checks, "failed": [c["name"] for c in failed]}
    if failed:
        gs.emit(gs.envelope(False, data, gs.error_obj(
            "PREFLIGHT.FAILED", f"{len(failed)} check(s) failed", True,
            "apply each check's fix, then re-run")))
        return 1
    gs.emit(gs.envelope(True, data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
