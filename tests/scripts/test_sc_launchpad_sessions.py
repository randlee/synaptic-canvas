"""Runtime tests for sc-launchpad: sessions, isolation, cleanup, timeouts, typed failures.

Every launch runs fake `claude` / `codex` executables on PATH (a shebang script on
POSIX, a `.cmd` shim on Windows), so no real CLI, network, or credentials are used.
"""

import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "packages" / "sc-launchpad" / "scripts" / "sc_launchpad_task.py"
spec = importlib.util.spec_from_file_location("sc_launchpad_task_sessions", SCRIPT)
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)
import launchpad_process  # noqa: E402  (on sys.path once the runtime is loaded)

SESSION = "11111111-2222-4333-8444-555555555555"
THREAD = "01a14b21-8dde-7922-9867-dd61bf90ebf1"
ISOLATED = {"tools": "none", "cwd": "temp"}

FAKE_CLI = textwrap.dedent(
    """
    import json, os, re, subprocess, sys, threading
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
                    "atm_identity": os.environ.get("ATM_IDENTITY"),
                    "codex_home": os.environ.get("CODEX_HOME"),
                    "env_probe": {k: os.environ.get(k) for k in spec.get("env_probe", [])},
                },
                fh,
            )
    if spec.get("claude_transcripts"):
        projects = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "projects")
        os.makedirs(os.path.join(projects, re.sub(r"[^A-Za-z0-9]", "-", os.getcwd())))
    if spec.get("holder_port"):
        # A grandchild that would outlive us unless the whole tree is killed. It holds a
        # connection to the test, so the test sees readiness on accept and death as EOF.
        holder = (
            "import socket, threading; "
            f"s = socket.create_connection(('127.0.0.1', {spec['holder_port']})); "
            "s.sendall(b'ready'); threading.Event().wait(300)"
        )
        subprocess.Popen([sys.executable, "-c", holder], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if spec.get("pre_stdout"):
        sys.stdout.write(spec["pre_stdout"])
        sys.stdout.flush()
    if spec.get("block"):
        threading.Event().wait(300)  # outlives any test; bounded so a failed run leaks nothing
    sys.stdout.write(spec.get("stdout", ""))
    sys.stderr.write(spec.get("stderr", ""))
    sys.exit(spec.get("exit_code", 0))
    """
)


def jsonl(*events):
    return "\n".join(json.dumps(event) for event in events) + "\n"


def claude_init(session_id=SESSION, tools=(), mcp_servers=()):
    return {"type": "system", "subtype": "init", "session_id": session_id,
            "tools": list(tools), "mcp_servers": list(mcp_servers)}


def claude_result(**overrides):
    event = {"type": "result", "subtype": "success", "is_error": False, "session_id": SESSION,
             "result": '```json\n{"choice": "A"}\n```'}
    event.update(overrides)
    return event


def claude_stream(*middle, init=None, **result):
    return jsonl(init or claude_init(), *middle, claude_result(**result))


CLAUDE_OK = claude_stream()
CODEX_OK = jsonl(
    {"type": "thread.started", "thread_id": THREAD},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "thinking"}},
    {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": "FINAL"}},
    {"type": "turn.completed", "usage": {}},
)


@pytest.fixture(autouse=True)
def private_tmp(tmp_path, monkeypatch):
    """Temp cwds, codex homes, and audit logs land under tmp_path, never the real TMPDIR."""
    path = tmp_path / "tmp"
    path.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(path))
    return path


