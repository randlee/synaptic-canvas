"""
Tests for pytest plugin HTML report integration.

This module tests the report generation hooks and state management
added to the pytest_plugin.py module.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from harness.fixture_loader import FixtureConfig, TestConfig
from harness.models import TestStatus
from harness.pytest_plugin import (
    TestReportState,
    _create_minimal_test_result,
    _generate_fixture_report,
    _report_state,
)


# =============================================================================
# TestReportState Tests
# =============================================================================


class TestTestReportState:
    """Tests for the TestReportState class."""

    def test_init_creates_empty_state(self):
        """Test that initialization creates empty state."""
        state = TestReportState()
        assert state.fixture_names == []
        assert state.has_failures is False

    def test_reset_clears_state(self):
        """Test that reset clears all accumulated state."""
        state = TestReportState()
        state._has_failures = True
        state._test_results["fixture1"] = [{"test_id": "test1"}]

        state.reset()

        assert state.fixture_names == []
        assert state.has_failures is False
        assert state._test_results == {}

    def test_record_fixture_config(self):
        """Test recording fixture configurations."""
        state = TestReportState()
        config = MagicMock(spec=FixtureConfig)
        config.name = "test-fixture"

        state.record_fixture_config("test-fixture", config)

        assert state.get_fixture_config("test-fixture") is config

    def test_record_fixture_config_only_once(self):
        """Test that fixture config is only recorded once."""
        state = TestReportState()
        config1 = MagicMock(spec=FixtureConfig)
        config2 = MagicMock(spec=FixtureConfig)

        state.record_fixture_config("fixture", config1)
        state.record_fixture_config("fixture", config2)

        assert state.get_fixture_config("fixture") is config1

    def test_record_test_result_creates_fixture_entry(self):
        """Test that recording a result creates the fixture entry."""
        state = TestReportState()
        test_config = MagicMock(spec=TestConfig)

        state.record_test_result(
            fixture_name="my-fixture",
            test_id="test-001",
            test_config=test_config,
            passed=True,
        )

        assert "my-fixture" in state.fixture_names
        results = state.get_test_results("my-fixture")
        assert len(results) == 1
        assert results[0]["test_id"] == "test-001"
        assert results[0]["passed"] is True

    def test_record_test_result_tracks_failures(self):
        """Test that failed tests are tracked."""
        state = TestReportState()
        test_config = MagicMock(spec=TestConfig)

        state.record_test_result(
            fixture_name="fixture",
            test_id="test-001",
            test_config=test_config,
            passed=False,
            error_message="Something went wrong",
        )

        assert state.has_failures is True
        results = state.get_test_results("fixture")
        assert results[0]["error_message"] == "Something went wrong"

    def test_record_multiple_tests_same_fixture(self):
        """Test recording multiple tests for the same fixture."""
        state = TestReportState()
        test_config = MagicMock(spec=TestConfig)

        state.record_test_result(
            fixture_name="fixture",
            test_id="test-001",
            test_config=test_config,
            passed=True,
        )
        state.record_test_result(
            fixture_name="fixture",
            test_id="test-002",
            test_config=test_config,
            passed=False,
        )

        results = state.get_test_results("fixture")
        assert len(results) == 2
        assert results[0]["test_id"] == "test-001"
        assert results[1]["test_id"] == "test-002"

    def test_record_tests_multiple_fixtures(self):
        """Test recording tests across multiple fixtures."""
        state = TestReportState()
        test_config = MagicMock(spec=TestConfig)

        state.record_test_result(
            fixture_name="fixture-a",
            test_id="test-a1",
            test_config=test_config,
            passed=True,
        )
        state.record_test_result(
            fixture_name="fixture-b",
            test_id="test-b1",
            test_config=test_config,
            passed=True,
        )

        assert "fixture-a" in state.fixture_names
        assert "fixture-b" in state.fixture_names
        assert len(state.get_test_results("fixture-a")) == 1
        assert len(state.get_test_results("fixture-b")) == 1

    def test_get_fixture_config_returns_none_for_unknown(self):
        """Test that unknown fixture returns None."""
        state = TestReportState()
        assert state.get_fixture_config("unknown") is None

    def test_get_test_results_returns_empty_for_unknown(self):
        """Test that unknown fixture returns empty list."""
        state = TestReportState()
        assert state.get_test_results("unknown") == []

    def test_record_with_collected_data_and_expectations(self):
        """Test recording results with full data."""
        state = TestReportState()
        test_config = MagicMock(spec=TestConfig)
        collected_data = MagicMock()
        expectations = [MagicMock(), MagicMock()]

        state.record_test_result(
            fixture_name="fixture",
            test_id="test-001",
            test_config=test_config,
            passed=True,
            collected_data=collected_data,
            expectations=expectations,
            duration_ms=1234.5,
            pytest_output="test output",
        )

        results = state.get_test_results("fixture")
        assert results[0]["collected_data"] is collected_data
        assert results[0]["expectations"] == expectations
        assert results[0]["duration_ms"] == 1234.5
        assert results[0]["pytest_output"] == "test output"


# =============================================================================
# _create_minimal_test_result Tests
# =============================================================================


def _make_test_config_mock(
    test_id: str = "test-001",
    test_name: str = "Test Name",
    description: str = "Test description",
    tags: list | None = None,
    model: str = "haiku",
    prompt: str = "/test command",
    tools: list | None = None,
):
    """Create a properly configured test config mock."""
    test_config = MagicMock()
    test_config.test_id = test_id
    test_config.test_name = test_name
    test_config.description = description
    test_config.tags = tags if tags is not None else []
    test_config.execution = MagicMock()
    test_config.execution.model = model
    test_config.execution.prompt = prompt
    test_config.execution.tools = tools if tools is not None else []
    test_config.setup = None
    return test_config


class TestCreateMinimalTestResult:
    """Tests for the _create_minimal_test_result function."""

    def test_creates_passing_result(self):
        """Test creating a minimal passing result."""
        test_config = _make_test_config_mock(
            test_id="test-001",
            test_name="Test Name",
            description="Test description",
            tags=["tag1", "tag2"],
            model="haiku",
            prompt="/test command",
        )

        result = _create_minimal_test_result(
            test_config=test_config,
            fixture_name="my-fixture",
            passed=True,
            duration_ms=1500.0,
            error_message=None,
        )

        assert result.test_id == "test-001"
        assert result.test_name == "Test Name"
        assert result.status == TestStatus.PASS
        assert result.pass_rate == "1/1"  # String format: "passed/total"
        assert result.duration_ms == 1500
        assert len(result.expectations) == 0

    def test_creates_failing_result(self):
        """Test creating a minimal failing result."""
        test_config = _make_test_config_mock(
            test_id="test-002",
            test_name="Failing Test",
            description="This test fails",
            model="sonnet",
            prompt="/failing command",
        )

        result = _create_minimal_test_result(
            test_config=test_config,
            fixture_name="my-fixture",
            passed=False,
            duration_ms=2000.0,
            error_message="Connection timed out",
        )

        assert result.test_id == "test-002"
        assert result.status == TestStatus.FAIL
        assert result.pass_rate == "0/1"  # String format: "passed/total"
        assert len(result.expectations) == 1
        assert result.expectations[0].failure_reason == "Connection timed out"

    def test_truncates_long_test_ids_for_tab_label(self):
        """Test that long test IDs are truncated for tab labels."""
        test_config = _make_test_config_mock(
            test_id="very-long-test-id-that-exceeds-limit",
            test_name="Test",
        )

        result = _create_minimal_test_result(
            test_config=test_config,
            fixture_name="fixture",
            passed=True,
            duration_ms=100.0,
            error_message=None,
        )

        assert len(result.tab_label) == 15
        assert result.tab_label == "very-long-test-"

    def test_includes_metadata(self):
        """Test that metadata is properly set."""
        test_config = _make_test_config_mock(
            test_id="test-003",
            test_name="Metadata Test",
            description="Testing metadata",
            tags=["unit"],
            model="opus",
            prompt="/metadata test",
        )

        result = _create_minimal_test_result(
            test_config=test_config,
            fixture_name="metadata-fixture",
            passed=True,
            duration_ms=500.0,
            error_message=None,
        )

        assert result.metadata.fixture == "metadata-fixture"
        assert result.metadata.model == "opus"

    def test_includes_reproduce_section(self):
        """Test that reproduce section is populated."""
        test_config = _make_test_config_mock(
            test_id="test-004",
            test_name="Reproduce Test",
            prompt="/reproduce test",
        )

        result = _create_minimal_test_result(
            test_config=test_config,
            fixture_name="fixture",
            passed=True,
            duration_ms=100.0,
            error_message=None,
        )

        assert "claude" in result.reproduce.test_command
        assert "/reproduce test" in result.reproduce.test_command


# =============================================================================
# _generate_fixture_report Tests
# =============================================================================


def _make_fixture_config_mock(
    name: str = "test-fixture",
    package: str = "test-package",
    description: str = "Test Fixture",
):
    """Create a properly configured fixture config mock."""
    fixture_config = MagicMock()
    fixture_config.name = name
    fixture_config.package = package
    fixture_config.description = description
    return fixture_config


class TestGenerateFixtureReport:
    """Tests for the _generate_fixture_report function."""

    def test_returns_none_for_empty_results(self):
        """Test that None is returned when no results exist."""
        # Ensure state is clean
        _report_state.reset()

        result = _generate_fixture_report(
            fixture_name="nonexistent",
            report_path=Path("/tmp"),
            project_path=Path("/tmp"),
        )

        assert result is None

    def test_generates_html_file(self):
        """Test that HTML file is generated."""
        _report_state.reset()

        # Create test config mock
        test_config = _make_test_config_mock(
            test_id="test-001",
            test_name="Test One",
            description="A test",
        )

        # Create fixture config mock
        fixture_config = _make_fixture_config_mock(
            name="test-fixture",
            package="test-package",
            description="Test Fixture",
        )

        _report_state.record_fixture_config("test-fixture", fixture_config)
        _report_state.record_test_result(
            fixture_name="test-fixture",
            test_id="test-001",
            test_config=test_config,
            passed=True,
            collected_data=None,
            expectations=[],
            duration_ms=1000.0,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir)
            project_path = Path(tmpdir)

            result = _generate_fixture_report(
                fixture_name="test-fixture",
                report_path=report_path,
                project_path=project_path,
            )

            assert result is not None
            assert result.exists()
            assert result.suffix == ".html"

            # Check JSON was also created
            json_path = report_path / "test-fixture.json"
            assert json_path.exists()

    def test_handles_generation_errors_gracefully(self):
        """Test that errors during generation are handled."""
        _report_state.reset()

        # Record a result with test config
        test_config = _make_test_config_mock(
            test_id="test-001",
            test_name="Error Test",
        )

        fixture_config = _make_fixture_config_mock(
            name="error-fixture",
            package="",
            description="Error Fixture",
        )

        _report_state.record_fixture_config("error-fixture", fixture_config)
        _report_state.record_test_result(
            fixture_name="error-fixture",
            test_id="test-001",
            test_config=test_config,
            passed=True,
            collected_data=None,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # The function should handle errors and return None or the path
            # depending on implementation
            result = _generate_fixture_report(
                fixture_name="error-fixture",
                report_path=Path(tmpdir),
                project_path=Path(tmpdir),
            )
            # Should either succeed with fallback handling or return None
            # The important thing is it doesn't raise


# =============================================================================
# Global State Tests
# =============================================================================


class TestGlobalReportState:
    """Tests for the global _report_state instance."""

    def test_global_state_exists(self):
        """Test that the global state instance exists."""
        from harness.pytest_plugin import _report_state

        assert _report_state is not None
        assert isinstance(_report_state, TestReportState)

    def test_global_state_can_be_reset(self):
        """Test that the global state can be reset."""
        from harness.pytest_plugin import _report_state

        # Pollute the state
        _report_state._has_failures = True
        _report_state._test_results["test"] = []

        # Reset
        _report_state.reset()

        assert _report_state.has_failures is False
        assert _report_state.fixture_names == []


# =============================================================================
# Integration Tests (using pytest test infrastructure)
# =============================================================================


class TestPytestHookIntegration:
    """Integration tests for pytest hooks."""

    def test_sessionstart_resets_state(self):
        """Test that pytest_sessionstart resets the state."""
        from harness.pytest_plugin import pytest_sessionstart, _report_state

        # Pollute the state
        _report_state._has_failures = True

        # Create mock session
        session = MagicMock()

        pytest_sessionstart(session)

        assert _report_state.has_failures is False
        assert _report_state._session_start is not None

    def test_runtest_makereport_records_yaml_item_results(self):
        """Test that pytest_runtest_makereport records YAML test results."""
        from harness.pytest_plugin import (
            pytest_runtest_makereport,
            YAMLTestItem,
            _report_state,
        )

        _report_state.reset()

        # Create mock test config
        test_config = MagicMock(spec=TestConfig)
        test_config.test_id = "test-001"

        # Create mock fixture config
        fixture_config = MagicMock(spec=FixtureConfig)
        fixture_config.name = "mock-fixture"

        # Create mock YAMLTestItem
        item = MagicMock(spec=YAMLTestItem)
        item.fixture_config = fixture_config
        item.test_config = test_config
        item.collected_data = None
        item.evaluated_expectations = []
        item.execution_duration_ms = 1000.0
        item.execution_error = None
        item.claude_stdout = ""
        item.claude_stderr = ""
        item.expected_plugins = []
        item.plugin_install_results = []

        # Create mock call info (successful)
        call = MagicMock()
        call.when = "call"
        call.excinfo = None

        pytest_runtest_makereport(item, call)

        assert "mock-fixture" in _report_state.fixture_names
        results = _report_state.get_test_results("mock-fixture")
        assert len(results) == 1
        assert results[0]["passed"] is True

    def test_runtest_makereport_ignores_non_call_phases(self):
        """Test that non-call phases are ignored."""
        from harness.pytest_plugin import (
            pytest_runtest_makereport,
            YAMLTestItem,
            _report_state,
        )

        _report_state.reset()

        # Create mock YAMLTestItem
        item = MagicMock(spec=YAMLTestItem)

        # Create mock call info for setup phase
        call = MagicMock()
        call.when = "setup"  # Not "call"
        call.excinfo = None

        pytest_runtest_makereport(item, call)

        # Nothing should be recorded
        assert _report_state.fixture_names == []

    def test_runtest_makereport_ignores_non_yaml_items(self):
        """Test that non-YAML items are ignored."""
        from harness.pytest_plugin import pytest_runtest_makereport, _report_state

        _report_state.reset()

        # Create a regular pytest item (not YAMLTestItem)
        item = MagicMock()
        item.__class__ = pytest.Item  # Not YAMLTestItem

        call = MagicMock()
        call.when = "call"

        pytest_runtest_makereport(item, call)

        # Nothing should be recorded
        assert _report_state.fixture_names == []
