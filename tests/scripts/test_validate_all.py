"""
Tests for scripts/validate-all.py - Master validation orchestrator.

Tests cover:
- ValidatorConfig model
- ValidatorResult model
- ValidationSummary model
- run_validator function
- run_validators_sequential function
- run_validators_parallel function
- get_validators filtering
- CLI argument parsing
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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
def mock_scripts(temp_dir):
    """Create mock validator scripts."""
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()

    # Create a passing script
    passing_script = scripts_dir / "pass.py"
    passing_script.write_text('#!/usr/bin/env python3\nimport sys\nprint("PASS")\nsys.exit(0)\n')
    passing_script.chmod(0o755)

    # Create a failing script
    failing_script = scripts_dir / "fail.py"
    failing_script.write_text('#!/usr/bin/env python3\nimport sys\nprint("FAIL", file=sys.stderr)\nsys.exit(1)\n')
    failing_script.chmod(0o755)

    return scripts_dir


# ============================================================================
# Import Tests
# ============================================================================


def test_imports():
    """Test that all required imports work."""
    # This tests that the module can be imported
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "validate_all",
        Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "ValidatorConfig")
    assert hasattr(module, "ValidatorResult")
    assert hasattr(module, "ValidationSummary")
    assert hasattr(module, "run_validator")
    assert hasattr(module, "run_validators_sequential")
    assert hasattr(module, "run_validators_parallel")
    assert hasattr(module, "get_validators")
    assert hasattr(module, "main")


# ============================================================================
# Model Tests
# ============================================================================


class TestValidatorConfig:
    """Tests for ValidatorConfig model."""

    def test_basic_creation(self):
        """Test creating a validator config."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        config = module.ValidatorConfig(
            name="Test Validator",
            command=["python3", "test.py"],
        )

        assert config.name == "Test Validator"
        assert config.command == ["python3", "test.py"]
        assert config.required is True  # default
        assert config.timeout == 300  # default

    def test_optional_validator(self):
        """Test creating an optional validator."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        config = module.ValidatorConfig(
            name="Optional Test",
            command=["python3", "optional.py"],
            required=False,
            timeout=60,
        )

        assert config.required is False
        assert config.timeout == 60


class TestValidatorResult:
    """Tests for ValidatorResult model."""

    def test_passed_result(self):
        """Test creating a passed result."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.ValidatorResult(
            name="Test",
            command="python3 test.py",
            exit_code=0,
            passed=True,
            stdout="All tests passed",
            duration_seconds=1.5,
        )

        assert result.passed is True
        assert result.exit_code == 0

    def test_failed_result(self):
        """Test creating a failed result."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.ValidatorResult(
            name="Test",
            command="python3 test.py",
            exit_code=1,
            passed=False,
            stderr="Error occurred",
            error_message="Test failed",
        )

        assert result.passed is False
        assert result.exit_code == 1
        assert result.error_message == "Test failed"


class TestValidationSummary:
    """Tests for ValidationSummary model."""

    def test_empty_summary(self):
        """Test creating an empty summary."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        summary = module.ValidationSummary()

        assert summary.total_validators == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.all_passed is False

    def test_all_passed_summary(self):
        """Test summary when all validators pass."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        summary = module.ValidationSummary(
            total_validators=3,
            passed=3,
            failed=0,
            all_passed=True,
            results=[
                module.ValidatorResult(name="A", command="a", exit_code=0, passed=True),
                module.ValidatorResult(name="B", command="b", exit_code=0, passed=True),
                module.ValidatorResult(name="C", command="c", exit_code=0, passed=True),
            ],
        )

        assert summary.all_passed is True
        assert summary.passed == 3

    def test_to_json(self):
        """Test JSON serialization."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        summary = module.ValidationSummary(
            total_validators=1,
            passed=1,
            all_passed=True,
        )

        json_str = summary.to_json()
        data = json.loads(json_str)

        assert data["total_validators"] == 1
        assert data["passed"] == 1
        assert data["all_passed"] is True


