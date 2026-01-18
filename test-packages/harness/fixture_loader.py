"""
YAML fixture loading and parsing for Claude Code test harness.

This module provides functionality to:
- Discover fixture directories from a fixtures path
- Parse fixture.yaml manifests and individual test_*.yaml files
- Create FixtureConfig and TestConfig dataclasses from YAML
- Support inheritance of setup/teardown between fixture and test level

Based on the fixture design from:
- docs/requirements/test-harness-design-spec.md (Section 7)

Example usage:
    from harness.fixture_loader import FixtureLoader, discover_fixtures

    # Discover all fixtures
    loader = FixtureLoader("/path/to/test-packages/fixtures")
    fixtures = loader.discover_fixtures()

    # Load a specific fixture
    config = loader.load_fixture("sc-startup")
    for test in config.tests:
        print(f"Test: {test.test_id}")

Example fixture structure:
    fixtures/
      sc-startup/
        fixture.yaml           # Fixture configuration
        tests/
          test_readonly.yaml   # Individual test
          test_init.yaml
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class FixtureValidationError(Exception):
    """Exception raised when fixture validation fails.

    This exception is raised during fixture loading when the fixture
    configuration contains invalid or inconsistent values that would
    prevent proper test execution.

    Attributes:
        message: Human-readable error message describing the validation failure
        fixture_name: Name of the fixture that failed validation (if available)
    """

    def __init__(self, message: str, fixture_name: str | None = None):
        self.fixture_name = fixture_name
        prefix = f"[{fixture_name}] " if fixture_name else ""
        super().__init__(f"{prefix}{message}")


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class FileMapping:
    """Represents a file to copy during setup.

    Attributes:
        src: Source path relative to fixture directory
        dest: Destination path relative to project root
    """
    src: str
    dest: str

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "FileMapping":
        """Create FileMapping from dictionary."""
        return cls(
            src=data.get("src", ""),
            dest=data.get("dest", ""),
        )


@dataclass
class SetupConfig:
    """Setup configuration for fixtures or tests.

    Attributes:
        plugins: List of plugins to install
        files: List of file mappings to copy
        commands: List of shell commands to run
    """
    plugins: list[str] = field(default_factory=list)
    files: list[FileMapping] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SetupConfig":
        """Create SetupConfig from dictionary."""
        if not data:
            return cls()

        files = [FileMapping.from_dict(f) for f in data.get("files", [])]
        return cls(
            plugins=data.get("plugins", []),
            files=files,
            commands=data.get("commands", []),
        )

    def merge(self, other: "SetupConfig") -> "SetupConfig":
        """Merge with another SetupConfig (other takes precedence for conflicts)."""
        return SetupConfig(
            plugins=self.plugins + other.plugins,
            files=self.files + other.files,
            commands=self.commands + other.commands,
        )


@dataclass
class TeardownConfig:
    """Teardown configuration for fixtures.

    Attributes:
        commands: List of shell commands to run for cleanup
    """
    commands: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TeardownConfig":
        """Create TeardownConfig from dictionary."""
        if not data:
            return cls()
        return cls(commands=data.get("commands", []))


@dataclass
class ExpectationConfig:
    """Configuration for a single expectation.

    Attributes:
        id: Unique expectation identifier
        description: Human-readable description
        type: Expectation type (tool_call, hook_event, subagent_event, output_contains)
        expected: Type-specific expected values
    """
    id: str
    description: str
    type: str
    expected: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any], index: int = 0) -> "ExpectationConfig":
        """Create ExpectationConfig from dictionary."""
        return cls(
            id=data.get("id", f"exp-{index+1:03d}"),
            description=data.get("description", ""),
            type=data.get("type", "tool_call"),
            expected=data.get("expected", {}),
        )


@dataclass
class ExecutionConfig:
    """Execution configuration for a test.

    Attributes:
        prompt: The prompt to send to Claude
        model: Claude model to use (default: haiku)
        tools: List of tools to allow
        timeout_ms: Timeout in milliseconds
    """
    prompt: str = ""
    model: str = "haiku"
    tools: list[str] = field(default_factory=list)
    timeout_ms: int = 60000

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ExecutionConfig":
        """Create ExecutionConfig from dictionary."""
        if not data:
            return cls()
        return cls(
            prompt=data.get("prompt", ""),
            model=data.get("model", "haiku"),
            tools=data.get("tools", []),
            timeout_ms=data.get("timeout_ms", 60000),
        )


@dataclass
class TestConfig:
    """Configuration for an individual test loaded from test_*.yaml.

    Attributes:
        test_id: Unique test identifier
        test_name: Human-readable test name
        description: Test description
        tags: List of tags for filtering
        execution: Execution configuration
        setup: Additional setup for this test
        expectations: List of expectations to evaluate
        skip: Whether to skip this test
        skip_reason: Reason for skipping
        source_path: Path to the source YAML file
    """
    __test__ = False  # Prevent pytest collection

    test_id: str
    test_name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    setup: SetupConfig = field(default_factory=SetupConfig)
    expectations: list[ExpectationConfig] = field(default_factory=list)
    skip: bool = False
    skip_reason: str = ""
    source_path: Path | None = None

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "TestConfig":
        """Load test configuration from YAML file.

        Args:
            yaml_path: Path to test_*.yaml file

        Returns:
            TestConfig instance

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        with open(yaml_path) as f:
            data = yaml.safe_load(f) or {}

        expectations = [
            ExpectationConfig.from_dict(exp, i)
            for i, exp in enumerate(data.get("expectations", []))
        ]

        return cls(
            test_id=data.get("test_id", yaml_path.stem),
            test_name=data.get("test_name", yaml_path.stem.replace("_", " ").title()),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            execution=ExecutionConfig.from_dict(data.get("execution")),
            setup=SetupConfig.from_dict(data.get("setup")),
            expectations=expectations,
            skip=data.get("skip", False),
            skip_reason=data.get("skip_reason", ""),
            source_path=yaml_path,
        )

    @property
    def prompt(self) -> str:
        """Convenience access to execution prompt."""
        return self.execution.prompt

    @property
    def model(self) -> str:
        """Convenience access to execution model."""
        return self.execution.model

    @property
    def tools(self) -> list[str]:
        """Convenience access to execution tools."""
        return self.execution.tools

    @property
    def timeout_ms(self) -> int:
        """Convenience access to execution timeout."""
        return self.execution.timeout_ms


