import json
import re
from pathlib import Path

import pytest
from jsonschema import ValidationError as SchemaValidationError
from jsonschema import validate as validate_schema

from ai_cli import agent_models, task_runner

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "packages" / "sc-codex"
FAKE_CODEX = "/fake/bin/codex"
FAKE_CLAUDE = "/fake/bin/claude"


def test_resolve_model_codex_aliases() -> None:
    assert task_runner.resolve_model("codex", None) == "gpt-6.1-sol"
    assert task_runner.resolve_model("codex", "codex") == "gpt-6.1-sol"
    assert task_runner.resolve_model("codex", "sol") == "gpt-6.1-sol"
    assert task_runner.resolve_model("codex", "astra") == "gpt-6-astra"
    assert task_runner.resolve_model("codex", "luna") == "gpt-6-luna"
    assert task_runner.resolve_model("codex", "terra") == "gpt-5.6-terra"


@pytest.mark.parametrize("model_id", list(agent_models.MODELS["codex"]))
def test_resolve_model_codex_full_ids(model_id: str) -> None:
    assert task_runner.resolve_model("codex", model_id) == model_id


@pytest.mark.parametrize(
    "legacy", ["gpt-5.2-codex", "codex-max", "max", "codex-mini", "mini", "gpt-5", "gpt-5.2", "gtp-5", "gpt-5.5"]
)
def test_resolve_model_codex_legacy_aliases_removed(legacy: str) -> None:
    with pytest.raises(agent_models.ModelError, match=r"Use an alias \(astra, sol, terra, luna, codex\)"):
        task_runner.resolve_model("codex", legacy)


def test_resolve_model_claude_defaults() -> None:
    assert task_runner.resolve_model("claude", None) == "claude-fable-5-1"
    assert task_runner.resolve_model("claude", "fable") == "claude-fable-5-1"
    assert task_runner.resolve_model("claude", "opus") == "claude-opus-5-5"
    assert task_runner.resolve_model("claude", "sonnet") == "claude-sonnet-5-5"
    assert task_runner.resolve_model("claude", "haiku") == "claude-haiku-5-5"


def test_resolve_model_invalid_claude() -> None:
    with pytest.raises(ValueError):
        task_runner.resolve_model("claude", "gpt-6.1-sol")


def test_resolve_model_invalid_codex() -> None:
    with pytest.raises(ValueError):
        task_runner.resolve_model("codex", "sonnet")


def _schema() -> dict:
    return json.loads((PACKAGE / "schemas" / "task_tool.schema.json").read_text(encoding="utf-8"))


def test_schema_model_and_effort_enums_match_agent_models() -> None:
    props = _schema()["properties"]
    expected = agent_models.model_choices("codex") + agent_models.model_choices("claude")
    assert [m for m in props["model"]["enum"] if m is not None] == expected
    assert [e for e in props["reasoning_effort"]["enum"] if e is not None] == list(agent_models.EFFORTS)
    # Descriptions are generated from the table too (task_tool builds them).
    assert props["model"]["description"] == task_runner.TaskToolInput.model_fields["model"].description
    assert (
        props["reasoning_effort"]["description"]
        == task_runner.TaskToolInput.model_fields["reasoning_effort"].description
    )
    for choice in expected:
        assert choice in props["model"]["description"]


def test_schema_nullability_matches_pydantic() -> None:
    schema = _schema()
    props = schema["properties"]
    generated = task_runner.TaskToolInput.model_json_schema()["properties"]
    for name, field in task_runner.TaskToolInput.model_fields.items():
        if field.is_required():
            continue
        pyd_nullable = any(o.get("type") == "null" for o in generated[name].get("anyOf", []))
        types = props[name]["type"]
        json_nullable = "null" in (types if isinstance(types, list) else [types])
        assert pyd_nullable == json_nullable, name
        if json_nullable and "enum" in props[name]:
            assert None in props[name]["enum"], name

    base = {"description": "d", "prompt": "p", "subagent_type": "s"}
    for extra in ({"reasoning_effort": None}, {"reasoning_effort": "low"}, {"model": None}, {"model": "sol"}):
        instance = {**base, **extra}
        task_runner.TaskToolInput.model_validate(instance)
        validate_schema(instance=instance, schema=schema)
    with pytest.raises(SchemaValidationError):
        validate_schema(instance={**base, "reasoning_effort": "minimal"}, schema=schema)
    with pytest.raises(SchemaValidationError):
        validate_schema(instance={**base, "model": "mini"}, schema=schema)