@pytest.fixture
def fake_bin(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = tmp_path / "fake_cli.py"
    script.write_text(FAKE_CLI, encoding="utf-8")
    for name in ("claude", "codex", "gemini"):
        if os.name == "nt":
            (bin_dir / f"{name}.cmd").write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
        else:
            target = bin_dir / name
            target.write_text(f"#!{sys.executable}\n" + FAKE_CLI, encoding="utf-8")
            target.chmod(0o755)
    return bin_dir


@pytest.fixture
def workdir(tmp_path):
    path = tmp_path / "work"
    path.mkdir()
    return path


def make_env(fake_bin, tmp_path, spec=None, **extra):
    env = dict(os.environ)
    for name in ("ATM_TEAM", "ATM_IDENTITY", "CODEX_HOME"):
        env.pop(name, None)
    tmp = str(tmp_path / "tmp")
    env.update(
        PATH=str(fake_bin) + os.pathsep + env.get("PATH", ""),
        FAKE_CLI_SPEC=json.dumps(spec or {}),
        FAKE_CLI_RECORD=str(tmp_path / "record.json"),
        CLAUDE_PROJECT_DIR=str(tmp_path / "project"),
        CLAUDE_CONFIG_DIR=str(tmp_path / "claude-config"),
        TMPDIR=tmp, TEMP=tmp, TMP=tmp,
    )
    env.update(extra)
    return env


def recorded(tmp_path):
    return json.loads((tmp_path / "record.json").read_text(encoding="utf-8"))


def payload(**fields):
    base = {"description": "test launch", "prompt": "Answer the question", "tool": "claude"}
    base.update(fields)
    return lp.LaunchpadInput.model_validate(base)


def run(fake_bin, tmp_path, spec, **fields):
    try:
        return lp.run_payload(payload(**fields), make_env(fake_bin, tmp_path, spec))
    except lp.LaunchFailure as failure:  # pre-launch failures; main() wraps these the same way
        return lp.envelope(None, failure)


def error_code(response):
    return response["error"]["code"] if response["error"] else None


# --- successful launches ------------------------------------------------------


def test_claude_isolated_turn(fake_bin, tmp_path, private_tmp):
    response = run(fake_bin, tmp_path, {"stdout": CLAUDE_OK, "claude_transcripts": True}, model="haiku", isolation=ISOLATED)
    assert response["success"] is True, response
    data = response["data"]
    assert (data["session_id"], data["result_text"]) == (SESSION, '```json\n{"choice": "A"}\n```')
    assert data["output_format"] == "json" and data["stdout"] is None
    assert data["isolation"]["tools"] == "none" and "--safe-mode" in data["isolation"]["flags"]
    rec = recorded(tmp_path)
    cwd = Path(data["cwd"])
    assert Path(rec["cwd"]).resolve() == cwd and rec["cwd_entries"] == []
    assert cwd.parent == private_tmp.resolve() and cwd.name.startswith("sc-launchpad-")
    assert rec["stdin"] == "Answer the question" and "Answer the question" not in rec["argv"]
    transcripts = lp.claude_project_dir(cwd, {"CLAUDE_CONFIG_DIR": str(tmp_path / "claude-config")})
    assert data["cleanup_paths"] == [str(cwd), str(transcripts)]


def test_claude_resume_in_given_cwd(fake_bin, tmp_path, workdir):
    response = run(fake_bin, tmp_path, {"stdout": claude_stream(result="because")},
                   cwd=str(workdir), resume_session_id=SESSION, isolation={"tools": "none", "cwd": "given"})
    assert response["success"] is True, response
    data = response["data"]
    assert (data["resumed_session_id"], data["result_text"], data["warnings"]) == (SESSION, "because", [])
    assert data["cleanup_paths"] == []
    rec = recorded(tmp_path)
    assert rec["argv"][rec["argv"].index("--resume") + 1] == SESSION
    assert Path(rec["cwd"]).resolve() == workdir.resolve()


def test_resume_reporting_new_session_id_adds_warning(fake_bin, tmp_path, workdir):
    other = "99999999-2222-4333-8444-555555555555"
    response = run(fake_bin, tmp_path, {"stdout": claude_stream(init=claude_init(other), session_id=other)},
                   cwd=str(workdir), resume_session_id=SESSION, isolation={})
    assert response["success"] is True and response["data"]["warnings"]


def test_codex_isolated_turn_uses_private_codex_home(fake_bin, tmp_path, private_tmp):
    real_home = tmp_path / "real-codex"
    real_home.mkdir()
    (real_home / "auth.json").write_text("{}")
    (real_home / "AGENTS.md").write_text("leak")
    env = make_env(fake_bin, tmp_path, {"stdout": CODEX_OK}, CODEX_HOME=str(real_home))
    response = lp.run_payload(payload(tool="codex", model="luna", isolation=ISOLATED), env)
    assert response["success"] is True, response
    data = response["data"]
    assert (data["session_id"], data["result_text"], data["model"]) == (THREAD, "FINAL", "gpt-6-luna")
    codex_home = Path(recorded(tmp_path)["codex_home"])
    assert codex_home.parent == private_tmp.resolve()
    assert sorted(p.name for p in codex_home.iterdir()) == ["auth.json"]
    assert data["cleanup_paths"] == [data["cwd"], str(codex_home)]
    assert recorded(tmp_path)["argv"][:2] == ["exec", "--json"]


def test_codex_resume_reuses_the_same_codex_home(fake_bin, tmp_path, workdir):
    first = run(fake_bin, tmp_path, {"stdout": CODEX_OK}, tool="codex", cwd=str(workdir), isolation={"tools": "none"})
    home = recorded(tmp_path)["codex_home"]
    second = run(fake_bin, tmp_path, {"stdout": CODEX_OK}, tool="codex", cwd=str(workdir),
                 resume_session_id=THREAD, isolation={"tools": "none"})
    assert first["success"] and second["success"], second
    rec = recorded(tmp_path)
    assert rec["codex_home"] == home
    assert rec["argv"][:3] == ["exec", "resume", "--json"] and rec["argv"][-3:] == ["--", THREAD, "-"]


def test_codex_default_tools_keep_the_users_codex_home(fake_bin, tmp_path, workdir):
    response = run(fake_bin, tmp_path, {"stdout": CODEX_OK}, tool="codex", cwd=str(workdir), isolation={})
    assert response["success"] is True and recorded(tmp_path)["codex_home"] is None


def test_codex_warnings_from_error_items_and_transient_errors(fake_bin, tmp_path, workdir):
    stdout = jsonl(
        {"type": "thread.started", "thread_id": THREAD},
        {"type": "item.completed", "item": {"type": "error", "message": "code mode fail closed"}},
        {"type": "error", "message": "Reconnecting... 1/5"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}},
        {"type": "turn.completed"},
    )
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool="codex", cwd=str(workdir), output_format="json")
    assert response["data"]["warnings"] == ["code mode fail closed", "Reconnecting... 1/5"]


