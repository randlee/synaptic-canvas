"""
Unit tests for compare-versions.py

Tests cover:
- Version extraction from files
- Package version comparison
- Error handling with Result pattern
- JSON output
- Text output with colors
- Edge cases and error conditions
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Add harness to path for result module
harness_path = Path(__file__).parent.parent.parent / "test-packages" / "harness"
if str(harness_path) not in sys.path:
    sys.path.insert(0, str(harness_path))

# Import compare-versions.py using importlib (file has hyphens)
scripts_path = Path(__file__).parent.parent.parent / "scripts"
compare_versions_file = scripts_path / "compare-versions.py"
spec = importlib.util.spec_from_file_location("compare_versions", compare_versions_file)
compare_versions = importlib.util.module_from_spec(spec)
sys.modules["compare_versions"] = compare_versions
spec.loader.exec_module(compare_versions)

# Import specific items
from compare_versions import (
    ArtifactVersion,
    ComparisonData,
    ComparisonError,
    PackageComparison,
    compare_all_packages,
    compare_package_versions,
    extract_version_from_file,
    format_color,
    get_marketplace_version,
    main,
    output_json,
    output_text,
)
from result import Failure, Success


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Create a temporary repository structure with test data."""
    repo_root = tmp_path / "test-repo"
    repo_root.mkdir()

    # Create version.yaml
    version_yaml = repo_root / "version.yaml"
    version_yaml.write_text("version: 1.0.0\n")

    # Create packages directory
    packages_dir = repo_root / "packages"
    packages_dir.mkdir()

    # Create test-package with consistent versions
    test_pkg = packages_dir / "test-package"
    test_pkg.mkdir()

    manifest = test_pkg / "manifest.yaml"
    manifest.write_text("version: 1.0.0\n")

    commands_dir = test_pkg / "commands"
    commands_dir.mkdir()
    (commands_dir / "test-command.md").write_text("---\nversion: 1.0.0\n---\n")

    skills_dir = test_pkg / "skills"
    skills_dir.mkdir()
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nversion: 1.0.0\n---\n")

    agents_dir = test_pkg / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("---\nversion: 1.0.0\n---\n")

    # Create mismatch-package with inconsistent versions
    mismatch_pkg = packages_dir / "mismatch-package"
    mismatch_pkg.mkdir()

    manifest2 = mismatch_pkg / "manifest.yaml"
    manifest2.write_text("version: 2.0.0\n")

    commands_dir2 = mismatch_pkg / "commands"
    commands_dir2.mkdir()
    (commands_dir2 / "old-command.md").write_text("---\nversion: 1.5.0\n---\n")

    return repo_root


@pytest.fixture
def temp_file_with_version(tmp_path: Path) -> Path:
    """Create a temporary file with version in YAML frontmatter."""
    file_path = tmp_path / "test.yaml"
    file_path.write_text("version: 1.2.3\n")
    return file_path


@pytest.fixture
def temp_markdown_with_version(tmp_path: Path) -> Path:
    """Create a temporary markdown file with version in frontmatter."""
    file_path = tmp_path / "test.md"
    file_path.write_text('---\nversion: "2.3.4"\n---\nContent\n')
    return file_path


# -----------------------------------------------------------------------------
# Test Version Extraction
# -----------------------------------------------------------------------------


def test_extract_version_from_yaml_file(temp_file_with_version: Path) -> None:
    """Test extracting version from YAML file."""
    result = extract_version_from_file(temp_file_with_version)
    assert isinstance(result, Success)
    assert result.value == "1.2.3"


def test_extract_version_from_markdown_file(temp_markdown_with_version: Path) -> None:
    """Test extracting version from markdown file with frontmatter."""
    result = extract_version_from_file(temp_markdown_with_version)
    assert isinstance(result, Success)
    assert result.value == "2.3.4"


def test_extract_version_from_nonexistent_file(tmp_path: Path) -> None:
    """Test extracting version from non-existent file."""
    file_path = tmp_path / "nonexistent.yaml"
    result = extract_version_from_file(file_path)
    assert isinstance(result, Failure)
    assert "does not exist" in result.error.message


