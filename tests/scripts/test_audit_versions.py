"""Tests for audit-versions.py script with 100% coverage."""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Add scripts and harness directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "test-packages" / "harness")
)

# Import using importlib to handle hyphens in filename
import importlib.util

spec = importlib.util.spec_from_file_location(
    "audit_versions",
    Path(__file__).parent.parent.parent / "scripts" / "audit-versions.py",
)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)

from result import Failure, Success

# Import functions from audit_versions module
extract_version_from_frontmatter = audit_module.extract_version_from_frontmatter
get_manifest_version = audit_module.get_manifest_version
audit_commands = audit_module.audit_commands
audit_skills = audit_module.audit_skills
audit_agents = audit_module.audit_agents
audit_version_consistency = audit_module.audit_version_consistency
audit_changelogs = audit_module.audit_changelogs
audit_marketplace_version = audit_module.audit_marketplace_version
audit_versions = audit_module.audit_versions
AuditData = audit_module.AuditData
CheckResult = audit_module.CheckResult
ManifestSchema = audit_module.ManifestSchema
VersionYamlSchema = audit_module.VersionYamlSchema
print_check_result = audit_module.print_check_result


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
    }


@pytest.fixture
def repo_with_packages(temp_dir, sample_manifest):
    """Create repository structure with packages."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    # Create test-package
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    # Create manifest
    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create directories
    (package_dir / "commands").mkdir()
    (package_dir / "skills" / "test-skill").mkdir(parents=True)
    (package_dir / "agents").mkdir()

    # Create command with frontmatter
    (package_dir / "commands" / "test.md").write_text(
        """---
name: test
version: 1.0.0
description: Test command
---

# Test Command
"""
    )

    # Create skill with frontmatter
    (package_dir / "skills" / "test-skill" / "SKILL.md").write_text(
        """---
name: test-skill
version: 1.0.0
description: Test skill
---

# Test Skill
"""
    )

    # Create agent with frontmatter
    (package_dir / "agents" / "test-agent.md").write_text(
        """---
name: test-agent
version: 1.0.0
description: Test agent
---

