"""Tests for validate-marketplace-sync.py script."""

import json
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
    "validate_marketplace_sync",
    Path(__file__).parent.parent.parent / "scripts" / "validate-marketplace-sync.py",
)
sync_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_module)

from result import Failure, Success

load_json = sync_module.load_json
load_manifest = sync_module.load_manifest
get_package_dirs = sync_module.get_package_dirs
find_in_list = sync_module.find_in_list
validate_marketplace_sync = sync_module.validate_marketplace_sync
fix_sync_issues = sync_module.fix_sync_issues
SyncValidationResult = sync_module.SyncValidationResult


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
        "artifacts": {"commands": ["commands/test.md"]},
    }


@pytest.fixture
def sample_marketplace():
    """Sample marketplace.json content."""
    return {
        "name": "test-marketplace",
        "plugins": [
            {
                "name": "test-package",
                "source": "./packages/test-package",
                "description": "Test package",
                "version": "1.0.0",
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
                "version": "1.0.0",
                "description": "Test package",
            }
        }
    }


@pytest.fixture
def complete_setup(temp_dir, sample_manifest, sample_marketplace, sample_registry):
    """Create complete synchronized setup."""
    # Create packages directory
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    # Create package
    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace.json
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry.json
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    return {
        "packages_dir": packages_dir,
        "marketplace_path": marketplace_path,
        "registry_path": registry_path,
        "package_dir": package_dir,
    }


# ============================================================================
# SyncValidationResult Tests
# ============================================================================


def test_sync_validation_result_is_valid_when_clean():
    """Test is_valid returns True when synchronized."""
    result = SyncValidationResult()
    assert result.is_valid() is True


def test_sync_validation_result_is_valid_false_with_missing_marketplace():
    """Test is_valid returns False with missing marketplace entries."""
    result = SyncValidationResult(missing_in_marketplace=["pkg1"])
    assert result.is_valid() is False


def test_sync_validation_result_is_valid_false_with_missing_registry():
    """Test is_valid returns False with missing registry entries."""
    result = SyncValidationResult(missing_in_registry=["pkg1"])
    assert result.is_valid() is False


def test_sync_validation_result_is_valid_false_with_version_mismatches():
    """Test is_valid returns False with version mismatches."""
    result = SyncValidationResult(
        version_mismatches=[
            {"package": "pkg1", "manifest": "1.0.0", "marketplace": "0.9.0"}
        ]
    )
    assert result.is_valid() is False


def test_sync_validation_result_get_summary_synchronized():
    """Test get_summary for synchronized state."""
    result = SyncValidationResult(total_packages=5, packages_validated=5)
    summary = result.get_summary()
    assert "SYNCHRONIZED" in summary
    assert "5" in summary


def test_sync_validation_result_get_summary_out_of_sync():
    """Test get_summary for out of sync state."""
    result = SyncValidationResult(
        missing_in_marketplace=["pkg1"],
        version_mismatches=[
            {"package": "pkg2", "manifest": "2.0.0", "marketplace": "1.0.0"}
        ],
        total_packages=2,
        packages_validated=2,
    )
    summary = result.get_summary()
    assert "OUT OF SYNC" in summary
    assert "pkg1" in summary
    assert "pkg2" in summary


# ============================================================================
# load_json Tests
# ============================================================================


def test_load_json_success(temp_dir):
    """Test loading valid JSON file."""
    json_file = temp_dir / "test.json"
    data = {"key": "value"}

    with open(json_file, "w") as f:
        json.dump(data, f)

    result = load_json(json_file)
    assert isinstance(result, Success)
    assert result.value == data


def test_load_json_missing_file(temp_dir):
    """Test loading non-existent file."""
    json_file = temp_dir / "missing.json"
    result = load_json(json_file)
    assert isinstance(result, Failure)
    assert "not found" in result.error.message


def test_load_json_invalid_json(temp_dir):
    """Test loading invalid JSON."""
    json_file = temp_dir / "invalid.json"

    with open(json_file, "w") as f:
        f.write("not valid json {{{")

    result = load_json(json_file)
    assert isinstance(result, Failure)
    assert "Invalid JSON" in result.error.message


