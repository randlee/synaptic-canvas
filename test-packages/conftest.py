"""
Pytest configuration for Claude Code Test Harness.

This conftest.py file:
- Registers the harness pytest plugin for YAML fixture discovery
- Defines shared pytest fixtures (isolated_session, collector, etc.)
- Configures test paths and markers

Usage:
    # Run all tests (including harness unit tests and fixture tests)
    pytest test-packages/ -v

    # Run only fixture tests
    pytest test-packages/fixtures/ -v

    # Run specific fixture
    pytest test-packages/fixtures/sc-startup/ -v

    # Run harness unit tests only
    pytest test-packages/harness/tests/ -v

    # Filter by tag/keyword
    pytest test-packages/fixtures/ -v -k "readonly"
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

import pytest


# =============================================================================
# Path Configuration
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_PACKAGES_ROOT = Path(__file__).resolve().parent
HARNESS_PATH = TEST_PACKAGES_ROOT / "harness"
FIXTURES_PATH = TEST_PACKAGES_ROOT / "fixtures"

# Ensure harness package is importable
if str(TEST_PACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_PACKAGES_ROOT))

# Import and register the pytest plugin hooks for YAML fixture discovery
try:
    from harness.pytest_plugin import (
        pytest_collect_file,
        pytest_collection_modifyitems,
        pytest_configure as plugin_pytest_configure,
    )
    PLUGIN_AVAILABLE = True
except ImportError:
    PLUGIN_AVAILABLE = False
    logging.warning("harness.pytest_plugin not available - YAML fixture discovery disabled")

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# =============================================================================
# Pytest Configuration Hooks
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and plugin."""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "fixture_test: mark test as a YAML fixture test",
    )
    config.addinivalue_line(
        "markers",
        "keyword(name): mark test with a keyword for filtering",
    )

    # Call plugin's configure if available
    if PLUGIN_AVAILABLE:
        plugin_pytest_configure(config)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command line options."""
    parser.addoption(
        "--fixtures-path",
        action="store",
        default=None,
        help="Path to fixtures directory (default: test-packages/fixtures)",
    )
    parser.addoption(
        "--generate-report",
        action="store_true",
        default=False,
        help="Generate HTML report after test run",
    )
    parser.addoption(
        "--report-dir",
        action="store",
        default=None,
        help="Directory for generated reports (default: test-packages/reports)",
    )


# =============================================================================
# Existing Fixtures (preserved)
# =============================================================================


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Create a temporary repo directory for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


@pytest.fixture
def temp_home(tmp_path: Path) -> Path:
    """Create a temporary home directory for testing."""
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture
def clean_env(temp_home: Path) -> dict:
    """Provide a clean environment with overridden HOME."""
    env = dict(os.environ)
    env["HOME"] = str(temp_home)
    env["PYTHONNOUSERSITE"] = "1"
    return env


@pytest.fixture
def plugin_harness_path() -> Path:
    """Return path to plugin test harness."""
    return REPO_ROOT / "test-packages" / "test_fixtures" / "plugin_test_harness.py"


@pytest.fixture
def claude_cli() -> str | None:
    """Return path to claude CLI."""
    return os.environ.get("CLAUDE_CLI_PATH") or shutil.which("claude")


# =============================================================================
# Session-Scoped Path Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def test_packages_path() -> Path:
    """Return the test-packages directory path."""
    return TEST_PACKAGES_ROOT


@pytest.fixture(scope="session")
def fixtures_path_session(request: pytest.FixtureRequest) -> Path:
    """Return the fixtures directory path (session-scoped).

    Checks for command line override first.
    """
    custom_path = request.config.getoption("--fixtures-path")
    if custom_path:
        return Path(custom_path).absolute()
    return FIXTURES_PATH


@pytest.fixture(scope="session")
def reports_path(request: pytest.FixtureRequest) -> Path:
    """Return the reports directory path (created if needed)."""
    custom_path = request.config.getoption("--report-dir")
    if custom_path:
        path = Path(custom_path).absolute()
    else:
        path = TEST_PACKAGES_ROOT / "reports"

    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def harness_path() -> Path:
    """Return the harness code directory path."""
    return HARNESS_PATH


# =============================================================================
# Harness Fixtures
# =============================================================================


@pytest.fixture
def fixture_loader(fixtures_path_session: Path):
    """Provide a FixtureLoader instance."""
    try:
        from harness.fixture_loader import FixtureLoader
        return FixtureLoader(fixtures_path_session)
    except ImportError:
        pytest.skip("harness.fixture_loader not available")


@pytest.fixture
def isolated_session():
    """Provide an isolated Claude session with automatic cleanup."""
    try:
        from harness.environment import isolated_claude_session

        with isolated_claude_session(
            project_path=TEST_PACKAGES_ROOT,
            cleanup=True,
        ) as session:
            yield session
    except ImportError:
        pytest.skip("harness.environment not available")


@pytest.fixture
def collector_factory():
    """Provide a factory for creating DataCollector instances."""
    try:
        from harness.collector import DataCollector

        def _create(trace_path=None, transcript_path=None):
            return DataCollector(
                trace_path=trace_path,
                transcript_path=transcript_path,
            )

        return _create
    except ImportError:
        pytest.skip("harness.collector not available")


@pytest.fixture
def report_builder():
    """Provide a ReportBuilder instance."""
    try:
        from harness.reporter import ReportBuilder
        return ReportBuilder(project_path=TEST_PACKAGES_ROOT)
    except ImportError:
        pytest.skip("harness.reporter not available")


@pytest.fixture
def expectation_evaluator_factory():
    """Provide a factory for creating ExpectationEvaluator instances."""
    try:
        from harness.reporter import ExpectationEvaluator

        def _create(collected_data):
            return ExpectationEvaluator(collected_data)

        return _create
    except ImportError:
        pytest.skip("harness.reporter not available")


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_trace_events() -> list[dict]:
    """Provide sample hook trace events for testing."""
    return [
        {
            "ts": "2026-01-16T12:00:00.000Z",
            "event": "SessionStart",
            "session_id": "test-session-123",
            "transcript_path": "/tmp/test/session.jsonl",
            "cwd": "/path/to/project",
        },
        {
            "ts": "2026-01-16T12:00:01.000Z",
            "event": "UserPromptSubmit",
            "session_id": "test-session-123",
            "prompt": "Test prompt",
        },
        {
            "ts": "2026-01-16T12:00:02.000Z",
            "event": "PreToolUse",
            "session_id": "test-session-123",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "tool_use_id": "tool-001",
        },
        {
            "ts": "2026-01-16T12:00:03.000Z",
            "event": "PostToolUse",
            "session_id": "test-session-123",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "tool_response": {"stdout": "file1.txt\nfile2.txt", "stderr": ""},
            "tool_use_id": "tool-001",
        },
        {
            "ts": "2026-01-16T12:00:10.000Z",
            "event": "SessionEnd",
            "session_id": "test-session-123",
            "reason": "completed",
        },
    ]


@pytest.fixture
def sample_transcript_entries() -> list[dict]:
    """Provide sample transcript entries for testing."""
    return [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "Test prompt",
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll help you with that."},
                ],
            },
        },
        {
            "type": "tool_use",
            "id": "tool-001",
            "name": "Bash",
            "input": {"command": "ls -la"},
        },
        {
            "type": "tool_result",
            "tool_use_id": "tool-001",
            "content": "file1.txt\nfile2.txt",
            "is_error": False,
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Here are the files in the directory."},
                ],
            },
        },
    ]


@pytest.fixture
def sample_fixture_yaml() -> str:
    """Provide sample fixture.yaml content for testing."""
    return """