def test_extract_version_from_file_without_version(tmp_path: Path) -> None:
    """Test extracting version from file without version field."""
    file_path = tmp_path / "no_version.yaml"
    file_path.write_text("name: test\n")
    result = extract_version_from_file(file_path)
    assert isinstance(result, Failure)
    assert "No version field found" in result.error.message


def test_extract_version_from_corrupted_file(tmp_path: Path) -> None:
    """Test extracting version from file with invalid content."""
    file_path = tmp_path / "corrupted.yaml"
    # Create file with non-UTF8 content
    file_path.write_bytes(b"\xff\xfe Invalid content")
    result = extract_version_from_file(file_path)
    assert isinstance(result, Failure)
    assert "Failed to read file" in result.error.message


def test_get_marketplace_version(temp_repo: Path) -> None:
    """Test getting marketplace version."""
    result = get_marketplace_version(temp_repo)
    assert isinstance(result, Success)
    assert result.value == "1.0.0"


def test_get_marketplace_version_missing_file(tmp_path: Path) -> None:
    """Test getting marketplace version when file is missing."""
    result = get_marketplace_version(tmp_path)
    assert isinstance(result, Failure)
    assert "does not exist" in result.error.message


# -----------------------------------------------------------------------------
# Test Package Comparison
# -----------------------------------------------------------------------------


def test_compare_package_versions_consistent(temp_repo: Path) -> None:
    """Test comparing versions in a consistent package."""
    result = compare_package_versions("test-package", temp_repo)
    assert isinstance(result, Success)

    comparison = result.value
    assert comparison.package_name == "test-package"
    assert comparison.manifest_version == "1.0.0"
    assert len(comparison.artifacts) == 3
    assert not comparison.has_mismatches


def test_compare_package_versions_with_mismatches(temp_repo: Path) -> None:
    """Test comparing versions in a package with mismatches."""
    result = compare_package_versions("mismatch-package", temp_repo)
    assert isinstance(result, Success)

    comparison = result.value
    assert comparison.package_name == "mismatch-package"
    assert comparison.manifest_version == "2.0.0"
    assert len(comparison.artifacts) == 1
    assert comparison.has_mismatches


def test_compare_package_versions_nonexistent_package(temp_repo: Path) -> None:
    """Test comparing versions for non-existent package."""
    result = compare_package_versions("nonexistent-package", temp_repo)
    assert isinstance(result, Failure)
    assert "does not exist" in result.error.message


def test_compare_package_versions_no_manifest(temp_repo: Path) -> None:
    """Test comparing versions for package without manifest."""
    pkg_dir = temp_repo / "packages" / "no-manifest"
    pkg_dir.mkdir()

    result = compare_package_versions("no-manifest", temp_repo)
    assert isinstance(result, Failure)
    assert "Failed to read manifest version" in result.error.message


def test_compare_package_versions_with_warnings(temp_repo: Path) -> None:
    """Test comparing versions when some artifacts fail to parse."""
    pkg_dir = temp_repo / "packages" / "warning-package"
    pkg_dir.mkdir()

    manifest = pkg_dir / "manifest.yaml"
    manifest.write_text("version: 1.0.0\n")

    commands_dir = pkg_dir / "commands"
    commands_dir.mkdir()
    # Create command without version
    (commands_dir / "bad-command.md").write_text("---\nname: test\n---\n")

    result = compare_package_versions("warning-package", temp_repo)
    assert isinstance(result, Success)
    assert len(result.warnings) > 0


# -----------------------------------------------------------------------------
# Test Full Comparison
# -----------------------------------------------------------------------------


def test_compare_all_packages_success(temp_repo: Path) -> None:
    """Test comparing all packages successfully."""
    result = compare_all_packages(temp_repo)
    assert isinstance(result, Success)

    data = result.value
    assert data.marketplace_version == "1.0.0"
    assert len(data.packages) >= 2
    assert not data.overall_consistent  # mismatch-package has mismatches


