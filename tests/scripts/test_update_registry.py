"""Tests for update-registry.py script."""

import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime

import pytest
import yaml

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# Import using importlib to handle hyphens in filename
import importlib.util
spec = importlib.util.spec_from_file_location("update_registry", Path(__file__).parent.parent.parent / "scripts" / "update-registry.py")
update_registry_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_registry_module)

load_manifest = update_registry_module.load_manifest
load_registry = update_registry_module.load_registry
extract_package_info = update_registry_module.extract_package_info
calculate_metadata = update_registry_module.calculate_metadata
find_packages = update_registry_module.find_packages
update_registry = update_registry_module.update_registry


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_manifest():
    """Sample manifest.yaml content."""
    return {
        "name": "sc-test-package",
        "version": "0.7.0",
        "description": "Test package",
        "author": "testuser",
        "license": "MIT",
        "keywords": ["test", "example"],
        "category": "tools",
        "artifacts": {
            "commands": ["cmd1.md", "cmd2.md"],
            "skills": ["skill1/SKILL.md"],
            "agents": ["agent1/AGENT.md", "agent2/AGENT.md"],
            "scripts": ["script1.py"],
        },
    }


@pytest.fixture
def sample_registry():
    """Sample registry.json content."""
    return {
        "name": "synaptic-canvas",
        "version": "0.7.0",
        "description": "A marketplace for Claude Code skills",
        "author": {"name": "randlee"},
        "packages": [],
        "metadata": {
            "totalPackages": 0,
            "totalCommands": 0,
            "totalSkills": 0,
            "totalAgents": 0,
            "totalScripts": 0,
        },
        "generated": datetime.now().isoformat(),
        "lastUpdated": datetime.now().isoformat(),
    }


def test_load_manifest_success(temp_dir, sample_manifest):
    """Test loading a valid manifest file."""
    manifest_path = temp_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest, f)

    result = load_manifest(temp_dir)
    assert result is not None
    assert result["name"] == "sc-test-package"
    assert result["version"] == "0.7.0"


def test_load_manifest_missing(temp_dir):
    """Test loading when manifest doesn't exist."""
    result = load_manifest(temp_dir)
    assert result is None


def test_load_manifest_invalid_yaml(temp_dir):
    """Test loading invalid YAML."""
    manifest_path = temp_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        f.write("invalid: yaml: content: :")

    result = load_manifest(temp_dir)
    assert result is None


def test_load_registry_success(temp_dir, sample_registry):
    """Test loading a valid registry file."""
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = load_registry(registry_path)
    assert result is not None
    assert result["name"] == "synaptic-canvas"


def test_load_registry_missing(temp_dir):
    """Test loading when registry doesn't exist."""
    registry_path = temp_dir / "registry.json"
    result = load_registry(registry_path)
    assert result is None


def test_load_registry_invalid_json(temp_dir):
    """Test loading invalid JSON."""
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        f.write("not valid json {{{")

    result = load_registry(registry_path)
    assert result is None


def test_extract_package_info(sample_manifest, temp_dir):
    """Test extracting package info from manifest."""
    result = extract_package_info(sample_manifest, temp_dir)

    assert result["name"] == "sc-test-package"
    assert result["version"] == "0.7.0"
    assert result["description"] == "Test package"
    assert result["artifacts"]["commands"] == 2
    assert result["artifacts"]["skills"] == 1
    assert result["artifacts"]["agents"] == 2
    assert result["artifacts"]["scripts"] == 1


def test_extract_package_info_empty():
    """Test extracting info from empty manifest."""
    result = extract_package_info({}, Path("."))
    assert result == {}


def test_calculate_metadata():
    """Test calculating metadata from packages."""
    packages = [
        {
            "name": "pkg1",
            "artifacts": {
                "commands": 2,
                "skills": 1,
                "agents": 3,
                "scripts": 1,
            },
        },
        {
            "name": "pkg2",
            "artifacts": {
                "commands": 1,
                "skills": 2,
                "agents": 1,
                "scripts": 0,
            },
        },
    ]

    result = calculate_metadata(packages)
    assert result["totalPackages"] == 2
    assert result["totalCommands"] == 3
    assert result["totalSkills"] == 3
    assert result["totalAgents"] == 4
    assert result["totalScripts"] == 1


