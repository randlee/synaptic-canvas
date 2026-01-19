"""Tests for validate-manifest-artifacts.py script."""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "test-packages" / "harness")
)

# Import using importlib to handle hyphens in filename
import importlib.util

spec = importlib.util.spec_from_file_location(
    "validate_manifest_artifacts",
    Path(__file__).parent.parent.parent / "scripts" / "validate-manifest-artifacts.py",
)
validate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_module)

from result import Failure, Success

load_manifest = validate_module.load_manifest
get_disk_files = validate_module.get_disk_files
validate_script_file = validate_module.validate_script_file
validate_manifest_artifacts = validate_module.validate_manifest_artifacts
ManifestSchema = validate_module.ManifestSchema
ManifestValidationResult = validate_module.ManifestValidationResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_manifest():
    """Sample manifest.yaml content."""
    return {
        "name": "test-package",
        "version": "1.0.0",
        "description": "Test package",
        "author": "test-author",
        "license": "MIT",
        "tags": ["test"],
        "artifacts": {
            "commands": ["commands/test.md"],
            "skills": ["skills/test/SKILL.md"],
            "agents": ["agents/test.md"],
            "scripts": ["scripts/test.py"],
        },
        "requires": [],
    }


@pytest.fixture
def package_with_files(temp_dir, sample_manifest):
    """Create package directory with files."""
    package_dir = temp_dir / "test-package"
    package_dir.mkdir()

    # Create manifest
    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create artifact directories
    (package_dir / "commands").mkdir()
    (package_dir / "skills" / "test").mkdir(parents=True)
    (package_dir / "agents").mkdir()
    (package_dir / "scripts").mkdir()

    # Create files
    (package_dir / "commands" / "test.md").write_text("# Test command")
    (package_dir / "skills" / "test" / "SKILL.md").write_text("# Test skill")
    (package_dir / "agents" / "test.md").write_text("# Test agent")

    # Create script with shebang
    script_path = package_dir / "scripts" / "test.py"
    script_path.write_text("#!/usr/bin/env python3\nprint('test')\n")

    return package_dir


# ============================================================================
# ManifestValidationResult Tests
# ============================================================================


def test_validation_result_is_valid_when_clean():
    """Test is_valid returns True when no errors."""
    result = ManifestValidationResult(package_name="test")
    assert result.is_valid() is True


def test_validation_result_is_valid_false_with_missing_files():
    """Test is_valid returns False with missing files."""
    result = ManifestValidationResult(
        package_name="test", missing_files=["missing.py"]
    )
    assert result.is_valid() is False


def test_validation_result_is_valid_false_with_orphaned_files():
    """Test is_valid returns False with orphaned files."""
    result = ManifestValidationResult(
        package_name="test", orphaned_files=["orphan.py"]
    )
    assert result.is_valid() is False


def test_validation_result_is_valid_false_with_invalid_scripts():
    """Test is_valid returns False with invalid scripts."""
    result = ManifestValidationResult(
        package_name="test", invalid_scripts=["bad.sh"]
    )
    assert result.is_valid() is False


def test_validation_result_is_valid_false_with_missing_shebangs():
    """Test is_valid returns False with missing shebangs."""
    result = ManifestValidationResult(
        package_name="test", missing_shebangs=["script.py"]
    )
    assert result.is_valid() is False


def test_validation_result_get_summary_pass():
    """Test get_summary for passing validation."""
    result = ManifestValidationResult(
        package_name="test", total_artifacts=5, total_disk_files=5
    )
    summary = result.get_summary()
    assert "test" in summary
    assert "PASS" in summary
    assert "5" in summary


def test_validation_result_get_summary_fail():
    """Test get_summary for failing validation."""
    result = ManifestValidationResult(
        package_name="test",
        missing_files=["missing.py"],
        orphaned_files=["orphan.md"],
        total_artifacts=5,
        total_disk_files=5,
    )
    summary = result.get_summary()
    assert "test" in summary
    assert "FAIL" in summary
    assert "missing.py" in summary
    assert "orphan.md" in summary


# ============================================================================
# load_manifest Tests
# ============================================================================


def test_load_manifest_success(package_with_files):
    """Test loading valid manifest."""
    result = load_manifest(package_with_files)
    assert isinstance(result, Success)
    assert result.value.name == "test-package"
    assert result.value.version == "1.0.0"