@pytest.mark.parametrize(("tool", "flag"), [("claude", "--no-session-persistence"), ("codex", "--ephemeral")])
def test_ephemeral_flag(fake_bin, tmp_path, tool, flag):
    stdout = CLAUDE_OK if tool == "claude" else CODEX_OK
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool=tool, isolation=ISOLATED, ephemeral=True)
    assert response["success"] is True, response
    assert flag in recorded(tmp_path)["argv"]


def test_text_mode(fake_bin, tmp_path, workdir):
    response = run(fake_bin, tmp_path, {"stdout": "plain text\n"}, cwd=str(workdir), model="haiku")
    assert response["success"] is True
    data = response["data"]
    assert (data["stdout"], data["output_format"], data["session_id"]) == ("plain text\n", "text", None)
    rec = recorded(tmp_path)
    assert rec["argv"] == ["--print", "--dangerously-skip-permissions", "--model", "claude-haiku-5-5"]
    assert rec["stdin"] == "Answer the question"


@pytest.mark.parametrize(
    ("tool", "stdout", "flags"),
    [("claude", "ok\n", ["--effort", "max"]), ("codex", "ok\n", ["-c", "model_reasoning_effort=max"])],
)
def test_effort_reaches_the_cli(fake_bin, tmp_path, workdir, tool, stdout, flags):
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool=tool, cwd=str(workdir), effort="max")
    assert response["success"] is True, response
    assert response["data"]["effort"] == "max"
    argv = recorded(tmp_path)["argv"]
    assert argv[argv.index("--model") + 2:][:2] == flags