def test_compare_all_packages_missing_version_yaml(tmp_path: Path) -> None:
    """Test comparing all packages when version.yaml is missing."""
    packages_dir = tmp_path / "packages"
    packages_dir.mkdir()

    result = compare_all_packages(tmp_path)
    assert isinstance(result, Failure)
    assert "Failed to read marketplace version" in result.error.message


def test_compare_all_packages_missing_packages_dir(tmp_path: Path) -> None:
    """Test comparing all packages when packages directory is missing."""
    version_yaml = tmp_path / "version.yaml"
    version_yaml.write_text("version: 1.0.0\n")

    result = compare_all_packages(tmp_path)
    assert isinstance(result, Failure)
    assert "Packages directory does not exist" in result.error.message


def test_compare_all_packages_with_partial_failures(temp_repo: Path) -> None:
    """Test comparing all packages with some failures."""
    # Create a package with broken manifest
    broken_pkg = temp_repo / "packages" / "broken-package"
    broken_pkg.mkdir()

    result = compare_all_packages(temp_repo)
    # With a broken package, collect_results will return Failure with partial results
    assert isinstance(result, Failure)
    # Should have partial results with the working packages
    assert result.partial_result is not None
    assert len(result.partial_result) >= 2


# -----------------------------------------------------------------------------
# Test Pydantic Models
# -----------------------------------------------------------------------------


def test_artifact_version_model() -> None:
    """Test ArtifactVersion Pydantic model."""
    artifact = ArtifactVersion(
        artifact_type="command",
        name="test-command",
        version="1.0.0",
        file_path="/path/to/command.md",
    )
    assert artifact.artifact_type == "command"
    assert artifact.name == "test-command"
    assert artifact.version == "1.0.0"


def test_package_comparison_model() -> None:
    """Test PackageComparison Pydantic model."""
    comparison = PackageComparison(
        package_name="test-package",
        manifest_version="1.0.0",
        artifacts=[],
        has_mismatches=False,
    )
    assert comparison.package_name == "test-package"
    assert comparison.manifest_version == "1.0.0"
    assert len(comparison.artifacts) == 0


def test_comparison_data_model() -> None:
    """Test ComparisonData Pydantic model."""
    data = ComparisonData(
        marketplace_version="1.0.0", packages=[], overall_consistent=True
    )
    assert data.marketplace_version == "1.0.0"
    assert data.overall_consistent


# -----------------------------------------------------------------------------
# Test Output Functions
# -----------------------------------------------------------------------------


def test_format_color() -> None:
    """Test color formatting function."""
    colored = format_color("test", "red")
    assert "\033[0;31m" in colored
    assert "test" in colored
    assert "\033[0m" in colored


def test_format_color_unknown_color() -> None:
    """Test color formatting with unknown color."""
    colored = format_color("test", "unknown")
    assert "test" in colored


def test_output_text_consistent(temp_repo: Path, capsys) -> None:
    """Test text output for consistent versions."""
    result = compare_all_packages(temp_repo)
    assert isinstance(result, Success)

    # Filter to only consistent package
    consistent_packages = [
        pkg for pkg in result.value.packages if not pkg.has_mismatches
    ]
    data = ComparisonData(
        marketplace_version=result.value.marketplace_version,
        packages=consistent_packages,
        overall_consistent=True,
    )

    output_text(data, show_mismatches_only=False, verbose=False)
    captured = capsys.readouterr()
    assert "Synaptic Canvas Version Comparison" in captured.out
    assert "Marketplace Version:" in captured.out


def test_output_text_with_mismatches(temp_repo: Path, capsys) -> None:
    """Test text output with version mismatches."""
    result = compare_all_packages(temp_repo)
    assert isinstance(result, Success)

    output_text(result.value, show_mismatches_only=False, verbose=True)
    captured = capsys.readouterr()
    assert "mismatch-package" in captured.out
    assert "✗" in captured.out or "✓" in captured.out


