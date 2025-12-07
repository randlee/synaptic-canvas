"""Test Claude Code marketplace integration."""
import json
from pathlib import Path


def test_marketplace_json_exists():
    """Verify .claude-plugin/marketplace.json exists."""
    marketplace = Path(".claude-plugin/marketplace.json")
    assert marketplace.exists(), ".claude-plugin/marketplace.json not found"


def test_marketplace_json_valid():
    """Verify marketplace.json is valid JSON with required fields."""
    marketplace = Path(".claude-plugin/marketplace.json")
    data = json.loads(marketplace.read_text())

    assert "name" in data, "marketplace.json missing 'name' field"
    assert data["name"] == "synaptic-canvas", f"Expected name 'synaptic-canvas', got '{data['name']}'"
    assert "owner" in data, "marketplace.json missing 'owner' field"
    assert "plugins" in data, "marketplace.json missing 'plugins' field"
    assert len(data["plugins"]) == 4, f"Expected 4 plugins, found {len(data['plugins'])}"


def test_all_packages_have_plugin_json():
    """Verify each package has .claude-plugin/plugin.json."""
    packages = ["sc-delay-tasks", "sc-git-worktree", "sc-manage", "sc-repomix-nuget"]

    for pkg in packages:
        plugin_json = Path(f"packages/{pkg}/.claude-plugin/plugin.json")
        assert plugin_json.exists(), f"{pkg} missing .claude-plugin/plugin.json"

        data = json.loads(plugin_json.read_text())
        assert data["name"] == pkg, f"Expected name '{pkg}', got '{data['name']}'"
        assert "version" in data, f"{pkg}/plugin.json missing 'version' field"
        assert data["version"] == "0.5.1", f"{pkg} expected version 0.5.1, got {data['version']}"


def test_plugin_json_schema_valid():
    """Verify plugin.json files have required fields."""
    packages = ["sc-delay-tasks", "sc-git-worktree", "sc-manage", "sc-repomix-nuget"]

    required_fields = ["name", "description", "version", "author", "license"]

    for pkg in packages:
        plugin_json = Path(f"packages/{pkg}/.claude-plugin/plugin.json")
        data = json.loads(plugin_json.read_text())

        for field in required_fields:
            assert field in data, f"{pkg}/plugin.json missing required field '{field}'"


def test_marketplace_package_sources_exist():
    """Verify all package sources referenced in marketplace exist."""
    marketplace = Path(".claude-plugin/marketplace.json")
    data = json.loads(marketplace.read_text())

    for plugin in data["plugins"]:
        source = plugin["source"]
        source_path = Path(source.lstrip("./"))
        assert source_path.exists(), f"Source path '{source}' does not exist"
        assert source_path.is_dir(), f"Source path '{source}' is not a directory"


def test_plugin_component_directories_exist():
    """Verify plugin component directories (commands, agents, skills) exist."""
    packages = ["sc-delay-tasks", "sc-git-worktree", "sc-manage", "sc-repomix-nuget"]

    for pkg in packages:
        plugin_json = Path(f"packages/{pkg}/.claude-plugin/plugin.json")
        data = json.loads(plugin_json.read_text())
        pkg_path = Path(f"packages/{pkg}")

        # Check commands directory
        if "commands" in data:
            commands_paths = data["commands"] if isinstance(data["commands"], list) else [data["commands"]]
            for cmd_path in commands_paths:
                full_path = pkg_path / cmd_path.lstrip("./")
                assert full_path.exists(), f"{pkg}: commands path '{cmd_path}' does not exist"

        # Check agents directory
        if "agents" in data:
            agents_paths = data["agents"] if isinstance(data["agents"], list) else [data["agents"]]
            for agent_path in agents_paths:
                full_path = pkg_path / agent_path.lstrip("./")
                assert full_path.exists(), f"{pkg}: agents path '{agent_path}' does not exist"

        # Check skills directory
        if "skills" in data:
            skills_paths = data["skills"] if isinstance(data["skills"], list) else [data["skills"]]
            for skill_path in skills_paths:
                full_path = pkg_path / skill_path.lstrip("./")
                assert full_path.exists(), f"{pkg}: skills path '{skill_path}' does not exist"


def test_marketplace_metadata_consistency():
    """Verify marketplace and plugin metadata are consistent."""
    marketplace = Path(".claude-plugin/marketplace.json")
    marketplace_data = json.loads(marketplace.read_text())

    for marketplace_plugin in marketplace_data["plugins"]:
        pkg_name = marketplace_plugin["name"]
        plugin_json = Path(f"packages/{pkg_name}/.claude-plugin/plugin.json")
        plugin_data = json.loads(plugin_json.read_text())

        # Check version consistency
        assert (
            marketplace_plugin["version"] == plugin_data["version"]
        ), f"{pkg_name}: version mismatch between marketplace ({marketplace_plugin['version']}) and plugin.json ({plugin_data['version']})"

        # Check name consistency
        assert (
            marketplace_plugin["name"] == plugin_data["name"]
        ), f"{pkg_name}: name mismatch between marketplace and plugin.json"
