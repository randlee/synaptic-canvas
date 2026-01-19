"""
Unit tests for artifact preservation with Result pattern.

Tests the refactored _preserve_artifacts() function and related helpers,
verifying:
- Result pattern error handling
- Partial failure scenarios (some artifacts succeed, some fail)
- Permission denied simulation
- All possible artifacts still attempted even on failures
- Never failing tests due to artifact preservation errors
"""

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness.pytest_plugin import (
    ArtifactReport,
    _preserve_artifacts,
    _write_artifact,
    _write_enriched_artifact,
)
from harness.result import ArtifactError, Failure, Success


class TestWriteArtifact:
    """Tests for _write_artifact helper function."""

    def test_successful_write(self, tmp_path: Path):
        """Test successful artifact write returns Success with path."""
        dest = tmp_path / "test.txt"
        result = _write_artifact(dest, "test content", "test")

        assert isinstance(result, Success)
        assert result.value == dest
        assert dest.read_text() == "test content"

    def test_creates_parent_directories(self, tmp_path: Path):
        """Test that parent directories are created automatically."""
        dest = tmp_path / "nested" / "dir" / "test.txt"
        result = _write_artifact(dest, "nested content", "test")

        assert isinstance(result, Success)
        assert dest.exists()
        assert dest.read_text() == "nested content"

    def test_write_failure_returns_failure(self, tmp_path: Path):
        """Test that write errors return Failure with ArtifactError."""
        # Create a read-only directory to cause write failure
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        dest = readonly_dir / "test.txt"

        # Make directory read-only (no write permission)
        original_mode = readonly_dir.stat().st_mode
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            result = _write_artifact(dest, "content", "test")

            assert isinstance(result, Failure)
            assert isinstance(result.error, ArtifactError)
            assert result.error.operation == "write"
            assert str(dest) in result.error.path
            assert "test:" in result.error.message  # artifact_type is prefixed
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(original_mode)

    def test_error_includes_artifact_type(self, tmp_path: Path):
        """Test that error message includes artifact type for context."""
        with patch("builtins.open", side_effect=IOError("disk full")):
            result = _write_artifact(tmp_path / "test.txt", "content", "transcript")

            assert isinstance(result, Failure)
            assert "transcript:" in result.error.message


class TestArtifactReport:
    """Tests for ArtifactReport dataclass."""

    def test_empty_report(self):
        """Test default empty report."""
        report = ArtifactReport()
        assert report.successful_writes == []
        assert report.failed_writes == []
        assert report.warnings == []
        assert report.total_attempted == 0
        assert report.success_count == 0
        assert report.failure_count == 0
        assert report.has_failures is False

    def test_report_with_successes(self, tmp_path: Path):
        """Test report tracking successful writes."""
        report = ArtifactReport()
        report.successful_writes.append(tmp_path / "file1.txt")
        report.successful_writes.append(tmp_path / "file2.txt")

        assert report.total_attempted == 2
        assert report.success_count == 2
        assert report.failure_count == 0
        assert report.has_failures is False

    def test_report_with_failures(self, tmp_path: Path):
        """Test report tracking failed writes."""
        report = ArtifactReport()
        report.successful_writes.append(tmp_path / "file1.txt")
        report.failed_writes.append(
            ArtifactError(operation="write", path="/bad/path", message="Permission denied")
        )

        assert report.total_attempted == 2
        assert report.success_count == 1
        assert report.failure_count == 1
        assert report.has_failures is True

    def test_report_with_warnings(self):
        """Test report tracking warnings."""
        report = ArtifactReport()
        report.warnings.append("Empty transcript for test-1")
        report.warnings.append("Validation warning")

        assert len(report.warnings) == 2
        assert report.has_failures is False  # Warnings don't count as failures


