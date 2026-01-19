"""
Tests for scripts/generate-validation-report.py - HTML report generator.

Tests cover:
- Pydantic models (Issue, ValidatorResult, PackageVersion, etc.)
- Data collection functions
- Report generation
- HTML rendering
- Cleanup logic
- CLI interface
"""

import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "test-packages" / "harness"))


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def mock_project(temp_dir):
    """Create a mock project structure."""
    # Create version.yaml
    version_file = temp_dir / "version.yaml"
    version_file.write_text("version: 1.0.0\n")

    # Create packages directory
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    # Create a test package
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir()

    manifest = {
        "name": "test-package",
        "version": "1.0.0",
        "description": "Test package",
        "author": "Test",
        "license": "MIT",
        "tags": ["test"],
        "artifacts": {
            "commands": ["commands/test.md"],
            "skills": [],
            "agents": [],
            "scripts": [],
        },
    }
    (pkg_dir / "manifest.yaml").write_text(yaml.dump(manifest))

    # Create commands directory with a test command
    commands_dir = pkg_dir / "commands"
    commands_dir.mkdir()
    (commands_dir / "test.md").write_text(
        "---\nname: test\nversion: 1.0.0\ndescription: Test command\n---\nTest"
    )

    # Create reports directory
    reports_dir = temp_dir / "reports"
    reports_dir.mkdir()

    # Create scripts directory with mock validators
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()

    pass_script = scripts_dir / "pass-validator.py"
    pass_script.write_text('#!/usr/bin/env python3\nimport sys\nprint("PASS")\nsys.exit(0)\n')
    pass_script.chmod(0o755)

    return temp_dir


# ============================================================================
# Import Tests
# ============================================================================


def test_imports():
    """Test that all required imports work."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "generate_validation_report",
        Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "Issue")
    assert hasattr(module, "ValidatorResult")
    assert hasattr(module, "PackageVersion")
    assert hasattr(module, "ReportData")
    assert hasattr(module, "generate_validation_report")
    assert hasattr(module, "cleanup_old_reports")
    assert hasattr(module, "main")


# ============================================================================
# Model Tests
# ============================================================================


class TestIssue:
    """Tests for Issue model."""

    def test_basic_creation(self):
        """Test creating an issue."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        issue = module.Issue(
            message="Test issue",
            severity=module.Severity.HIGH,
            file_path="test.py",
        )

        assert issue.message == "Test issue"
        assert issue.severity == module.Severity.HIGH
        assert issue.file_path == "test.py"

    def test_severity_badge_class(self):
        """Test severity badge class mapping."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        critical = module.Issue(message="Critical", severity=module.Severity.CRITICAL)
        assert "danger" in critical.severity_badge_class()

        high = module.Issue(message="High", severity=module.Severity.HIGH)
        assert "warning" in high.severity_badge_class()

        medium = module.Issue(message="Medium", severity=module.Severity.MEDIUM)
        assert "info" in medium.severity_badge_class()

        low = module.Issue(message="Low", severity=module.Severity.LOW)
        assert "secondary" in low.severity_badge_class()


class TestValidatorResult:
    """Tests for ValidatorResult model."""

    def test_passed_result(self):
        """Test creating a passed validator result."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.ValidatorResult(
            name="Test Validator",
            command="python3 test.py",
            exit_code=0,
            passed=True,
            stdout="All tests passed",
            duration_seconds=1.5,
        )

        assert result.passed is True
        assert result.exit_code == 0
        assert result.duration_seconds == 1.5

    def test_failed_result(self):
        """Test creating a failed validator result."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.ValidatorResult(
            name="Test Validator",
            command="python3 test.py",
            exit_code=1,
            passed=False,
            stderr="Error occurred",
            error_message="Validation failed",
        )

        assert result.passed is False
        assert result.exit_code == 1
        assert result.error_message == "Validation failed"


class TestPackageVersion:
    """Tests for PackageVersion model."""

    def test_consistent_package(self):
        """Test creating a consistent package version."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        pkg = module.PackageVersion(
            package_name="test-pkg",
            manifest_version="1.0.0",
            commands=[{"name": "cmd1", "version": "1.0.0"}],
            is_consistent=True,
        )

        assert pkg.is_consistent is True
        assert pkg.manifest_version == "1.0.0"

    def test_inconsistent_package(self):
        """Test creating an inconsistent package version."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        pkg = module.PackageVersion(
            package_name="test-pkg",
            manifest_version="1.0.0",
            commands=[{"name": "cmd1", "version": "0.9.0"}],
            is_consistent=False,
        )

        assert pkg.is_consistent is False


class TestFileInfo:
    """Tests for FileInfo model."""

    def test_creation(self):
        """Test creating file info."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        info = module.FileInfo(
            path="test.yaml",
            modified_time="2024-01-15T10:30:00",
            size_bytes=1024,
        )

        assert info.path == "test.yaml"
        assert info.size_bytes == 1024


