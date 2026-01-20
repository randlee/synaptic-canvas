"""Comprehensive tests for validate-frontmatter-schema.py script."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "test-packages" / "harness"))

# Import script module
import importlib.util

spec = importlib.util.spec_from_file_location(
    "validate_frontmatter_schema",
    Path(__file__).parent.parent.parent / "scripts" / "validate-frontmatter-schema.py",
)
validate_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validate_module
spec.loader.exec_module(validate_module)

# Import functions and classes
extract_frontmatter = validate_module.extract_frontmatter
validate_frontmatter_schema = validate_module.validate_frontmatter_schema
validate_file = validate_module.validate_file
find_markdown_files = validate_module.find_markdown_files
validate_all = validate_module.validate_all
determine_artifact_type = validate_module.determine_artifact_type
BaseFrontmatter = validate_module.BaseFrontmatter
CommandFrontmatter = validate_module.CommandFrontmatter
SkillFrontmatter = validate_module.SkillFrontmatter
AgentFrontmatter = validate_module.AgentFrontmatter
FrontmatterValidationError = validate_module.FrontmatterValidationError
FrontmatterData = validate_module.FrontmatterData

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
def valid_command_frontmatter():
    """Valid command frontmatter."""
    return {
        "name": "test-command",
        "version": "1.0.0",
        "description": "A test command",
    }


@pytest.fixture
def valid_skill_frontmatter():
    """Valid skill frontmatter."""
    return {
        "name": "test-skill",
        "version": "2.1.3",
        "description": "A test skill",
        "entry_point": "/test-skill",
    }


@pytest.fixture
def valid_agent_frontmatter():
    """Valid agent frontmatter."""
    return {
        "name": "test-agent",
        "version": "0.7.0",
        "description": "A test agent",
        "model": "sonnet",
        "color": "blue",
    }


def create_markdown_file(path: Path, frontmatter: Dict[str, Any], content: str = "") -> None:
    """Helper to create markdown file with frontmatter."""
    yaml_content = yaml.dump(frontmatter, default_flow_style=False)
    full_content = f"---\n{yaml_content}---\n\n{content}"
    path.write_text(full_content, encoding="utf-8")


# -----------------------------------------------------------------------------
# Test Pydantic Models
# -----------------------------------------------------------------------------


def test_base_frontmatter_valid():
    """Test valid base frontmatter."""
    data = {
        "name": "test-item",
        "version": "1.0.0",
        "description": "Test description",
    }
    model = BaseFrontmatter(**data)
    assert model.name == "test-item"
    assert model.version == "1.0.0"
    assert model.description == "Test description"


def test_base_frontmatter_kebab_case_validation():
    """Test name must be kebab-case."""
    # Valid kebab-case
    BaseFrontmatter(name="test", version="1.0.0", description="Test")
    BaseFrontmatter(name="test-item", version="1.0.0", description="Test")
    BaseFrontmatter(name="test-item-123", version="1.0.0", description="Test")

    # Invalid kebab-case
    with pytest.raises(ValueError, match="kebab-case"):
        BaseFrontmatter(name="TestItem", version="1.0.0", description="Test")
    with pytest.raises(ValueError, match="kebab-case"):
        BaseFrontmatter(name="test_item", version="1.0.0", description="Test")
    with pytest.raises(ValueError, match="kebab-case"):
        BaseFrontmatter(name="test item", version="1.0.0", description="Test")
    with pytest.raises(ValueError, match="kebab-case"):
        BaseFrontmatter(name="-test", version="1.0.0", description="Test")
    with pytest.raises(ValueError, match="kebab-case"):
        BaseFrontmatter(name="test-", version="1.0.0", description="Test")


def test_base_frontmatter_semver_validation():
    """Test version must be semantic version."""
    # Valid semver
    BaseFrontmatter(name="test", version="0.0.0", description="Test")
    BaseFrontmatter(name="test", version="1.0.0", description="Test")
    BaseFrontmatter(name="test", version="10.20.30", description="Test")

    # Invalid semver
    with pytest.raises(ValueError, match="SemVer"):
        BaseFrontmatter(name="test", version="1.0", description="Test")
    with pytest.raises(ValueError, match="SemVer"):
        BaseFrontmatter(name="test", version="1", description="Test")
    with pytest.raises(ValueError, match="SemVer"):
        BaseFrontmatter(name="test", version="v1.0.0", description="Test")
    with pytest.raises(ValueError, match="SemVer"):
        BaseFrontmatter(name="test", version="1.0.0-beta", description="Test")


def test_command_frontmatter_valid():
    """Test valid command frontmatter."""
    data = {
        "name": "test-cmd",
        "version": "1.0.0",
        "description": "Test",
        "options": ["--flag1", "--flag2"],
    }
    model = CommandFrontmatter(**data)
    assert model.options == ["--flag1", "--flag2"]


def test_command_frontmatter_optional_options():
    """Test command options field is optional."""
    data = {
        "name": "test-cmd",
        "version": "1.0.0",
        "description": "Test",
    }
    model = CommandFrontmatter(**data)
    assert model.options is None


def test_skill_frontmatter_valid():
    """Test valid skill frontmatter."""
    data = {
        "name": "test-skill",
        "version": "1.0.0",
        "description": "Test",
        "entry_point": "/test-skill",
    }
    model = SkillFrontmatter(**data)
    assert model.entry_point == "/test-skill"


def test_skill_frontmatter_entry_point_validation():
    """Test entry_point must start with /."""
    # Valid
    SkillFrontmatter(
        name="test",
        version="1.0.0",
        description="Test",
        entry_point="/test",
    )

    # Invalid
    with pytest.raises(ValueError, match="must start with /"):
        SkillFrontmatter(
            name="test",
            version="1.0.0",
            description="Test",
            entry_point="test",
        )


def test_agent_frontmatter_valid():
    """Test valid agent frontmatter."""
    data = {
        "name": "test-agent",
        "version": "1.0.0",
        "description": "Test",
        "model": "opus",
        "color": "green",
    }
    model = AgentFrontmatter(**data)
    assert model.model == "opus"
    assert model.color == "green"


def test_agent_frontmatter_model_validation():
    """Test model must be one of allowed values."""
    # Valid models
    for model in ["sonnet", "opus", "haiku"]:
        AgentFrontmatter(
            name="test",
            version="1.0.0",
            description="Test",
            model=model,
            color="blue",
        )

    # Invalid model
    with pytest.raises(ValueError, match="Model must be one of"):
        AgentFrontmatter(
            name="test",
            version="1.0.0",
            description="Test",
            model="gpt4",
            color="blue",
        )


def test_agent_frontmatter_color_validation():
    """Test color must be one of allowed values."""
    # Valid colors
    for color in ["gray", "green", "purple", "blue", "red", "yellow"]:
        AgentFrontmatter(
            name="test",
            version="1.0.0",
            description="Test",
            model="sonnet",
            color=color,
        )

    # Invalid color
    with pytest.raises(ValueError, match="Color must be one of"):
        AgentFrontmatter(
            name="test",
            version="1.0.0",
            description="Test",
            model="sonnet",
            color="orange",
        )


# -----------------------------------------------------------------------------
# Test Frontmatter Extraction
# -----------------------------------------------------------------------------


def test_extract_frontmatter_valid(temp_dir, valid_command_frontmatter):
    """Test extracting valid frontmatter."""
    file_path = temp_dir / "commands" / "test.md"
    file_path.parent.mkdir(parents=True)
    create_markdown_file(file_path, valid_command_frontmatter, "# Test Content")

    result = extract_frontmatter(str(file_path))
    assert isinstance(result, Success)
    assert result.value.artifact_type == "command"
    assert result.value.data == valid_command_frontmatter


def test_extract_frontmatter_missing_file(temp_dir):
    """Test extracting from non-existent file."""
    result = extract_frontmatter(str(temp_dir / "missing.md"))
    assert isinstance(result, Failure)
    assert "Failed to read file" in result.error.message


def test_extract_frontmatter_no_frontmatter(temp_dir):
    """Test file without frontmatter."""
    file_path = temp_dir / "commands" / "test.md"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("# Just content, no frontmatter")

    result = extract_frontmatter(str(file_path))
    assert isinstance(result, Failure)
    assert "No frontmatter found" in result.error.message


def test_extract_frontmatter_invalid_yaml(temp_dir):
    """Test file with invalid YAML."""
    file_path = temp_dir / "commands" / "test.md"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("---\ninvalid: yaml: content: :\n---\n")

    result = extract_frontmatter(str(file_path))
    assert isinstance(result, Failure)
    assert "Invalid YAML" in result.error.message


def test_extract_frontmatter_not_dict(temp_dir):
    """Test frontmatter that is not a dict."""
    file_path = temp_dir / "commands" / "test.md"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("---\n- item1\n- item2\n---\n")

    result = extract_frontmatter(str(file_path))
    assert isinstance(result, Failure)
    assert "must be a YAML object/dict" in result.error.message


# -----------------------------------------------------------------------------
# Test Artifact Type Detection
# -----------------------------------------------------------------------------


def test_determine_artifact_type_command():
    """Test artifact type detection for commands."""
    assert determine_artifact_type("/path/to/packages/test/commands/cmd.md") == "command"


def test_determine_artifact_type_skill():
    """Test artifact type detection for skills."""
    assert determine_artifact_type("/path/to/packages/test/skills/test/SKILL.md") == "skill"


def test_determine_artifact_type_agent():
    """Test artifact type detection for agents."""
    assert determine_artifact_type("/path/to/packages/test/agents/agent.md") == "agent"


def test_determine_artifact_type_unknown():
    """Test artifact type detection for unknown paths."""
    assert determine_artifact_type("/path/to/some/random/file.md") == "unknown"


# -----------------------------------------------------------------------------
# Test Schema Validation
# -----------------------------------------------------------------------------


def test_validate_frontmatter_schema_command_valid(valid_command_frontmatter):
    """Test validating valid command frontmatter."""
    data = FrontmatterData(
        file_path="/test/commands/test.md",
        artifact_type="command",
        data=valid_command_frontmatter,
        raw_frontmatter="",
    )
    result = validate_frontmatter_schema(data)
    assert isinstance(result, Success)


def test_validate_frontmatter_schema_command_missing_field():
    """Test command with missing required field."""
    data = FrontmatterData(
        file_path="/test/commands/test.md",
        artifact_type="command",
        data={"name": "test", "version": "1.0.0"},  # missing description
        raw_frontmatter="",
    )
    result = validate_frontmatter_schema(data)
    assert isinstance(result, Failure)
    assert "description" in result.error.field_name.lower()


def test_validate_frontmatter_schema_skill_valid(valid_skill_frontmatter):
    """Test validating valid skill frontmatter."""
    data = FrontmatterData(
        file_path="/test/skills/test/SKILL.md",
        artifact_type="skill",
        data=valid_skill_frontmatter,
        raw_frontmatter="",
    )
    result = validate_frontmatter_schema(data)
    assert isinstance(result, Success)


def test_validate_frontmatter_schema_skill_missing_entry_point():
    """Test skill with missing entry_point."""
    data = FrontmatterData(
        file_path="/test/skills/test/SKILL.md",
        artifact_type="skill",
        data={"name": "test", "version": "1.0.0", "description": "Test"},
        raw_frontmatter="",
    )
    result = validate_frontmatter_schema(data)
    assert isinstance(result, Failure)
    assert "entry_point" in result.error.field_name.lower()


def test_validate_frontmatter_schema_skill_invalid_entry_point():
    """Test skill with invalid entry_point (not starting with /)."""
    data = FrontmatterData(
        file_path="/test/skills/test/SKILL.md",
        artifact_type="skill",
        data={
            "name": "test",
            "version": "1.0.0",
            "description": "Test",
            "entry_point": "test",
        },
        raw_frontmatter="",
    )
    result = validate_frontmatter_schema(data)
    assert isinstance(result, Failure)
    assert "must start with /" in result.error.message


def test_validate_frontmatter_schema_agent_valid(valid_agent_frontmatter):
    """Test validating valid agent frontmatter."""
    data = FrontmatterData(
        file_path="/test/agents/test.md",
        artifact_type="agent",
        data=valid_agent_frontmatter,
        raw_frontmatter="",
    )
    result = validate_frontmatter_schema(data)
    assert isinstance(result, Success)


def test_validate_frontmatter_schema_agent_invalid_model():
    """Test agent with invalid model."""
    data = FrontmatterData(
        file_path="/test/agents/test.md",
        artifact_type="agent",
        data={
            "name": "test",
            "version": "1.0.0",
            "description": "Test",
            "model": "invalid",
            "color": "blue",
        },
        raw_frontmatter="",
    )
    result = validate_frontmatter_schema(data)
    assert isinstance(result, Failure)
    assert "Model must be one of" in result.error.message


def test_validate_frontmatter_schema_agent_invalid_color():
    """Test agent with invalid color."""
    data = FrontmatterData(
        file_path="/test/agents/test.md",
        artifact_type="agent",
        data={
            "name": "test",
            "version": "1.0.0",
            "description": "Test",
            "model": "sonnet",
            "color": "orange",
        },
        raw_frontmatter="",
    )
    result = validate_frontmatter_schema(data)
    assert isinstance(result, Failure)
    assert "Color must be one of" in result.error.message


def test_validate_frontmatter_schema_unknown_type():
    """Test validation with unknown artifact type."""
    data = FrontmatterData(
        file_path="/test/other/test.md",
        artifact_type="unknown",
        data={"name": "test", "version": "1.0.0", "description": "Test"},
        raw_frontmatter="",
    )
    result = validate_frontmatter_schema(data)
    assert isinstance(result, Failure)
    assert "Unknown artifact type" in result.error.message


# -----------------------------------------------------------------------------
# Test File Validation Pipeline
# -----------------------------------------------------------------------------


def test_validate_file_valid_command(temp_dir, valid_command_frontmatter):
    """Test complete validation pipeline for valid command."""
    file_path = temp_dir / "commands" / "test.md"
    file_path.parent.mkdir(parents=True)
    create_markdown_file(file_path, valid_command_frontmatter)

    result = validate_file(str(file_path))
    assert isinstance(result, Success)
    assert result.value.artifact_type == "command"


def test_validate_file_invalid_frontmatter(temp_dir):
    """Test validation pipeline with invalid frontmatter."""
    file_path = temp_dir / "commands" / "test.md"
    file_path.parent.mkdir(parents=True)
    create_markdown_file(
        file_path,
        {"name": "Test", "version": "1.0.0", "description": "Test"},  # Invalid name (not kebab-case)
    )

    result = validate_file(str(file_path))
    assert isinstance(result, Failure)


# -----------------------------------------------------------------------------
# Test File Discovery
# -----------------------------------------------------------------------------


def test_find_markdown_files_empty(temp_dir):
    """Test finding files in empty directory."""
    files = find_markdown_files(str(temp_dir))
    assert files == []


def test_find_markdown_files_commands(temp_dir):
    """Test finding command files."""
    pkg_dir = temp_dir / "packages" / "test-pkg"
    cmd_dir = pkg_dir / "commands"
    cmd_dir.mkdir(parents=True)

    (cmd_dir / "cmd1.md").write_text("test")
    (cmd_dir / "cmd2.md").write_text("test")

    files = find_markdown_files(str(temp_dir))
    assert len(files) == 2
    assert all("commands" in f for f in files)


def test_find_markdown_files_skills(temp_dir):
    """Test finding skill files."""
    pkg_dir = temp_dir / "packages" / "test-pkg"
    skill_dir = pkg_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)

    (skill_dir / "SKILL.md").write_text("test")

    files = find_markdown_files(str(temp_dir))
    assert len(files) == 1
    assert "SKILL.md" in files[0]


def test_find_markdown_files_agents(temp_dir):
    """Test finding agent files (only .md, not .py)."""
    pkg_dir = temp_dir / "packages" / "test-pkg"
    agent_dir = pkg_dir / "agents"
    agent_dir.mkdir(parents=True)

    (agent_dir / "agent1.md").write_text("test")
    (agent_dir / "agent2.md").write_text("test")
    (agent_dir / "agent_impl.py").write_text("# Python script")

    files = find_markdown_files(str(temp_dir))
    assert len(files) == 2
    assert all(f.endswith(".md") for f in files)
    assert not any(f.endswith(".py") for f in files)


def test_find_markdown_files_specific_package(temp_dir):
    """Test finding files for specific package."""
    pkg1_dir = temp_dir / "packages" / "pkg1"
    pkg2_dir = temp_dir / "packages" / "pkg2"

    (pkg1_dir / "commands").mkdir(parents=True)
    (pkg2_dir / "commands").mkdir(parents=True)

    (pkg1_dir / "commands" / "cmd.md").write_text("test")
    (pkg2_dir / "commands" / "cmd.md").write_text("test")

    files = find_markdown_files(str(temp_dir), package_name="pkg1")
    assert len(files) == 1
    assert "pkg1" in files[0]


# -----------------------------------------------------------------------------
# Test Complete Validation
# -----------------------------------------------------------------------------


def test_validate_all_success(temp_dir, valid_command_frontmatter, valid_skill_frontmatter):
    """Test validate_all with all valid files."""
    pkg_dir = temp_dir / "packages" / "test-pkg"

    # Create command
    cmd_dir = pkg_dir / "commands"
    cmd_dir.mkdir(parents=True)
    create_markdown_file(cmd_dir / "test.md", valid_command_frontmatter)

    # Create skill
    skill_dir = pkg_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    create_markdown_file(skill_dir / "SKILL.md", valid_skill_frontmatter)

    result = validate_all(str(temp_dir))
    assert isinstance(result, Success)
    assert len(result.value) == 2


def test_validate_all_with_errors(temp_dir):
    """Test validate_all with some invalid files."""
    pkg_dir = temp_dir / "packages" / "test-pkg"
    cmd_dir = pkg_dir / "commands"
    cmd_dir.mkdir(parents=True)

    # Valid file
    create_markdown_file(
        cmd_dir / "valid.md",
        {"name": "valid", "version": "1.0.0", "description": "Valid"},
    )

    # Invalid file (bad version)
    create_markdown_file(
        cmd_dir / "invalid.md",
        {"name": "invalid", "version": "1.0", "description": "Invalid"},
    )

    result = validate_all(str(temp_dir))
    assert isinstance(result, Failure)
    assert len(result.error) == 1


def test_validate_all_specific_file(temp_dir, valid_command_frontmatter):
    """Test validate_all with specific file path."""
    # Create file in commands directory so artifact type is recognized
    cmd_dir = temp_dir / "commands"
    cmd_dir.mkdir()
    file_path = cmd_dir / "test.md"
    create_markdown_file(file_path, valid_command_frontmatter)

    result = validate_all(str(temp_dir), specific_path=str(file_path))
    assert isinstance(result, Success)
    assert len(result.value) == 1


def test_validate_all_nonexistent_path(temp_dir):
    """Test validate_all with non-existent path."""
    result = validate_all(str(temp_dir), specific_path="/nonexistent/path")
    assert isinstance(result, Failure)


# -----------------------------------------------------------------------------
# Test Cross-Platform Paths
# -----------------------------------------------------------------------------


def test_cross_platform_paths_posix(temp_dir):
    """Test that paths work correctly on POSIX systems."""
    pkg_dir = temp_dir / "packages" / "test-pkg" / "commands"
    pkg_dir.mkdir(parents=True)

    file_path = pkg_dir / "test.md"
    create_markdown_file(
        file_path,
        {"name": "test", "version": "1.0.0", "description": "Test"},
    )

    result = validate_file(str(file_path))
    assert isinstance(result, Success)


# -----------------------------------------------------------------------------
# Test Edge Cases
# -----------------------------------------------------------------------------


def test_empty_description():
    """Test that empty description is allowed (Pydantic doesn't enforce non-empty by default)."""
    # Empty string is technically valid, just not recommended
    model = BaseFrontmatter(name="test", version="1.0.0", description="")
    assert model.description == ""


def test_extra_fields_forbidden():
    """Test that extra fields are forbidden."""
    with pytest.raises(ValueError):
        CommandFrontmatter(
            name="test",
            version="1.0.0",
            description="Test",
            extra_field="not allowed",
        )


def test_version_with_leading_zeros():
    """Test semantic version with leading zeros."""
    # Should be valid
    BaseFrontmatter(name="test", version="0.0.0", description="Test")
    BaseFrontmatter(name="test", version="0.10.20", description="Test")


def test_validation_error_str():
    """Test FrontmatterValidationError string representation."""
    error = FrontmatterValidationError(
        message="Test error",
        file_path="/path/to/file.md",
        line_number=5,
        field_name="name",
    )
    error_str = str(error)
    assert "ERROR" in error_str
    assert "/path/to/file.md" in error_str
    assert "5" in error_str
    assert "name" in error_str
    assert "Test error" in error_str
