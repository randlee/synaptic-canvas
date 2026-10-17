"""Session, resume, isolation, timeout, and typed-failure tests for sc-launchpad.

Every test that launches a child uses fake `claude` / `codex` executables placed
on PATH (a shebang script on POSIX, a `.cmd` shim on Windows), so no real CLI,
network, or credentials are involved.
"""

import importlib.util
import json
import os
import subprocess
import sys
import signal
import textwrap
import time
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).parent.parent.parent
    / "packages"
    / "sc-launchpad"
    / "scripts"
    / "sc_launchpad_task.py"
)
spec = importlib.util.spec_from_file_location("sc_launchpad_task_sessions", SCRIPT)
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)

SESSION = "11111111-2222-4333-8444-555555555555"
THREAD = "01a14b21-8dde-7922-9867-dd61bf90ebf1"

FAKE_CLI = textwrap.dedent(
    """
    import json, os, subprocess, sys, time
    spec = json.loads(os.environ.get("FAKE_CLI_SPEC", "{}"))
    record = os.environ.get("FAKE_CLI_RECORD")
    if record:
        with open(record, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "argv": sys.argv[1:],
                    "cwd": os.getcwd(),
                    "cwd_entries": sorted(os.listdir(os.getcwd())),
                    "stdin": sys.stdin.buffer.read().decode("utf-8") if not sys.stdin.isatty() else None,
                    "atm_team": os.environ.get("ATM_TEAM"),
                },
                fh,
            )
    if spec.get("spawn_pid_file"):
        # A grandchild that would outlive us unless the whole tree is killed.
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(120)"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        with open(spec["spawn_pid_file"] + ".tmp", "w") as fh:
            fh.write(str(child.pid))
        os.replace(spec["spawn_pid_file"] + ".tmp", spec["spawn_pid_file"])
    if spec.get("pre_stdout"):
        sys.stdout.write(spec["pre_stdout"])
        sys.stdout.flush()
    if spec.get("sleep"):
        time.sleep(spec["sleep"])
    sys.stdout.write(spec.get("stdout", ""))
    sys.stderr.write(spec.get("stderr", ""))
    sys.exit(spec.get("exit_code", 0))
    """
)


def claude_json(**overrides):
    data = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "session_id": SESSION,
        "result": '```json\n{"choice": "A"}\n```',
    }
    data.update(overrides)
    return json.dumps(data)


def codex_jsonl(*events):
    return "\n".join(json.dumps(event) for event in events) + "\n"


CODEX_OK = codex_jsonl(
    {"type": "thread.started", "thread_id": THREAD},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "thinking"}},
    {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": "FINAL"}},
    {"type": "turn.completed", "usage": {}},
)


