"""Comprehensive tests for validate-agents.py script."""

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
    "validate_agents",
    Path(__file__).parent.parent.parent / "scripts" / "validate-agents.py",
)
validate_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validate_module
spec.loader.exec_module(validate_module)

# Import functions and classes
load_registry = validate_module.load_registry
extract_frontmatter = validate_module.extract_frontmatter
validate_agent_version = validate_module.validate_agent_version
validate_skill_constraints = validate_module.validate_skill_constraints
validate_all_agents = validate_module.validate_all_agents
AgentValidationError = validate_module.AgentValidationError
AgentRegistry = validate_module.AgentRegistry
AgentRegistryEntry = validate_module.AgentRegistryEntry
AgentFrontmatter = validate_module.AgentFrontmatter
SkillDependency = validate_module.SkillDependency
ValidationData = validate_module.ValidationData

from result import Success, Failure, AggregateError


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_registry_data():
    """Valid registry data."""
    return {
        "agents": {
            "test-agent": {"version": "1.0.0", "path": ".claude/agents/test-agent.md"},
            "another-agent": {
                "version": "2.1.3",
                "path": ".claude/agents/another-agent.md",
            },
        }
    }


@pytest.fixture
def valid_registry_with_skills():
    """Valid registry with skill dependencies."""
    return {
        "agents": {
            "test-agent": {"version": "1.0.0", "path": ".claude/agents/test-agent.md"},
            "dep-agent": {"version": "2.5.0", "path": ".claude/agents/dep-agent.md"},
        },
        "skills": {
            "test-skill": {
                "depends_on": {"test-agent": "1.x", "dep-agent": "2.x"},
                "entry_point": "/test-skill",
            }
        },
    }


@pytest.fixture
def valid_agent_frontmatter():
    """Valid agent frontmatter."""
    return {
        "name": "test-agent",
        "version": "1.0.0",
        "description": "A test agent",
        "model": "sonnet",
        "color": "blue",
    }


def create_yaml_file(path: Path, data: Dict[str, Any]) -> None:
    """Helper to create YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)


def create_markdown_file(path: Path, frontmatter: Dict[str, Any], content: str = "") -> None:
    """Helper to create markdown file with frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_content = yaml.dump(frontmatter, default_flow_style=False)
    full_content = f"---\n{yaml_content}---\n\n{content}"
    path.write_text(full_content, encoding="utf-8")


# -----------------------------------------------------------------------------
# Test AgentValidationError
# -----------------------------------------------------------------------------


def test_agent_validation_error_str():
    """Test AgentValidationError string formatting."""
    error = AgentValidationError(
        message="Test error",
        file_path="/path/to/file",
        agent_name="test-agent",
    )
    result = str(error)
    assert "ERROR" in result
    assert "test-agent" in result
    assert "/path/to/file" in result
    assert "Test error" in result


def test_agent_validation_error_warning():
    """Test AgentValidationError with warning severity."""
    error = AgentValidationError(
        message="Test warning",
        severity="warning",
    )
    result = str(error)
    assert "WARNING" in result


# -----------------------------------------------------------------------------
# Test Pydantic Models
# -----------------------------------------------------------------------------


def test_agent_registry_entry_valid():
    """Test valid AgentRegistryEntry."""
    entry = AgentRegistryEntry(version="1.0.0", path=".claude/agents/test.md")
    assert entry.version == "1.0.0"
    assert entry.path == ".claude/agents/test.md"


def test_agent_registry_entry_invalid_version():
    """Test AgentRegistryEntry with invalid version."""
    with pytest.raises(Exception):  # Pydantic validation error
        AgentRegistryEntry(version="invalid", path=".claude/agents/test.md")


def test_agent_registry_valid():
    """Test valid AgentRegistry."""
    data = {
        "agents": {
            "test-agent": {"version": "1.0.0", "path": ".claude/agents/test.md"}
        }
    }
    registry = AgentRegistry(**data)
    assert "test-agent" in registry.agents
    assert registry.agents["test-agent"].version == "1.0.0"