# ============================================================================
# load_manifest Tests
# ============================================================================


def test_load_manifest_success(temp_dir, sample_manifest):
    """Test loading valid manifest."""
    package_dir = temp_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    result = load_manifest(package_dir)
    assert isinstance(result, Success)
    assert result.value["name"] == "test-package"
    assert result.value["version"] == "1.0.0"


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


# ============================================================================
# get_package_dirs Tests
# ============================================================================


def test_get_package_dirs_multiple_packages(temp_dir):
    """Test getting multiple package directories."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    (packages_dir / "pkg1").mkdir()
    (packages_dir / "pkg2").mkdir()
    (packages_dir / "pkg3").mkdir()

    dirs = get_package_dirs(packages_dir)
    assert len(dirs) == 3
    assert any(d.name == "pkg1" for d in dirs)
    assert any(d.name == "pkg2" for d in dirs)
    assert any(d.name == "pkg3" for d in dirs)


def test_get_package_dirs_ignores_hidden(temp_dir):
    """Test that hidden directories are ignored."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    (packages_dir / "pkg1").mkdir()
    (packages_dir / ".hidden").mkdir()

    dirs = get_package_dirs(packages_dir)
    assert len(dirs) == 1
    assert dirs[0].name == "pkg1"


def test_get_package_dirs_ignores_files(temp_dir):
    """Test that files are ignored."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    (packages_dir / "pkg1").mkdir()
    (packages_dir / "file.txt").write_text("not a directory")

    dirs = get_package_dirs(packages_dir)
    assert len(dirs) == 1
    assert dirs[0].name == "pkg1"


def test_get_package_dirs_nonexistent_dir(temp_dir):
    """Test with non-existent packages directory."""
    packages_dir = temp_dir / "nonexistent"
    dirs = get_package_dirs(packages_dir)
    assert len(dirs) == 0


# ============================================================================
# find_in_list Tests
# ============================================================================


def test_find_in_list_found():
    """Test finding item in list."""
    items = [
        {"name": "pkg1", "version": "1.0.0"},
        {"name": "pkg2", "version": "2.0.0"},
    ]

    result = find_in_list(items, "pkg1")
    assert result is not None
    assert result["name"] == "pkg1"


def test_find_in_list_not_found():
    """Test when item not in list."""
    items = [{"name": "pkg1", "version": "1.0.0"}]

    result = find_in_list(items, "pkg-missing")
    assert result is None


def test_find_in_list_empty_list():
    """Test searching empty list."""
    result = find_in_list([], "pkg1")
    assert result is None


# ============================================================================
# validate_marketplace_sync Tests
# ============================================================================


def test_validate_marketplace_sync_all_synchronized(complete_setup):
    """Test validation when everything is synchronized."""
    result = validate_marketplace_sync(
        packages_dir=complete_setup["packages_dir"],
        marketplace_path=complete_setup["marketplace_path"],
        registry_path=complete_setup["registry_path"],
        verbose=False,
    )

    assert isinstance(result, Success)
    assert result.value.is_valid()
    assert result.value.total_packages == 1
    assert result.value.packages_validated == 1


def test_validate_marketplace_sync_missing_in_marketplace(
    temp_dir, sample_manifest, sample_registry
):
    """Test validation with package missing in marketplace."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create empty marketplace
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump({"name": "test", "plugins": []}, f)

    # Create registry
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert "test-package" in result.value.missing_in_marketplace


def test_validate_marketplace_sync_missing_in_registry(
    temp_dir, sample_manifest, sample_marketplace
):
    """Test validation with package missing in registry."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create empty registry
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump({"packages": {}}, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert "test-package" in result.value.missing_in_registry


def test_validate_marketplace_sync_version_mismatch_marketplace(
    temp_dir, sample_manifest, sample_marketplace, sample_registry
):
    """Test validation with version mismatch in marketplace."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace with wrong version
    sample_marketplace["plugins"][0]["version"] = "0.9.0"
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert len(result.value.version_mismatches) == 1
    assert result.value.version_mismatches[0]["package"] == "test-package"
    assert result.value.version_mismatches[0]["manifest"] == "1.0.0"
    assert result.value.version_mismatches[0]["marketplace"] == "0.9.0"