@pytest.fixture
def fake_bin(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = tmp_path / "fake_cli.py"
    script.write_text(FAKE_CLI, encoding="utf-8")
    for name in ("claude", "codex", "gemini"):
        if os.name == "nt":
            (bin_dir / f"{name}.cmd").write_text(
                f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8"
            )
        else:
            target = bin_dir / name
            target.write_text(
                f"#!{sys.executable}\n" + FAKE_CLI, encoding="utf-8"
            )
            target.chmod(0o755)
    return bin_dir


@pytest.fixture
def workdir(tmp_path):
    path = tmp_path / "work"
    path.mkdir()
    return path


def make_env(fake_bin, tmp_path, spec=None, **extra):
    env = dict(os.environ)
    env.pop("ATM_TEAM", None)
    env.pop("ATM_IDENTITY", None)
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    env["FAKE_CLI_SPEC"] = json.dumps(spec or {})
    env["FAKE_CLI_RECORD"] = str(tmp_path / "record.json")
    env.update(extra)
    return env


def recorded(tmp_path):
    return json.loads((tmp_path / "record.json").read_text(encoding="utf-8"))


def payload(**fields):
    base = {"description": "test launch", "prompt": "Answer the question", "tool": "claude"}
    base.update(fields)
    return lp.LaunchpadInput.model_validate(base)


def run(fake_bin, tmp_path, spec, **fields):
    return lp.run_payload(payload(**fields), make_env(fake_bin, tmp_path, spec))


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


def test_result_variants_are_frozen_with_literal_discriminant():
    ok = lp.Ok(5)
    err = lp.Err(lp.Failure("X.Y", "boom"))
    assert ok.kind == "ok" and ok.value == 5
    assert err.kind == "err" and err.error.code == "X.Y"
    with pytest.raises(FrozenInstanceError):
        ok.value = 6
    with pytest.raises(FrozenInstanceError):
        err.error = None


def test_unwrap_raises_launchpad_error_for_err():
    with pytest.raises(lp.LaunchpadError) as excinfo:
        lp.unwrap(lp.Err(lp.Failure("X.Y", "boom", suggested_action="fix")))
    assert excinfo.value.code == "X.Y"
    assert excinfo.value.suggested_action == "fix"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {"cwd": "/tmp", "resume_session_id": SESSION},
        {"resume_session_id": SESSION, "isolation": {"tools": "none", "cwd": "temp"}},
        {"cwd": "/tmp", "isolation": {"cwd": "temp"}},
        {},
        {"cwd": "/tmp", "resume_session_id": SESSION, "isolation": {}, "output_format": "text"},
        {"cwd": "/tmp", "isolation": {"tools": "some"}},
        {"cwd": "/tmp", "isolation": {"network": "off"}},
        {"cwd": "/tmp", "timeout_seconds": 0},
        {"cwd": "/tmp", "resume_session_id": ""},
        {"cwd": "/tmp", "session": "x"},
    ],
)
def test_invalid_payloads_are_rejected(fields):
    raw = json.dumps(
        dict({"description": "d", "prompt": "p", "tool": "claude"}, **fields)
    )
    result = lp.load_payload_result(raw)
    assert result.kind == "err"
    assert result.error.code == "VALIDATION.INVALID_PAYLOAD"


def test_existing_payload_shape_still_validates_and_defaults_to_text():
    item = payload(cwd="/tmp", model="haiku", extra_args=["--x"], atm_identity="r1")
    assert item.resolved_output_format() == "text"
    assert item.isolation is None and item.resume_session_id is None


def test_isolation_or_resume_defaults_to_json_output():
    assert payload(cwd="/tmp", isolation={}).resolved_output_format() == "json"
    resumed = payload(cwd="/tmp", resume_session_id=SESSION, isolation={"tools": "none"})
    assert resumed.resolved_output_format() == "json"
    assert payload(cwd="/tmp", output_format="json").resolved_output_format() == "json"


def test_temp_cwd_payload_needs_no_cwd():
    item = payload(isolation={"tools": "none", "cwd": "temp"})
    assert item.cwd is None


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------


def test_claude_json_isolated_command():
    item = payload(model="haiku", isolation={"tools": "none", "cwd": "temp"})
    command = lp.build_command(item, "haiku")
    assert command[:4] == ["claude", "--print", "--output-format", "json"]
    assert "--dangerously-skip-permissions" not in command
    tools_at = command.index("--tools")
    assert command[tools_at + 1] == ""
    assert command[tools_at + 2].startswith("--")
    for flag in ("--strict-mcp-config", "--safe-mode", "--disable-slash-commands"):
        assert flag in command
    # The prompt goes to stdin, never argv.
    assert "Answer the question" not in command
    assert lp.prompt_stdin(item) == "Answer the question"


def test_claude_resume_relaxed_command_keeps_permissions_flag():
    item = payload(cwd="/tmp", resume_session_id=SESSION, isolation={"tools": "default"})
    command = lp.build_command(item, "sonnet")
    assert command[command.index("--resume") + 1] == SESSION
    assert "--dangerously-skip-permissions" in command
    assert "--tools" not in command


