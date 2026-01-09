#!/usr/bin/env python3
"""
Checklist agent (fallback provider).
- Reads roadmap.md and optional prompts/ directory.
- Provides query/transition with v0.5 envelope; no gates.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from sc_cli.board_config import BoardConfigError, load_board_config


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


def _parse_roadmap(path: Path) -> List[Dict[str, Any]]:
    """Minimal parser: markdown checklist lines '- [ ] title (sprint_id: X)'."""
    cards: List[Dict[str, Any]] = []
    if not path.is_file():
        raise FileNotFoundError(f"roadmap not found: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("- ["):
            continue
        checked = line.startswith("- [x]")
        # naive sprint_id extraction in parentheses
        sprint_id = None
        title = line.split("]", 1)[-1].strip()
        if "(" in title and ")" in title:
            inner = title[title.find("(") + 1 : title.find(")")]
            if inner.lower().startswith("sprint_id:"):
                sprint_id = inner.split(":", 1)[1].strip()
                title = title[: title.find("(")].strip()
        cards.append({"sprint_id": sprint_id, "title": title, "status": "done" if checked else "planned"})
    return cards


def _write_roadmap(path: Path, cards: List[Dict[str, Any]]) -> None:
    lines = []
    for card in cards:
        mark = "x" if card.get("status") == "done" else " "
        title = card.get("title") or card.get("sprint_id") or "item"
        sprint = card.get("sprint_id")
        suffix = f" (sprint_id: {sprint})" if sprint else ""
        lines.append(f"- [{mark}] {title}{suffix}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        params = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps(_error("INPUT.INVALID_JSON", "Could not parse input JSON", False, "Fix input and retry")))
        return 1

    action = params.get("action")
    roadmap_path = Path(params.get("roadmap_path", ".project/roadmap.md"))
    prompts_dir = Path(params.get("prompts_dir", ".project/prompts"))
    config_path = params.get("config_path", ".project/board.config.yaml")

    if not action:
        print(json.dumps(_error("INPUT.MISSING", "action is required", False, "Provide action=query|transition")))
        return 1

    try:
        cfg = load_board_config(config_path)
    except BoardConfigError as exc:
        print(json.dumps(_error("CONFIG.INVALID", str(exc), False, "Fix .project/board.config.yaml")))
        return 1

    if cfg.board.provider != "checklist":
        print(json.dumps(_error("PROVIDER.NOT_CHECKLIST", "provider!=checklist", True, "Use kanban agents instead")))
        return 0

    prompts_dir.mkdir(parents=True, exist_ok=True)

    if action == "query":
        try:
            cards = _parse_roadmap(roadmap_path)
        except FileNotFoundError:
            print(json.dumps(_error("CHECKLIST.MISSING_ROADMAP", f"Roadmap not found: {roadmap_path}", True, "Create roadmap.md")))
            return 1
        print(
            json.dumps(
                {
                    "success": True,
                    "canceled": False,
                    "aborted_by": None,
                    "data": {"cards": cards},
                    "error": None,
                    "metadata": {"tool_calls": [], "duration_ms": 0},
                }
            )
        )
        return 0

    if action == "transition":
        card = params.get("card") or {}
        target_status = params.get("target_status")
        if not target_status:
            print(json.dumps(_error("INPUT.MISSING", "target_status required", False, "Provide target_status")))
            return 1
        cards = _parse_roadmap(roadmap_path)
        selector = card.get("sprint_id") or card.get("worktree") or card.get("title")
        if not selector:
            print(json.dumps(_error("INPUT.MISSING", "card selector missing", False, "Provide sprint_id/worktree/title")))
            return 1
        found = False
        for c in cards:
            if c.get("sprint_id") == selector or c.get("title") == selector:
                c["status"] = target_status
                found = True
                break
        if not found:
            cards.append({"sprint_id": card.get("sprint_id"), "title": card.get("title") or selector, "status": target_status})
        _write_roadmap(roadmap_path, cards)
        # Create/update ephemeral prompt
        if target_status in {"active", "review"} and card.get("sprint_id"):
            prompt_path = prompts_dir / f"{card['sprint_id']}.md"
            if not prompt_path.exists():
                prompt_path.write_text(f"# Prompt for {card['sprint_id']}\n\n", encoding="utf-8")

        print(
            json.dumps(
                {
                    "success": True,
                    "canceled": False,
                    "aborted_by": None,
                    "data": {"card": {"sprint_id": card.get("sprint_id"), "status": target_status}},
                    "error": None,
                    "metadata": {"tool_calls": [], "duration_ms": 0},
                }
            )
        )
        return 0

    print(json.dumps(_error("INPUT.UNSUPPORTED_ACTION", f"Unsupported action {action}", False, "Use query or transition")))
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