# --- docs cannot drift from the table -------------------------------------------------------

_DOCS = sorted(p for p in PACKAGE.rglob("*.md") if p.name != "CHANGELOG.md") + [
    PACKAGE / "schemas" / "task_tool.schema.json"
]
_ID_PATTERNS = (re.compile(r"gpt-\d[\w.-]*"), re.compile(r"claude-[a-z]+-\d[\w-]*"))


def _readme_rows() -> list:
    rows = []
    for tool in ("codex", "claude"):
        default_id = agent_models.resolve_model(tool).id
        for spec in agent_models.MODELS[tool].values():
            aliases = [a for a, target in agent_models.ALIASES[tool].items() if target == spec.id]
            rows.append(
                "| {tool} | `{id}` | {aliases} | {efforts} | {default_effort} | {default} |".format(
                    tool=tool,
                    id=spec.id,
                    aliases=", ".join(f"`{a}`" for a in aliases) or "-",
                    efforts=", ".join(spec.efforts),
                    default_effort=spec.default_effort or "CLI default",
                    default="yes" if spec.id == default_id else "",
                ).replace("|  |", "| |")
            )
    return rows


def test_readme_model_table_matches_agent_models() -> None:
    lines = (PACKAGE / "README.md").read_text(encoding="utf-8").splitlines()
    table = [ln.rstrip() for ln in lines if ln.startswith(("| codex |", "| claude |"))]
    assert table == _readme_rows()
    text = "\n".join(lines)
    for model_id in agent_models.MODELS["codex"]:
        assert model_id in text


@pytest.mark.parametrize("doc", _DOCS, ids=lambda p: str(p.relative_to(PACKAGE)))
def test_docs_name_only_known_model_ids(doc: Path) -> None:
    known = {m for tool in agent_models.TOOLS for m in agent_models.MODELS[tool]}
    text = doc.read_text(encoding="utf-8")
    found = {m.rstrip(".-") for pattern in _ID_PATTERNS for m in pattern.findall(text)}
    assert found <= known, f"{doc.name} names model ids not in agent_models: {sorted(found - known)}"


# --- command building and execution ---------------------------------------------------------