def test_agent_registry_with_skills():
    """Test AgentRegistry with skills."""
    data = {
        "agents": {"test-agent": {"version": "1.0.0", "path": ".claude/agents/test.md"}},
        "skills": {"test-skill": {"depends_on": {"test-agent": "1.x"}}},
    }
    registry = AgentRegistry(**data)
    assert registry.skills is not None
    assert "test-skill" in registry.skills


def test_skill_dependency_valid():
    """Test valid SkillDependency."""
    dep = SkillDependency(depends_on={"test-agent": "1.x"}, entry_point="/test")
    assert dep.depends_on["test-agent"] == "1.x"
    assert dep.entry_point == "/test"


def test_agent_frontmatter_valid():
    """Test valid AgentFrontmatter."""
    frontmatter = AgentFrontmatter(
        name="test-agent", version="1.0.0", description="Test agent"
    )
    assert frontmatter.name == "test-agent"
    assert frontmatter.version == "1.0.0"


def test_agent_frontmatter_invalid_version():
    """Test AgentFrontmatter with invalid version."""
    with pytest.raises(Exception):  # Pydantic validation error
        AgentFrontmatter(name="test-agent", version="invalid", description="Test")


def test_agent_frontmatter_allows_extra_fields():
    """Test AgentFrontmatter allows extra fields like model and color."""
    data = {
        "name": "test-agent",
        "version": "1.0.0",
        "description": "Test agent",
        "model": "sonnet",
        "color": "blue",
    }
    frontmatter = AgentFrontmatter(**data)
    assert frontmatter.name == "test-agent"


# -----------------------------------------------------------------------------
# Test load_registry
# -----------------------------------------------------------------------------


def test_load_registry_success(temp_dir, valid_registry_data):
    """Test successful registry loading."""
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    result = load_registry(registry_path)

    assert isinstance(result, Success)
    assert isinstance(result.value, AgentRegistry)
    assert "test-agent" in result.value.agents


def test_load_registry_file_not_found(temp_dir):
    """Test registry loading when file does not exist."""
    registry_path = temp_dir / "nonexistent.yaml"

    result = load_registry(registry_path)

    assert isinstance(result, Failure)
    assert "not found" in result.error.message.lower()


def test_load_registry_empty_file(temp_dir):
    """Test registry loading with empty file."""
    registry_path = temp_dir / "registry.yaml"
    registry_path.write_text("")

    result = load_registry(registry_path)

    assert isinstance(result, Failure)
    assert "empty" in result.error.message.lower()


def test_load_registry_invalid_yaml(temp_dir):
    """Test registry loading with invalid YAML."""
    registry_path = temp_dir / "registry.yaml"
    registry_path.write_text("invalid: [yaml")

    result = load_registry(registry_path)

    assert isinstance(result, Failure)
    assert "yaml" in result.error.message.lower()


def test_load_registry_invalid_schema(temp_dir):
    """Test registry loading with invalid schema."""
    registry_path = temp_dir / "registry.yaml"
    data = {"agents": {"test": {"version": "invalid"}}}  # Missing path, invalid version
    create_yaml_file(registry_path, data)

    result = load_registry(registry_path)

    assert isinstance(result, Failure)
    assert "validation" in result.error.message.lower()