def test_validate_marketplace_sync_version_mismatch_registry(
    temp_dir, sample_manifest, sample_marketplace, sample_registry
):
    """Test validation with version mismatch in registry."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry with wrong version
    sample_registry["packages"]["test-package"]["version"] = "0.8.0"
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert len(result.value.version_mismatches) == 1
    assert result.value.version_mismatches[0]["package"] == "test-package"
    assert result.value.version_mismatches[0]["registry"] == "0.8.0"


def test_validate_marketplace_sync_version_mismatch_both(
    temp_dir, sample_manifest, sample_marketplace, sample_registry
):
    """Test validation with version mismatch in both marketplace and registry."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace with wrong version
    sample_marketplace["plugins"][0]["version"] = "0.9.0"
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry with wrong version
    sample_registry["packages"]["test-package"]["version"] = "0.8.0"
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert not result.value.is_valid()
    assert len(result.value.version_mismatches) == 1
    mismatch = result.value.version_mismatches[0]
    assert mismatch["package"] == "test-package"
    assert mismatch["manifest"] == "1.0.0"
    assert mismatch["marketplace"] == "0.9.0"
    assert mismatch["registry"] == "0.8.0"


def test_validate_marketplace_sync_missing_marketplace_file(temp_dir):
    """Test validation when marketplace.json is missing."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    marketplace_path = temp_dir / "marketplace.json"
    registry_path = temp_dir / "registry.json"

    with open(registry_path, "w") as f:
        json.dump({"packages": {}}, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Failure)
    assert "not found" in result.error.message


def test_validate_marketplace_sync_missing_registry_file(temp_dir):
    """Test validation when registry.json is missing."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    marketplace_path = temp_dir / "marketplace.json"
    registry_path = temp_dir / "registry.json"

    with open(marketplace_path, "w") as f:
        json.dump({"name": "test", "plugins": []}, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Failure)
    assert "not found" in result.error.message


def test_validate_marketplace_sync_verbose_mode(complete_setup, capsys):
    """Test validation with verbose mode enabled."""
    result = validate_marketplace_sync(
        packages_dir=complete_setup["packages_dir"],
        marketplace_path=complete_setup["marketplace_path"],
        registry_path=complete_setup["registry_path"],
        verbose=True,
    )

    assert isinstance(result, Success)
    captured = capsys.readouterr()
    assert "test-package" in captured.out