def test_calculate_metadata_empty():
    """Test calculating metadata with no packages."""
    result = calculate_metadata([])
    assert result["totalPackages"] == 0
    assert result["totalCommands"] == 0


def test_find_packages(temp_dir):
    """Test finding package directories."""
    # Create package structure
    (temp_dir / "sc-pkg1").mkdir()
    (temp_dir / "sc-pkg2").mkdir()
    (temp_dir / "not-a-package.txt").touch()

    result = find_packages(temp_dir)
    assert len(result) == 2
    assert (temp_dir / "sc-pkg1") in result
    assert (temp_dir / "sc-pkg2") in result


def test_find_packages_empty(temp_dir):
    """Test finding packages in empty directory."""
    result = find_packages(temp_dir)
    assert result == []


def test_find_packages_missing_dir(temp_dir):
    """Test finding packages in non-existent directory."""
    missing = temp_dir / "missing" / "packages"
    result = find_packages(missing)
    assert result == []


def test_update_registry_new_package(temp_dir, sample_manifest, sample_registry):
    """Test updating registry with new package."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    pkg_dir = packages_dir / "sc-test-package"
    pkg_dir.mkdir()
    with open(pkg_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    success = update_registry(packages_dir, registry_path, dry_run=False)
    assert success is True

    with open(registry_path) as f:
        updated = json.load(f)

    assert len(updated["packages"]) == 1
    assert updated["packages"][0]["name"] == "sc-test-package"
    assert updated["metadata"]["totalPackages"] == 1
    assert updated["metadata"]["totalCommands"] == 2


def test_update_registry_existing_package(temp_dir, sample_manifest, sample_registry):
    """Test updating registry with existing package."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    pkg_dir = packages_dir / "sc-test-package"
    pkg_dir.mkdir()
    with open(pkg_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Pre-populate registry
    sample_registry["packages"] = [
        {
            "name": "sc-test-package",
            "version": "0.6.0",  # Old version
            "artifacts": {"commands": 1},
        }
    ]

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    success = update_registry(packages_dir, registry_path, dry_run=False)
    assert success is True

    with open(registry_path) as f:
        updated = json.load(f)

    # Should be updated to new version
    assert updated["packages"][0]["version"] == "0.7.0"


def test_update_registry_dry_run(temp_dir, sample_manifest, sample_registry):
    """Test dry-run mode doesn't write changes."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    pkg_dir = packages_dir / "sc-test-package"
    pkg_dir.mkdir()
    with open(pkg_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    original_content = sample_registry.copy()

    success = update_registry(packages_dir, registry_path, dry_run=True)
    assert success is True

    with open(registry_path) as f:
        after = json.load(f)

    # Registry should not be modified in dry-run
    assert after["packages"] == original_content["packages"]


def test_update_registry_missing_manifest(temp_dir, sample_registry):
    """Test updating with package that has no manifest."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    # Create package dir but no manifest
    (packages_dir / "sc-no-manifest").mkdir()

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    success = update_registry(packages_dir, registry_path, dry_run=False)
    # Should still succeed (with warning), just skip the package
    assert success is True

    with open(registry_path) as f:
        updated = json.load(f)

    # Registry should remain unchanged
    assert len(updated["packages"]) == 0


def test_update_registry_specific_package(temp_dir, sample_manifest, sample_registry):
    """Test updating specific package only."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    # Create two packages
    for i in range(1, 3):
        pkg_dir = packages_dir / f"sc-test-package-{i}"
        pkg_dir.mkdir()
        manifest = sample_manifest.copy()
        manifest["name"] = f"sc-test-package-{i}"
        with open(pkg_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    # Update only package 1
    success = update_registry(
        packages_dir, registry_path, package_name="sc-test-package-1", dry_run=False
    )
    assert success is True

    with open(registry_path) as f:
        updated = json.load(f)

    assert len(updated["packages"]) == 1
    assert updated["packages"][0]["name"] == "sc-test-package-1"


def test_update_registry_nonexistent_package(temp_dir, sample_registry):
    """Test updating non-existent specific package."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    success = update_registry(
        packages_dir,
        registry_path,
        package_name="sc-nonexistent",
        dry_run=False,
    )
    assert success is False