# ============================================================================
# Function Tests
# ============================================================================


class TestRunValidator:
    """Tests for run_validator function."""

    def test_run_passing_script(self, temp_dir, mock_scripts):
        """Test running a passing validator script."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        config = module.ValidatorConfig(
            name="Pass Test",
            command=["python3", str(mock_scripts / "pass.py")],
        )

        result = module.run_validator(config)

        assert result.is_success()
        assert result.value.passed is True
        assert result.value.exit_code == 0

    def test_run_failing_script(self, temp_dir, mock_scripts):
        """Test running a failing validator script."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        config = module.ValidatorConfig(
            name="Fail Test",
            command=["python3", str(mock_scripts / "fail.py")],
        )

        result = module.run_validator(config)

        assert result.is_success()  # Execution succeeded, even if script failed
        assert result.value.passed is False
        assert result.value.exit_code == 1

    def test_run_nonexistent_script(self):
        """Test running a nonexistent script."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        config = module.ValidatorConfig(
            name="Missing Test",
            command=["python3", "/nonexistent/script.py"],
        )

        result = module.run_validator(config)

        # Python returns exit code 2 when script file doesn't exist
        # The execution "succeeds" but the script fails
        assert result.is_success()
        assert result.value.passed is False
        assert result.value.exit_code == 2

    def test_run_nonexistent_binary(self):
        """Test running a nonexistent binary."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        config = module.ValidatorConfig(
            name="Missing Binary Test",
            command=["/nonexistent/binary"],
        )

        result = module.run_validator(config)

        # When the binary itself doesn't exist, we get a FileNotFoundError
        assert result.is_failure()
        assert "not found" in result.error.message.lower()

    def test_run_with_timeout(self, temp_dir):
        """Test timeout handling."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        # Create a slow script
        slow_script = temp_dir / "slow.py"
        slow_script.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(10)\n')
        slow_script.chmod(0o755)

        config = module.ValidatorConfig(
            name="Slow Test",
            command=["python3", str(slow_script)],
            timeout=1,  # 1 second timeout
        )

        result = module.run_validator(config)

        assert result.is_failure()
        assert "timeout" in result.error.message.lower()


class TestRunValidatorsSequential:
    """Tests for run_validators_sequential function."""

    def test_all_pass(self, temp_dir, mock_scripts):
        """Test sequential run when all validators pass."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = [
            module.ValidatorConfig(name="Test 1", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Test 2", command=["python3", str(mock_scripts / "pass.py")]),
        ]

        result = module.run_validators_sequential(validators)

        assert result.is_success()
        assert result.value.all_passed is True
        assert result.value.passed == 2
        assert result.value.failed == 0

    def test_stop_on_failure(self, temp_dir, mock_scripts):
        """Test sequential run stops on failure by default."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = [
            module.ValidatorConfig(name="Test 1", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Test 2", command=["python3", str(mock_scripts / "fail.py")]),
            module.ValidatorConfig(name="Test 3", command=["python3", str(mock_scripts / "pass.py")]),
        ]

        result = module.run_validators_sequential(validators, continue_on_failure=False)

        assert result.is_success()
        assert result.value.all_passed is False
        assert result.value.passed == 1
        assert result.value.failed == 1
        assert result.value.skipped == 1  # Test 3 should be skipped

    def test_continue_on_failure(self, temp_dir, mock_scripts):
        """Test sequential run continues on failure when requested."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = [
            module.ValidatorConfig(name="Test 1", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Test 2", command=["python3", str(mock_scripts / "fail.py")]),
            module.ValidatorConfig(name="Test 3", command=["python3", str(mock_scripts / "pass.py")]),
        ]

        result = module.run_validators_sequential(validators, continue_on_failure=True)

        assert result.is_success()
        assert result.value.all_passed is False
        assert result.value.passed == 2
        assert result.value.failed == 1
        assert result.value.skipped == 0

    def test_optional_validator_skipped(self, temp_dir, mock_scripts):
        """Test that optional validators don't stop execution."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = [
            module.ValidatorConfig(name="Test 1", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Optional", command=["python3", str(mock_scripts / "fail.py")], required=False),
            module.ValidatorConfig(name="Test 3", command=["python3", str(mock_scripts / "pass.py")]),
        ]

        result = module.run_validators_sequential(validators, continue_on_failure=False)

        assert result.is_success()
        assert result.value.passed == 2
        assert result.value.skipped == 1  # Optional failure is skipped, not failed


class TestRunValidatorsParallel:
    """Tests for run_validators_parallel function."""

    def test_all_pass_parallel(self, temp_dir, mock_scripts):
        """Test parallel run when all validators pass."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = [
            module.ValidatorConfig(name="Test 1", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Test 2", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Test 3", command=["python3", str(mock_scripts / "pass.py")]),
        ]

        result = module.run_validators_parallel(validators, max_workers=2)

        assert result.is_success()
        assert result.value.all_passed is True
        assert result.value.passed == 3

    def test_some_fail_parallel(self, temp_dir, mock_scripts):
        """Test parallel run when some validators fail."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = [
            module.ValidatorConfig(name="Pass 1", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Fail 1", command=["python3", str(mock_scripts / "fail.py")]),
            module.ValidatorConfig(name="Pass 2", command=["python3", str(mock_scripts / "pass.py")]),
        ]

        result = module.run_validators_parallel(validators, max_workers=3)

        assert result.is_success()
        assert result.value.all_passed is False
        assert result.value.passed == 2
        assert result.value.failed == 1


class TestGetValidators:
    """Tests for get_validators function."""

    def test_get_all_validators(self):
        """Test getting all validators."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = module.get_validators()

        assert len(validators) > 0
        assert all(isinstance(v, module.ValidatorConfig) for v in validators)

    def test_include_filter(self):
        """Test including specific validators."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = module.get_validators(include=["version"])

        assert len(validators) > 0
        assert all("version" in v.name.lower() for v in validators)

    def test_exclude_filter(self):
        """Test excluding specific validators."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        all_validators = module.get_validators()
        filtered = module.get_validators(exclude=["security"])

        assert len(filtered) < len(all_validators)
        assert all("security" not in v.name.lower() for v in filtered)

    def test_include_and_exclude(self):
        """Test include and exclude together."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = module.get_validators(include=["manifest", "version"], exclude=["artifact"])

        assert len(validators) > 0
        for v in validators:
            name_lower = v.name.lower()
            assert "manifest" in name_lower or "version" in name_lower
            assert "artifact" not in name_lower


# ============================================================================
# CLI Tests
# ============================================================================


class TestCLI:
    """Tests for CLI interface."""

    def test_help_option(self):
        """Test --help option."""
        result = subprocess.run(
            ["python3", str(Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Master validation orchestrator" in result.stdout
        assert "--parallel" in result.stdout
        assert "--continue-on-failure" in result.stdout
        assert "--json" in result.stdout

    def test_list_option(self):
        """Test --list option."""
        result = subprocess.run(
            ["python3", str(Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"), "--list"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Available validators" in result.stdout
        assert "Version Consistency" in result.stdout

    def test_json_output(self, temp_dir, mock_scripts):
        """Test --json output option."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        # Mock to return single passing validator
        original_validators = module.DEFAULT_VALIDATORS
        module.DEFAULT_VALIDATORS = [
            module.ValidatorConfig(name="Test", command=["python3", str(mock_scripts / "pass.py")])
        ]

        try:
            result = subprocess.run(
                ["python3", str(Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"), "--json"],
                capture_output=True,
                text=True,
                cwd=temp_dir,
            )

            # Parse JSON output
            data = json.loads(result.stdout)
            assert "total_validators" in data
            assert "results" in data

        finally:
            module.DEFAULT_VALIDATORS = original_validators


class TestPrintSummary:
    """Tests for print_summary function."""

    def test_print_all_passed(self, capsys):
        """Test printing summary when all passed."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        summary = module.ValidationSummary(
            total_validators=2,
            passed=2,
            failed=0,
            all_passed=True,
            results=[
                module.ValidatorResult(name="Test 1", command="test1", exit_code=0, passed=True, duration_seconds=1.0),
                module.ValidatorResult(name="Test 2", command="test2", exit_code=0, passed=True, duration_seconds=2.0),
            ],
        )

        module.print_summary(summary)
        captured = capsys.readouterr()

        assert "ALL PASSED" in captured.out
        assert "Passed:            2" in captured.out

    def test_print_some_failed(self, capsys):
        """Test printing summary when some failed."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        summary = module.ValidationSummary(
            total_validators=2,
            passed=1,
            failed=1,
            all_passed=False,
            results=[
                module.ValidatorResult(name="Pass", command="pass", exit_code=0, passed=True, duration_seconds=1.0),
                module.ValidatorResult(name="Fail", command="fail", exit_code=1, passed=False, duration_seconds=2.0),
            ],
        )

        module.print_summary(summary)
        captured = capsys.readouterr()

        assert "FAILED" in captured.out
        assert "Failed:            1" in captured.out


# ============================================================================
# Error Type Tests
# ============================================================================


class TestValidatorError:
    """Tests for ValidatorError dataclass."""

    def test_creation(self):
        """Test creating a ValidatorError."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        error = module.ValidatorError(
            validator_name="Test",
            message="Something went wrong",
            exit_code=1,
            stdout="output",
            stderr="error",
            duration_seconds=1.5,
        )

        assert error.validator_name == "Test"
        assert error.message == "Something went wrong"
        assert error.exit_code == 1


class TestOrchestratorError:
    """Tests for OrchestratorError dataclass."""

    def test_creation(self):
        """Test creating an OrchestratorError."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        error = module.OrchestratorError(
            message="Orchestration failed",
            details={"key": "value"},
        )

        assert error.message == "Orchestration failed"
        assert error.details["key"] == "value"


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests."""

    def test_full_sequential_workflow(self, temp_dir, mock_scripts):
        """Test complete sequential workflow."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = [
            module.ValidatorConfig(name="Step 1", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Step 2", command=["python3", str(mock_scripts / "pass.py")]),
        ]

        result = module.run_validators_sequential(validators, verbose=False)

        assert result.is_success()
        summary = result.value
        assert summary.all_passed
        assert summary.total_duration_seconds > 0
        assert len(summary.results) == 2

    def test_full_parallel_workflow(self, temp_dir, mock_scripts):
        """Test complete parallel workflow."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        validators = [
            module.ValidatorConfig(name="Step 1", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Step 2", command=["python3", str(mock_scripts / "pass.py")]),
            module.ValidatorConfig(name="Step 3", command=["python3", str(mock_scripts / "pass.py")]),
        ]

        result = module.run_validators_parallel(validators, max_workers=3, verbose=False)

        assert result.is_success()
        summary = result.value
        assert summary.all_passed
        assert len(summary.results) == 3

    def test_working_directory(self, temp_dir, mock_scripts):
        """Test running validator with specific working directory."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location(
            "validate_all",
            Path(__file__).parent.parent.parent / "scripts" / "validate-all.py"
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        # Create script that outputs cwd
        cwd_script = mock_scripts / "cwd.py"
        cwd_script.write_text('#!/usr/bin/env python3\nimport os\nprint(os.getcwd())\n')
        cwd_script.chmod(0o755)

        config = module.ValidatorConfig(
            name="CWD Test",
            command=["python3", str(cwd_script)],
        )

        result = module.run_validator(config, cwd=temp_dir)

        assert result.is_success()
        assert str(temp_dir) in result.value.stdout
