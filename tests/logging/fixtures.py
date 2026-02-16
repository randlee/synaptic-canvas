"""Test fixtures for SC structured logging tests.

Provides reusable fixtures for testing:
- Temporary log directories
- Mock hook payloads
- Sample log entries (valid/invalid)
- Cleanup utilities

Usage:
    from tests.logging.fixtures import (
        create_temp_log_dir,
        mock_hook_payload,
        sample_log_entries
    )
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List


# =============================================================================
# Directory Fixtures
# =============================================================================

def create_temp_log_dir(package_name: str = "test-package") -> Path:
    """Create temporary log directory structure for testing.

    Args:
        package_name: Package name for log directory

    Returns:
        Path to package log directory (.claude/state/logs/<package>)

    Example:
        log_dir = create_temp_log_dir("sc-git-worktree")
        # Returns: /tmp/xyz/.claude/state/logs/sc-git-worktree/
    """
    temp_root = Path(tempfile.mkdtemp())
    log_dir = temp_root / ".claude" / "state" / "logs" / package_name
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def cleanup_temp_dir(path: Path) -> None:
    """Clean up temporary directory.

    Args:
        path: Path to temporary directory to remove
    """
    import shutil
    if path.exists():
        shutil.rmtree(path)


# =============================================================================
# Mock Hook Payloads
# =============================================================================

def mock_hook_payload(
    tool_name: str = "Task",
    command: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create mock hook payload for testing.

    Args:
        tool_name: Tool name (e.g., "Task", "Bash", "Edit")
        command: Tool command/input
        extra_fields: Additional fields to include

    Returns:
        Mock hook payload dictionary

    Example:
        payload = mock_hook_payload(
            tool_name="Task",
            command='{"agent": "test-agent"}',
            extra_fields={"session_id": "abc123"}
        )
    """
    payload = {
        "tool_name": tool_name,
        "tool_input": {
            "command": command or '{"test": "data"}'
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if extra_fields:
        payload.update(extra_fields)

    return payload


def mock_agent_spawn_payload(
    agent_type: str = "test-agent",
    prompt: str = "Test prompt",
    allowed: bool = True
) -> Dict[str, Any]:
    """Create mock agent spawn gate payload.

    Args:
        agent_type: Agent type/subagent_type
        prompt: Agent prompt
        allowed: Whether spawn should be allowed

    Returns:
        Mock agent spawn payload with decision
    """
    return {
        "tool_name": "Task",
        "tool_input": {
            "subagent_type": agent_type,
            "prompt": prompt
        },
        "decision": {
            "allowed": allowed,
            "reason": "Test reason"
        }
    }


def mock_pretool_use_payload(
    tool_name: str,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """Create mock PreToolUse hook payload.

    Args:
        tool_name: Name of tool being invoked
        params: Tool parameters

    Returns:
        Mock PreToolUse payload

    Example:
        payload = mock_pretool_use_payload(
            tool_name="Bash",
            params={"command": "ls -la"}
        )
    """
    return {
        "tool_name": tool_name,
        "tool_input": params,
        "hook_type": "PreToolUse",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =============================================================================
# Sample Log Entries
# =============================================================================

def sample_log_entry(
    event: str = "test_event",
    package: str = "test-package",
    level: str = "info",
    **extra_fields
) -> Dict[str, Any]:
    """Create sample log entry with default values.

    Args:
        event: Event type
        package: Package name
        level: Log level
        **extra_fields: Additional fields to include

    Returns:
        Sample log entry dictionary

    Example:
        entry = sample_log_entry(
            event="worktree_create",
            package="sc-git-worktree",
            branch_name="feature-x"
        )
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "package": package,
        "level": level
    }
    entry.update(extra_fields)
    return entry


def sample_log_entries(count: int = 5, package: str = "test-package") -> List[Dict[str, Any]]:
    """Create multiple sample log entries.

    Args:
        count: Number of entries to create
        package: Package name

    Returns:
        List of sample log entry dictionaries

    Example:
        entries = sample_log_entries(10, "sc-git-worktree")
    """
    return [
        sample_log_entry(
            event=f"test_event_{i}",
            package=package,
            index=i
        )
        for i in range(count)
    ]


def sample_hook_log_entry(
    event: str = "agent_spawn_gate",
    allowed: bool = True,
    **extra_fields
) -> Dict[str, Any]:
    """Create sample hook log entry.

    Args:
        event: Hook event type
        allowed: Whether action was allowed
        **extra_fields: Additional fields

    Returns:
        Sample hook log entry with payload and decision
    """
    payload = mock_hook_payload()
    decision = {
        "allowed": allowed,
        "reason": "Test reason",
        "rule": "test_rule"
    }

    entry = sample_log_entry(
        event=event,
        package="hooks",
        level="info" if allowed else "warning",
        payload=payload,
        decision=decision
    )
    entry.update(extra_fields)
    return entry


def sample_agent_runner_audit_entry(
    agent_name: str = "test-agent",
    outcome: str = "prepared",
    version: str = "1.0.0"
) -> Dict[str, Any]:
    """Create sample agent runner audit entry.

    Args:
        agent_name: Agent name
        outcome: Outcome (prepared/success/error)
        version: Agent version

    Returns:
        Sample audit entry
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "agent": agent_name,
        "version_frontmatter": version,
        "file_sha256": "a" * 64,  # Valid 64-char hex
        "invoker": "agent-runner",
        "outcome": outcome
    }


# =============================================================================
# Invalid Entry Fixtures (for testing validation)
# =============================================================================

def invalid_log_entries() -> List[Dict[str, Any]]:
    """Create list of invalid log entries for testing validation.

    Returns:
        List of invalid log entry dictionaries
    """
    return [
        # Missing timestamp
        {
            "event": "test",
            "package": "test-package",
            "level": "info"
        },
        # Missing event
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "package": "test-package",
            "level": "info"
        },
        # Invalid level
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "test",
            "package": "test-package",
            "level": "invalid_level"
        },
        # Invalid timestamp format
        {
            "timestamp": "not-a-timestamp",
            "event": "test",
            "package": "test-package",
            "level": "info"
        }
    ]


def entries_with_secrets() -> List[Dict[str, Any]]:
    """Create log entries containing secrets for testing security validation.

    Returns:
        List of log entries with secrets
    """
    return [
        sample_log_entry(password="secret123"),
        sample_log_entry(api_key="sk-1234567890"),
        sample_log_entry(token="bearer_xyz789"),
        sample_log_entry(auth_header="Bearer abc123def456"),
        sample_log_entry(credentials={"user": "admin", "password": "pass123"})
    ]


# =============================================================================
# File Writing Helpers
# =============================================================================

def write_log_file(
    log_dir: Path,
    event_type: str,
    entries: List[Dict[str, Any]]
) -> Path:
    """Write log entries to JSONL file.

    Args:
        log_dir: Log directory path
        event_type: Event type (filename)
        entries: List of log entry dictionaries

    Returns:
        Path to written log file

    Example:
        log_file = write_log_file(
            log_dir,
            "test-event",
            sample_log_entries(10)
        )
    """
    log_file = log_dir / f"{event_type}.jsonl"
    with log_file.open("w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return log_file


def append_log_entry(
    log_dir: Path,
    event_type: str,
    entry: Dict[str, Any]
) -> Path:
    """Append single log entry to JSONL file.

    Args:
        log_dir: Log directory path
        event_type: Event type (filename)
        entry: Log entry dictionary

    Returns:
        Path to log file
    """
    log_file = log_dir / f"{event_type}.jsonl"
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return log_file


# =============================================================================
# Environment Variable Mocking
# =============================================================================

def mock_env_vars(
    project_dir: Optional[str] = None,
    plugin_root: Optional[str] = None
) -> Dict[str, str]:
    """Create mock environment variable dictionary for testing.

    Args:
        project_dir: CLAUDE_PROJECT_DIR value
        plugin_root: CLAUDE_PLUGIN_ROOT value

    Returns:
        Dictionary of environment variables

    Example:
        import os
        env = mock_env_vars(project_dir="/tmp/test")
        os.environ.update(env)
    """
    env = {}
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = project_dir
    if plugin_root:
        env["CLAUDE_PLUGIN_ROOT"] = plugin_root
    return env


# =============================================================================
# Complete Test Scenarios
# =============================================================================

def setup_logging_test_scenario(
    package_name: str = "test-package",
    num_entries: int = 5
) -> tuple[Path, Path, List[Dict[str, Any]]]:
    """Set up complete logging test scenario with directory and entries.

    Args:
        package_name: Package name
        num_entries: Number of log entries to create

    Returns:
        Tuple of (temp_root, log_dir, entries)

    Example:
        temp_root, log_dir, entries = setup_logging_test_scenario("sc-git-worktree")
        # Test code here
        cleanup_temp_dir(temp_root)
    """
    log_dir = create_temp_log_dir(package_name)
    temp_root = log_dir.parent.parent.parent  # Get temp root

    entries = sample_log_entries(num_entries, package_name)
    write_log_file(log_dir, "test-event", entries)

    return temp_root, log_dir, entries