class TestTestSummary:
    """Tests for TestSummary model."""

    def test_empty_summary(self):
        """Test creating empty test summary."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        summary = module.TestSummary()

        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0

    def test_populated_summary(self):
        """Test creating populated test summary."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        summary = module.TestSummary(
            total=100,
            passed=95,
            failed=3,
            skipped=2,
            duration_seconds=45.5,
        )

        assert summary.total == 100
        assert summary.passed == 95
        assert summary.failed == 3


class TestReportData:
    """Tests for ReportData model."""

    def test_default_creation(self):
        """Test creating report data with defaults."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        data = module.ReportData()

        assert data.overall_passed is True
        assert data.total_packages == 0
        assert len(data.validator_results) == 0
        assert len(data.issues) == 0

    def test_get_issues_by_severity(self):
        """Test filtering issues by severity."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        data = module.ReportData(
            issues=[
                module.Issue(message="Critical 1", severity=module.Severity.CRITICAL),
                module.Issue(message="High 1", severity=module.Severity.HIGH),
                module.Issue(message="Critical 2", severity=module.Severity.CRITICAL),
            ]
        )

        critical_issues = data.get_issues_by_severity(module.Severity.CRITICAL)
        assert len(critical_issues) == 2

        high_issues = data.get_issues_by_severity(module.Severity.HIGH)
        assert len(high_issues) == 1


# ============================================================================
# Data Collection Function Tests
# ============================================================================


class TestGetMarketplaceVersion:
    """Tests for get_marketplace_version function."""

    def test_valid_version_file(self, temp_dir):
        """Test reading valid version file."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        version_file = temp_dir / "version.yaml"
        version_file.write_text("version: 2.0.0\n")

        result = module.get_marketplace_version(temp_dir)

        assert result.is_success()
        assert result.value == "2.0.0"

    def test_missing_version_file(self, temp_dir):
        """Test missing version file."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.get_marketplace_version(temp_dir)

        assert result.is_failure()
        assert "not found" in result.error.message.lower()

    def test_invalid_yaml(self, temp_dir):
        """Test invalid YAML in version file."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        version_file = temp_dir / "version.yaml"
        version_file.write_text("invalid: yaml: content:\n")

        result = module.get_marketplace_version(temp_dir)

        # May succeed with partial parse or fail
        # Just ensure it doesn't crash


class TestExtractFrontmatterVersion:
    """Tests for extract_frontmatter_version function."""

    def test_valid_frontmatter(self, temp_dir):
        """Test extracting version from valid frontmatter."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        md_file = temp_dir / "test.md"
        md_file.write_text("---\nname: test\nversion: 1.2.3\n---\nContent")

        version = module.extract_frontmatter_version(md_file)

        assert version == "1.2.3"

    def test_missing_version(self, temp_dir):
        """Test extracting from frontmatter without version."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        md_file = temp_dir / "test.md"
        md_file.write_text("---\nname: test\n---\nContent")

        version = module.extract_frontmatter_version(md_file)

        assert version is None

    def test_no_frontmatter(self, temp_dir):
        """Test extracting from file without frontmatter."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        md_file = temp_dir / "test.md"
        md_file.write_text("Just plain content")

        version = module.extract_frontmatter_version(md_file)

        assert version is None


class TestCollectPackageVersions:
    """Tests for collect_package_versions function."""

    def test_collect_from_mock_project(self, mock_project):
        """Test collecting package versions from mock project."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.collect_package_versions(mock_project)

        assert result.is_success()
        assert len(result.value) == 1
        assert result.value[0].package_name == "test-package"
        assert result.value[0].manifest_version == "1.0.0"

    def test_missing_packages_dir(self, temp_dir):
        """Test handling missing packages directory."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.collect_package_versions(temp_dir)

        assert result.is_failure()
        assert "not found" in result.error.message.lower()


