#!/usr/bin/env python3
"""
Verify version consistency across packages and artifacts.

This script validates that:
- All commands have version frontmatter
- All skills have version frontmatter
- All agents have version frontmatter
- Artifact versions match package versions
- CHANGELOG files exist for versioned packages

Exit codes:
    0: All checks passed
    1: Mismatches or missing versions found
    2: Critical errors

Usage:
    python3 scripts/audit-versions.py [--verbose] [--fix-warnings]
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator

# Add test-packages/harness to path for Result imports
sys.path.insert(
    0, str(Path(__file__).parent.parent / "test-packages" / "harness")
)
from result import Failure, Result, Success


# ============================================================================
# Error Types
# ============================================================================


@dataclass
class AuditError:
    """Error during version audit."""

    message: str
    file_path: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class CheckResult:
    """Result of an individual check."""

    check_name: str
    status: str  # "PASS", "FAIL", "WARN"
    message: str = ""


@dataclass
class AuditData:
    """Results of version audit."""

    checks: list[CheckResult] = field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warnings: int = 0

    def add_check(self, check: CheckResult) -> None:
        """Add a check result and update counters."""
        self.checks.append(check)
        self.total_checks += 1

        if check.status == "PASS":
            self.passed_checks += 1
        elif check.status == "FAIL":
            self.failed_checks += 1
        elif check.status == "WARN":
            self.warnings += 1

    def is_valid(self) -> bool:
        """Check if audit passed (no failures)."""
        return self.failed_checks == 0


# ============================================================================
# Pydantic Models
# ============================================================================


class ManifestSchema(BaseModel):
    """Schema for manifest.yaml."""

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str
    author: str
    license: str

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate semantic version format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be X.Y.Z format")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Version parts must be numeric: {v}")
        return v


class VersionYamlSchema(BaseModel):
    """Schema for version.yaml."""

    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate semantic version format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be X.Y.Z format")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Version parts must be numeric: {v}")
        return v


# ============================================================================
# Version Extraction Functions
# ============================================================================


def extract_version_from_frontmatter(file_path: Path) -> Result[Optional[str], AuditError]:
    """
    Extract version from YAML frontmatter.

    Args:
        file_path: Path to file with YAML frontmatter

    Returns:
        Success with version string if found, None if not found, Failure on error
    """
    if not file_path.exists():
        return Failure(
            error=AuditError(
                message="File not found",
                file_path=str(file_path.as_posix()),
            )
        )

    try:
        with open(file_path) as f:
            content = f.read()

        # Look for YAML frontmatter (between --- markers)
        frontmatter_pattern = r"^---\s*\n(.*?)\n---"
        match = re.search(frontmatter_pattern, content, re.DOTALL | re.MULTILINE)

        if not match:
            return Success(value=None)

        frontmatter_text = match.group(1)

        # Parse YAML frontmatter
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if isinstance(frontmatter, dict) and "version" in frontmatter:
                version = str(frontmatter["version"])
                return Success(value=version)
            else:
                return Success(value=None)
        except yaml.YAMLError:
            return Success(value=None)

    except Exception as e:
        return Failure(
            error=AuditError(
                message=f"Error reading file: {e}",
                file_path=str(file_path.as_posix()),
            )
        )


def get_manifest_version(package_path: Path) -> Result[Optional[str], AuditError]:
    """
    Get version from package manifest.

    Args:
        package_path: Path to package directory

    Returns:
        Success with version string if found, None if manifest not found, Failure on error
    """
    manifest_path = package_path / "manifest.yaml"

    if not manifest_path.exists():
        return Success(value=None)

    try:
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        manifest = ManifestSchema(**data)
        return Success(value=manifest.version)

    except yaml.YAMLError as e:
        return Failure(
            error=AuditError(
                message=f"Invalid YAML: {e}",
                file_path=str(manifest_path.as_posix()),
            )
        )
    except Exception as e:
        return Failure(
            error=AuditError(
                message=f"Validation error: {e}",
                file_path=str(manifest_path.as_posix()),
            )
        )


# ============================================================================
# Audit Functions
# ============================================================================


def audit_commands(repo_root: Path, verbose: bool = False) -> Result[list[CheckResult], AuditError]:
    """
    Audit command version frontmatter.

    Args:
        repo_root: Path to repository root
        verbose: Enable verbose output

    Returns:
        Success with list of check results, Failure on critical error
    """
    checks = []
    command_files = list(repo_root.glob("packages/*/commands/*.md"))

    for cmd_file in command_files:
        cmd_name = cmd_file.stem
        version_result = extract_version_from_frontmatter(cmd_file)

        if isinstance(version_result, Failure):
            checks.append(
                CheckResult(
                    check_name=f"Command: {cmd_name}",
                    status="FAIL",
                    message=version_result.error.message,
                )
            )
        elif version_result.value is None:
            checks.append(
                CheckResult(
                    check_name=f"Command: {cmd_name}",
                    status="FAIL",
                    message="Missing version frontmatter",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_name=f"Command: {cmd_name} (v{version_result.value})",
                    status="PASS",
                )
            )

    return Success(value=checks)


def audit_skills(repo_root: Path, verbose: bool = False) -> Result[list[CheckResult], AuditError]:
    """
    Audit skill version frontmatter.

    Args:
        repo_root: Path to repository root
        verbose: Enable verbose output

    Returns:
        Success with list of check results, Failure on critical error
    """
    checks = []
    skill_files = list(repo_root.glob("packages/*/skills/*/SKILL.md"))

    for skill_file in skill_files:
        skill_name = skill_file.parent.name
        version_result = extract_version_from_frontmatter(skill_file)

        if isinstance(version_result, Failure):
            checks.append(
                CheckResult(
                    check_name=f"Skill: {skill_name}",
                    status="FAIL",
                    message=version_result.error.message,
                )
            )
        elif version_result.value is None:
            checks.append(
                CheckResult(
                    check_name=f"Skill: {skill_name}",
                    status="FAIL",
                    message="Missing version frontmatter",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_name=f"Skill: {skill_name} (v{version_result.value})",
                    status="PASS",
                )
            )

    return Success(value=checks)


def audit_agents(repo_root: Path, verbose: bool = False) -> Result[list[CheckResult], AuditError]:
    """
    Audit agent version frontmatter.

    Args:
        repo_root: Path to repository root
        verbose: Enable verbose output

    Returns:
        Success with list of check results, Failure on critical error
    """
    checks = []
    agent_files = list(repo_root.glob("packages/*/agents/*.md"))
    agent_files.extend(repo_root.glob(".claude/agents/*.md"))

    for agent_file in agent_files:
        agent_name = agent_file.stem
        version_result = extract_version_from_frontmatter(agent_file)

        if isinstance(version_result, Failure):
            checks.append(
                CheckResult(
                    check_name=f"Agent: {agent_name}",
                    status="FAIL",
                    message=version_result.error.message,
                )
            )
        elif version_result.value is None:
            checks.append(
                CheckResult(
                    check_name=f"Agent: {agent_name}",
                    status="FAIL",
                    message="Missing version frontmatter",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_name=f"Agent: {agent_name} (v{version_result.value})",
                    status="PASS",
                )
            )

    return Success(value=checks)


def audit_version_consistency(
    repo_root: Path, verbose: bool = False
) -> Result[list[CheckResult], AuditError]:
    """
    Audit that artifact versions match package versions.

    Args:
        repo_root: Path to repository root
        verbose: Enable verbose output

    Returns:
        Success with list of check results, Failure on critical error
    """
    checks = []
    packages_dir = repo_root / "packages"

    if not packages_dir.exists():
        return Failure(
            error=AuditError(
                message="Packages directory not found",
                file_path=str(packages_dir.as_posix()),
            )
        )

    for package_dir in packages_dir.iterdir():
        if not package_dir.is_dir() or package_dir.name.startswith("."):
            continue

        package_name = package_dir.name

        # Get package version
        version_result = get_manifest_version(package_dir)
        if isinstance(version_result, Failure):
            checks.append(
                CheckResult(
                    check_name=f"Package: {package_name}",
                    status="FAIL",
                    message=version_result.error.message,
                )
            )
            continue

        package_version = version_result.value
        if package_version is None:
            checks.append(
                CheckResult(
                    check_name=f"Package: {package_name}",
                    status="FAIL",
                    message="No manifest.yaml or version found",
                )
            )
            continue

        # Check commands
        for cmd_file in (package_dir / "commands").glob("*.md") if (package_dir / "commands").exists() else []:
            version_result = extract_version_from_frontmatter(cmd_file)
            if isinstance(version_result, Success) and version_result.value:
                cmd_version = version_result.value
                if cmd_version != package_version:
                    checks.append(
                        CheckResult(
                            check_name=f"Command in {package_name}",
                            status="FAIL",
                            message=f"Version mismatch: command={cmd_version}, package={package_version}",
                        )
                    )

        # Check skills
        for skill_file in (package_dir / "skills").glob("*/SKILL.md") if (package_dir / "skills").exists() else []:
            version_result = extract_version_from_frontmatter(skill_file)
            if isinstance(version_result, Success) and version_result.value:
                skill_version = version_result.value
                if skill_version != package_version:
                    checks.append(
                        CheckResult(
                            check_name=f"Skill in {package_name}",
                            status="FAIL",
                            message=f"Version mismatch: skill={skill_version}, package={package_version}",
                        )
                    )

        # Check agents
        for agent_file in (package_dir / "agents").glob("*.md") if (package_dir / "agents").exists() else []:
            version_result = extract_version_from_frontmatter(agent_file)
            if isinstance(version_result, Success) and version_result.value:
                agent_version = version_result.value
                if agent_version != package_version:
                    checks.append(
                        CheckResult(
                            check_name=f"Agent in {package_name}",
                            status="FAIL",
                            message=f"Version mismatch: agent={agent_version}, package={package_version}",
                        )
                    )

    return Success(value=checks)


def audit_changelogs(repo_root: Path, verbose: bool = False) -> Result[list[CheckResult], AuditError]:
    """
    Audit that CHANGELOG files exist for packages.

    Args:
        repo_root: Path to repository root
        verbose: Enable verbose output

    Returns:
        Success with list of check results, Failure on critical error
    """
    checks = []
    packages_dir = repo_root / "packages"

    if not packages_dir.exists():
        return Failure(
            error=AuditError(
                message="Packages directory not found",
                file_path=str(packages_dir.as_posix()),
            )
        )

    for package_dir in packages_dir.iterdir():
        if not package_dir.is_dir() or package_dir.name.startswith("."):
            continue

        package_name = package_dir.name
        changelog = package_dir / "CHANGELOG.md"

        if not changelog.exists():
            checks.append(
                CheckResult(
                    check_name=f"CHANGELOG for {package_name}",
                    status="WARN",
                    message="No CHANGELOG.md found",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_name=f"CHANGELOG for {package_name}",
                    status="PASS",
                )
            )

    return Success(value=checks)


def audit_marketplace_version(repo_root: Path, verbose: bool = False) -> Result[list[CheckResult], AuditError]:
    """
    Audit marketplace version from version.yaml.

    Args:
        repo_root: Path to repository root
        verbose: Enable verbose output

    Returns:
        Success with list of check results, Failure on critical error
    """
    checks = []
    version_file = repo_root / "version.yaml"

    if not version_file.exists():
        checks.append(
            CheckResult(
                check_name="Marketplace version",
                status="FAIL",
                message="version.yaml not found",
            )
        )
        return Success(value=checks)

    # version.yaml is plain YAML (not frontmatter), so parse directly
    try:
        with open(version_file) as f:
            data = yaml.safe_load(f)

        if isinstance(data, dict) and "version" in data:
            version = str(data["version"])
            checks.append(
                CheckResult(
                    check_name=f"Marketplace version (v{version})",
                    status="PASS",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_name="Marketplace version",
                    status="FAIL",
                    message="No version found in version.yaml",
                )
            )
    except yaml.YAMLError as e:
        checks.append(
            CheckResult(
                check_name="Marketplace version",
                status="FAIL",
                message=f"Invalid YAML: {e}",
            )
        )
    except Exception as e:
        checks.append(
            CheckResult(
                check_name="Marketplace version",
                status="FAIL",
                message=f"Error reading file: {e}",
            )
        )

    return Success(value=checks)


def audit_versions(repo_root: Path, verbose: bool = False) -> Result[AuditData, AuditError]:
    """
    Run complete version audit.

    Args:
        repo_root: Path to repository root
        verbose: Enable verbose output

    Returns:
        Success with audit data, Failure on critical error
    """
    audit_data = AuditData()
    warnings_list = []

    # Run all audit checks
    audit_funcs = [
        ("Checking commands...", audit_commands),
        ("Checking skills...", audit_skills),
        ("Checking agents...", audit_agents),
        ("Checking version consistency...", audit_version_consistency),
        ("Checking CHANGELOGs...", audit_changelogs),
        ("Checking marketplace version...", audit_marketplace_version),
    ]

    for section_name, audit_func in audit_funcs:
        if verbose:
            print(section_name)

        result = audit_func(repo_root, verbose)

        if isinstance(result, Failure):
            return result

        for check in result.value:
            audit_data.add_check(check)

    return Success(value=audit_data, warnings=warnings_list)


# ============================================================================
# CLI and Output
# ============================================================================


def print_check_result(check: CheckResult, verbose: bool = False) -> None:
    """
    Print a check result with colored output.

    Args:
        check: Check result to print
        verbose: Enable verbose output (print PASS checks)
    """
    # Color codes
    RED = "\033[0;31m"
    YELLOW = "\033[1;33m"
    GREEN = "\033[0;32m"
    NC = "\033[0m"  # No Color

    if check.status == "PASS":
        if verbose:
            print(f"{GREEN}✓{NC} {check.check_name}")
    elif check.status == "FAIL":
        if check.message:
            print(f"{RED}✗ FAIL{NC} {check.check_name}: {check.message}")
        else:
            print(f"{RED}✗ FAIL{NC} {check.check_name}")
    elif check.status == "WARN":
        if check.message:
            print(f"{YELLOW}⚠ WARN{NC} {check.check_name}: {check.message}")
        else:
            print(f"{YELLOW}⚠ WARN{NC} {check.check_name}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify version consistency across packages and artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run audit with minimal output:
    python3 scripts/audit-versions.py

  Run audit with verbose output:
    python3 scripts/audit-versions.py --verbose

  Run audit with auto-fix for warnings:
    python3 scripts/audit-versions.py --fix-warnings
""",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (show all checks)",
    )
    parser.add_argument(
        "--fix-warnings",
        action="store_true",
        help="Automatically fix warnings (not implemented yet)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to repository root (default: current directory)",
    )

    args = parser.parse_args()

    # Print header
    print("=== Synaptic Canvas Version Audit ===")
    print()

    # Run audit
    result = audit_versions(args.repo_root, verbose=args.verbose)

    if isinstance(result, Failure):
        print(f"✗ Critical error: {result.error.message}")
        if result.error.file_path:
            print(f"  File: {result.error.file_path}")
        return 2

    audit_data = result.value

    # Print individual check results
    for check in audit_data.checks:
        print_check_result(check, verbose=args.verbose)

    # Print summary
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"  # No Color

    print()
    print("=== Audit Results ===")
    print(f"Total checks: {audit_data.total_checks}")
    print(f"Passed: {GREEN}{audit_data.passed_checks}{NC}")
    print(f"Failed: {RED}{audit_data.failed_checks}{NC}")
    print(f"Warnings: {YELLOW}{audit_data.warnings}{NC}")
    print()

    if audit_data.is_valid():
        print(f"{GREEN}All checks passed!{NC}")
        return 0
    else:
        print(f"{RED}{audit_data.failed_checks} check(s) failed{NC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
