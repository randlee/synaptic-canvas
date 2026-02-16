#!/usr/bin/env python3
"""SC Structured Logging Library - Jenga Template

USAGE:
1. Copy this template to your package: packages/<your-package>/scripts/sc_logging.py
2. Update PACKAGE_NAME constant
3. Extend LogEntry with package-specific fields if needed
4. Use log_event() to write structured logs

JENGA EXPANSION:
- {{PACKAGE_NAME}} - Replace with your package name
- {{EXTRA_FIELDS}} - Add package-specific Pydantic fields
- {{EXTRA_IMPORTS}} - Add package-specific imports

Standard log location: .claude/state/logs/<package>/<event-type>.jsonl
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from pydantic import BaseModel, Field, ConfigDict, field_validator
except ImportError:
    print("ERROR: pydantic not installed. Run: pip install pydantic", file=sys.stderr)
    sys.exit(1)

# {{PACKAGE_NAME}} - Replace with your package name
PACKAGE_NAME = "{{PACKAGE_NAME}}"


# =============================================================================
# Environment Variable Helpers
# =============================================================================

def _normalize_path(value: Optional[str | Path]) -> Optional[Path]:
    """Normalize path by expanding user and resolving to absolute.

    Args:
        value: Path string or Path object

    Returns:
        Resolved absolute Path or None
    """
    if value is None:
        return None
    return Path(value).expanduser().resolve()


def find_project_root(start: Optional[Path] = None) -> Optional[Path]:
    """Find project root by searching upward for marker files/directories.

    Args:
        start: Starting directory (default: Path.cwd())

    Returns:
        Project root Path or None if not found

    Searches upward for:
        - .git directory (git repository)
        - .claude directory (Claude Code project)
        - .sc directory (Synaptic Canvas project)
    """
    current = Path(start or Path.cwd()).resolve()

    # Search upward through parent directories
    for parent in [current, *current.parents]:
        # Check for project markers
        if any([
            (parent / ".git").exists(),
            (parent / ".claude").exists(),
            (parent / ".sc").exists(),
        ]):
            return parent

    return None


def get_project_dir() -> Path:
    """Get project directory with robust fallback chain.

    Returns:
        Project directory Path (never None)

    Fallback order:
        1. CLAUDE_PROJECT_DIR (Claude Code hook context)
        2. CODEX_PROJECT_DIR (Codex compatibility)
        3. Search upward for .git/.claude/.sc markers
        4. Path.cwd() (last resort)

    Note:
        Environment variables are only available in hook contexts.
        Background agents, Bash tool, and teammates use marker search fallback.
    """
    # Try environment variables first (available in hook contexts)
    project_dir = os.getenv("CLAUDE_PROJECT_DIR") or os.getenv("CODEX_PROJECT_DIR")
    if project_dir:
        return _normalize_path(project_dir)

    # Try to find project root by searching for markers
    found_root = find_project_root()
    if found_root:
        return found_root

    # Last resort: current working directory
    return Path.cwd()


def get_plugin_root() -> Optional[Path]:
    """Get plugin root directory from environment with fallback.

    Returns:
        Plugin root Path or None

    Environment Variables:
        - CLAUDE_PLUGIN_ROOT (Claude Code hook context)
        - Fallback: Derive from current file location
    """
    plugin_root = os.getenv("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        return _normalize_path(plugin_root)
    # Fallback: assume we're in packages/<package>/scripts/
    return Path(__file__).parent.parent.parent


# Standard log location following SC conventions
# Uses get_project_dir() to support environment variables in hook contexts
LOGS_DIR = get_project_dir() / ".claude" / "state" / "logs" / PACKAGE_NAME


# =============================================================================
# Base Schema - DO NOT MODIFY (unless updating template across all packages)
# =============================================================================

class BaseLogEntry(BaseModel):
    """Base log entry schema - extendable via inheritance.

    All log entries MUST include these fields.
    """
    model_config = ConfigDict(extra="allow")  # Allow additional fields

    timestamp: str = Field(
        description="ISO 8601 timestamp with timezone (UTC)",
        examples=["2026-02-11T10:30:45.123456Z"]
    )
    event: str = Field(
        description="Event type identifier",
        examples=["agent_spawn_allowed", "PreToolUse-Task", "preflight_check"]
    )
    package: str = Field(
        description="Package name",
        examples=["sc-git-worktree", "sc-github-issue"]
    )
    level: str = Field(
        default="info",
        description="Log level",
        pattern="^(debug|info|warning|error|critical)$"
    )


# =============================================================================
# Package-Specific Extensions - CUSTOMIZE THIS SECTION
# =============================================================================

# {{EXTRA_IMPORTS}}
# Add package-specific imports here
# Example:
# from typing import Literal


class LogEntry(BaseLogEntry):
    """Extended log entry with package-specific fields.

    {{EXTRA_FIELDS}}
    Add your package-specific fields here using Pydantic Field definitions.

    Examples:
        session_id: Optional[str] = Field(default=None, description="Session ID")
        agent_type: Optional[str] = Field(default=None, description="Agent type")
        outcome: Optional[Literal["success", "error"]] = None
    """
    # Add package-specific fields below:
    pass

    # =========================================================================
    # Example Field Validators - CUSTOMIZE OR REMOVE
    # =========================================================================
    #
    # Pydantic v2 field validators provide type-safe validation and normalization.
    # Use mode="before" for normalization, mode="after" for semantic validation.
    #
    # Example 1: Validate file path exists
    #
    # file_path: Optional[str] = Field(default=None, description="Path to file")
    #
    # @field_validator("file_path", mode="before")
    # @classmethod
    # def _validate_file_path_exists(cls, v):
    #     """Validate file exists at path."""
    #     if v is not None:
    #         path = Path(v)
    #         if not path.exists():
    #             raise ValueError(f"File not found: {v}")
    #         return str(path.resolve())  # Normalize to absolute path
    #     return v
    #
    # Example 2: Validate package directory
    #
    # package_name: Optional[str] = Field(default=None, description="Package name")
    #
    # @field_validator("package_name", mode="before")
    # @classmethod
    # def _validate_package_dir(cls, v):
    #     """Validate package directory exists."""
    #     if v is not None:
    #         project_dir = get_project_dir()
    #         pkg_dir = project_dir / "packages" / v
    #         if not pkg_dir.exists():
    #             raise ValueError(f"Package directory not found: {pkg_dir}")
    #     return v
    #
    # Example 3: Normalize and validate non-empty string
    #
    # session_id: Optional[str] = Field(default=None, description="Session ID")
    #
    # @field_validator("session_id", mode="before")
    # @classmethod
    # def _validate_session_id(cls, v):
    #     """Normalize and validate session ID."""
    #     if v is not None:
    #         if not isinstance(v, str):
    #             raise ValueError("session_id must be string")
    #         v = v.strip()
    #         if not v:
    #             raise ValueError("session_id cannot be empty")
    #     return v
    #
    # Example 4: Multiple fields with same validator
    #
    # @field_validator("field1", "field2", "field3", mode="after")
    # @classmethod
    # def _validate_not_empty(cls, v):
    #     """Ensure fields are not empty strings."""
    #     if isinstance(v, str) and not v.strip():
    #         raise ValueError("Field must not be empty string")
    #     return v


# =============================================================================
# Logging Functions
# =============================================================================

def get_log_file(event_type: str, *, log_dir: Optional[Path] = None) -> Path:
    """Get log file path for event type.

    Args:
        event_type: Event type (e.g., "agent-spawn-gate", "preflight")
        log_dir: Override log directory (default: LOGS_DIR)

    Returns:
        Path to log file (.jsonl)

    Standard naming: <event-type>.jsonl (append-friendly JSONL format)
    """
    log_dir = log_dir or LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize event type for filename (replace spaces/special chars with hyphens)
    safe_event = event_type.lower().replace(" ", "-").replace("_", "-")
    return log_dir / f"{safe_event}.jsonl"


def validate_log_directory(log_dir: Optional[Path] = None) -> Path:
    """Validate and ensure log directory exists with correct structure.

    Args:
        log_dir: Log directory to validate (default: LOGS_DIR)

    Returns:
        Validated log directory Path

    Raises:
        ValueError: If log directory structure is invalid

    Standard structure:
        .claude/state/logs/<package>/

    This function ensures:
    - .claude directory exists in project root
    - state/logs subdirectory structure is correct
    - Package-specific subdirectory exists
    - Directories have appropriate permissions
    """
    log_dir = log_dir or LOGS_DIR

    # Ensure directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Validate structure (.claude/state/logs/<package>)
    if not (log_dir.parent.name == "logs" and
            log_dir.parent.parent.name == "state" and
            log_dir.parent.parent.parent.name == ".claude"):
        print(
            f"WARNING: Log directory does not follow standard structure: {log_dir}\n"
            f"Expected: .claude/state/logs/{PACKAGE_NAME}/",
            file=sys.stderr
        )

    return log_dir


def log_event(
    event: str,
    level: str = "info",
    log_dir: Optional[Path] = None,
    **extra_fields
) -> None:
    """Log a structured event.

    Args:
        event: Event type identifier
        level: Log level (debug|info|warning|error|critical)
        log_dir: Override log directory (default: LOGS_DIR)
        **extra_fields: Additional fields to include in log entry

    Example:
        log_event(
            event="agent_spawn_allowed",
            level="info",
            session_id="abc123",
            agent_type="scrum-master"
        )
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    entry = LogEntry(
        timestamp=timestamp,
        event=event,
        package=PACKAGE_NAME,
        level=level,
        **extra_fields
    )

    log_file = get_log_file(event, log_dir=log_dir)

    try:
        with log_file.open("a") as f:
            f.write(entry.model_dump_json() + "\n")
    except Exception as e:
        # Don't fail the operation on logging errors
        print(f"WARNING: Failed to write log: {e}", file=sys.stderr)