def test_load_registry_unexpected_error(temp_dir, monkeypatch):
    """Test registry loading with unexpected error."""
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, {"agents": {}})

    def mock_open(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    monkeypatch.setattr("builtins.open", mock_open)

    result = load_registry(registry_path)

    assert isinstance(result, Failure)
    assert "unexpected error" in result.error.message.lower()


# -----------------------------------------------------------------------------
# Test extract_frontmatter
# -----------------------------------------------------------------------------


def test_extract_frontmatter_success(temp_dir):
    """Test successful frontmatter extraction."""
    file_path = temp_dir / "test.md"
    frontmatter = {"name": "test", "version": "1.0.0"}
    create_markdown_file(file_path, frontmatter, "Some content")

    result = extract_frontmatter(file_path)

    assert isinstance(result, Success)
    assert result.value["name"] == "test"
    assert result.value["version"] == "1.0.0"


def test_extract_frontmatter_file_not_found(temp_dir):
    """Test frontmatter extraction when file does not exist."""
    file_path = temp_dir / "nonexistent.md"

    result = extract_frontmatter(file_path)

    assert isinstance(result, Failure)
    assert "not found" in result.error.message.lower()


def test_extract_frontmatter_no_opening_delimiter(temp_dir):
    """Test frontmatter extraction with no opening delimiter."""
    file_path = temp_dir / "test.md"
    file_path.write_text("No frontmatter here")

    result = extract_frontmatter(file_path)

    assert isinstance(result, Failure)
    assert "missing opening ---" in result.error.message.lower()


def test_extract_frontmatter_no_closing_delimiter(temp_dir):
    """Test frontmatter extraction with no closing delimiter."""
    file_path = temp_dir / "test.md"
    file_path.write_text("---\nname: test\nversion: 1.0.0")

    result = extract_frontmatter(file_path)

    assert isinstance(result, Failure)
    assert "missing closing ---" in result.error.message.lower()


def test_extract_frontmatter_empty(temp_dir):
    """Test frontmatter extraction with empty frontmatter."""
    file_path = temp_dir / "test.md"
    file_path.write_text("---\n---\n\nContent")

    result = extract_frontmatter(file_path)

    assert isinstance(result, Failure)
    assert "empty" in result.error.message.lower()


def test_extract_frontmatter_invalid_yaml(temp_dir):
    """Test frontmatter extraction with invalid YAML."""
    file_path = temp_dir / "test.md"
    file_path.write_text("---\ninvalid: [yaml\n---\n")

    result = extract_frontmatter(file_path)

    assert isinstance(result, Failure)
    assert "yaml" in result.error.message.lower()


def test_extract_frontmatter_unexpected_error(temp_dir, monkeypatch):
    """Test frontmatter extraction with unexpected error."""
    file_path = temp_dir / "test.md"
    create_markdown_file(file_path, {"name": "test"}, "content")

    def mock_read_text(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    result = extract_frontmatter(file_path)

    assert isinstance(result, Failure)
    assert "unexpected error" in result.error.message.lower()


# -----------------------------------------------------------------------------
# Test validate_agent_version
# -----------------------------------------------------------------------------


def test_validate_agent_version_success(temp_dir, monkeypatch):
    """Test successful agent version validation."""
    # Change to temp dir so relative paths work
    monkeypatch.chdir(temp_dir)

    agent_path = temp_dir / ".claude" / "agents" / "test-agent.md"
    frontmatter = {
        "name": "test-agent",
        "version": "1.0.0",
        "description": "Test agent",
    }
    create_markdown_file(agent_path, frontmatter)

    registry_entry = AgentRegistryEntry(
        version="1.0.0", path=".claude/agents/test-agent.md"
    )

    result = validate_agent_version("test-agent", registry_entry, temp_dir)

    assert isinstance(result, Success)
    assert result.value == "1.0.0"


def test_validate_agent_version_file_not_found(temp_dir, monkeypatch):
    """Test agent version validation when file does not exist."""
    monkeypatch.chdir(temp_dir)
    registry_entry = AgentRegistryEntry(
        version="1.0.0", path=".claude/agents/nonexistent.md"
    )

    result = validate_agent_version("test-agent", registry_entry, temp_dir)

    assert isinstance(result, Failure)
    assert "test-agent" in result.error.agent_name


def test_validate_agent_version_invalid_frontmatter_schema(temp_dir, monkeypatch):
    """Test agent version validation with invalid frontmatter schema."""
    monkeypatch.chdir(temp_dir)
    agent_path = temp_dir / ".claude" / "agents" / "test-agent.md"
    frontmatter = {"name": "test-agent", "version": "invalid"}  # Missing description
    create_markdown_file(agent_path, frontmatter)

    registry_entry = AgentRegistryEntry(
        version="1.0.0", path=".claude/agents/test-agent.md"
    )

    result = validate_agent_version("test-agent", registry_entry, temp_dir)

    assert isinstance(result, Failure)
    assert "validation" in result.error.message.lower()


def test_validate_agent_version_missing_version(temp_dir, monkeypatch):
    """Test agent version validation with missing version."""
    monkeypatch.chdir(temp_dir)
    agent_path = temp_dir / ".claude" / "agents" / "test-agent.md"
    frontmatter = {"name": "test-agent", "description": "Test"}
    # Create manually to bypass Pydantic validation
    agent_path.parent.mkdir(parents=True, exist_ok=True)
    content = "---\nname: test-agent\nversion: \"\"\ndescription: Test\n---\n"
    agent_path.write_text(content)

    registry_entry = AgentRegistryEntry(
        version="1.0.0", path=".claude/agents/test-agent.md"
    )

    result = validate_agent_version("test-agent", registry_entry, temp_dir)

    assert isinstance(result, Failure)


def test_validate_agent_version_mismatch(temp_dir, monkeypatch):
    """Test agent version validation with version mismatch."""
    monkeypatch.chdir(temp_dir)
    agent_path = temp_dir / ".claude" / "agents" / "test-agent.md"
    frontmatter = {
        "name": "test-agent",
        "version": "1.0.0",
        "description": "Test agent",
    }
    create_markdown_file(agent_path, frontmatter)

    registry_entry = AgentRegistryEntry(
        version="2.0.0", path=".claude/agents/test-agent.md"
    )

    result = validate_agent_version("test-agent", registry_entry, temp_dir)

    assert isinstance(result, Failure)
    assert "mismatch" in result.error.message.lower()
    assert result.error.details["file_version"] == "1.0.0"
    assert result.error.details["registry_version"] == "2.0.0"


# -----------------------------------------------------------------------------
# Test validate_skill_constraints
# -----------------------------------------------------------------------------


def test_validate_skill_constraints_success():
    """Test successful skill constraint validation."""
    skill_dep = SkillDependency(depends_on={"test-agent": "1.x"})
    registry_data = {
        "agents": {"test-agent": {"version": "1.5.0", "path": "test.md"}}
    }
    registry = AgentRegistry(**registry_data)

    result = validate_skill_constraints("test-skill", skill_dep, registry)

    assert isinstance(result, Success)
    assert "test-agent:1.x" in result.value


def test_validate_skill_constraints_version_mismatch():
    """Test skill constraint validation with version mismatch."""
    skill_dep = SkillDependency(depends_on={"test-agent": "1.x"})
    registry_data = {
        "agents": {"test-agent": {"version": "2.0.0", "path": "test.md"}}
    }
    registry = AgentRegistry(**registry_data)

    result = validate_skill_constraints("test-skill", skill_dep, registry)

    assert isinstance(result, Failure)
    assert isinstance(result.error, AggregateError)
    assert len(result.error.errors) == 1


def test_validate_skill_constraints_undefined_agent():
    """Test skill constraint validation with undefined agent."""
    skill_dep = SkillDependency(depends_on={"nonexistent-agent": "1.x"})
    registry_data = {"agents": {}}
    registry = AgentRegistry(**registry_data)

    result = validate_skill_constraints("test-skill", skill_dep, registry)

    assert isinstance(result, Failure)
    assert isinstance(result.error, AggregateError)
    assert "undefined" in str(result.error.errors[0]).lower()


def test_validate_skill_constraints_skill_to_skill_dependency():
    """Test skill constraint validation with skill-to-skill dependency."""
    skill_dep = SkillDependency(depends_on={"another-skill": "1.x"})
    registry_data = {
        "agents": {},
        "skills": {"another-skill": {"depends_on": {}}},
    }
    registry = AgentRegistry(**registry_data)

    result = validate_skill_constraints("test-skill", skill_dep, registry)

    assert isinstance(result, Success)
    assert "another-skill:1.x" in result.value


def test_validate_skill_constraints_non_x_constraint():
    """Test skill constraint validation with non-.x constraint."""
    skill_dep = SkillDependency(depends_on={"test-agent": "1.0.0"})
    registry_data = {
        "agents": {"test-agent": {"version": "1.0.0", "path": "test.md"}}
    }
    registry = AgentRegistry(**registry_data)

    result = validate_skill_constraints("test-skill", skill_dep, registry)

    assert isinstance(result, Success)
    assert "test-agent:1.0.0" in result.value


def test_validate_skill_constraints_multiple_dependencies():
    """Test skill constraint validation with multiple dependencies."""
    skill_dep = SkillDependency(
        depends_on={"agent-1": "1.x", "agent-2": "2.x"}
    )
    registry_data = {
        "agents": {
            "agent-1": {"version": "1.5.0", "path": "agent1.md"},
            "agent-2": {"version": "2.0.0", "path": "agent2.md"},
        }
    }
    registry = AgentRegistry(**registry_data)

    result = validate_skill_constraints("test-skill", skill_dep, registry)

    assert isinstance(result, Success)
    assert len(result.value) == 2


def test_validate_skill_constraints_partial_success():
    """Test skill constraint validation with partial success."""
    skill_dep = SkillDependency(
        depends_on={"good-agent": "1.x", "bad-agent": "1.x"}
    )
    registry_data = {
        "agents": {"good-agent": {"version": "1.0.0", "path": "good.md"}}
    }
    registry = AgentRegistry(**registry_data)

    result = validate_skill_constraints("test-skill", skill_dep, registry)

    assert isinstance(result, Failure)
    assert result.partial_result is not None
    assert "good-agent:1.x" in result.partial_result


# -----------------------------------------------------------------------------
# Test validate_all_agents
# -----------------------------------------------------------------------------


def test_validate_all_agents_success(temp_dir, valid_registry_data, monkeypatch):
    """Test successful validation of all agents."""
    monkeypatch.chdir(temp_dir)
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    # Create agent files
    for agent_name, entry in valid_registry_data["agents"].items():
        agent_path = temp_dir / entry["path"]
        frontmatter = {
            "name": agent_name,
            "version": entry["version"],
            "description": f"Description for {agent_name}",
        }
        create_markdown_file(agent_path, frontmatter)

    result = validate_all_agents(registry_path, verbose=False)

    assert isinstance(result, Success)
    assert result.value.total_agents == 2
    assert result.value.validated_agents == 2


def test_validate_all_agents_registry_not_found(temp_dir):
    """Test validation when registry does not exist."""
    registry_path = temp_dir / "nonexistent.yaml"

    result = validate_all_agents(registry_path, verbose=False)

    assert isinstance(result, Failure)


def test_validate_all_agents_with_errors(temp_dir, valid_registry_data, monkeypatch):
    """Test validation with some agent errors."""
    monkeypatch.chdir(temp_dir)
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    # Create only one agent file (missing the other)
    first_agent = list(valid_registry_data["agents"].keys())[0]
    first_entry = valid_registry_data["agents"][first_agent]
    agent_path = temp_dir / first_entry["path"]
    frontmatter = {
        "name": first_agent,
        "version": first_entry["version"],
        "description": f"Description for {first_agent}",
    }
    create_markdown_file(agent_path, frontmatter)

    result = validate_all_agents(registry_path, verbose=False)

    assert isinstance(result, Failure)
    assert isinstance(result.error, AggregateError)
    assert result.partial_result.validated_agents == 1
    assert result.partial_result.total_agents == 2


def test_validate_all_agents_with_skills_success(temp_dir, valid_registry_with_skills, monkeypatch):
    """Test validation with skill dependencies."""
    monkeypatch.chdir(temp_dir)
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_with_skills)

    # Create agent files
    for agent_name, entry in valid_registry_with_skills["agents"].items():
        agent_path = temp_dir / entry["path"]
        frontmatter = {
            "name": agent_name,
            "version": entry["version"],
            "description": f"Description for {agent_name}",
        }
        create_markdown_file(agent_path, frontmatter)

    result = validate_all_agents(registry_path, verbose=False)

    assert isinstance(result, Success)
    assert result.value.total_skills == 1
    assert result.value.validated_dependencies == 2


def test_validate_all_agents_with_skill_errors(temp_dir, monkeypatch):
    """Test validation with skill constraint errors."""
    monkeypatch.chdir(temp_dir)
    registry_data = {
        "agents": {"test-agent": {"version": "2.0.0", "path": ".claude/agents/test.md"}},
        "skills": {"test-skill": {"depends_on": {"test-agent": "1.x"}}},
    }
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, registry_data)

    # Create agent file
    agent_path = temp_dir / ".claude" / "agents" / "test.md"
    frontmatter = {
        "name": "test-agent",
        "version": "2.0.0",
        "description": "Test agent",
    }
    create_markdown_file(agent_path, frontmatter)

    result = validate_all_agents(registry_path, verbose=False)

    assert isinstance(result, Failure)
    assert isinstance(result.error, AggregateError)


