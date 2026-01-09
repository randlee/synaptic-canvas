#!/usr/bin/env python3
"""
Gate runner (v0.7.1).
- Input JSON: { "card": {...}, "worktrees": [...], "prs": [...] }
- Executes worktree and PR validations, aggregates results.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _run_subtool(main_func, payload: Dict[str, Any]) -> Dict[str, Any]:
    from io import StringIO
    import sys as _sys

    stdin_backup = _sys.stdin
    stdout_backup = _sys.stdout
    _sys.stdin = StringIO(json.dumps(payload))
    out = StringIO()
    _sys.stdout = out
    try:
        main_func()
    finally:
        _sys.stdin = stdin_backup
        _sys.stdout = stdout_backup
    try:
        return json.loads(out.getvalue() or "{}")
    except Exception:
        return {"success": False, "error": {"code": "SUBTASK.INVALID_JSON", "message": "Failed to parse subtask output"}}


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.stdout.write(json.dumps({"success": False, "error": {"code": "INPUT.INVALID_JSON", "message": "Cannot parse input"}}))
        return 1

    worktrees_payload = {"worktrees": payload.get("worktrees", [])}
    prs_payload = {"prs": payload.get("prs", [])}

    # dynamic load sub-tools to avoid import path issues
    base = Path(__file__).resolve().parent
    validate_worktrees_path = base / "validate_worktrees.py"
    validate_pr_state_path = base / "validate_pr_state.py"
    spec_wt = importlib.util.spec_from_file_location("validate_worktrees", validate_worktrees_path)
    mod_wt = importlib.util.module_from_spec(spec_wt)  # type: ignore
    assert spec_wt and spec_wt.loader
    spec_wt.loader.exec_module(mod_wt)  # type: ignore
    wt_main = getattr(mod_wt, "main")

    spec_pr = importlib.util.spec_from_file_location("validate_pr_state", validate_pr_state_path)
    mod_pr = importlib.util.module_from_spec(spec_pr)  # type: ignore
    assert spec_pr and spec_pr.loader
    spec_pr.loader.exec_module(mod_pr)  # type: ignore
    pr_main = getattr(mod_pr, "main")

    wt_result = _run_subtool(wt_main, worktrees_payload)
    pr_result = _run_subtool(pr_main, prs_payload)

    results: List[Dict[str, Any]] = []
    results.extend(wt_result.get("data", {}).get("results", []))
    results.extend(pr_result.get("data", {}).get("results", []))

    all_success = wt_result.get("success") and pr_result.get("success")
    sys.stdout.write(
        json.dumps(
            {
                "success": bool(all_success),
                "data": {"results": results},
                "error": None if all_success else {"code": "GATES.FAILED", "message": "One or more gates failed"},
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
