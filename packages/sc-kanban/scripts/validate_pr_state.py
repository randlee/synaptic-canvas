#!/usr/bin/env python3
"""
PR validation (v0.7.1).
- Input: JSON { "prs": [ { "url": "...", "branch": "...", "worktree_path": "..." } ] }
- Output: fenced JSON with PR state, git clean/pushed status
"""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, Dict, List


def _run(cmd: List[str], cwd: str | None = None, timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)


def _git_status_clean(path: str) -> bool:
    try:
        result = _run(["git", "status", "--porcelain"], cwd=path)
        return result.returncode == 0 and result.stdout.strip() == ""
    except Exception:
        return False


def _git_pushed(path: str, branch: str) -> bool:
    try:
        local = _run(["git", "rev-parse", branch], cwd=path)
        remote = _run(["git", "ls-remote", "--heads", "origin", branch], cwd=path)
        if local.returncode != 0 or remote.returncode != 0:
            return False
        local_sha = local.stdout.strip()
        remote_sha = remote.stdout.strip().split()[0] if remote.stdout.strip() else ""
        return local_sha and remote_sha and local_sha == remote_sha
    except Exception:
        return False


def _gh_pr_state(url: str) -> str:
    try:
        result = _run(["gh", "pr", "view", url, "--json", "state"])
        if result.returncode != 0:
            return "UNKNOWN"
        data = json.loads(result.stdout)
        return data.get("state", "UNKNOWN")
    except Exception:
        return "UNKNOWN"


def _validate_pr(entry: Dict[str, Any]) -> Dict[str, Any]:
    url = entry.get("url")
    branch = entry.get("branch")
    worktree_path = entry.get("worktree_path")
    if not url or not branch or not worktree_path:
        return {"url": url, "branch": branch, "worktree_path": worktree_path, "success": False, "error": "MISSING_FIELDS"}
    state = _gh_pr_state(url)
    clean = _git_status_clean(worktree_path)
    pushed = _git_pushed(worktree_path, branch)
    success = state in {"OPEN", "MERGED"} and clean and pushed
    return {
        "url": url,
        "branch": branch,
        "worktree_path": worktree_path,
        "state": state,
        "clean": clean,
        "pushed": pushed,
        "success": success,
        "error": None if success else "PR.INVALID_STATE",
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.stdout.write(
            json.dumps(
                {
                    "success": False,
                    "error": {"code": "INPUT.INVALID_JSON", "message": "Cannot parse input"},
                }
            )
        )
        return 1

    prs = payload.get("prs") or []
    results = [_validate_pr(pr) for pr in prs]
    all_success = all(r.get("success") for r in results) if results else False
    sys.stdout.write(
        json.dumps(
            {
                "success": all_success,
                "data": {"results": results},
                "error": None if all_success else {"code": "PR.VALIDATION_FAILED", "message": "One or more PRs failed validation"},
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
