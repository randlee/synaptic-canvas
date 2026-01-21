import json
from pathlib import Path

import pytest
from jsonschema import ValidationError as SchemaValidationError
from jsonschema import validate as validate_schema

from ai_cli import task_runner


def test_resolve_model_codex_aliases() -> None:
    assert task_runner.resolve_model("codex", None) == "gpt-5.2-codex"
    assert task_runner.resolve_model("codex", "codex") == "gpt-5.2-codex"
    assert task_runner.resolve_model("codex", "max") == "gpt-5.1-codex-max"
    assert task_runner.resolve_model("codex", "codex-mini") == "gpt-5.1-codex-mini"
    assert task_runner.resolve_model("codex", "gpt-5") == "gpt-5.2"


def test_resolve_model_claude_defaults() -> None:
    assert task_runner.resolve_model("claude", None) == "sonnet"
    assert task_runner.resolve_model("claude", "haiku") == "haiku"


def test_resolve_model_invalid_claude() -> None:
    with pytest.raises(ValueError):
        task_runner.resolve_model("claude", "gpt-5")


def test_resolve_model_invalid_codex() -> None:
    with pytest.raises(ValueError):
        task_runner.resolve_model("codex", "sonnet")


def test_resolve_runner_prefers_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(runner: str) -> str:
        if runner == "claude":
            return "claude 1.0"
        return "codex 1.0"

    monkeypatch.setattr(task_runner, "_check_runner_available", fake_check)
    assert task_runner.resolve_runner(None) == "claude"


def test_resolve_runner_falls_back_to_codex(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(runner: str) -> str:
        if runner == "claude":
            raise FileNotFoundError("claude missing")
        return "codex 1.0"

    monkeypatch.setattr(task_runner, "_check_runner_available", fake_check)
    assert task_runner.resolve_runner(None) == "codex"


def test_resolve_runner_uses_preferred(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(runner: str) -> str:
        return f"{runner} 1.0"

    monkeypatch.setattr(task_runner, "_check_runner_available", fake_check)
    assert task_runner.resolve_runner("codex") == "codex"


def test_resolve_runner_missing_preferred(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(runner: str) -> str:
        raise FileNotFoundError("missing")

    monkeypatch.setattr(task_runner, "_check_runner_available", fake_check)
    with pytest.raises(FileNotFoundError):
        task_runner.resolve_runner("claude")


def test_default_output_dir_codex_uses_codex_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", "/tmp/codex-home")
    assert task_runner._default_output_dir("codex") == Path("/tmp/codex-home") / "sessions"


def test_default_output_dir_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    assert task_runner._default_output_dir("codex") == tmp_path / ".sc" / "sessions"
    assert task_runner._default_output_dir("claude") == tmp_path / ".sc" / "sessions"


def test_output_schema_validation_ok() -> None:
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "packages"
        / "sc-codex"
        / "schemas"
        / "task_tool.output.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate_schema(instance={"output": "ok", "agentId": "agent-1"}, schema=schema)
    validate_schema(
        instance={"output": "Async agent launched successfully.", "agentId": "agent-1", "output_file": "/tmp/x.jsonl"},
        schema=schema,
    )


def test_output_schema_validation_error() -> None:
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "packages"
        / "sc-codex"
        / "schemas"
        / "task_tool.output.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    with pytest.raises(SchemaValidationError):
        validate_schema(instance={"output": "ok"}, schema=schema)


def test_run_task_logs_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_log(event):
        calls.append(event)

    def fake_run_sync(runner, model, prompt):
        raise RuntimeError("boom")

    monkeypatch.setattr(task_runner, "write_log", fake_log)
    monkeypatch.setattr(task_runner, "run_sync", fake_run_sync)

    payload = task_runner.TaskToolInput(
        description="Test",
        prompt="fail",
        subagent_type="test",
    )

    with pytest.raises(RuntimeError):
        task_runner.run_task(payload, runner="claude", model="sonnet", run_in_background=False)

    events = [c.get("event") for c in calls]
    assert "task_start" in events
    assert "task_end" in events


def test_resolve_agent_path_prefers_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agent_dir = tmp_path / ".claude" / "agents"
    agent_dir.mkdir(parents=True)
    agent_file = agent_dir / "agent-a.md"
    agent_file.write_text("---\nname: agent-a\n---\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert task_runner.resolve_agent_path("agent-a", "claude") == agent_file.resolve()


def test_resolve_agent_path_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent = tmp_path / "parent"
    child = parent / "child"
    agent_dir = parent / ".claude" / "agents"
    agent_dir.mkdir(parents=True)
    agent_file = agent_dir / "agent-b.md"
    agent_file.write_text("---\nname: agent-b\n---\n", encoding="utf-8")
    child.mkdir()
    monkeypatch.chdir(child)
    assert task_runner.resolve_agent_path("agent-b", "claude") == agent_file.resolve()


def test_resolve_agent_path_missing_codex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(Path.cwd())
    with pytest.raises(FileNotFoundError):
        task_runner.resolve_agent_path("no-such-agent", "codex")


def test_run_pretool_hooks_success(tmp_path: Path) -> None:
    agent_file = tmp_path / "agent.md"
    agent_file.write_text(
        "---\n"
        "hooks:\n"
        "  PreToolUse:\n"
        "    - matcher: \"Bash\"\n"
        "      hooks:\n"
        "        - type: command\n"
        "          command: \"python -c \\\"import json,sys; json.load(sys.stdin); sys.exit(0)\\\"\"\n"
        "---\n",
        encoding="utf-8",
    )
    payload = task_runner.TaskToolInput(
        description="Test",
        prompt="ok",
        subagent_type=str(agent_file),
    )
    task_runner.run_pretool_hooks(agent_file, payload)


def test_run_pretool_hooks_failure(tmp_path: Path) -> None:
    agent_file = tmp_path / "agent.md"
    agent_file.write_text(
        "---\n"
        "hooks:\n"
        "  PreToolUse:\n"
        "    - matcher: \"Bash\"\n"
        "      hooks:\n"
        "        - type: command\n"
        "          command: \"python -c \\\"import sys; sys.exit(2)\\\"\"\n"
        "---\n",
        encoding="utf-8",
    )
    payload = task_runner.TaskToolInput(
        description="Test",
        prompt="fail",
        subagent_type=str(agent_file),
    )
    with pytest.raises(RuntimeError):
        task_runner.run_pretool_hooks(agent_file, payload)
