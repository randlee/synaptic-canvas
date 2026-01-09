#!/usr/bin/env python3
"""
kanban-transition agent implementation (stubbed gates).
- Loads board config
- Enforces provider (kanban vs checklist advisory)
- Moves card across backlog/board/done with scrubbing
- TODO: add gate execution (worktree/PR/git) before finalizing transition
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict

from sc_cli.board_config import BoardConfigError, load_board_config
from sc_kanban.board import load_cards_by_status, transition_card


def _error(code: str, message: str, recoverable: bool, suggested_action: str) -> Dict[str, Any]:
    return {
        "success": False,
        "canceled": False,
        "aborted_by": None,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
            "suggested_action": suggested_action,
        },
        "metadata": {"tool_calls": [], "duration_ms": 0},
    }


def main() -> int:
    try:
        params = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps(_error("INPUT.INVALID_JSON", "Could not parse input JSON", False, "Fix input and retry")))
        return 1

    selector = params.get("card_selector")
    target_status = params.get("target_status")
    config_path = params.get("config_path", ".project/board.config.yaml")
    base_dir = Path(params.get("base_dir", "."))

    if not selector or not target_status:
        print(
            json.dumps(
                _error(
                    "INPUT.MISSING",
                    "card_selector and target_status are required",
                    False,
                    "Provide card_selector and target_status",
                )
            )
        )
        return 1

    # Optional gates payload (for v0.7.1+)
    gates_payload = params.get("gates")

    try:
        cfg = load_board_config(config_path)
    except BoardConfigError as exc:
        print(json.dumps(_error("CONFIG.INVALID", str(exc), False, "Fix .project/board.config.yaml")))
        return 1

    if cfg.board.provider == "checklist":
        print(
            json.dumps(
                _error(
                    "PROVIDER.CHECKLIST",
                    "Board config provider=checklist; call checklist agent",
                    True,
                    "Invoke checklist-agent/query-update with same card selector",
                )
            )
        )
        return 0

    # Basic gates (v0.7.0): require pr_url for review/done
    cards = load_cards_by_status(base_dir, cfg)
    all_cards = cards["backlog"] + cards["board"]
    source_card = next((c for c in all_cards if c.get("worktree") == selector or c.get("sprint_id") == selector), None)
    if source_card is None:
        print(json.dumps(_error("CARD.NOT_FOUND", f"Card '{selector}' not found", False, "Create or select an existing card")))
        return 1
    if target_status in {"review", "done"}:
        if not source_card.get("pr_url"):
            print(
                json.dumps(
                    _error(
                        "GATE.PR_REQUIRED",
                        "pr_url is required before moving to review/done",
                        True,
                        "Set pr_url on the card then retry",
                    )
                )
            )
            return 1
    # WIP check
    wip_limit = (cfg.board.wip.per_column or {}).get(target_status)
    current_count = sum(1 for c in cards["board"] if c.get("status") == target_status)
    already_in_target = source_card.get("status") == target_status
    if wip_limit is not None and wip_limit > 0 and not already_in_target and current_count >= wip_limit:
        print(
            json.dumps(
                _error(
                    "GATE.WIP",
                    f"WIP limit reached for {target_status}",
                    True,
                    "Finish or move other cards before starting a new one",
                )
            )
        )
        return 1

    # Build default gates payload if not provided (only for review/done)
    if not gates_payload and cfg.board.provider == "kanban" and target_status in {"review", "done"}:
        worktree_path = source_card.get("worktree")
        branch = source_card.get("worktree")  # worktree includes branch prefix
        prs = []
        worktrees = []
        if worktree_path and Path(worktree_path).is_dir():
            worktrees.append({"path": worktree_path, "branch": branch})
        if source_card.get("pr_url") and worktree_path and Path(worktree_path).is_dir():
            prs.append({"url": source_card.get("pr_url"), "branch": branch, "worktree_path": worktree_path})
        gates_payload = {"worktrees": worktrees, "prs": prs}

    # Run gates if provided (v0.7.1)
    failed_gates = []
    if gates_payload:
        has_inputs = bool(gates_payload.get("worktrees")) or bool(gates_payload.get("prs"))
        if has_inputs:
            gate_result = _run_gates(gates_payload)
            if not gate_result.get("success"):
                for r in gate_result.get("data", {}).get("results", []):
                    if not r.get("success"):
                        failed_gates.append(
                            {
                                "rule": r.get("error") or "GATE.FAIL",
                                "field": r.get("branch") or r.get("url"),
                                "location": r.get("path") or r.get("worktree_path"),
                                "code": r.get("error") or "GATE.FAIL",
                                "detail": r,
                                "suggested_action": "Resolve gate failure and retry",
                                "recoverable": True,
                            }
                        )
        if failed_gates:
            print(
                json.dumps(
                    {
                        "success": False,
                        "canceled": False,
                        "aborted_by": None,
                        "data": None,
                        "error": {
                            "code": "GATE.FAILURES",
                            "message": "One or more gates failed",
                            "recoverable": True,
                            "suggested_action": "Resolve gate failures and retry",
                        },
                        "metadata": {"failed_gates": failed_gates},
                    }
                )
            )
            return 1

    try:
        updated = transition_card(cfg, selector=selector, target_status=target_status, base_dir=base_dir)
    except KeyError as exc:
        print(
            json.dumps(
                _error(
                    "CARD.NOT_FOUND",
                    str(exc),
                    False,
                    "Ensure card exists in backlog/board for the selector and retry",
                )
            )
        )
        return 1
    except Exception as exc:  # pragma: no cover - unexpected
        print(json.dumps(_error("UNEXPECTED", str(exc), False, "Inspect logs and retry")))
        return 1

    print(
        json.dumps(
            {
                "success": True,
                "canceled": False,
                "aborted_by": None,
                "data": {"card": updated},
                "error": None,
                "metadata": {"tool_calls": [], "duration_ms": 0},
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
def _run_gates(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke run_gates.main with in-memory stdin/stdout."""
    import sys as _sys
    from io import StringIO

    run_gates_path = Path(__file__).resolve().parent.parent / "scripts" / "run_gates.py"
    spec = importlib.util.spec_from_file_location("run_gates", run_gates_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    run_gates_main = getattr(mod, "main")

    stdin_backup = _sys.stdin
    stdout_backup = _sys.stdout
    _sys.stdin = StringIO(json.dumps(payload))
    out = StringIO()
    _sys.stdout = out
    try:
        run_gates_main()
    finally:
        _sys.stdin = stdin_backup
        _sys.stdout = stdout_backup
    try:
        return json.loads(out.getvalue() or "{}")
    except Exception:
        return {"success": False, "error": {"code": "GATES.INVALID_OUTPUT", "message": "Failed to parse gate output"}}