def test_audit_log_records_launch_without_prompt(fake_bin, tmp_path):
    env = make_env(fake_bin, tmp_path, {"stdout": CLAUDE_OK})
    body = json.dumps({"description": "d", "prompt": "SECRET-PROMPT", "tool": "claude", "isolation": ISOLATED})
    assert json.loads(_invoke(["--json", body], env).stdout)["success"] is True
    log = tmp_path / "project" / ".claude" / "state" / "logs" / "sc-launchpad" / "launch.jsonl"
    record = json.loads(log.read_text(encoding="utf-8"))
    assert (record["event"], record["package"], record["level"]) == ("launch", "sc-launchpad", "info")
    assert record["session_id"] == SESSION
    assert "SECRET-PROMPT" not in log.read_text(encoding="utf-8")


# --- env_file -------------------------------------------------------------------


def test_env_file_overrides_inherited_and_is_never_logged(fake_bin, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("ANTHROPIC_API_KEY=fresh-key-value\nSC_FROM_FILE='yes'\n", encoding="utf-8")
    env = make_env(fake_bin, tmp_path, {"stdout": CLAUDE_OK, "env_probe": ["ANTHROPIC_API_KEY", "SC_FROM_FILE"]},
                   ANTHROPIC_API_KEY="stale-key-value")
    body = json.dumps({"description": "d", "prompt": "p", "tool": "claude", "isolation": ISOLATED, "env_file": ".env"})
    response = json.loads(_invoke(["--json", body], env).stdout)
    assert response["success"] is True, response
    assert recorded(tmp_path)["env_probe"] == {"ANTHROPIC_API_KEY": "fresh-key-value", "SC_FROM_FILE": "yes"}
    assert response["data"]["env_file"] == str((project / ".env").resolve())
    assert response["data"]["env_keys"] == ["ANTHROPIC_API_KEY", "SC_FROM_FILE"]
    log = (project / ".claude" / "state" / "logs" / "sc-launchpad" / "launch.jsonl").read_text(encoding="utf-8")
    assert json.loads(log)["env_keys"] == ["ANTHROPIC_API_KEY", "SC_FROM_FILE"]
    assert "fresh-key-value" not in log and "fresh-key-value" not in json.dumps(response)


def test_env_file_found_in_main_checkout_from_linked_worktree(fake_bin, tmp_path):
    main = tmp_path / "repo"
    (main / ".git" / "worktrees" / "feat").mkdir(parents=True)
    (main / ".git" / "worktrees" / "feat" / "commondir").write_text("../..\n", encoding="utf-8")
    (main / ".env").write_text("SC_FROM_FILE=main\n", encoding="utf-8")
    linked = tmp_path / "wt" / "feat"
    linked.mkdir(parents=True)
    (linked / ".git").write_text(f"gitdir: {main / '.git' / 'worktrees' / 'feat'}\n", encoding="utf-8")
    response = run(fake_bin, tmp_path, {"stdout": CODEX_OK, "env_probe": ["SC_FROM_FILE"]},
                   tool="codex", cwd=str(linked), output_format="json", env_file=".env")
    assert response["success"] is True, response
    assert recorded(tmp_path)["env_probe"] == {"SC_FROM_FILE": "main"}


def test_launchpad_variables_win_over_env_file(fake_bin, tmp_path):
    real_home = tmp_path / "real-codex"
    real_home.mkdir()
    (real_home / "auth.json").write_text("{}", encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    (project / "creds.env").write_text(
        f"CODEX_HOME={real_home}\nATM_IDENTITY=from-file\nATM_TEAM=team-file\n", encoding="utf-8"
    )
    response = run(fake_bin, tmp_path, {"stdout": CODEX_OK}, tool="codex", isolation=ISOLATED, env_file="creds.env")
    assert response["success"] is True, response
    child = recorded(tmp_path)
    home = Path(child["codex_home"])
    assert home != real_home and (home / "auth.json").exists()  # private home, login taken from the file's
    # Not teammate mode: the identity is cleared, the team is kept.
    assert response["data"]["atm_identity"] is None
    assert child["atm_identity"] is None
    assert child["atm_team"] == "team-file"


def test_child_keeps_parent_team_but_never_its_identity(fake_bin, tmp_path, workdir):
    env = make_env(fake_bin, tmp_path, {"stdout": "ok\n"}, ATM_TEAM="team-a", ATM_IDENTITY="Parent-1234")
    env["PATH"] = str(fake_bin)  # no `atm`: any registration attempt would fail the launch
    response = lp.run_payload(payload(cwd=str(workdir)), env)
    assert response["success"] is True, response
    child = recorded(tmp_path)
    assert child["atm_team"] == "team-a"
    assert child["atm_identity"] is None
    assert response["data"]["teammate_mode"] is False


def test_missing_env_file_fails_before_launch(fake_bin, tmp_path, workdir):
    response = run(fake_bin, tmp_path, {"stdout": CLAUDE_OK}, cwd=str(workdir), env_file="nope.env")
    assert error_code(response) == "VALIDATION.ENV_FILE_NOT_FOUND"
    assert str(workdir / "nope.env") in response["error"]["details"]["searched"]
    assert not (tmp_path / "record.json").exists()


def test_without_env_file_the_environment_is_inherited_unchanged(fake_bin, tmp_path, workdir):
    (workdir / ".env").write_text("SC_FROM_FILE=should-not-load\n", encoding="utf-8")
    env = make_env(fake_bin, tmp_path, {"stdout": "ok\n", "env_probe": ["SC_FROM_FILE"]}, SC_FROM_FILE="inherited")
    response = lp.run_payload(payload(cwd=str(workdir)), env)
    assert response["success"] is True and response["data"]["env_file"] is None
    assert recorded(tmp_path)["env_probe"] == {"SC_FROM_FILE": "inherited"}


# --- isolation verification ---------------------------------------------------


@pytest.mark.parametrize(
    "stdout",
    [
        claude_stream(init=claude_init(tools=["Bash"])),
        claude_stream(init=claude_init(mcp_servers=[{"name": "fs", "status": "connected"}])),
        claude_stream({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read"}]}}),
        jsonl(claude_result()),  # no init event: tool-less run not proven
    ],
)
def test_claude_tools_under_no_tools_isolation_fail_closed(fake_bin, tmp_path, stdout):
    response = run(fake_bin, tmp_path, {"stdout": stdout}, isolation=ISOLATED)
    assert error_code(response) == "ISOLATION.VIOLATED"
    assert response["error"]["recoverable"] is False
    assert response["data"]["result_text"] is None


def test_codex_tool_item_under_no_tools_isolation_fails_closed(fake_bin, tmp_path):
    stdout = jsonl(
        {"type": "thread.started", "thread_id": THREAD},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "ls"}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
        {"type": "turn.completed"},
    )
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool="codex", isolation=ISOLATED)
    assert error_code(response) == "ISOLATION.VIOLATED"
    assert response["error"]["details"]["tool_activity"] == ["item:command_execution"]


def test_tool_activity_is_fine_without_no_tools_isolation(fake_bin, tmp_path, workdir):
    stdout = claude_stream(init=claude_init(tools=["Bash"]))
    assert run(fake_bin, tmp_path, {"stdout": stdout}, cwd=str(workdir), isolation={})["success"] is True


# --- typed failures -----------------------------------------------------------


def test_cli_not_found_lists_searched_path(tmp_path, workdir):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(lp.LaunchFailure) as exc:
        lp.run_payload(payload(cwd=str(workdir)), dict(os.environ, PATH=str(empty)))
    assert exc.value.code == "CLI.NOT_FOUND" and exc.value.details["searched_path"] == [str(empty)]


def test_temp_cwd_is_removed_when_no_child_starts(fake_bin, tmp_path, private_tmp):
    env = make_env(fake_bin, tmp_path, {}, ATM_TEAM="team-a")
    env["PATH"] = str(fake_bin)  # no `atm` -> member registration fails
    with pytest.raises(lp.LaunchFailure) as exc:
        lp.run_payload(payload(atm_identity="r1", isolation={"cwd": "temp"}), env)
    assert exc.value.code == "CLI.NOT_FOUND" and exc.value.details["cli"] == "atm"
    assert list(private_tmp.iterdir()) == []


@pytest.mark.parametrize("output_format", ["text", "json"])
def test_non_zero_exit_reports_tails(fake_bin, tmp_path, workdir, output_format):
    response = run(fake_bin, tmp_path, {"exit_code": 3, "stderr": "something broke\n", "stdout": "partial"},
                   cwd=str(workdir), output_format=output_format)
    assert error_code(response) == "CLI.NON_ZERO_EXIT"
    assert "something broke" in response["error"]["details"]["stderr_tail"]
    assert response["data"]["exit_code"] == 3
    if output_format == "json":
        assert response["error"]["details"]["stdout_tail"] == "partial"


# Timeout and stop tests never race a clock: the fake child blocks forever, so the
# timeout always fires, and tree-kill proofs wait on socket events, never on polling.
# GUARD only bounds a broken run; a passing run never waits on it.
GUARD = 60


@pytest.mark.parametrize("tool", ["claude", "codex"])
def test_timeout_reports_timed_out(fake_bin, tmp_path, workdir, tool):
    response = run(fake_bin, tmp_path, {"block": True}, tool=tool, cwd=str(workdir),
                   output_format="json", timeout_seconds=0.01)
    assert error_code(response) == "CLI.TIMEOUT" and response["data"]["timed_out"] is True


def test_text_mode_timeout(fake_bin, tmp_path, workdir):
    response = run(fake_bin, tmp_path, {"block": True}, cwd=str(workdir), timeout_seconds=0.01)
    assert error_code(response) == "CLI.TIMEOUT" and response["data"]["timed_out"] is True


@pytest.mark.parametrize("tool", ["claude", "codex"])
def test_timeout_keeps_partial_session_and_cleanup_paths(fake_bin, tmp_path, monkeypatch, tool):
    first = claude_init() if tool == "claude" else {"type": "thread.started", "thread_id": THREAD}
    timed_out = launchpad_process.ProcessOutcome(None, jsonl(first), "", True, 1.0)
    monkeypatch.setattr(lp, "run_process", lambda *args: timed_out)
    response = run(fake_bin, tmp_path, {}, tool=tool, isolation={"cwd": "temp"}, timeout_seconds=1)
    assert error_code(response) == "CLI.TIMEOUT"
    assert response["data"]["session_id"] == (SESSION if tool == "claude" else THREAD)
    assert response["data"]["cleanup_paths"] == [response["data"]["cwd"]]


@pytest.fixture
def holder_server():
    server = socket.create_server(("127.0.0.1", 0))
    server.settimeout(GUARD)
    yield server
    server.close()


def accept_holder(server):
    """Block until the grandchild is running; return its connection."""
    conn, _ = server.accept()
    conn.settimeout(GUARD)
    assert conn.makefile("rb").read(5) == b"ready"
    return conn


def assert_holder_dead(conn):
    """EOF (or a reset) on the grandchild's connection means its process is gone."""
    try:
        assert conn.recv(1) == b"", "grandchild survived the tree kill"
    except ConnectionResetError:
        pass
    finally:
        conn.close()


def test_timeout_kills_grandchildren_too(fake_bin, tmp_path, holder_server, monkeypatch):
    process = launchpad_process
    held = []

    class TimeoutOnceHolderIsUp(subprocess.Popen):
        """The first wait 'times out' only after the grandchild is up; no clock involved."""

        armed = True

        def communicate(self, input=None, timeout=None):
            if TimeoutOnceHolderIsUp.armed:
                TimeoutOnceHolderIsUp.armed = False
                held.append(accept_holder(holder_server))
                raise subprocess.TimeoutExpired(self.args, timeout)
            return super().communicate(input, timeout)

    monkeypatch.setattr(process.subprocess, "Popen", TimeoutOnceHolderIsUp)
    env = make_env(fake_bin, tmp_path, {"block": True, "holder_port": holder_server.getsockname()[1]})
    outcome = process.run_process([sys.executable, str(tmp_path / "fake_cli.py")], tmp_path, env, 1, None)
    assert outcome.timed_out is True
    assert_holder_dead(held[0])


@pytest.mark.skipif(os.name == "nt", reason="SIGTERM cannot be intercepted on Windows")
def test_sigterm_to_runtime_kills_child_tree_and_prints_envelope(fake_bin, tmp_path, holder_server):
    env = make_env(fake_bin, tmp_path, {"block": True, "holder_port": holder_server.getsockname()[1]})
    body = json.dumps({"description": "d", "prompt": "p", "tool": "claude", "isolation": ISOLATED})
    proc = subprocess.Popen([sys.executable, str(SCRIPT), "--json", body], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, env=env)
    try:
        conn = accept_holder(holder_server)  # the tree exists, so the stop handlers are installed
        proc.send_signal(signal.SIGTERM)
        envelope = json.loads(proc.communicate(timeout=GUARD)[0])
    finally:
        proc.kill()
    assert envelope["error"]["code"] == "RUNTIME.INTERRUPTED"
    assert_holder_dead(conn)


@pytest.mark.parametrize(
    ("tool", "stdout"),
    [("claude", "not json at all"), ("claude", "[1, 2]"), ("codex", "this is not jsonl\n"), ("claude", "")],
)
def test_unparseable_output(fake_bin, tmp_path, workdir, tool, stdout):
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool=tool, cwd=str(workdir), output_format="json")
    assert error_code(response) == "CLI.OUTPUT_UNPARSEABLE"


@pytest.mark.parametrize(
    ("tool", "stdout"),
    [
        ("claude", jsonl({"type": "system", "subtype": "init"}, {"type": "result", "result": "x"})),
        ("codex", jsonl({"type": "item.completed", "item": {"type": "agent_message", "text": "x"}}, {"type": "turn.completed"})),
    ],
)
def test_missing_session_id(fake_bin, tmp_path, workdir, tool, stdout):
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool=tool, cwd=str(workdir), output_format="json")
    assert error_code(response) == "CLI.SESSION_ID_MISSING"