class _Result:
    def __init__(self, returncode: int, stdout: bytes = b"", stderr: bytes = b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _capture_run(monkeypatch: pytest.MonkeyPatch, result: "_Result" = None) -> list:
    calls: list = []

    def fake_run(cmd, input, capture_output, env):
        calls.append({"cmd": cmd, "input": input, "env": env})
        return result or _Result(0, stdout=b"ok\n")

    monkeypatch.setattr(task_runner, "_check_runner_available", lambda runner: f"{runner} 1.0")
    monkeypatch.setattr(
        task_runner.shutil, "which", lambda name: {"codex": FAKE_CODEX, "claude": FAKE_CLAUDE}.get(name)
    )
    monkeypatch.setattr(task_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(task_runner, "write_log", lambda event: None)
    return calls


def test_build_command_codex_sol_low() -> None:
    model = task_runner.resolve_model("codex", "sol")
    assert task_runner.build_command("codex", FAKE_CODEX, model, "low") == [
        FAKE_CODEX,
        "exec",
        "--yolo",
        "--model",
        "gpt-6.1-sol",
        "-c",
        "model_reasoning_effort=low",
        "-",
    ]


def test_build_command_claude_effort() -> None:
    assert task_runner.build_command("claude", FAKE_CLAUDE, "opus", "max") == [
        FAKE_CLAUDE,
        "--model",
        "claude-opus-5-5",
        "--effort",
        "max",
        "--print",
    ]


def test_build_command_flags_carry_no_quotes() -> None:
    for tool in agent_models.TOOLS:
        for spec in agent_models.MODELS[tool].values():
            for effort in spec.efforts:
                cmd = task_runner.build_command(tool, "x", spec.id, effort)
                assert not any('"' in arg or "'" in arg for arg in cmd), cmd


def test_run_sync_codex_passes_effort_and_prompt_on_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_run(monkeypatch)
    prompt = "line one\r\nline two \u00e9"
    assert task_runner.run_sync("codex", "gpt-6-luna", prompt, "medium") == "ok"
    assert calls[0]["cmd"] == [
        FAKE_CODEX, "exec", "--yolo", "--model", "gpt-6-luna", "-c", "model_reasoning_effort=medium", "-"
    ]
    # Binary UTF-8 on stdin, byte for byte (no newline translation), never in argv.
    assert calls[0]["input"] == prompt.encode("utf-8")
    assert prompt not in calls[0]["cmd"]


def test_run_sync_codex_omits_effort_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_run(monkeypatch)
    task_runner.run_sync("codex", "gpt-6-astra", "hi")
    assert calls[0]["cmd"] == [FAKE_CODEX, "exec", "--yolo", "--model", "gpt-6-astra", "-"]


def test_run_sync_claude_passes_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_run(monkeypatch)
    task_runner.run_sync("claude", "sonnet", "hi", "high")
    assert calls[0]["cmd"] == [FAKE_CLAUDE, "--model", "claude-sonnet-5-5", "--effort", "high", "--print"]
    assert calls[0]["input"] == b"hi"


@pytest.mark.parametrize("runner", ["codex", "claude"])
def test_run_sync_child_never_inherits_atm_identity(monkeypatch: pytest.MonkeyPatch, runner) -> None:
    monkeypatch.setenv("ATM_IDENTITY", "Parent-1234")
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    calls = _capture_run(monkeypatch)
    task_runner.run_sync(runner, task_runner.resolve_model(runner, None), "hi")
    env = calls[0]["env"]
    assert "ATM_IDENTITY" not in env
    assert "Parent-1234" not in env.values()
    assert env["ATM_TEAM"] == "atm-core"  # still on the caller's team
    assert task_runner.os.environ["ATM_IDENTITY"] == "Parent-1234"  # caller's env untouched


def test_run_sync_raises_with_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    _capture_run(monkeypatch, _Result(1, stderr=b"model rejected\n"))
    with pytest.raises(RuntimeError, match="model rejected"):
        task_runner.run_sync("codex", "gpt-6.1-sol", "hi")


def test_run_sync_does_not_retry_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # The ChatGPT-account fallback to gpt-5.5 was removed: codex no longer serves gpt-5.5.
    calls = _capture_run(
        monkeypatch,
        _Result(1, stderr=b"The 'gpt-6.1-sol' model is not supported when using Codex with a ChatGPT account."),
    )
    with pytest.raises(RuntimeError):
        task_runner.run_sync("codex", "gpt-6.1-sol", "hi")
    assert len(calls) == 1


def test_runner_executable_uses_which_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_runner.shutil, "which", lambda name: f"C:/npm/{name}.cmd")
    assert task_runner._runner_executable("codex") == "C:/npm/codex.cmd"
    monkeypatch.setattr(task_runner.shutil, "which", lambda name: None)
    with pytest.raises(FileNotFoundError):
        task_runner._runner_executable("claude")


@pytest.mark.parametrize(
    "runner,model,effort",
    [("codex", "gpt-6-luna", "ultra"), ("codex", "gpt-5.6-luna", "ultra"), ("claude", "opus", "ultra")],
)
def test_unsupported_effort_for_model_rejected(runner: str, model: str, effort: str) -> None:
    with pytest.raises(agent_models.ModelError, match="is not supported by"):
        task_runner.resolve_reasoning_effort(runner, model, effort)


@pytest.mark.parametrize(
    "runner,model,effort",
    [("codex", "gpt-6.1-sol", "ultra"), ("codex", "gpt-6-astra", "ultra"), ("codex", "gpt-6-luna", "max"),
     ("claude", "fable", "max")],
)
def test_supported_effort_for_model_accepted(runner: str, model: str, effort: str) -> None:
    assert task_runner.resolve_reasoning_effort(runner, model, effort) == effort
    assert task_runner.resolve_reasoning_effort(runner, model, None) is None


def test_run_task_rejects_unsupported_effort_before_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_run(monkeypatch)
    payload = task_runner.TaskToolInput(description="Test", prompt="x", subagent_type="test", reasoning_effort="ultra")
    with pytest.raises(agent_models.ModelError, match="not supported by gpt-6-luna"):
        task_runner.run_task(payload, runner="codex", model="gpt-6-luna", run_in_background=True)
    assert calls == []


def test_prepare_payload_rejects_unknown_effort() -> None:
    with pytest.raises(agent_models.ModelError, match="Effort 'extreme'"):
        task_runner.prepare_payload(
            {"description": "T", "prompt": "x", "subagent_type": "t", "reasoning_effort": "extreme"}, "codex"
        )


def test_prepare_payload_writes_back_resolved_model() -> None:
    payload, model = task_runner.prepare_payload({"description": "T", "prompt": "x", "subagent_type": "t"}, "codex")
    assert model == payload.model == "gpt-6.1-sol"
    payload, model = task_runner.prepare_payload(
        {"description": "T", "prompt": "x", "subagent_type": "t", "model": "luna"}, "codex", effort="high"
    )
    assert (model, payload.model, payload.reasoning_effort) == ("gpt-6-luna", "gpt-6-luna", "high")


def _run_sc_codex_task(monkeypatch: pytest.MonkeyPatch, argv: list) -> dict:
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
    assert got["model"] == "gpt-6.1-sol"
    assert got["payload"].reasoning_effort == "low"
    # Default for sc_codex_task.py is background mode.
    assert got["background"] is True


def test_sc_codex_task_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    got = _run_sc_codex_task(monkeypatch, ["hello"])
    assert got["model"] == got["payload"].model == "gpt-6.1-sol"
    assert got["payload"].reasoning_effort is None


def test_sc_codex_task_cli_overrides_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"description": "d", "prompt": "p", "model": "luna", "reasoning_effort": "high"})
    got = _run_sc_codex_task(monkeypatch, ["--model", "astra", "--effort", "xhigh", "--json", payload])
    assert got["model"] == "gpt-6-astra"
    assert got["payload"].reasoning_effort == "xhigh"