def test_validate_marketplace_sync_multiple_packages(temp_dir):
    """Test validation with multiple packages."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    # Create two packages
    for i in range(1, 3):
        pkg_dir = packages_dir / f"pkg{i}"
        pkg_dir.mkdir()

        manifest = {
            "name": f"pkg{i}",
            "version": f"{i}.0.0",
            "description": f"Package {i}",
            "author": "test",
            "license": "MIT",
            "artifacts": {},
        }

        with open(pkg_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

    # Create marketplace
    marketplace = {
        "name": "test",
        "plugins": [
            {
                "name": "pkg1",
                "source": "./packages/pkg1",
                "description": "Package 1",
                "version": "1.0.0",
                "author": {"name": "test"},
                "license": "MIT",
                "keywords": [],
                "category": "tools",
            },
            {
                "name": "pkg2",
                "source": "./packages/pkg2",
                "description": "Package 2",
                "version": "2.0.0",
                "author": {"name": "test"},
                "license": "MIT",
                "keywords": [],
                "category": "tools",
            },
        ],
    }

    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(marketplace, f)

    # Create registry
    registry = {
        "packages": {
            "pkg1": {"name": "pkg1", "version": "1.0.0"},
            "pkg2": {"name": "pkg2", "version": "2.0.0"},
        }
    }

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(registry, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert result.value.is_valid()
    assert result.value.total_packages == 2
    assert result.value.packages_validated == 2


# ============================================================================
# fix_sync_issues Tests
# ============================================================================


def test_fix_sync_issues_no_fixes_needed(complete_setup):
    """Test fix when already synchronized."""
    result = fix_sync_issues(
        packages_dir=complete_setup["packages_dir"],
        marketplace_path=complete_setup["marketplace_path"],
        registry_path=complete_setup["registry_path"],
        verbose=False,
    )

    assert isinstance(result, Success)
    assert result.value is False  # No changes made


def test_fix_sync_issues_fixes_marketplace_version(
    temp_dir, sample_manifest, sample_marketplace, sample_registry
):
    """Test fixing version mismatch in marketplace."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace with wrong version
    sample_marketplace["plugins"][0]["version"] = "0.9.0"
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = fix_sync_issues(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert result.value is True  # Changes made

    # Verify fix
    with open(marketplace_path) as f:
        updated = json.load(f)

    assert updated["plugins"][0]["version"] == "1.0.0"


def test_fix_sync_issues_fixes_registry_version(
    temp_dir, sample_manifest, sample_marketplace, sample_registry
):
    """Test fixing version mismatch in registry."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry with wrong version
    sample_registry["packages"]["test-package"]["version"] = "0.8.0"
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = fix_sync_issues(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert result.value is True  # Changes made

    # Verify fix
    with open(registry_path) as f:
        updated = json.load(f)

    assert updated["packages"]["test-package"]["version"] == "1.0.0"


def test_fix_sync_issues_verbose_mode(
    temp_dir, sample_manifest, sample_marketplace, sample_registry, capsys
):
    """Test fix with verbose mode enabled."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace with wrong version
    sample_marketplace["plugins"][0]["version"] = "0.9.0"
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = fix_sync_issues(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=True,
    )

    assert isinstance(result, Success)
    captured = capsys.readouterr()
    assert "Updated" in captured.out or "updated" in captured.out


# ============================================================================
# CLI/main() Tests
# ============================================================================


def test_main_validate_synchronized(complete_setup, monkeypatch):
    """Test CLI validation mode with synchronized setup."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate-marketplace-sync.py",
            "--packages-dir",
            str(complete_setup["packages_dir"]),
            "--marketplace",
            str(complete_setup["marketplace_path"]),
            "--registry",
            str(complete_setup["registry_path"]),
        ],
    )

    main = sync_module.main
    exit_code = main()
    assert exit_code == 0


def test_main_validate_out_of_sync(
    temp_dir, sample_manifest, sample_marketplace, sample_registry, monkeypatch
):
    """Test CLI validation mode with out of sync data."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace with wrong version
    sample_marketplace["plugins"][0]["version"] = "0.9.0"
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate-marketplace-sync.py",
            "--packages-dir",
            str(packages_dir),
            "--marketplace",
            str(marketplace_path),
            "--registry",
            str(registry_path),
        ],
    )

    main = sync_module.main
    exit_code = main()
    assert exit_code == 1


def test_main_fix_mode(
    temp_dir, sample_manifest, sample_marketplace, sample_registry, monkeypatch
):
    """Test CLI fix mode."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace with wrong version
    sample_marketplace["plugins"][0]["version"] = "0.9.0"
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate-marketplace-sync.py",
            "--packages-dir",
            str(packages_dir),
            "--marketplace",
            str(marketplace_path),
            "--registry",
            str(registry_path),
            "--fix",
        ],
    )

    main = sync_module.main
    exit_code = main()
    assert exit_code == 0

    # Verify fix was applied
    with open(marketplace_path) as f:
        updated = json.load(f)
    assert updated["plugins"][0]["version"] == "1.0.0"


def test_main_verbose_mode(complete_setup, monkeypatch, capsys):
    """Test CLI with verbose mode."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate-marketplace-sync.py",
            "--packages-dir",
            str(complete_setup["packages_dir"]),
            "--marketplace",
            str(complete_setup["marketplace_path"]),
            "--registry",
            str(complete_setup["registry_path"]),
            "--verbose",
        ],
    )

    main = sync_module.main
    exit_code = main()
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "test-package" in captured.out