def test_missing_result_text_keeps_session_id(fake_bin, tmp_path, workdir):
    stdout = jsonl({"type": "thread.started", "thread_id": THREAD}, {"type": "turn.completed"})
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool="codex", cwd=str(workdir), output_format="json")
    assert error_code(response) == "CLI.RESULT_MISSING" and response["data"]["session_id"] == THREAD


@pytest.mark.parametrize(
    ("tool", "stderr"),
    [
        ("claude", f"No conversation found with session ID: {SESSION}\n"),
        ("codex", f"Error: thread/resume failed: no rollout found for thread id {SESSION} (code -32600)\n"),
    ],
)
def test_resume_unknown_session(fake_bin, tmp_path, workdir, tool, stderr):
    response = run(fake_bin, tmp_path, {"exit_code": 1, "stderr": stderr}, tool=tool, cwd=str(workdir),
                   resume_session_id=SESSION, isolation={"tools": "none"})
    assert error_code(response) == "CLI.RESUME_SESSION_NOT_FOUND"
    assert response["error"]["details"]["resume_session_id"] == SESSION


@pytest.mark.parametrize(
    ("tool", "spec"),
    [
        ("claude", {"exit_code": 1, "stdout": claude_stream(is_error=True, api_error_status=401, result="Invalid API key")}),
        ("codex", {"exit_code": 1, "stderr": "Error: unexpected status 401 Unauthorized\n"}),
    ],
)
def test_auth_failure(fake_bin, tmp_path, workdir, tool, spec):
    response = run(fake_bin, tmp_path, spec, tool=tool, cwd=str(workdir), output_format="json")
    assert error_code(response) == "CLI.AUTH_FAILED"