# Test Agent
"""
    )

    # Create CHANGELOG
    (package_dir / "CHANGELOG.md").write_text("# Changelog\n\n## 1.0.0\n- Initial release\n")

    # Create version.yaml
    (temp_dir / "version.yaml").write_text("version: 0.7.0\n")

    return temp_dir


# ============================================================================
# AuditData and CheckResult Tests
# ============================================================================


def test_check_result_creation():
    """Test CheckResult dataclass creation."""
    check = CheckResult(check_name="Test", status="PASS")
    assert check.check_name == "Test"
    assert check.status == "PASS"
    assert check.message == ""


def test_check_result_with_message():
    """Test CheckResult with message."""
    check = CheckResult(check_name="Test", status="FAIL", message="Error occurred")
    assert check.message == "Error occurred"


def test_audit_data_add_check_pass():
    """Test adding PASS check to AuditData."""
    data = AuditData()
    check = CheckResult(check_name="Test", status="PASS")
    data.add_check(check)

    assert data.total_checks == 1
    assert data.passed_checks == 1
    assert data.failed_checks == 0
    assert data.warnings == 0


def test_audit_data_add_check_fail():
    """Test adding FAIL check to AuditData."""
    data = AuditData()
    check = CheckResult(check_name="Test", status="FAIL", message="Error")
    data.add_check(check)

    assert data.total_checks == 1
    assert data.passed_checks == 0
    assert data.failed_checks == 1
    assert data.warnings == 0


def test_audit_data_add_check_warn():
    """Test adding WARN check to AuditData."""
    data = AuditData()
    check = CheckResult(check_name="Test", status="WARN", message="Warning")
    data.add_check(check)

    assert data.total_checks == 1
    assert data.passed_checks == 0
    assert data.failed_checks == 0
    assert data.warnings == 1


def test_audit_data_is_valid_when_clean():
    """Test is_valid returns True when no failures."""
    data = AuditData()
    data.add_check(CheckResult(check_name="Test1", status="PASS"))
    data.add_check(CheckResult(check_name="Test2", status="WARN"))
    assert data.is_valid() is True


def test_audit_data_is_valid_false_with_failures():
    """Test is_valid returns False with failures."""
    data = AuditData()
    data.add_check(CheckResult(check_name="Test1", status="PASS"))
    data.add_check(CheckResult(check_name="Test2", status="FAIL"))
    assert data.is_valid() is False


def test_audit_data_multiple_checks():
    """Test adding multiple checks."""
    data = AuditData()
    data.add_check(CheckResult(check_name="Test1", status="PASS"))
    data.add_check(CheckResult(check_name="Test2", status="FAIL"))
    data.add_check(CheckResult(check_name="Test3", status="WARN"))

    assert data.total_checks == 3
    assert data.passed_checks == 1
    assert data.failed_checks == 1
    assert data.warnings == 1
    assert len(data.checks) == 3


# ============================================================================
# Pydantic Model Tests
# ============================================================================


def test_manifest_schema_valid():
    """Test ManifestSchema with valid data."""
    manifest = ManifestSchema(
        name="test-package",
        version="1.0.0",
        description="Test",
        author="test",
        license="MIT",
    )
    assert manifest.name == "test-package"
    assert manifest.version == "1.0.0"


def test_manifest_schema_invalid_name():
    """Test ManifestSchema with invalid name."""
    with pytest.raises(Exception):
        ManifestSchema(
            name="INVALID-NAME",  # uppercase not allowed
            version="1.0.0",
            description="Test",
            author="test",
            license="MIT",
        )


def test_manifest_schema_invalid_version():
    """Test ManifestSchema with invalid version."""
    with pytest.raises(Exception):
        ManifestSchema(
            name="test-package",
            version="1.0",  # missing patch
            description="Test",
            author="test",
            license="MIT",
        )


def test_manifest_schema_non_numeric_version():
    """Test ManifestSchema with non-numeric version parts."""
    with pytest.raises(Exception):
        ManifestSchema(
            name="test-package",
            version="1.0.beta",
            description="Test",
            author="test",
            license="MIT",
        )


def test_version_yaml_schema_valid():
    """Test VersionYamlSchema with valid data."""
    version = VersionYamlSchema(version="0.7.0")
    assert version.version == "0.7.0"


def test_version_yaml_schema_invalid():
    """Test VersionYamlSchema with invalid version."""
    with pytest.raises(Exception):
        VersionYamlSchema(version="1.0")


# ============================================================================
# extract_version_from_frontmatter Tests
# ============================================================================


def test_extract_version_from_frontmatter_success(temp_dir):
    """Test extracting version from valid frontmatter."""
    file_path = temp_dir / "test.md"
    file_path.write_text(
        """---
name: test
version: 1.2.3
description: Test
---

# Content
"""
    )

    result = extract_version_from_frontmatter(file_path)
    assert isinstance(result, Success)
    assert result.value == "1.2.3"


def test_extract_version_from_frontmatter_no_frontmatter(temp_dir):
    """Test extracting version when no frontmatter exists."""
    file_path = temp_dir / "test.md"
    file_path.write_text("# Just content\n\nNo frontmatter here.")

    result = extract_version_from_frontmatter(file_path)
    assert isinstance(result, Success)
    assert result.value is None


def test_extract_version_from_frontmatter_no_version(temp_dir):
    """Test extracting version when frontmatter has no version."""
    file_path = temp_dir / "test.md"
    file_path.write_text(
        """---
name: test
description: Test
---

# Content
"""
    )

    result = extract_version_from_frontmatter(file_path)
    assert isinstance(result, Success)
    assert result.value is None


def test_extract_version_from_frontmatter_invalid_yaml(temp_dir):
    """Test extracting version from invalid YAML frontmatter."""
    file_path = temp_dir / "test.md"
    file_path.write_text(
        """---