def test_codex_json_isolated_command():
    item = payload(tool="codex", model="luna", isolation={"tools": "none", "cwd": "temp"})
    command = lp.build_command(item, "gpt-5.6-luna")
    assert command[:3] == ["codex", "exec", "--json"]
    assert "--yolo" not in command
    assert "--skip-git-repo-check" in command
    assert 'sandbox_mode="read-only"' in command
    assert 'web_search="disabled"' in command
    for feature in ("shell_tool", "unified_exec", "code_mode_host"):
        assert command[command.index(feature) - 1] == "--disable"
    assert command[-2:] == ["--", "-"]
    assert lp.prompt_stdin(item) == "Answer the question"


def test_codex_resume_command_places_session_before_prompt():
    item = payload(
        tool="codex", cwd="/tmp", resume_session_id=THREAD, isolation={"tools": "none"}
    )
    command = lp.build_command(item, "gpt-5.6-terra")
    assert command[:4] == ["codex", "exec", "resume", "--json"]
    assert command[-3:] == ["--", THREAD, "-"]
    assert "--sandbox" not in command  # `exec resume` has no --sandbox; -c is used


def test_codex_resume_relaxed_uses_yolo():
    item = payload(
        tool="codex", cwd="/tmp", resume_session_id=THREAD, isolation={"tools": "default"}
    )
    command = lp.build_command(item, "gpt-5.6-terra")
    assert "--yolo" in command
    assert "--disable" not in command


# ---------------------------------------------------------------------------
# Successful structured launches
# ---------------------------------------------------------------------------


def test_claude_isolated_turn_returns_session_and_result(fake_bin, tmp_path):
    response = run(
        fake_bin,
        tmp_path,
        {"stdout": claude_json()},
        model="haiku",
        isolation={"tools": "none", "cwd": "temp"},
    )
    assert response["success"] is True, response
    data = response["data"]
    assert data["session_id"] == SESSION
    assert data["result_text"] == '```json\n{"choice": "A"}\n```'
    assert data["output_format"] == "json"
    assert data["isolation"]["tools"] == "none"
    assert data["isolation"]["cwd"] == "temp"
    assert "--safe-mode" in data["isolation"]["flags"]
    assert data["stdout"].strip() == claude_json()
    rec = recorded(tmp_path)
    assert Path(rec["cwd"]).resolve() == Path(data["cwd"]).resolve()
    assert rec["cwd_entries"] == []
    assert Path(data["cwd"]).name.startswith("sc-launchpad-")
    assert data["temp_cwd_created"] is True
    assert rec["stdin"] == "Answer the question"
    assert "Answer the question" not in rec["argv"]


def test_claude_resume_uses_given_cwd_and_session(fake_bin, tmp_path, workdir):
    response = run(
        fake_bin,
        tmp_path,
        {"stdout": claude_json(result="because")},
        cwd=str(workdir),
        resume_session_id=SESSION,
        isolation={"tools": "none", "cwd": "given"},
    )
    assert response["success"] is True, response
    assert response["data"]["resumed_session_id"] == SESSION
    assert response["data"]["result_text"] == "because"
    assert response["data"]["warnings"] == []
    rec = recorded(tmp_path)
    assert rec["argv"][rec["argv"].index("--resume") + 1] == SESSION
    assert Path(rec["cwd"]).resolve() == workdir.resolve()


def test_resume_reporting_new_session_id_adds_warning(fake_bin, tmp_path, workdir):
    response = run(
        fake_bin,
        tmp_path,
        {"stdout": claude_json(session_id="99999999-2222-4333-8444-555555555555")},
        cwd=str(workdir),
        resume_session_id=SESSION,
        isolation={},
    )
    assert response["success"] is True
    assert response["data"]["warnings"]


