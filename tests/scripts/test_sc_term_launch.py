"""Tests for the sc-launch-term terminal launcher."""

from pathlib import Path
import importlib.util

import pytest


spec = importlib.util.spec_from_file_location(
    "sc_term_launch",
    Path(__file__).parent.parent.parent
    / "packages"
    / "sc-launch-term"
    / "scripts"
    / "sc-term-launch.py",
)
sc_term_launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc_term_launch)


def claude_spec(name):
    return sc_term_launch.agent_models.resolve_model("claude", name)


def codex_spec(name):
    return sc_term_launch.agent_models.resolve_model("codex", name)


def test_build_claude_argv_without_tmux():
    command = sc_term_launch.build_claude_argv(
        claude_spec("sonnet"), None, ["--continue"], teammate_mode=False
    )
    assert command == [
        "claude",
        "--model",
        "claude-sonnet-5-5",
        "--dangerously-skip-permissions",
        "--continue",
    ]


def test_build_claude_argv_with_tmux_and_effort():
    command = sc_term_launch.build_claude_argv(
        claude_spec("haiku"),
        "high",
        ["--resume", "abc123"],
        teammate_mode=True,
    )
    assert command == [
        "claude",
        "--model",
        "claude-haiku-5-5",
        "--effort",
        "high",
        "--dangerously-skip-permissions",
        "--teammate-mode",
        "tmux",
        "--resume",
        "abc123",
    ]


@pytest.mark.parametrize(
    ("model", "model_id"),
    [
        ("sol", "gpt-6.1-sol"),
        ("astra", "gpt-6-astra"),
        ("terra", "gpt-5.6-terra"),
        ("luna", "gpt-6-luna"),
        ("codex", "gpt-6.1-sol"),
        ("gpt-5.6-luna", "gpt-5.6-luna"),
    ],
)
def test_build_codex_argv_routes_models(model, model_id):
    command = sc_term_launch.build_codex_argv(codex_spec(model), None, ["--search"])
    assert command == [
        "codex",
        "--model",
        model_id,
        "--yolo",
        "--enable",
        "hooks",
        "--search",
    ]


def test_build_codex_argv_passes_effort_unquoted():
    command = sc_term_launch.build_codex_argv(codex_spec("astra"), "ultra", [])
    assert command[:5] == ["codex", "--model", "gpt-6-astra", "-c", "model_reasoning_effort=ultra"]


@pytest.mark.parametrize(
    ("tool", "model", "label", "model_id"),
    [
        ("claude", "fable", "fable", "claude-fable-5-1"),
        ("claude", "claude-opus-5-5", "opus", "claude-opus-5-5"),
        ("codex", "codex", "sol", "gpt-6.1-sol"),
        ("codex", "gpt-6-sol", "gpt-6-sol", "gpt-6-sol"),
    ],
)
def test_resolve_model_labels(tool, model, label, model_id):
    spec, got = sc_term_launch.resolve_model(tool, model, None)
    assert (got, spec.id) == (label, model_id)


def test_resolve_model_rejects_unsupported_effort(capsys):
    with pytest.raises(SystemExit):
        sc_term_launch.resolve_model("codex", "luna", "ultra")
    assert "Supported: low, medium, high, xhigh, max" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("tool", "label", "family"),
    [("claude", "opus", "opus"), ("claude", "claude-opus-5-5", "opus"), ("codex", "gpt-6-sol", "sol")],
)
def test_identity_family(tool, label, family):
    assert sc_term_launch.identity_family(tool, label) == family


def test_model_choices_come_from_shared_table():
    agent_models = sc_term_launch.agent_models
    assert set(sc_term_launch.CODEX_MODELS) == set(agent_models.ALIASES["codex"]) | set(agent_models.MODELS["codex"])
    assert set(sc_term_launch.CLAUDE_MODELS) == set(agent_models.ALIASES["claude"]) | set(agent_models.MODELS["claude"])
    for alias in agent_models.ALIASES["codex"]:
        if alias != "codex":
            assert alias in sc_term_launch._IDENTITY_NAMES, f"add an identity pool for {alias}"
    for alias in agent_models.ALIASES["claude"]:
        assert alias in sc_term_launch._IDENTITY_NAMES, f"add an identity pool for {alias}"


def test_render_command_argv_posix_quotes_spaces():
    command = sc_term_launch.render_command_argv(
        ["claude", "--model", "opus", "--resume", "session with spaces"],
        "wezterm",
    )
    assert command == "claude --model opus --resume 'session with spaces'"


def test_render_command_argv_powershell_quotes_spaces():
    command = sc_term_launch.render_command_argv(
        ["claude", "--model", "sonnet", "--resume", "session with spaces"],
        "wt",
    )
    assert command == "& 'claude' '--model' 'sonnet' '--resume' 'session with spaces'"


def test_parser_collects_passthrough_claude_args():
    argv, passthrough = sc_term_launch.split_passthrough_argv(
        [
            "launch-claude-model",
            "sonnet",
            "/tmp/project",
            "--terminal",
            "wezterm",
            "--",
            "--continue",
            "--resume",
            "abc123",
        ]
    )
    parser = sc_term_launch.build_parser()
    args = parser.parse_args(argv)
    assert args.subcommand == "launch-claude-model"
    assert args.model == "sonnet"
    assert args.dir == "/tmp/project"
    assert args.terminal == "wezterm"
    assert passthrough == ["--continue", "--resume", "abc123"]