def test_validate_all_agents_verbose_mode(temp_dir, valid_registry_data, capsys, monkeypatch):
    """Test validation with verbose output."""
    monkeypatch.chdir(temp_dir)
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    # Create agent files
    for agent_name, entry in valid_registry_data["agents"].items():
        agent_path = temp_dir / entry["path"]
        frontmatter = {
            "name": agent_name,
            "version": entry["version"],
            "description": f"Description for {agent_name}",
        }
        create_markdown_file(agent_path, frontmatter)

    result = validate_all_agents(registry_path, verbose=True)

    assert isinstance(result, Success)
    captured = capsys.readouterr()
    assert "Validating agent:" in captured.out


# -----------------------------------------------------------------------------
# Test CLI main function
# -----------------------------------------------------------------------------


def test_main_success(temp_dir, valid_registry_data, monkeypatch, capsys):
    """Test main CLI with successful validation."""
    monkeypatch.chdir(temp_dir)
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    # Create agent files
    for agent_name, entry in valid_registry_data["agents"].items():
        agent_path = temp_dir / entry["path"]
        frontmatter = {
            "name": agent_name,
            "version": entry["version"],
            "description": f"Description for {agent_name}",
        }
        create_markdown_file(agent_path, frontmatter)

    # Mock sys.argv
    monkeypatch.setattr(
        sys, "argv", ["validate-agents.py", "--registry", str(registry_path)]
    )

    exit_code = validate_module.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "validated successfully" in captured.out.lower()