def log_hook_event(
    event: str,
    hook_data: dict,
    decision: Optional[dict] = None,
    log_dir: Optional[Path] = None
) -> None:
    """Log a hook event with standard structure.

    Args:
        event: Event type (e.g., "PreToolUse-Task", "agent_spawn_gate")
        hook_data: Full hook payload from stdin
        decision: Optional decision data (e.g., {"allowed": True, "reason": "..."})
        log_dir: Override log directory

    Example:
        data = json.load(sys.stdin)
        log_hook_event(
            event="agent_spawn_gate",
            hook_data=data,
            decision={"allowed": False, "reason": "Rule 1 violation", "rule": "..."}
        )
    """
    extra = {"payload": hook_data}
    if decision:
        extra["decision"] = decision

    log_event(
        event=event,
        level="info" if decision is None or decision.get("allowed") else "warning",
        log_dir=log_dir,
        **extra
    )


# =============================================================================
# Querying Helpers (optional - for convenience)
# =============================================================================

def read_logs(
    event_type: str,
    limit: Optional[int] = None,
    log_dir: Optional[Path] = None
) -> list[LogEntry]:
    """Read log entries from file.

    Args:
        event_type: Event type to read
        limit: Maximum number of entries (most recent first)
        log_dir: Override log directory

    Returns:
        List of LogEntry objects (most recent first if limit specified)
    """
    log_file = get_log_file(event_type, log_dir=log_dir)
    if not log_file.exists():
        return []

    entries = []
    with log_file.open("r") as f:
        for line in f:
            try:
                entry = LogEntry.model_validate_json(line.strip())
                entries.append(entry)
            except Exception:
                continue  # Skip invalid entries

    if limit:
        entries = entries[-limit:][::-1]  # Most recent first

    return entries


# =============================================================================
# CLI Interface (optional - for testing)
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SC Logging CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Log command
    log_parser = subparsers.add_parser("log", help="Log an event")
    log_parser.add_argument("event", help="Event type")
    log_parser.add_argument("--level", default="info", choices=["debug", "info", "warning", "error", "critical"])
    log_parser.add_argument("--field", action="append", help="Additional field (key=value)")

    # Read command
    read_parser = subparsers.add_parser("read", help="Read log entries")
    read_parser.add_argument("event_type", help="Event type to read")
    read_parser.add_argument("--limit", type=int, help="Limit number of entries")

    args = parser.parse_args()

    if args.command == "log":
        extra = {}
        if args.field:
            for field in args.field:
                key, value = field.split("=", 1)
                extra[key] = value
        log_event(args.event, level=args.level, **extra)
        print(f"✓ Logged event: {args.event}")

    elif args.command == "read":
        entries = read_logs(args.event_type, limit=args.limit)
        for entry in entries:
            print(entry.model_dump_json(indent=2))

    else:
        parser.print_help()
