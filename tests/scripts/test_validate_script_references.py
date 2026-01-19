"""Comprehensive tests for validate-script-references.py script."""

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "test-packages" / "harness"))

# Import script module
import importlib.util

spec = importlib.util.spec_from_file_location(
    "validate_script_references",
    Path(__file__).parent.parent.parent / "scripts" / "validate-script-references.py",
)
validate_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validate_module
spec.loader.exec_module(validate_module)

# Import functions and classes
extract_frontmatter = validate_module.extract_frontmatter
extract_script_references_from_hooks = validate_module.extract_script_references_from_hooks
extract_script_references_from_manifest = validate_module.extract_script_references_from_manifest
validate_script_exists = validate_module.validate_script_exists
validate_script_is_python = validate_module.validate_script_is_python
validate_shebang = validate_module.validate_shebang
validate_script_in_package_dir = validate_module.validate_script_in_package_dir
validate_script_reference = validate_module.validate_script_reference
validate_package_scripts = validate_module.validate_package_scripts
validate_all_packages = validate_module.validate_all_packages
find_packages = validate_module.find_packages
ScriptReference = validate_module.ScriptReference
ScriptReferenceError = validate_module.ScriptReferenceError
ValidatedScriptReference = validate_module.ValidatedScriptReference

from result import Success, Failure


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_manifest_with_scripts():
    """Sample manifest with script references."""
    return {
        "name": "test-package",
        "version": "0.7.0",
        "description": "Test package",
        "artifacts": {
            "scripts": [
                "scripts/test_script.py",
                "scripts/helper.py",
            ],
            "agents": [
                "agents/agent1.md",
                "agents/agent_impl.py",
            ],
        },
    }


@pytest.fixture
def sample_frontmatter_with_hooks():
    """Sample frontmatter with hook references."""
    return {
        "name": "test-agent",
        "version": "0.7.0",
        "description": "Test agent",
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 scripts/validate_hook.py",
                        }
                    ],
                }
            ],
        },
    }


def create_markdown_file(path: Path, frontmatter: Dict[str, Any], content: str = "") -> None:
    """Helper to create markdown file with frontmatter."""
    yaml_content = yaml.dump(frontmatter, default_flow_style=False)
    full_content = f"---\n{yaml_content}---\n\n{content}"
    path.write_text(full_content, encoding="utf-8")


def create_python_script(path: Path, with_shebang: bool = True, shebang: str = "#!/usr/bin/env python3") -> None:
    """Helper to create Python script."""
    content = ""
    if with_shebang:
        content = f"{shebang}\n"
    content += '"""Test script."""\n\nif __name__ == "__main__":\n    print("test")\n'
    path.write_text(content, encoding="utf-8")


# -----------------------------------------------------------------------------
# Test Frontmatter Extraction
# -----------------------------------------------------------------------------


def test_extract_frontmatter_valid(temp_dir, sample_frontmatter_with_hooks):
    """Test extracting valid frontmatter."""
    file_path = temp_dir / "test.md"
    create_markdown_file(file_path, sample_frontmatter_with_hooks)

    result = extract_frontmatter(str(file_path))
    assert isinstance(result, Success)
    assert "hooks" in result.value


def test_extract_frontmatter_no_frontmatter(temp_dir):
    """Test extracting from file without frontmatter."""
    file_path = temp_dir / "test.md"
    file_path.write_text("# Just content")

    result = extract_frontmatter(str(file_path))
    assert isinstance(result, Success)
    assert result.value == {}
    assert "No frontmatter found" in result.warnings[0]


def test_extract_frontmatter_missing_file(temp_dir):
    """Test extracting from non-existent file."""
    result = extract_frontmatter(str(temp_dir / "missing.md"))
    assert isinstance(result, Failure)
    assert "Failed to read file" in result.error.message


def test_extract_frontmatter_invalid_yaml(temp_dir):
    """Test file with invalid YAML."""
    file_path = temp_dir / "test.md"
    file_path.write_text("---\ninvalid: yaml: content: :\n---\n")

    result = extract_frontmatter(str(file_path))
    assert isinstance(result, Failure)
    assert "Invalid YAML" in result.error.message