def test_main_with_errors(temp_dir, valid_registry_data, monkeypatch, capsys):
    """Test main CLI with validation errors."""
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    # Don't create agent files to trigger errors

    # Mock sys.argv
    monkeypatch.setattr(
        sys, "argv", ["validate-agents.py", "--registry", str(registry_path)]
    )

    exit_code = validate_module.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.err


def test_main_json_output_success(temp_dir, valid_registry_data, monkeypatch, capsys):
    """Test main CLI with JSON output for success."""
    monkeypatch.chdir(temp_dir)
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    # Create agent files
    for agent_name, entry in valid_registry_data["agents"].items():
        agent_path = temp_dir / entry["path"]
        frontmatter = {
            "name": agent_name,
            "version": entry["version"],
            "description": f"Description for {agent_name}",
        }
        create_markdown_file(agent_path, frontmatter)

    # Mock sys.argv
    monkeypatch.setattr(
        sys, "argv", ["validate-agents.py", "--registry", str(registry_path), "--json"]
    )

    exit_code = validate_module.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["success"] is True
    assert output["total_agents"] == 2


def test_main_json_output_errors(temp_dir, valid_registry_data, monkeypatch, capsys):
    """Test main CLI with JSON output for errors."""
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    # Don't create agent files to trigger errors

    # Mock sys.argv
    monkeypatch.setattr(
        sys, "argv", ["validate-agents.py", "--registry", str(registry_path), "--json"]
    )

    exit_code = validate_module.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["success"] is False
    assert "errors" in output