def test_codex_turn_returns_thread_id_and_last_message(fake_bin, tmp_path):
    response = run(
        fake_bin,
        tmp_path,
        {"stdout": CODEX_OK},
        tool="codex",
        model="luna",
        isolation={"tools": "none", "cwd": "temp"},
    )
    assert response["success"] is True, response
    assert response["data"]["session_id"] == THREAD
    assert response["data"]["result_text"] == "FINAL"
    assert response["data"]["model"] == "gpt-5.6-luna"
    argv = recorded(tmp_path)["argv"]
    assert argv[:2] == ["exec", "--json"]


def test_codex_resume_argv(fake_bin, tmp_path, workdir):
    response = run(
        fake_bin,
        tmp_path,
        {"stdout": CODEX_OK},
        tool="codex",
        cwd=str(workdir),
        resume_session_id=THREAD,
        isolation={"tools": "none"},
    )
    assert response["success"] is True, response
    argv = recorded(tmp_path)["argv"]
    assert argv[:3] == ["exec", "resume", "--json"]
    assert argv[-3:] == ["--", THREAD, "-"]
    assert recorded(tmp_path)["stdin"] == "Answer the question"
    assert response["data"]["temp_cwd_created"] is False


def test_codex_item_errors_and_transient_error_events_become_warnings(fake_bin, tmp_path, workdir):
    stdout = codex_jsonl(
        {"type": "thread.started", "thread_id": THREAD},
        {"type": "item.completed", "item": {"type": "error", "message": "code mode fail closed"}},
        {"type": "error", "message": "Reconnecting... 1/5"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}},
        {"type": "turn.completed"},
    )
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool="codex", cwd=str(workdir), output_format="json")
    assert response["success"] is True, response
    assert response["data"]["warnings"] == ["code mode fail closed", "Reconnecting... 1/5"]


def test_text_mode_is_backward_compatible(fake_bin, tmp_path, workdir):
    response = run(fake_bin, tmp_path, {"stdout": "plain text\n"}, cwd=str(workdir), model="haiku")
    assert response["success"] is True
    data = response["data"]
    for key in ("tool", "model", "cwd", "teammate_mode", "atm_team", "atm_identity", "exit_code", "stdout", "stderr"):
        assert key in data
    assert data["stdout"] == "plain text\n"
    assert data["session_id"] is None and data["result_text"] is None
    assert data["output_format"] == "text"
    rec = recorded(tmp_path)
    assert rec["argv"] == ["--dangerously-skip-permissions", "--print", "--model", "haiku", "Answer the question"]
    # Legacy text mode keeps the prompt on argv; stdin is empty, never inherited.
    assert rec["stdin"] in ("", None)


@pytest.mark.parametrize("tool", ["claude", "codex"])
def test_text_mode_command_line_is_unchanged(tool):
    item = payload(tool=tool, cwd="/tmp", extra_args=["--x"])
    model = "sonnet" if tool == "claude" else "gpt-5.6-terra"
    expected = {
        "claude": ["claude", "--dangerously-skip-permissions", "--print", "--model", "sonnet", "--x", "Answer the question"],
        "codex": ["codex", "exec", "--yolo", "--model", "gpt-5.6-terra", "--x", "Answer the question"],
    }[tool]
    assert lp.build_command(item, model) == expected
    assert lp.prompt_stdin(item) is None


# ---------------------------------------------------------------------------
# Typed failures
# ---------------------------------------------------------------------------


def test_cli_not_found_lists_searched_path(tmp_path, workdir):
    empty = tmp_path / "empty"
    empty.mkdir()
    env = dict(os.environ, PATH=str(empty))
    response = lp.run_payload(payload(cwd=str(workdir)), env)
    assert response["success"] is False
    assert response["error"]["code"] == "CLI.NOT_FOUND"
    assert response["error"]["details"]["searched_path"] == [str(empty)]
    assert response["error"]["suggested_action"]


def test_atm_not_found_in_teammate_mode(fake_bin, tmp_path, workdir):
    env = make_env(fake_bin, tmp_path, {}, ATM_TEAM="team-a")
    env["PATH"] = str(fake_bin)
    response = lp.run_payload(payload(cwd=str(workdir), atm_identity="r1"), env)
    assert response["error"]["code"] == "CLI.NOT_FOUND"
    assert response["error"]["details"]["cli"] == "atm"