# -----------------------------------------------------------------------------
# Test Hook Reference Extraction
# -----------------------------------------------------------------------------


def test_extract_script_references_from_hooks_valid(sample_frontmatter_with_hooks):
    """Test extracting script references from hooks."""
    references = extract_script_references_from_hooks(
        "/test/agent.md", sample_frontmatter_with_hooks
    )
    assert len(references) == 1
    assert references[0].script_path == "scripts/validate_hook.py"
    assert references[0].reference_type == "hook"
    assert references[0].hook_type == "PreToolUse"


def test_extract_script_references_from_hooks_no_hooks():
    """Test extracting when no hooks present."""
    frontmatter = {
        "name": "test",
        "version": "1.0.0",
        "description": "Test",
    }
    references = extract_script_references_from_hooks("/test/agent.md", frontmatter)
    assert len(references) == 0


def test_extract_script_references_from_hooks_multiple():
    """Test extracting multiple hook references."""
    frontmatter = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": "python3 scripts/hook1.py"},
                        {"type": "command", "command": "python3 scripts/hook2.py"},
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Read",
                    "hooks": [
                        {"type": "command", "command": "python3 scripts/hook3.py"},
                    ],
                }
            ],
        }
    }
    references = extract_script_references_from_hooks("/test/agent.md", frontmatter)
    assert len(references) == 3
    assert references[0].hook_type == "PreToolUse"
    assert references[2].hook_type == "PostToolUse"


def test_extract_script_references_from_hooks_invalid_structure():
    """Test extracting with invalid hook structure."""
    frontmatter = {
        "hooks": "invalid",  # Should be dict
    }
    references = extract_script_references_from_hooks("/test/agent.md", frontmatter)
    assert len(references) == 0


# -----------------------------------------------------------------------------
# Test Manifest Reference Extraction
# -----------------------------------------------------------------------------


def test_extract_script_references_from_manifest_valid(temp_dir, sample_manifest_with_scripts):
    """Test extracting script references from manifest."""
    manifest_path = temp_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest_with_scripts, f)

    result = extract_script_references_from_manifest(str(manifest_path))
    assert isinstance(result, Success)
    assert len(result.value) == 3  # 2 scripts + 1 agent .py file
    assert any(ref.script_path == "scripts/test_script.py" for ref in result.value)
    assert any(ref.script_path == "agents/agent_impl.py" for ref in result.value)


def test_extract_script_references_from_manifest_no_scripts(temp_dir):
    """Test extracting from manifest with no scripts."""
    manifest = {
        "name": "test",
        "version": "1.0.0",
        "description": "Test",
        "artifacts": {
            "commands": ["cmd.md"],
        },
    }
    manifest_path = temp_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)

    result = extract_script_references_from_manifest(str(manifest_path))
    assert isinstance(result, Success)
    assert len(result.value) == 0


def test_extract_script_references_from_manifest_missing_file(temp_dir):
    """Test extracting from non-existent manifest."""
    result = extract_script_references_from_manifest(str(temp_dir / "missing.yaml"))
    assert isinstance(result, Failure)
    assert "Failed to read manifest" in result.error.message


def test_extract_script_references_from_manifest_invalid_yaml(temp_dir):
    """Test extracting from invalid YAML manifest."""
    manifest_path = temp_dir / "manifest.yaml"
    manifest_path.write_text("invalid: yaml: content: :")

    result = extract_script_references_from_manifest(str(manifest_path))
    assert isinstance(result, Failure)


# -----------------------------------------------------------------------------
# Test Script Existence Validation
# -----------------------------------------------------------------------------


def test_validate_script_exists_valid(temp_dir):
    """Test validating script that exists."""
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / "test.py"
    create_python_script(script_path)

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="scripts/test.py",
        reference_type="hook",
    )

    result = validate_script_exists(reference, str(temp_dir))
    assert isinstance(result, Success)
    assert result.value.endswith("test.py")


