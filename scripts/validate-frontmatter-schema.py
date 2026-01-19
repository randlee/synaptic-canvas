#!/usr/bin/env python3
"""
validate-frontmatter-schema.py - Validate frontmatter in commands/skills/agents

Usage:
  python3 scripts/validate-frontmatter-schema.py [--package <name>] [--path <path>]

Options:
  --package NAME    Validate specific package only
  --path PATH       Validate specific file or directory
  --verbose         Show detailed validation output
  --json            Output results as JSON

Exit Codes:
  0: All frontmatter valid
  1: Schema violations found

Validates:
  - All commands/skills/agents have complete frontmatter
  - Required fields: name, version, description
  - Field types are correct
  - Values are valid (e.g., model in [sonnet, opus, haiku])
  - Frontmatter matches unified schema
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationError as PydanticValidationError

# Add test-packages/harness to path for Result types
sys.path.insert(0, str(Path(__file__).parent.parent / "test-packages" / "harness"))
from result import Result, Success, Failure, collect_results

try:
    import yaml  # type: ignore
except ImportError:
    print("Error: PyYAML not installed. Run: pip install PyYAML", file=sys.stderr)
    sys.exit(1)


# -----------------------------------------------------------------------------
# Error Types
# -----------------------------------------------------------------------------


@dataclass
class FrontmatterValidationError:
    """Represents a frontmatter validation error."""

    message: str
    file_path: str
    line_number: Optional[int] = None
    field_name: Optional[str] = None
    severity: str = "error"  # "error" or "warning"

    def __str__(self) -> str:
        """Format error as string."""
        location = f"{self.file_path}"
        if self.line_number:
            location += f":{self.line_number}"
        if self.field_name:
            location += f" ({self.field_name})"
        return f"{self.severity.upper()}: {location}: {self.message}"


# -----------------------------------------------------------------------------
# Pydantic Models for Frontmatter Schema
# -----------------------------------------------------------------------------


class BaseFrontmatter(BaseModel):
    """Base frontmatter fields common to all types."""

    name: str = Field(..., description="Name in kebab-case")
    version: str = Field(..., description="Semantic version X.Y.Z")
    description: str = Field(..., description="Description of the artifact")

    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def validate_kebab_case(cls, v: str) -> str:
        """Validate name is in kebab-case."""
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", v):
            raise ValueError(f"Name must be kebab-case: {v}")
        return v

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate semantic version format."""
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Version must be SemVer (X.Y.Z): {v}")
        return v


class CommandFrontmatter(BaseFrontmatter):
    """Frontmatter schema for commands."""

    options: Optional[List[str]] = Field(default=None, description="Command options")


class SkillFrontmatter(BaseFrontmatter):
    """Frontmatter schema for skills."""

    entry_point: str = Field(..., description="Entry point starting with /")

    @field_validator("entry_point")
    @classmethod
    def validate_entry_point(cls, v: str) -> str:
        """Validate entry point starts with /."""
        if not v.startswith("/"):
            raise ValueError(f"Entry point must start with /: {v}")
        return v


class AgentFrontmatter(BaseFrontmatter):
    """Frontmatter schema for agents."""

    model: str = Field(..., description="Model: sonnet, opus, or haiku")
    color: str = Field(..., description="Color: gray, green, purple, blue, red, or yellow")

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model is one of allowed values."""
        allowed = {"sonnet", "opus", "haiku"}
        if v not in allowed:
            raise ValueError(f"Model must be one of {allowed}: {v}")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate color is one of allowed values."""
        allowed = {"gray", "green", "purple", "blue", "red", "yellow"}
        if v not in allowed:
            raise ValueError(f"Color must be one of {allowed}: {v}")
        return v


# -----------------------------------------------------------------------------
# Frontmatter Data Container
# -----------------------------------------------------------------------------


@dataclass
class FrontmatterData:
    """Container for validated frontmatter."""

    file_path: str
    artifact_type: str  # "command", "skill", or "agent"
    data: Dict[str, Any]
    raw_frontmatter: str


# -----------------------------------------------------------------------------
# Frontmatter Extraction and Validation
# -----------------------------------------------------------------------------