@pytest.mark.parametrize("output_format", ["text", "json"])
def test_non_zero_exit_reports_stderr_tail(fake_bin, tmp_path, workdir, output_format):
    response = run(
        fake_bin,
        tmp_path,
        {"exit_code": 3, "stderr": "something broke\n"},
        cwd=str(workdir),
        output_format=output_format,
    )
    assert response["success"] is False
    assert response["error"]["code"] == "CLI.NON_ZERO_EXIT"
    assert "something broke" in response["error"]["details"]["stderr_tail"]
    assert response["data"]["exit_code"] == 3


@pytest.mark.parametrize("tool", ["claude", "codex"])
def test_timeout_kills_child(fake_bin, tmp_path, tool):
    spec = {"sleep": 30, "stdout": "late"}
    if tool == "codex":
        spec["pre_stdout"] = json.dumps({"type": "thread.started", "thread_id": THREAD}) + "\n"
    response = run(
        fake_bin,
        tmp_path,
        spec,
        tool=tool,
        isolation={"tools": "none", "cwd": "temp"},
        timeout_seconds=1,
    )
    assert response["success"] is False
    assert response["error"]["code"] == "CLI.TIMEOUT"
    assert response["data"]["timed_out"] is True
    assert response["data"]["duration_seconds"] < 20
    if tool == "codex":
        assert response["data"]["session_id"] == THREAD
        assert response["error"]["details"]["partial_session_id"] == THREAD


def _pid_alive(pid):
    if os.name == "nt":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True
        ).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # pragma: no cover - pid reused by another user
        return True
    # A zombie still answers kill(0); treat an unreaped zombie as dead.
    try:
        stat = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout
    except OSError:  # pragma: no cover
        return True
    return bool(stat.strip()) and not stat.strip().startswith("Z")


def _wait_dead(pid, seconds=10.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.1)
    return False


@pytest.mark.parametrize("tool", ["claude", "codex"])
def test_timeout_kills_grandchildren_too(fake_bin, tmp_path, tool):
    pid_file = tmp_path / "grandchild.pid"
    response = run(
        fake_bin,
        tmp_path,
        {"sleep": 60, "spawn_pid_file": str(pid_file)},
        tool=tool,
        isolation={"tools": "none", "cwd": "temp"},
        timeout_seconds=2,
    )
    assert response["error"]["code"] == "CLI.TIMEOUT"
    grandchild = int(pid_file.read_text())
    assert _wait_dead(grandchild), f"grandchild {grandchild} survived the timeout kill"


@pytest.mark.skipif(os.name == "nt", reason="SIGTERM cannot be intercepted on Windows")
def test_sigterm_to_runtime_kills_child_tree_and_prints_envelope(fake_bin, tmp_path):
    pid_file = tmp_path / "grandchild.pid"
    env = make_env(fake_bin, tmp_path, {"sleep": 60, "spawn_pid_file": str(pid_file)})
    body = json.dumps(
        {"description": "d", "prompt": "p", "tool": "claude",
         "isolation": {"tools": "none", "cwd": "temp"}}
    )
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--json", body],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
        text=True, env=env,
    )
    deadline = time.monotonic() + 30
    while not pid_file.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert pid_file.exists()
    proc.send_signal(signal.SIGTERM)
    stdout, _ = proc.communicate(timeout=30)
    envelope = json.loads(stdout)
    assert envelope["success"] is False
    assert envelope["error"]["code"] == "RUNTIME.INTERRUPTED"
    assert _wait_dead(int(pid_file.read_text()))


def test_text_mode_timeout(fake_bin, tmp_path, workdir):
    response = run(fake_bin, tmp_path, {"sleep": 30}, cwd=str(workdir), timeout_seconds=1)
    assert response["error"]["code"] == "CLI.TIMEOUT"
    assert response["data"]["timed_out"] is True


