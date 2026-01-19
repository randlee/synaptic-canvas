"""Tests for validate-cross-references.py script."""

import json
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# Import using importlib to handle hyphens in filename
import importlib.util

spec = importlib.util.spec_from_file_location(
    "validate_cross_references",
    Path(__file__).parent.parent.parent / "scripts" / "validate-cross-references.py",
)
validate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_module)

# Import functions and classes
load_yaml = validate_module.load_yaml
load_json = validate_module.load_json
validate_manifest_plugin_consistency = validate_module.validate_manifest_plugin_consistency
validate_marketplace_consistency = validate_module.validate_marketplace_consistency
validate_registry_consistency = validate_module.validate_registry_consistency
validate_agent_registry = validate_module.validate_agent_registry
validate_dependencies = validate_module.validate_dependencies
validate_package = validate_module.validate_package
validate_all = validate_module.validate_all
DependencyGraph = validate_module.DependencyGraph
ManifestSchema = validate_module.ManifestSchema
PluginSchema = validate_module.PluginSchema
MarketplaceSchema = validate_module.MarketplaceSchema
RegistrySchema = validate_module.RegistrySchema
AgentRegistrySchema = validate_module.AgentRegistrySchema
CrossReferenceError = validate_module.CrossReferenceError
ValidationReport = validate_module.ValidationReport
Success = validate_module.Success
Failure = validate_module.Failure


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


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
        "version": "0.7.0",
        "description": "Test package description",
        "author": "test-author",
        "license": "MIT",
        "tags": ["test", "sample"],
        "artifacts": {
            "commands": ["commands/test.md"],
            "agents": ["agents/test-agent.md"],
        },
        "requires": ["git >= 2.20"],
    }


@pytest.fixture
def sample_plugin():
    """Sample plugin.json content."""
    return {
        "name": "test-package",
        "description": "Test package description",
        "version": "0.7.0",
        "author": {"name": "test-author"},
        "license": "MIT",
        "keywords": ["test", "sample"],
        "commands": ["./commands/test.md"],
        "agents": ["./agents/test-agent.md"],
    }


@pytest.fixture
def sample_marketplace():
    """Sample marketplace.json content."""
    return {
        "name": "test-marketplace",
        "owner": {"name": "test-owner"},
        "metadata": {"version": "0.7.0"},
        "plugins": [
            {
                "name": "test-package",
                "source": "./packages/test-package",
                "description": "Test package description",
                "version": "0.7.0",
                "author": {"name": "test-author"},
                "license": "MIT",
                "keywords": ["test"],
                "category": "tools",
            }
        ],
    }


@pytest.fixture
def sample_registry():
    """Sample registry.json content."""
    return {
        "packages": {
            "test-package": {
                "name": "test-package",
                "version": "0.7.0",
                "status": "beta",
                "tier": 0,
                "description": "Test package description",
                "github": "test/repo",
                "repo": "https://github.com/test/repo",
                "path": "packages/test-package",
                "license": "MIT",
                "author": "test-author",
                "tags": ["test"],
                "artifacts": {"commands": 1, "agents": 1},
                "dependencies": [],
            }
        }
    }


@pytest.fixture
def sample_agent_registry():
    """Sample .claude/agents/registry.yaml content."""
    return {
        "agents": {
            "test-agent": {"version": "0.1.0", "path": ".claude/agents/test-agent.md"}
        },
        "skills": {},
    }


# -----------------------------------------------------------------------------
# Schema Tests
# -----------------------------------------------------------------------------


def test_manifest_schema_valid():
    """Test ManifestSchema with valid data."""
    data = {
        "name": "test-pkg",
        "version": "1.0.0",
        "description": "Test",
        "author": "author",
        "license": "MIT",
    }
    manifest = ManifestSchema(**data)
    assert manifest.name == "test-pkg"
    assert manifest.version == "1.0.0"


def test_manifest_schema_invalid_version():
    """Test ManifestSchema rejects invalid version."""
    data = {
        "name": "test-pkg",
        "version": "invalid",
        "description": "Test",
        "author": "author",
        "license": "MIT",
    }
    with pytest.raises(ValueError):
        ManifestSchema(**data)


def test_plugin_schema_valid():
    """Test PluginSchema with valid data."""
    data = {
        "name": "test-pkg",
        "description": "Test",
        "version": "1.0.0",
        "author": {"name": "author"},
        "license": "MIT",
    }
    plugin = PluginSchema(**data)
    assert plugin.name == "test-pkg"


