"""Reusable Pydantic schemas for testing SC structured logging.

Provides common test schemas and validation patterns that can be reused
across package tests.

Usage:
    from tests.logging.schemas import TestLogEntry, AgentSpawnLogEntry

    entry = TestLogEntry.model_validate_json(json_string)
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


# =============================================================================
# Base Test Schemas
# =============================================================================

class MinimalLogEntry(BaseModel):
    """Minimal log entry schema for basic validation.

    Contains only required core fields.
    """
    timestamp: str
    event: str
    level: str = "info"

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        """Validate log level is valid."""
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v


class StandardLogEntry(BaseModel):
    """Standard log entry schema with package field.

    Matches BaseLogEntry from sc-logging template.
    """
    model_config = ConfigDict(extra="allow")

    timestamp: str = Field(description="ISO 8601 timestamp")
    event: str = Field(description="Event type")
    package: str = Field(description="Package name")
    level: str = Field(default="info", pattern="^(debug|info|warning|error|critical)$")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_format(cls, v):
        """Validate timestamp is ISO 8601 format."""
        try:
            # Try parsing as ISO 8601
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}")
        return v


# =============================================================================
# Hook-Specific Schemas
# =============================================================================

class HookLogEntry(StandardLogEntry):
    """Log entry for hook events with payload and decision."""
    payload: dict = Field(description="Hook payload from stdin")
    decision: Optional[dict] = Field(default=None, description="Hook decision (allowed/blocked)")

    @field_validator("decision")
    @classmethod
    def validate_decision_structure(cls, v):
        """Validate decision has required 'allowed' field."""
        if v is not None and "allowed" not in v:
            raise ValueError("Decision must have 'allowed' field")
        return v


class AgentSpawnLogEntry(HookLogEntry):
    """Log entry for agent spawn gate events."""
    agent_type: Optional[str] = Field(default=None, description="Type of agent spawned")
    session_id: Optional[str] = Field(default=None, description="Session ID")


# =============================================================================
# Agent Runner Schemas
# =============================================================================

class AgentRunnerAuditEntry(BaseModel):
    """Agent runner audit log entry schema."""
    timestamp: str
    agent: str
    version_frontmatter: Optional[str]
    file_sha256: str
    invoker: str = "agent-runner"
    outcome: str
    duration_ms: Optional[int] = None

    @field_validator("file_sha256")
    @classmethod
    def validate_sha256_format(cls, v):
        """Validate SHA-256 is 64-character hex string."""
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError(f"Invalid SHA-256 hash: {v} (must be 64-char hex)")
        if not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError(f"Invalid SHA-256 hash: {v} (must be hexadecimal)")
        return v


# =============================================================================
# Package-Specific Example Schemas
# =============================================================================

class WorktreeLogEntry(StandardLogEntry):
    """Example: sc-git-worktree log entry."""
    session_id: Optional[str] = None
    branch_name: Optional[str] = None
    worktree_path: Optional[str] = None
    outcome: Optional[Literal["success", "failure", "partial"]] = None
    error_code: Optional[int] = None


class PreflightLogEntry(StandardLogEntry):
    """Example: sc-commit-push-pr preflight log entry."""
    check_name: Optional[str] = None
    check_passed: Optional[bool] = None
    details: Optional[dict] = None


class CIAutomationLogEntry(StandardLogEntry):
    """Example: sc-ci-automation log entry."""
    phase: Optional[Literal["pull", "build", "test", "fix", "pr"]] = None
    status: Optional[Literal["started", "completed", "failed"]] = None
    duration_ms: Optional[int] = None


# =============================================================================
# Schema Inheritance Patterns
# =============================================================================

class ExtendedLogEntry(StandardLogEntry):
    """Example of extending StandardLogEntry with custom fields.

    Demonstrates best practices for package-specific extensions.
    """
    # Custom fields with Field() for documentation
    custom_field: Optional[str] = Field(
        default=None,
        description="Example custom field",
        examples=["value1", "value2"]
    )

    # Custom validator
    @field_validator("custom_field", mode="before")
    @classmethod
    def validate_custom_field(cls, v):
        """Example validator for custom field."""
        if v is not None and not isinstance(v, str):
            raise ValueError("custom_field must be string or None")
        return v


# =============================================================================
# Validator Patterns (Reusable)
# =============================================================================

def validate_non_empty_string(v: Optional[str], field_name: str) -> Optional[str]:
    """Reusable validator for non-empty strings.

    Args:
        v: Field value
        field_name: Name of field for error messages

    Returns:
        Validated value

    Raises:
        ValueError: If string is empty

    Usage:
        @field_validator("my_field", mode="before")
        @classmethod
        def validate_my_field(cls, v):
            return validate_non_empty_string(v, "my_field")
    """
    if v is not None and isinstance(v, str):
        if not v.strip():
            raise ValueError(f"{field_name} cannot be empty string")
        return v.strip()
    return v


def validate_path_exists(v: Optional[str], field_name: str) -> Optional[str]:
    """Reusable validator for file path existence.

    Args:
        v: Path string
        field_name: Name of field for error messages

    Returns:
        Validated path

    Raises:
        ValueError: If path doesn't exist

    Usage:
        @field_validator("file_path", mode="before")
        @classmethod
        def validate_file_path(cls, v):
            return validate_path_exists(v, "file_path")
    """
    if v is not None:
        from pathlib import Path
        path = Path(v)
        if not path.exists():
            raise ValueError(f"{field_name} does not exist: {v}")
    return v


# =============================================================================
# Test Helpers
# =============================================================================

def create_test_log_entry(**kwargs) -> dict:
    """Create a test log entry dictionary with default values.

    Args:
        **kwargs: Override default fields

    Returns:
        Log entry dictionary suitable for testing

    Example:
        entry = create_test_log_entry(
            event="test_event",
            package="test-package",
            custom_field="value"
        )
    """
    defaults = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": "test_event",
        "package": "test-package",
        "level": "info"
    }
    defaults.update(kwargs)
    return defaults


def validate_entry_structure(entry: dict, required_fields: list[str]) -> None:
    """Validate log entry has required fields.

    Args:
        entry: Log entry dictionary
        required_fields: List of required field names

    Raises:
        ValueError: If required fields missing
    """
    missing = [f for f in required_fields if f not in entry]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