@pytest.mark.parametrize(
    ("tool", "stdout"),
    [
        ("claude", "not json at all"),
        ("claude", "[1, 2]"),
        ("codex", "this is not jsonl\n"),
        ("claude", ""),
    ],
)
def test_unparseable_output(fake_bin, tmp_path, workdir, tool, stdout):
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool=tool, cwd=str(workdir), output_format="json")
    assert response["success"] is False
    assert response["error"]["code"] == "CLI.OUTPUT_UNPARSEABLE"


@pytest.mark.parametrize(
    ("tool", "stdout"),
    [
        ("claude", claude_json(session_id=None)),
        ("codex", codex_jsonl({"type": "item.completed", "item": {"type": "agent_message", "text": "x"}}, {"type": "turn.completed"})),
    ],
)
def test_missing_session_id(fake_bin, tmp_path, workdir, tool, stdout):
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool=tool, cwd=str(workdir), output_format="json")
    assert response["error"]["code"] == "CLI.SESSION_ID_MISSING"


def test_missing_result_text_keeps_session_id(fake_bin, tmp_path, workdir):
    stdout = codex_jsonl({"type": "thread.started", "thread_id": THREAD}, {"type": "turn.completed"})
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool="codex", cwd=str(workdir), output_format="json")
    assert response["error"]["code"] == "CLI.RESULT_MISSING"
    assert response["data"]["session_id"] == THREAD


@pytest.mark.parametrize(
    ("tool", "stderr"),
    [
        ("claude", "No conversation found with session ID: " + SESSION + "\n"),
        ("codex", "Error: thread/resume: thread/resume failed: no rollout found for thread id " + SESSION + " (code -32600)\n"),
    ],
)
def test_resume_unknown_session(fake_bin, tmp_path, workdir, tool, stderr):
    response = run(
        fake_bin,
        tmp_path,
        {"exit_code": 1, "stderr": stderr},
        tool=tool,
        cwd=str(workdir),
        resume_session_id=SESSION,
        isolation={"tools": "none"},
    )
    assert response["error"]["code"] == "CLI.RESUME_SESSION_NOT_FOUND"
    assert response["error"]["details"]["resume_session_id"] == SESSION
    assert stderr.strip() in response["error"]["details"]["stderr_tail"]


def test_claude_auth_failure_from_api_error_status(fake_bin, tmp_path, workdir):
    stdout = claude_json(is_error=True, api_error_status=401, result="Invalid API key")
    response = run(fake_bin, tmp_path, {"stdout": stdout, "exit_code": 1}, cwd=str(workdir), output_format="json")
    assert response["error"]["code"] == "CLI.AUTH_FAILED"
    assert response["data"]["session_id"] == SESSION


def test_codex_auth_failure_from_stderr(fake_bin, tmp_path, workdir):
    response = run(
        fake_bin,
        tmp_path,
        {"exit_code": 1, "stderr": "Error: unexpected status 401 Unauthorized\n"},
        tool="codex",
        cwd=str(workdir),
        output_format="json",
    )
    assert response["error"]["code"] == "CLI.AUTH_FAILED"


def test_codex_turn_failed_with_zero_exit_is_reported_error(fake_bin, tmp_path, workdir):
    stdout = codex_jsonl(
        {"type": "thread.started", "thread_id": THREAD},
        {"type": "turn.failed", "error": {"message": "model overloaded"}},
    )
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool="codex", cwd=str(workdir), output_format="json")
    assert response["error"]["code"] == "CLI.REPORTED_ERROR"
    assert response["error"]["details"]["reported_error"] == "model overloaded"
    assert response["data"]["session_id"] == THREAD


def test_claude_is_error_with_zero_exit_is_reported_error(fake_bin, tmp_path, workdir):
    stdout = claude_json(is_error=True, result="max turns reached", subtype="error_max_turns")
    response = run(fake_bin, tmp_path, {"stdout": stdout}, cwd=str(workdir), output_format="json")
    assert response["error"]["code"] == "CLI.REPORTED_ERROR"


