#!/usr/bin/env python3
"""
Validate manifest artifacts and file existence.

This script validates that:
- All files listed in manifest.yaml artifacts exist on disk
- All actual files in commands/skills/agents/scripts are in manifest
- Reports orphaned files (exist but not in manifest)
- Reports missing files (in manifest but don't exist)
- All scripts in manifest are Python (.py extension)
- Scripts have proper shebang (#!/usr/bin/env python3)

Exit codes:
    0: All checks passed
    1: Missing or orphaned files found

Usage:
    python3 scripts/validate-manifest-artifacts.py [--package <name>] [--verbose]
"""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

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
class ValidationError:
    """Error during validation."""

    message: str
    file_path: str
    line_number: Optional[int] = None
    details: dict = field(default_factory=dict)


@dataclass
class ManifestValidationResult:
    """Results of manifest artifact validation."""

    package_name: str
    missing_files: list[str] = field(default_factory=list)
    orphaned_files: list[str] = field(default_factory=list)
    invalid_scripts: list[str] = field(default_factory=list)
    missing_shebangs: list[str] = field(default_factory=list)
    total_artifacts: int = 0
    total_disk_files: int = 0

    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return not (
            self.missing_files
            or self.orphaned_files
            or self.invalid_scripts
            or self.missing_shebangs
        )

    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"\nValidation Results for {self.package_name}:",
            f"  Manifest artifacts: {self.total_artifacts}",
            f"  Files on disk: {self.total_disk_files}",
        ]

        if self.missing_files:
            lines.append(f"\n  Missing files ({len(self.missing_files)}):")
            for f in self.missing_files:
                lines.append(f"    - {f}")

        if self.orphaned_files:
            lines.append(f"\n  Orphaned files ({len(self.orphaned_files)}):")
            for f in self.orphaned_files:
                lines.append(f"    - {f}")

        if self.invalid_scripts:
            lines.append(f"\n  Invalid scripts ({len(self.invalid_scripts)}):")
            for f in self.invalid_scripts:
                lines.append(f"    - {f}")

        if self.missing_shebangs:
            lines.append(f"\n  Missing shebangs ({len(self.missing_shebangs)}):")
            for f in self.missing_shebangs:
                lines.append(f"    - {f}")

        if self.is_valid():
            lines.append("\n  Status: PASS ✓")
        else:
            lines.append("\n  Status: FAIL ✗")

        return "\n".join(lines)


# ============================================================================
# Pydantic Models
# ============================================================================


class ManifestArtifacts(BaseModel):
    """Artifacts section of manifest.yaml."""

    commands: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list)

    def all_files(self) -> list[str]:
        """Get all artifact files."""
        return self.commands + self.skills + self.agents + self.scripts