def test_marketplace_schema_valid(sample_marketplace):
    """Test MarketplaceSchema with valid data."""
    marketplace = MarketplaceSchema(**sample_marketplace)
    assert marketplace.name == "test-marketplace"
    assert len(marketplace.plugins) == 1


def test_registry_schema_valid(sample_registry):
    """Test RegistrySchema with valid data."""
    registry = RegistrySchema(**sample_registry)
    assert "test-package" in registry.packages


def test_agent_registry_schema_valid(sample_agent_registry):
    """Test AgentRegistrySchema with valid data."""
    registry = AgentRegistrySchema(**sample_agent_registry)
    assert "test-agent" in registry.agents


# -----------------------------------------------------------------------------
# Load File Tests
# -----------------------------------------------------------------------------


def test_load_yaml_success(temp_dir, sample_manifest):
    """Test loading valid YAML file."""
    yaml_file = temp_dir / "test.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_manifest, f)

    result = load_yaml(yaml_file)
    assert isinstance(result, Success)
    assert result.value["name"] == "test-package"


def test_load_yaml_missing(temp_dir):
    """Test loading non-existent YAML file."""
    yaml_file = temp_dir / "missing.yaml"
    result = load_yaml(yaml_file)
    assert isinstance(result, Failure)
    assert "not found" in result.error.message.lower()


def test_load_yaml_invalid(temp_dir):
    """Test loading invalid YAML file."""
    yaml_file = temp_dir / "invalid.yaml"
    with open(yaml_file, "w") as f:
        f.write("invalid: yaml: :{{{")

    result = load_yaml(yaml_file)
    assert isinstance(result, Failure)
    assert "yaml" in result.error.message.lower()


def test_load_yaml_empty(temp_dir):
    """Test loading empty YAML file."""
    yaml_file = temp_dir / "empty.yaml"
    with open(yaml_file, "w") as f:
        f.write("")

    result = load_yaml(yaml_file)
    assert isinstance(result, Failure)
    assert "empty" in result.error.message.lower()


def test_load_json_success(temp_dir, sample_plugin):
    """Test loading valid JSON file."""
    json_file = temp_dir / "test.json"
    with open(json_file, "w") as f:
        json.dump(sample_plugin, f)

    result = load_json(json_file)
    assert isinstance(result, Success)
    assert result.value["name"] == "test-package"


def test_load_json_missing(temp_dir):
    """Test loading non-existent JSON file."""
    json_file = temp_dir / "missing.json"
    result = load_json(json_file)
    assert isinstance(result, Failure)
    assert "not found" in result.error.message.lower()


def test_load_json_invalid(temp_dir):
    """Test loading invalid JSON file."""
    json_file = temp_dir / "invalid.json"
    with open(json_file, "w") as f:
        f.write("not valid json {{{")

    result = load_json(json_file)
    assert isinstance(result, Failure)
    assert "json" in result.error.message.lower()


# -----------------------------------------------------------------------------
# Manifest-Plugin Consistency Tests
# -----------------------------------------------------------------------------


def test_validate_manifest_plugin_consistency_success(temp_dir, sample_manifest, sample_plugin):
    """Test successful manifest-plugin validation."""
    manifest_path = temp_dir / "manifest.yaml"
    plugin_path = temp_dir / "plugin.json"

    # Create artifact files
    commands_dir = temp_dir / "commands"
    agents_dir = temp_dir / "agents"
    commands_dir.mkdir()
    agents_dir.mkdir()
    (commands_dir / "test.md").write_text("# Test command")
    (agents_dir / "test-agent.md").write_text("# Test agent")

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    result = validate_manifest_plugin_consistency(manifest_path, plugin_path)
    assert isinstance(result, Success)


def test_validate_manifest_plugin_version_mismatch(temp_dir, sample_manifest, sample_plugin):
    """Test detection of version mismatch."""
    manifest_path = temp_dir / "manifest.yaml"
    plugin_path = temp_dir / "plugin.json"

    sample_manifest["version"] = "0.7.0"
    sample_plugin["version"] = "0.6.0"

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    result = validate_manifest_plugin_consistency(manifest_path, plugin_path)
    assert isinstance(result, Failure)
    assert "version mismatch" in result.error.message.lower()