def test_sc_codex_task_payload_effort_used_without_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"description": "d", "prompt": "p", "model": "terra", "reasoning_effort": "max"})
    got = _run_sc_codex_task(monkeypatch, ["--json", payload])
    assert got["model"] == "gpt-5.6-terra"
    assert got["payload"].reasoning_effort == "max"


def test_sc_codex_task_cli_overrides_invalid_payload_values(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"description": "d", "prompt": "p", "model": "mini", "reasoning_effort": "extreme"})
    got = _run_sc_codex_task(monkeypatch, ["--model", "sol", "--effort", "low", "--json", payload])
    assert got["model"] == "gpt-6.1-sol"
    # Persisted payload carries the resolved override, so background runs/logs reflect it.
    assert got["payload"].model == "gpt-6.1-sol"
    assert got["payload"].reasoning_effort == "low"


def test_sc_codex_task_rejects_unknown_cli_model(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit, match="Unknown codex model 'mini'. Use an alias"):
        _run_sc_codex_task(monkeypatch, ["--model", "mini", "hello"])


def test_sc_codex_task_rejects_unknown_payload_model(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"description": "d", "prompt": "p", "model": "gpt-5.2-codex"})
    with pytest.raises(SystemExit) as exc:
        _run_sc_codex_task(monkeypatch, ["--json", payload])
    message = str(exc.value)
    assert message.startswith("Unknown codex model 'gpt-5.2-codex'. Use an alias")
    assert "literal_error" not in message and "validation error" not in message


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

    payload, model = task_runner.prepare_payload(
        {"description": "Test", "prompt": "bg", "subagent_type": "test", "model": "sol", "reasoning_effort": "high"},
        "codex",
    )
    result = task_runner.run_task(payload, runner="codex", model=model, run_in_background=True, output_dir=tmp_path)
    payload_file = tmp_path / f"{result.agentId}.input.json"
    stored = task_runner.TaskToolInput.model_validate_json(payload_file.read_text(encoding="utf-8"))
    assert stored.reasoning_effort == "high"
    assert stored.model == "gpt-6.1-sol"
    assert "--input-file" in popen_cmds[0]
    start = [e for e in logs if e.get("event") == "task_start"][0]
    assert start["reasoning_effort"] == "high"
    assert start["model"] == "gpt-6.1-sol"

    # The child process re-reads the payload and passes effort through to run_sync.
    seen = {}

    def fake_run_sync(runner, model, prompt, reasoning_effort=None):
        seen.update(model=model, effort=reasoning_effort)
        return "done"

    monkeypatch.setattr(task_runner, "run_sync", fake_run_sync)
    task_runner.run_background_child_with_payload(
        stored, "codex", "gpt-6.1-sol", tmp_path / f"{result.agentId}.jsonl", result.agentId
    )
    assert seen == {"model": "gpt-6.1-sol", "effort": "high"}
    end = [e for e in logs if e.get("event") == "task_end"][0]
    assert end["reasoning_effort"] == "high"


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
    assert all("reasoning_effort" in c for c in calls if c.get("event") in ("task_start", "task_end"))


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


