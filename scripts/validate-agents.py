#!/usr/bin/env python3
"""
validate-agents.py - Validate agent frontmatter versions match registry

Usage:
  python3 scripts/validate-agents.py [--registry <path>] [--verbose]

Options:
  --registry PATH   Path to registry.yaml (default: .claude/agents/registry.yaml)
  --verbose         Show detailed validation output
  --json            Output results as JSON

Exit Codes:
  0: All agent versions validated
  1: Version mismatches or validation errors found

Validates:
  - Agent frontmatter versions match registry.yaml versions
  - All agents in registry have corresponding .md files
  - Skill dependencies reference valid agents with correct version constraints
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationError as PydanticValidationError

# Add test-packages/harness to path for Result types
sys.path.insert(0, str(Path(__file__).parent.parent / "test-packages" / "harness"))
from result import Result, Success, Failure, collect_results, AggregateError

try:
    import yaml  # type: ignore
except ImportError:
    print("Error: PyYAML not installed. Run: pip install PyYAML", file=sys.stderr)
    sys.exit(1)


# -----------------------------------------------------------------------------
# Error Types
# -----------------------------------------------------------------------------


@dataclass
class AgentValidationError:
    """Represents an agent validation error."""

    message: str
    file_path: str = ""
    agent_name: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "error"  # "error" or "warning"

    def __str__(self) -> str:
        """Format error as string."""
        parts = [f"{self.severity.upper()}"]
        if self.agent_name:
            parts.append(f"[{self.agent_name}]")
        if self.file_path:
            parts.append(f"({self.file_path})")
        parts.append(self.message)
        return ": ".join(parts)


# -----------------------------------------------------------------------------
# Pydantic Models
# -----------------------------------------------------------------------------


class AgentRegistryEntry(BaseModel):
    """Schema for agent entry in registry."""

    version: str = Field(..., description="Semantic version X.Y.Z")
    path: str = Field(..., description="Path to agent markdown file")

    model_config = {"extra": "forbid"}

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate semantic version format."""
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Version must be SemVer (X.Y.Z): {v}")
        return v


class SkillDependency(BaseModel):
    """Schema for skill dependency constraints."""

    depends_on: Dict[str, str] = Field(
        default_factory=dict, description="Map of agent/skill name to version constraint"
    )
    entry_point: Optional[str] = Field(default=None, description="Skill entry point")

    model_config = {"extra": "forbid"}


class AgentRegistry(BaseModel):
    """Schema for agent registry.yaml."""

    agents: Dict[str, AgentRegistryEntry] = Field(
        default_factory=dict, description="Map of agent names to registry entries"
    )
    skills: Optional[Dict[str, SkillDependency]] = Field(
        default=None, description="Optional skill dependency constraints"
    )

    model_config = {"extra": "forbid"}