@pytest.mark.parametrize(
    ("tool", "stdout", "reported"),
    [
        ("codex", jsonl({"type": "thread.started", "thread_id": THREAD},
                        {"type": "turn.failed", "error": {"message": "model overloaded"}}), "model overloaded"),
        ("claude", claude_stream(is_error=True, result="max turns reached"), "max turns reached"),
    ],
)
def test_error_reported_with_zero_exit(fake_bin, tmp_path, workdir, tool, stdout, reported):
    response = run(fake_bin, tmp_path, {"stdout": stdout}, tool=tool, cwd=str(workdir), output_format="json")
    assert error_code(response) == "CLI.REPORTED_ERROR"
    assert response["error"]["details"]["reported_error"] == reported
    assert response["data"]["session_id"]


def test_rejected_isolation_flag_is_version_drift(fake_bin, tmp_path):
    response = run(fake_bin, tmp_path, {"exit_code": 1, "stderr": "Error: Unknown feature flag: code_mode_host\n"},
                   tool="codex", isolation=ISOLATED)
    error = response["error"]
    assert error["code"] == "CLI.UNSUPPORTED_FLAG"
    assert error["details"]["rejected"] == "code_mode_host" and error["details"]["rejected_is_isolation_flag"]
    assert "never weakened" in error["suggested_action"]