def test_validate_script_exists_missing(temp_dir):
    """Test validating script that doesn't exist."""
    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="scripts/missing.py",
        reference_type="hook",
    )

    result = validate_script_exists(reference, str(temp_dir))
    assert isinstance(result, Failure)
    assert "does not exist" in result.error.message


def test_validate_script_exists_is_directory(temp_dir):
    """Test validating when path is a directory."""
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="scripts",
        reference_type="hook",
    )

    result = validate_script_exists(reference, str(temp_dir))
    assert isinstance(result, Failure)
    assert "not a file" in result.error.message


# -----------------------------------------------------------------------------
# Test Python File Validation
# -----------------------------------------------------------------------------


def test_validate_script_is_python_valid(temp_dir):
    """Test validating Python file."""
    script_path = str(temp_dir / "test.py")
    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="test.py",
        reference_type="hook",
    )

    result = validate_script_is_python(script_path, reference)
    assert isinstance(result, Success)


def test_validate_script_is_python_invalid(temp_dir):
    """Test validating non-Python file."""
    script_path = str(temp_dir / "test.sh")
    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="test.sh",
        reference_type="hook",
    )

    result = validate_script_is_python(script_path, reference)
    assert isinstance(result, Failure)
    assert "must be a Python file" in result.error.message


# -----------------------------------------------------------------------------
# Test Shebang Validation
# -----------------------------------------------------------------------------


def test_validate_shebang_valid(temp_dir):
    """Test validating script with proper shebang."""
    script_path = temp_dir / "test.py"
    create_python_script(script_path, with_shebang=True)

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="test.py",
        reference_type="hook",
    )

    result = validate_shebang(str(script_path), reference)
    assert isinstance(result, Success)
    has_shebang, shebang_line = result.value
    assert has_shebang
    assert "python" in shebang_line.lower()


def test_validate_shebang_missing(temp_dir):
    """Test validating script without shebang."""
    script_path = temp_dir / "test.py"
    create_python_script(script_path, with_shebang=False)

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="test.py",
        reference_type="hook",
    )

    result = validate_shebang(str(script_path), reference)
    assert isinstance(result, Success)
    has_shebang, shebang_line = result.value
    assert not has_shebang
    assert shebang_line is None
    assert "missing shebang" in result.warnings[0]


def test_validate_shebang_non_python(temp_dir):
    """Test validating script with non-Python shebang."""
    script_path = temp_dir / "test.py"
    create_python_script(script_path, with_shebang=True, shebang="#!/bin/bash")

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="test.py",
        reference_type="hook",
    )

    result = validate_shebang(str(script_path), reference)
    assert isinstance(result, Success)
    has_shebang, shebang_line = result.value
    assert has_shebang
    assert "does not reference Python" in result.warnings[0]


# -----------------------------------------------------------------------------
# Test Package Directory Validation
# -----------------------------------------------------------------------------


def test_validate_script_in_package_dir_valid(temp_dir):
    """Test validating script in package directory."""
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / "test.py"
    create_python_script(script_path)

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="scripts/test.py",
        reference_type="hook",
    )

    result = validate_script_in_package_dir(reference, str(temp_dir))
    assert isinstance(result, Success)


def test_validate_script_in_package_dir_outside(temp_dir):
    """Test validating script outside package directory."""
    # Create script outside temp_dir
    outside_script = temp_dir.parent / "outside.py"
    create_python_script(outside_script)

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="../outside.py",
        reference_type="hook",
    )

    result = validate_script_in_package_dir(reference, str(temp_dir))
    assert isinstance(result, Failure)
    assert "outside package directory" in result.error.message


# -----------------------------------------------------------------------------
# Test Complete Script Reference Validation
# -----------------------------------------------------------------------------


def test_validate_script_reference_valid(temp_dir):
    """Test complete validation pipeline for valid script."""
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / "test.py"
    create_python_script(script_path, with_shebang=True)

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="scripts/test.py",
        reference_type="hook",
    )

    result = validate_script_reference(reference, str(temp_dir))
    assert isinstance(result, Success)
    assert result.value.has_shebang
    assert "python" in result.value.shebang_line.lower()