def test_main_verbose_flag(temp_dir, valid_registry_data, monkeypatch, capsys):
    """Test main CLI with verbose flag."""
    monkeypatch.chdir(temp_dir)
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    # Create agent files
    for agent_name, entry in valid_registry_data["agents"].items():
        agent_path = temp_dir / entry["path"]
        frontmatter = {
            "name": agent_name,
            "version": entry["version"],
            "description": f"Description for {agent_name}",
        }
        create_markdown_file(agent_path, frontmatter)

    # Mock sys.argv
    monkeypatch.setattr(
        sys,
        "argv",
        ["validate-agents.py", "--registry", str(registry_path), "--verbose"],
    )

    exit_code = validate_module.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Validating agent:" in captured.out


def test_main_default_registry_path(temp_dir, monkeypatch, capsys):
    """Test main CLI with default registry path."""
    # Change to temp dir
    monkeypatch.chdir(temp_dir)

    # Create registry at default location
    registry_path = temp_dir / ".claude" / "agents" / "registry.yaml"
    # Use relative path from where registry is located
    registry_data = {
        "agents": {"test-agent": {"version": "1.0.0", "path": "test.md"}}
    }
    create_yaml_file(registry_path, registry_data)

    # Create agent file in same directory as registry
    agent_path = temp_dir / ".claude" / "agents" / "test.md"
    frontmatter = {
        "name": "test-agent",
        "version": "1.0.0",
        "description": "Test agent",
    }
    create_markdown_file(agent_path, frontmatter)

    # Mock sys.argv with no --registry flag
    monkeypatch.setattr(sys, "argv", ["validate-agents.py"])

    exit_code = validate_module.main()

    assert exit_code == 0


