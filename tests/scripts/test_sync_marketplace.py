"""Tests for sync-marketplace-json.py script."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# Import using importlib to handle hyphens in filename
import importlib.util
spec = importlib.util.spec_from_file_location("sync_marketplace_json", Path(__file__).parent.parent.parent / "scripts" / "sync-marketplace-json.py")
sync_marketplace_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_marketplace_module)

load_json = sync_marketplace_module.load_json
find_package = sync_marketplace_module.find_package
sync_marketplace = sync_marketplace_module.sync_marketplace


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_registry():
    """Sample registry.json content."""
    return {
        "name": "synaptic-canvas",
        "packages": [
            {
                "name": "sc-pkg1",
                "source": "./packages/sc-pkg1",
                "description": "First package",
                "version": "0.7.0",
                "author": {"name": "randlee"},
                "license": "MIT",
                "keywords": ["pkg1"],
                "category": "tools",
            },
            {
                "name": "sc-pkg2",
                "source": "./packages/sc-pkg2",
                "description": "Second package",
                "version": "0.7.0",
                "author": {"name": "randlee"},
                "license": "MIT",
                "keywords": ["pkg2"],
                "category": "automation",
            },
        ],
    }


@pytest.fixture
def sample_marketplace():
    """Sample marketplace.json content."""
    return {
        "name": "synaptic-canvas",
        "owner": {"name": "randlee"},
        "metadata": {"version": "0.7.0"},
        "plugins": [
            {
                "name": "sc-pkg1",
                "source": "./packages/sc-pkg1",
                "description": "First package",
                "version": "0.6.0",  # Old version
                "author": {"name": "randlee"},
                "license": "MIT",
                "keywords": ["pkg1"],
                "category": "tools",
            },
        ],
    }


def test_load_json_success(temp_dir):
    """Test loading a valid JSON file."""
    json_file = temp_dir / "test.json"
    data = {"key": "value"}
    with open(json_file, "w") as f:
        json.dump(data, f)

    result = load_json(json_file)
    assert result == data


def test_load_json_missing(temp_dir):
    """Test loading non-existent file."""
    json_file = temp_dir / "missing.json"
    result = load_json(json_file)
    assert result is None


def test_load_json_invalid(temp_dir):
    """Test loading invalid JSON."""
    json_file = temp_dir / "invalid.json"
    with open(json_file, "w") as f:
        f.write("not valid json {{{")

    result = load_json(json_file)
    assert result is None


def test_find_package_found():
    """Test finding package in list."""
    packages = [
        {"name": "pkg1", "version": "1.0.0"},
        {"name": "pkg2", "version": "2.0.0"},
    ]

    result = find_package(packages, "pkg1")
    assert result is not None
    assert result["name"] == "pkg1"


def test_find_package_not_found():
    """Test when package not in list."""
    packages = [{"name": "pkg1", "version": "1.0.0"}]

    result = find_package(packages, "pkg-missing")
    assert result is None


def test_find_package_empty_list():
    """Test searching empty list."""
    result = find_package([], "pkg1")
    assert result is None


def test_sync_marketplace_update_version(temp_dir, sample_registry, sample_marketplace):
    """Test updating version in marketplace."""
    registry_path = temp_dir / "registry.json"
    marketplace_path = temp_dir / "marketplace.json"

    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    success = sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert success is True

    with open(marketplace_path) as f:
        result = json.load(f)

    # Check version was updated
    pkg1 = find_package(result["plugins"], "sc-pkg1")
    assert pkg1["version"] == "0.7.0"


def test_sync_marketplace_add_missing_package(temp_dir, sample_registry, sample_marketplace):
    """Test adding missing package from registry."""
    registry_path = temp_dir / "registry.json"
    marketplace_path = temp_dir / "marketplace.json"

    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    success = sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert success is True

    with open(marketplace_path) as f:
        result = json.load(f)

    # Check sc-pkg2 was added
    pkg2 = find_package(result["plugins"], "sc-pkg2")
    assert pkg2 is not None
    assert pkg2["version"] == "0.7.0"
    assert len(result["plugins"]) == 2


def test_sync_marketplace_dry_run(temp_dir, sample_registry, sample_marketplace):
    """Test dry-run doesn't modify marketplace."""
    registry_path = temp_dir / "registry.json"
    marketplace_path = temp_dir / "marketplace.json"

    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Run dry-run
    success = sync_marketplace(registry_path, marketplace_path, dry_run=True)
    assert success is True

    # Read file - should be unchanged
    with open(marketplace_path) as f:
        result = json.load(f)

    pkg1 = find_package(result["plugins"], "sc-pkg1")
    assert pkg1["version"] == "0.6.0"  # Should not be updated