def test_main_fix_with_verbose(
    temp_dir, sample_manifest, sample_marketplace, sample_registry, monkeypatch, capsys
):
    """Test CLI fix mode with verbose output."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create marketplace with wrong version
    sample_marketplace["plugins"][0]["version"] = "0.9.0"
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(sample_marketplace, f)

    # Create registry
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate-marketplace-sync.py",
            "--packages-dir",
            str(packages_dir),
            "--marketplace",
            str(marketplace_path),
            "--registry",
            str(registry_path),
            "--fix",
            "--verbose",
        ],
    )

    main = sync_module.main
    exit_code = main()
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "Updated" in captured.out or "synchronized" in captured.out.lower()


def test_main_error_handling(temp_dir, monkeypatch):
    """Test CLI error handling with missing files."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    marketplace_path = temp_dir / "marketplace.json"
    registry_path = temp_dir / "registry.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate-marketplace-sync.py",
            "--packages-dir",
            str(packages_dir),
            "--marketplace",
            str(marketplace_path),
            "--registry",
            str(registry_path),
        ],
    )

    main = sync_module.main
    exit_code = main()
    assert exit_code == 1


# ============================================================================
# Additional Coverage Tests
# ============================================================================


def test_sync_result_with_missing_in_registry_summary():
    """Test summary with missing in registry."""
    result = SyncValidationResult(
        missing_in_registry=["pkg1", "pkg2"],
        total_packages=2,
        packages_validated=2,
    )
    summary = result.get_summary()
    assert "Missing in registry.json" in summary
    assert "pkg1" in summary
    assert "pkg2" in summary


def test_validate_with_package_missing_version(temp_dir):
    """Test validation with package missing version in manifest."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    # Create manifest without version
    manifest = {
        "name": "test-package",
        "description": "Test",
        "author": "test",
        "license": "MIT",
        "artifacts": {},
    }

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)

    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump({"name": "test", "plugins": []}, f)

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump({"packages": {}}, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert len(result.warnings) > 0


def test_validate_with_orphaned_plugins(temp_dir, sample_manifest):
    """Test validation with plugin in marketplace but not in packages/."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    # Create marketplace with plugin that doesn't exist
    marketplace = {
        "name": "test",
        "plugins": [
            {
                "name": "orphan-package",
                "source": "./packages/orphan-package",
                "description": "Orphan",
                "version": "1.0.0",
                "author": {"name": "test"},
                "license": "MIT",
                "keywords": [],
                "category": "tools",
            }
        ],
    }

    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump(marketplace, f)

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump({"packages": {}}, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert len(result.warnings) > 0
    assert any("orphan-package" in w for w in result.warnings)


def test_validate_with_orphaned_registry_packages(temp_dir, sample_manifest):
    """Test validation with package in registry but not in packages/."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump({"name": "test", "plugins": []}, f)

    # Create registry with package that doesn't exist
    registry = {
        "packages": {
            "orphan-package": {"name": "orphan-package", "version": "1.0.0"}
        }
    }

    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(registry, f)

    result = validate_marketplace_sync(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    assert isinstance(result, Success)
    assert len(result.warnings) > 0
    assert any("orphan-package" in w for w in result.warnings)


def test_fix_with_no_matching_package_in_plugins(
    temp_dir, sample_manifest, sample_registry
):
    """Test fix when mismatch exists but package not found in plugins."""
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    package_dir = packages_dir / "test-package"
    package_dir.mkdir()

    with open(package_dir / "manifest.yaml", "w") as f:
        yaml.dump(sample_manifest, f)

    # Create empty marketplace
    marketplace_path = temp_dir / "marketplace.json"
    with open(marketplace_path, "w") as f:
        json.dump({"name": "test", "plugins": []}, f)

    # Create registry with correct version
    registry_path = temp_dir / "registry.json"
    with open(registry_path, "w") as f:
        json.dump(sample_registry, f)

    result = fix_sync_issues(
        packages_dir=packages_dir,
        marketplace_path=marketplace_path,
        registry_path=registry_path,
        verbose=False,
    )

    # Should not fail, just report no changes
    assert isinstance(result, Success)
