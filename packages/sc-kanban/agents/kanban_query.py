#!/usr/bin/env python3
"""
kanban-query agent implementation.
- Loads board config
- Enforces provider (checklist advisory)
- Returns cards from backlog/board/done with optional filters
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

from sc_cli.board_config import BoardConfigError, load_board_config
from sc_kanban.board import load_cards_by_status


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

    status_filter = params.get("status")
    sprint_filter = params.get("sprint_id")
    worktree_filter = params.get("worktree")
    config_path = params.get("config_path", ".project/board.config.yaml")
    base_dir = Path(params.get("base_dir", "."))

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
                    "Invoke checklist-agent/query-update",
                )
            )
        )
        return 0

    cards = load_cards_by_status(base_dir, cfg)
    all_cards = cards["backlog"] + cards["board"] + cards["done"]

    def _matches(card: Dict[str, Any]) -> bool:
        if status_filter and card.get("status") != status_filter:
            return False
        if sprint_filter and card.get("sprint_id") != sprint_filter:
            return False
        if worktree_filter and card.get("worktree") != worktree_filter:
            return False
        return True

    filtered = [c for c in all_cards if _matches(c)]

    print(
        json.dumps(
            {
                "success": True,
                "canceled": False,
                "aborted_by": None,
                "data": {"cards": filtered},
                "error": None,
                "metadata": {"tool_calls": [], "duration_ms": 0},
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
