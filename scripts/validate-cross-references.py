#!/usr/bin/env python3
"""
validate-cross-references.py - Validate all file cross-references in the repository

Usage:
  python3 scripts/validate-cross-references.py [--package <name>] [--verbose]

Validates:
- marketplace.json ↔ manifest.yaml (versions, descriptions)
- registry.json ↔ manifest.yaml (versions, metadata)
- plugin.json ↔ manifest.yaml (artifacts, metadata)
- .claude/agents/registry.yaml ↔ actual agent files
- Dependencies reference valid packages
- Circular dependency detection

Exit codes:
  0: All cross-references valid
  1: Cross-reference issues found
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml
from pydantic import BaseModel, Field, field_validator

# Add test-packages/harness to path for Result imports
sys.path.insert(0, str(Path(__file__).parent.parent / "test-packages" / "harness"))
from result import AggregateError, Failure, Result, Success, collect_results


# -----------------------------------------------------------------------------
# Error Types
# -----------------------------------------------------------------------------


@dataclass
class CrossReferenceError:
    """Error during cross-reference validation."""

    message: str
    source_file: str
    target_file: str
    context: Dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Report of validation results."""

    total_checks: int
    passed_checks: int
    failed_checks: int
    warnings: List[str] = field(default_factory=list)
    errors: List[CrossReferenceError] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.failed_checks == 0


# -----------------------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------------------


class ManifestSchema(BaseModel):
    """Schema for manifest.yaml."""

    name: str
    version: str
    description: str
    author: str
    license: str
    tags: List[str] = Field(default_factory=list)
    artifacts: Optional[Dict[str, List[str]]] = None
    install: Optional[Dict] = None
    requires: Optional[Dict[str, List[str]] | List[str]] = Field(default=None)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        import re

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Invalid version format: {v}")
        return v


class PluginSchema(BaseModel):
    """Schema for plugin.json."""

    name: str
    description: str
    version: str
    author: Dict[str, str]
    license: str
    keywords: List[str] = Field(default_factory=list)
    commands: Optional[List[str]] = Field(default_factory=list)
    agents: Optional[List[str]] = Field(default_factory=list)
    skills: Optional[List[str]] = Field(default_factory=list)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        import re

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Invalid version format: {v}")
        return v


class MarketplacePluginSchema(BaseModel):
    """Schema for plugin entry in marketplace.json."""

    name: str
    source: str
    description: str
    version: str
    author: Dict[str, str]
    license: str
    keywords: List[str] = Field(default_factory=list)
    category: str


class MarketplaceSchema(BaseModel):
    """Schema for marketplace.json."""

    name: str
    owner: Dict[str, str]
    metadata: Dict[str, str]
    plugins: List[MarketplacePluginSchema]


class RegistryPackageSchema(BaseModel):
    """Schema for package entry in registry.json."""

    name: str
    version: str
    status: str
    tier: int
    description: str
    github: str
    repo: str
    path: str
    license: str
    author: str
    tags: List[str]
    artifacts: Dict[str, int]
    dependencies: List[str] = Field(default_factory=list)


class RegistrySchema(BaseModel):
    """Schema for registry.json."""

    packages: Dict[str, RegistryPackageSchema]


class AgentEntrySchema(BaseModel):
    """Schema for agent entry in registry.yaml."""

    version: str
    path: str


class AgentRegistrySchema(BaseModel):
    """Schema for .claude/agents/registry.yaml."""

    agents: Dict[str, AgentEntrySchema]
    skills: Optional[Dict[str, Dict]] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Dependency Graph for Circular Detection
# -----------------------------------------------------------------------------