class TestPreserveArtifacts:
    """Tests for _preserve_artifacts function."""

    @pytest.fixture
    def mock_collected_data(self):
        """Create mock collected data for testing."""
        data = MagicMock()
        data.raw_transcript_entries = [
            {"type": "human", "message": "test prompt"},
            {"type": "assistant", "message": "test response"},
        ]
        data.raw_hook_events = [
            {"event": "test_start", "timestamp": "2024-01-01T00:00:00Z"},
        ]
        data.claude_cli_stdout = "stdout output"
        data.claude_cli_stderr = "stderr output"
        return data

    @pytest.fixture
    def mock_fixture_config(self, tmp_path: Path):
        """Create mock fixture config for testing."""
        config = MagicMock()
        config.package = "test-package"
        config.source_path = tmp_path / "fixture.yaml"
        return config

    @pytest.fixture
    def test_results_data(self, mock_collected_data):
        """Create test results data for testing."""
        test_config = MagicMock()
        test_config.test_id = "test-001"
        test_config.test_name = "Test 001"
        test_config.source_path = Path("/tmp/test.yaml")

        return [
            {
                "test_id": "test-001",
                "test_config": test_config,
                "collected_data": mock_collected_data,
                "pytest_output": "pytest output here",
            }
        ]

    def test_returns_success_on_all_writes_succeed(
        self, tmp_path: Path, test_results_data, mock_fixture_config
    ):
        """Test that Success is returned when all artifacts write successfully."""
        # Mock enrichment to avoid complex dependencies
        with patch(
            "harness.pytest_plugin._write_enriched_artifact",
            return_value=Success(value=[], warnings=[]),
        ):
            result = _preserve_artifacts(
                fixture_name="test-fixture",
                report_path=tmp_path,
                test_results_data=test_results_data,
                fixture_config=mock_fixture_config,
            )

        assert isinstance(result, Success)
        report = result.value
        assert report.success_count > 0
        assert report.failure_count == 0

    def test_returns_failure_with_partial_success(
        self, tmp_path: Path, test_results_data, mock_fixture_config
    ):
        """Test that Failure is returned with partial results when some writes fail."""
        # Create the directories first
        latest_dir = tmp_path / "test-fixture"
        history_dir = tmp_path / "history" / "test-fixture"

        # Mock enrichment to fail
        enrichment_error = ArtifactError(
            operation="enrichment",
            path="test-fixture/test-001-enriched.json",
            message="Enrichment failed",
        )
        with patch(
            "harness.pytest_plugin._write_enriched_artifact",
            return_value=Failure(enrichment_error),
        ):
            result = _preserve_artifacts(
                fixture_name="test-fixture",
                report_path=tmp_path,
                test_results_data=test_results_data,
                fixture_config=mock_fixture_config,
            )

        # Should return Failure since there was an error
        assert isinstance(result, Failure)

        # But partial_result should contain the ArtifactReport
        partial_report = result.partial_result
        assert partial_report is not None
        assert isinstance(partial_report, ArtifactReport)

        # Some artifacts should have succeeded (transcript, trace, cli, pytest)
        assert partial_report.success_count > 0

        # The enrichment error should be recorded
        assert partial_report.failure_count >= 1

    def test_all_artifacts_attempted_even_on_failure(
        self, tmp_path: Path, test_results_data, mock_fixture_config
    ):
        """Test that all artifact types are attempted even when some fail."""
        # Track which artifact types were attempted
        attempted_types = []

        original_write = _write_artifact

        def tracking_write(path: Path, content: str, artifact_type: str):
            attempted_types.append(artifact_type)
            # Fail transcript writes, succeed others
            if artifact_type == "transcript":
                return Failure(
                    ArtifactError(
                        operation="write", path=str(path), message="Simulated failure"
                    )
                )
            return original_write(path, content, artifact_type)

        with (
            patch("harness.pytest_plugin._write_artifact", side_effect=tracking_write),
            patch(
                "harness.pytest_plugin._write_enriched_artifact",
                return_value=Success(value=[], warnings=[]),
            ),
        ):
            result = _preserve_artifacts(
                fixture_name="test-fixture",
                report_path=tmp_path,
                test_results_data=test_results_data,
                fixture_config=mock_fixture_config,
            )

        # All artifact types should have been attempted
        assert "transcript" in attempted_types
        assert "trace" in attempted_types
        assert "cli_output" in attempted_types
        assert "pytest_output" in attempted_types

    def test_empty_data_produces_warnings_not_failures(
        self, tmp_path: Path, mock_fixture_config
    ):
        """Test that empty transcript/trace data produces warnings, not failures."""
        empty_data = MagicMock()
        empty_data.raw_transcript_entries = []
        empty_data.raw_hook_events = []
        empty_data.claude_cli_stdout = ""
        empty_data.claude_cli_stderr = ""

        test_config = MagicMock()
        test_config.test_id = "test-empty"
        test_config.test_name = "Empty Test"
        test_config.source_path = Path("/tmp/test.yaml")

        test_results_data = [
            {
                "test_id": "test-empty",
                "test_config": test_config,
                "collected_data": empty_data,
                "pytest_output": "",
            }
        ]

        with patch(
            "harness.pytest_plugin._write_enriched_artifact",
            return_value=Success(value=[], warnings=["No data to enrich"]),
        ):
            result = _preserve_artifacts(
                fixture_name="test-fixture",
                report_path=tmp_path,
                test_results_data=test_results_data,
                fixture_config=mock_fixture_config,
            )

        # Should succeed (no write failures)
        assert isinstance(result, Success)
        report = result.value

        # Should have warnings about empty data
        assert len(report.warnings) > 0

    def test_directory_creation_failure_handled(
        self, tmp_path: Path, test_results_data, mock_fixture_config
    ):
        """Test that directory creation failures are handled gracefully."""
        # Make report_path read-only to cause mkdir failure
        original_mode = tmp_path.stat().st_mode
        tmp_path.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            result = _preserve_artifacts(
                fixture_name="test-fixture",
                report_path=tmp_path,
                test_results_data=test_results_data,
                fixture_config=mock_fixture_config,
            )

            # Should return Failure but not raise exception
            assert isinstance(result, Failure)
            assert result.partial_result is not None
        finally:
            tmp_path.chmod(original_mode)

    def test_creates_both_latest_and_history_directories(
        self, tmp_path: Path, test_results_data, mock_fixture_config
    ):
        """Test that both latest and history directories are created."""
        with patch(
            "harness.pytest_plugin._write_enriched_artifact",
            return_value=Success(value=[], warnings=[]),
        ):
            result = _preserve_artifacts(
                fixture_name="test-fixture",
                report_path=tmp_path,
                test_results_data=test_results_data,
                fixture_config=mock_fixture_config,
            )

        # Latest directory should exist
        latest_dir = tmp_path / "test-fixture"
        assert latest_dir.exists()

        # History directory should exist (with timestamp subdirectory)
        history_dir = tmp_path / "history" / "test-fixture"
        assert history_dir.exists()
        # Should have one timestamp folder
        assert len(list(history_dir.iterdir())) >= 1