def test_validate_manifest_plugin_name_mismatch(temp_dir, sample_manifest, sample_plugin):
    """Test detection of name mismatch."""
    manifest_path = temp_dir / "manifest.yaml"
    plugin_path = temp_dir / "plugin.json"

    sample_manifest["name"] = "package-a"
    sample_plugin["name"] = "package-b"

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    result = validate_manifest_plugin_consistency(manifest_path, plugin_path)
    assert isinstance(result, Failure)
    assert "name mismatch" in result.error.message.lower()


def test_validate_manifest_plugin_description_mismatch(
    temp_dir, sample_manifest, sample_plugin
):
    """Test warning for description mismatch."""
    manifest_path = temp_dir / "manifest.yaml"
    plugin_path = temp_dir / "plugin.json"

    # Create artifacts
    commands_dir = temp_dir / "commands"
    agents_dir = temp_dir / "agents"
    commands_dir.mkdir()
    agents_dir.mkdir()
    (commands_dir / "test.md").write_text("# Test")
    (agents_dir / "test-agent.md").write_text("# Test")

    sample_manifest["description"] = "Description A"
    sample_plugin["description"] = "Description B"

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    result = validate_manifest_plugin_consistency(manifest_path, plugin_path)
    assert isinstance(result, Success)
    assert len(result.warnings) > 0
    assert any("description" in w.lower() for w in result.warnings)


def test_validate_manifest_plugin_missing_artifact(temp_dir, sample_manifest, sample_plugin):
    """Test detection of missing artifact file."""
    manifest_path = temp_dir / "manifest.yaml"
    plugin_path = temp_dir / "plugin.json"

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    result = validate_manifest_plugin_consistency(manifest_path, plugin_path)
    assert isinstance(result, Failure)
    assert "artifact not found" in result.error.message.lower()


# -----------------------------------------------------------------------------
# Marketplace Consistency Tests
# -----------------------------------------------------------------------------


def test_validate_marketplace_consistency_success(temp_dir, sample_marketplace, sample_manifest):
    """Test successful marketplace validation."""
    marketplace_path = temp_dir / "marketplace.json"
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    manifest_path = pkg_dir / "manifest.yaml"

    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)
    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)

    result = validate_marketplace_consistency(marketplace_path, packages_dir)
    assert isinstance(result, Success)


def test_validate_marketplace_consistency_missing_manifest(temp_dir, sample_marketplace):
    """Test detection of missing manifest for marketplace plugin."""
    marketplace_path = temp_dir / "marketplace.json"
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    result = validate_marketplace_consistency(marketplace_path, packages_dir)
    assert isinstance(result, Failure)
    assert "manifest not found" in result.error.message.lower()


def test_validate_marketplace_consistency_version_mismatch(
    temp_dir, sample_marketplace, sample_manifest
):
    """Test detection of version mismatch."""
    marketplace_path = temp_dir / "marketplace.json"
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    manifest_path = pkg_dir / "manifest.yaml"

    sample_marketplace["plugins"][0]["version"] = "0.6.0"
    sample_manifest["version"] = "0.7.0"

    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)
    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)

    result = validate_marketplace_consistency(marketplace_path, packages_dir)
    assert isinstance(result, Failure)
    assert "version mismatch" in result.error.message.lower()


# -----------------------------------------------------------------------------
# Registry Consistency Tests
# -----------------------------------------------------------------------------


def test_validate_registry_consistency_success(temp_dir, sample_registry, sample_manifest):
    """Test successful registry validation."""
    registry_path = temp_dir / "registry.json"
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    manifest_path = pkg_dir / "manifest.yaml"

    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)
    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)

    result = validate_registry_consistency(registry_path, packages_dir)
    assert isinstance(result, Success)


def test_validate_registry_consistency_missing_manifest(temp_dir, sample_registry):
    """Test detection of missing manifest for registry package."""
    registry_path = temp_dir / "registry.json"
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = validate_registry_consistency(registry_path, packages_dir)
    assert isinstance(result, Failure)
    assert "manifest not found" in result.error.message.lower()


def test_validate_registry_consistency_version_mismatch(
    temp_dir, sample_registry, sample_manifest
):
    """Test detection of version mismatch."""
    registry_path = temp_dir / "registry.json"
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    manifest_path = pkg_dir / "manifest.yaml"

    sample_registry["packages"]["test-package"]["version"] = "0.6.0"
    sample_manifest["version"] = "0.7.0"

    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)
    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)

    result = validate_registry_consistency(registry_path, packages_dir)
    assert isinstance(result, Failure)
    assert "version mismatch" in result.error.message.lower()