@dataclass
class DependencyGraph:
    """Graph for tracking package dependencies."""

    nodes: Set[str] = field(default_factory=set)
    edges: Dict[str, Set[str]] = field(default_factory=dict)

    def add_node(self, package: str) -> None:
        """Add a package node."""
        self.nodes.add(package)
        if package not in self.edges:
            self.edges[package] = set()

    def add_edge(self, from_pkg: str, to_pkg: str) -> None:
        """Add a dependency edge."""
        self.add_node(from_pkg)
        self.add_node(to_pkg)
        self.edges[from_pkg].add(to_pkg)

    def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.edges.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)

        for node in self.nodes:
            if node not in visited:
                dfs(node, [])

        return cycles


# -----------------------------------------------------------------------------
# Validation Functions
# -----------------------------------------------------------------------------


def load_yaml(file_path: Path) -> Result[Dict, CrossReferenceError]:
    """Load and parse YAML file."""
    try:
        if not file_path.exists():
            return Failure(
                error=CrossReferenceError(
                    message=f"File not found: {file_path}",
                    source_file=str(file_path),
                    target_file="",
                )
            )

        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        if data is None:
            return Failure(
                error=CrossReferenceError(
                    message=f"Empty YAML file: {file_path}",
                    source_file=str(file_path),
                    target_file="",
                )
            )

        return Success(value=data, warnings=[])
    except yaml.YAMLError as e:
        return Failure(
            error=CrossReferenceError(
                message=f"Invalid YAML: {e}",
                source_file=str(file_path),
                target_file="",
            )
        )
    except Exception as e:
        return Failure(
            error=CrossReferenceError(
                message=f"Error loading YAML: {e}",
                source_file=str(file_path),
                target_file="",
            )
        )


def load_json(file_path: Path) -> Result[Dict, CrossReferenceError]:
    """Load and parse JSON file."""
    try:
        if not file_path.exists():
            return Failure(
                error=CrossReferenceError(
                    message=f"File not found: {file_path}",
                    source_file=str(file_path),
                    target_file="",
                )
            )

        with open(file_path, "r") as f:
            data = json.load(f)

        return Success(value=data, warnings=[])
    except json.JSONDecodeError as e:
        return Failure(
            error=CrossReferenceError(
                message=f"Invalid JSON: {e}",
                source_file=str(file_path),
                target_file="",
            )
        )
    except Exception as e:
        return Failure(
            error=CrossReferenceError(
                message=f"Error loading JSON: {e}",
                source_file=str(file_path),
                target_file="",
            )
        )


def validate_manifest_plugin_consistency(
    manifest_path: Path, plugin_path: Path
) -> Result[bool, CrossReferenceError]:
    """Validate manifest.yaml matches plugin.json."""
    manifest_result = load_yaml(manifest_path)
    if isinstance(manifest_result, Failure):
        return manifest_result

    plugin_result = load_json(plugin_path)
    if isinstance(plugin_result, Failure):
        return plugin_result

    try:
        manifest = ManifestSchema(**manifest_result.value)
        plugin = PluginSchema(**plugin_result.value)

        warnings = []

        # Check version consistency
        if manifest.version != plugin.version:
            return Failure(
                error=CrossReferenceError(
                    message=f"Version mismatch: manifest={manifest.version}, plugin={plugin.version}",
                    source_file=str(manifest_path),
                    target_file=str(plugin_path),
                    context={"manifest_version": manifest.version, "plugin_version": plugin.version},
                )
            )

        # Check name consistency
        if manifest.name != plugin.name:
            return Failure(
                error=CrossReferenceError(
                    message=f"Name mismatch: manifest={manifest.name}, plugin={plugin.name}",
                    source_file=str(manifest_path),
                    target_file=str(plugin_path),
                )
            )

        # Check description consistency
        if manifest.description != plugin.description:
            warnings.append(
                f"Description mismatch: manifest={manifest.description[:50]}..., plugin={plugin.description[:50]}..."
            )

        # Validate artifacts exist
        if manifest.artifacts:
            for artifact_type, artifact_list in manifest.artifacts.items():
                for artifact_path in artifact_list:
                    full_path = manifest_path.parent / artifact_path
                    if not full_path.exists():
                        return Failure(
                            error=CrossReferenceError(
                                message=f"Artifact not found: {artifact_path}",
                                source_file=str(manifest_path),
                                target_file=str(full_path),
                                context={"artifact_type": artifact_type},
                            )
                        )

        return Success(value=True, warnings=warnings)

    except Exception as e:
        return Failure(
            error=CrossReferenceError(
                message=f"Validation error: {e}",
                source_file=str(manifest_path),
                target_file=str(plugin_path),
            )
        )


