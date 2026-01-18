"""
Unit tests for harness.fixture_loader module.

Tests the fixture loading functionality including:
- YAML parsing for fixture.yaml and test_*.yaml
- Fixture and test discovery
- Configuration merging
- Error handling
- Fixture validation (fail-fast guardrails)

Run with:
    pytest test-packages/harness/tests/test_fixture_loader.py -v
"""

import json
import tempfile
from pathlib import Path

import pytest

from harness.fixture_loader import (
    ExecutionConfig,
    ExpectationConfig,
    FileMapping,
    FixtureConfig,
    FixtureLoader,
    FixtureValidationError,
    SetupConfig,
    TeardownConfig,
    TestConfig,
    discover_fixtures,
    load_fixture,
    load_test,
)


# =============================================================================
# FileMapping Tests
# =============================================================================


class TestFileMapping:
    """Tests for FileMapping dataclass."""

    def test_from_dict(self):
        """Test creating FileMapping from dictionary."""
        data = {"src": "data/config.yaml", "dest": ".claude/config.yaml"}
        mapping = FileMapping.from_dict(data)

        assert mapping.src == "data/config.yaml"
        assert mapping.dest == ".claude/config.yaml"

    def test_from_dict_empty(self):
        """Test creating FileMapping from empty dictionary."""
        mapping = FileMapping.from_dict({})

        assert mapping.src == ""
        assert mapping.dest == ""


# =============================================================================
# SetupConfig Tests
# =============================================================================


class TestSetupConfig:
    """Tests for SetupConfig dataclass."""

    def test_from_dict_full(self):
        """Test creating SetupConfig from full dictionary."""
        data = {
            "plugins": ["plugin-a", "plugin-b"],
            "files": [
                {"src": "a.yaml", "dest": "b.yaml"},
                {"src": "c.yaml", "dest": "d.yaml"},
            ],
            "commands": ["echo hello", "ls -la"],
        }
        setup = SetupConfig.from_dict(data)

        assert setup.plugins == ["plugin-a", "plugin-b"]
        assert len(setup.files) == 2
        assert setup.files[0].src == "a.yaml"
        assert setup.commands == ["echo hello", "ls -la"]

    def test_from_dict_none(self):
        """Test creating SetupConfig from None."""
        setup = SetupConfig.from_dict(None)

        assert setup.plugins == []
        assert setup.files == []
        assert setup.commands == []

    def test_from_dict_empty(self):
        """Test creating SetupConfig from empty dictionary."""
        setup = SetupConfig.from_dict({})

        assert setup.plugins == []
        assert setup.files == []
        assert setup.commands == []

    def test_merge(self):
        """Test merging two SetupConfig instances."""
        setup1 = SetupConfig(
            plugins=["plugin-a"],
            files=[FileMapping("a.yaml", "b.yaml")],
            commands=["echo 1"],
        )
        setup2 = SetupConfig(
            plugins=["plugin-b"],
            files=[FileMapping("c.yaml", "d.yaml")],
            commands=["echo 2"],
        )

        merged = setup1.merge(setup2)

        assert merged.plugins == ["plugin-a", "plugin-b"]
        assert len(merged.files) == 2
        assert merged.commands == ["echo 1", "echo 2"]


# =============================================================================
# TeardownConfig Tests
# =============================================================================


class TestTeardownConfig:
    """Tests for TeardownConfig dataclass."""

    def test_from_dict(self):
        """Test creating TeardownConfig from dictionary."""
        data = {"commands": ["git checkout -- .", "rm -f trace.jsonl"]}
        teardown = TeardownConfig.from_dict(data)

        assert teardown.commands == ["git checkout -- .", "rm -f trace.jsonl"]

    def test_from_dict_none(self):
        """Test creating TeardownConfig from None."""
        teardown = TeardownConfig.from_dict(None)

        assert teardown.commands == []


# =============================================================================
# ExpectationConfig Tests
# =============================================================================