def test_validate_script_reference_missing(temp_dir):
    """Test validation for missing script."""
    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="scripts/missing.py",
        reference_type="hook",
    )

    result = validate_script_reference(reference, str(temp_dir))
    assert isinstance(result, Failure)


def test_validate_script_reference_not_python(temp_dir):
    """Test validation for non-Python script."""
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / "test.sh"
    script_path.write_text("#!/bin/bash\necho test")

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="scripts/test.sh",
        reference_type="hook",
    )

    result = validate_script_reference(reference, str(temp_dir))
    assert isinstance(result, Failure)


# -----------------------------------------------------------------------------
# Test Package-Level Validation
# -----------------------------------------------------------------------------


def test_validate_package_scripts_valid(temp_dir):
    """Test validating package with valid scripts."""
    # Create manifest
    manifest = {
        "name": "test-pkg",
        "version": "0.7.0",
        "description": "Test",
        "artifacts": {
            "scripts": ["scripts/test.py"],
        },
    }
    manifest_path = temp_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)

    # Create script
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()
    create_python_script(scripts_dir / "test.py")

    result = validate_package_scripts(str(temp_dir))
    assert isinstance(result, Success)
    assert len(result.value) == 1


def test_validate_package_scripts_with_hooks(temp_dir, sample_frontmatter_with_hooks):
    """Test validating package with hook references."""
    # Create agent with hook
    agents_dir = temp_dir / "agents"
    agents_dir.mkdir()
    create_markdown_file(agents_dir / "agent.md", sample_frontmatter_with_hooks)

    # Create hook script
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()
    create_python_script(scripts_dir / "validate_hook.py")

    result = validate_package_scripts(str(temp_dir))
    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].reference.reference_type == "hook"


def test_validate_package_scripts_missing_script(temp_dir):
    """Test validating package with missing script."""
    # Create manifest referencing non-existent script
    manifest = {
        "name": "test-pkg",
        "version": "0.7.0",
        "description": "Test",
        "artifacts": {
            "scripts": ["scripts/missing.py"],
        },
    }
    manifest_path = temp_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)

    result = validate_package_scripts(str(temp_dir))
    assert isinstance(result, Failure)
    assert len(result.error) == 1


def test_validate_package_scripts_no_references(temp_dir):
    """Test validating package with no script references."""
    # Create manifest with no scripts
    manifest = {
        "name": "test-pkg",
        "version": "0.7.0",
        "description": "Test",
        "artifacts": {
            "commands": ["cmd.md"],
        },
    }
    manifest_path = temp_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)

    result = validate_package_scripts(str(temp_dir))
    assert isinstance(result, Success)
    assert len(result.value) == 0
    assert "No script references found" in result.warnings


# -----------------------------------------------------------------------------
# Test Package Discovery
# -----------------------------------------------------------------------------


def test_find_packages_empty(temp_dir):
    """Test finding packages in empty directory."""
    packages = find_packages(str(temp_dir))
    assert packages == []


def test_find_packages_multiple(temp_dir):
    """Test finding multiple packages."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    (packages_dir / "pkg1").mkdir()
    (packages_dir / "pkg2").mkdir()
    (packages_dir / ".hidden").mkdir()  # Should be ignored

    packages = find_packages(str(temp_dir))
    assert len(packages) == 2
    assert not any(".hidden" in p for p in packages)


def test_find_packages_specific(temp_dir):
    """Test finding specific package."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    (packages_dir / "pkg1").mkdir()
    (packages_dir / "pkg2").mkdir()

    packages = find_packages(str(temp_dir), package_name="pkg1")
    assert len(packages) == 1
    assert "pkg1" in packages[0]


# -----------------------------------------------------------------------------
# Test Repository-Level Validation
# -----------------------------------------------------------------------------