def validate_marketplace_consistency(
    marketplace_path: Path, packages_dir: Path
) -> Result[bool, CrossReferenceError]:
    """Validate marketplace.json matches package manifests."""
    marketplace_result = load_json(marketplace_path)
    if isinstance(marketplace_result, Failure):
        return marketplace_result

    try:
        marketplace = MarketplaceSchema(**marketplace_result.value)
        warnings = []

        for plugin in marketplace.plugins:
            # Find corresponding manifest
            pkg_name = plugin.name
            manifest_path = packages_dir / pkg_name / "manifest.yaml"

            if not manifest_path.exists():
                return Failure(
                    error=CrossReferenceError(
                        message=f"Manifest not found for marketplace plugin: {pkg_name}",
                        source_file=str(marketplace_path),
                        target_file=str(manifest_path),
                    )
                )

            manifest_result = load_yaml(manifest_path)
            if isinstance(manifest_result, Failure):
                return manifest_result

            manifest = ManifestSchema(**manifest_result.value)

            # Check version consistency
            if plugin.version != manifest.version:
                return Failure(
                    error=CrossReferenceError(
                        message=f"Version mismatch for {pkg_name}: marketplace={plugin.version}, manifest={manifest.version}",
                        source_file=str(marketplace_path),
                        target_file=str(manifest_path),
                    )
                )

            # Check description consistency
            if plugin.description != manifest.description:
                warnings.append(
                    f"Description mismatch for {pkg_name}: marketplace vs manifest"
                )

        return Success(value=True, warnings=warnings)

    except Exception as e:
        return Failure(
            error=CrossReferenceError(
                message=f"Marketplace validation error: {e}",
                source_file=str(marketplace_path),
                target_file="",
            )
        )


def validate_registry_consistency(
    registry_path: Path, packages_dir: Path
) -> Result[bool, CrossReferenceError]:
    """Validate registry.json matches package manifests."""
    registry_result = load_json(registry_path)
    if isinstance(registry_result, Failure):
        return registry_result

    try:
        registry = RegistrySchema(**registry_result.value)
        warnings = []

        for pkg_name, pkg_info in registry.packages.items():
            # Find corresponding manifest
            manifest_path = packages_dir / pkg_name / "manifest.yaml"

            if not manifest_path.exists():
                return Failure(
                    error=CrossReferenceError(
                        message=f"Manifest not found for registry package: {pkg_name}",
                        source_file=str(registry_path),
                        target_file=str(manifest_path),
                    )
                )

            manifest_result = load_yaml(manifest_path)
            if isinstance(manifest_result, Failure):
                return manifest_result

            manifest = ManifestSchema(**manifest_result.value)

            # Check version consistency
            if pkg_info.version != manifest.version:
                return Failure(
                    error=CrossReferenceError(
                        message=f"Version mismatch for {pkg_name}: registry={pkg_info.version}, manifest={manifest.version}",
                        source_file=str(registry_path),
                        target_file=str(manifest_path),
                    )
                )

        return Success(value=True, warnings=warnings)

    except Exception as e:
        return Failure(
            error=CrossReferenceError(
                message=f"Registry validation error: {e}",
                source_file=str(registry_path),
                target_file="",
            )
        )


