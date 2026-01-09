#!/usr/bin/env python3
"""
Worktree validation (v0.7.1).
- Input: JSON { "worktrees": [ { "path": "...", "branch": "main/1-1" } ] }
- Output: fenced JSON with per-worktree status (exists, clean)
"""
from __future__ import annotations

import json
import os
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


def _validate_worktree(entry: Dict[str, Any]) -> Dict[str, Any]:
    path = entry.get("path")
    branch = entry.get("branch")
    if not path:
        return {"branch": branch, "path": path, "success": False, "error": "MISSING_PATH"}
    exists = os.path.isdir(path)
    clean = _git_status_clean(path) if exists else False
    return {
        "branch": branch,
        "path": path,
        "success": exists and clean,
        "exists": exists,
        "clean": clean,
        "error": None if exists and clean else ("NOT_FOUND" if not exists else "DIRTY"),
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

    worktrees = payload.get("worktrees") or []
    results = [_validate_worktree(wt) for wt in worktrees]
    all_success = all(r.get("success") for r in results) if results else False
    sys.stdout.write(
        json.dumps(
            {
                "success": all_success,
                "data": {"results": results},
                "error": None if all_success else {"code": "WORKTREE.VALIDATION_FAILED", "message": "One or more worktrees failed"},
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