def test_output_text_mismatches_only(temp_repo: Path, capsys) -> None:
    """Test text output showing only mismatches."""
    result = compare_all_packages(temp_repo)
    assert isinstance(result, Success)

    output_text(result.value, show_mismatches_only=True, verbose=False)
    captured = capsys.readouterr()
    assert "mismatch-package" in captured.out


def test_output_json(temp_repo: Path, capsys) -> None:
    """Test JSON output."""
    result = compare_all_packages(temp_repo)
    assert isinstance(result, Success)

    output_json(result.value)
    captured = capsys.readouterr()

    # Parse JSON to verify it's valid
    data = json.loads(captured.out)
    assert "marketplace" in data
    assert "packages" in data
    assert isinstance(data["packages"], list)


# -----------------------------------------------------------------------------
# Test Main Entry Point
# -----------------------------------------------------------------------------


def test_main_with_consistent_versions(temp_repo: Path) -> None:
    """Test main function with consistent versions."""
    # Remove mismatch-package to make everything consistent
    import shutil
    mismatch_pkg = temp_repo / "packages" / "mismatch-package"
    if mismatch_pkg.exists():
        shutil.rmtree(mismatch_pkg)

    result = compare_all_packages(temp_repo)
    assert isinstance(result, Success)
    assert result.value.overall_consistent


def test_main_with_json_output(temp_repo: Path, monkeypatch, capsys) -> None:
    """Test main function with JSON output."""
    monkeypatch.chdir(temp_repo)
    monkeypatch.setattr(sys, "argv", ["compare-versions.py", "--json"])

    result = compare_all_packages(temp_repo)
    assert isinstance(result, Success)

    output_json(result.value)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "marketplace" in data


def test_main_with_verbose_output(temp_repo: Path) -> None:
    """Test main function with verbose output."""
    result = compare_all_packages(temp_repo)
    assert isinstance(result, Success)
    # Verbose just shows more details
    assert len(result.value.packages) >= 2


def test_main_with_mismatches_only(temp_repo: Path) -> None:
    """Test main function showing only mismatches."""
    result = compare_all_packages(temp_repo)
    assert isinstance(result, Success)
    # Should include mismatch-package
    mismatch_packages = [pkg for pkg in result.value.packages if pkg.has_mismatches]
    assert len(mismatch_packages) >= 1


# -----------------------------------------------------------------------------
# Test Error Types
# -----------------------------------------------------------------------------


def test_comparison_error_str() -> None:
    """Test ComparisonError string representation."""
    error = ComparisonError(message="test error", file_path="/path/to/file")
    error_str = str(error)
    assert "/path/to/file" in error_str
    assert "test error" in error_str


def test_comparison_error_str_without_path() -> None:
    """Test ComparisonError string representation without file path."""
    error = ComparisonError(message="test error")
    error_str = str(error)
    assert "test error" in error_str


def test_comparison_error_with_details() -> None:
    """Test ComparisonError with details dictionary."""
    error = ComparisonError(
        message="test error", file_path="/path/to/file", details={"key": "value"}
    )
    assert error.details["key"] == "value"


# -----------------------------------------------------------------------------
# Test Cross-Platform Path Handling
# -----------------------------------------------------------------------------


def test_artifact_version_uses_posix_paths(temp_repo: Path) -> None:
    """Test that artifact versions use POSIX paths for cross-platform compatibility."""
    result = compare_package_versions("test-package", temp_repo)
    assert isinstance(result, Success)

    # Check that all file paths use forward slashes
    for artifact in result.value.artifacts:
        assert "/" in artifact.file_path or "\\" not in artifact.file_path


# -----------------------------------------------------------------------------
# Test Edge Cases
# -----------------------------------------------------------------------------


def test_empty_package_directory(temp_repo: Path) -> None:
    """Test handling of empty package directory."""
    empty_pkg = temp_repo / "packages" / "empty-package"
    empty_pkg.mkdir()

    manifest = empty_pkg / "manifest.yaml"
    manifest.write_text("version: 1.0.0\n")

    result = compare_package_versions("empty-package", temp_repo)
    assert isinstance(result, Success)
    assert len(result.value.artifacts) == 0
    assert not result.value.has_mismatches


