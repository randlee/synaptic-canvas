import json
from pathlib import Path

import pytest
from jsonschema import ValidationError as SchemaValidationError
from jsonschema import validate as validate_schema

from ai_cli import task_runner


def test_resolve_model_codex_aliases() -> None:
    assert task_runner.resolve_model("codex", None) == "gpt-6-astra"
    assert task_runner.resolve_model("codex", "codex") == "gpt-6-astra"
    assert task_runner.resolve_model("codex", "sol") == "gpt-6-sol"
    assert task_runner.resolve_model("codex", "astra") == "gpt-6-astra"
    assert task_runner.resolve_model("codex", "luna") == "gpt-6-luna"
    assert task_runner.resolve_model("codex", "terra") == "gpt-5.6-terra"


@pytest.mark.parametrize(
    "slug",
    ["gpt-6-sol", "gpt-6-astra", "gpt-6-luna", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"],
)
def test_resolve_model_codex_full_slugs(slug: str) -> None:
    assert task_runner.resolve_model("codex", slug) == slug


@pytest.mark.parametrize(
    "legacy", ["gpt-5.2-codex", "codex-max", "max", "codex-mini", "mini", "gpt-5", "gpt-5.2", "gtp-5"]
)
def test_resolve_model_codex_legacy_aliases_removed(legacy: str) -> None:
    with pytest.raises(ValueError, match="Valid aliases: codex, sol, astra, luna, terra"):
        task_runner.resolve_model("codex", legacy)


def test_model_catalog_consistent_with_schema_and_pydantic() -> None:
    schema_path = (
        Path(__file__).resolve().parents[1] / "packages" / "sc-codex" / "schemas" / "task_tool.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    props = schema["properties"]
    expected_models = set(task_runner.CLAUDE_MODELS) | set(task_runner.CODEX_MODEL_NAMES)
    assert set(props["model"]["enum"]) == expected_models
    assert props["reasoning_effort"]["enum"] == list(task_runner.REASONING_EFFORTS)

    generated = task_runner.TaskToolInput.model_json_schema()["properties"]
    generated_models = set()
    for option in generated["model"]["anyOf"]:
        generated_models.update(option.get("enum", []))
    assert generated_models == expected_models
    effort_enum = [o for o in generated["reasoning_effort"]["anyOf"] if "enum" in o][0]["enum"]
    assert effort_enum == list(task_runner.REASONING_EFFORTS)

    # Every alias targets a known slug; every slug has an effort table.
    assert set(task_runner.CODEX_MODEL_ALIASES.values()) <= set(task_runner.CODEX_MODEL_SLUGS)
    for efforts in task_runner.CODEX_MODEL_EFFORTS.values():
        assert set(efforts) <= set(task_runner.REASONING_EFFORTS)


def test_resolve_model_claude_defaults() -> None:
    assert task_runner.resolve_model("claude", None) == "sonnet"
    assert task_runner.resolve_model("claude", "haiku") == "haiku"


def test_resolve_model_invalid_claude() -> None:
    with pytest.raises(ValueError):
        task_runner.resolve_model("claude", "gpt-6-sol")


def test_resolve_model_invalid_codex() -> None:
    with pytest.raises(ValueError):
        task_runner.resolve_model("codex", "sonnet")


class _Result:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


_ACCOUNT_ERR = "The '{m}' model is not supported when using Codex with a ChatGPT account."


def _capture_codex(monkeypatch: pytest.MonkeyPatch, results=None) -> list:
    calls: list = []

    def fake_run(cmd, text, capture_output):
        calls.append(cmd)
        if results:
            return results[len(calls) - 1]
        return _Result(0, stdout="ok")

    monkeypatch.setattr(task_runner, "_check_runner_available", lambda runner: f"{runner} 1.0")
    monkeypatch.setattr(task_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(task_runner, "write_log", lambda event: None)
    return calls


def test_codex_account_fallback_detection() -> None:
    assert task_runner._should_fallback_codex_model("gpt-6-sol", _ACCOUNT_ERR.format(m="gpt-6-sol")) is True
    assert (
        task_runner._should_fallback_codex_model("gpt-5.6-terra", _ACCOUNT_ERR.format(m="gpt-5.6-terra")) is True
    )
    # Never falls back from the fallback model itself, nor on unrelated errors.
    assert task_runner._should_fallback_codex_model("gpt-5.5", _ACCOUNT_ERR.format(m="gpt-5.5")) is False
    assert task_runner._should_fallback_codex_model("gpt-6-sol", "unsupported") is False


def test_run_sync_retries_codex_with_general_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_codex(
        monkeypatch, [_Result(1, stderr=_ACCOUNT_ERR.format(m="gpt-6-sol")), _Result(0, stdout="ok")]
    )
    assert task_runner.run_sync("codex", "gpt-6-sol", "hello", "ultra") == "ok"
    assert calls[0][4] == "gpt-6-sol"
    assert calls[0][5:7] == ["-c", 'model_reasoning_effort="ultra"']
    assert calls[1][4] == "gpt-5.5"
    # ultra is not supported by gpt-5.5, so the retry clamps to its highest level.
    assert calls[1][5:7] == ["-c", 'model_reasoning_effort="xhigh"']


def test_codex_cmd_sol_low() -> None:
    model = task_runner.resolve_model("codex", "sol")
    effort = task_runner.resolve_reasoning_effort(model, "low")
    assert task_runner._codex_cmd(model, effort, "hi") == [
        "codex",
        "exec",
        "--yolo",
        "--model",
        "gpt-6-sol",
        "-c",
        'model_reasoning_effort="low"',
        "hi",
    ]


def test_run_sync_passes_effort_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_codex(monkeypatch)
    task_runner.run_sync("codex", "gpt-6-luna", "hi", "medium")
    assert calls[0] == ["codex", "exec", "--yolo", "--model", "gpt-6-luna", "-c", 'model_reasoning_effort="medium"', "hi"]


def test_run_sync_omits_effort_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_codex(monkeypatch)
    task_runner.run_sync("codex", "gpt-6-astra", "hi")
    assert calls[0] == ["codex", "exec", "--yolo", "--model", "gpt-6-astra", "hi"]
    assert "-c" not in calls[0]


def test_run_sync_claude_ignores_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_codex(monkeypatch)
    task_runner.run_sync("claude", "sonnet", "hi", "ultra")
    assert calls[0] == ["claude", "--model", "sonnet", "--print", "hi"]


@pytest.mark.parametrize(
    "model,effort",
    [("gpt-6-luna", "ultra"), ("gpt-5.6-luna", "ultra"), ("gpt-5.5", "max"), ("gpt-5.5", "ultra")],
)
def test_unsupported_effort_for_model_rejected(model: str, effort: str) -> None:
    with pytest.raises(ValueError, match="not supported by"):
        task_runner.resolve_reasoning_effort(model, effort)


@pytest.mark.parametrize(
    "model,effort",
    [("gpt-6-sol", "ultra"), ("gpt-6-astra", "ultra"), ("gpt-6-luna", "max"), ("gpt-5.5", "xhigh")],
)
def test_supported_effort_for_model_accepted(model: str, effort: str) -> None:
    assert task_runner.resolve_reasoning_effort(model, effort) == effort
    assert task_runner.resolve_reasoning_effort(model, None) is None


def test_run_task_rejects_unsupported_effort_before_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_codex(monkeypatch)
    payload = task_runner.TaskToolInput(
        description="Test", prompt="x", subagent_type="test", reasoning_effort="ultra"
    )
    with pytest.raises(ValueError, match="not supported by gpt-5.5"):
        task_runner.run_task(payload, runner="codex", model="gpt-5.5", run_in_background=True)
    assert calls == []


def test_payload_rejects_unknown_effort() -> None:
    with pytest.raises(Exception):
        task_runner.TaskToolInput(description="T", prompt="x", subagent_type="t", reasoning_effort="extreme")


def _run_sc_codex_task(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> dict:
    import importlib
    import sys

    sc_codex_task = importlib.import_module("sc_codex_task")
    captured: dict = {}

    def fake_run_task(payload, runner, model, run_in_background, raise_on_error=True, output_dir=None):
        captured.update(payload=payload, runner=runner, model=model, background=run_in_background)
        return task_runner.TaskToolOutputForeground(output="ok", agentId="a")

    monkeypatch.setattr(sc_codex_task, "resolve_runner", lambda preferred: "codex")
    monkeypatch.setattr(sc_codex_task, "run_task", fake_run_task)
    monkeypatch.setattr(sys, "argv", ["sc_codex_task.py", *argv])
    assert sc_codex_task.main() == 0
    return captured


def test_sc_codex_task_cli_model_and_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    got = _run_sc_codex_task(monkeypatch, ["--model", "sol", "--effort", "low", "hello"])
    assert got["model"] == "gpt-6-sol"
    assert got["payload"].reasoning_effort == "low"
    # Default for sc_codex_task.py is background mode.
    assert got["background"] is True


def test_sc_codex_task_cli_overrides_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps(
        {"description": "d", "prompt": "p", "model": "luna", "reasoning_effort": "high"}
    )
    got = _run_sc_codex_task(monkeypatch, ["--model", "astra", "--effort", "xhigh", "--json", payload])
    assert got["model"] == "gpt-6-astra"
    assert got["payload"].reasoning_effort == "xhigh"


def test_sc_codex_task_payload_effort_used_without_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"description": "d", "prompt": "p", "model": "terra", "reasoning_effort": "max"})
    got = _run_sc_codex_task(monkeypatch, ["--json", payload])
    assert got["model"] == "gpt-5.6-terra"
    assert got["payload"].reasoning_effort == "max"


def test_sc_codex_task_rejects_unsupported_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit, match="not supported by gpt-6-luna"):
        _run_sc_codex_task(monkeypatch, ["--model", "luna", "--effort", "ultra", "hello"])


def test_background_payload_carries_effort(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    popen_cmds = []
    logs = []

    class FakeProc:
        def poll(self):
            return None

    def fake_popen(cmd, stdout, stderr, env):
        popen_cmds.append(cmd)
        return FakeProc()

    monkeypatch.setattr(task_runner, "_check_runner_available", lambda runner: f"{runner} 1.0")
    monkeypatch.setattr(task_runner, "resolve_agent_path", lambda subagent_type, runner: None)
    monkeypatch.setattr(task_runner.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(task_runner, "write_log", lambda event: logs.append(event))

    payload = task_runner.TaskToolInput(
        description="Test", prompt="bg", subagent_type="test", reasoning_effort="high"
    )
    result = task_runner.run_task(
        payload, runner="codex", model="gpt-6-sol", run_in_background=True, output_dir=tmp_path
    )
    payload_file = tmp_path / f"{result.agentId}.input.json"
    stored = task_runner.TaskToolInput.model_validate_json(payload_file.read_text(encoding="utf-8"))
    assert stored.reasoning_effort == "high"
    assert "--input-file" in popen_cmds[0]
    start = [e for e in logs if e.get("event") == "task_start"][0]
    assert start["reasoning_effort"] == "high"

    # The child process re-reads the payload and passes effort through to run_sync.
    seen = {}

    def fake_run_sync(runner, model, prompt, reasoning_effort=None):
        seen.update(model=model, effort=reasoning_effort)
        return "done"

    monkeypatch.setattr(task_runner, "run_sync", fake_run_sync)
    task_runner.run_background_child_with_payload(
        stored, "codex", "gpt-6-sol", tmp_path / f"{result.agentId}.jsonl", result.agentId
    )
    assert seen == {"model": "gpt-6-sol", "effort": "high"}


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

    def fake_run_sync(runner, model, prompt, reasoning_effort=None):
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
        "          command: \"python3 -c \\\"import json,sys; json.load(sys.stdin); sys.exit(0)\\\"\"\n"
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
        "          command: \"python3 -c \\\"import sys; sys.exit(2)\\\"\"\n"
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