def test_load_manifest_missing_file(temp_dir):
    """Test loading when manifest doesn't exist."""
    package_dir = temp_dir / "missing-package"
    package_dir.mkdir()

    result = load_manifest(package_dir)
    assert isinstance(result, Failure)
    assert "not found" in result.error.message


def test_load_manifest_invalid_yaml(temp_dir):
    """Test loading invalid YAML."""
    package_dir = temp_dir / "invalid-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        f.write("invalid: yaml: content: {{{")

    result = load_manifest(package_dir)
    assert isinstance(result, Failure)
    assert "YAML" in result.error.message


def test_load_manifest_invalid_schema(temp_dir):
    """Test loading manifest with invalid schema."""
    package_dir = temp_dir / "invalid-schema"
    package_dir.mkdir()

    manifest = {
        "name": "INVALID-NAME",  # uppercase not allowed
        "version": "1.0.0",
        "description": "Test",
        "author": "test",
        "license": "MIT",
        "artifacts": {},
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    result = load_manifest(package_dir)
    assert isinstance(result, Failure)


def test_load_manifest_invalid_version(temp_dir):
    """Test loading manifest with invalid version."""
    package_dir = temp_dir / "invalid-version"
    package_dir.mkdir()

    manifest = {
        "name": "test-package",
        "version": "1.0",  # missing patch version
        "description": "Test",
        "author": "test",
        "license": "MIT",
        "artifacts": {},
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    result = load_manifest(package_dir)
    assert isinstance(result, Failure)


def test_load_manifest_version_with_non_numeric_parts(temp_dir):
    """Test loading manifest with non-numeric version parts."""
    package_dir = temp_dir / "bad-version"
    package_dir.mkdir()

    manifest = {
        "name": "test-package",
        "version": "1.0.beta",  # non-numeric part
        "description": "Test",
        "author": "test",
        "license": "MIT",
        "artifacts": {},
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    result = load_manifest(package_dir)
    assert isinstance(result, Failure)


# ============================================================================
# get_disk_files Tests
# ============================================================================


def test_get_disk_files_all_present(package_with_files):
    """Test getting disk files when all present."""
    files = get_disk_files(package_with_files)
    assert "commands/test.md" in files
    assert "skills/test/SKILL.md" in files
    assert "agents/test.md" in files
    assert "scripts/test.py" in files
    assert len(files) == 4


def test_get_disk_files_empty_package(temp_dir):
    """Test getting disk files from empty package."""
    package_dir = temp_dir / "empty-package"
    package_dir.mkdir()

    files = get_disk_files(package_dir)
    assert len(files) == 0


def test_get_disk_files_partial_dirs(temp_dir):
    """Test getting disk files when only some directories exist."""
    package_dir = temp_dir / "partial-package"
    package_dir.mkdir()

    (package_dir / "commands").mkdir()
    (package_dir / "commands" / "cmd.md").write_text("# Command")

    files = get_disk_files(package_dir)
    assert files == ["commands/cmd.md"]


def test_get_disk_files_nested_structure(temp_dir):
    """Test getting disk files with nested directory structure."""
    package_dir = temp_dir / "nested-package"
    package_dir.mkdir()

    (package_dir / "skills" / "test" / "nested").mkdir(parents=True)
    (package_dir / "skills" / "test" / "SKILL.md").write_text("# Skill")
    (package_dir / "skills" / "test" / "nested" / "deep.md").write_text("# Deep")

    files = get_disk_files(package_dir)
    assert "skills/test/SKILL.md" in files
    assert "skills/test/nested/deep.md" in files
    assert len(files) == 2


def test_get_disk_files_ignores_directories(temp_dir):
    """Test that get_disk_files only returns files, not directories."""
    package_dir = temp_dir / "dir-test-package"
    package_dir.mkdir()

    (package_dir / "commands").mkdir()
    (package_dir / "commands" / "subdir").mkdir()
    (package_dir / "commands" / "cmd.md").write_text("# Command")

    files = get_disk_files(package_dir)
    assert files == ["commands/cmd.md"]
    assert "commands/subdir" not in files


# ============================================================================
# validate_script_file Tests
# ============================================================================


def test_validate_script_file_valid(package_with_files):
    """Test validating a valid script file."""
    result = validate_script_file(package_with_files, "scripts/test.py")
    assert isinstance(result, Success)
    assert result.value is True


def test_validate_script_file_wrong_extension(temp_dir):
    """Test validating script with wrong extension."""
    package_dir = temp_dir / "bad-ext-package"
    package_dir.mkdir()
    (package_dir / "scripts").mkdir()

    script_path = package_dir / "scripts" / "test.sh"
    script_path.write_text("#!/bin/bash\necho test\n")

    result = validate_script_file(package_dir, "scripts/test.sh")
    assert isinstance(result, Failure)
    assert "extension" in result.error.message.lower()


def test_validate_script_file_missing_shebang(temp_dir):
    """Test validating script without shebang."""
    package_dir = temp_dir / "no-shebang-package"
    package_dir.mkdir()
    (package_dir / "scripts").mkdir()

    script_path = package_dir / "scripts" / "test.py"
    script_path.write_text("print('test')\n")

    result = validate_script_file(package_dir, "scripts/test.py")
    assert isinstance(result, Failure)
    assert "shebang" in result.error.message.lower()


def test_validate_script_file_wrong_shebang(temp_dir):
    """Test validating script with non-standard shebang."""
    package_dir = temp_dir / "wrong-shebang-package"
    package_dir.mkdir()
    (package_dir / "scripts").mkdir()

    script_path = package_dir / "scripts" / "test.py"
    script_path.write_text("#!/usr/bin/python\nprint('test')\n")

    result = validate_script_file(package_dir, "scripts/test.py")
    assert isinstance(result, Success)
    assert len(result.warnings) > 0
    assert "Non-standard shebang" in result.warnings[0]


def test_validate_script_file_missing(temp_dir):
    """Test validating non-existent script."""
    package_dir = temp_dir / "missing-script-package"
    package_dir.mkdir()

    result = validate_script_file(package_dir, "scripts/missing.py")
    assert isinstance(result, Failure)


# ============================================================================
# validate_manifest_artifacts Tests
# ============================================================================


def test_validate_manifest_artifacts_all_valid(package_with_files):
    """Test validation when all artifacts are valid."""
    result = validate_manifest_artifacts(package_with_files, verbose=False)
    assert isinstance(result, Success)
    assert result.value.is_valid()
    assert result.value.package_name == "test-package"
    assert result.value.total_artifacts == 4
    assert result.value.total_disk_files == 4


def test_validate_manifest_artifacts_missing_files(temp_dir, sample_manifest):
    """Test validation with missing files."""
    package_dir = temp_dir / "missing-files-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Only create some directories
    (package_dir / "commands").mkdir()
    (package_dir / "commands" / "test.md").write_text("# Command")

    result = validate_manifest_artifacts(package_dir, verbose=False)
    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert len(result.value.missing_files) == 3  # skills, agents, scripts


def test_validate_manifest_artifacts_orphaned_files(temp_dir, sample_manifest):
    """Test validation with orphaned files."""
    package_dir = temp_dir / "orphaned-files-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create all required files
    (package_dir / "commands").mkdir()
    (package_dir / "skills" / "test").mkdir(parents=True)
    (package_dir / "agents").mkdir()
    (package_dir / "scripts").mkdir()

    (package_dir / "commands" / "test.md").write_text("# Command")
    (package_dir / "skills" / "test" / "SKILL.md").write_text("# Skill")
    (package_dir / "agents" / "test.md").write_text("# Agent")
    script = package_dir / "scripts" / "test.py"
    script.write_text("#!/usr/bin/env python3\nprint('test')\n")

    # Add orphaned file
    (package_dir / "commands" / "orphan.md").write_text("# Orphan")

    result = validate_manifest_artifacts(package_dir, verbose=False)
    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert "commands/orphan.md" in result.value.orphaned_files


def test_validate_manifest_artifacts_invalid_script_extension(temp_dir):
    """Test validation with invalid script extension."""
    package_dir = temp_dir / "invalid-ext-package"
    package_dir.mkdir()

    manifest = {
        "name": "test-package",
        "version": "1.0.0",
        "description": "Test",
        "author": "test",
        "license": "MIT",
        "artifacts": {
            "scripts": ["scripts/test.sh"],
        },
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    (package_dir / "scripts").mkdir()
    (package_dir / "scripts" / "test.sh").write_text("#!/bin/bash\necho test\n")

    result = validate_manifest_artifacts(package_dir, verbose=False)
    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert "scripts/test.sh" in result.value.invalid_scripts


def test_validate_manifest_artifacts_missing_shebang(temp_dir):
    """Test validation with script missing shebang."""
    package_dir = temp_dir / "no-shebang-pkg"
    package_dir.mkdir()

    manifest = {
        "name": "test-package",
        "version": "1.0.0",
        "description": "Test",
        "author": "test",
        "license": "MIT",
        "artifacts": {
            "scripts": ["scripts/test.py"],
        },
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    (package_dir / "scripts").mkdir()
    (package_dir / "scripts" / "test.py").write_text("print('test')\n")

    result = validate_manifest_artifacts(package_dir, verbose=False)
    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert "scripts/test.py" in result.value.missing_shebangs


def test_validate_manifest_artifacts_no_manifest(temp_dir):
    """Test validation when manifest is missing."""
    package_dir = temp_dir / "no-manifest-package"
    package_dir.mkdir()

    result = validate_manifest_artifacts(package_dir, verbose=False)
    assert isinstance(result, Failure)
    assert "not found" in result.error.message


def test_validate_manifest_artifacts_verbose_mode(package_with_files, capsys):
    """Test validation with verbose mode enabled."""
    result = validate_manifest_artifacts(package_with_files, verbose=True)
    assert isinstance(result, Success)

    captured = capsys.readouterr()
    assert "test-package" in captured.out
    assert "PASS" in captured.out


def test_validate_manifest_artifacts_multiple_issues(temp_dir):
    """Test validation with multiple different issues."""
    package_dir = temp_dir / "multi-issue-package"
    package_dir.mkdir()

    manifest = {
        "name": "test-package",
        "version": "1.0.0",
        "description": "Test",
        "author": "test",
        "license": "MIT",
        "artifacts": {
            "commands": ["commands/missing.md"],
            "scripts": ["scripts/bad.sh", "scripts/no-shebang.py"],
        },
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    (package_dir / "commands").mkdir()
    (package_dir / "scripts").mkdir()
    (package_dir / "commands" / "orphan.md").write_text("# Orphan")
    (package_dir / "scripts" / "bad.sh").write_text("#!/bin/bash\n")
    (package_dir / "scripts" / "no-shebang.py").write_text("print('test')\n")

    result = validate_manifest_artifacts(package_dir, verbose=False)
    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert len(result.value.missing_files) >= 1
    assert len(result.value.orphaned_files) >= 1
    assert len(result.value.invalid_scripts) >= 1
    assert len(result.value.missing_shebangs) >= 1


# ============================================================================
# Cross-platform Path Tests
# ============================================================================


def test_cross_platform_path_handling_posix(temp_dir, sample_manifest):
    """Test path handling on POSIX systems."""
    package_dir = temp_dir / "posix-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create nested structure
    (package_dir / "skills" / "test").mkdir(parents=True)
    (package_dir / "skills" / "test" / "SKILL.md").write_text("# Skill")

    files = get_disk_files(package_dir)
    # Should use forward slashes
    assert "skills/test/SKILL.md" in files


def test_cross_platform_manifest_paths(temp_dir):
    """Test that manifest paths are handled consistently."""
    package_dir = temp_dir / "path-test-package"
    package_dir.mkdir()

    manifest = {
        "name": "test-package",
        "version": "1.0.0",
        "description": "Test",
        "author": "test",
        "license": "MIT",
        "artifacts": {
            "skills": ["skills/nested/SKILL.md"],
        },
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    (package_dir / "skills" / "nested").mkdir(parents=True)
    (package_dir / "skills" / "nested" / "SKILL.md").write_text("# Skill")

    result = validate_manifest_artifacts(package_dir, verbose=False)
    assert isinstance(result, Success)
    assert result.value.is_valid()


# ============================================================================
# Edge Cases
# ============================================================================


def test_validate_empty_artifacts(temp_dir):
    """Test validation with empty artifacts section."""
    package_dir = temp_dir / "empty-artifacts"
    package_dir.mkdir()

    manifest = {
        "name": "test-package",
        "version": "1.0.0",
        "description": "Test",
        "author": "test",
        "license": "MIT",
        "artifacts": {},
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    result = validate_manifest_artifacts(package_dir, verbose=False)
    assert isinstance(result, Success)
    assert result.value.is_valid()
    assert result.value.total_artifacts == 0


def test_validate_hidden_files_ignored(temp_dir, sample_manifest):
    """Test that hidden files are included (they're valid artifacts)."""
    package_dir = temp_dir / "hidden-files-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    (package_dir / "commands").mkdir()
    (package_dir / "commands" / ".hidden.md").write_text("# Hidden")
    (package_dir / "commands" / "test.md").write_text("# Command")

    files = get_disk_files(package_dir)
    # Hidden files should be included
    assert "commands/.hidden.md" in files


# ============================================================================
# CLI/main() Tests
# ============================================================================


def test_main_with_valid_package(temp_dir, monkeypatch, sample_manifest):
    """Test CLI with valid package."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    (package_dir / "commands").mkdir()
    (package_dir / "skills" / "test").mkdir(parents=True)
    (package_dir / "agents").mkdir()
    (package_dir / "scripts").mkdir()

    (package_dir / "commands" / "test.md").write_text("# Command")
    (package_dir / "skills" / "test" / "SKILL.md").write_text("# Skill")
    (package_dir / "agents" / "test.md").write_text("# Agent")
    script = package_dir / "scripts" / "test.py"
    script.write_text("#!/usr/bin/env python3\nprint('test')\n")

    # Mock sys.argv
    monkeypatch.setattr(
        "sys.argv",
        ["validate-manifest-artifacts.py", "--packages-dir", str(packages_dir)],
    )

    # Import and run main
    main = validate_module.main
    exit_code = main()
    assert exit_code == 0


def test_main_with_invalid_package(temp_dir, monkeypatch, sample_manifest):
    """Test CLI with invalid package (missing files)."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Don't create any files - they'll all be missing

    monkeypatch.setattr(
        "sys.argv",
        ["validate-manifest-artifacts.py", "--packages-dir", str(packages_dir)],
    )

    main = validate_module.main
    exit_code = main()
    assert exit_code == 1


def test_main_with_specific_package(temp_dir, monkeypatch, sample_manifest):
    """Test CLI with --package flag."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    (package_dir / "commands").mkdir()
    (package_dir / "skills" / "test").mkdir(parents=True)
    (package_dir / "agents").mkdir()
    (package_dir / "scripts").mkdir()

    (package_dir / "commands" / "test.md").write_text("# Command")
    (package_dir / "skills" / "test" / "SKILL.md").write_text("# Skill")
    (package_dir / "agents" / "test.md").write_text("# Agent")
    script = package_dir / "scripts" / "test.py"
    script.write_text("#!/usr/bin/env python3\nprint('test')\n")

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate-manifest-artifacts.py",
            "--packages-dir",
            str(packages_dir),
            "--package",
            "test-package",
        ],
    )

    main = validate_module.main
    exit_code = main()
    assert exit_code == 0


def test_main_with_nonexistent_packages_dir(temp_dir, monkeypatch):
    """Test CLI with non-existent packages directory."""
    packages_dir = temp_dir / "nonexistent"

    monkeypatch.setattr(
        "sys.argv",
        ["validate-manifest-artifacts.py", "--packages-dir", str(packages_dir)],
    )

    main = validate_module.main
    exit_code = main()
    assert exit_code == 1


def test_main_verbose_flag(temp_dir, monkeypatch, sample_manifest, capsys):
    """Test CLI with --verbose flag."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    (package_dir / "commands").mkdir()
    (package_dir / "skills" / "test").mkdir(parents=True)
    (package_dir / "agents").mkdir()
    (package_dir / "scripts").mkdir()

    (package_dir / "commands" / "test.md").write_text("# Command")
    (package_dir / "skills" / "test" / "SKILL.md").write_text("# Skill")
    (package_dir / "agents" / "test.md").write_text("# Agent")
    script = package_dir / "scripts" / "test.py"
    script.write_text("#!/usr/bin/env python3\nprint('test')\n")

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate-manifest-artifacts.py",
            "--packages-dir",
            str(packages_dir),
            "--verbose",
        ],
    )

    main = validate_module.main
    exit_code = main()
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "test-package" in captured.out