def test_unknown_flag_is_reported_as_version_drift(fake_bin, tmp_path):
    response = run(
        fake_bin,
        tmp_path,
        {"exit_code": 1, "stderr": "Error: Unknown feature flag: code_mode_host\n"},
        tool="codex",
        isolation={"tools": "none", "cwd": "temp"},
    )
    error = response["error"]
    assert error["code"] == "CLI.UNSUPPORTED_FLAG"
    assert "code_mode_host" in error["message"]
    assert error["details"]["rejected"] == "code_mode_host"
    assert error["details"]["rejected_is_isolation_flag"] is True
    assert "code_mode_host" in error["suggested_action"]
    assert "never weakened" in error["suggested_action"]


def test_unknown_extra_arg_names_the_flag(fake_bin, tmp_path, workdir):
    response = run(
        fake_bin,
        tmp_path,
        {"exit_code": 1, "stderr": "error: unknown option '--bogus'\n"},
        cwd=str(workdir),
        output_format="json",
        extra_args=["--bogus"],
    )
    error = response["error"]
    assert error["code"] == "CLI.UNSUPPORTED_FLAG"
    assert error["details"]["rejected"] == "--bogus"
    assert error["details"]["rejected_is_isolation_flag"] is False
    assert "extra_args" in error["suggested_action"]


@pytest.mark.parametrize("bad", ["-x", "a b", "id;rm", "id&calc", "x\"y", "%PATH%"])
def test_resume_session_id_charset_is_restricted(bad):
    raw = json.dumps(
        {"description": "d", "prompt": "p", "tool": "codex", "cwd": "/tmp",
         "resume_session_id": bad, "isolation": {}}
    )
    assert lp.load_payload_result(raw).error.code == "VALIDATION.INVALID_PAYLOAD"


def test_temp_cwd_is_removed_when_launch_never_happens(fake_bin, tmp_path, monkeypatch):
    created = []
    real_mkdtemp = lp.tempfile.mkdtemp

    def mkdtemp(**kwargs):
        created.append(real_mkdtemp(**kwargs))
        return created[-1]

    monkeypatch.setattr(lp.tempfile, "mkdtemp", mkdtemp)
    env = make_env(fake_bin, tmp_path, {}, ATM_TEAM="team-a")
    env["PATH"] = str(fake_bin)  # no `atm` -> member registration fails
    response = lp.run_payload(
        payload(atm_identity="r1", isolation={"tools": "none", "cwd": "temp"}), env
    )
    assert response["error"]["code"] == "CLI.NOT_FOUND"
    assert created and not Path(created[0]).exists()


@pytest.mark.parametrize(
    "fields",
    [
        {"output_format": "json"},
        {"isolation": {"tools": "none"}},
        {"resume_session_id": SESSION, "isolation": {}},
    ],
)
def test_gemini_new_fields_are_typed_unsupported(fake_bin, tmp_path, workdir, fields):
    response = run(fake_bin, tmp_path, {}, tool="gemini", cwd=str(workdir), **fields)
    assert response["error"]["code"] == "CAPABILITY.UNSUPPORTED"
    assert not (tmp_path / "record.json").exists()


def test_invalid_cwd_is_reported_before_launch(fake_bin, tmp_path):
    response = run(fake_bin, tmp_path, {}, cwd=str(tmp_path / "missing"), output_format="json")
    assert response["error"]["code"] == "VALIDATION.INVALID_CWD"


# ---------------------------------------------------------------------------
# Direct script invocation contract (program -> subprocess -> one JSON envelope)
# ---------------------------------------------------------------------------


