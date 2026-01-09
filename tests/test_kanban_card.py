import json
from pathlib import Path

import importlib.util


def load_agent_main(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    return mod.main


def run_agent(main_func, params: dict, tmp_path: Path) -> dict:
    import sys
    from io import StringIO

    stdin_backup = sys.stdin
    stdout_backup = sys.stdout
    sys.stdin = StringIO(json.dumps(params))
    out = StringIO()
    sys.stdout = out
    try:
        main_func()
    finally:
        sys.stdin = stdin_backup
        sys.stdout = stdout_backup
    return json.loads(out.getvalue())


def write_config(tmp_path: Path) -> Path:
    cfg = {
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
            "fields": [{"id": "worktree", "required": True}, {"id": "pr_url"}],
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
    cfg_path = tmp_path / ".project" / "board.config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    return cfg_path


def test_create_backlog_card(tmp_path: Path) -> None:
    kanban_card_main = load_agent_main(Path("packages/sc-kanban/agents/kanban_card.py").resolve())
    cfg_path = write_config(tmp_path)
    result = run_agent(
        kanban_card_main,
        {
            "action": "create",
            "card": {"worktree": "main/1-1", "title": "Setup"},
            "target_status": "backlog",
            "config_path": str(cfg_path),
            "base_dir": str(tmp_path),
        },
        tmp_path,
    )
    assert result["success"] is True
    backlog = json.loads((tmp_path / ".project" / "backlog.json").read_text())
    assert backlog[0]["worktree"] == "main/1-1"


def test_create_board_card(tmp_path: Path) -> None:
    kanban_card_main = load_agent_main(Path("packages/sc-kanban/agents/kanban_card.py").resolve())
    cfg_path = write_config(tmp_path)
    result = run_agent(
        kanban_card_main,
        {
            "action": "create",
            "card": {"worktree": "main/1-2", "title": "Feature"},
            "target_status": "planned",
            "config_path": str(cfg_path),
            "base_dir": str(tmp_path),
        },
        tmp_path,
    )
    assert result["success"] is True
    board = json.loads((tmp_path / ".project" / "board.json").read_text())
    assert board[0]["status"] == "planned"


def test_update_board_card(tmp_path: Path) -> None:
    kanban_card_main = load_agent_main(Path("packages/sc-kanban/agents/kanban_card.py").resolve())
    cfg_path = write_config(tmp_path)
    board = tmp_path / ".project" / "board.json"
    board.parent.mkdir(parents=True, exist_ok=True)
    board.write_text(json.dumps([{"worktree": "main/1-3", "status": "active"}]), encoding="utf-8")

    result = run_agent(
        kanban_card_main,
        {
            "action": "update",
            "card": {"worktree": "main/1-3", "pr_url": "https://example/pr/1"},
            "config_path": str(cfg_path),
            "base_dir": str(tmp_path),
        },
        tmp_path,
    )
    assert result["success"] is True
    board_data = json.loads(board.read_text())
    assert board_data[0]["pr_url"] == "https://example/pr/1"


def test_provider_checklist_advisory(tmp_path: Path) -> None:
    kanban_card_main = load_agent_main(Path("packages/sc-kanban/agents/kanban_card.py").resolve())
    cfg_path = write_config(tmp_path)
    # flip provider to checklist
    cfg = json.loads((tmp_path / ".project" / "board.config.yaml").read_text())
    cfg["board"]["provider"] = "checklist"
    (tmp_path / ".project" / "board.config.yaml").write_text(json.dumps(cfg), encoding="utf-8")

    result = run_agent(
        kanban_card_main,
        {
            "action": "create",
            "card": {"worktree": "main/1-4"},
            "config_path": str(cfg_path),
            "base_dir": str(tmp_path),
        },
        tmp_path,
    )
    assert result["success"] is False
    assert result["error"]["code"] == "PROVIDER.CHECKLIST"
