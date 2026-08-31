"""
Unit tests for Codex parity: environment provisioning, event mapping, and
runner routing.

Covers:
- Model alias resolution / codex-model detection (environment.MODEL_ALIASES)
- CODEX_HOME provisioning (setup_codex_home / setup_test_environment)
- ZDOTDIR provisioning for Codex's login-shell PATH control
- AGENTS.md generation (Codex's Skill-tool parity mechanism)
- IsolatedSession.run_codex_command (subprocess construction, trace capture)
- Codex JSONL event -> CollectedData mapping (collector.py)
- TestRunner routing a gpt-*/luna/sol/terra model through the codex path
  while leaving the Claude path byte-identical
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness.collector import (
    ClaudeResponseText,
    CollectedData,
    CorrelatedToolCall,
    DataCollector,
    build_collected_data_from_codex_events,
    parse_codex_events,
)
from harness.environment import (
    CODEX_DIR,
    MODEL_ALIASES,
    cleanup_test_environment,
    create_isolated_home,
    is_codex_model,
    provision_codex_zdot,
    resolve_model,
    setup_codex_home,
    setup_test_environment,
    write_codex_agents_md,
)


# A representative recorded JSONL sample from `codex exec --json`, covering
# command_execution, agent_message, and turn.completed (usage) events.
CODEX_EVENTS_SAMPLE = "\n".join(
    [
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "id": "item-1",
                    "type": "command_execution",
                    "command": "ls -la",
                    "aggregated_output": "total 0\ndrwxr-xr-x  2 user  staff  64 Jan 1 00:00 .\n",
                    "exit_code": 0,
                },
            }
        ),
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "id": "item-2",
                    "type": "command_execution",
                    "command": "false",
                    "aggregated_output": "",
                    "exit_code": 1,
                },
            }
        ),
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "id": "item-3",
                    "type": "agent_message",
                    "text": "I listed the files and confirmed the failing command.",
                },
            }
        ),
        json.dumps(
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 45,
                    "cached_input_tokens": 10,
                },
            }
        ),
    ]
)


# =============================================================================
# Alias resolution
# =============================================================================


class TestModelAliasResolution:
    """Tests for resolve_model / is_codex_model."""

    def test_known_aliases_resolve(self):
        assert resolve_model("luna") == "gpt-5.6-luna"
        assert resolve_model("sol") == "gpt-5.6-sol"
        assert resolve_model("terra") == "gpt-5.6-terra"

    def test_unknown_alias_passes_through(self):
        assert resolve_model("haiku") == "haiku"
        assert resolve_model("gpt-5.6-luna") == "gpt-5.6-luna"

    def test_alias_table_matches_ecosystem_convention(self):
        # Mirrors scripts/run-evals-local.py's MODEL_ALIASES table.
        assert MODEL_ALIASES == {
            "luna": "gpt-5.6-luna",
            "sol": "gpt-5.6-sol",
            "terra": "gpt-5.6-terra",
        }

    def test_is_codex_model_true_for_gpt_and_aliases(self):
        assert is_codex_model("gpt-5.6-luna") is True
        assert is_codex_model("luna") is True
        assert is_codex_model("sol") is True
        assert is_codex_model("terra") is True

    def test_is_codex_model_false_for_claude_models(self):
        assert is_codex_model("haiku") is False
        assert is_codex_model("sonnet") is False
        assert is_codex_model("opus") is False


# =============================================================================
# CODEX_HOME provisioning
# =============================================================================


class TestSetupCodexHome:
    """Tests for setup_codex_home."""

    def test_creates_codex_home_directory(self):
        home = create_isolated_home()
        try:
            codex_home = setup_codex_home(home)
            assert codex_home == home / CODEX_DIR
            assert codex_home.exists()
            assert codex_home.is_dir()
        finally:
            cleanup_test_environment(home, force=True)

    def test_copies_auth_from_source_home(self):
        home = create_isolated_home()
        try:
            with tempfile.TemporaryDirectory() as source_dir:
                source_home = Path(source_dir)
                source_codex = source_home / ".codex"
                source_codex.mkdir(parents=True)
                (source_codex / "auth.json").write_text('{"token": "abc"}')

                codex_home = setup_codex_home(home, source_home=source_home)

                assert (codex_home / "auth.json").exists()
                assert (codex_home / "auth.json").read_text() == '{"token": "abc"}'
        finally:
            cleanup_test_environment(home, force=True)

    def test_missing_source_auth_still_creates_dir(self):
        home = create_isolated_home()
        try:
            codex_home = setup_codex_home(
                home, source_home=Path("/nonexistent/source/home")
            )
            assert codex_home.exists()
            assert not (codex_home / "auth.json").exists()
        finally:
            cleanup_test_environment(home, force=True)


class TestSetupTestEnvironmentCodexHome:
    """Tests that setup_test_environment wires CODEX_HOME additively."""

    def test_sets_codex_home_env_var(self):
        home = create_isolated_home()
        try:
            env = setup_test_environment(home, Path("/fake/project"))
            assert env["CODEX_HOME"] == str(home / CODEX_DIR)
            assert Path(env["CODEX_HOME"]).exists()
        finally:
            cleanup_test_environment(home, force=True)

    def test_claude_env_vars_unaffected(self):
        """Adding CODEX_HOME must not disturb the existing Claude isolation vars."""
        home = create_isolated_home()
        try:
            env = setup_test_environment(home, Path("/fake/project"))
            assert env["HOME"] == str(home)
            assert "SC_TEST_PROJECT" in env
        finally:
            cleanup_test_environment(home, force=True)


# =============================================================================
# ZDOTDIR provisioning
# =============================================================================


class TestProvisionCodexZdot:
    """Tests for provision_codex_zdot."""

    def test_creates_zdot_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            zdot_dir = Path(tmp) / "zdot"
            bin_dir = Path(tmp) / "bin"

            provision_codex_zdot(zdot_dir, bin_dir)

            assert (zdot_dir / ".zshenv").exists()
            assert (zdot_dir / ".zprofile").exists()
            assert (zdot_dir / ".zshrc").exists()

    def test_zshenv_prepends_bin_dir_to_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            zdot_dir = Path(tmp) / "zdot"
            bin_dir = Path(tmp) / "bin"

            provision_codex_zdot(zdot_dir, bin_dir)

            content = (zdot_dir / ".zshenv").read_text()
            assert str(bin_dir) in content
            assert content.startswith(f'export PATH="{bin_dir}:$PATH"')

    def test_zprofile_and_zshrc_are_empty(self):
        """Empty .zprofile/.zshrc so nothing re-clobbers PATH after .zshenv runs."""
        with tempfile.TemporaryDirectory() as tmp:
            zdot_dir = Path(tmp) / "zdot"
            bin_dir = Path(tmp) / "bin"

            provision_codex_zdot(zdot_dir, bin_dir)

            assert (zdot_dir / ".zprofile").read_text() == ""
            assert (zdot_dir / ".zshrc").read_text() == ""


# =============================================================================
# AGENTS.md generation (Skill-tool parity)
# =============================================================================


class TestWriteCodexAgentsMd:
    """Tests for write_codex_agents_md."""

    def test_writes_agents_md_listing_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp)
            skills_dir = project_path / ".claude" / "skills"
            (skills_dir / "skill-one").mkdir(parents=True)
            (skills_dir / "skill-one" / "SKILL.md").write_text("# Skill One")
            (skills_dir / "skill-two").mkdir(parents=True)
            (skills_dir / "skill-two" / "SKILL.md").write_text("# Skill Two")

            result = write_codex_agents_md(project_path)

            agents_path = project_path / "AGENTS.md"
            assert result == agents_path
            assert agents_path.exists()
            content = agents_path.read_text()
            assert "skill-one/SKILL.md" in content
            assert "skill-two/SKILL.md" in content
            assert "read the relevant skill and follow it" in content.lower()

    def test_skips_when_agents_md_already_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp)
            skills_dir = project_path / ".claude" / "skills" / "skill-one"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text("# Skill One")

            existing = project_path / "AGENTS.md"
            existing.write_text("# Fixture-provided AGENTS.md\n")

            result = write_codex_agents_md(project_path)

            assert result is None
            # Existing content must be left untouched.
            assert existing.read_text() == "# Fixture-provided AGENTS.md\n"

    def test_skips_when_no_skills_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp)

            result = write_codex_agents_md(project_path)

            assert result is None
            assert not (project_path / "AGENTS.md").exists()


# =============================================================================
# IsolatedSession.run_codex_command
# =============================================================================


class TestRunCodexCommand:
    """Tests for IsolatedSession.run_codex_command."""

    def _make_project(self, tmp: Path) -> Path:
        project_path = tmp / "project"
        (project_path / ".claude").mkdir(parents=True)
        (project_path / "reports").mkdir()
        return project_path

    def test_builds_expected_command(self):
        from harness.environment import isolated_claude_session

        with tempfile.TemporaryDirectory() as tmp:
            project_path = self._make_project(Path(tmp))

            with isolated_claude_session(project_path) as session:
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    session.run_codex_command("do the thing", model="luna")

                    cmd = mock_run.call_args[0][0]
                    assert cmd[0] == "codex"
                    assert cmd[1:4] == ["exec", "--yolo", "--model"]
                    assert cmd[4] == "gpt-5.6-luna"  # alias resolved
                    assert "--json" in cmd
                    assert "--skip-git-repo-check" in cmd
                    assert cmd[-1] == "do the thing"

    def test_sets_zdotdir_in_env(self):
        from harness.environment import isolated_claude_session

        with tempfile.TemporaryDirectory() as tmp:
            project_path = self._make_project(Path(tmp))

            with isolated_claude_session(project_path) as session:
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    session.run_codex_command("do the thing", model="luna")

                    env = mock_run.call_args[1]["env"]
                    assert "ZDOTDIR" in env
                    assert Path(env["ZDOTDIR"]).exists()
                    assert (Path(env["ZDOTDIR"]) / ".zshenv").exists()

    def test_writes_events_file_from_stdout(self):
        from harness.environment import isolated_claude_session

        with tempfile.TemporaryDirectory() as tmp:
            project_path = self._make_project(Path(tmp))

            with isolated_claude_session(project_path) as session:
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout=CODEX_EVENTS_SAMPLE, stderr=""
                    )

                    events_path = project_path / "reports" / "test-codex-events.jsonl"
                    session.run_codex_command(
                        "do the thing", model="luna", events_path=events_path
                    )

                    assert events_path.exists()
                    assert events_path.read_text() == CODEX_EVENTS_SAMPLE
                    assert session.codex_events_path == events_path

    def test_timeout_propagates(self):
        from harness.environment import isolated_claude_session

        with tempfile.TemporaryDirectory() as tmp:
            project_path = self._make_project(Path(tmp))

            with isolated_claude_session(project_path) as session:
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    session.run_codex_command("hi", model="luna", timeout=45)

                    assert mock_run.call_args[1]["timeout"] == 45


# =============================================================================
# Codex event -> CollectedData mapping
# =============================================================================


class TestParseCodexEvents:
    """Tests for parse_codex_events."""

    def test_parses_recorded_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            events_path = Path(tmp) / "codex-events.jsonl"
            events_path.write_text(CODEX_EVENTS_SAMPLE)

            events = parse_codex_events(events_path)

            assert len(events) == 4
            assert events[0]["type"] == "item.completed"
            assert events[-1]["type"] == "turn.completed"

    def test_missing_file_returns_empty_list(self):
        events = parse_codex_events(Path("/nonexistent/codex-events.jsonl"))
        assert events == []

    def test_skips_malformed_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            events_path = Path(tmp) / "codex-events.jsonl"
            events_path.write_text("not json\n" + CODEX_EVENTS_SAMPLE.splitlines()[0])

            events = parse_codex_events(events_path)

            assert len(events) == 1


class TestBuildCollectedDataFromCodexEvents:
    """Tests for build_collected_data_from_codex_events (the event-mapping table)."""

    def _events(self) -> list[dict]:
        return [json.loads(line) for line in CODEX_EVENTS_SAMPLE.splitlines()]

    def test_maps_command_execution_to_bash_tool_call(self):
        data = build_collected_data_from_codex_events(self._events())

        assert len(data.tool_calls) == 2
        first = data.tool_calls[0]
        assert isinstance(first, CorrelatedToolCall)
        assert first.tool_name == "Bash"
        assert first.tool_input == {"command": "ls -la"}
        assert first.tool_response["exit_code"] == 0
        assert "total 0" in first.tool_response["stdout"]
        assert first.is_error is False

    def test_nonzero_exit_code_marks_error(self):
        data = build_collected_data_from_codex_events(self._events())

        failing = data.tool_calls[1]
        assert failing.tool_input == {"command": "false"}
        assert failing.tool_response["exit_code"] == 1
        assert failing.is_error is True

    def test_maps_agent_message_to_claude_response_text(self):
        data = build_collected_data_from_codex_events(self._events())

        assert len(data.claude_responses) == 1
        response = data.claude_responses[0]
        assert isinstance(response, ClaudeResponseText)
        assert "listed the files" in response.text

    def test_maps_turn_completed_usage_to_token_usage(self):
        data = build_collected_data_from_codex_events(self._events())

        assert data.token_usage is not None
        assert data.token_usage.input_tokens == 120
        assert data.token_usage.output_tokens == 45
        assert data.token_usage.cache_creation_tokens == 10

    def test_no_usage_events_leaves_token_usage_none(self):
        events = [
            e for e in self._events() if e.get("type") != "turn.completed"
        ]
        data = build_collected_data_from_codex_events(events)
        assert data.token_usage is None

    def test_prompt_is_propagated(self):
        data = build_collected_data_from_codex_events(
            self._events(), prompt="do the thing"
        )
        assert data.prompt == "do the thing"

    def test_existing_evaluators_see_bash_tool_calls(self):
        """Sanity check: the mapping is consumable by tool_call-style evaluators,
        which key off tool_name + tool_input['command'] regardless of origin."""
        data = build_collected_data_from_codex_events(self._events())

        bash_commands = [
            tc.tool_input.get("command")
            for tc in data.tool_calls
            if tc.tool_name == "Bash"
        ]
        assert "ls -la" in bash_commands
        assert "false" in bash_commands


class TestDataCollectorCollectFromCodexEvents:
    """Tests for DataCollector.collect_from_codex_events."""

    def test_collect_from_codex_events_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            events_path = Path(tmp) / "test-codex-events.jsonl"
            events_path.write_text(CODEX_EVENTS_SAMPLE)

            collector = DataCollector()
            data = collector.collect_from_codex_events(
                events_path, prompt="do the thing"
            )

            assert isinstance(data, CollectedData)
            assert data.prompt == "do the thing"
            assert len(data.tool_calls) == 2
            assert len(data.claude_responses) == 1
            assert data.token_usage is not None


# =============================================================================
# TestRunner routing (codex path activates only on model match)
# =============================================================================


class TestRunnerCodexRouting:
    """Tests that TestRunner routes gpt-*/luna/sol/terra models through codex,
    while the Claude path (_build_test_command for a Claude model) is untouched."""

    def test_build_test_command_uses_codex_for_luna(self):
        from harness.runner import TestConfig, TestRunner

        with tempfile.TemporaryDirectory() as tmp:
            runner = TestRunner(project_path=tmp)
            test_config = TestConfig(
                test_id="t1",
                test_name="Test One",
                prompt="do the thing",
                model="luna",
            )

            command = runner._build_test_command(test_config)

            assert command.startswith("codex exec --yolo --model gpt-5.6-luna")
            assert "do the thing" in command

    def test_build_test_command_uses_codex_for_raw_gpt_model(self):
        from harness.runner import TestConfig, TestRunner

        with tempfile.TemporaryDirectory() as tmp:
            runner = TestRunner(project_path=tmp)
            test_config = TestConfig(
                test_id="t1",
                test_name="Test One",
                prompt="do the thing",
                model="gpt-5.6-sol",
            )

            command = runner._build_test_command(test_config)

            assert command.startswith("codex exec --yolo --model gpt-5.6-sol")

    def test_build_test_command_claude_path_untouched(self):
        """Regression: Claude command construction is unaffected by the codex branch."""
        from harness.runner import TestConfig, TestRunner

        with tempfile.TemporaryDirectory() as tmp:
            runner = TestRunner(project_path=tmp)
            test_config = TestConfig(
                test_id="t1",
                test_name="Test One",
                prompt="list files",
                model="haiku",
                tools=["Bash", "Read"],
            )

            command = runner._build_test_command(test_config)

            assert command == (
                'claude -p "list files" --model haiku '
                "--setting-sources project --dangerously-skip-permissions "
                "--tools Bash,Read"
            )

    def test_run_test_invokes_codex_session_method_for_codex_model(self):
        """Full run_test() dispatch: a luna test must call run_codex_command,
        never run_command, and must not call find_transcript()."""
        from harness.runner import FixtureConfig, TestRunner

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "project"
            (project_path / ".claude").mkdir(parents=True)
            fixture_dir = project_path.parent / "fixtures" / "demo" / "tests"
            fixture_dir.mkdir(parents=True)
            (fixture_dir.parent / "fixture.yaml").write_text(
                "name: demo\ntests_dir: tests\n"
            )
            (fixture_dir / "test_luna.yaml").write_text(
                "test_id: test_luna\n"
                "test_name: Luna Test\n"
                "execution:\n"
                "  prompt: hello\n"
                "  model: luna\n"
                "  timeout_ms: 5000\n"
            )

            runner = TestRunner(
                project_path=project_path,
                fixtures_path=fixture_dir.parent.parent,
            )
            fixture_config = FixtureConfig.from_yaml(fixture_dir.parent / "fixture.yaml")

            codex_events_sample = CODEX_EVENTS_SAMPLE

            def fake_run_codex_command(self, prompt, model, timeout, events_path):
                events_path.parent.mkdir(parents=True, exist_ok=True)
                events_path.write_text(codex_events_sample)
                self.codex_events_path = events_path
                self._process_result = MagicMock(
                    returncode=0, stdout=codex_events_sample, stderr=""
                )
                return self._process_result

            with patch(
                "harness.environment.IsolatedSession.run_codex_command",
                new=fake_run_codex_command,
            ), patch(
                "harness.environment.IsolatedSession.run_command"
            ) as mock_run_command, patch(
                "harness.environment.IsolatedSession.find_transcript"
            ) as mock_find_transcript:
                result = runner.run_test(
                    "demo", "test_luna.yaml", fixture_config=fixture_config
                )

            mock_run_command.assert_not_called()
            mock_find_transcript.assert_not_called()
            assert result.test_id == "test_luna"

            events_file = runner.reports_path / "test_luna-codex-events.jsonl"
            assert events_file.exists()