class AgentFrontmatter(BaseModel):
    """Schema for agent frontmatter in markdown files."""

    name: str = Field(..., description="Agent name in kebab-case")
    version: str = Field(..., description="Semantic version X.Y.Z")
    description: str = Field(..., description="Description of the agent")

    model_config = {"extra": "allow"}  # Allow additional fields like model, color

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate semantic version format."""
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Version must be SemVer (X.Y.Z): {v}")
        return v


# -----------------------------------------------------------------------------
# Data Classes
# -----------------------------------------------------------------------------


@dataclass
class ValidationData:
    """Result of successful validation."""

    registry_path: str
    total_agents: int
    validated_agents: int
    total_skills: int
    validated_dependencies: int
    warnings: List[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Core Functions
# -----------------------------------------------------------------------------


def load_registry(registry_path: Path) -> Result[AgentRegistry, AgentValidationError]:
    """
    Load and parse agent registry YAML file.

    Args:
        registry_path: Path to registry.yaml

    Returns:
        Success with AgentRegistry or Failure with error
    """
    if not registry_path.exists():
        return Failure(
            error=AgentValidationError(
                message=f"Registry not found: {registry_path.as_posix()}",
                file_path=registry_path.as_posix(),
            )
        )

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return Failure(
                error=AgentValidationError(
                    message="Registry is empty",
                    file_path=registry_path.as_posix(),
                )
            )

        registry = AgentRegistry(**data)
        return Success(value=registry)

    except yaml.YAMLError as e:
        return Failure(
            error=AgentValidationError(
                message=f"Failed to parse YAML: {e}",
                file_path=registry_path.as_posix(),
            )
        )
    except PydanticValidationError as e:
        return Failure(
            error=AgentValidationError(
                message=f"Registry schema validation failed: {e}",
                file_path=registry_path.as_posix(),
            )
        )
    except Exception as e:
        return Failure(
            error=AgentValidationError(
                message=f"Unexpected error loading registry: {e}",
                file_path=registry_path.as_posix(),
            )
        )


def extract_frontmatter(file_path: Path) -> Result[Dict[str, Any], AgentValidationError]:
    """
    Extract YAML frontmatter from markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        Success with frontmatter dict or Failure with error
    """
    if not file_path.exists():
        return Failure(
            error=AgentValidationError(
                message=f"File not found: {file_path.as_posix()}",
                file_path=file_path.as_posix(),
            )
        )

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find frontmatter delimiters
        if not lines or lines[0].strip() != "---":
            return Failure(
                error=AgentValidationError(
                    message="No frontmatter found (missing opening ---)",
                    file_path=file_path.as_posix(),
                )
            )

        # Find closing delimiter
        closing_index = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                closing_index = i
                break

        if closing_index is None:
            return Failure(
                error=AgentValidationError(
                    message="No frontmatter found (missing closing ---)",
                    file_path=file_path.as_posix(),
                )
            )

        # Extract and parse YAML
        frontmatter_lines = lines[1:closing_index]
        frontmatter_text = "\n".join(frontmatter_lines)

        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if not frontmatter:
                return Failure(
                    error=AgentValidationError(
                        message="Frontmatter is empty",
                        file_path=file_path.as_posix(),
                    )
                )
            return Success(value=frontmatter)

        except yaml.YAMLError as e:
            return Failure(
                error=AgentValidationError(
                    message=f"Failed to parse frontmatter YAML: {e}",
                    file_path=file_path.as_posix(),
                )
            )

    except Exception as e:
        return Failure(
            error=AgentValidationError(
                message=f"Unexpected error reading file: {e}",
                file_path=file_path.as_posix(),
            )
        )


def validate_agent_version(
    agent_name: str,
    registry_entry: AgentRegistryEntry,
    registry_base_path: Path,
) -> Result[str, AgentValidationError]:
    """
    Validate that agent frontmatter version matches registry version.

    Args:
        agent_name: Name of the agent
        registry_entry: Registry entry for the agent
        registry_base_path: Base path for resolving relative paths (current working directory)

    Returns:
        Success with validated version or Failure with error
    """
    # Resolve agent file path - paths in registry are relative to repo root
    # If path is already absolute, Path() will use it as-is
    # If path is relative, resolve from current working directory
    agent_path = Path(registry_entry.path)
    if not agent_path.is_absolute():
        agent_path = registry_base_path / registry_entry.path

    # Extract frontmatter
    frontmatter_result = extract_frontmatter(agent_path)
    if isinstance(frontmatter_result, Failure):
        return Failure(
            error=AgentValidationError(
                message=frontmatter_result.error.message,
                file_path=agent_path.as_posix(),
                agent_name=agent_name,
            )
        )

    frontmatter_data = frontmatter_result.value

    # Validate frontmatter schema
    try:
        frontmatter = AgentFrontmatter(**frontmatter_data)
    except PydanticValidationError as e:
        return Failure(
            error=AgentValidationError(
                message=f"Frontmatter validation failed: {e}",
                file_path=agent_path.as_posix(),
                agent_name=agent_name,
            )
        )

    # Check version presence
    file_version = frontmatter.version
    registry_version = registry_entry.version

    if not file_version or not registry_version:
        return Failure(
            error=AgentValidationError(
                message=f"Missing version (file='{file_version}' registry='{registry_version}')",
                file_path=agent_path.as_posix(),
                agent_name=agent_name,
                details={
                    "file_version": file_version,
                    "registry_version": registry_version,
                },
            )
        )

    # Check version match
    if file_version != registry_version:
        return Failure(
            error=AgentValidationError(
                message=f"Version mismatch: file={file_version} registry={registry_version}",
                file_path=agent_path.as_posix(),
                agent_name=agent_name,
                details={
                    "file_version": file_version,
                    "registry_version": registry_version,
                },
            )
        )

    return Success(value=file_version)


def validate_skill_constraints(
    skill_name: str,
    skill_dep: SkillDependency,
    registry: AgentRegistry,
) -> Result[List[str], AgentValidationError]:
    """
    Validate skill dependency constraints against registry.

    Args:
        skill_name: Name of the skill
        skill_dep: Skill dependency information
        registry: Agent registry

    Returns:
        Success with list of validated dependencies or Failure with error
    """
    validated_deps = []
    errors = []

    for dep_name, constraint in skill_dep.depends_on.items():
        # Check if dependency is an agent
        if dep_name in registry.agents:
            agent_version = registry.agents[dep_name].version

            # Validate version constraint (e.g., "1.x")
            if re.match(r"^\d+\.x$", constraint):
                required_major = constraint.split(".")[0]
                agent_major = agent_version.split(".")[0]

                if agent_major != required_major:
                    errors.append(
                        AgentValidationError(
                            message=f"Skill '{skill_name}' requires {dep_name} {constraint}, but registry has {agent_version}",
                            agent_name=dep_name,
                            details={
                                "skill": skill_name,
                                "constraint": constraint,
                                "agent_version": agent_version,
                            },
                        )
                    )
                    continue

            validated_deps.append(f"{dep_name}:{constraint}")

        # Check if dependency is another skill
        elif registry.skills and dep_name in registry.skills:
            # Skill-to-skill dependency (allowed)
            validated_deps.append(f"{dep_name}:{constraint}")

        else:
            # Unknown dependency
            errors.append(
                AgentValidationError(
                    message=f"Skill '{skill_name}' depends on undefined agent/skill '{dep_name}'",
                    agent_name=dep_name,
                    details={
                        "skill": skill_name,
                        "dependency": dep_name,
                    },
                )
            )

    if errors:
        return Failure(
            error=AggregateError(errors=errors),
            partial_result=validated_deps,
        )

    return Success(value=validated_deps)


def validate_all_agents(
    registry_path: Path, verbose: bool = False
) -> Result[ValidationData, AgentValidationError]:
    """
    Validate all agents in the registry.

    Args:
        registry_path: Path to registry.yaml
        verbose: Whether to show detailed output

    Returns:
        Success with ValidationData or Failure with error
    """
    # Load registry
    registry_result = load_registry(registry_path)
    if isinstance(registry_result, Failure):
        return registry_result

    registry = registry_result.value
    # Use current working directory as base path for relative paths in registry
    registry_base_path = Path.cwd()

    # Validate each agent
    agent_results = []
    for agent_name, registry_entry in registry.agents.items():
        if verbose:
            print(f"Validating agent: {agent_name}")

        result = validate_agent_version(agent_name, registry_entry, registry_base_path)
        agent_results.append(result)

    # Collect agent validation results
    agents_collected = collect_results(agent_results)

    # Validate skill constraints if present
    skill_results = []
    if registry.skills:
        for skill_name, skill_dep in registry.skills.items():
            if verbose:
                print(f"Validating skill dependencies: {skill_name}")

            result = validate_skill_constraints(skill_name, skill_dep, registry)
            skill_results.append(result)

    # Collect skill validation results
    skills_collected = collect_results(skill_results) if skill_results else Success(value=[])

    # Aggregate results
    all_errors = []
    warnings = []

    if isinstance(agents_collected, Failure):
        if isinstance(agents_collected.error, AggregateError):
            all_errors.extend(agents_collected.error.errors)
        else:
            all_errors.append(agents_collected.error)

    if isinstance(skills_collected, Failure):
        if isinstance(skills_collected.error, AggregateError):
            all_errors.extend(skills_collected.error.errors)
        else:
            all_errors.append(skills_collected.error)

    if all_errors:
        return Failure(
            error=AggregateError(errors=all_errors),
            partial_result=ValidationData(
                registry_path=registry_path.as_posix(),
                total_agents=len(registry.agents),
                validated_agents=len([r for r in agent_results if isinstance(r, Success)]),
                total_skills=len(registry.skills) if registry.skills else 0,
                validated_dependencies=0,
                warnings=warnings,
            ),
        )

    # Success
    validated_agents = len(agents_collected.value) if isinstance(agents_collected, Success) else 0
    validated_deps = (
        sum(len(deps) for deps in skills_collected.value)
        if isinstance(skills_collected, Success)
        else 0
    )

    return Success(
        value=ValidationData(
            registry_path=registry_path.as_posix(),
            total_agents=len(registry.agents),
            validated_agents=validated_agents,
            total_skills=len(registry.skills) if registry.skills else 0,
            validated_dependencies=validated_deps,
            warnings=warnings,
        )
    )


# -----------------------------------------------------------------------------
# CLI Interface
# -----------------------------------------------------------------------------


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Validate agent frontmatter versions match registry"
    )
    parser.add_argument(
        "--registry",
        type=str,
        default=".claude/agents/registry.yaml",
        help="Path to registry.yaml (default: .claude/agents/registry.yaml)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed validation output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Resolve registry path
    registry_path = Path(args.registry)

    # Run validation
    result = validate_all_agents(registry_path, verbose=args.verbose)

    # Output results
    if isinstance(result, Success):
        data = result.value

        if args.json:
            output = {
                "success": True,
                "registry_path": data.registry_path,
                "total_agents": data.total_agents,
                "validated_agents": data.validated_agents,
                "total_skills": data.total_skills,
                "validated_dependencies": data.validated_dependencies,
                "warnings": data.warnings,
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"All agent versions validated successfully")
            print(f"  Registry: {data.registry_path}")
            print(f"  Agents: {data.validated_agents}/{data.total_agents}")
            if data.total_skills > 0:
                print(f"  Skills: {data.total_skills}")
                print(f"  Validated dependencies: {data.validated_dependencies}")

            if data.warnings:
                print("\nWarnings:")
                for warning in data.warnings:
                    print(f"  - {warning}")

        return 0

    else:
        error = result.error

        if args.json:
            if isinstance(error, AggregateError):
                errors_list = [str(e) for e in error.errors]
            else:
                errors_list = [str(error)]

            output = {
                "success": False,
                "errors": errors_list,
            }

            if result.partial_result:
                data = result.partial_result
                output["partial_results"] = {
                    "validated_agents": data.validated_agents,
                    "total_agents": data.total_agents,
                }

            print(json.dumps(output, indent=2))
        else:
            if isinstance(error, AggregateError):
                print("Validation errors found:", file=sys.stderr)
                for err in error.errors:
                    print(f"  {err}", file=sys.stderr)
            else:
                print(f"ERROR: {error}", file=sys.stderr)

            if result.partial_result:
                data = result.partial_result
                print(
                    f"\nPartial results: {data.validated_agents}/{data.total_agents} agents validated",
                    file=sys.stderr,
                )

        return 1


if __name__ == "__main__":
    sys.exit(main())