def test_rejected_extra_arg_names_the_flag(fake_bin, tmp_path, workdir):
    response = run(fake_bin, tmp_path, {"exit_code": 1, "stderr": "error: unknown option '--bogus'\n"},
                   cwd=str(workdir), output_format="json", extra_args=["--bogus"])
    error = response["error"]
    assert error["details"]["rejected"] == "--bogus" and not error["details"]["rejected_is_isolation_flag"]
    assert "extra_args" in error["suggested_action"]


@pytest.mark.parametrize(
    "fields",
    [{"output_format": "json"}, {"isolation": {"tools": "none"}}, {"resume_session_id": SESSION, "isolation": {}},
     {"ephemeral": True}, {"effort": "high"}],
)
def test_gemini_session_fields_are_typed_unsupported(fake_bin, tmp_path, workdir, fields):
    response = run(fake_bin, tmp_path, {}, tool="gemini", cwd=str(workdir), **fields)
    assert error_code(response) == "CAPABILITY.UNSUPPORTED"
    assert not (tmp_path / "record.json").exists()


def test_invalid_cwd_is_reported_before_launch(fake_bin, tmp_path):
    response = run(fake_bin, tmp_path, {}, cwd=str(tmp_path / "missing"), output_format="json")
    assert error_code(response) == "VALIDATION.INVALID_CWD"


