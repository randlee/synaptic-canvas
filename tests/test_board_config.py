import textwrap
from pathlib import Path

import pytest

from sc_cli.board_config import BoardConfigError, load_board_config


def write_cfg(tmp_path: Path, content: str) -> Path:
    cfg_path = tmp_path / "board.config.yaml"
    cfg_path.write_text(textwrap.dedent(content), encoding="utf-8")
    return cfg_path


def test_load_board_config_happy_path(tmp_path: Path) -> None:
    cfg_path = write_cfg(
        tmp_path,
        """
        version: "0.7"
        board:
          backlog_path: .project/backlog.json
          board_path: .project/board.json
          done_path: .project/done.json
          provider: kanban
          wip:
            per_column:
              active: 3
              review: 2
          columns:
            - id: planned
              name: Planned
            - id: active
            - id: review
            - id: done
              name: Done
        cards:
          fields:
            - id: worktree
              required: true
            - id: pr_url
            - id: assignee
          conventions:
            worktree_pattern: "<project-branch>/<sprint-id>-<sprint-name>"
            sprint_id_grammar: "<phase>.<number>[<letter>]*"
        agents:
          transition: sc-kanban/kanban-transition
          query: sc-kanban/kanban-query
          checklist_fallback: checklist-agent/query-update
        """,
    )

    cfg = load_board_config(cfg_path)

    assert cfg.version == "0.7"
    assert cfg.board.provider == "kanban"
    assert cfg.board.columns[0].id == "planned"
    assert cfg.cards.fields[0].id == "worktree"
    assert cfg.agents.transition == "sc-kanban/kanban-transition"


def test_requires_checklist_agent_when_provider_checklist(tmp_path: Path) -> None:
    cfg_path = write_cfg(
        tmp_path,
        """
        version: "0.7"
        board:
          backlog_path: .project/backlog.json
          board_path: .project/board.json
          done_path: .project/done.json
          provider: checklist
          columns:
            - id: planned
          wip:
            per_column: {}
        cards:
          fields:
            - id: worktree
          conventions:
            worktree_pattern: "<project-branch>/<sprint-id>-<sprint-name>"
            sprint_id_grammar: "<phase>.<number>[<letter>]*"
        agents:
          transition: sc-kanban/kanban-transition
          query: sc-kanban/kanban-query
        """,
    )

    with pytest.raises(BoardConfigError) as exc:
        load_board_config(cfg_path)
    assert "provider=checklist requires agents.checklist_fallback" in str(exc.value)


def test_provider_checklist_happy_path(tmp_path: Path) -> None:
    cfg_path = write_cfg(
        tmp_path,
        """
        version: "0.7"
        board:
          backlog_path: .project/backlog.json
          board_path: .project/board.json
          done_path: .project/done.json
          provider: checklist
          columns:
            - id: planned
            - id: done
          wip:
            per_column:
              planned: 0
              done: 0
        cards:
          fields:
            - id: worktree
              required: true
          conventions:
            worktree_pattern: "<project-branch>/<sprint-id>-<sprint-name>"
            sprint_id_grammar: "<phase>.<number>[<letter>]*"
        agents:
          checklist_fallback: checklist-agent/query-update
        """,
    )

    cfg = load_board_config(cfg_path)

    assert cfg.board.provider == "checklist"
    assert cfg.agents.checklist_fallback == "checklist-agent/query-update"


def test_fails_on_duplicate_columns(tmp_path: Path) -> None:
    cfg_path = write_cfg(
        tmp_path,
        """
        version: "0.7"
        board:
          path: .project/board.json
          provider: kanban
          columns:
            - id: planned
            - id: planned
        cards:
          fields:
            - id: worktree
          conventions:
            worktree_pattern: "<project-branch>/<sprint-id>-<sprint-name>"
            sprint_id_grammar: "<phase>.<number>[<letter>]*"
        agents:
          transition: sc-kanban/kanban-transition
          query: sc-kanban/kanban-query
          checklist_fallback: checklist-agent/query-update
        """,
    )

    with pytest.raises(BoardConfigError) as exc:
        load_board_config(cfg_path)
    assert "board.columns ids must be unique" in str(exc.value)


def test_fails_on_duplicate_fields(tmp_path: Path) -> None:
    cfg_path = write_cfg(
        tmp_path,
        """
        version: "0.7"
        board:
          path: .project/board.json
          provider: kanban
          columns:
            - id: planned
          wip:
            per_column: {}
        cards:
          fields:
            - id: worktree
            - id: worktree
          conventions:
            worktree_pattern: "<project-branch>/<sprint-id>-<sprint-name>"
            sprint_id_grammar: "<phase>.<number>[<letter>]*"
        agents:
          transition: sc-kanban/kanban-transition
          query: sc-kanban/kanban-query
          checklist_fallback: checklist-agent/query-update
        """,
    )

    with pytest.raises(BoardConfigError) as exc:
        load_board_config(cfg_path)
    assert "cards.fields ids must be unique" in str(exc.value)


def test_fails_on_negative_wip(tmp_path: Path) -> None:
    cfg_path = write_cfg(
        tmp_path,
        """
        version: "0.7"
        board:
          path: .project/board.json
          provider: kanban
          columns:
            - id: planned
          wip:
            per_column:
              planned: -1
        cards:
          fields:
            - id: worktree
          conventions:
            worktree_pattern: "<project-branch>/<sprint-id>-<sprint-name>"
            sprint_id_grammar: "<phase>.<number>[<letter>]*"
        agents:
          transition: sc-kanban/kanban-transition
          query: sc-kanban/kanban-query
          checklist_fallback: checklist-agent/query-update
        """,
    )

    with pytest.raises(BoardConfigError) as exc:
        load_board_config(cfg_path)
    assert "WIP limit for column 'planned' must be >= 0" in str(exc.value)


def test_missing_file_raises_board_config_error(tmp_path: Path) -> None:
    missing = tmp_path / "board.config.yaml"
    with pytest.raises(BoardConfigError) as exc:
        load_board_config(missing)
    assert "Board config file not found" in str(exc.value)