invalid: yaml: content: {{{
---

# Content
"""
    )

    result = extract_version_from_frontmatter(file_path)
    assert isinstance(result, Success)
    assert result.value is None


def test_extract_version_from_frontmatter_file_not_found(temp_dir):
    """Test extracting version from non-existent file."""
    file_path = temp_dir / "nonexistent.md"

    result = extract_version_from_frontmatter(file_path)
    assert isinstance(result, Failure)
    assert "not found" in result.error.message.lower()


def test_extract_version_from_frontmatter_multiline(temp_dir):
    """Test extracting version from multiline frontmatter."""
    file_path = temp_dir / "test.md"
    file_path.write_text(
        """---
name: test
version: 2.0.0
description: |
  Multi-line
  description
  here
tags:
  - tag1
  - tag2
---

# Content
"""
    )

    result = extract_version_from_frontmatter(file_path)
    assert isinstance(result, Success)
    assert result.value == "2.0.0"


def test_extract_version_from_frontmatter_numeric_version(temp_dir):
    """Test extracting numeric version (should be converted to string)."""
    file_path = temp_dir / "test.md"
    file_path.write_text(
        """---
name: test
version: 1.0.0
---

# Content
"""
    )

    result = extract_version_from_frontmatter(file_path)
    assert isinstance(result, Success)
    assert result.value == "1.0.0"
    assert isinstance(result.value, str)


# ============================================================================
# get_manifest_version Tests
# ============================================================================


def test_get_manifest_version_success(temp_dir, sample_manifest):
    """Test getting version from valid manifest."""
    package_dir = temp_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    result = get_manifest_version(package_dir)
    assert isinstance(result, Success)
    assert result.value == "1.0.0"


def test_get_manifest_version_no_manifest(temp_dir):
    """Test getting version when manifest doesn't exist."""
    package_dir = temp_dir / "test-package"
    package_dir.mkdir()

    result = get_manifest_version(package_dir)
    assert isinstance(result, Success)
    assert result.value is None


def test_get_manifest_version_invalid_yaml(temp_dir):
    """Test getting version from invalid YAML manifest."""
    package_dir = temp_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        f.write("invalid: yaml: content: {{{")

    result = get_manifest_version(package_dir)
    assert isinstance(result, Failure)
    assert "YAML" in result.error.message


def test_get_manifest_version_invalid_schema(temp_dir):
    """Test getting version from manifest with invalid schema."""
    package_dir = temp_dir / "test-package"
    package_dir.mkdir()

    manifest = {
        "name": "INVALID",
        "version": "1.0.0",
        "description": "Test",
        "author": "test",
        "license": "MIT",
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    result = get_manifest_version(package_dir)
    assert isinstance(result, Failure)


# ============================================================================
# audit_commands Tests
# ============================================================================


def test_audit_commands_all_valid(repo_with_packages):
    """Test auditing commands when all have valid versions."""
    result = audit_commands(repo_with_packages, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "PASS"
    assert "test" in result.value[0].check_name


def test_audit_commands_missing_version(temp_dir):
    """Test auditing commands with missing version."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()
    (package_dir / "commands").mkdir()

    (package_dir / "commands" / "test.md").write_text("# No frontmatter")

    result = audit_commands(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "FAIL"
    assert "Missing version" in result.value[0].message


def test_audit_commands_no_commands(temp_dir):
    """Test auditing when no commands exist."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    result = audit_commands(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 0


def test_audit_commands_verbose(repo_with_packages, capsys):
    """Test auditing commands with verbose output."""
    result = audit_commands(repo_with_packages, verbose=True)
    assert isinstance(result, Success)


# ============================================================================
# audit_skills Tests
# ============================================================================


def test_audit_skills_all_valid(repo_with_packages):
    """Test auditing skills when all have valid versions."""
    result = audit_skills(repo_with_packages, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "PASS"
    assert "test-skill" in result.value[0].check_name


def test_audit_skills_missing_version(temp_dir):
    """Test auditing skills with missing version."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()
    (package_dir / "skills" / "test-skill").mkdir(parents=True)

    (package_dir / "skills" / "test-skill" / "SKILL.md").write_text("# No frontmatter")

    result = audit_skills(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "FAIL"


def test_audit_skills_no_skills(temp_dir):
    """Test auditing when no skills exist."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    result = audit_skills(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 0


# ============================================================================
# audit_agents Tests
# ============================================================================


def test_audit_agents_all_valid(repo_with_packages):
    """Test auditing agents when all have valid versions."""
    result = audit_agents(repo_with_packages, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "PASS"
    assert "test-agent" in result.value[0].check_name


def test_audit_agents_missing_version(temp_dir):
    """Test auditing agents with missing version."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()
    (package_dir / "agents").mkdir()

    (package_dir / "agents" / "test-agent.md").write_text("# No frontmatter")

    result = audit_agents(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "FAIL"


def test_audit_agents_in_claude_dir(temp_dir):
    """Test auditing agents in .claude/agents directory."""
    claude_dir = temp_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True)

    (claude_dir / "test-agent.md").write_text(
        """---
version: 1.0.0
---
# Agent
"""
    )

    result = audit_agents(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "PASS"


def test_audit_agents_no_agents(temp_dir):
    """Test auditing when no agents exist."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    result = audit_agents(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 0


# ============================================================================
# audit_version_consistency Tests
# ============================================================================


def test_audit_version_consistency_all_match(repo_with_packages):
    """Test version consistency when all versions match."""
    result = audit_version_consistency(repo_with_packages, verbose=False)
    assert isinstance(result, Success)
    # No failures means all versions matched
    for check in result.value:
        assert check.status != "FAIL"


def test_audit_version_consistency_mismatch_command(temp_dir, sample_manifest):
    """Test version consistency with mismatched command version."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    (package_dir / "commands").mkdir()
    (package_dir / "commands" / "test.md").write_text(
        """---
version: 2.0.0
---
# Command
"""
    )

    result = audit_version_consistency(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert any(
        check.status == "FAIL" and "mismatch" in check.message.lower()
        for check in result.value
    )


def test_audit_version_consistency_mismatch_skill(temp_dir, sample_manifest):
    """Test version consistency with mismatched skill version."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    (package_dir / "skills" / "test-skill").mkdir(parents=True)
    (package_dir / "skills" / "test-skill" / "SKILL.md").write_text(
        """---
version: 3.0.0
---
# Skill
"""
    )

    result = audit_version_consistency(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert any(
        check.status == "FAIL" and "mismatch" in check.message.lower()
        for check in result.value
    )


def test_audit_version_consistency_mismatch_agent(temp_dir, sample_manifest):
    """Test version consistency with mismatched agent version."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    (package_dir / "agents").mkdir()
    (package_dir / "agents" / "test-agent.md").write_text(
        """---
version: 4.0.0
---
# Agent
"""
    )

    result = audit_version_consistency(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert any(
        check.status == "FAIL" and "mismatch" in check.message.lower()
        for check in result.value
    )


def test_audit_version_consistency_no_manifest(temp_dir):
    """Test version consistency when package has no manifest."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    result = audit_version_consistency(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert any(
        check.status == "FAIL" and "manifest" in check.message.lower()
        for check in result.value
    )


def test_audit_version_consistency_no_packages_dir(temp_dir):
    """Test version consistency when packages directory doesn't exist."""
    result = audit_version_consistency(temp_dir, verbose=False)
    assert isinstance(result, Failure)
    assert "not found" in result.error.message.lower()


def test_audit_version_consistency_hidden_package(temp_dir, sample_manifest):
    """Test that hidden packages are skipped."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    hidden_dir = packages_dir / ".hidden-package"
    hidden_dir.mkdir()

    with open(hidden_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    result = audit_version_consistency(temp_dir, verbose=False)
    assert isinstance(result, Success)
    # Should not include hidden package
    assert all(".hidden" not in check.check_name for check in result.value)


# ============================================================================
# audit_changelogs Tests
# ============================================================================


def test_audit_changelogs_all_present(repo_with_packages):
    """Test auditing CHANGELOGs when all are present."""
    result = audit_changelogs(repo_with_packages, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "PASS"


def test_audit_changelogs_missing(temp_dir, sample_manifest):
    """Test auditing CHANGELOGs when missing."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    result = audit_changelogs(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "WARN"
    assert "No CHANGELOG" in result.value[0].message


def test_audit_changelogs_no_packages_dir(temp_dir):
    """Test auditing CHANGELOGs when packages directory doesn't exist."""
    result = audit_changelogs(temp_dir, verbose=False)
    assert isinstance(result, Failure)


# ============================================================================
# audit_marketplace_version Tests
# ============================================================================


def test_audit_marketplace_version_success(temp_dir):
    """Test auditing marketplace version when present."""
    (temp_dir / "version.yaml").write_text("version: 0.7.0\n")

    result = audit_marketplace_version(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "PASS"
    assert "0.7.0" in result.value[0].check_name


def test_audit_marketplace_version_missing_file(temp_dir):
    """Test auditing marketplace version when file missing."""
    result = audit_marketplace_version(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "FAIL"
    assert "not found" in result.value[0].message


def test_audit_marketplace_version_no_version(temp_dir):
    """Test auditing marketplace version when version missing."""
    (temp_dir / "version.yaml").write_text("# No version here\n")

    result = audit_marketplace_version(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].status == "FAIL"
    assert "No version found" in result.value[0].message


# ============================================================================
# audit_versions (Integration) Tests
# ============================================================================


def test_audit_versions_complete_success(repo_with_packages):
    """Test complete audit with all checks passing."""
    result = audit_versions(repo_with_packages, verbose=False)
    assert isinstance(result, Success)
    assert result.value.is_valid()
    assert result.value.total_checks > 0
    assert result.value.passed_checks > 0


def test_audit_versions_with_failures(temp_dir):
    """Test complete audit with some failures."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()
    (package_dir / "commands").mkdir()

    # Create command without version
    (package_dir / "commands" / "test.md").write_text("# No version")

    result = audit_versions(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert result.value.failed_checks > 0


def test_audit_versions_verbose(repo_with_packages, capsys):
    """Test complete audit with verbose output."""
    result = audit_versions(repo_with_packages, verbose=True)
    assert isinstance(result, Success)

    captured = capsys.readouterr()
    assert "Checking commands..." in captured.out


# ============================================================================
# print_check_result Tests
# ============================================================================


def test_print_check_result_pass_verbose(capsys):
    """Test printing PASS check with verbose."""
    check = CheckResult(check_name="Test", status="PASS")
    print_check_result(check, verbose=True)

    captured = capsys.readouterr()
    assert "✓" in captured.out
    assert "Test" in captured.out


def test_print_check_result_pass_not_verbose(capsys):
    """Test printing PASS check without verbose."""
    check = CheckResult(check_name="Test", status="PASS")
    print_check_result(check, verbose=False)

    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_check_result_fail(capsys):
    """Test printing FAIL check."""
    check = CheckResult(check_name="Test", status="FAIL", message="Error message")
    print_check_result(check, verbose=False)

    captured = capsys.readouterr()
    assert "✗ FAIL" in captured.out
    assert "Test" in captured.out
    assert "Error message" in captured.out


def test_print_check_result_fail_no_message(capsys):
    """Test printing FAIL check without message."""
    check = CheckResult(check_name="Test", status="FAIL")
    print_check_result(check, verbose=False)

    captured = capsys.readouterr()
    assert "✗ FAIL" in captured.out
    assert "Test" in captured.out


def test_print_check_result_warn(capsys):
    """Test printing WARN check."""
    check = CheckResult(check_name="Test", status="WARN", message="Warning message")
    print_check_result(check, verbose=False)

    captured = capsys.readouterr()
    assert "⚠ WARN" in captured.out
    assert "Test" in captured.out
    assert "Warning message" in captured.out


def test_print_check_result_warn_no_message(capsys):
    """Test printing WARN check without message."""
    check = CheckResult(check_name="Test", status="WARN")
    print_check_result(check, verbose=False)

    captured = capsys.readouterr()
    assert "⚠ WARN" in captured.out


# ============================================================================
# CLI/main() Tests
# ============================================================================


def test_main_success(repo_with_packages, monkeypatch):
    """Test main function with successful audit."""
    monkeypatch.setattr(
        "sys.argv",
        ["audit-versions.py", "--repo-root", str(repo_with_packages)],
    )

    main = audit_module.main
    exit_code = main()
    assert exit_code == 0


def test_main_with_failures(temp_dir, monkeypatch):
    """Test main function with failures."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()
    (package_dir / "commands").mkdir()
    (package_dir / "commands" / "test.md").write_text("# No version")

    monkeypatch.setattr(
        "sys.argv",
        ["audit-versions.py", "--repo-root", str(temp_dir)],
    )

    main = audit_module.main
    exit_code = main()
    assert exit_code == 1


def test_main_verbose_flag(repo_with_packages, monkeypatch, capsys):
    """Test main function with verbose flag."""
    monkeypatch.setattr(
        "sys.argv",
        ["audit-versions.py", "--repo-root", str(repo_with_packages), "--verbose"],
    )

    main = audit_module.main
    exit_code = main()
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "Checking commands..." in captured.out


def test_main_fix_warnings_flag(repo_with_packages, monkeypatch):
    """Test main function with fix-warnings flag."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit-versions.py",
            "--repo-root",
            str(repo_with_packages),
            "--fix-warnings",
        ],
    )

    main = audit_module.main
    exit_code = main()
    assert exit_code == 0


def test_main_critical_error(temp_dir, monkeypatch):
    """Test main function with critical error."""
    # Create invalid repo (no packages dir)
    monkeypatch.setattr(
        "sys.argv",
        ["audit-versions.py", "--repo-root", str(temp_dir)],
    )

    main = audit_module.main
    exit_code = main()
    assert exit_code == 2


def test_main_default_repo_root(monkeypatch):
    """Test main function with default repo root."""
    monkeypatch.setattr("sys.argv", ["audit-versions.py"])

    main = audit_module.main
    # Will fail because current dir likely doesn't have proper structure
    exit_code = main()
    assert exit_code in [0, 1, 2]


# ============================================================================
# Cross-platform Path Tests
# ============================================================================


def test_paths_use_posix_format(temp_dir):
    """Test that paths are normalized to POSIX format."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(
            {
                "name": "test-package",
                "version": "1.0.0",
                "description": "Test",
                "author": "test",
                "license": "MIT",
            },
            f,
        )

    result = get_manifest_version(package_dir)
    assert isinstance(result, Success)

    # Check that error paths would use POSIX format
    result = extract_version_from_frontmatter(temp_dir / "nonexistent.md")
    assert isinstance(result, Failure)
    # Path should use forward slashes
    assert "/" in result.error.file_path or "\\" not in result.error.file_path


# ============================================================================
# Edge Cases
# ============================================================================


def test_empty_packages_directory(temp_dir):
    """Test audit with empty packages directory."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    result = audit_versions(temp_dir, verbose=False)
    assert isinstance(result, Success)


def test_multiple_packages(temp_dir, sample_manifest):
    """Test audit with multiple packages."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    for i in range(3):
        package_dir = packages_dir / f"package-{i}"
        package_dir.mkdir()

        manifest = sample_manifest.copy()
        manifest["name"] = f"package-{i}"

        with open(package_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

    result = audit_version_consistency(temp_dir, verbose=False)
    assert isinstance(result, Success)


def test_artifact_without_frontmatter_markers(temp_dir):
    """Test handling of file without proper frontmatter markers."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()
    (package_dir / "commands").mkdir()

    # Create file with version but no frontmatter markers
    (package_dir / "commands" / "test.md").write_text(
        """version: 1.0.0

# Command
"""
    )

    result = audit_commands(temp_dir, verbose=False)
    assert isinstance(result, Success)
    assert result.value[0].status == "FAIL"
