import importlib.util
import json
from pathlib import Path


def load_checklist_main(path: Path):
    spec = importlib.util.spec_from_file_location("checklist_agent", path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    return mod.main


def run_agent(main_func, params: dict, tmp_path: Path) -> dict:
    input_path = tmp_path / "stdin.json"
    input_path.write_text(json.dumps(params), encoding="utf-8")
    # simulate stdin
    import sys

    sys.stdin = open(input_path, "r", encoding="utf-8")
    from io import StringIO
    out = StringIO()
    sys.stdout = out
    try:
        main_func()
    finally:
        sys.stdin = sys.__stdin__
        sys.stdout = sys.__stdout__
    return json.loads(out.getvalue())


def test_checklist_query_and_transition(tmp_path: Path) -> None:
    agent_path = Path("packages/sc-kanban/agents/checklist_agent.py").resolve()
    checklist_main = load_checklist_main(agent_path)
    roadmap = tmp_path / ".project" / "roadmap.md"
    roadmap.parent.mkdir(parents=True, exist_ok=True)
    roadmap.write_text("- [ ] Setup (sprint_id: 1.1)\n", encoding="utf-8")

    base_params = {
        "config_path": str(tmp_path / ".project" / "board.config.yaml"),
        "roadmap_path": str(roadmap),
        "prompts_dir": str(tmp_path / ".project" / "prompts"),
    }
    cfg = {
        "version": "0.7",
        "board": {
            "backlog_path": ".project/backlog.json",
            "board_path": ".project/board.json",
            "done_path": ".project/done.json",
            "provider": "checklist",
            "wip": {"per_column": {}},
            "columns": [{"id": "planned"}, {"id": "done"}],
        },
        "cards": {
            "fields": [{"id": "worktree"}, {"id": "sprint_id"}],
            "conventions": {
                "worktree_pattern": "<project-branch>/<sprint-id>-<sprint-name>",
                "sprint_id_grammar": "<phase>.<number>[<letter>]*",
            },
        },
        "agents": {"checklist_fallback": "checklist-agent/query-update"},
    }
    (tmp_path / ".project" / "board.config.yaml").write_text(json.dumps(cfg), encoding="utf-8")

    # Query
    result = run_agent(checklist_main, {"action": "query", **base_params}, tmp_path)
    assert result["success"] is True
    assert result["data"]["cards"][0]["sprint_id"] == "1.1"

    # Transition to active (creates prompt)
    result = run_agent(
        checklist_main,
        {
            "action": "transition",
            "card": {"sprint_id": "1.1", "title": "Setup"},
            "target_status": "active",
            **base_params,
        },
        tmp_path,
    )
    assert result["success"] is True
    prompt = (tmp_path / ".project" / "prompts" / "1.1.md")
    assert prompt.exists()
    # Transition to done (no additional prompt needed)
    result = run_agent(
        checklist_main,
        {
            "action": "transition",
            "card": {"sprint_id": "1.1", "title": "Setup"},
            "target_status": "done",
            **base_params,
        },
        tmp_path,
    )
    assert result["success"] is True


def test_checklist_provider_mismatch(tmp_path: Path) -> None:
    agent_path = Path("packages/sc-kanban/agents/checklist_agent.py").resolve()
    checklist_main = load_checklist_main(agent_path)
    cfg = {
        "version": "0.7",
        "board": {
            "backlog_path": ".project/backlog.json",
            "board_path": ".project/board.json",
            "done_path": ".project/done.json",
            "provider": "kanban",
            "wip": {"per_column": {}},
            "columns": [{"id": "planned"}, {"id": "done"}],
        },
        "cards": {
            "fields": [{"id": "sprint_id"}],
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
    (tmp_path / ".project").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".project" / "board.config.yaml").write_text(json.dumps(cfg), encoding="utf-8")

    result = run_agent(
        checklist_main,
        {"action": "query", "config_path": str(tmp_path / ".project" / "board.config.yaml")},
        tmp_path,
    )
    assert result["success"] is False
    assert result["error"]["code"] == "PROVIDER.NOT_CHECKLIST"


def test_checklist_missing_roadmap(tmp_path: Path) -> None:
    agent_path = Path("packages/sc-kanban/agents/checklist_agent.py").resolve()
    checklist_main = load_checklist_main(agent_path)
    cfg = {
        "version": "0.7",
        "board": {
            "backlog_path": ".project/backlog.json",
            "board_path": ".project/board.json",
            "done_path": ".project/done.json",
            "provider": "checklist",
            "wip": {"per_column": {}},
            "columns": [{"id": "planned"}, {"id": "done"}],
        },
        "cards": {
            "fields": [{"id": "sprint_id"}],
            "conventions": {
                "worktree_pattern": "<project-branch>/<sprint-id>-<sprint-name>",
                "sprint_id_grammar": "<phase>.<number>[<letter>]*",
            },
        },
        "agents": {"checklist_fallback": "checklist-agent/query-update"},
    }
    (tmp_path / ".project").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".project" / "board.config.yaml").write_text(json.dumps(cfg), encoding="utf-8")

    result = run_agent(
        checklist_main,
        {"action": "query", "config_path": str(tmp_path / ".project" / "board.config.yaml")},
        tmp_path,
    )
    assert result["success"] is False
    assert result["error"]["code"] == "CHECKLIST.MISSING_ROADMAP"