def validate_agent_registry(
    agent_registry_path: Path, repo_root: Path
) -> Result[bool, CrossReferenceError]:
    """Validate .claude/agents/registry.yaml references existing agent files."""
    registry_result = load_yaml(agent_registry_path)
    if isinstance(registry_result, Failure):
        return registry_result

    try:
        registry = AgentRegistrySchema(**registry_result.value)
        warnings = []

        for agent_name, agent_info in registry.agents.items():
            agent_path = repo_root / agent_info.path

            if not agent_path.exists():
                return Failure(
                    error=CrossReferenceError(
                        message=f"Agent file not found: {agent_name} -> {agent_info.path}",
                        source_file=str(agent_registry_path),
                        target_file=str(agent_path),
                        context={"agent_name": agent_name},
                    )
                )

        return Success(value=True, warnings=warnings)

    except Exception as e:
        return Failure(
            error=CrossReferenceError(
                message=f"Agent registry validation error: {e}",
                source_file=str(agent_registry_path),
                target_file="",
            )
        )


def validate_dependencies(
    packages_dir: Path, registry_path: Optional[Path] = None
) -> Result[bool, CrossReferenceError]:
    """Validate package dependencies reference valid packages."""
    warnings = []
    graph = DependencyGraph()

    # Get list of valid packages
    valid_packages = set()
    for pkg_dir in packages_dir.iterdir():
        if pkg_dir.is_dir() and (pkg_dir / "manifest.yaml").exists():
            valid_packages.add(pkg_dir.name)

    # Check each package's dependencies
    for pkg_dir in packages_dir.iterdir():
        if not pkg_dir.is_dir():
            continue

        manifest_path = pkg_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue

        manifest_result = load_yaml(manifest_path)
        if isinstance(manifest_result, Failure):
            return manifest_result

        try:
            manifest = ManifestSchema(**manifest_result.value)
            pkg_name = manifest.name

            graph.add_node(pkg_name)

            # Parse dependencies - handle both list and dict formats
            deps_to_check = []
            if isinstance(manifest.requires, dict):
                # Dict format: {packages: [...], cli: [...]}
                deps_to_check = manifest.requires.get("packages", [])
            elif isinstance(manifest.requires, list):
                # List format: [...]
                deps_to_check = manifest.requires

            # Parse dependencies (format: "package >= version" or "package")
            for dep in deps_to_check:
                dep_parts = dep.split(">=")
                dep_name = dep_parts[0].strip()

                # Check if it's a package dependency (starts with "sc-")
                if dep_name.startswith("sc-"):
                    if dep_name not in valid_packages:
                        return Failure(
                            error=CrossReferenceError(
                                message=f"Invalid dependency: {pkg_name} depends on non-existent package {dep_name}",
                                source_file=str(manifest_path),
                                target_file="",
                                context={"dependency": dep},
                            )
                        )

                    # Add to dependency graph
                    graph.add_edge(pkg_name, dep_name)

        except Exception as e:
            return Failure(
                error=CrossReferenceError(
                    message=f"Error processing dependencies for {pkg_dir.name}: {e}",
                    source_file=str(manifest_path),
                    target_file="",
                )
            )

    # Check for circular dependencies
    cycles = graph.detect_cycles()
    if cycles:
        cycle_strs = [" -> ".join(cycle) for cycle in cycles]
        return Failure(
            error=CrossReferenceError(
                message=f"Circular dependencies detected: {', '.join(cycle_strs)}",
                source_file="dependency graph",
                target_file="",
                context={"cycles": cycle_strs},
            )
        )

    return Success(value=True, warnings=warnings)


def validate_package(package_dir: Path, repo_root: Path) -> Result[bool, CrossReferenceError]:
    """Validate all cross-references for a single package."""
    results = []

    # Validate manifest ↔ plugin.json
    manifest_path = package_dir / "manifest.yaml"
    plugin_path = package_dir / ".claude-plugin" / "plugin.json"

    if manifest_path.exists() and plugin_path.exists():
        results.append(validate_manifest_plugin_consistency(manifest_path, plugin_path))

    # Collect results
    collected = collect_results(results)
    if isinstance(collected, Failure):
        # Extract first error from aggregate
        if collected.error.errors:
            return Failure(error=collected.error.errors[0])
        return Failure(
            error=CrossReferenceError(
                message="Unknown validation error",
                source_file=str(package_dir),
                target_file="",
            )
        )

    warnings = []
    for result in results:
        if isinstance(result, Success):
            warnings.extend(result.warnings)

    return Success(value=True, warnings=warnings)


