#!/usr/bin/env python3
"""
kanban-card agent (create/update) for kanban provider.
- Creates lean backlog entries or rich board entries.
- Updates existing cards across backlog/board.
- Provider=checklist returns advisory error.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from sc_cli.board_config import BoardConfigError, load_board_config
from sc_kanban.board import _card_id, _load_json, _write_json


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


def _find_and_update(cards: List[Dict[str, Any]], selector: str, patch: Dict[str, Any]) -> bool:
    for idx, card in enumerate(cards):
        if _card_id(card) == selector:
            merged = card.copy()
            merged.update(patch)
            cards[idx] = merged
            return True
    return False


def main() -> int:
    try:
        params = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps(_error("INPUT.INVALID_JSON", "Could not parse input JSON", False, "Fix input and retry")))
        return 1

    action = params.get("action", "create")
    card = params.get("card") or {}
    target_status = params.get("target_status", "backlog")
    selector = card.get("worktree") or card.get("sprint_id")
    config_path = params.get("config_path", ".project/board.config.yaml")
    base_dir = Path(params.get("base_dir", "."))

    if not selector:
        print(json.dumps(_error("INPUT.MISSING", "card.worktree or card.sprint_id is required", False, "Provide selector fields")))
        return 1

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
                    "Use checklist-agent for checklist provider",
                )
            )
        )
        return 0

    backlog_path = (base_dir / cfg.board.backlog_path).resolve()
    board_path = (base_dir / cfg.board.board_path).resolve()

    backlog_cards = _load_json(backlog_path)
    board_cards = _load_json(board_path)

    if action == "create":
        card["status"] = target_status
        if target_status == "backlog":
            # ensure not duplicated in board
            backlog_cards = [c for c in backlog_cards if _card_id(c) != selector]
            backlog_cards.append(card)
        else:
            board_cards = [c for c in board_cards if _card_id(c) != selector]
            backlog_cards = [c for c in backlog_cards if _card_id(c) != selector]
            board_cards.append(card)
    elif action == "update":
        updated = _find_and_update(backlog_cards, selector, card)
        if not updated:
            updated = _find_and_update(board_cards, selector, card)
        if not updated:
            print(json.dumps(_error("CARD.NOT_FOUND", f"Card '{selector}' not found", True, "Create the card then update")))
            return 1
    else:
        print(json.dumps(_error("INPUT.UNSUPPORTED_ACTION", f"Unsupported action {action}", False, "Use create or update")))
        return 1

    _write_json(backlog_path, backlog_cards)
    _write_json(board_path, board_cards)

    print(
        json.dumps(
            {
                "success": True,
                "canceled": False,
                "aborted_by": None,
                "data": {"card": card},
                "error": None,
                "metadata": {"tool_calls": [], "duration_ms": 0},
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
