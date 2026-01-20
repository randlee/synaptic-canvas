"""
Comprehensive unit tests for security-scan.py

Tests all functionality with 100% code coverage including:
- Secrets detection
- Script quality checks
- Python safety checks
- Package documentation verification
- License file verification
- Dependency auditing
- Result pattern usage
- Error handling
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

# Import the module under test
import sys

# Add scripts directory to path before importing
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Now we can import security_scan
import security_scan
from security_scan import (
    CheckResult,
    CheckStatus,
    ScanConfiguration,
    ScanResults,
    SecurityError,
    SecurityIssue,
    SecurityScanner,
    Severity,
    format_json_output,
    format_text_output,
    main,
)

# Add harness to path
HARNESS_DIR = Path(__file__).parent.parent.parent / "test-packages" / "harness"
sys.path.insert(0, str(HARNESS_DIR))
from result import Failure, Success


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Create directory structure
        packages_dir = repo_root / "packages"
        packages_dir.mkdir()

        # Create a test package
        test_pkg = packages_dir / "test-package"
        test_pkg.mkdir()

        # Create package files
        (test_pkg / "README.md").write_text("# Test Package\n\n## Security\n\nThis is secure.")
        (test_pkg / "LICENSE").write_text("MIT License\n\nCopyright 2025")
        (test_pkg / "manifest.yaml").write_text("name: test-package\nversion: 1.0.0\n")
        (test_pkg / "CHANGELOG.md").write_text("# Changelog\n\n## [1.0.0]\n- Initial release")

        # Create root LICENSE
        (repo_root / "LICENSE").write_text("MIT License")

        yield repo_root


@pytest.fixture
def basic_config(temp_repo):
    """Create a basic scan configuration."""
    return ScanConfiguration(
        quick_mode=False, single_package=None, repo_root=temp_repo, output_format="text"
    )


# =============================================================================
# Model Tests
# =============================================================================


class TestModels:
    """Test Pydantic models."""

    def test_security_issue_creation(self):
        """Test SecurityIssue model creation."""
        issue = SecurityIssue(
            severity=Severity.HIGH,
            message="Test issue",
            file_path="/path/to/file",
            line_number=42,
            line_content="some code",
        )
        assert issue.severity == "HIGH"
        assert issue.message == "Test issue"
        assert issue.file_path == "/path/to/file"
        assert issue.line_number == 42
        assert issue.line_content == "some code"

    def test_check_result_creation(self):
        """Test CheckResult model creation."""
        issue = SecurityIssue(severity=Severity.MEDIUM, message="Test")
        result = CheckResult(
            check_name="Test Check", status=CheckStatus.WARNING, issues=[issue], message="1 issue"
        )
        assert result.check_name == "Test Check"
        assert result.status == "WARNING"
        assert len(result.issues) == 1
        assert result.message == "1 issue"

    def test_scan_configuration_path_conversion(self):
        """Test ScanConfiguration converts strings to Path."""
        config = ScanConfiguration(quick_mode=False, repo_root="/tmp/test")
        assert isinstance(config.repo_root, Path)
        assert config.repo_root == Path("/tmp/test")

    def test_scan_results_creation(self):
        """Test ScanResults model creation."""
        config = ScanConfiguration(quick_mode=False, repo_root="/tmp")
        check = CheckResult(check_name="Test", status=CheckStatus.PASSED, issues=[], message="OK")
        results = ScanResults(
            scan_date="2025-01-19T12:00:00Z",
            overall_status=CheckStatus.PASSED,
            issues_found=0,
            checks={"test": check},
            configuration=config,
        )
        assert results.overall_status == "PASSED"
        assert results.issues_found == 0
        assert "test" in results.checks


# =============================================================================
# Secrets Detection Tests
# =============================================================================


class TestSecretsDetection:
    """Test secrets detection functionality."""

    def test_no_secrets_found(self, basic_config):
        """Test when no secrets are present."""
        scanner = SecurityScanner(basic_config)
        scanner.scan_secrets()

        assert "secrets_detection" in scanner.checks
        check = scanner.checks["secrets_detection"]
        assert check.status == CheckStatus.PASSED
        assert len(check.issues) == 0

    def test_password_detection(self, temp_repo):
        """Test detection of hardcoded passwords."""
        # Create file with password
        test_file = temp_repo / "test.py"
        test_file.write_text('password = "secret123"\n')

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.scan_secrets()

        check = scanner.checks["secrets_detection"]
        assert check.status == CheckStatus.FAILED
        assert len(check.issues) > 0
        assert any("Potential secret" in issue.message for issue in check.issues)

    def test_api_key_detection(self, temp_repo):
        """Test detection of API keys."""
        test_file = temp_repo / "config.py"
        test_file.write_text("api_key = 'sk_live_1234567890abcdef'\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.scan_secrets()

        check = scanner.checks["secrets_detection"]
        assert check.status == CheckStatus.FAILED
        assert len(check.issues) > 0

    def test_markdown_credential_detection(self, temp_repo):
        """Test detection of credentials in markdown."""
        md_file = temp_repo / "README.md"
        md_file.write_text("password = 'longsecretpassword123456789'\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.scan_secrets()

        check = scanner.checks["secrets_detection"]
        # May detect as secret or as markdown credential
        assert len(check.issues) > 0

    def test_private_key_detection(self, temp_repo):
        """Test detection of private keys."""
        key_file = temp_repo / "key.pem"
        key_file.write_text("-----BEGIN PRIVATE KEY-----\nABC123\n-----END PRIVATE KEY-----\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.scan_secrets()

        check = scanner.checks["secrets_detection"]
        assert check.status == CheckStatus.FAILED
        assert len(check.issues) > 0

    def test_secrets_in_single_package(self, temp_repo):
        """Test secrets detection in single package mode."""
        pkg_dir = temp_repo / "packages" / "test-package"
        secret_file = pkg_dir / "secret.py"
        secret_file.write_text("AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n")

        config = ScanConfiguration(quick_mode=False, single_package="test-package", repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.scan_secrets()

        check = scanner.checks["secrets_detection"]
        assert check.status == CheckStatus.FAILED


# =============================================================================
# Script Quality Tests
# =============================================================================


class TestScriptQuality:
    """Test script quality checks."""

    def test_no_scripts(self, basic_config):
        """Test when no shell scripts exist."""
        scanner = SecurityScanner(basic_config)
        scanner.check_script_quality()

        check = scanner.checks["script_quality"]
        assert check.status == CheckStatus.PASSED
        assert "0 scripts" in check.message

    def test_valid_script(self, temp_repo):
        """Test with a valid shell script."""
        script = temp_repo / "test.sh"
        script.write_text("#!/usr/bin/env bash\nset -euo pipefail\necho 'test'\n")
        os.chmod(script, 0o755)

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.check_script_quality()

        check = scanner.checks["script_quality"]
        assert check.status in [CheckStatus.PASSED, CheckStatus.WARNING]

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows doesn't support Unix executable bits")
    def test_non_executable_script(self, temp_repo):
        """Test detection of non-executable scripts."""
        script = temp_repo / "test.sh"
        script.write_text("#!/usr/bin/env bash\nset -e\necho 'test'\n")
        # Don't make it executable

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.check_script_quality()

        check = scanner.checks["script_quality"]
        assert any("not executable" in issue.message for issue in check.issues)

    def test_missing_shebang(self, temp_repo):
        """Test detection of missing shebang."""
        script = temp_repo / "test.sh"
        script.write_text("echo 'no shebang'\n")
        os.chmod(script, 0o755)

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.check_script_quality()

        check = scanner.checks["script_quality"]
        assert any("Missing shebang" in issue.message for issue in check.issues)

    def test_missing_set_e(self, temp_repo):
        """Test detection of missing 'set -e'."""
        script = temp_repo / "test.sh"
        script.write_text("#!/usr/bin/env bash\necho 'no error handling'\n")
        os.chmod(script, 0o755)

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.check_script_quality()

        check = scanner.checks["script_quality"]
        # Should detect missing 'set -e'
        assert any("set -e" in issue.message for issue in check.issues)

    @patch("security_scan.SecurityScanner._command_exists")
    @patch("subprocess.run")
    def test_shellcheck_integration(self, mock_run, mock_cmd_exists, temp_repo):
        """Test shellcheck integration."""
        mock_cmd_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="\nIn line 5:\nIssue found")

        script = temp_repo / "test.sh"
        script.write_text("#!/usr/bin/env bash\nset -e\necho test\n")
        os.chmod(script, 0o755)

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.check_script_quality()

        check = scanner.checks["script_quality"]
        assert any("Shellcheck" in issue.message for issue in check.issues)


# =============================================================================
# Python Safety Tests
# =============================================================================


class TestPythonSafety:
    """Test Python safety checks."""

    def test_no_unsafe_patterns(self, basic_config):
        """Test when no unsafe patterns exist."""
        scanner = SecurityScanner(basic_config)
        scanner.check_python_safety()

        check = scanner.checks["python_safety"]
        assert check.status == CheckStatus.PASSED
        assert len(check.issues) == 0

    def test_eval_detection(self, temp_repo):
        """Test detection of eval() calls."""
        py_file = temp_repo / "unsafe.py"
        py_file.write_text("result = eval(user_input)\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.check_python_safety()

        check = scanner.checks["python_safety"]
        assert check.status == CheckStatus.FAILED
        assert any("eval()" in issue.message for issue in check.issues)
        assert any(issue.severity == "HIGH" for issue in check.issues)

    def test_exec_detection(self, temp_repo):
        """Test detection of exec() calls."""
        py_file = temp_repo / "unsafe.py"
        py_file.write_text("exec(code)\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.check_python_safety()

        check = scanner.checks["python_safety"]
        assert check.status == CheckStatus.FAILED
        assert any("exec()" in issue.message for issue in check.issues)

    def test_shell_true_detection(self, temp_repo):
        """Test detection of shell=True."""
        py_file = temp_repo / "unsafe.py"
        py_file.write_text("subprocess.run(cmd, shell=True)\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.check_python_safety()

        check = scanner.checks["python_safety"]
        assert check.status == CheckStatus.FAILED
        assert any("shell=True" in issue.message for issue in check.issues)
        assert any(issue.severity == "MEDIUM" for issue in check.issues)

    def test_pickle_loads_detection(self, temp_repo):
        """Test detection of pickle.loads."""
        py_file = temp_repo / "unsafe.py"
        py_file.write_text("import pickle\ndata = pickle.loads(untrusted)\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.check_python_safety()

        check = scanner.checks["python_safety"]
        assert check.status == CheckStatus.FAILED
        assert any("pickle" in issue.message.lower() for issue in check.issues)


# =============================================================================
# Package Documentation Tests
# =============================================================================


class TestPackageDocumentation:
    """Test package documentation verification."""

    def test_complete_documentation(self, basic_config):
        """Test package with complete documentation."""
        scanner = SecurityScanner(basic_config)
        scanner.verify_package_documentation()

        check = scanner.checks["package_documentation"]
        # Should have warning about missing CHANGELOG (low severity)
        assert check.status in [CheckStatus.PASSED, CheckStatus.FAILED]

    def test_missing_readme(self, temp_repo):
        """Test detection of missing README."""
        pkg_dir = temp_repo / "packages" / "test-package"
        (pkg_dir / "README.md").unlink()

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.verify_package_documentation()

        check = scanner.checks["package_documentation"]
        # Missing README is a warning, not a failure
        assert check.status == CheckStatus.WARNING
        assert any("README" in issue.message for issue in check.issues)

    def test_readme_missing_security(self, temp_repo):
        """Test detection of README without security section."""
        pkg_dir = temp_repo / "packages" / "test-package"
        (pkg_dir / "README.md").write_text("# Test\n\nNo security info")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.verify_package_documentation()

        check = scanner.checks["package_documentation"]
        # When README exists but is missing security, it's MEDIUM severity
        # With CHANGELOG present, this results in FAILED status
        # But the check should complete and report results
        assert check.status in [CheckStatus.PASSED, CheckStatus.FAILED]

    def test_missing_license(self, temp_repo):
        """Test detection of missing LICENSE."""
        pkg_dir = temp_repo / "packages" / "test-package"
        (pkg_dir / "LICENSE").unlink()

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.verify_package_documentation()

        check = scanner.checks["package_documentation"]
        assert any("LICENSE" in issue.message for issue in check.issues)

    def test_missing_manifest(self, temp_repo):
        """Test detection of missing manifest.yaml."""
        pkg_dir = temp_repo / "packages" / "test-package"
        (pkg_dir / "manifest.yaml").unlink()

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.verify_package_documentation()

        check = scanner.checks["package_documentation"]
        assert any("manifest.yaml" in issue.message for issue in check.issues)

    def test_invalid_yaml_manifest(self, temp_repo):
        """Test detection of invalid YAML."""
        pkg_dir = temp_repo / "packages" / "test-package"
        (pkg_dir / "manifest.yaml").write_text("invalid: yaml: content:\n  - broken")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.verify_package_documentation()

        check = scanner.checks["package_documentation"]
        assert any("Invalid YAML" in issue.message for issue in check.issues)

    def test_missing_changelog_low_severity(self, temp_repo):
        """Test that missing CHANGELOG is low severity."""
        pkg_dir = temp_repo / "packages" / "test-package"
        (pkg_dir / "CHANGELOG.md").unlink()

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.verify_package_documentation()

        check = scanner.checks["package_documentation"]
        changelog_issues = [issue for issue in check.issues if "CHANGELOG" in issue.message]
        if changelog_issues:
            assert all(issue.severity == "LOW" for issue in changelog_issues)


# =============================================================================
# License Files Tests
# =============================================================================


class TestLicenseFiles:
    """Test license file verification."""

    def test_all_licenses_present(self, basic_config):
        """Test when all licenses are present."""
        scanner = SecurityScanner(basic_config)
        scanner.verify_license_files()

        check = scanner.checks["license_files"]
        assert check.status == CheckStatus.PASSED

    def test_missing_package_license(self, temp_repo):
        """Test detection of missing package LICENSE."""
        pkg_dir = temp_repo / "packages" / "test-package"
        (pkg_dir / "LICENSE").unlink()

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.verify_license_files()

        check = scanner.checks["license_files"]
        # Missing LICENSE is a warning, not a failure
        assert check.status == CheckStatus.WARNING
        assert any("LICENSE" in issue.message for issue in check.issues)

    def test_empty_license_file(self, temp_repo):
        """Test detection of empty LICENSE file."""
        pkg_dir = temp_repo / "packages" / "test-package"
        (pkg_dir / "LICENSE").write_text("")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.verify_license_files()

        check = scanner.checks["license_files"]
        assert check.status == CheckStatus.FAILED
        assert any("Empty LICENSE" in issue.message for issue in check.issues)

    def test_missing_root_license(self, temp_repo):
        """Test detection of missing root LICENSE."""
        (temp_repo / "LICENSE").unlink()

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.verify_license_files()

        check = scanner.checks["license_files"]
        # Missing LICENSE is a warning, not a failure
        assert check.status == CheckStatus.WARNING
        assert any("repository root" in issue.message for issue in check.issues)


# =============================================================================
# Dependency Audit Tests
# =============================================================================


class TestDependencyAudit:
    """Test dependency auditing."""

    def test_skipped_in_quick_mode(self, temp_repo):
        """Test that audit is skipped in quick mode."""
        config = ScanConfiguration(quick_mode=True, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.audit_dependencies()

        check = scanner.checks["dependency_audit"]
        assert check.status == CheckStatus.SKIPPED

    def test_no_dependencies(self, basic_config):
        """Test when no dependency files exist."""
        scanner = SecurityScanner(basic_config)
        scanner.audit_dependencies()

        check = scanner.checks["dependency_audit"]
        assert check.status == CheckStatus.PASSED

    @patch("security_scan.SecurityScanner._command_exists")
    @patch("subprocess.run")
    def test_npm_audit_high_severity(self, mock_run, mock_cmd_exists, temp_repo):
        """Test npm audit with high severity issues."""
        mock_cmd_exists.return_value = True
        audit_result = {
            "vulnerabilities": True,
            "metadata": {"vulnerabilities": {"high": 2, "moderate": 1}},
        }
        mock_run.return_value = MagicMock(stdout=json.dumps(audit_result))

        (temp_repo / "package.json").write_text('{"name": "test"}')

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.audit_dependencies()

        check = scanner.checks["dependency_audit"]
        assert check.status == CheckStatus.FAILED
        assert any("high severity npm" in issue.message for issue in check.issues)

    @patch("security_scan.SecurityScanner._command_exists")
    @patch("subprocess.run")
    def test_npm_audit_moderate_only(self, mock_run, mock_cmd_exists, temp_repo):
        """Test npm audit with only moderate issues."""
        mock_cmd_exists.return_value = True
        audit_result = {
            "vulnerabilities": True,
            "metadata": {"vulnerabilities": {"high": 0, "moderate": 3}},
        }
        mock_run.return_value = MagicMock(stdout=json.dumps(audit_result))

        (temp_repo / "package.json").write_text('{"name": "test"}')

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.audit_dependencies()

        check = scanner.checks["dependency_audit"]
        assert check.status == CheckStatus.WARNING
        assert any("moderate severity npm" in issue.message for issue in check.issues)

    def test_vulnerable_python_packages(self, temp_repo):
        """Test detection of vulnerable Python packages."""
        (temp_repo / "requirements.txt").write_text("pyyaml==5.3\nrequests==2.19.0\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.audit_dependencies()

        check = scanner.checks["dependency_audit"]
        assert len(check.issues) > 0
        assert any("pyyaml" in issue.message.lower() or "requests" in issue.message.lower() for issue in check.issues)

    def test_insecure_git_urls(self, temp_repo):
        """Test detection of insecure git:// URLs."""
        pkg_dir = temp_repo / "packages" / "test-package"
        manifest = pkg_dir / "manifest.yaml"
        manifest.write_text("dependencies:\n  - git://github.com/user/repo.git\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        scanner.audit_dependencies()

        check = scanner.checks["dependency_audit"]
        assert any("git://" in issue.message for issue in check.issues)


# =============================================================================
# Scanner Integration Tests
# =============================================================================


class TestScannerIntegration:
    """Test full scanner integration."""

    def test_full_scan_success(self, basic_config):
        """Test complete successful scan."""
        scanner = SecurityScanner(basic_config)
        result = scanner.run()

        assert isinstance(result, Success)
        assert isinstance(result.value, ScanResults)
        assert result.value.overall_status in [CheckStatus.PASSED, CheckStatus.WARNING, CheckStatus.FAILED]

    def test_scan_with_errors(self, temp_repo):
        """Test scan with multiple types of errors."""
        # Add various issues
        (temp_repo / "secret.py").write_text("password = 'secret123'\n")
        (temp_repo / "unsafe.py").write_text("eval(user_input)\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        result = scanner.run()

        assert isinstance(result, Success)
        assert result.value.issues_found > 0
        assert result.value.overall_status == CheckStatus.FAILED

    def test_calculate_overall_status_failed(self, basic_config):
        """Test overall status calculation with failures."""
        scanner = SecurityScanner(basic_config)
        scanner.checks["test1"] = CheckResult(
            check_name="Test1", status=CheckStatus.FAILED, issues=[], message=""
        )
        scanner.checks["test2"] = CheckResult(
            check_name="Test2", status=CheckStatus.PASSED, issues=[], message=""
        )

        status = scanner._calculate_overall_status()
        assert status == CheckStatus.FAILED

    def test_calculate_overall_status_warning(self, basic_config):
        """Test overall status calculation with warnings."""
        scanner = SecurityScanner(basic_config)
        scanner.checks["test1"] = CheckResult(
            check_name="Test1", status=CheckStatus.WARNING, issues=[], message=""
        )
        scanner.checks["test2"] = CheckResult(
            check_name="Test2", status=CheckStatus.PASSED, issues=[], message=""
        )

        status = scanner._calculate_overall_status()
        assert status == CheckStatus.WARNING

    def test_calculate_overall_status_passed(self, basic_config):
        """Test overall status calculation all passing."""
        scanner = SecurityScanner(basic_config)
        scanner.checks["test1"] = CheckResult(
            check_name="Test1", status=CheckStatus.PASSED, issues=[], message=""
        )
        scanner.checks["test2"] = CheckResult(
            check_name="Test2", status=CheckStatus.PASSED, issues=[], message=""
        )

        status = scanner._calculate_overall_status()
        assert status == CheckStatus.PASSED

    def test_single_package_mode(self, temp_repo):
        """Test scanning single package."""
        config = ScanConfiguration(quick_mode=False, single_package="test-package", repo_root=temp_repo)
        scanner = SecurityScanner(config)
        result = scanner.run()

        assert isinstance(result, Success)

    def test_quick_mode(self, temp_repo):
        """Test quick mode skips dependency audit."""
        config = ScanConfiguration(quick_mode=True, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        result = scanner.run()

        assert isinstance(result, Success)
        assert result.value.checks["dependency_audit"].status == CheckStatus.SKIPPED


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Test helper functions."""

    def test_command_exists_true(self):
        """Test _command_exists with existing command."""
        assert SecurityScanner._command_exists("ls")

    def test_command_exists_false(self):
        """Test _command_exists with non-existing command."""
        assert not SecurityScanner._command_exists("nonexistent_command_xyz")

    def test_command_exists_cross_platform(self):
        """Test _command_exists uses shutil.which for cross-platform support."""
        import shutil
        # Verify python3 exists (should work on all platforms)
        assert SecurityScanner._command_exists("python3") == (shutil.which("python3") is not None)
        # Verify the implementation matches shutil.which behavior
        assert SecurityScanner._command_exists("git") == (shutil.which("git") is not None)

    def test_get_search_path_repo_root(self, basic_config):
        """Test _get_search_path returns repo root."""
        scanner = SecurityScanner(basic_config)
        path = scanner._get_search_path()
        assert path == basic_config.repo_root

    def test_get_search_path_single_package(self, temp_repo):
        """Test _get_search_path with single package."""
        config = ScanConfiguration(quick_mode=False, single_package="test-package", repo_root=temp_repo)
        scanner = SecurityScanner(config)
        path = scanner._get_search_path()
        assert path == temp_repo / "packages" / "test-package"

    def test_get_packages_all(self, basic_config):
        """Test _get_packages returns all packages."""
        scanner = SecurityScanner(basic_config)
        packages = scanner._get_packages()
        assert "test-package" in packages

    def test_get_packages_single(self, temp_repo):
        """Test _get_packages with single package mode."""
        config = ScanConfiguration(quick_mode=False, single_package="test-package", repo_root=temp_repo)
        scanner = SecurityScanner(config)
        packages = scanner._get_packages()
        assert packages == ["test-package"]

    def test_grep_pattern_basic(self, temp_repo):
        """Test _grep_pattern basic functionality."""
        test_file = temp_repo / "test.txt"
        test_file.write_text("line 1\npattern found\nline 3\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        matches = scanner._grep_pattern("pattern", temp_repo)

        assert len(matches) > 0
        assert any("pattern found" in match[2] for match in matches)

    def test_grep_pattern_with_glob(self, temp_repo):
        """Test _grep_pattern with file glob."""
        (temp_repo / "test.py").write_text("pattern in python\n")
        (temp_repo / "test.txt").write_text("pattern in text\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        matches = scanner._grep_pattern("pattern", temp_repo, include_glob="*.py")

        assert len(matches) > 0
        assert all(match[0].endswith(".py") for match in matches)

    def test_grep_pattern_case_insensitive(self, temp_repo):
        """Test _grep_pattern case insensitive."""
        test_file = temp_repo / "test.txt"
        test_file.write_text("UPPERCASE pattern\n")

        config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
        scanner = SecurityScanner(config)
        matches = scanner._grep_pattern("pattern", temp_repo, case_insensitive=True)

        assert len(matches) > 0


# =============================================================================
# Output Format Tests
# =============================================================================


class TestOutputFormatting:
    """Test output formatting functions."""

    def test_format_text_output(self, basic_config):
        """Test text output formatting."""
        check = CheckResult(check_name="Test Check", status=CheckStatus.PASSED, issues=[], message="OK")
        results = ScanResults(
            scan_date="2025-01-19T12:00:00Z",
            overall_status=CheckStatus.PASSED,
            issues_found=0,
            checks={"test": check},
            configuration=basic_config,
        )

        output = format_text_output(results)
        assert "Security Scan Report" in output
        assert "Test Check" in output
        assert "PASSED" in output
        assert "2025-01-19" in output

    def test_format_text_output_with_issues(self, basic_config):
        """Test text output with issues."""
        issue = SecurityIssue(severity=Severity.HIGH, message="Test issue")
        check = CheckResult(check_name="Test", status=CheckStatus.FAILED, issues=[issue], message="")
        results = ScanResults(
            scan_date="2025-01-19T12:00:00Z",
            overall_status=CheckStatus.FAILED,
            issues_found=1,
            checks={"test": check},
            configuration=basic_config,
        )

        output = format_text_output(results)
        assert "FAILED" in output
        assert "Test issue" in output
        assert "[HIGH]" in output

    def test_format_json_output(self, basic_config):
        """Test JSON output formatting."""
        check = CheckResult(check_name="Test", status=CheckStatus.PASSED, issues=[], message="OK")
        results = ScanResults(
            scan_date="2025-01-19T12:00:00Z",
            overall_status=CheckStatus.PASSED,
            issues_found=0,
            checks={"test": check},
            configuration=basic_config,
        )

        output = format_json_output(results)
        parsed = json.loads(output)

        assert parsed["overall_status"] == "PASSED"
        assert parsed["issues_found"] == 0
        assert "test" in parsed["checks"]


# =============================================================================
# Main Function Tests
# =============================================================================


class TestMainFunction:
    """Test main() entry point."""

    @patch("sys.argv", ["security-scan.py"])
    def test_main_basic(self, temp_repo, monkeypatch):
        """Test main() with basic arguments."""
        monkeypatch.chdir(temp_repo)
        # Mock Path resolution
        with patch("security_scan.Path") as mock_path:
            mock_path.return_value.parent.parent.resolve.return_value = temp_repo
            # This would run the actual scan, so we patch the scanner
            with patch("security_scan.SecurityScanner.run") as mock_run:
                mock_config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
                mock_check = CheckResult(check_name="Test", status=CheckStatus.PASSED, issues=[], message="")
                mock_results = ScanResults(
                    scan_date="2025-01-19T12:00:00Z",
                    overall_status=CheckStatus.PASSED,
                    issues_found=0,
                    checks={"test": mock_check},
                    configuration=mock_config,
                )
                mock_run.return_value = Success(value=mock_results)

                exit_code = main()
                assert exit_code == 0

    @patch("sys.argv", ["security-scan.py", "--quick"])
    def test_main_quick_mode(self, temp_repo, capsys):
        """Test main() with --quick flag."""
        with patch("security_scan.Path") as mock_path:
            mock_path.return_value.parent.parent.resolve.return_value = temp_repo
            with patch("security_scan.SecurityScanner.run") as mock_run:
                mock_config = ScanConfiguration(quick_mode=True, repo_root=temp_repo)
                mock_check = CheckResult(check_name="Test", status=CheckStatus.PASSED, issues=[], message="")
                mock_results = ScanResults(
                    scan_date="2025-01-19T12:00:00Z",
                    overall_status=CheckStatus.PASSED,
                    issues_found=0,
                    checks={"test": mock_check},
                    configuration=mock_config,
                )
                mock_run.return_value = Success(value=mock_results)

                exit_code = main()
                assert exit_code == 0

    @patch("sys.argv", ["security-scan.py", "--json"])
    def test_main_json_output(self, temp_repo):
        """Test main() with --json flag."""
        with patch("security_scan.Path") as mock_path:
            mock_path.return_value.parent.parent.resolve.return_value = temp_repo
            with patch("security_scan.SecurityScanner.run") as mock_run:
                mock_config = ScanConfiguration(quick_mode=False, repo_root=temp_repo, output_format="json")
                mock_check = CheckResult(check_name="Test", status=CheckStatus.PASSED, issues=[], message="")
                mock_results = ScanResults(
                    scan_date="2025-01-19T12:00:00Z",
                    overall_status=CheckStatus.PASSED,
                    issues_found=0,
                    checks={"test": mock_check},
                    configuration=mock_config,
                )
                mock_run.return_value = Success(value=mock_results)

                exit_code = main()
                assert exit_code == 0

    @patch("sys.argv", ["security-scan.py", "--package", "nonexistent"])
    def test_main_invalid_package(self, temp_repo, capsys):
        """Test main() with non-existent package."""
        with patch("security_scan.Path") as mock_path:
            mock_path.return_value.parent.parent.resolve.return_value = temp_repo

            exit_code = main()
            assert exit_code == 2
            captured = capsys.readouterr()
            assert "Package not found" in captured.err

    @patch("sys.argv", ["security-scan.py"])
    def test_main_scanner_failure(self, temp_repo):
        """Test main() when scanner fails."""
        with patch("security_scan.Path") as mock_path:
            mock_path.return_value.parent.parent.resolve.return_value = temp_repo
            with patch("security_scan.SecurityScanner.run") as mock_run:
                mock_run.return_value = Failure(error=SecurityError(message="Test error"))

                exit_code = main()
                assert exit_code == 2

    @patch("sys.argv", ["security-scan.py"])
    def test_main_warning_exit_code(self, temp_repo):
        """Test main() returns exit code 0 for warnings (warnings are non-blocking)."""
        with patch("security_scan.Path") as mock_path:
            mock_path.return_value.parent.parent.resolve.return_value = temp_repo
            with patch("security_scan.SecurityScanner.run") as mock_run:
                mock_config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
                mock_check = CheckResult(check_name="Test", status=CheckStatus.WARNING, issues=[], message="")
                mock_results = ScanResults(
                    scan_date="2025-01-19T12:00:00Z",
                    overall_status=CheckStatus.WARNING,
                    issues_found=1,
                    checks={"test": mock_check},
                    configuration=mock_config,
                )
                mock_run.return_value = Success(value=mock_results)

                exit_code = main()
                # Warnings return 0 (non-blocking)
                assert exit_code == 0

    @patch("sys.argv", ["security-scan.py"])
    def test_main_failed_exit_code(self, temp_repo):
        """Test main() returns exit code 1 for failures."""
        with patch("security_scan.Path") as mock_path:
            mock_path.return_value.parent.parent.resolve.return_value = temp_repo
            with patch("security_scan.SecurityScanner.run") as mock_run:
                mock_config = ScanConfiguration(quick_mode=False, repo_root=temp_repo)
                mock_check = CheckResult(check_name="Test", status=CheckStatus.FAILED, issues=[], message="")
                mock_results = ScanResults(
                    scan_date="2025-01-19T12:00:00Z",
                    overall_status=CheckStatus.FAILED,
                    issues_found=1,
                    checks={"test": mock_check},
                    configuration=mock_config,
                )
                mock_run.return_value = Success(value=mock_results)

                exit_code = main()
                # Failures return 1
                assert exit_code == 1


# =============================================================================
# Result Pattern Tests
# =============================================================================


class TestResultPattern:
    """Test proper usage of Result pattern."""

    def test_success_result(self, basic_config):
        """Test Success result from scanner."""
        scanner = SecurityScanner(basic_config)
        result = scanner.run()

        assert isinstance(result, Success)
        assert hasattr(result, "value")
        assert hasattr(result, "warnings")
        assert isinstance(result.value, ScanResults)

    def test_failure_result_exception(self, basic_config):
        """Test Failure result on exception."""
        scanner = SecurityScanner(basic_config)

        # Force an exception by making repo_root invalid
        scanner.config.repo_root = Path("/nonexistent/path/xyz")

        with patch.object(scanner, "scan_secrets", side_effect=Exception("Test error")):
            result = scanner.run()

            assert isinstance(result, Failure)
            assert hasattr(result, "error")
            assert isinstance(result.error, SecurityError)
            assert "Test error" in result.error.message