name: sample-fixture
description: Sample fixture for testing
package: test-package@test

setup:
  plugins:
    - test-plugin@test
  files:
    - src: data/config.yaml
      dest: .claude/config.yaml
  commands:
    - echo "Setting up"

teardown:
  commands:
    - echo "Cleaning up"

tests_dir: tests
"""


@pytest.fixture
def sample_test_yaml() -> str:
    """Provide sample test_*.yaml content for testing."""
    return """
test_id: sample-test-001
test_name: Sample Test
description: A sample test for testing the harness
tags:
  - sample
  - unit

execution:
  prompt: "/sample-command --flag"
  model: haiku
  tools:
    - Bash
    - Read
  timeout_ms: 30000

setup:
  commands:
    - echo "Test-specific setup"

expectations:
  - id: exp-001
    description: Should call Bash tool
    type: tool_call
    expected:
      tool: Bash
      pattern: "echo.*"

  - id: exp-002
    description: Should contain success message
    type: output_contains
    expected:
      pattern: "success"
      flags: "i"
"""


@pytest.fixture
def temp_fixtures_dir(tmp_path: Path, sample_fixture_yaml: str, sample_test_yaml: str) -> Path:
    """Create a temporary fixtures directory with sample content."""
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()

    # Create sample fixture
    sample_dir = fixtures_dir / "sample-fixture"
    sample_dir.mkdir()

    # Write fixture.yaml
    (sample_dir / "fixture.yaml").write_text(sample_fixture_yaml)

    # Create tests directory
    tests_dir = sample_dir / "tests"
    tests_dir.mkdir()

    # Write test file
    (tests_dir / "test_sample.yaml").write_text(sample_test_yaml)

    return fixtures_dir
