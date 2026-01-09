#!/usr/bin/env python3
"""
Minimal board file handling for sc-kanban v0.7.0.

Responsibilities:
- Load board config (shared with sc-project-manager).
- Move cards between backlog.json, board.json, done.json with optional scrubbing.
- Enforce simple constraints (unique card ids, status assignment).

Notes:
- This does not run external gates (PR merged, worktree cleanup); those belong to kanban-transition agent.
- Card identifiers: prefer worktree; fall back to sprint_id.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sc_cli.board_config import BoardConfig, BoardConfigError, load_board_config

Status = str

# Fields to retain when scrubbing rich cards into done.json
DONE_FIELDS = {"sprint_id", "title", "pr_url", "completed_at", "actual_cycles"}


def _load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    data = json.loads(text)
    if isinstance(data, list):
        return data
    raise ValueError(f"Expected list in {path}, got {type(data).__name__}")


def _write_json(path: Path, data: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _card_id(card: Dict[str, Any]) -> Optional[str]:
    return card.get("worktree") or card.get("sprint_id")


def scrub_card(card: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return a lean card for done.json."""
    ts = (now or datetime.now(timezone.utc)).isoformat()
    base = {k: v for k, v in card.items() if k in DONE_FIELDS}
    if "completed_at" not in base:
        base["completed_at"] = ts
    if "actual_cycles" not in base:
        base["actual_cycles"] = card.get("actual_cycles", 0)
    return base


def _find_card(cards: List[Dict[str, Any]], selector: str) -> Tuple[int, Dict[str, Any]]:
    for idx, card in enumerate(cards):
        cid = _card_id(card)
        if cid == selector:
            return idx, card
    raise KeyError(f"Card '{selector}' not found")


def move_card_between_files(
    selector: str,
    source_path: Path,
    dest_path: Path,
    target_status: Status,
    scrub: bool = False,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Move a card identified by selector from source file to dest file."""
    source_cards = _load_json(source_path)
    idx, card = _find_card(source_cards, selector)
    source_cards.pop(idx)

    card["status"] = target_status
    dest_cards = _load_json(dest_path)
    updated = scrub_card(card, now=now) if scrub else card
    dest_cards.append(updated)

    _write_json(source_path, source_cards)
    _write_json(dest_path, dest_cards)
    return updated


def transition_card(
    cfg: BoardConfig,
    selector: str,
    target_status: Status,
    base_dir: Path,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Transition a card across backlog/board/done files."""
    backlog_path = (base_dir / cfg.board.backlog_path).resolve()
    board_path = (base_dir / cfg.board.board_path).resolve()
    done_path = (base_dir / cfg.board.done_path).resolve()

    backlog_cards = _load_json(backlog_path)
    board_cards = _load_json(board_path)

    def _find_in_lists() -> Tuple[str, int, Dict[str, Any]]:
        for idx, card in enumerate(backlog_cards):
            if _card_id(card) == selector:
                return "backlog", idx, card
        for idx, card in enumerate(board_cards):
            if _card_id(card) == selector:
                return "board", idx, card
        raise KeyError(f"Card '{selector}' not found")

    location, idx, card = _find_in_lists()

    if target_status in {"planned", "active", "review"}:
        if location == "backlog":
            backlog_cards.pop(idx)
            card["status"] = target_status
            # Remove any existing board entry for same card to avoid duplicates
            board_cards = [c for c in board_cards if _card_id(c) != selector]
            board_cards.append(card)
        else:
            card["status"] = target_status
            board_cards[idx] = card
        _write_json(backlog_path, backlog_cards)
        _write_json(board_path, board_cards)
        return card

    if target_status == "done":
        if location != "board":
            raise KeyError(f"Card '{selector}' not found on board for done transition")
        board_cards.pop(idx)
        card["status"] = target_status
        done_cards = _load_json(done_path)
        done_cards.append(scrub_card(card, now=now))
        _write_json(board_path, board_cards)
        _write_json(done_path, done_cards)
        return done_cards[-1]

    raise ValueError(f"Unsupported target_status '{target_status}'")


def load_cards_by_status(base_dir: Path, cfg: BoardConfig) -> Dict[str, List[Dict[str, Any]]]:
    """Load backlog/board/done into a single dict."""
    return {
        "backlog": _load_json(base_dir / cfg.board.backlog_path),
        "board": _load_json(base_dir / cfg.board.board_path),
        "done": _load_json(base_dir / cfg.board.done_path),
    }


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Kanban board file utilities")
    parser.add_argument("--config", default=".project/board.config.yaml", help="Path to board config yaml")
    sub = parser.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("transition", help="Move a card to a target status")
    t.add_argument("--card", required=True, help="Card selector (worktree or sprint_id)")
    t.add_argument("--status", required=True, help="Target status: planned|active|review|done")
    t.add_argument("--base-dir", default=".", help="Directory containing backlog.json/board.json/done.json")

    args = parser.parse_args(argv)

    try:
        cfg = load_board_config(args.config)
    except BoardConfigError as exc:
        parser.error(str(exc))

    base_dir = Path(args.base_dir)

    if args.cmd == "transition":
        updated = transition_card(cfg, selector=args.card, target_status=args.status, base_dir=base_dir)
        print(json.dumps(updated, indent=2))
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli_main())
