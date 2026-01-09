import json
from pathlib import Path

import pytest

from sc_cli.board_config import BoardConfig
from sc_kanban.board import load_cards_by_status, move_card_between_files, scrub_card, transition_card


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def sample_config() -> BoardConfig:
    return BoardConfig.model_validate(
        {
            "version": "0.7",
            "board": {
                "backlog_path": ".project/backlog.json",
                "board_path": ".project/board.json",
                "done_path": ".project/done.json",
                "provider": "kanban",
                "wip": {"per_column": {"active": 3}},
                "columns": [{"id": "planned"}, {"id": "active"}, {"id": "review"}, {"id": "done"}],
            },
            "cards": {
                "fields": [{"id": "worktree", "required": True}],
                "conventions": {
                    "worktree_pattern": "<project-branch>/<sprint-id>-<sprint-name>",
                    "sprint_id_grammar": "<phase>.<number>[<letter>]*",
                },
            },
            "agents": {
                "transition": "sc-kanban/kanban-transition",
                "query": "sc-kanban/kanban-query",
                "checklist_fallback": "checklist-agent/query-update",
            },
        }
    )


def test_scrub_card_removes_rich_fields() -> None:
    card = {
        "sprint_id": "1.1",
        "title": "Setup",
        "worktree": "main/1-1-setup",
        "dev_prompt": "do work",
        "qa_prompt": "test",
        "actual_cycles": 2,
    }
    scrubbed = scrub_card(card, now=None)
    assert scrubbed["sprint_id"] == "1.1"
    assert "worktree" not in scrubbed
    assert "dev_prompt" not in scrubbed
    assert scrubbed["actual_cycles"] == 2
    assert "completed_at" in scrubbed


def test_move_card_between_files(tmp_path: Path) -> None:
    project_dir = tmp_path / ".project"
    project_dir.mkdir()
    backlog = project_dir / "backlog.json"
    board = project_dir / "board.json"
    write_json(backlog, [{"worktree": "main/1-1-setup", "status": "planned"}])
    write_json(board, [])
    cfg = sample_config()

    moved = move_card_between_files(
        selector="main/1-1-setup", source_path=backlog, dest_path=board, target_status="active", scrub=False
    )
    assert moved["status"] == "active"
    assert load_cards_by_status(tmp_path, cfg)["backlog"] == []
    assert load_cards_by_status(tmp_path, cfg)["board"][0]["worktree"] == "main/1-1-setup"


def test_transition_done_scrubs_and_moves(tmp_path: Path) -> None:
    project_dir = tmp_path / ".project"
    project_dir.mkdir()
    board = project_dir / "board.json"
    done = project_dir / "done.json"
    write_json(board, [{"worktree": "main/1-1-setup", "title": "Setup", "status": "review", "actual_cycles": 3}])
    cfg = sample_config()

    result = transition_card(cfg, selector="main/1-1-setup", target_status="done", base_dir=tmp_path)

    assert result["actual_cycles"] == 3
    assert "worktree" not in result
    assert load_cards_by_status(tmp_path, cfg)["board"] == []
    assert load_cards_by_status(tmp_path, cfg)["done"][0]["title"] == "Setup"


def test_transition_from_backlog_to_planned(tmp_path: Path) -> None:
    project_dir = tmp_path / ".project"
    project_dir.mkdir()
    backlog = project_dir / "backlog.json"
    write_json(backlog, [{"worktree": "main/1-2-feature", "status": "backlog"}])
    cfg = sample_config()

    result = transition_card(cfg, selector="main/1-2-feature", target_status="planned", base_dir=tmp_path)

    assert result["status"] == "planned"
    cards = load_cards_by_status(tmp_path, cfg)
    assert cards["backlog"] == []
    assert cards["board"][0]["status"] == "planned"


def test_missing_card_raises(tmp_path: Path) -> None:
    cfg = sample_config()
    with pytest.raises(KeyError):
        transition_card(cfg, selector="missing", target_status="done", base_dir=tmp_path)


def test_within_board_planned_to_active(tmp_path: Path) -> None:
    project_dir = tmp_path / ".project"
    project_dir.mkdir()
    board = project_dir / "board.json"
    write_json(board, [{"worktree": "main/1-3-feature", "status": "planned"}])
    cfg = sample_config()

    result = transition_card(cfg, selector="main/1-3-feature", target_status="active", base_dir=tmp_path)

    assert result["status"] == "active"
    cards = load_cards_by_status(tmp_path, cfg)
    assert len(cards["board"]) == 1
    assert cards["board"][0]["status"] == "active"


def test_within_board_active_to_review(tmp_path: Path) -> None:
    project_dir = tmp_path / ".project"
    project_dir.mkdir()
    board = project_dir / "board.json"
    write_json(board, [{"worktree": "main/1-4-feature", "status": "active"}])
    cfg = sample_config()

    result = transition_card(cfg, selector="main/1-4-feature", target_status="review", base_dir=tmp_path)

    assert result["status"] == "review"
    cards = load_cards_by_status(tmp_path, cfg)
    assert len(cards["board"]) == 1
    assert cards["board"][0]["status"] == "review"