class TestCollectConfigFiles:
    """Tests for collect_config_files function."""

    def test_collect_from_mock_project(self, mock_project):
        """Test collecting config files from mock project."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        files = module.collect_config_files(mock_project)

        assert len(files) >= 1
        paths = [f.path for f in files]
        assert "version.yaml" in paths


class TestExtractIssues:
    """Tests for extract_issues function."""

    def test_extract_from_failed_validators(self):
        """Test extracting issues from failed validators."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        results = [
            module.ValidatorResult(
                name="Test 1",
                command="test1",
                exit_code=0,
                passed=True,
            ),
            module.ValidatorResult(
                name="Test 2",
                command="test2",
                exit_code=1,
                passed=False,
                stderr="Error: Something went wrong",
            ),
        ]

        issues = module.extract_issues(results)

        assert len(issues) >= 1
        assert any("Test 2" in i.message for i in issues)

    def test_no_issues_for_passing(self):
        """Test no issues extracted from passing validators."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        results = [
            module.ValidatorResult(name="Test 1", command="test1", exit_code=0, passed=True),
            module.ValidatorResult(name="Test 2", command="test2", exit_code=0, passed=True),
        ]

        issues = module.extract_issues(results)

        assert len(issues) == 0


# ============================================================================
# Report Generation Tests
# ============================================================================


class TestGenerateReportFilename:
    """Tests for generate_report_filename function."""

    def test_default_prefix(self):
        """Test generating filename with default prefix."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        filename = module.generate_report_filename()

        assert "validation-report.html" in filename
        # Check timestamp format YYYY-MM-DD-HHmmss
        assert len(filename.split("-")[0]) == 4  # year

    def test_custom_prefix(self):
        """Test generating filename with custom prefix."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        filename = module.generate_report_filename("unit-test")

        assert "unit-test-report.html" in filename


class TestCleanupOldReports:
    """Tests for cleanup_old_reports function."""

    def test_cleanup_keeps_recent(self, temp_dir):
        """Test that cleanup keeps the most recent reports."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        # Create 7 mock reports
        import time
        for i in range(7):
            report = temp_dir / f"2024-01-{15+i:02d}-100000-validation-report.html"
            report.write_text(f"Report {i}")
            # Ensure different modification times
            time.sleep(0.01)

        deleted = module.cleanup_old_reports(temp_dir, keep_count=5)

        assert len(deleted) == 2
        remaining = list(temp_dir.glob("*-validation-report.html"))
        assert len(remaining) == 5

    def test_cleanup_empty_dir(self, temp_dir):
        """Test cleanup with no reports."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        deleted = module.cleanup_old_reports(temp_dir, keep_count=5)

        assert len(deleted) == 0

    def test_cleanup_fewer_than_keep(self, temp_dir):
        """Test cleanup when fewer reports exist than keep count."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        # Create 3 reports (less than default 5)
        for i in range(3):
            report = temp_dir / f"2024-01-{15+i:02d}-100000-validation-report.html"
            report.write_text(f"Report {i}")

        deleted = module.cleanup_old_reports(temp_dir, keep_count=5)

        assert len(deleted) == 0
        remaining = list(temp_dir.glob("*-validation-report.html"))
        assert len(remaining) == 3


class TestRenderHtmlReport:
    """Tests for render_html_report function."""

    def test_render_basic_report(self):
        """Test rendering a basic HTML report."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        data = module.ReportData(
            timestamp="2024-01-15T10:30:00",
            report_file="test-report.html",
            overall_passed=True,
            total_packages=3,
            marketplace_version="1.0.0",
        )

        html = module.render_html_report(data)

        assert "<!DOCTYPE html>" in html
        assert "Synaptic Canvas Validation Report" in html
        assert "1.0.0" in html

    def test_render_with_failures(self):
        """Test rendering report with failures."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        data = module.ReportData(
            overall_passed=False,
            validator_results=[
                module.ValidatorResult(
                    name="Failed Test",
                    command="test",
                    exit_code=1,
                    passed=False,
                ),
            ],
        )

        html = module.render_html_report(data)

        assert "FAIL" in html


# ============================================================================
# Integration Tests
# ============================================================================