class TestWriteEnrichedArtifact:
    """Tests for _write_enriched_artifact helper function."""

    @pytest.fixture
    def mock_collected_data(self):
        """Create mock collected data with transcript entries."""
        data = MagicMock()
        data.raw_transcript_entries = [
            {"type": "human", "message": "test"},
        ]
        data.raw_hook_events = []
        return data

    def test_returns_success_with_no_data(self, tmp_path: Path):
        """Test that empty data returns Success with warning."""
        empty_data = MagicMock()
        empty_data.raw_transcript_entries = []
        empty_data.raw_hook_events = []

        result = _write_enriched_artifact(
            test_id="test-001",
            fixture_name="test-fixture",
            result_data={"test_config": None},
            collected_data=empty_data,
            fixture_config=None,
            latest_dir=tmp_path,
            history_dir=tmp_path / "history",
        )

        assert isinstance(result, Success)
        assert result.value == []  # No files written
        assert len(result.warnings) > 0  # Should have warning about no data

    def test_returns_failure_on_enrichment_error(self, tmp_path: Path, mock_collected_data):
        """Test that enrichment errors return Failure."""
        # Mock build_timeline_tree to raise exception
        # Must patch where the import happens (inside _write_enriched_artifact)
        with patch(
            "harness.enrichment.build_timeline_tree",
            side_effect=ValueError("Invalid data"),
        ):
            result = _write_enriched_artifact(
                test_id="test-001",
                fixture_name="test-fixture",
                result_data={"test_config": None},
                collected_data=mock_collected_data,
                fixture_config=None,
                latest_dir=tmp_path,
                history_dir=tmp_path / "history",
            )

        assert isinstance(result, Failure)
        assert result.error.operation == "enrichment"
        assert "Failed to generate enriched data" in result.error.message

    def test_validation_warnings_not_failures(self, tmp_path: Path, mock_collected_data):
        """Test that pydantic ValidationError produces warnings, not failures."""
        from pydantic import ValidationError as PydanticValidationError

        # Create directories
        latest_dir = tmp_path / "latest"
        history_dir = tmp_path / "history"
        latest_dir.mkdir()
        history_dir.mkdir()

        # Mock successful enrichment with model that has validation issues
        mock_enriched = MagicMock()
        mock_enriched.model_dump_json.return_value = "{}"
        mock_enriched.model_dump.return_value = {}

        # Create a mock that raises the actual ValidationError used in pydantic
        # We need to import the actual ValidationError from pydantic
        def raise_validation_error(*args, **kwargs):
            # This raises an actual pydantic ValidationError
            from pydantic import BaseModel

            class Strict(BaseModel):
                required_field: str

            Strict.model_validate({})  # This will raise ValidationError

        with (
            patch("harness.enrichment.build_timeline_tree", return_value=mock_enriched),
            patch(
                "harness.schemas.EnrichedData.model_validate",
                side_effect=raise_validation_error,
            ),
        ):
            result = _write_enriched_artifact(
                test_id="test-001",
                fixture_name="test-fixture",
                result_data={"test_config": None},
                collected_data=mock_collected_data,
                fixture_config=None,
                latest_dir=latest_dir,
                history_dir=history_dir,
            )

        # Should still succeed (validation warnings don't cause failure)
        assert isinstance(result, Success)
        # Should have a warning about the validation failure
        assert len(result.warnings) > 0
        assert any("validation" in w.lower() for w in result.warnings)