def extract_frontmatter(file_path: str) -> Result[FrontmatterData, FrontmatterValidationError]:
    """
    Extract YAML frontmatter from markdown file.

    Args:
        file_path: Path to the markdown file

    Returns:
        Success with FrontmatterData if valid, Failure with FrontmatterValidationError otherwise
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return Failure(
            error=FrontmatterValidationError(
                message=f"Failed to read file: {e}",
                file_path=file_path,
            )
        )

    # Extract frontmatter between --- markers
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return Failure(
            error=FrontmatterValidationError(
                message="No frontmatter found (expected YAML between --- markers)",
                file_path=file_path,
                line_number=1,
            )
        )

    raw_frontmatter = match.group(1)

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError as e:
        return Failure(
            error=FrontmatterValidationError(
                message=f"Invalid YAML in frontmatter: {e}",
                file_path=file_path,
                line_number=getattr(e, "problem_mark", None).line + 1 if hasattr(e, "problem_mark") else None,
            )
        )

    if not isinstance(frontmatter, dict):
        return Failure(
            error=FrontmatterValidationError(
                message="Frontmatter must be a YAML object/dict",
                file_path=file_path,
            )
        )

    # Determine artifact type from file path
    artifact_type = determine_artifact_type(file_path)

    return Success(
        value=FrontmatterData(
            file_path=file_path,
            artifact_type=artifact_type,
            data=frontmatter,
            raw_frontmatter=raw_frontmatter,
        ),
        warnings=[],
    )


def determine_artifact_type(file_path: str) -> str:
    """
    Determine artifact type from file path.

    Args:
        file_path: Path to the file

    Returns:
        "command", "skill", or "agent"
    """
    path_parts = Path(file_path).parts
    if "commands" in path_parts:
        return "command"
    elif "skills" in path_parts:
        return "skill"
    elif "agents" in path_parts:
        return "agent"
    else:
        return "unknown"


def validate_frontmatter_schema(data: FrontmatterData) -> Result[FrontmatterData, FrontmatterValidationError]:
    """
    Validate frontmatter against schema based on artifact type.

    Args:
        data: Extracted frontmatter data

    Returns:
        Success with FrontmatterData if valid, Failure with FrontmatterValidationError otherwise
    """
    # Select appropriate schema
    schema_map = {
        "command": CommandFrontmatter,
        "skill": SkillFrontmatter,
        "agent": AgentFrontmatter,
    }

    schema = schema_map.get(data.artifact_type)
    if schema is None:
        return Failure(
            error=FrontmatterValidationError(
                message=f"Unknown artifact type: {data.artifact_type}",
                file_path=data.file_path,
            )
        )

    # Validate against Pydantic model
    try:
        schema(**data.data)
    except PydanticValidationError as e:
        # Extract first error for clarity
        first_error = e.errors()[0]
        field_name = ".".join(str(loc) for loc in first_error["loc"])
        message = first_error["msg"]

        return Failure(
            error=FrontmatterValidationError(
                message=message,
                file_path=data.file_path,
                field_name=field_name,
            )
        )

    return Success(value=data, warnings=[])


def validate_file(file_path: str) -> Result[FrontmatterData, FrontmatterValidationError]:
    """
    Complete validation pipeline for a single file.

    Args:
        file_path: Path to the markdown file

    Returns:
        Success with FrontmatterData if valid, Failure with FrontmatterValidationError otherwise
    """
    # Step 1: Extract frontmatter
    result = extract_frontmatter(file_path)
    if isinstance(result, Failure):
        return result

    # Step 2: Validate schema
    return validate_frontmatter_schema(result.value)


# -----------------------------------------------------------------------------
# File Discovery
# -----------------------------------------------------------------------------


def find_markdown_files(base_path: str, package_name: Optional[str] = None) -> List[str]:
    """
    Find all markdown files in commands/skills/agents directories.

    Args:
        base_path: Root path to search from
        package_name: Optional package name to filter by

    Returns:
        List of file paths
    """
    base = Path(base_path)
    packages_dir = base / "packages"

    if not packages_dir.exists():
        return []

    files = []

    # Determine which packages to scan
    if package_name:
        package_dirs = [packages_dir / package_name]
    else:
        package_dirs = [p for p in packages_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]

    # Scan each package for commands/skills/agents
    for package_dir in package_dirs:
        if not package_dir.exists():
            continue

        # Commands
        commands_dir = package_dir / "commands"
        if commands_dir.exists():
            files.extend(str(f) for f in commands_dir.glob("*.md"))

        # Skills
        skills_dir = package_dir / "skills"
        if skills_dir.exists():
            files.extend(str(f) for f in skills_dir.rglob("SKILL.md"))

        # Agents (only .md files, not .py)
        agents_dir = package_dir / "agents"
        if agents_dir.exists():
            files.extend(str(f) for f in agents_dir.glob("*.md"))

    return sorted(files)


# -----------------------------------------------------------------------------
# Main Validation Logic
# -----------------------------------------------------------------------------


def validate_all(
    base_path: str,
    package_name: Optional[str] = None,
    specific_path: Optional[str] = None,
) -> Result[List[FrontmatterData], List[FrontmatterValidationError]]:
    """
    Validate all frontmatter in the repository.

    Args:
        base_path: Root path of the repository
        package_name: Optional package name to filter by
        specific_path: Optional specific file or directory to validate

    Returns:
        Success with list of validated frontmatter, or Failure with list of errors
    """
    # Determine files to validate
    if specific_path:
        specific = Path(specific_path)
        if specific.is_file():
            files = [str(specific)]
        elif specific.is_dir():
            files = find_markdown_files(str(specific), package_name)
        else:
            return Failure(error=[FrontmatterValidationError(
                message=f"Path does not exist: {specific_path}",
                file_path=specific_path,
            )])
    else:
        files = find_markdown_files(base_path, package_name)

    if not files:
        return Success(value=[], warnings=["No markdown files found to validate"])

    # Validate each file
    results = [validate_file(f) for f in files]

    # Collect results
    collected = collect_results(results)

    if isinstance(collected, Failure):
        # Extract individual errors from AggregateError
        errors = collected.error.errors if hasattr(collected.error, "errors") else [collected.error]
        return Failure(error=errors)

    return Success(value=collected.value, warnings=collected.warnings)


# -----------------------------------------------------------------------------
# CLI Interface
# -----------------------------------------------------------------------------


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate frontmatter schema in commands/skills/agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--package", help="Validate specific package only")
    parser.add_argument("--path", help="Validate specific file or directory")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Determine repository root
    repo_root = Path(__file__).parent.parent
    if not (repo_root / "packages").exists():
        print(f"Error: packages directory not found in {repo_root}", file=sys.stderr)
        return 1

    # Run validation
    result = validate_all(
        base_path=str(repo_root),
        package_name=args.package,
        specific_path=args.path,
    )

    # Output results
    if args.json:
        output_json(result)
    else:
        output_text(result, verbose=args.verbose)

    # Return exit code
    return 0 if isinstance(result, Success) else 1


def output_json(result: Result[List[FrontmatterData], List[FrontmatterValidationError]]) -> None:
    """Output results as JSON."""
    if isinstance(result, Success):
        output = {
            "status": "success",
            "files_validated": len(result.value),
            "warnings": result.warnings,
        }
    else:
        output = {
            "status": "failure",
            "errors": [
                {
                    "file": err.file_path,
                    "message": err.message,
                    "line": err.line_number,
                    "field": err.field_name,
                    "severity": err.severity,
                }
                for err in result.error
            ],
        }

    print(json.dumps(output, indent=2))


def output_text(result: Result[List[FrontmatterData], List[FrontmatterValidationError]], verbose: bool = False) -> None:
    """Output results as human-readable text."""
    if isinstance(result, Success):
        print(f"✓ Validated {len(result.value)} files successfully")
        if result.warnings:
            for warning in result.warnings:
                print(f"  Warning: {warning}")
        if verbose and result.value:
            print("\nValidated files:")
            for data in result.value:
                print(f"  - {data.file_path} ({data.artifact_type})")
    else:
        print(f"✗ Validation failed with {len(result.error)} errors:", file=sys.stderr)
        for error in result.error:
            print(f"  {error}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
