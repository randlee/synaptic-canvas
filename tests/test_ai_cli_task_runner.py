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


def test_default_output_dir_codex_uses_codex_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", "/tmp/codex-home")
    assert task_runner._default_output_dir("codex") == Path("/tmp/codex-home") / "sessions"


def test_default_output_dir_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    assert task_runner._default_output_dir("codex") == tmp_path / ".sc" / "sessions"
    assert task_runner._default_output_dir("claude") == tmp_path / ".sc" / "sessions"


def test_output_schema_validation_ok() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "src" / "ai_cli" / "task_tool.output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate_schema(instance={"output": "ok", "agentId": "agent-1"}, schema=schema)
    validate_schema(
        instance={"output": "Async agent launched successfully.", "agentId": "agent-1", "output_file": "/tmp/x.jsonl"},
        schema=schema,
    )


def test_output_schema_validation_error() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "src" / "ai_cli" / "task_tool.output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    with pytest.raises(SchemaValidationError):
        validate_schema(instance={"output": "ok"}, schema=schema)