def _run_ai_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, payload: dict, argv: list):
    import sys

    from ai_cli import cli

    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")
    captured: dict = {}

    def fake_run_task(payload, runner, model, run_in_background, output_dir=None, raise_on_error=True):
        captured.update(payload=payload, runner=runner, model=model, background=run_in_background)
        return task_runner.TaskToolOutputForeground(output="ok", agentId="a")

    monkeypatch.setattr(cli, "resolve_runner", lambda preferred: preferred or "codex")
    monkeypatch.setattr(cli, "run_task", fake_run_task)
    monkeypatch.setattr(cli, "write_log", lambda event: None)
    monkeypatch.setattr(sys, "argv", ["ai_cli", "run", "--file", str(input_file), *argv])
    return cli.main(), captured


_BASE_PAYLOAD = {"description": "d", "prompt": "p", "subagent_type": "sc-codex"}


def test_ai_cli_run_effort_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    rc, got = _run_ai_cli(
        monkeypatch,
        tmp_path,
        {**_BASE_PAYLOAD, "reasoning_effort": "high"},
        ["--runner", "codex", "--model", "sol", "--effort", "low"],
    )
    assert rc == 0
    assert got["model"] == "gpt-6.1-sol"
    assert got["payload"].model == "gpt-6.1-sol"
    assert got["payload"].reasoning_effort == "low"
    assert got["background"] is False  # ai_cli run defaults to blocking


def test_ai_cli_run_claude_runner_effort(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    rc, got = _run_ai_cli(monkeypatch, tmp_path, _BASE_PAYLOAD, ["--runner", "claude", "--effort", "xhigh"])
    assert rc == 0
    assert got["model"] == "claude-fable-5-1"
    assert got["payload"].reasoning_effort == "xhigh"


def test_ai_cli_run_rejects_unsupported_effort(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    rc, got = _run_ai_cli(
        monkeypatch, tmp_path, _BASE_PAYLOAD, ["--runner", "codex", "--model", "luna", "--effort", "ultra"]
    )
    assert rc != 0
    assert got == {}
    assert "not supported by gpt-6-luna" in capsys.readouterr().err


def test_ai_cli_run_overrides_invalid_payload_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    rc, got = _run_ai_cli(
        monkeypatch,
        tmp_path,
        {**_BASE_PAYLOAD, "model": "mini", "reasoning_effort": "extreme"},
        ["--runner", "codex", "--model", "sol", "--effort", "low"],
    )
    assert rc == 0
    assert got["payload"].model == "gpt-6.1-sol"
    assert got["payload"].reasoning_effort == "low"


def test_ai_cli_run_unknown_payload_model_fails_with_choices(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    rc, got = _run_ai_cli(monkeypatch, tmp_path, {**_BASE_PAYLOAD, "model": "mini"}, ["--runner", "codex"])
    assert rc != 0
    assert got == {}
    assert "Unknown codex model 'mini'. Use an alias" in capsys.readouterr().err
