import json
from pathlib import Path

import importlib.util
from sc_cli.board_config import load_board_config
from sc_kanban.board import load_cards_by_status


def _load_agent_main(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    return mod.main


def run_agent(main_func, params: dict) -> dict:
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


def write_config(tmp_path: Path, provider: str = "kanban") -> Path:
    cfg = {
        "version": "0.7",
        "board": {
            "backlog_path": ".project/backlog.json",
            "board_path": ".project/board.json",
            "done_path": ".project/done.json",
            "provider": provider,
            "wip": {"per_column": {"active": 3}},
            "columns": [{"id": "planned"}, {"id": "active"}, {"id": "review"}, {"id": "done"}],
        },
        "cards": {
            "fields": [{"id": "worktree", "required": True}, {"id": "sprint_id"}],
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


def test_provider_advisory_when_checklist(tmp_path: Path) -> None:
    kanban_query_main = _load_agent_main(Path("packages/sc-kanban/agents/kanban_query.py"))
    kanban_transition_main = _load_agent_main(Path("packages/sc-kanban/agents/kanban_transition.py"))
    cfg_path = write_config(tmp_path, provider="checklist")
    result = run_agent(
        kanban_query_main,
        {"config_path": str(cfg_path), "base_dir": str(tmp_path)},
    )
    assert result["success"] is False
    assert result["error"]["code"] == "PROVIDER.CHECKLIST"

    result = run_agent(
        kanban_transition_main,
        {"config_path": str(cfg_path), "base_dir": str(tmp_path), "card_selector": "main/1-1", "target_status": "planned"},
    )
    assert result["success"] is False
    assert result["error"]["code"] == "PROVIDER.CHECKLIST"


def test_full_cycle_kanban(tmp_path: Path) -> None:
    kanban_transition_main = _load_agent_main(Path("packages/sc-kanban/agents/kanban_transition.py"))
    cfg_path = write_config(tmp_path, provider="kanban")
    backlog = tmp_path / ".project" / "backlog.json"
    backlog.parent.mkdir(parents=True, exist_ok=True)
    backlog.write_text(json.dumps([{"worktree": "main/1-1", "status": "backlog", "pr_url": "https://example/pr/1"}]), encoding="utf-8")

    # planned -> active -> review -> done (scrub)
    for status in ["planned", "active", "review", "done"]:
        result = run_agent(
            kanban_transition_main,
            {
                "config_path": str(cfg_path),
                "base_dir": str(tmp_path),
                "card_selector": "main/1-1",
                "target_status": status,
            },
        )
        assert result["success"] is True

    cfg = load_board_config(cfg_path)
    cards = load_cards_by_status(tmp_path, cfg)
    assert cards["backlog"] == []
    assert cards["board"] == []
    assert "worktree" not in cards["done"][0]


def test_pm_fallback_to_checklist(tmp_path: Path) -> None:
    checklist_main = _load_agent_main(Path("packages/sc-kanban/agents/checklist_agent.py"))
    cfg_path = write_config(tmp_path, provider="checklist")
    roadmap = tmp_path / ".project" / "roadmap.md"
    roadmap.parent.mkdir(parents=True, exist_ok=True)
    roadmap.write_text("- [ ] Setup (sprint_id: 1.1)\n", encoding="utf-8")

    result = run_agent(
        checklist_main,
        {"action": "query", "config_path": str(cfg_path), "roadmap_path": str(roadmap), "prompts_dir": str(tmp_path / '.project' / 'prompts')},
    )
    assert result["success"] is True
    assert result["data"]["cards"][0]["sprint_id"] == "1.1"
