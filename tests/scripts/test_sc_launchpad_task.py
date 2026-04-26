"""Tests for the sc-launchpad runtime."""

from pathlib import Path
import importlib.util


spec = importlib.util.spec_from_file_location(
    "sc_launchpad_task",
    Path(__file__).parent.parent.parent
    / "packages"
    / "sc-launchpad"
    / "scripts"
    / "sc_launchpad_task.py",
)
sc_launchpad_task = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc_launchpad_task)


def test_resolve_teammate_mode_requires_both_team_and_identity():
    teammate_mode, team, identity = sc_launchpad_task.resolve_teammate_mode(
        {"ATM_TEAM": "annotations-test"},
        None,
    )
    assert teammate_mode is False
    assert team is None
    assert identity is None


def test_resolve_teammate_mode_enables_when_both_present():
    teammate_mode, team, identity = sc_launchpad_task.resolve_teammate_mode(
        {"ATM_TEAM": "annotations-test"},
        "reviewer-1",
    )
    assert teammate_mode is True
    assert team == "annotations-test"
    assert identity == "reviewer-1"


def test_build_child_env_clears_atm_vars_without_teammate_mode():
    env = sc_launchpad_task.build_child_env(
        {
            "ATM_TEAM": "annotations-test",
            "ATM_IDENTITY": "team-lead",
            "KEEP_ME": "yes",
        },
        False,
        None,
        None,
    )
    assert "ATM_TEAM" not in env
    assert "ATM_IDENTITY" not in env
    assert env["KEEP_ME"] == "yes"


def test_build_child_env_sets_both_atm_vars_in_teammate_mode():
    env = sc_launchpad_task.build_child_env(
        {"KEEP_ME": "yes"},
        True,
        "annotations-test",
        "reviewer-1",
    )
    assert env["ATM_TEAM"] == "annotations-test"
    assert env["ATM_IDENTITY"] == "reviewer-1"
    assert env["KEEP_ME"] == "yes"


def test_build_command_for_claude():
    payload = sc_launchpad_task.LaunchpadInput(
        description="Launch Claude",
        prompt="Review the diff",
        tool="claude",
        model="haiku",
        cwd="/tmp",
        extra_args=["--append-system-prompt", "Focus on tests"],
    )
    command = sc_launchpad_task.build_command(payload, "haiku")
    assert command == [
        "claude",
        "--dangerously-skip-permissions",
        "--print",
        "--model",
        "haiku",
        "--append-system-prompt",
        "Focus on tests",
        "Review the diff",
    ]


def test_build_command_for_codex():
    payload = sc_launchpad_task.LaunchpadInput(
        description="Launch Codex",
        prompt="Implement the fix",
        tool="codex",
        model="max",
        cwd="/tmp",
        extra_args=["--skip-git-repo-check"],
    )
    command = sc_launchpad_task.build_command(payload, "gpt-5.1-codex-max")
    assert command == [
        "codex",
        "exec",
        "--full-auto",
        "--model",
        "gpt-5.1-codex-max",
        "--skip-git-repo-check",
        "Implement the fix",
    ]


def test_build_command_for_gemini():
    payload = sc_launchpad_task.LaunchpadInput(
        description="Launch Gemini",
        prompt="Summarize the issue",
        tool="gemini",
        model="gemini-2.5-pro",
        cwd="/tmp",
        extra_args=["--output-format", "json"],
    )
    command = sc_launchpad_task.build_command(payload, "gemini-2.5-pro")
    assert command == [
        "gemini",
        "--yolo",
        "--prompt",
        "Summarize the issue",
        "--model",
        "gemini-2.5-pro",
        "--output-format",
        "json",
    ]


def test_roster_model_uses_tool_name_for_codex():
    payload = sc_launchpad_task.LaunchpadInput(
        description="Launch Codex",
        prompt="Implement the fix",
        tool="codex",
        cwd="/tmp",
    )
    assert sc_launchpad_task.roster_model(payload, "gpt-5.2-codex") == "codex"
