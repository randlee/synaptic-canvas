"""Unit tests for the sc-launchpad modules: payload rules, models, command lines, parsers."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "packages" / "sc-launchpad" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import launchpad_commands as commands  # noqa: E402
import launchpad_output as output  # noqa: E402
from launchpad_models import LaunchFailure, LaunchpadInput, normalize_tool_model, roster_model  # noqa: E402
from launchpad_shared import build_child_env, resolve_teammate_mode  # noqa: E402

SESSION = "11111111-2222-4333-8444-555555555555"
ISOLATED = {"tools": "none", "cwd": "temp"}


def payload(**fields):
    base = {"description": "d", "prompt": "Answer the question", "tool": "claude", "cwd": "/tmp"}
    base.update(fields)
    if base.get("isolation", {}).get("cwd") == "temp":
        base.pop("cwd")
    return LaunchpadInput.model_validate({k: v for k, v in base.items() if v is not None})


# --- teammate mode -----------------------------------------------------------


@pytest.mark.parametrize(
    ("env", "identity", "expected"),
    [
        ({"ATM_TEAM": "t"}, None, (False, None, None)),
        ({}, "r1", (False, None, None)),
        ({"ATM_TEAM": "t"}, "r1", (True, "t", "r1")),
    ],
)
def test_teammate_mode_needs_team_and_identity(env, identity, expected):
    assert resolve_teammate_mode(env, identity) == expected


def test_teammate_mode_generates_identity_for_a_team_member_without_one(monkeypatch):
    import agent_identity

    monkeypatch.setattr(agent_identity.secrets, "choice", lambda pool: pool[0])
    monkeypatch.setattr(agent_identity.secrets, "token_hex", lambda nbytes: "0a0b")
    parent = {"ATM_TEAM": "t", "ATM_IDENTITY": "Parent-1234", "BEADS_ACTOR": "Parent-Actor"}
    # Team, no atm_identity: a new identity from the family's pool, never the parent's.
    assert resolve_teammate_mode(parent, None, "opus") == (True, "t", "Orion-0a0b")
    assert resolve_teammate_mode(parent, "  ", "sol") == (True, "t", "Smith-0a0b")
    # An explicit identity is used as given.
    assert resolve_teammate_mode(parent, "r1", "opus") == (True, "t", "r1")
    # No pool (isolation.tools='none'): nothing is generated, not a teammate.
    assert resolve_teammate_mode(parent, None, None) == (False, None, None)
    # No team: nothing is generated.
    assert resolve_teammate_mode({"ATM_IDENTITY": "Parent-1234"}, None, "opus") == (False, None, None)


def test_child_env_sets_or_clears_atm_vars():
    parent = {"ATM_TEAM": "t", "ATM_IDENTITY": "lead", "BEADS_ACTOR": "Parent-Actor", "KEEP": "1"}
    teammate = {"KEEP": "1", "ATM_TEAM": "t", "ATM_IDENTITY": "r1", "BEADS_ACTOR": "r1"}
    # Not teammate mode: the parent's identity and BEADS_ACTOR are dropped, its team is kept.
    assert build_child_env(parent, False, None, None) == {"KEEP": "1", "ATM_TEAM": "t"}
    assert build_child_env({"ATM_IDENTITY": "lead", "KEEP": "1"}, False, None, None) == {"KEEP": "1"}
    assert build_child_env({"BEADS_ACTOR": "Parent-Actor", "KEEP": "1"}, False, None, None) == {"KEEP": "1"}
    # Teammate mode: BEADS_ACTOR equals the registered ATM_IDENTITY.
    assert build_child_env({"KEEP": "1"}, True, "t", "r1") == teammate
    # Teammate mode replaces an inherited identity and BEADS_ACTOR with the registered one.
    assert build_child_env(parent, True, "t", "r1") == teammate


# --- payload rules -----------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {"resume_session_id": SESSION},  # resume needs explicit isolation
        {"resume_session_id": SESSION, "isolation": ISOLATED},
        {"isolation": {"cwd": "temp"}},  # temp cwd forbids an explicit cwd
        {"cwd": None},
        {"resume_session_id": SESSION, "isolation": {}, "output_format": "text"},
        {"isolation": {"tools": "some"}},
        {"isolation": {"network": "off"}},
        {"timeout_seconds": 0},
        {"resume_session_id": ""},
        {"session": "x"},
        {"isolation": {"tools": "none"}, "extra_args": ["--x"]},
        {"isolation": {"tools": "none"}, "atm_identity": "r1"},
    ],
)
def test_invalid_payloads_are_rejected(fields):
    with pytest.raises(ValueError):
        base = {"description": "d", "prompt": "p", "tool": "claude", "cwd": "/tmp"}
        base.update(fields)
        LaunchpadInput.model_validate({k: v for k, v in base.items() if v is not None})


@pytest.mark.parametrize("bad", ["-x", "a b", "id;rm", "id&calc", 'x"y', "%PATH%"])
def test_resume_session_id_charset_is_restricted(bad):
    with pytest.raises(ValueError):
        payload(tool="codex", resume_session_id=bad, isolation={})


def test_structured_output_defaults():
    assert payload().structured is False
    assert payload(isolation={}).structured is True
    assert payload(resume_session_id=SESSION, isolation={"tools": "none"}).structured is True
    assert payload(isolation={}, output_format="text").structured is False


# --- models ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tool", "model", "expected"),
    [
        ("claude", None, "claude-fable-5-1"),
        ("claude", "opus", "claude-opus-5-5"),
        ("claude", "claude-haiku-5-5", "claude-haiku-5-5"),
        ("claude", "fable[1m]", "claude-fable-5-1[1m]"),
        ("claude", "claude-opus-5-5[1m]", "claude-opus-5-5[1m]"),
        ("codex", None, "gpt-6.1-sol"),
        ("codex", "codex", "gpt-6.1-sol"),
        ("codex", "astra", "gpt-6-astra"),
        ("codex", "gpt-5.6-luna", "gpt-5.6-luna"),
        ("gemini", "gemini-2.5-pro", "gemini-2.5-pro"),
    ],
)
def test_normalize_tool_model(tool, model, expected):
    assert normalize_tool_model(payload(tool=tool, model=model)) == expected


@pytest.mark.parametrize(
    ("fields", "code"),
    [
        ({"model": "gpt-4"}, "VALIDATION.INVALID_MODEL"),
        ({"tool": "codex", "model": "max"}, "VALIDATION.INVALID_MODEL"),  # legacy alias is gone
        ({"model": "claude-sonnet-4-6"}, "VALIDATION.INVALID_MODEL"),  # ids outside the table
        ({"tool": "codex", "model": "sol[1m]"}, "VALIDATION.INVALID_MODEL"),  # 1M is claude-only
        ({"model": "haiku", "effort": "ultra"}, "VALIDATION.INVALID_EFFORT"),
        ({"effort": "extreme"}, "VALIDATION.INVALID_EFFORT"),
        ({"tool": "codex", "model": "luna", "effort": "ultra"}, "VALIDATION.INVALID_EFFORT"),
    ],
)
def test_bad_model_or_effort_is_a_typed_failure(fields, code):
    with pytest.raises(LaunchFailure) as exc:
        normalize_tool_model(payload(**fields))
    assert exc.value.code == code
    assert "Supported" in exc.value.message or "Use an alias" in exc.value.message


@pytest.mark.parametrize(
    ("tool", "model", "expected"),
    [
        ("claude", "claude-opus-5-5", "opus"),
        ("claude", "claude-fable-5-1[1m]", "fable[1m]"),
        ("codex", "gpt-6.1-sol", "sol"),
        ("codex", "gpt-6-sol", "gpt-6-sol"),  # no alias points at it
        ("gemini", "x", "gemini"),
    ],
)
def test_roster_model(tool, model, expected):
    assert roster_model(payload(tool=tool), model) == expected


# --- command lines -----------------------------------------------------------


def test_text_mode_commands_put_prompt_on_stdin():
    claude = commands.build_command(payload(extra_args=["--x"]), "claude-haiku-5-5")
    assert claude.argv == ["claude", "--print", "--dangerously-skip-permissions", "--model", "claude-haiku-5-5", "--x"]
    codex = commands.build_command(payload(tool="codex", extra_args=["--x"]), "gpt-5.6-terra")
    assert codex.argv == ["codex", "exec", "--yolo", "--model", "gpt-5.6-terra", "--x", "--", "-"]
    assert claude.stdin == codex.stdin == "Answer the question"


def test_effort_flags_are_unquoted():
    claude = commands.build_command(payload(effort="xhigh"), "claude-opus-5-5").argv
    assert claude[claude.index("--model"):][:4] == ["--model", "claude-opus-5-5", "--effort", "xhigh"]
    codex = commands.build_command(payload(tool="codex", effort="ultra"), "gpt-6.1-sol").argv
    assert codex[codex.index("--model"):][:4] == ["--model", "gpt-6.1-sol", "-c", "model_reasoning_effort=ultra"]
    commands.check_batch_shim("codex.cmd", codex)  # must not raise


def test_no_effort_passes_no_effort_flag():
    argv = commands.build_command(payload(tool="codex"), "gpt-6.1-sol").argv
    assert "-c" not in argv and "--effort" not in argv


def test_gemini_keeps_prompt_on_argv():
    command = commands.build_command(payload(tool="gemini", extra_args=["--y"]), "g")
    assert command.argv == ["gemini", "--yolo", "--prompt", "Answer the question", "--model", "g", "--y"]
    assert command.stdin is None


def test_claude_isolated_command():
    argv = commands.build_command(payload(isolation=ISOLATED, ephemeral=True), "claude-haiku-5-5").argv
    assert argv[:5] == ["claude", "--print", "--output-format", "stream-json", "--verbose"]
    assert "--dangerously-skip-permissions" not in argv
    assert argv[argv.index("--tools") + 1] == ""
    assert {"--strict-mcp-config", "--safe-mode", "--disable-slash-commands", "--no-session-persistence"} <= set(argv)


def test_claude_resume_with_default_tools_keeps_permissions_flag():
    argv = commands.build_command(payload(resume_session_id=SESSION, isolation={}), "claude-sonnet-5-5").argv
    assert argv[argv.index("--resume") + 1] == SESSION
    assert "--dangerously-skip-permissions" in argv and "--tools" not in argv


def test_codex_isolated_command_is_shim_safe():
    argv = commands.build_command(payload(tool="codex", isolation=ISOLATED, ephemeral=True), "gpt-6.1-sol").argv
    assert argv[:3] == ["codex", "exec", "--json"]
    assert "--yolo" not in argv and "--ephemeral" in argv
    assert {"--skip-git-repo-check", "sandbox_mode=read-only", "web_search=disabled"} <= set(argv)
    for feature in commands.CODEX_DISABLED_FEATURES:
        assert argv[argv.index(feature) - 1] == "--disable"
    assert argv[-2:] == ["--", "-"]
    commands.check_batch_shim("codex.cmd", argv)  # must not raise


def test_codex_resume_places_session_before_stdin_marker():
    argv = commands.build_command(payload(tool="codex", resume_session_id=SESSION, isolation={}), "gpt-6.1-sol").argv
    assert argv[:4] == ["codex", "exec", "resume", "--json"]
    assert "--yolo" in argv
    assert argv[-3:] == ["--", SESSION, "-"]


@pytest.mark.parametrize("arg", ['say "hi"', "a&b", "50%", "x|y", "^", "line\nbreak"])
def test_batch_shim_rejects_cmd_metacharacters(arg):
    with pytest.raises(LaunchFailure) as exc:
        commands.check_batch_shim(r"C:\bin\claude.CMD", ["claude", "--x", arg])
    assert exc.value.code == "CLI.UNSAFE_ARGUMENT" and exc.value.recoverable is False
    commands.check_batch_shim("/usr/local/bin/claude", ["claude", arg])  # native: fine


def test_codex_private_home_links_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(commands.tempfile, "tempdir", str(tmp_path))
    source = tmp_path / "real-codex"
    source.mkdir()
    (source / "auth.json").write_text("{}")
    home = commands.codex_private_home(tmp_path / "cwd", {"CODEX_HOME": str(source)})
    assert home.name.startswith(commands.CODEX_HOME_PREFIX)
    assert (home / "auth.json").read_text() == "{}"
    assert commands.codex_private_home(tmp_path / "cwd", {"CODEX_HOME": str(source)}) == home
    assert commands.codex_private_home(tmp_path / "other", {}) != home


# --- parsers -----------------------------------------------------------------


def lines(*events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


def test_claude_stream_parser_collects_tool_evidence():
    parsed = output.parse_claude(
        lines(
            {"type": "system", "subtype": "init", "session_id": SESSION, "tools": ["Bash"], "mcp_servers": []},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
            {"type": "result", "is_error": False, "result": "ok", "session_id": SESSION},
        )
    )
    assert (parsed.session_id, parsed.result_text, parsed.toolless_init) == (SESSION, "ok", False)
    assert parsed.tool_activity == ["init.tools:Bash", "tool_use:Bash"]


def test_codex_parser_flags_tool_items_and_keeps_last_message():
    parsed = output.parse_codex(
        lines(
            {"type": "thread.started", "thread_id": SESSION},
            {"type": "item.started", "item": {"type": "command_execution"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "a"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "b"}},
            {"type": "turn.completed"},
        )
    )
    assert (parsed.session_id, parsed.result_text) == (SESSION, "b")
    assert parsed.tool_activity == ["item:command_execution"]