def test_sync_marketplace_no_changes_needed(temp_dir):
    """Test when marketplace is already in sync."""
    registry = {
        "name": "synaptic-canvas",
        "packages": [
            {
                "name": "sc-pkg1",
                "source": "./packages/sc-pkg1",
                "description": "Package 1",
                "version": "0.7.0",
                "author": {"name": "randlee"},
                "license": "MIT",
                "keywords": ["pkg1"],
                "category": "tools",
            },
        ],
    }

    marketplace = {
        "name": "synaptic-canvas",
        "plugins": [
            {
                "name": "sc-pkg1",
                "source": "./packages/sc-pkg1",
                "description": "Package 1",
                "version": "0.7.0",
                "author": {"name": "randlee"},
                "license": "MIT",
                "keywords": ["pkg1"],
                "category": "tools",
            },
        ],
    }

    registry_path = temp_dir / "registry.json"
    marketplace_path = temp_dir / "marketplace.json"

    with open(registry_path, "w") as f:
        json.dump(registry, f)
    with open(marketplace_path, "w") as f:
        json.dump(marketplace, f)

    success = sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert success is True


def test_sync_marketplace_update_description(temp_dir, sample_registry, sample_marketplace):
    """Test updating description in marketplace."""
    sample_marketplace["plugins"][0]["description"] = "Old description"
    sample_registry["packages"][0]["description"] = "New description"

    registry_path = temp_dir / "registry.json"
    marketplace_path = temp_dir / "marketplace.json"

    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    success = sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert success is True

    with open(marketplace_path) as f:
        result = json.load(f)

    pkg1 = find_package(result["plugins"], "sc-pkg1")
    assert pkg1["description"] == "New description"


def test_sync_marketplace_missing_registry(temp_dir, sample_marketplace):
    """Test when registry file is missing."""
    registry_path = temp_dir / "registry.json"
    marketplace_path = temp_dir / "marketplace.json"

    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    success = sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert success is False


def test_sync_marketplace_missing_marketplace(temp_dir, sample_registry):
    """Test when marketplace file is missing."""
    registry_path = temp_dir / "registry.json"
    marketplace_path = temp_dir / "marketplace.json"

    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    success = sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert success is False


def test_sync_marketplace_empty_registry(temp_dir):
    """Test with empty registry."""
    registry = {"name": "synaptic-canvas", "packages": []}
    marketplace = {
        "name": "synaptic-canvas",
        "plugins": [
            {
                "name": "sc-old-pkg",
                "source": "./packages/sc-old-pkg",
                "description": "Old package",
                "version": "1.0.0",
                "author": {"name": "randlee"},
                "license": "MIT",
                "keywords": [],
                "category": "tools",
            },
        ],
    }

    registry_path = temp_dir / "registry.json"
    marketplace_path = temp_dir / "marketplace.json"

    with open(registry_path, "w") as f:
        json.dump(registry, f)
    with open(marketplace_path, "w") as f:
        json.dump(marketplace, f)

    # Should still succeed but warn about orphaned package
    success = sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert success is True