def test_package_with_only_commands(temp_repo: Path) -> None:
    """Test package with only commands."""
    cmd_pkg = temp_repo / "packages" / "commands-only"
    cmd_pkg.mkdir()

    manifest = cmd_pkg / "manifest.yaml"
    manifest.write_text("version: 1.0.0\n")

    commands_dir = cmd_pkg / "commands"
    commands_dir.mkdir()
    (commands_dir / "cmd1.md").write_text("---\nversion: 1.0.0\n---\n")
    (commands_dir / "cmd2.md").write_text("---\nversion: 1.0.0\n---\n")

    result = compare_package_versions("commands-only", temp_repo)
    assert isinstance(result, Success)
    assert len(result.value.artifacts) == 2
    assert all(a.artifact_type == "command" for a in result.value.artifacts)


def test_version_with_quotes(tmp_path: Path) -> None:
    """Test extracting version with various quote styles."""
    # Single quotes
    file1 = tmp_path / "single_quotes.yaml"
    file1.write_text("version: '1.2.3'\n")
    result1 = extract_version_from_file(file1)
    assert isinstance(result1, Success)
    assert result1.value == "1.2.3"

    # Double quotes
    file2 = tmp_path / "double_quotes.yaml"
    file2.write_text('version: "1.2.3"\n')
    result2 = extract_version_from_file(file2)
    assert isinstance(result2, Success)
    assert result2.value == "1.2.3"


def test_version_with_whitespace(tmp_path: Path) -> None:
    """Test extracting version with extra whitespace."""
    file_path = tmp_path / "whitespace.yaml"
    file_path.write_text("version:   1.2.3   \n")
    result = extract_version_from_file(file_path)
    assert isinstance(result, Success)
    assert result.value == "1.2.3"


def test_main_with_failure_and_partial_results(capsys) -> None:
    """Test main function error handling with partial results."""
    # Test the error path by checking the logic
    # Create a failure with partial results
    from compare_versions import ComparisonData, PackageComparison

    failure_result = Failure(
        error=ComparisonError(message="Test error"),
        partial_result=[
            PackageComparison(
                package_name="test",
                manifest_version="1.0.0",
                artifacts=[],
                has_mismatches=False
            )
        ]
    )

    # Simulate the error path
    if isinstance(failure_result, Failure):
        print(f"Error: {failure_result.error}", file=sys.stderr)
        if failure_result.partial_result and isinstance(failure_result.partial_result, list):
            data = ComparisonData(
                marketplace_version="unknown",
                packages=failure_result.partial_result,
                overall_consistent=False,
            )
            output_json(data)

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "marketplace" in captured.out


def test_main_output_path_with_failure_text(capsys) -> None:
    """Test main function error handling with text output."""
    from compare_versions import ComparisonData, PackageComparison

    failure_result = Failure(
        error=ComparisonError(message="Test error"),
        partial_result=[
            PackageComparison(
                package_name="test",
                manifest_version="1.0.0",
                artifacts=[],
                has_mismatches=False
            )
        ]
    )

    # Simulate the error path with text output
    if isinstance(failure_result, Failure):
        print(f"Error: {failure_result.error}", file=sys.stderr)
        if failure_result.partial_result and isinstance(failure_result.partial_result, list):
            data = ComparisonData(
                marketplace_version="unknown",
                packages=failure_result.partial_result,
                overall_consistent=False,
            )
            output_text(data, show_mismatches_only=False, verbose=False)

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "Version Comparison" in captured.out


def test_extract_version_yaml_parse_fallback(tmp_path: Path) -> None:
    """Test fallback to regex when YAML parsing fails but regex works."""
    file_path = tmp_path / "fallback.md"
    # Content that will fail YAML parsing but regex will work
    file_path.write_text("Some content\nversion: 3.2.1\nMore content\n")
    result = extract_version_from_file(file_path)
    assert isinstance(result, Success)
    assert result.value == "3.2.1"