def test_main_with_skill_output(temp_dir, valid_registry_with_skills, monkeypatch, capsys):
    """Test main CLI with skills in output."""
    monkeypatch.chdir(temp_dir)
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_with_skills)

    # Create agent files
    for agent_name, entry in valid_registry_with_skills["agents"].items():
        agent_path = temp_dir / entry["path"]
        frontmatter = {
            "name": agent_name,
            "version": entry["version"],
            "description": f"Description for {agent_name}",
        }
        create_markdown_file(agent_path, frontmatter)

    # Mock sys.argv
    monkeypatch.setattr(
        sys, "argv", ["validate-agents.py", "--registry", str(registry_path)]
    )

    exit_code = validate_module.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Skills:" in captured.out
    assert "Validated dependencies:" in captured.out


# -----------------------------------------------------------------------------
# Test ValidationData
# -----------------------------------------------------------------------------


def test_validation_data_creation():
    """Test ValidationData dataclass creation."""
    data = ValidationData(
        registry_path="/path/to/registry.yaml",
        total_agents=5,
        validated_agents=5,
        total_skills=2,
        validated_dependencies=4,
        warnings=["Warning 1"],
    )
    assert data.registry_path == "/path/to/registry.yaml"
    assert data.total_agents == 5
    assert len(data.warnings) == 1


# -----------------------------------------------------------------------------
# Test edge cases
# -----------------------------------------------------------------------------


def test_agent_with_version_0_0_0(temp_dir, monkeypatch):
    """Test agent with version 0.0.0."""
    monkeypatch.chdir(temp_dir)
    agent_path = temp_dir / "test-agent.md"
    frontmatter = {
        "name": "test-agent",
        "version": "0.0.0",
        "description": "Test agent",
    }
    create_markdown_file(agent_path, frontmatter)

    registry_entry = AgentRegistryEntry(version="0.0.0", path="test-agent.md")

    result = validate_agent_version("test-agent", registry_entry, temp_dir)

    assert isinstance(result, Success)