# --- direct invocation: one JSON envelope, exit 0 -----------------------------


def _invoke(args, env, stdin=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True,
                          env=env, timeout=60)


LARGE_PROMPT = "State: " + json.dumps({"rows": ["x" * 90 + str(i) for i in range(500)]}) + "\nQ: café ✓ 日本?"


@pytest.mark.parametrize(("tool", "stdout"), [("claude", CLAUDE_OK), ("codex", CODEX_OK)])
def test_large_utf8_prompt_from_stdin_payload_reaches_child_stdin(fake_bin, tmp_path, tool, stdout):
    assert len(LARGE_PROMPT.encode("utf-8")) > 40_000
    env = make_env(fake_bin, tmp_path, {"stdout": stdout}, PYTHONIOENCODING="cp1252")
    body = json.dumps({"description": "big", "prompt": LARGE_PROMPT, "tool": tool, "isolation": ISOLATED},
                      ensure_ascii=False)
    proc = _invoke(["--json", "-"], env, stdin=b"\xef\xbb\xbf" + body.encode("utf-8"))
    assert proc.returncode == 0
    assert json.loads(proc.stdout.decode("utf-8"))["success"] is True
    rec = recorded(tmp_path)
    assert rec["stdin"] == LARGE_PROMPT and all(len(arg) < 1000 for arg in rec["argv"])


def test_json_argument_payload(fake_bin, tmp_path):
    body = json.dumps({"description": "d", "prompt": "p", "tool": "claude", "isolation": ISOLATED})
    proc = _invoke(["--json", body], make_env(fake_bin, tmp_path, {"stdout": CLAUDE_OK}))
    assert json.loads(proc.stdout)["data"]["session_id"] == SESSION


@pytest.mark.parametrize(("args", "code"), [(["--json", "{not json"], "VALIDATION.INVALID_JSON"),
                                            (["--json"], "VALIDATION.MISSING_INPUT")])
def test_invalid_input_still_exits_zero_with_envelope(tmp_path, args, code):
    proc = _invoke(args, dict(os.environ, CLAUDE_PROJECT_DIR=str(tmp_path)), stdin=b"")
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["error"]["code"] == code
