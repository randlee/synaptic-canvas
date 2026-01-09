import importlib.util
import json
from pathlib import Path


def load_agent_main(path: Path):
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


def write_config(tmp_path: Path, wip_active: int) -> Path:
    cfg = {
        "version": "0.7",
        "board": {
            "backlog_path": ".project/backlog.json",
            "board_path": ".project/board.json",
            "done_path": ".project/done.json",
            "provider": "kanban",
            "wip": {"per_column": {"active": wip_active}},
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
    cfg_path = tmp_path / ".project" / "board.config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    return cfg_path


def test_wip_limit_blocks_new_active(tmp_path: Path) -> None:
    kanban_transition_main = load_agent_main(Path("packages/sc-kanban/agents/kanban_transition.py").resolve())
    cfg_path = write_config(tmp_path, wip_active=1)
    backlog = tmp_path / ".project" / "backlog.json"
    backlog.parent.mkdir(parents=True, exist_ok=True)
    backlog.write_text(json.dumps([{"worktree": "main/1-1", "status": "backlog"}, {"worktree": "main/1-2", "status": "backlog"}]), encoding="utf-8")
    (tmp_path / ".project" / "board.json").write_text("[]", encoding="utf-8")

    # First card to active should be allowed if pr_url when needed later
    result1 = run_agent(
        kanban_transition_main,
        {
            "config_path": str(cfg_path),
            "base_dir": str(tmp_path),
            "card_selector": "main/1-1",
            "target_status": "active",
        }
    )
    assert result1["success"] is True

    # Second card should hit WIP limit
    result2 = run_agent(
        kanban_transition_main,
        {
            "config_path": str(cfg_path),
            "base_dir": str(tmp_path),
            "card_selector": "main/1-2",
            "target_status": "active",
        }
    )
    assert result2["success"] is False
    assert result2["error"]["code"] == "GATE.WIP"