class TestExpectationConfig:
    """Tests for ExpectationConfig dataclass."""

    def test_from_dict_full(self):
        """Test creating ExpectationConfig from full dictionary."""
        data = {
            "id": "exp-001",
            "description": "Should call Bash",
            "type": "tool_call",
            "expected": {"tool": "Bash", "pattern": "ls.*"},
        }
        exp = ExpectationConfig.from_dict(data)

        assert exp.id == "exp-001"
        assert exp.description == "Should call Bash"
        assert exp.type == "tool_call"
        assert exp.expected == {"tool": "Bash", "pattern": "ls.*"}

    def test_from_dict_minimal(self):
        """Test creating ExpectationConfig with defaults."""
        data = {"expected": {"pattern": "test"}}
        exp = ExpectationConfig.from_dict(data, index=2)

        assert exp.id == "exp-003"  # index + 1, formatted
        assert exp.description == ""
        assert exp.type == "tool_call"


# =============================================================================
# ExecutionConfig Tests
# =============================================================================


class TestExecutionConfig:
    """Tests for ExecutionConfig dataclass."""

    def test_from_dict_full(self):
        """Test creating ExecutionConfig from full dictionary."""
        data = {
            "prompt": "/sc-startup --readonly",
            "model": "sonnet",
            "tools": ["Bash", "Read"],
            "timeout_ms": 45000,
        }
        exec_config = ExecutionConfig.from_dict(data)

        assert exec_config.prompt == "/sc-startup --readonly"
        assert exec_config.model == "sonnet"
        assert exec_config.tools == ["Bash", "Read"]
        assert exec_config.timeout_ms == 45000

    def test_from_dict_defaults(self):
        """Test ExecutionConfig with default values."""
        exec_config = ExecutionConfig.from_dict(None)

        assert exec_config.prompt == ""
        assert exec_config.model == "haiku"
        assert exec_config.tools == []
        assert exec_config.timeout_ms == 60000


# =============================================================================
# TestConfig Tests
# =============================================================================


class TestTestConfig:
    """Tests for TestConfig dataclass."""

    def test_from_yaml_full(self):
        """Test loading full test configuration from YAML."""
        yaml_content = """
test_id: test-001
test_name: Full Test
description: A complete test configuration
tags:
  - integration
  - readonly

execution:
  prompt: "/command --flag"
  model: haiku
  tools:
    - Bash
  timeout_ms: 30000

setup:
  commands:
    - echo "setup"

expectations:
  - id: exp-001
    description: Should work
    type: tool_call
    expected:
      tool: Bash
      pattern: ".*"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = TestConfig.from_yaml(Path(f.name))

                assert config.test_id == "test-001"
                assert config.test_name == "Full Test"
                assert config.description == "A complete test configuration"
                assert config.tags == ["integration", "readonly"]
                assert config.execution.prompt == "/command --flag"
                assert config.execution.model == "haiku"
                assert config.execution.tools == ["Bash"]
                assert len(config.expectations) == 1
                assert config.expectations[0].id == "exp-001"
            finally:
                Path(f.name).unlink()

    def test_from_yaml_minimal(self, tmp_path: Path):
        """Test loading minimal test configuration from YAML."""
        test_file = tmp_path / "test_minimal.yaml"
        yaml_content = """
test_id: minimal-test
execution:
  prompt: "test prompt"
"""
        test_file.write_text(yaml_content)

        config = TestConfig.from_yaml(test_file)

        assert config.test_id == "minimal-test"
        # test_name defaults to filename stem converted to title case
        assert config.test_name == "Test Minimal"
        assert config.execution.prompt == "test prompt"
        assert config.execution.model == "haiku"  # Default

    def test_convenience_properties(self):
        """Test convenience property accessors."""
        config = TestConfig(
            test_id="test",
            test_name="Test",
            execution=ExecutionConfig(
                prompt="prompt",
                model="sonnet",
                tools=["Bash"],
                timeout_ms=10000,
            ),
        )

        assert config.prompt == "prompt"
        assert config.model == "sonnet"
        assert config.tools == ["Bash"]
        assert config.timeout_ms == 10000

    def test_skip_configuration(self):
        """Test skip configuration loading."""
        yaml_content = """
test_id: skipped-test
skip: true
skip_reason: Not implemented yet
execution:
  prompt: "test"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = TestConfig.from_yaml(Path(f.name))

                assert config.skip is True
                assert config.skip_reason == "Not implemented yet"
            finally:
                Path(f.name).unlink()


# =============================================================================
# FixtureConfig Tests
# =============================================================================


