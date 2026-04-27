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


def test_build_claude_argv_without_tmux():
    command = sc_term_launch.build_claude_argv("sonnet", ["--continue"], teammate_mode=False)
    assert command == [
        "claude",
        "--model",
        "sonnet",
        "--dangerously-skip-permissions",
        "--continue",
    ]


def test_build_claude_argv_with_tmux():
    command = sc_term_launch.build_claude_argv(
        "haiku",
        ["--resume", "abc123"],
        teammate_mode=True,
    )
    assert command == [
        "claude",
        "--model",
        "haiku",
        "--dangerously-skip-permissions",
        "--teammate-mode",
        "tmux",
        "--resume",
        "abc123",
    ]


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


def test_resolve_identity_requires_value_when_atm_team_set(monkeypatch):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    with pytest.raises(SystemExit) as exc_info:
        sc_term_launch.resolve_identity(None)
    assert exc_info.value.code == 1


def test_resolve_identity_accepts_value_when_atm_team_set(monkeypatch):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    assert sc_term_launch.resolve_identity("alice") == "alice"


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
    launch_id, session_record = sc_term_launch.session_tracking_for_member_model("codex", "/tmp/project")
    assert launch_id is not None
    assert session_record is not None
    assert session_record.parent == Path("/tmp/project").resolve() / ".sc" / "sessions" / "codex"
    assert session_record.stem.endswith(launch_id)


def test_session_tracking_for_non_codex_member_model():
    launch_id, session_record = sc_term_launch.session_tracking_for_member_model("gemini", "/tmp/project")
    assert launch_id is None
    assert session_record is None


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