def test_parser_collects_passthrough_codex_args():
    argv, passthrough = sc_term_launch.split_passthrough_argv(
        [
            "launch-codex-model",
            "sol",
            "/tmp/project",
            "--terminal",
            "cmux",
            "--",
            "--search",
        ]
    )
    parser = sc_term_launch.build_parser()
    args = parser.parse_args(argv)
    assert args.subcommand == "launch-codex-model"
    assert args.model == "sol"
    assert args.effort is None
    assert args.dir == "/tmp/project"
    assert args.terminal == "cmux"
    assert passthrough == ["--search"]


def test_apply_atm_env_prefix_posix():
    command = sc_term_launch.apply_atm_env_prefix(
        "claude --model sonnet",
        "wezterm",
        "annotations-test",
        "alice",
    )
    assert (
        command
        == "export ATM_TEAM=annotations-test && export ATM_IDENTITY=alice && claude --model sonnet"
    )


def test_apply_atm_env_prefix_powershell():
    command = sc_term_launch.apply_atm_env_prefix(
        "& 'claude' '--model' 'sonnet'",
        "wt",
        "annotations-test",
        "alice",
    )
    assert (
        command
        == "$env:ATM_TEAM = 'annotations-test'; $env:ATM_IDENTITY = 'alice'; & 'claude' '--model' 'sonnet'"
    )


def test_resolve_identity_generates_random_when_omitted(monkeypatch):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    identity = sc_term_launch.resolve_identity(None)
    assert identity is not None
    assert len(identity) > 0


def test_resolve_identity_accepts_value_when_atm_team_set(monkeypatch):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    assert sc_term_launch.resolve_identity("alice") == "alice"


def test_resolve_identity_uses_tool_pool(monkeypatch):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    identity = sc_term_launch.resolve_identity(None, "gemini")
    name, suffix = identity.rsplit("-", 1)
    assert name in sc_term_launch._IDENTITY_NAMES["gemini"]
    assert len(suffix) == 4


@pytest.mark.parametrize("model", ["sol", "astra", "terra", "luna", "codex"])
def test_resolve_identity_uses_codex_model_pool(monkeypatch, model):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    identity = sc_term_launch.resolve_identity(None, model)
    name, suffix = identity.rsplit("-", 1)
    pool_model = "sol" if model == "codex" else model
    assert name in sc_term_launch._IDENTITY_NAMES[pool_model]
    assert len(suffix) == 4


def test_generate_ulid_and_session_path():
    launch_id = sc_term_launch.generate_ulid()
    path = sc_term_launch.build_claude_session_record_path("/tmp/project", launch_id)
    assert len(launch_id) == 26
    assert path.parent == Path("/tmp/project").resolve() / ".sc" / "sessions" / "claude"
    assert path.stem.endswith(launch_id)


def test_generate_codex_session_path():
    launch_id = sc_term_launch.generate_ulid()
    path = sc_term_launch.build_codex_session_record_path("/tmp/project", launch_id)
    assert path.parent == Path("/tmp/project").resolve() / ".sc" / "sessions" / "codex"
    assert path.stem.endswith(launch_id)


def test_session_tracking_for_codex_member_model():
    launch_id, session_record = sc_term_launch.session_tracking_for_member_model(
        "codex", "/tmp/project"
    )
    assert launch_id is not None
    assert session_record is not None
    assert (
        session_record.parent
        == Path("/tmp/project").resolve() / ".sc" / "sessions" / "codex"
    )
    assert session_record.stem.endswith(launch_id)


def test_session_tracking_for_non_codex_member_model():
    launch_id, session_record = sc_term_launch.session_tracking_for_member_model(
        "gemini", "/tmp/project"
    )
    assert launch_id is None
    assert session_record is None


def test_session_tracking_for_codex_model_alias():
    launch_id, session_record = sc_term_launch.session_tracking_for_member_model(
        "sol", "/tmp/project"
    )
    assert launch_id is not None
    assert session_record is not None
    assert (
        session_record.parent
        == Path("/tmp/project").resolve() / ".sc" / "sessions" / "codex"
    )


def test_apply_env_prefix_with_session_tracking_posix():
    command = sc_term_launch.apply_env_prefix(
        "claude --model haiku",
        "ghostty",
        {
            "SC_LAUNCH_ID": "01JVY7YVYH57FHE2S2P0S8F3XW",
            "SC_SESSION_RECORD": "/tmp/project/.sc/sessions/claude/session.json",
        },
    )
    assert (
        command
        == "export SC_LAUNCH_ID=01JVY7YVYH57FHE2S2P0S8F3XW && export SC_SESSION_RECORD=/tmp/project/.sc/sessions/claude/session.json && claude --model haiku"
    )


def test_launch_cmux_creates_focused_workspace(monkeypatch):
    calls = []

    def fake_run(command, *, check):
        calls.append((command, check))

    monkeypatch.setattr(sc_term_launch.subprocess, "run", fake_run)
    sc_term_launch.launch_cmux("claude --model fable", "/tmp/project", True, "fable")

    assert calls == [
        (
            [
                "cmux",
                "new-workspace",
                "--cwd",
                "/tmp/project",
                "--name",
                "fable",
                "--command",
                "claude --model fable",
                "--focus",
                "true",
            ],
            True,
        )
    ]