def test_validate_all_packages_success(temp_dir):
    """Test validating all packages successfully."""
    packages_dir = temp_dir / "packages"

    # Create package 1
    pkg1_dir = packages_dir / "pkg1"
    pkg1_dir.mkdir(parents=True)
    manifest1 = {
        "name": "pkg1",
        "version": "1.0.0",
        "description": "Test",
        "artifacts": {"scripts": ["scripts/test1.py"]},
    }
    with open(pkg1_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest1, f)
    scripts1_dir = pkg1_dir / "scripts"
    scripts1_dir.mkdir()
    create_python_script(scripts1_dir / "test1.py")

    # Create package 2
    pkg2_dir = packages_dir / "pkg2"
    pkg2_dir.mkdir(parents=True)
    manifest2 = {
        "name": "pkg2",
        "version": "1.0.0",
        "description": "Test",
        "artifacts": {"scripts": ["scripts/test2.py"]},
    }
    with open(pkg2_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest2, f)
    scripts2_dir = pkg2_dir / "scripts"
    scripts2_dir.mkdir()
    create_python_script(scripts2_dir / "test2.py")

    result = validate_all_packages(str(temp_dir))
    assert isinstance(result, Success)
    assert len(result.value) == 2


def test_validate_all_packages_with_errors(temp_dir):
    """Test validating packages with some errors."""
    packages_dir = temp_dir / "packages"

    # Valid package
    pkg1_dir = packages_dir / "pkg1"
    pkg1_dir.mkdir(parents=True)
    manifest1 = {
        "name": "pkg1",
        "version": "1.0.0",
        "description": "Test",
        "artifacts": {"scripts": ["scripts/test1.py"]},
    }
    with open(pkg1_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest1, f)
    scripts1_dir = pkg1_dir / "scripts"
    scripts1_dir.mkdir()
    create_python_script(scripts1_dir / "test1.py")

    # Invalid package (missing script)
    pkg2_dir = packages_dir / "pkg2"
    pkg2_dir.mkdir(parents=True)
    manifest2 = {
        "name": "pkg2",
        "version": "1.0.0",
        "description": "Test",
        "artifacts": {"scripts": ["scripts/missing.py"]},
    }
    with open(pkg2_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest2, f)

    result = validate_all_packages(str(temp_dir))
    assert isinstance(result, Failure)


def test_validate_all_packages_specific_path(temp_dir):
    """Test validating specific package path."""
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-pkg"
    pkg_dir.mkdir(parents=True)

    manifest = {
        "name": "test",
        "version": "1.0.0",
        "description": "Test",
        "artifacts": {"scripts": ["scripts/test.py"]},
    }
    with open(pkg_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    scripts_dir = pkg_dir / "scripts"
    scripts_dir.mkdir()
    create_python_script(scripts_dir / "test.py")

    result = validate_all_packages(str(temp_dir), specific_path=str(pkg_dir))
    assert isinstance(result, Success)
    assert len(result.value) == 1


def test_validate_all_packages_nonexistent_path(temp_dir):
    """Test validating non-existent path."""
    result = validate_all_packages(str(temp_dir), specific_path="/nonexistent")
    assert isinstance(result, Failure)


# -----------------------------------------------------------------------------
# Test Cross-Platform Paths
# -----------------------------------------------------------------------------


def test_cross_platform_paths(temp_dir):
    """Test that paths work correctly across platforms."""
    scripts_dir = temp_dir / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / "test.py"
    create_python_script(script_path)

    reference = ScriptReference(
        source_file=str(temp_dir / "test.md"),
        script_path="scripts/test.py",
        reference_type="hook",
    )

    result = validate_script_reference(reference, str(temp_dir))
    assert isinstance(result, Success)


# -----------------------------------------------------------------------------
# Test Error String Representation
# -----------------------------------------------------------------------------


def test_script_reference_error_str():
    """Test ScriptReferenceError string representation."""
    error = ScriptReferenceError(
        message="Test error",
        file_path="/path/to/file.md",
        script_reference="scripts/test.py",
        line_number=10,
    )
    error_str = str(error)
    assert "ERROR" in error_str
    assert "/path/to/file.md" in error_str
    assert "scripts/test.py" in error_str
    assert "10" in error_str
    assert "Test error" in error_str