class TestGenerateValidationReport:
    """Tests for generate_validation_report function."""

    def test_generate_basic_report(self, mock_project):
        """Test generating a basic validation report."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.generate_validation_report(
            mock_project,
            skip_tests=True,  # Skip pytest for faster test
            no_cleanup=True,
            verbose=False,
        )

        assert result.is_success()
        assert result.value.total_packages >= 1

        # Check report file was created
        reports = list((mock_project / "reports").glob("*-validation-report.html"))
        assert len(reports) >= 1

    def test_generate_with_custom_output(self, mock_project):
        """Test generating report with custom output path."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        custom_path = mock_project / "reports" / "custom-report.html"

        result = module.generate_validation_report(
            mock_project,
            output_path=custom_path,
            skip_tests=True,
            no_cleanup=True,
        )

        assert result.is_success()
        assert custom_path.exists()

    def test_generate_with_cleanup(self, mock_project):
        """Test report generation with cleanup."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        reports_dir = mock_project / "reports"

        # Create some old reports
        import time
        for i in range(7):
            old_report = reports_dir / f"2024-01-{10+i:02d}-100000-validation-report.html"
            old_report.write_text(f"Old report {i}")
            time.sleep(0.01)

        result = module.generate_validation_report(
            mock_project,
            skip_tests=True,
            keep_reports=3,
            verbose=False,
        )

        assert result.is_success()

        # Should have 3 old + 1 new = keeping only 3 most recent
        remaining = list(reports_dir.glob("*-validation-report.html"))
        assert len(remaining) <= 4  # 3 kept + 1 new


# ============================================================================
# CLI Tests
# ============================================================================


class TestCLI:
    """Tests for CLI interface."""

    def test_help_option(self):
        """Test --help option."""
        result = subprocess.run(
            [
                "python3",
                str(Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Generate comprehensive HTML validation report" in result.stdout
        assert "--skip-tests" in result.stdout
        assert "--keep-reports" in result.stdout
        assert "--no-cleanup" in result.stdout

    def test_skip_tests_option(self, mock_project):
        """Test --skip-tests option."""
        result = subprocess.run(
            [
                "python3",
                str(Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"),
                "--skip-tests",
                "--no-cleanup",
                "--project-root",
                str(mock_project),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # May fail due to missing validator scripts, but should not crash
        # Just verify the option is recognized
        assert "--skip-tests" not in result.stderr or "unrecognized" not in result.stderr


# ============================================================================
# Error Type Tests
# ============================================================================


class TestReportError:
    """Tests for ReportError dataclass."""

    def test_creation(self):
        """Test creating a ReportError."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        error = module.ReportError(
            message="Report generation failed",
            file_path="report.html",
            details={"reason": "disk full"},
        )

        assert error.message == "Report generation failed"
        assert error.file_path == "report.html"
        assert error.details["reason"] == "disk full"


class TestFileError:
    """Tests for FileError dataclass."""

    def test_creation(self):
        """Test creating a FileError."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        error = module.FileError(
            operation="read",
            path="/tmp/test.yaml",
            message="File not found",
        )

        assert error.operation == "read"
        assert error.path == "/tmp/test.yaml"
        assert error.message == "File not found"


# ============================================================================
# Severity Tests
# ============================================================================


class TestSeverity:
    """Tests for Severity constants."""

    def test_severity_values(self):
        """Test severity value constants."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.Severity.CRITICAL == "critical"
        assert module.Severity.HIGH == "high"
        assert module.Severity.MEDIUM == "medium"
        assert module.Severity.LOW == "low"


# ============================================================================
# HTML Template Tests
# ============================================================================


class TestHtmlTemplate:
    """Tests for HTML template."""

    def test_template_exists(self):
        """Test that HTML template is defined."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "HTML_TEMPLATE")
        assert "<!DOCTYPE html>" in module.HTML_TEMPLATE
        assert "bootstrap" in module.HTML_TEMPLATE.lower()  # Bootstrap 5 CDN link
        assert "Executive Summary" in module.HTML_TEMPLATE

    def test_template_has_all_sections(self):
        """Test that template has all required sections."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        template = module.HTML_TEMPLATE

        # Check for required sections
        assert "Executive Summary" in template
        assert "Version Matrix" in template
        assert "Package Details" in template
        assert "Validation Test Results" in template
        assert "Unit Test Results" in template
        assert "File Inventory" in template
        assert "Issues" in template


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_package_versions(self):
        """Test handling empty package versions list."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        data = module.ReportData(package_versions=[])
        html = module.render_html_report(data)

        # Should render without errors
        assert "<!DOCTYPE html>" in html

    def test_special_characters_in_messages(self):
        """Test handling special characters in issue messages."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        data = module.ReportData(
            issues=[
                module.Issue(message='Test with <script>alert("xss")</script>'),
                module.Issue(message="Test with 'quotes' and \"double quotes\""),
            ]
        )

        html = module.render_html_report(data)

        # Should render without errors (Jinja2 auto-escapes)
        assert "<!DOCTYPE html>" in html

    def test_very_long_output(self):
        """Test handling very long validator output."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "generate_validation_report",
            Path(__file__).parent.parent.parent / "scripts" / "generate-validation-report.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        long_output = "x" * 10000

        data = module.ReportData(
            validator_results=[
                module.ValidatorResult(
                    name="Long Output Test",
                    command="test",
                    exit_code=0,
                    passed=True,
                    stdout=long_output,
                )
            ]
        )

        html = module.render_html_report(data)

        # Should render without errors
        assert "<!DOCTYPE html>" in html
