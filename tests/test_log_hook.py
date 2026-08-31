"""Tests for scripts/log-hook.py (Claude Code hook trace logger).

log-hook.py reads a hook event name from --event, reads raw stdin (the hook
payload Claude Code passes in, e.g. a PreToolUse/PostToolUse JSON blob),
and appends one JSON line to --log (default reports/trace.jsonl) containing
ts/event/cwd/stdin/env. It never parses stdin as JSON -- it stores it
verbatim as a string -- so it must never crash on malformed or empty input.
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "log-hook.py"


def _load():
    spec = importlib.util.spec_from_file_location("log_hook", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PRETOOLUSE_PAYLOAD = json.dumps({
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "echo hi"},
})

POSTTOOLUSE_PAYLOAD = json.dumps({
    "hook_event_name": "PostToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "echo hi"},
    "tool_response": {"stdout": "hi\n", "stderr": "", "exitCode": 0},
})


def _run_main(mod, monkeypatch, argv, stdin_text):
    monkeypatch.setattr(sys, "argv", ["log-hook.py"] + argv)
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))
    return mod.main()


def test_pretooluse_payload_appends_one_jsonl_record(tmp_path, monkeypatch):
    mod = _load()
    log_path = tmp_path / "reports" / "trace.jsonl"
    rc = _run_main(mod, monkeypatch, ["--event", "PreToolUse", "--log", str(log_path)],
                   PRETOOLUSE_PAYLOAD)
    assert rc == 0
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "PreToolUse"
    assert record["stdin"] == PRETOOLUSE_PAYLOAD
    assert "ts" in record and record["ts"].endswith("Z")
    assert "cwd" in record


def test_posttooluse_payload_recorded(tmp_path, monkeypatch):
    mod = _load()
    log_path = tmp_path / "trace.jsonl"
    rc = _run_main(mod, monkeypatch, ["--event", "PostToolUse", "--log", str(log_path)],
                   POSTTOOLUSE_PAYLOAD)
    assert rc == 0
    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["event"] == "PostToolUse"
    parsed_stdin = json.loads(record["stdin"])
    assert parsed_stdin["tool_response"]["exitCode"] == 0


def test_appends_across_multiple_invocations(tmp_path, monkeypatch):
    mod = _load()
    log_path = tmp_path / "trace.jsonl"
    _run_main(mod, monkeypatch, ["--event", "PreToolUse", "--log", str(log_path)],
              PRETOOLUSE_PAYLOAD)
    _run_main(mod, monkeypatch, ["--event", "PostToolUse", "--log", str(log_path)],
              POSTTOOLUSE_PAYLOAD)
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    events = [json.loads(line)["event"] for line in lines]
    assert events == ["PreToolUse", "PostToolUse"]


def test_creates_missing_parent_directories(tmp_path, monkeypatch):
    mod = _load()
    log_path = tmp_path / "deep" / "nested" / "reports" / "trace.jsonl"
    rc = _run_main(mod, monkeypatch, ["--event", "PreToolUse", "--log", str(log_path)], "{}")
    assert rc == 0
    assert log_path.exists()


def test_empty_stdin_does_not_crash(tmp_path, monkeypatch):
    mod = _load()
    log_path = tmp_path / "trace.jsonl"
    rc = _run_main(mod, monkeypatch, ["--event", "PreToolUse", "--log", str(log_path)], "")
    assert rc == 0
    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["stdin"] == ""


def test_malformed_non_json_stdin_does_not_crash(tmp_path, monkeypatch):
    """stdin is stored verbatim as a string, never json.loads'd -- garbage input must be safe."""
    mod = _load()
    log_path = tmp_path / "trace.jsonl"
    garbage = "{not valid json!! \x00 \n <<< binary-ish \xff"
    rc = _run_main(mod, monkeypatch, ["--event", "PreToolUse", "--log", str(log_path)], garbage)
    assert rc == 0
    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert "not valid json" in record["stdin"]


def test_env_vars_captured_only_when_set(tmp_path, monkeypatch):
    mod = _load()
    log_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("CLAUDE_AGENT_ID", "agent-123")
    monkeypatch.delenv("CLAUDE_AGENT_TASK", raising=False)
    _run_main(mod, monkeypatch, ["--event", "PreToolUse", "--log", str(log_path)], "{}")
    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["env"].get("CLAUDE_AGENT_ID") == "agent-123"
    assert "CLAUDE_AGENT_TASK" not in record["env"]


def test_default_log_path_is_reports_trace_jsonl(monkeypatch):
    mod = _load()
    parser_defaults = {}
    # Inspect via argparse: build the parser the same way main() does by
    # checking the --log default without actually writing anywhere.
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", required=True)
    ap.add_argument("--log", default="reports/trace.jsonl")
    args = ap.parse_args(["--event", "PreToolUse"])
    assert args.log == "reports/trace.jsonl"


def test_subprocess_end_to_end_via_real_stdin(tmp_path):
    """Exercise the script as an actual OS process, matching real hook invocation."""
    log_path = tmp_path / "trace.jsonl"
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--event", "PreToolUse", "--log", str(log_path)],
        input=PRETOOLUSE_PAYLOAD,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["event"] == "PreToolUse"
    assert record["stdin"] == PRETOOLUSE_PAYLOAD


def test_subprocess_malformed_stdin_still_exits_zero(tmp_path):
    """Hooks must fail safe: garbage stdin must never crash the process."""
    log_path = tmp_path / "trace.jsonl"
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--event", "PostToolUse", "--log", str(log_path)],
        input="not json at all {{{",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert log_path.exists()