class TestFixtureConfig:
    """Tests for FixtureConfig dataclass."""

    def test_from_yaml_full(self, tmp_path: Path):
        """Test loading full fixture configuration from YAML."""
        # Create fixture structure
        fixture_dir = tmp_path / "test-fixture"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        # Write fixture.yaml
        fixture_yaml = """
name: test-fixture
description: Test fixture description
package: test-package@test

setup:
  plugins:
    - plugin-a
  files:
    - src: data/config.yaml
      dest: .claude/config.yaml
  commands:
    - echo "setup"

teardown:
  commands:
    - echo "cleanup"

tests_dir: tests
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        # Write test file
        test_yaml = """
test_id: test-001
test_name: Test One
execution:
  prompt: "test"
"""
        (tests_dir / "test_one.yaml").write_text(test_yaml)

        # Load fixture
        config = FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        assert config.name == "test-fixture"
        assert config.description == "Test fixture description"
        assert config.package == "test-package@test"
        assert config.setup.plugins == ["plugin-a"]
        assert len(config.setup.files) == 1
        assert config.teardown.commands == ["echo \"cleanup\""]
        assert len(config.tests) == 1
        assert config.tests[0].test_id == "test-001"

    def test_from_yaml_without_tests(self, tmp_path: Path):
        """Test loading fixture without loading tests."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        fixture_yaml = """
name: no-tests
description: Fixture without loading tests
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        config = FixtureConfig.from_yaml(
            fixture_dir / "fixture.yaml",
            load_tests=False,
        )

        assert config.name == "no-tests"
        assert config.tests == []

    def test_discover_tests_multiple(self, tmp_path: Path):
        """Test discovering multiple test files."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        (fixture_dir / "fixture.yaml").write_text("name: multi\n")

        for i in range(3):
            (tests_dir / f"test_{i}.yaml").write_text(
                f"test_id: test-{i:03d}\nexecution:\n  prompt: test{i}\n"
            )

        config = FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        assert len(config.tests) == 3
        assert config.tests[0].test_id == "test-000"
        assert config.tests[1].test_id == "test-001"
        assert config.tests[2].test_id == "test-002"

    def test_get_merged_setup(self, tmp_path: Path):
        """Test merging fixture and test setup."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        fixture_yaml = """
name: merge-test
setup:
  commands:
    - echo "fixture setup"
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        test_yaml = """
test_id: test-001
setup:
  commands:
    - echo "test setup"
execution:
  prompt: test
"""
        (tests_dir / "test_merge.yaml").write_text(test_yaml)

        config = FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")
        merged = config.get_merged_setup(config.tests[0])

        assert merged.commands == ["echo \"fixture setup\"", "echo \"test setup\""]


# =============================================================================
# FixtureLoader Tests
# =============================================================================