@dataclass
class FixtureConfig:
    """Configuration for a test fixture loaded from fixture.yaml.

    Attributes:
        name: Fixture name (usually directory name)
        description: Human-readable description
        package: Package being tested (e.g., 'sc-startup@synaptic-canvas')
        setup: Shared setup for all tests
        teardown: Shared teardown for all tests
        tests_dir: Directory containing test files (default: 'tests')
        tests: Loaded test configurations
        source_path: Path to fixture.yaml
    """
    name: str
    description: str = ""
    package: str = ""
    setup: SetupConfig = field(default_factory=SetupConfig)
    teardown: TeardownConfig = field(default_factory=TeardownConfig)
    tests_dir: str = "tests"
    tests: list[TestConfig] = field(default_factory=list)
    source_path: Path | None = None

    @classmethod
    def from_yaml(cls, yaml_path: Path, load_tests: bool = True) -> "FixtureConfig":
        """Load fixture configuration from YAML file.

        Args:
            yaml_path: Path to fixture.yaml
            load_tests: Whether to also load test configurations

        Returns:
            FixtureConfig instance with optionally loaded tests

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        with open(yaml_path) as f:
            data = yaml.safe_load(f) or {}

        config = cls(
            name=data.get("name", yaml_path.parent.name),
            description=data.get("description", ""),
            package=data.get("package", ""),
            setup=SetupConfig.from_dict(data.get("setup")),
            teardown=TeardownConfig.from_dict(data.get("teardown")),
            tests_dir=data.get("tests_dir", "tests"),
            source_path=yaml_path,
        )

        # Validate fixture configuration (fail fast)
        config._validate_fixture_config()

        if load_tests:
            config.tests = config.discover_tests()

        return config

    def discover_tests(self) -> list[TestConfig]:
        """Discover and load tests from the tests directory.

        Returns:
            List of TestConfig objects sorted by filename
        """
        if not self.source_path:
            return []

        tests_path = self.source_path.parent / self.tests_dir
        if not tests_path.exists():
            logger.warning(f"Tests directory not found: {tests_path}")
            return []

        tests = []
        for yaml_file in sorted(tests_path.glob("test_*.yaml")):
            try:
                test_config = TestConfig.from_yaml(yaml_file)
                tests.append(test_config)
                logger.debug(f"Loaded test: {test_config.test_id}")
            except Exception as e:
                logger.error(f"Failed to load test {yaml_file}: {e}")

        logger.info(f"Discovered {len(tests)} tests in {self.name}")
        return tests

    def get_merged_setup(self, test: TestConfig) -> SetupConfig:
        """Get merged setup combining fixture and test setup.

        Args:
            test: Test configuration

        Returns:
            Merged SetupConfig with fixture setup first, then test setup
        """
        return self.setup.merge(test.setup)

    def _validate_fixture_config(self) -> None:
        """Validate fixture configuration and fail fast if invalid.

        Performs the following validations:
        1. If `package` is specified, verify it exists in the marketplace registry
        2. If `package` is specified, verify `setup.plugins` is not empty
        3. If `package` is specified, verify the plugin has at least one
           skill/command/agent markdown file

        Raises:
            FixtureValidationError: If any validation rule fails
        """
        # Skip validation if no package is specified
        if not self.package:
            return

        # Extract plugin name from package (format: "plugin-name@source" or just "plugin-name")
        plugin_name = self.package.split("@")[0] if "@" in self.package else self.package

        # Find the project root by looking for the registry
        project_root = self._find_project_root()
        if not project_root:
            logger.warning(
                f"Could not find project root for validation, skipping registry check"
            )
        else:
            # Validation 1: Check plugin exists in marketplace registry
            registry_path = project_root / "docs" / "registries" / "nuget" / "registry.json"
            self._validate_plugin_in_registry(plugin_name, registry_path)

            # Validation 3: Check plugin has markdown files
            packages_path = project_root / "packages" / plugin_name
            self._validate_plugin_has_markdown_files(plugin_name, packages_path)

        # Validation 2: Check setup.plugins is not empty when package is specified
        self._validate_setup_plugins_not_empty(plugin_name)

    def _find_project_root(self) -> Path | None:
        """Find the project root by searching for the registry file.

        Searches upward from the fixture's source_path looking for
        docs/registries/nuget/registry.json.

        Returns:
            Path to project root, or None if not found
        """
        if not self.source_path:
            return None

        current = self.source_path.parent.absolute()
        # Search up to 10 levels to find project root
        for _ in range(10):
            registry_path = current / "docs" / "registries" / "nuget" / "registry.json"
            if registry_path.exists():
                return current
            if current.parent == current:
                break
            current = current.parent
        return None

    def _validate_plugin_in_registry(self, plugin_name: str, registry_path: Path) -> None:
        """Validate plugin exists in marketplace registry.

        Args:
            plugin_name: Name of the plugin to check
            registry_path: Path to the registry.json file

        Raises:
            FixtureValidationError: If plugin not found in registry
        """
        if not registry_path.exists():
            logger.warning(f"Registry file not found: {registry_path}")
            return

        try:
            with open(registry_path) as f:
                registry = json.load(f)

            packages = registry.get("packages", {})
            if plugin_name not in packages:
                raise FixtureValidationError(
                    f"Plugin '{plugin_name}' not found in marketplace registry",
                    fixture_name=self.name,
                )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse registry.json: {e}")
            raise FixtureValidationError(
                f"Failed to parse marketplace registry: {e}",
                fixture_name=self.name,
            ) from e

    def _validate_setup_plugins_not_empty(self, plugin_name: str) -> None:
        """Validate setup.plugins is not empty when package is specified.

        Args:
            plugin_name: Name of the plugin for error message

        Raises:
            FixtureValidationError: If setup.plugins is empty
        """
        if not self.setup.plugins:
            raise FixtureValidationError(
                f"setup.plugins must include the package when package field is specified",
                fixture_name=self.name,
            )

    def _validate_plugin_has_markdown_files(
        self, plugin_name: str, packages_path: Path
    ) -> None:
        """Validate plugin has at least one skill/command/agent markdown file.

        Args:
            plugin_name: Name of the plugin
            packages_path: Path to the plugin's package directory

        Raises:
            FixtureValidationError: If plugin has no markdown files
        """
        if not packages_path.exists():
            raise FixtureValidationError(
                f"Plugin directory not found: {packages_path}",
                fixture_name=self.name,
            )

        # Check for markdown files in skills/, commands/, and agents/ directories
        md_dirs = ["skills", "commands", "agents"]
        found_md_files = []

        for md_dir in md_dirs:
            dir_path = packages_path / md_dir
            if dir_path.exists():
                # Search recursively for .md files
                md_files = list(dir_path.glob("**/*.md"))
                found_md_files.extend(md_files)

        if not found_md_files:
            raise FixtureValidationError(
                f"Plugin '{plugin_name}' must have at least one "
                f"skill/command/agent markdown file",
                fixture_name=self.name,
            )


# =============================================================================
# Fixture Loader
# =============================================================================


class FixtureLoader:
    """Loads and manages test fixtures from a fixtures directory.

    Provides functionality to discover fixtures, load configurations,
    and access test definitions.

    Attributes:
        fixtures_path: Base path to fixtures directory

    Example:
        loader = FixtureLoader("/path/to/fixtures")
        fixtures = loader.discover_fixtures()
        config = loader.load_fixture("sc-startup")
    """

    def __init__(self, fixtures_path: str | Path):
        """Initialize the FixtureLoader.

        Args:
            fixtures_path: Path to the fixtures directory
        """
        self.fixtures_path = Path(fixtures_path).absolute()
        self._cache: dict[str, FixtureConfig] = {}

    def discover_fixtures(self) -> list[str]:
        """Discover available fixture names.

        Scans the fixtures directory for subdirectories containing
        a fixture.yaml file.

        Returns:
            List of fixture names (directory names)
        """
        if not self.fixtures_path.exists():
            logger.warning(f"Fixtures path not found: {self.fixtures_path}")
            return []

        fixtures = []
        for item in sorted(self.fixtures_path.iterdir()):
            if item.is_dir() and (item / "fixture.yaml").exists():
                fixtures.append(item.name)

        logger.info(f"Discovered {len(fixtures)} fixtures")
        return fixtures

    def load_fixture(
        self,
        fixture_name: str,
        load_tests: bool = True,
        use_cache: bool = True,
    ) -> FixtureConfig:
        """Load a fixture configuration.

        Args:
            fixture_name: Name of the fixture to load
            load_tests: Whether to also load test configurations
            use_cache: Whether to use cached configuration

        Returns:
            FixtureConfig instance

        Raises:
            FileNotFoundError: If fixture doesn't exist
        """
        if use_cache and fixture_name in self._cache:
            return self._cache[fixture_name]

        fixture_dir = self.fixtures_path / fixture_name
        yaml_path = fixture_dir / "fixture.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(f"Fixture not found: {yaml_path}")

        config = FixtureConfig.from_yaml(yaml_path, load_tests=load_tests)

        if use_cache:
            self._cache[fixture_name] = config

        return config

    def load_test(self, fixture_name: str, test_file: str) -> TestConfig:
        """Load a specific test configuration.

        Args:
            fixture_name: Name of the fixture
            test_file: Name of the test YAML file (e.g., 'test_readonly.yaml')

        Returns:
            TestConfig instance

        Raises:
            FileNotFoundError: If test file doesn't exist
        """
        fixture = self.load_fixture(fixture_name, load_tests=False)
        test_path = self.fixtures_path / fixture_name / fixture.tests_dir / test_file

        if not test_path.exists():
            raise FileNotFoundError(f"Test file not found: {test_path}")

        return TestConfig.from_yaml(test_path)

    def discover_tests(self, fixture_name: str) -> list[Path]:
        """Discover test files in a fixture.

        Args:
            fixture_name: Name of the fixture

        Returns:
            List of paths to test YAML files
        """
        fixture = self.load_fixture(fixture_name, load_tests=False)
        tests_path = self.fixtures_path / fixture_name / fixture.tests_dir

        if not tests_path.exists():
            return []

        return sorted(tests_path.glob("test_*.yaml"))

    def get_test_by_id(self, fixture_name: str, test_id: str) -> TestConfig | None:
        """Get a test configuration by its test_id.

        Args:
            fixture_name: Name of the fixture
            test_id: The test_id to search for

        Returns:
            TestConfig if found, None otherwise
        """
        fixture = self.load_fixture(fixture_name)
        for test in fixture.tests:
            if test.test_id == test_id:
                return test
        return None

    def get_tests_by_tag(self, fixture_name: str, tag: str) -> list[TestConfig]:
        """Get tests filtered by tag.

        Args:
            fixture_name: Name of the fixture
            tag: Tag to filter by

        Returns:
            List of TestConfig objects with the specified tag
        """
        fixture = self.load_fixture(fixture_name)
        return [test for test in fixture.tests if tag in test.tags]

    def clear_cache(self) -> None:
        """Clear the fixture cache."""
        self._cache.clear()


# =============================================================================
# Convenience Functions
# =============================================================================


def discover_fixtures(fixtures_path: str | Path) -> list[str]:
    """Discover available fixtures in a directory.

    Convenience function that creates a FixtureLoader and discovers fixtures.

    Args:
        fixtures_path: Path to fixtures directory

    Returns:
        List of fixture names
    """
    loader = FixtureLoader(fixtures_path)
    return loader.discover_fixtures()


def load_fixture(fixtures_path: str | Path, fixture_name: str) -> FixtureConfig:
    """Load a fixture configuration.

    Convenience function that creates a FixtureLoader and loads a fixture.

    Args:
        fixtures_path: Path to fixtures directory
        fixture_name: Name of the fixture to load

    Returns:
        FixtureConfig instance
    """
    loader = FixtureLoader(fixtures_path)
    return loader.load_fixture(fixture_name)


def load_test(fixtures_path: str | Path, fixture_name: str, test_file: str) -> TestConfig:
    """Load a test configuration.

    Convenience function that creates a FixtureLoader and loads a test.

    Args:
        fixtures_path: Path to fixtures directory
        fixture_name: Name of the fixture
        test_file: Name of the test YAML file

    Returns:
        TestConfig instance
    """
    loader = FixtureLoader(fixtures_path)
    return loader.load_test(fixture_name, test_file)