# -----------------------------------------------------------------------------
# Agent Registry Tests
# -----------------------------------------------------------------------------


def test_validate_agent_registry_success(temp_dir, sample_agent_registry):
    """Test successful agent registry validation."""
    registry_path = temp_dir / "registry.yaml"
    repo_root = temp_dir

    agent_dir = temp_dir / ".claude" / "agents"
    agent_dir.mkdir(parents=True)
    (agent_dir / "test-agent.md").write_text("# Test Agent")

    with open(registry_path, "w") as f:
        yaml.dump(sample_agent_registry, f)

    result = validate_agent_registry(registry_path, repo_root)
    assert isinstance(result, Success)


def test_validate_agent_registry_missing_file(temp_dir, sample_agent_registry):
    """Test detection of missing agent file."""
    registry_path = temp_dir / "registry.yaml"
    repo_root = temp_dir

    with open(registry_path, "w") as f:
        yaml.dump(sample_agent_registry, f)

    result = validate_agent_registry(registry_path, repo_root)
    assert isinstance(result, Failure)
    assert "agent file not found" in result.error.message.lower()


# -----------------------------------------------------------------------------
# Dependency Tests
# -----------------------------------------------------------------------------


def test_dependency_graph_add_node():
    """Test adding nodes to dependency graph."""
    graph = DependencyGraph()
    graph.add_node("pkg-a")
    assert "pkg-a" in graph.nodes
    assert "pkg-a" in graph.edges


def test_dependency_graph_add_edge():
    """Test adding edges to dependency graph."""
    graph = DependencyGraph()
    graph.add_edge("pkg-a", "pkg-b")
    assert "pkg-a" in graph.nodes
    assert "pkg-b" in graph.nodes
    assert "pkg-b" in graph.edges["pkg-a"]


def test_dependency_graph_no_cycles():
    """Test cycle detection with no cycles."""
    graph = DependencyGraph()
    graph.add_edge("pkg-a", "pkg-b")
    graph.add_edge("pkg-b", "pkg-c")
    cycles = graph.detect_cycles()
    assert len(cycles) == 0


def test_dependency_graph_simple_cycle():
    """Test detection of simple cycle."""
    graph = DependencyGraph()
    graph.add_edge("pkg-a", "pkg-b")
    graph.add_edge("pkg-b", "pkg-a")
    cycles = graph.detect_cycles()
    assert len(cycles) > 0


def test_dependency_graph_complex_cycle():
    """Test detection of complex cycle."""
    graph = DependencyGraph()
    graph.add_edge("pkg-a", "pkg-b")
    graph.add_edge("pkg-b", "pkg-c")
    graph.add_edge("pkg-c", "pkg-a")
    cycles = graph.detect_cycles()
    assert len(cycles) > 0


def test_validate_dependencies_success(temp_dir):
    """Test successful dependency validation."""
    packages_dir = temp_dir / "packages"

    # Create package A with no dependencies
    pkg_a_dir = packages_dir / "sc-pkg-a"
    pkg_a_dir.mkdir(parents=True)
    manifest_a = {
        "name": "sc-pkg-a",
        "version": "1.0.0",
        "description": "Package A",
        "author": "test",
        "license": "MIT",
        "requires": [],
    }
    with open(pkg_a_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest_a, f)

    # Create package B depending on A
    pkg_b_dir = packages_dir / "sc-pkg-b"
    pkg_b_dir.mkdir(parents=True)
    manifest_b = {
        "name": "sc-pkg-b",
        "version": "1.0.0",
        "description": "Package B",
        "author": "test",
        "license": "MIT",
        "requires": ["sc-pkg-a >= 1.0.0"],
    }
    with open(pkg_b_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest_b, f)

    result = validate_dependencies(packages_dir)
    assert isinstance(result, Success)