class TestFixtureLoader:
    """Tests for FixtureLoader class."""

    @pytest.fixture
    def fixtures_dir(self, tmp_path: Path) -> Path:
        """Create a fixtures directory structure for testing."""
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()

        # Create fixture-a
        fixture_a = fixtures / "fixture-a"
        fixture_a.mkdir()
        (fixture_a / "fixture.yaml").write_text(
            "name: fixture-a\ndescription: First fixture\n"
        )
        tests_a = fixture_a / "tests"
        tests_a.mkdir()
        (tests_a / "test_one.yaml").write_text(
            "test_id: a-001\ntags:\n  - tag-a\nexecution:\n  prompt: test\n"
        )
        (tests_a / "test_two.yaml").write_text(
            "test_id: a-002\ntags:\n  - tag-b\nexecution:\n  prompt: test\n"
        )

        # Create fixture-b
        fixture_b = fixtures / "fixture-b"
        fixture_b.mkdir()
        (fixture_b / "fixture.yaml").write_text(
            "name: fixture-b\ndescription: Second fixture\n"
        )

        # Create non-fixture directory (no fixture.yaml)
        non_fixture = fixtures / "not-a-fixture"
        non_fixture.mkdir()

        return fixtures

    def test_discover_fixtures(self, fixtures_dir: Path):
        """Test fixture discovery."""
        loader = FixtureLoader(fixtures_dir)
        fixtures = loader.discover_fixtures()

        assert "fixture-a" in fixtures
        assert "fixture-b" in fixtures
        assert "not-a-fixture" not in fixtures

    def test_discover_fixtures_empty(self, tmp_path: Path):
        """Test fixture discovery with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        loader = FixtureLoader(empty_dir)
        fixtures = loader.discover_fixtures()

        assert fixtures == []

    def test_discover_fixtures_nonexistent(self, tmp_path: Path):
        """Test fixture discovery with non-existent directory."""
        loader = FixtureLoader(tmp_path / "nonexistent")
        fixtures = loader.discover_fixtures()

        assert fixtures == []

    def test_load_fixture(self, fixtures_dir: Path):
        """Test loading a specific fixture."""
        loader = FixtureLoader(fixtures_dir)
        config = loader.load_fixture("fixture-a")

        assert config.name == "fixture-a"
        assert config.description == "First fixture"
        assert len(config.tests) == 2

    def test_load_fixture_caching(self, fixtures_dir: Path):
        """Test fixture caching."""
        loader = FixtureLoader(fixtures_dir)

        config1 = loader.load_fixture("fixture-a")
        config2 = loader.load_fixture("fixture-a")

        assert config1 is config2  # Same object due to caching

    def test_load_fixture_no_cache(self, fixtures_dir: Path):
        """Test loading without cache."""
        loader = FixtureLoader(fixtures_dir)

        config1 = loader.load_fixture("fixture-a", use_cache=False)
        config2 = loader.load_fixture("fixture-a", use_cache=False)

        assert config1 is not config2  # Different objects

    def test_load_fixture_not_found(self, fixtures_dir: Path):
        """Test loading non-existent fixture."""
        loader = FixtureLoader(fixtures_dir)

        with pytest.raises(FileNotFoundError):
            loader.load_fixture("nonexistent")

    def test_load_test(self, fixtures_dir: Path):
        """Test loading a specific test file."""
        loader = FixtureLoader(fixtures_dir)
        config = loader.load_test("fixture-a", "test_one.yaml")

        assert config.test_id == "a-001"

    def test_load_test_not_found(self, fixtures_dir: Path):
        """Test loading non-existent test file."""
        loader = FixtureLoader(fixtures_dir)

        with pytest.raises(FileNotFoundError):
            loader.load_test("fixture-a", "nonexistent.yaml")

    def test_discover_tests(self, fixtures_dir: Path):
        """Test discovering test files in a fixture."""
        loader = FixtureLoader(fixtures_dir)
        tests = loader.discover_tests("fixture-a")

        assert len(tests) == 2
        assert all(p.name.startswith("test_") for p in tests)

    def test_get_test_by_id(self, fixtures_dir: Path):
        """Test getting test by ID."""
        loader = FixtureLoader(fixtures_dir)
        test = loader.get_test_by_id("fixture-a", "a-001")

        assert test is not None
        assert test.test_id == "a-001"

    def test_get_test_by_id_not_found(self, fixtures_dir: Path):
        """Test getting non-existent test by ID."""
        loader = FixtureLoader(fixtures_dir)
        test = loader.get_test_by_id("fixture-a", "nonexistent")

        assert test is None

    def test_get_tests_by_tag(self, fixtures_dir: Path):
        """Test filtering tests by tag."""
        loader = FixtureLoader(fixtures_dir)
        tests = loader.get_tests_by_tag("fixture-a", "tag-a")

        assert len(tests) == 1
        assert tests[0].test_id == "a-001"

    def test_clear_cache(self, fixtures_dir: Path):
        """Test clearing the cache."""
        loader = FixtureLoader(fixtures_dir)
        loader.load_fixture("fixture-a")

        assert "fixture-a" in loader._cache

        loader.clear_cache()

        assert loader._cache == {}


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture
    def fixtures_dir(self, tmp_path: Path) -> Path:
        """Create a minimal fixtures directory."""
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()

        fixture = fixtures / "test-fixture"
        fixture.mkdir()
        (fixture / "fixture.yaml").write_text("name: test-fixture\n")
        tests = fixture / "tests"
        tests.mkdir()
        (tests / "test_one.yaml").write_text(
            "test_id: t-001\nexecution:\n  prompt: test\n"
        )

        return fixtures

    def test_discover_fixtures(self, fixtures_dir: Path):
        """Test discover_fixtures convenience function."""
        fixtures = discover_fixtures(fixtures_dir)

        assert "test-fixture" in fixtures

    def test_load_fixture(self, fixtures_dir: Path):
        """Test load_fixture convenience function."""
        config = load_fixture(fixtures_dir, "test-fixture")

        assert config.name == "test-fixture"

    def test_load_test(self, fixtures_dir: Path):
        """Test load_test convenience function."""
        config = load_test(fixtures_dir, "test-fixture", "test_one.yaml")

        assert config.test_id == "t-001"


# =============================================================================
# Fixture Validation Tests
# =============================================================================


class TestFixtureValidation:
    """Tests for fixture validation (fail-fast guardrails)."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a mock project structure with registry and packages."""
        # Create registry directory and file
        registry_dir = tmp_path / "docs" / "registries" / "nuget"
        registry_dir.mkdir(parents=True)

        registry_data = {
            "packages": {
                "valid-plugin": {
                    "name": "valid-plugin",
                    "version": "1.0.0",
                    "path": "packages/valid-plugin",
                },
                "plugin-no-md": {
                    "name": "plugin-no-md",
                    "version": "1.0.0",
                    "path": "packages/plugin-no-md",
                },
            }
        }
        (registry_dir / "registry.json").write_text(json.dumps(registry_data))

        # Create packages directory structure
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()

        # valid-plugin with markdown files
        valid_plugin = packages_dir / "valid-plugin"
        valid_plugin.mkdir()
        (valid_plugin / "commands").mkdir()
        (valid_plugin / "commands" / "valid-plugin.md").write_text(
            "# Valid Plugin Command"
        )

        # plugin-no-md without markdown files (empty structure)
        no_md_plugin = packages_dir / "plugin-no-md"
        no_md_plugin.mkdir()
        (no_md_plugin / "commands").mkdir()  # Empty commands dir
        (no_md_plugin / "skills").mkdir()  # Empty skills dir

        return tmp_path

    @pytest.fixture
    def fixtures_dir(self, project_root: Path) -> Path:
        """Create fixtures directory inside the project root."""
        fixtures = project_root / "test-packages" / "fixtures"
        fixtures.mkdir(parents=True)
        return fixtures

    def test_validation_skipped_when_no_package(self, fixtures_dir: Path):
        """Test that validation is skipped when package field is empty."""
        fixture_dir = fixtures_dir / "no-package"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        fixture_yaml = """
name: no-package
description: Fixture without package field
# No package field
setup:
  plugins: []
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        # Should not raise any exception
        config = FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")
        assert config.name == "no-package"
        assert config.package == ""

    def test_validation_error_plugin_not_in_registry(self, fixtures_dir: Path):
        """Test validation fails when package references non-existent plugin."""
        fixture_dir = fixtures_dir / "bad-plugin"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        fixture_yaml = """