class TestIntegrationScenarios:
    """Integration tests for artifact preservation scenarios."""

    def test_real_world_partial_failure_scenario(self, tmp_path: Path):
        """Test a realistic scenario where some artifacts fail but others succeed."""
        # Create mock data that will produce real artifacts
        collected_data = MagicMock()
        collected_data.raw_transcript_entries = [
            {"type": "human", "message": "Hello"},
            {"type": "assistant", "message": "Hi there"},
        ]
        collected_data.raw_hook_events = [
            {"event": "start", "timestamp": "2024-01-01T00:00:00Z"},
        ]
        collected_data.claude_cli_stdout = "CLI output"
        collected_data.claude_cli_stderr = ""

        test_config = MagicMock()
        test_config.test_id = "integration-test"
        test_config.test_name = "Integration Test"
        test_config.source_path = Path("/tmp/test.yaml")

        test_results_data = [
            {
                "test_id": "integration-test",
                "test_config": test_config,
                "collected_data": collected_data,
                "pytest_output": "test output",
            }
        ]

        fixture_config = MagicMock()
        fixture_config.package = "test-pkg"
        fixture_config.source_path = tmp_path / "fixture.yaml"

        # Mock enrichment to fail (simulating a bug in enrichment)
        with patch(
            "harness.pytest_plugin._write_enriched_artifact",
            return_value=Failure(
                ArtifactError(
                    operation="enrichment",
                    path="test/enriched.json",
                    message="Enrichment bug",
                )
            ),
        ):
            result = _preserve_artifacts(
                fixture_name="integration-fixture",
                report_path=tmp_path,
                test_results_data=test_results_data,
                fixture_config=fixture_config,
            )

        # Should be Failure due to enrichment error
        assert isinstance(result, Failure)

        # But we should have partial results
        partial_report = result.partial_result
        assert partial_report is not None

        # Transcript, trace, cli, and pytest should have succeeded
        # (2 dirs each = 8 files total, minus enriched)
        assert partial_report.success_count >= 6

        # Verify actual files were written
        latest_dir = tmp_path / "integration-fixture"
        assert (latest_dir / "integration-test-transcript.jsonl").exists()
        assert (latest_dir / "integration-test-trace.jsonl").exists()
        assert (latest_dir / "integration-test-claude-cli.txt").exists()
        assert (latest_dir / "integration-test-pytest.txt").exists()