def validate_all(
    repo_root: Path, package_filter: Optional[str] = None
) -> Result[ValidationReport, AggregateError]:
    """Validate all cross-references in the repository."""
    report = ValidationReport(total_checks=0, passed_checks=0, failed_checks=0)

    # Define paths
    packages_dir = repo_root / "packages"
    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    registry_path = repo_root / "docs" / "registries" / "nuget" / "registry.json"
    agent_registry_path = repo_root / ".claude" / "agents" / "registry.yaml"

    # Validate marketplace consistency
    if marketplace_path.exists():
        report.total_checks += 1
        result = validate_marketplace_consistency(marketplace_path, packages_dir)
        if isinstance(result, Success):
            report.passed_checks += 1
            report.warnings.extend(result.warnings)
        else:
            report.failed_checks += 1
            report.errors.append(result.error)

    # Validate registry consistency
    if registry_path.exists():
        report.total_checks += 1
        result = validate_registry_consistency(registry_path, packages_dir)
        if isinstance(result, Success):
            report.passed_checks += 1
            report.warnings.extend(result.warnings)
        else:
            report.failed_checks += 1
            report.errors.append(result.error)

    # Validate agent registry
    if agent_registry_path.exists():
        report.total_checks += 1
        result = validate_agent_registry(agent_registry_path, repo_root)
        if isinstance(result, Success):
            report.passed_checks += 1
            report.warnings.extend(result.warnings)
        else:
            report.failed_checks += 1
            report.errors.append(result.error)

    # Validate dependencies
    report.total_checks += 1
    result = validate_dependencies(packages_dir, registry_path)
    if isinstance(result, Success):
        report.passed_checks += 1
        report.warnings.extend(result.warnings)
    else:
        report.failed_checks += 1
        report.errors.append(result.error)

    # Validate individual packages
    for pkg_dir in packages_dir.iterdir():
        if not pkg_dir.is_dir():
            continue

        if package_filter and pkg_dir.name != package_filter:
            continue

        report.total_checks += 1
        result = validate_package(pkg_dir, repo_root)
        if isinstance(result, Success):
            report.passed_checks += 1
            report.warnings.extend(result.warnings)
        else:
            report.failed_checks += 1
            report.errors.append(result.error)

    if report.failed_checks > 0:
        return Failure(
            error=AggregateError(errors=report.errors),
            partial_result=report,
        )

    return Success(value=report, warnings=report.warnings)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate cross-references in the repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--package", help="Validate specific package only")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    # Get repo root
    repo_root = Path(__file__).parent.parent

    # Run validation
    result = validate_all(repo_root, args.package)

    # Print results
    if isinstance(result, Success):
        report = result.value
        print(f"\nValidation Results:")
        print(f"  Total checks: {report.total_checks}")
        print(f"  Passed: {report.passed_checks}")
        print(f"  Failed: {report.failed_checks}")

        if report.warnings and args.verbose:
            print(f"\nWarnings ({len(report.warnings)}):")
            for warning in report.warnings:
                print(f"  - {warning}")

        print("\n✓ All cross-references valid")
        return 0

    else:
        report = result.partial_result
        if report:
            print(f"\nValidation Results:")
            print(f"  Total checks: {report.total_checks}")
            print(f"  Passed: {report.passed_checks}")
            print(f"  Failed: {report.failed_checks}")

        print(f"\n✗ Cross-reference validation failed")
        print(f"\nErrors ({len(report.errors)}):")
        for error in report.errors:
            print(f"  - {error.message}")
            if args.verbose:
                print(f"    Source: {error.source_file}")
                if error.target_file:
                    print(f"    Target: {error.target_file}")
                if error.context:
                    print(f"    Context: {error.context}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