name: bad-plugin
description: References non-existent plugin
package: nonexistent-plugin@test
setup:
  plugins:
    - nonexistent-plugin@test
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        with pytest.raises(FixtureValidationError) as exc_info:
            FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        assert "not found in marketplace registry" in str(exc_info.value)
        assert "nonexistent-plugin" in str(exc_info.value)

    def test_validation_error_empty_setup_plugins(self, fixtures_dir: Path):
        """Test validation fails when setup.plugins is empty but package is specified."""
        fixture_dir = fixtures_dir / "empty-plugins"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        fixture_yaml = """
name: empty-plugins
description: Has package but empty setup.plugins
package: valid-plugin@test
setup:
  plugins: []
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        with pytest.raises(FixtureValidationError) as exc_info:
            FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        assert "setup.plugins must include the package" in str(exc_info.value)

    def test_validation_error_plugin_no_markdown_files(self, fixtures_dir: Path):
        """Test validation fails when plugin has no skill/command/agent markdown files."""
        fixture_dir = fixtures_dir / "no-md-fixture"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        fixture_yaml = """
name: no-md-fixture
description: Plugin without markdown files
package: plugin-no-md@test
setup:
  plugins:
    - plugin-no-md@test
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        with pytest.raises(FixtureValidationError) as exc_info:
            FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        assert "must have at least one skill/command/agent markdown file" in str(
            exc_info.value
        )

    def test_validation_passes_for_valid_fixture(self, fixtures_dir: Path):
        """Test validation passes when all rules are satisfied."""
        fixture_dir = fixtures_dir / "valid-fixture"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        fixture_yaml = """
name: valid-fixture
description: Valid fixture with all requirements met
package: valid-plugin@test
setup:
  plugins:
    - valid-plugin@test
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        # Should not raise any exception
        config = FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")
        assert config.name == "valid-fixture"
        assert config.package == "valid-plugin@test"
        assert config.setup.plugins == ["valid-plugin@test"]

    def test_validation_error_plugin_directory_not_found(self, fixtures_dir: Path):
        """Test validation fails when plugin directory doesn't exist."""
        # Add a plugin to registry but don't create its directory
        project_root = fixtures_dir.parent.parent
        registry_path = project_root / "docs" / "registries" / "nuget" / "registry.json"

        with open(registry_path) as f:
            registry = json.load(f)

        registry["packages"]["ghost-plugin"] = {
            "name": "ghost-plugin",
            "version": "1.0.0",
            "path": "packages/ghost-plugin",
        }

        with open(registry_path, "w") as f:
            json.dump(registry, f)

        fixture_dir = fixtures_dir / "ghost-fixture"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        fixture_yaml = """
name: ghost-fixture
description: Plugin exists in registry but directory missing
package: ghost-plugin@test
setup:
  plugins:
    - ghost-plugin@test
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        with pytest.raises(FixtureValidationError) as exc_info:
            FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        assert "Plugin directory not found" in str(exc_info.value)

    def test_validation_finds_md_in_nested_skills_directory(self, fixtures_dir: Path):
        """Test validation finds markdown files in nested skills directories."""
        project_root = fixtures_dir.parent.parent
        registry_path = project_root / "docs" / "registries" / "nuget" / "registry.json"

        with open(registry_path) as f:
            registry = json.load(f)

        registry["packages"]["nested-skill-plugin"] = {
            "name": "nested-skill-plugin",
            "version": "1.0.0",
            "path": "packages/nested-skill-plugin",
        }

        with open(registry_path, "w") as f:
            json.dump(registry, f)

        # Create plugin with nested skills structure
        plugin_dir = project_root / "packages" / "nested-skill-plugin"
        plugin_dir.mkdir()
        nested_skill = plugin_dir / "skills" / "nested-skill-plugin"
        nested_skill.mkdir(parents=True)
        (nested_skill / "SKILL.md").write_text("# Nested Skill")

        fixture_dir = fixtures_dir / "nested-skill-fixture"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        fixture_yaml = """