def test_validate_dependencies_invalid_reference(temp_dir):
    """Test detection of invalid package reference."""
    packages_dir = temp_dir / "packages"

    # Create package depending on non-existent package
    pkg_dir = packages_dir / "sc-pkg-a"
    pkg_dir.mkdir(parents=True)
    manifest = {
        "name": "sc-pkg-a",
        "version": "1.0.0",
        "description": "Package A",
        "author": "test",
        "license": "MIT",
        "requires": ["sc-pkg-nonexistent >= 1.0.0"],
    }
    with open(pkg_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    result = validate_dependencies(packages_dir)
    assert isinstance(result, Failure)
    assert "non-existent" in result.error.message.lower()


def test_validate_dependencies_circular(temp_dir):
    """Test detection of circular dependencies."""
    packages_dir = temp_dir / "packages"

    # Create package A depending on B
    pkg_a_dir = packages_dir / "sc-pkg-a"
    pkg_a_dir.mkdir(parents=True)
    manifest_a = {
        "name": "sc-pkg-a",
        "version": "1.0.0",
        "description": "Package A",
        "author": "test",
        "license": "MIT",
        "requires": ["sc-pkg-b >= 1.0.0"],
    }
    with open(pkg_a_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest_a, f)

    # Create package B depending on A
    pkg_b_dir = packages_dir / "sc-pkg-b"
    pkg_b_dir.mkdir(parents=True)
    manifest_b = {
        "name": "sc-pkg-b",
        "version": "1.0.0",
        "description": "Package B",
        "author": "test",
        "license": "MIT",
        "requires": ["sc-pkg-a >= 1.0.0"],
    }
    with open(pkg_b_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest_b, f)

    result = validate_dependencies(packages_dir)
    assert isinstance(result, Failure)
    assert "circular" in result.error.message.lower()


def test_validate_dependencies_non_package_deps(temp_dir):
    """Test that non-package dependencies are ignored."""
    packages_dir = temp_dir / "packages"

    pkg_dir = packages_dir / "sc-pkg-a"
    pkg_dir.mkdir(parents=True)
    manifest = {
        "name": "sc-pkg-a",
        "version": "1.0.0",
        "description": "Package A",
        "author": "test",
        "license": "MIT",
        "requires": ["git >= 2.20", "python >= 3.10"],
    }
    with open(pkg_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    result = validate_dependencies(packages_dir)
    assert isinstance(result, Success)


def test_validate_dependencies_dict_format(temp_dir):
    """Test dependency validation with dict format (packages/cli)."""
    packages_dir = temp_dir / "packages"

    # Create package A
    pkg_a_dir = packages_dir / "sc-pkg-a"
    pkg_a_dir.mkdir(parents=True)
    manifest_a = {
        "name": "sc-pkg-a",
        "version": "1.0.0",
        "description": "Package A",
        "author": "test",
        "license": "MIT",
        "requires": {"packages": [], "cli": ["git >= 2.20"]},
    }
    with open(pkg_a_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest_a, f)

    # Create package B depending on A (dict format)
    pkg_b_dir = packages_dir / "sc-pkg-b"
    pkg_b_dir.mkdir(parents=True)
    manifest_b = {
        "name": "sc-pkg-b",
        "version": "1.0.0",
        "description": "Package B",
        "author": "test",
        "license": "MIT",
        "requires": {"packages": ["sc-pkg-a >= 1.0.0"], "cli": ["gh >= 2.0"]},
    }
    with open(pkg_b_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest_b, f)

    result = validate_dependencies(packages_dir)
    assert isinstance(result, Success)


def test_validate_dependencies_dict_format_invalid(temp_dir):
    """Test detection of invalid dependency in dict format."""
    packages_dir = temp_dir / "packages"

    pkg_dir = packages_dir / "sc-pkg-a"
    pkg_dir.mkdir(parents=True)
    manifest = {
        "name": "sc-pkg-a",
        "version": "1.0.0",
        "description": "Package A",
        "author": "test",
        "license": "MIT",
        "requires": {"packages": ["sc-nonexistent >= 1.0.0"], "cli": []},
    }
    with open(pkg_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    result = validate_dependencies(packages_dir)
    assert isinstance(result, Failure)
    assert "non-existent" in result.error.message.lower()


def test_manifest_schema_requires_dict():
    """Test ManifestSchema accepts dict format for requires."""
    data = {
        "name": "test-pkg",
        "version": "1.0.0",
        "description": "Test",
        "author": "author",
        "license": "MIT",
        "requires": {"packages": ["sc-dep >= 1.0.0"], "cli": ["git >= 2.20"]},
    }
    manifest = ManifestSchema(**data)
    assert manifest.requires is not None
    assert isinstance(manifest.requires, dict)


def test_manifest_schema_requires_list():
    """Test ManifestSchema accepts list format for requires."""
    data = {
        "name": "test-pkg",
        "version": "1.0.0",
        "description": "Test",
        "author": "author",
        "license": "MIT",
        "requires": ["git >= 2.20", "python >= 3.10"],
    }
    manifest = ManifestSchema(**data)
    assert manifest.requires is not None
    assert isinstance(manifest.requires, list)


# -----------------------------------------------------------------------------
# Package Validation Tests
# -----------------------------------------------------------------------------


def test_validate_package_success(temp_dir, sample_manifest, sample_plugin):
    """Test successful package validation."""
    package_dir = temp_dir / "test-package"
    package_dir.mkdir()

    manifest_path = package_dir / "manifest.yaml"
    plugin_dir = package_dir / ".claude-plugin"
    plugin_dir.mkdir()
    plugin_path = plugin_dir / "plugin.json"

    # Create artifact files
    commands_dir = package_dir / "commands"
    agents_dir = package_dir / "agents"
    commands_dir.mkdir()
    agents_dir.mkdir()
    (commands_dir / "test.md").write_text("# Test")
    (agents_dir / "test-agent.md").write_text("# Test")

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    result = validate_package(package_dir, temp_dir)
    assert isinstance(result, Success)


def test_validate_package_missing_files(temp_dir):
    """Test package validation when files are missing."""
    package_dir = temp_dir / "test-package"
    package_dir.mkdir()

    result = validate_package(package_dir, temp_dir)
    assert isinstance(result, Success)  # No files to validate


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------


def test_validate_all_success(temp_dir, sample_manifest, sample_plugin):
    """Test full validation with valid repository."""
    # Create directory structure
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    # Create manifest
    manifest_path = pkg_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)

    # Create plugin.json
    plugin_dir = pkg_dir / ".claude-plugin"
    plugin_dir.mkdir()
    plugin_path = plugin_dir / "plugin.json"
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    # Create artifact files
    commands_dir = pkg_dir / "commands"
    agents_dir = pkg_dir / "agents"
    commands_dir.mkdir()
    agents_dir.mkdir()
    (commands_dir / "test.md").write_text("# Test")
    (agents_dir / "test-agent.md").write_text("# Test")

    result = validate_all(temp_dir)
    assert isinstance(result, Success)
    assert result.value.is_valid()


def test_validate_all_with_errors(temp_dir, sample_manifest, sample_plugin):
    """Test full validation with errors."""
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    # Create mismatched versions
    sample_manifest["version"] = "0.7.0"
    sample_plugin["version"] = "0.6.0"

    manifest_path = pkg_dir / "manifest.yaml"
    plugin_dir = pkg_dir / ".claude-plugin"
    plugin_dir.mkdir()
    plugin_path = plugin_dir / "plugin.json"

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    result = validate_all(temp_dir)
    assert isinstance(result, Failure)
    assert result.partial_result is not None
    assert not result.partial_result.is_valid()


def test_validate_all_with_package_filter(temp_dir, sample_manifest, sample_plugin):
    """Test validation with package filter."""
    packages_dir = temp_dir / "packages"

    # Create two packages
    for pkg_name in ["pkg-a", "pkg-b"]:
        pkg_dir = packages_dir / pkg_name
        pkg_dir.mkdir(parents=True)

        manifest = sample_manifest.copy()
        manifest["name"] = pkg_name
        plugin = sample_plugin.copy()
        plugin["name"] = pkg_name

        manifest_path = pkg_dir / "manifest.yaml"
        plugin_dir = pkg_dir / ".claude-plugin"
        plugin_dir.mkdir()
        plugin_path = plugin_dir / "plugin.json"

        # Create artifacts
        commands_dir = pkg_dir / "commands"
        agents_dir = pkg_dir / "agents"
        commands_dir.mkdir()
        agents_dir.mkdir()
        (commands_dir / "test.md").write_text("# Test")
        (agents_dir / "test-agent.md").write_text("# Test")

        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)
        with open(plugin_path, "w") as f:
            json.dump(plugin, f)

    # Validate only pkg-a
    result = validate_all(temp_dir, package_filter="pkg-a")
    assert isinstance(result, Success)


# -----------------------------------------------------------------------------
# Edge Case Tests
# -----------------------------------------------------------------------------


def test_validation_report_is_valid():
    """Test ValidationReport.is_valid method."""
    report = ValidationReport(total_checks=5, passed_checks=5, failed_checks=0)
    assert report.is_valid() is True

    report = ValidationReport(total_checks=5, passed_checks=4, failed_checks=1)
    assert report.is_valid() is False


def test_cross_reference_error_with_context():
    """Test CrossReferenceError with context."""
    error = CrossReferenceError(
        message="Test error",
        source_file="source.yaml",
        target_file="target.json",
        context={"key": "value"},
    )
    assert error.message == "Test error"
    assert error.context["key"] == "value"


def test_empty_packages_directory(temp_dir):
    """Test validation with empty packages directory."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    result = validate_all(temp_dir)
    assert isinstance(result, Success)


def test_validate_dependencies_empty_requires(temp_dir):
    """Test dependency validation with empty requires list."""
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "sc-pkg-a"
    pkg_dir.mkdir(parents=True)

    manifest = {
        "name": "sc-pkg-a",
        "version": "1.0.0",
        "description": "Test",
        "author": "test",
        "license": "MIT",
    }
    with open(pkg_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    result = validate_dependencies(packages_dir)
    assert isinstance(result, Success)


# -----------------------------------------------------------------------------
# CLI/Main Tests
# -----------------------------------------------------------------------------


def test_main_success(temp_dir, sample_manifest, sample_plugin, monkeypatch, capsys):
    """Test main() with successful validation."""
    # Setup valid repository structure
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    manifest_path = pkg_dir / "manifest.yaml"
    plugin_dir = pkg_dir / ".claude-plugin"
    plugin_dir.mkdir()
    plugin_path = plugin_dir / "plugin.json"

    # Create artifacts
    commands_dir = pkg_dir / "commands"
    agents_dir = pkg_dir / "agents"
    commands_dir.mkdir()
    agents_dir.mkdir()
    (commands_dir / "test.md").write_text("# Test")
    (agents_dir / "test-agent.md").write_text("# Test")

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    # Mock __file__ path
    import sys

    original_file = validate_module.__file__
    validate_module.__file__ = str(temp_dir / "scripts" / "validate-cross-references.py")

    # Mock sys.argv
    monkeypatch.setattr(sys, "argv", ["validate-cross-references.py"])

    try:
        exit_code = validate_module.main()
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "All cross-references valid" in captured.out
        assert "Total checks:" in captured.out
    finally:
        validate_module.__file__ = original_file


def test_main_with_errors(temp_dir, sample_manifest, sample_plugin, monkeypatch, capsys):
    """Test main() with validation errors."""
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    # Create version mismatch
    sample_manifest["version"] = "0.7.0"
    sample_plugin["version"] = "0.6.0"

    manifest_path = pkg_dir / "manifest.yaml"
    plugin_dir = pkg_dir / ".claude-plugin"
    plugin_dir.mkdir()
    plugin_path = plugin_dir / "plugin.json"

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    # Mock __file__ path
    original_file = validate_module.__file__
    validate_module.__file__ = str(temp_dir / "scripts" / "validate-cross-references.py")

    import sys

    monkeypatch.setattr(sys, "argv", ["validate-cross-references.py"])

    try:
        exit_code = validate_module.main()
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "validation failed" in captured.out.lower()
        assert "Errors" in captured.out
    finally:
        validate_module.__file__ = original_file


def test_main_with_verbose(temp_dir, sample_manifest, sample_plugin, monkeypatch, capsys):
    """Test main() with verbose flag."""
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    manifest_path = pkg_dir / "manifest.yaml"
    plugin_dir = pkg_dir / ".claude-plugin"
    plugin_dir.mkdir()
    plugin_path = plugin_dir / "plugin.json"

    # Create description mismatch for warning
    sample_manifest["description"] = "Description A"
    sample_plugin["description"] = "Description B"

    # Create artifacts
    commands_dir = pkg_dir / "commands"
    agents_dir = pkg_dir / "agents"
    commands_dir.mkdir()
    agents_dir.mkdir()
    (commands_dir / "test.md").write_text("# Test")
    (agents_dir / "test-agent.md").write_text("# Test")

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    # Mock __file__ path
    original_file = validate_module.__file__
    validate_module.__file__ = str(temp_dir / "scripts" / "validate-cross-references.py")

    import sys

    monkeypatch.setattr(sys, "argv", ["validate-cross-references.py", "--verbose"])

    try:
        exit_code = validate_module.main()
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Warnings" in captured.out
    finally:
        validate_module.__file__ = original_file


def test_main_with_package_filter(temp_dir, sample_manifest, sample_plugin, monkeypatch, capsys):
    """Test main() with package filter."""
    packages_dir = temp_dir / "packages"

    # Create two packages
    for pkg_name in ["pkg-a", "pkg-b"]:
        pkg_dir = packages_dir / pkg_name
        pkg_dir.mkdir(parents=True)

        manifest = sample_manifest.copy()
        manifest["name"] = pkg_name
        plugin = sample_plugin.copy()
        plugin["name"] = pkg_name

        manifest_path = pkg_dir / "manifest.yaml"
        plugin_dir = pkg_dir / ".claude-plugin"
        plugin_dir.mkdir()
        plugin_path = plugin_dir / "plugin.json"

        # Create artifacts
        commands_dir = pkg_dir / "commands"
        agents_dir = pkg_dir / "agents"
        commands_dir.mkdir()
        agents_dir.mkdir()
        (commands_dir / "test.md").write_text("# Test")
        (agents_dir / "test-agent.md").write_text("# Test")

        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)
        with open(plugin_path, "w") as f:
            json.dump(plugin, f)

    # Mock __file__ path
    original_file = validate_module.__file__
    validate_module.__file__ = str(temp_dir / "scripts" / "validate-cross-references.py")

    import sys

    monkeypatch.setattr(sys, "argv", ["validate-cross-references.py", "--package", "pkg-a"])

    try:
        exit_code = validate_module.main()
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "All cross-references valid" in captured.out
    finally:
        validate_module.__file__ = original_file


def test_main_verbose_with_errors(temp_dir, sample_manifest, sample_plugin, monkeypatch, capsys):
    """Test main() verbose mode with errors."""
    packages_dir = temp_dir / "packages"
    pkg_dir = packages_dir / "test-package"
    pkg_dir.mkdir(parents=True)

    # Create version mismatch
    sample_manifest["version"] = "0.7.0"
    sample_plugin["version"] = "0.6.0"

    manifest_path = pkg_dir / "manifest.yaml"
    plugin_dir = pkg_dir / ".claude-plugin"
    plugin_dir.mkdir()
    plugin_path = plugin_dir / "plugin.json"

    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(sample_plugin, f)

    # Mock __file__ path
    original_file = validate_module.__file__
    validate_module.__file__ = str(temp_dir / "scripts" / "validate-cross-references.py")

    import sys

    monkeypatch.setattr(sys, "argv", ["validate-cross-references.py", "--verbose"])

    try:
        exit_code = validate_module.main()
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Source:" in captured.out
        assert "Context:" in captured.out
    finally:
        validate_module.__file__ = original_file


def test_validate_all_no_partial_result_on_success(temp_dir):
    """Test validate_all returns no errors on success."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    result = validate_all(temp_dir)
    assert isinstance(result, Success)
    assert result.value.failed_checks == 0


def test_load_yaml_exception_handling(temp_dir):
    """Test YAML loading with permission error simulation."""
    import os

    yaml_file = temp_dir / "test.yaml"
    yaml_file.write_text("key: value")

    # Make file unreadable (on Unix systems)
    if os.name != "nt":
        os.chmod(yaml_file, 0o000)
        result = load_yaml(yaml_file)
        # Restore permissions
        os.chmod(yaml_file, 0o644)
        assert isinstance(result, Failure)


def test_load_json_exception_handling(temp_dir):
    """Test JSON loading with permission error simulation."""
    import os

    json_file = temp_dir / "test.json"
    json_file.write_text('{"key": "value"}')

    # Make file unreadable (on Unix systems)
    if os.name != "nt":
        os.chmod(json_file, 0o000)
        result = load_json(json_file)
        # Restore permissions
        os.chmod(json_file, 0o644)
        assert isinstance(result, Failure)


def test_validate_manifest_plugin_no_artifacts(temp_dir):
    """Test validation when manifest has no artifacts."""
    manifest_path = temp_dir / "manifest.yaml"
    plugin_path = temp_dir / "plugin.json"

    manifest = {
        "name": "test-package",
        "version": "0.7.0",
        "description": "Test package",
        "author": "test-author",
        "license": "MIT",
    }

    plugin = {
        "name": "test-package",
        "description": "Test package",
        "version": "0.7.0",
        "author": {"name": "test-author"},
        "license": "MIT",
    }

    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)
    with open(plugin_path, "w") as f:
        json.dump(plugin, f)

    result = validate_manifest_plugin_consistency(manifest_path, plugin_path)
    assert isinstance(result, Success)