def test_skill_constraint_with_high_version(temp_dir):
    """Test skill constraint with high version number."""
    skill_dep = SkillDependency(depends_on={"test-agent": "999.x"})
    registry_data = {
        "agents": {"test-agent": {"version": "999.0.0", "path": "test.md"}}
    }
    registry = AgentRegistry(**registry_data)

    result = validate_skill_constraints("test-skill", skill_dep, registry)

    assert isinstance(result, Success)


def test_empty_registry_agents(temp_dir):
    """Test validation with empty agents list."""
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, {"agents": {}})

    result = validate_all_agents(registry_path, verbose=False)

    assert isinstance(result, Success)
    assert result.value.total_agents == 0
    assert result.value.validated_agents == 0


def test_registry_with_no_skills_field(temp_dir, monkeypatch):
    """Test registry without skills field."""
    monkeypatch.chdir(temp_dir)
    registry_data = {
        "agents": {"test-agent": {"version": "1.0.0", "path": ".claude/agents/test.md"}}
    }
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, registry_data)

    # Create agent file
    agent_path = temp_dir / ".claude" / "agents" / "test.md"
    frontmatter = {
        "name": "test-agent",
        "version": "1.0.0",
        "description": "Test agent",
    }
    create_markdown_file(agent_path, frontmatter)

    result = validate_all_agents(registry_path, verbose=False)

    assert isinstance(result, Success)
    assert result.value.total_skills == 0


def test_skill_dependency_empty_depends_on():
    """Test skill dependency with empty depends_on."""
    skill_dep = SkillDependency(depends_on={})
    registry_data = {"agents": {}}
    registry = AgentRegistry(**registry_data)

    result = validate_skill_constraints("test-skill", skill_dep, registry)

    assert isinstance(result, Success)
    assert len(result.value) == 0


def test_main_with_warnings(temp_dir, valid_registry_data, monkeypatch, capsys):
    """Test main CLI with warnings in output."""
    monkeypatch.chdir(temp_dir)
    # Create a modified validate_all_agents that returns success with warnings
    registry_path = temp_dir / "registry.yaml"
    create_yaml_file(registry_path, valid_registry_data)

    # Create agent files
    for agent_name, entry in valid_registry_data["agents"].items():
        agent_path = temp_dir / entry["path"]
        frontmatter = {
            "name": agent_name,
            "version": entry["version"],
            "description": f"Description for {agent_name}",
        }
        create_markdown_file(agent_path, frontmatter)

    # Monkey-patch validate_all_agents to return warnings
    original_validate = validate_module.validate_all_agents

    def mock_validate_with_warnings(*args, **kwargs):
        result = original_validate(*args, **kwargs)
        if isinstance(result, Success):
            result.value.warnings.append("Test warning message")
        return result

    monkeypatch.setattr(validate_module, "validate_all_agents", mock_validate_with_warnings)

    # Mock sys.argv
    monkeypatch.setattr(
        sys, "argv", ["validate-agents.py", "--registry", str(registry_path)]
    )

    exit_code = validate_module.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Warnings:" in captured.out
    assert "Test warning message" in captured.out


def test_main_json_output_with_non_aggregate_error(temp_dir, monkeypatch, capsys):
    """Test main CLI JSON output with non-AggregateError."""
    registry_path = temp_dir / "nonexistent.yaml"

    # Mock sys.argv
    monkeypatch.setattr(
        sys, "argv", ["validate-agents.py", "--registry", str(registry_path), "--json"]
    )

    exit_code = validate_module.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["success"] is False
    assert "errors" in output
    assert len(output["errors"]) >= 1


def test_main_non_json_output_with_non_aggregate_error(temp_dir, monkeypatch, capsys):
    """Test main CLI standard output with non-AggregateError."""
    registry_path = temp_dir / "nonexistent.yaml"

    # Mock sys.argv
    monkeypatch.setattr(
        sys, "argv", ["validate-agents.py", "--registry", str(registry_path)]
    )

    exit_code = validate_module.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.err