name: nested-skill-fixture
description: Plugin with nested skill markdown file
package: nested-skill-plugin@test
setup:
  plugins:
    - nested-skill-plugin@test
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        # Should not raise any exception
        config = FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")
        assert config.name == "nested-skill-fixture"

    def test_fixture_validation_error_has_fixture_name(self, fixtures_dir: Path):
        """Test FixtureValidationError includes fixture name in message."""
        fixture_dir = fixtures_dir / "named-error"
        fixture_dir.mkdir()
        tests_dir = fixture_dir / "tests"
        tests_dir.mkdir()

        fixture_yaml = """
name: my-fixture-name
description: Should show fixture name in error
package: nonexistent@test
setup:
  plugins:
    - nonexistent@test
"""
        (fixture_dir / "fixture.yaml").write_text(fixture_yaml)

        with pytest.raises(FixtureValidationError) as exc_info:
            FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        # Error message should include fixture name prefix
        assert "[my-fixture-name]" in str(exc_info.value)


class TestFixtureValidationError:
    """Tests for FixtureValidationError exception class."""

    def test_error_with_fixture_name(self):
        """Test error message includes fixture name prefix."""
        error = FixtureValidationError(
            "Test error message", fixture_name="test-fixture"
        )
        assert str(error) == "[test-fixture] Test error message"
        assert error.fixture_name == "test-fixture"

    def test_error_without_fixture_name(self):
        """Test error message without fixture name."""
        error = FixtureValidationError("Test error message")
        assert str(error) == "Test error message"
        assert error.fixture_name is None

    def test_error_is_exception_subclass(self):
        """Test FixtureValidationError is an Exception subclass."""
        error = FixtureValidationError("Test")
        assert isinstance(error, Exception)
