#!/usr/bin/env python3
"""
compare-versions.py - Compare version numbers across packages

Usage:
  python3 scripts/compare-versions.py [--by-package] [--mismatches] [--verbose]

Options:
  --by-package   Show versions grouped by package (default)
  --mismatches   Only show packages with version mismatches
  --verbose      Show all artifact versions individually
  --json         Output as JSON

Exit codes:
0 - All versions consistent
1 - Mismatches found
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Add test-packages/harness to path for Result types
sys.path.insert(0, str(Path(__file__).parent.parent / "test-packages" / "harness"))
from result import Failure, Result, Success, collect_results

try:
    import yaml  # type: ignore
except ImportError:
    print("Error: PyYAML not installed. Run: pip install PyYAML", file=sys.stderr)
    sys.exit(1)


# -----------------------------------------------------------------------------
# Error Types
# -----------------------------------------------------------------------------


@dataclass
class ComparisonError:
    """Error during version comparison."""

    message: str
    file_path: str = ""
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        """Format error as string."""
        if self.file_path:
            return f"{self.file_path}: {self.message}"
        return self.message


# -----------------------------------------------------------------------------
# Pydantic Models
# -----------------------------------------------------------------------------


class ArtifactVersion(BaseModel):
    """Version information for an artifact."""

    artifact_type: str = Field(..., description="Type: command, skill, or agent")
    name: str = Field(..., description="Artifact name")
    version: str = Field(..., description="Version string")
    file_path: str = Field(..., description="Path to the artifact file")

    model_config = {"extra": "forbid"}


class PackageComparison(BaseModel):
    """Version comparison for a package."""

    package_name: str = Field(..., description="Package name")
    manifest_version: str = Field(..., description="Version from manifest.yaml")
    artifacts: List[ArtifactVersion] = Field(
        default_factory=list, description="List of artifact versions"
    )
    has_mismatches: bool = Field(
        default=False, description="Whether version mismatches exist"
    )

    model_config = {"extra": "forbid"}


class ComparisonData(BaseModel):
    """Complete version comparison data."""

    marketplace_version: str = Field(..., description="Marketplace platform version")
    packages: List[PackageComparison] = Field(
        default_factory=list, description="Package comparison results"
    )
    overall_consistent: bool = Field(
        default=True, description="Whether all versions are consistent"
    )

    model_config = {"extra": "forbid"}


# -----------------------------------------------------------------------------
# Version Extraction Functions
# -----------------------------------------------------------------------------


def extract_version_from_file(file_path: Path) -> Result[str, ComparisonError]:
    """
    Extract version from YAML frontmatter or manifest.

    Args:
        file_path: Path to the file to read

    Returns:
        Success with version string, or Failure with error
    """
    if not file_path.exists():
        return Failure(
            error=ComparisonError(
                message="File does not exist", file_path=str(file_path)
            )
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Try YAML parsing first
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and "version" in data:
                version = str(data["version"]).strip()
                return Success(value=version)
        except yaml.YAMLError:
            pass

        # Fall back to regex extraction for markdown files with frontmatter
        for line in content.split("\n"):
            if line.strip().startswith("version:"):
                # Extract version after colon
                parts = line.split(":", 1)
                if len(parts) == 2:
                    version = parts[1].strip().strip('"').strip("'")
                    return Success(value=version)

        return Failure(
            error=ComparisonError(
                message="No version field found", file_path=str(file_path)
            )
        )

    except Exception as e:
        return Failure(
            error=ComparisonError(
                message=f"Failed to read file: {e}", file_path=str(file_path)
            )
        )


def get_marketplace_version(repo_root: Path) -> Result[str, ComparisonError]:
    """
    Get marketplace platform version from version.yaml.

    Args:
        repo_root: Repository root path

    Returns:
        Success with version string, or Failure with error
    """
    version_file = repo_root / "version.yaml"
    return extract_version_from_file(version_file)


# -----------------------------------------------------------------------------
# Package Comparison Functions
# -----------------------------------------------------------------------------


def compare_package_versions(
    package_name: str, repo_root: Path
) -> Result[PackageComparison, ComparisonError]:
    """
    Compare versions within a package.

    Args:
        package_name: Name of the package
        repo_root: Repository root path

    Returns:
        Success with PackageComparison, or Failure with error
    """
    package_dir = repo_root / "packages" / package_name

    if not package_dir.exists():
        return Failure(
            error=ComparisonError(
                message=f"Package directory does not exist: {package_name}",
                file_path=str(package_dir),
            )
        )

    # Get manifest version
    manifest_path = package_dir / "manifest.yaml"
    manifest_result = extract_version_from_file(manifest_path)

    if isinstance(manifest_result, Failure):
        return Failure(
            error=ComparisonError(
                message=f"Failed to read manifest version: {manifest_result.error.message}",
                file_path=str(manifest_path),
            )
        )

    manifest_version = manifest_result.value
    artifacts: List[ArtifactVersion] = []
    warnings: List[str] = []

    # Check commands
    commands_dir = package_dir / "commands"
    if commands_dir.exists():
        for cmd_file in commands_dir.glob("*.md"):
            version_result = extract_version_from_file(cmd_file)
            if isinstance(version_result, Success):
                artifacts.append(
                    ArtifactVersion(
                        artifact_type="command",
                        name=cmd_file.stem,
                        version=version_result.value,
                        file_path=cmd_file.as_posix(),
                    )
                )
            else:
                warnings.append(
                    f"Could not extract version from command: {cmd_file.name}"
                )

    # Check skills
    skills_dir = package_dir / "skills"
    if skills_dir.exists():
        for skill_file in skills_dir.glob("*/SKILL.md"):
            version_result = extract_version_from_file(skill_file)
            if isinstance(version_result, Success):
                artifacts.append(
                    ArtifactVersion(
                        artifact_type="skill",
                        name=skill_file.parent.name,
                        version=version_result.value,
                        file_path=skill_file.as_posix(),
                    )
                )
            else:
                warnings.append(
                    f"Could not extract version from skill: {skill_file.parent.name}"
                )

    # Check agents
    agents_dir = package_dir / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            version_result = extract_version_from_file(agent_file)
            if isinstance(version_result, Success):
                artifacts.append(
                    ArtifactVersion(
                        artifact_type="agent",
                        name=agent_file.stem,
                        version=version_result.value,
                        file_path=agent_file.as_posix(),
                    )
                )
            else:
                warnings.append(
                    f"Could not extract version from agent: {agent_file.name}"
                )

    # Determine if there are mismatches
    has_mismatches = any(
        artifact.version != manifest_version for artifact in artifacts
    )

    comparison = PackageComparison(
        package_name=package_name,
        manifest_version=manifest_version,
        artifacts=artifacts,
        has_mismatches=has_mismatches,
    )

    return Success(value=comparison, warnings=warnings)


def compare_all_packages(repo_root: Path) -> Result[ComparisonData, ComparisonError]:
    """
    Compare versions across all packages.

    Args:
        repo_root: Repository root path

    Returns:
        Success with ComparisonData, or Failure with error
    """
    # Get marketplace version
    marketplace_result = get_marketplace_version(repo_root)
    if isinstance(marketplace_result, Failure):
        return Failure(
            error=ComparisonError(
                message=f"Failed to read marketplace version: {marketplace_result.error.message}"
            )
        )

    marketplace_version = marketplace_result.value
    packages_dir = repo_root / "packages"

    if not packages_dir.exists():
        return Failure(
            error=ComparisonError(
                message="Packages directory does not exist",
                file_path=str(packages_dir),
            )
        )

    # Compare each package
    package_results: List[Result[PackageComparison, ComparisonError]] = []
    for package_dir in sorted(packages_dir.iterdir()):
        if not package_dir.is_dir() or package_dir.name == "shared":
            continue
        result = compare_package_versions(package_dir.name, repo_root)
        package_results.append(result)

    # Collect results
    collected = collect_results(package_results)

    if isinstance(collected, Failure):
        # Even with failures, we might have partial results
        packages = collected.partial_result or []
        return Failure(
            error=ComparisonError(
                message="Failed to compare some packages",
                details={"errors": [str(e) for e in collected.error.errors]},
            ),
            partial_result=packages,
        )

    packages = collected.value
    warnings = collected.warnings

    # Determine overall consistency
    overall_consistent = not any(pkg.has_mismatches for pkg in packages)

    data = ComparisonData(
        marketplace_version=marketplace_version,
        packages=packages,
        overall_consistent=overall_consistent,
    )

    return Success(value=data, warnings=warnings)


# -----------------------------------------------------------------------------
# Output Functions
# -----------------------------------------------------------------------------


def format_color(text: str, color: str) -> str:
    """
    Format text with ANSI color codes.

    Args:
        text: Text to colorize
        color: Color name (red, green, yellow, blue)

    Returns:
        Colorized text
    """
    colors = {
        "red": "\033[0;31m",
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "blue": "\033[0;34m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def output_text(
    data: ComparisonData, show_mismatches_only: bool = False, verbose: bool = False
) -> None:
    """
    Output comparison results as formatted text.

    Args:
        data: Comparison data to output
        show_mismatches_only: Only show packages with mismatches
        verbose: Show all artifact versions individually
    """
    print("=== Synaptic Canvas Version Comparison ===")
    print()
    print(f"Marketplace Version: {data.marketplace_version}")
    print()

    for package in data.packages:
        if show_mismatches_only and not package.has_mismatches:
            continue

        if package.has_mismatches:
            header = format_color(
                f"Package: {package.package_name} (manifest: {package.manifest_version})",
                "red",
            )
        else:
            header = format_color(
                f"Package: {package.package_name} (manifest: {package.manifest_version})",
                "green",
            )

        print(header)

        if verbose:
            for artifact in package.artifacts:
                if artifact.version != package.manifest_version:
                    marker = format_color("✗", "red")
                    print(
                        f"  {marker} {artifact.artifact_type}/{artifact.name}: {artifact.version}"
                    )
                else:
                    marker = format_color("✓", "green")
                    print(
                        f"  {marker} {artifact.artifact_type}/{artifact.name}: {artifact.version}"
                    )

        print()

    if data.overall_consistent:
        print(format_color("All versions consistent!", "green"))
    else:
        print(format_color("Version mismatches found", "red"))


def output_json(data: ComparisonData) -> None:
    """
    Output comparison results as JSON.

    Args:
        data: Comparison data to output
    """
    # Convert to dict for JSON serialization
    output_data = {
        "marketplace": data.marketplace_version,
        "packages": [
            {
                "name": pkg.package_name,
                "version": pkg.manifest_version,
                "consistent": not pkg.has_mismatches,
            }
            for pkg in data.packages
        ],
    }
    print(json.dumps(output_data, indent=2))


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for mismatches or errors)
    """
    parser = argparse.ArgumentParser(
        description="Compare version numbers across packages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--by-package",
        action="store_true",
        help="Show versions grouped by package (default)",
    )
    parser.add_argument(
        "--mismatches", action="store_true", help="Only show packages with mismatches"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show all artifact versions individually",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Find repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Compare all packages
    result = compare_all_packages(repo_root)

    if isinstance(result, Failure):
        print(f"Error: {result.error}", file=sys.stderr)
        # If we have partial results, still output them
        if result.partial_result and isinstance(result.partial_result, list):
            data = ComparisonData(
                marketplace_version="unknown",
                packages=result.partial_result,
                overall_consistent=False,
            )
            if args.json:
                output_json(data)
            else:
                output_text(data, args.mismatches, args.verbose)
        return 1

    data = result.value

    # Output results
    if args.json:
        output_json(data)
    else:
        output_text(data, args.mismatches, args.verbose)

    # Return exit code based on consistency
    return 0 if data.overall_consistent else 1


if __name__ == "__main__":
    sys.exit(main())