def _invoke(args, env, stdin=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_direct_invocation_with_json_argument(fake_bin, tmp_path):
    env = make_env(fake_bin, tmp_path, {"stdout": claude_json()})
    body = json.dumps(
        {
            "description": "direct",
            "prompt": "Answer",
            "tool": "claude",
            "model": "haiku",
            "isolation": {"tools": "none", "cwd": "temp"},
            "timeout_seconds": 30,
        }
    )
    proc = _invoke(["--json", body], env)
    assert proc.returncode == 0
    envelope = json.loads(proc.stdout)
    assert envelope["success"] is True
    assert envelope["data"]["session_id"] == SESSION


def test_direct_invocation_reads_payload_from_stdin(fake_bin, tmp_path):
    env = make_env(fake_bin, tmp_path, {"stdout": CODEX_OK})
    body = json.dumps(
        {
            "description": "direct",
            "prompt": "Answer",
            "tool": "codex",
            "isolation": {"tools": "none", "cwd": "temp"},
        }
    )
    proc = _invoke(["--json", "-"], env, stdin=body)
    assert proc.returncode == 0
    envelope = json.loads(proc.stdout)
    assert envelope["success"] is True, envelope
    assert envelope["data"]["result_text"] == "FINAL"


def test_direct_invocation_failure_still_exits_zero_with_envelope(tmp_path):
    proc = _invoke(["--json", "{not json"], dict(os.environ))
    assert proc.returncode == 0
    envelope = json.loads(proc.stdout)
    assert envelope["success"] is False
    assert envelope["error"]["code"] == "VALIDATION.INVALID_JSON"


# ---------------------------------------------------------------------------
# Large prompts (plan-anchor sends up to ~64 KB): stdin, never argv
# ---------------------------------------------------------------------------

LARGE_PROMPT = "State: " + json.dumps({"rows": ["x" * 90 + str(i) for i in range(500)]}) + "\nQ: \u00e9\u2713?"


@pytest.mark.parametrize(
    ("tool", "stdout"), [("claude", claude_json()), ("codex", CODEX_OK)]
)
def test_large_prompt_is_delivered_on_stdin(fake_bin, tmp_path, tool, stdout):
    assert len(LARGE_PROMPT.encode("utf-8")) > 40_000
    env = make_env(fake_bin, tmp_path, {"stdout": stdout})
    body = json.dumps(
        {"description": "big", "prompt": LARGE_PROMPT, "tool": tool,
         "isolation": {"tools": "none", "cwd": "temp"}, "timeout_seconds": 60}
    )
    proc = _invoke(["--json", "-"], env, stdin=body)
    envelope = json.loads(proc.stdout)
    assert envelope["success"] is True, envelope
    rec = recorded(tmp_path)
    assert rec["stdin"] == LARGE_PROMPT
    assert all(len(arg) < 1000 for arg in rec["argv"])


def test_large_prompt_on_resume_is_delivered_on_stdin(fake_bin, tmp_path, workdir):
    response = run(
        fake_bin,
        tmp_path,
        {"stdout": CODEX_OK},
        tool="codex",
        prompt=LARGE_PROMPT,
        cwd=str(workdir),
        resume_session_id=THREAD,
        isolation={"tools": "none", "cwd": "given"},
    )
    assert response["success"] is True, response
    rec = recorded(tmp_path)
    assert rec["stdin"] == LARGE_PROMPT
    assert rec["argv"][-2:] == [THREAD, "-"]


def test_stdin_payload_is_utf8_regardless_of_locale(fake_bin, tmp_path):
    env = make_env(fake_bin, tmp_path, {"stdout": claude_json()}, PYTHONIOENCODING="cp1252")
    body = json.dumps(
        {"description": "utf8", "prompt": "café ✓ 日本", "tool": "claude",
         "isolation": {"tools": "none", "cwd": "temp"}},
        ensure_ascii=False,
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", "-"],
        input=b"\xef\xbb\xbf" + body.encode("utf-8"),
        capture_output=True,
        env=env,
        timeout=60,
    )
    envelope = json.loads(proc.stdout.decode("utf-8"))
    assert envelope["success"] is True, envelope
    assert recorded(tmp_path)["stdin"] == "café ✓ 日本"