class ManifestSchema(BaseModel):
    """Schema for manifest.yaml."""

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str
    author: str
    license: str
    tags: list[str] = Field(default_factory=list)
    artifacts: ManifestArtifacts
    requires: Optional[Union[dict, list]] = None  # Can be list or dict with packages/cli keys

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v):
        """Validate semantic version format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be X.Y.Z format")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Version parts must be numeric: {v}")
        return v


# ============================================================================
# Validation Functions
# ============================================================================


def load_manifest(package_path: Path) -> Result[ManifestSchema, ValidationError]:
    """
    Load and validate manifest.yaml.

    Args:
        package_path: Path to package directory

    Returns:
        Success with ManifestSchema if valid, Failure otherwise
    """
    manifest_path = package_path / "manifest.yaml"

    if not manifest_path.exists():
        return Failure(
            error=ValidationError(
                message="manifest.yaml not found",
                file_path=str(manifest_path),
            )
        )

    try:
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        manifest = ManifestSchema(**data)
        return Success(value=manifest)

    except yaml.YAMLError as e:
        return Failure(
            error=ValidationError(
                message=f"Invalid YAML: {e}",
                file_path=str(manifest_path),
            )
        )
    except Exception as e:
        return Failure(
            error=ValidationError(
                message=f"Validation error: {e}",
                file_path=str(manifest_path),
            )
        )


def get_disk_files(package_path: Path) -> list[str]:
    """
    Get all artifact files from disk.

    Args:
        package_path: Path to package directory

    Returns:
        List of relative file paths (normalized to forward slashes)
    """
    disk_files = []
    artifact_dirs = ["commands", "skills", "agents", "scripts"]

    for dir_name in artifact_dirs:
        dir_path = package_path / dir_name
        if not dir_path.exists():
            continue

        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                # Get path relative to package root
                rel_path = file_path.relative_to(package_path)
                # Normalize to forward slashes for cross-platform compatibility
                disk_files.append(rel_path.as_posix())

    return disk_files


def validate_script_file(
    package_path: Path, script_path: str
) -> Result[bool, ValidationError]:
    """
    Validate a script file.

    Args:
        package_path: Path to package directory
        script_path: Relative path to script file

    Returns:
        Success if valid, Failure with error details otherwise
    """
    warnings = []

    # Check extension
    if not script_path.endswith(".py"):
        return Failure(
            error=ValidationError(
                message="Script must have .py extension",
                file_path=script_path,
            )
        )

    # Check shebang
    full_path = package_path / script_path
    try:
        with open(full_path) as f:
            first_line = f.readline().strip()

        expected_shebang = "#!/usr/bin/env python3"
        if not first_line.startswith("#!"):
            return Failure(
                error=ValidationError(
                    message="Script missing shebang",
                    file_path=script_path,
                    details={"expected": expected_shebang},
                )
            )

        if first_line != expected_shebang:
            warnings.append(
                f"Non-standard shebang in {script_path}: {first_line} "
                f"(expected: {expected_shebang})"
            )

    except Exception as e:
        return Failure(
            error=ValidationError(
                message=f"Error reading script: {e}",
                file_path=script_path,
            )
        )

    return Success(value=True, warnings=warnings)


def validate_manifest_artifacts(
    package_path: Path, verbose: bool = False
) -> Result[ManifestValidationResult, ValidationError]:
    """
    Validate manifest artifacts against disk files.

    Args:
        package_path: Path to package directory
        verbose: Enable verbose output

    Returns:
        Success with validation results, or Failure with error
    """
    warnings = []

    # Load manifest
    manifest_result = load_manifest(package_path)
    if isinstance(manifest_result, Failure):
        return manifest_result

    manifest = manifest_result.value
    result = ManifestValidationResult(package_name=manifest.name)

    # Get manifest artifacts
    manifest_files = set(manifest.artifacts.all_files())
    result.total_artifacts = len(manifest_files)

    # Get disk files
    disk_files = set(get_disk_files(package_path))
    result.total_disk_files = len(disk_files)

    # Find missing files (in manifest but not on disk)
    result.missing_files = sorted(list(manifest_files - disk_files))

    # Find orphaned files (on disk but not in manifest)
    result.orphaned_files = sorted(list(disk_files - manifest_files))

    # Validate script files
    for script_path in manifest.artifacts.scripts:
        validation = validate_script_file(package_path, script_path)

        if isinstance(validation, Failure):
            error = validation.error
            if "extension" in error.message.lower():
                result.invalid_scripts.append(script_path)
            elif "shebang" in error.message.lower():
                result.missing_shebangs.append(script_path)

        elif isinstance(validation, Success):
            warnings.extend(validation.warnings)

    if verbose:
        print(result.get_summary())

    return Success(value=result, warnings=warnings)


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate manifest artifacts and file existence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Validate all packages:
    python3 scripts/validate-manifest-artifacts.py

  Validate specific package:
    python3 scripts/validate-manifest-artifacts.py --package sc-ci-automation

  Verbose output:
    python3 scripts/validate-manifest-artifacts.py --verbose
""",
    )

    parser.add_argument(
        "--package",
        type=str,
        help="Specific package name to validate (default: all packages)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--packages-dir",
        type=Path,
        default=Path("packages"),
        help="Path to packages directory (default: packages)",
    )

    args = parser.parse_args()

    # Determine packages to validate
    if args.package:
        package_dirs = [args.packages_dir / args.package]
    else:
        if not args.packages_dir.exists():
            print(f"Error: Packages directory not found: {args.packages_dir}")
            return 1

        package_dirs = [
            d for d in args.packages_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

    if not package_dirs:
        print("Error: No packages found to validate")
        return 1

    # Validate each package
    all_valid = True
    all_warnings = []

    for package_dir in sorted(package_dirs):
        if args.verbose:
            print(f"\n{'=' * 70}")
            print(f"Validating: {package_dir.name}")
            print(f"{'=' * 70}")

        result = validate_manifest_artifacts(package_dir, verbose=args.verbose)

        if isinstance(result, Failure):
            print(f"\n✗ Error validating {package_dir.name}:")
            print(f"  {result.error.message}")
            print(f"  File: {result.error.file_path}")
            all_valid = False
            continue

        validation_result = result.value
        all_warnings.extend(result.warnings)

        if not args.verbose:
            if validation_result.is_valid():
                print(f"✓ {package_dir.name}: PASS")
            else:
                print(f"✗ {package_dir.name}: FAIL")
                print(validation_result.get_summary())

        if not validation_result.is_valid():
            all_valid = False

    # Print warnings if any
    if all_warnings and args.verbose:
        print(f"\n{'=' * 70}")
        print("Warnings:")
        print(f"{'=' * 70}")
        for warning in all_warnings:
            print(f"  {warning}")

    # Summary
    print(f"\n{'=' * 70}")
    if all_valid:
        print("All validations PASSED ✓")
    else:
        print("Some validations FAILED ✗")
    print(f"{'=' * 70}")

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
