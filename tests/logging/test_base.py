"""Base test class for logging validation across all SC packages.

Provides reusable assertions and helpers for testing structured logging:
- Pydantic schema validation
- Log file existence checking
- Security validation (no secrets in logs)
- Helper functions for reading and mocking log data

Usage:
    from tests.logging.test_base import LoggingTestCase

    class TestMyPackageLogging(LoggingTestCase):
        def test_logging_works(self):
            # Your test code
            self.assert_log_file_exists("my-package", "event-type")
"""

import json
import re
import tempfile
import unittest
from pathlib import Path
from typing import Type, Optional, List

from pydantic import BaseModel


class LoggingTestCase(unittest.TestCase):
    """Base test class for structured logging tests.

    Provides:
    - Temporary log directory setup/teardown
    - Pydantic validation helpers
    - Security validation (no secrets)
    - Log reading helpers
    - Hook mocking utilities
    """

    def setUp(self):
        """Create temporary log directory for testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / ".claude" / "state" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    # =========================================================================
    # Validation Assertions
    # =========================================================================

    def assert_log_entry_valid(self, entry_json: str, schema: Type[BaseModel]) -> BaseModel:
        """Validate log entry against Pydantic schema.

        Args:
            entry_json: JSON string representing log entry
            schema: Pydantic model class to validate against

        Returns:
            Validated Pydantic model instance

        Raises:
            AssertionError: If validation fails
        """
        try:
            entry = schema.model_validate_json(entry_json)
        except Exception as e:
            self.fail(f"Log entry validation failed: {e}\nEntry: {entry_json}")

        # Validate core fields exist (if schema has them)
        if hasattr(entry, 'timestamp'):
            self.assertIsNotNone(entry.timestamp, "Log entry missing timestamp")
        if hasattr(entry, 'event'):
            self.assertIsNotNone(entry.event, "Log entry missing event")
        if hasattr(entry, 'level'):
            self.assertIn(
                entry.level,
                ["debug", "info", "warning", "error", "critical"],
                f"Invalid log level: {entry.level}"
            )

        return entry

    def assert_log_file_exists(self, package: str, event_type: str) -> Path:
        """Verify log file exists at expected location.

        Args:
            package: Package name (e.g., "sc-git-worktree")
            event_type: Event type (e.g., "agent-spawn-allowed")

        Returns:
            Path to log file

        Raises:
            AssertionError: If log file doesn't exist
        """
        log_file = self.log_dir / package / f"{event_type}.jsonl"
        self.assertTrue(
            log_file.exists(),
            f"Log file not found: {log_file}\nExpected location: .claude/state/logs/{package}/{event_type}.jsonl"
        )
        return log_file

    def assert_log_file_not_empty(self, package: str, event_type: str) -> None:
        """Verify log file exists and contains entries.

        Args:
            package: Package name
            event_type: Event type

        Raises:
            AssertionError: If file doesn't exist or is empty
        """
        log_file = self.assert_log_file_exists(package, event_type)
        self.assertGreater(
            log_file.stat().st_size,
            0,
            f"Log file is empty: {log_file}"
        )

    def assert_no_secrets_logged(
        self,
        log_dir: Optional[Path] = None,
        patterns: Optional[List[str]] = None
    ) -> None:
        """Security check: ensure no secrets in logs.

        Args:
            log_dir: Directory to scan (default: self.log_dir)
            patterns: Regex patterns to detect secrets (default: password/token/api_key)

        Raises:
            AssertionError: If secrets detected in logs
        """
        log_dir = log_dir or self.log_dir
        if patterns is None:
            patterns = [
                r"password\s*[:=]\s*[^\s]+",
                r"token\s*[:=]\s*[^\s]+",
                r"api[_-]?key\s*[:=]\s*[^\s]+",
                r"secret\s*[:=]\s*[^\s]+",
                r"bearer\s+[A-Za-z0-9\-._~+/]+=*",  # Bearer tokens
            ]

        violations = []
        for log_file in log_dir.rglob("*.jsonl"):
            content = log_file.read_text()
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    violations.append({
                        "file": str(log_file.relative_to(log_dir)),
                        "pattern": pattern,
                        "match": match.group(0),
                        "line": content[:match.start()].count('\n') + 1
                    })

        if violations:
            msg = "Secrets detected in logs:\n"
            for v in violations:
                msg += f"  {v['file']}:{v['line']} - {v['match']}\n"
            self.fail(msg)

    # =========================================================================
    # Helper Functions
    # =========================================================================

    def read_log_entries(
        self,
        package: str,
        event_type: str,
        limit: Optional[int] = None,
        schema: Optional[Type[BaseModel]] = None
    ) -> List[dict]:
        """Read and parse log entries from file.

        Args:
            package: Package name
            event_type: Event type
            limit: Maximum number of entries to read (most recent first)
            schema: Optional Pydantic schema to validate entries

        Returns:
            List of log entry dictionaries (or validated models if schema provided)
        """
        log_file = self.log_dir / package / f"{event_type}.jsonl"
        if not log_file.exists():
            return []

        entries = []
        with log_file.open("r") as f:
            for line in f:
                try:
                    entry_dict = json.loads(line.strip())
                    if schema:
                        entry = schema.model_validate(entry_dict)
                        entries.append(entry)
                    else:
                        entries.append(entry_dict)
                except Exception:
                    continue  # Skip invalid entries

        if limit:
            entries = entries[-limit:]  # Most recent entries

        return entries

    def write_log_entry(
        self,
        package: str,
        event_type: str,
        entry: dict
    ) -> Path:
        """Write a log entry for testing.

        Args:
            package: Package name
            event_type: Event type
            entry: Log entry dictionary

        Returns:
            Path to log file
        """
        package_dir = self.log_dir / package
        package_dir.mkdir(parents=True, exist_ok=True)

        log_file = package_dir / f"{event_type}.jsonl"
        with log_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")

        return log_file

    def mock_hook_stdin(self, data: dict) -> str:
        """Create mock stdin data for hook testing.

        Args:
            data: Hook payload dictionary

        Returns:
            JSON string for stdin input
        """
        return json.dumps(data, indent=2)

    def assert_entry_field_equals(
        self,
        package: str,
        event_type: str,
        field: str,
        expected_value: any,
        entry_index: int = -1
    ) -> None:
        """Assert a specific field in a log entry matches expected value.

        Args:
            package: Package name
            event_type: Event type
            field: Field name to check
            expected_value: Expected field value
            entry_index: Index of entry to check (default: -1 = most recent)

        Raises:
            AssertionError: If field doesn't match expected value
        """
        entries = self.read_log_entries(package, event_type)
        self.assertGreater(len(entries), 0, f"No log entries found for {package}/{event_type}")

        entry = entries[entry_index]
        self.assertIn(field, entry, f"Field '{field}' not found in log entry")
        self.assertEqual(
            entry[field],
            expected_value,
            f"Field '{field}' value mismatch"
        )

    def count_log_entries(self, package: str, event_type: str) -> int:
        """Count number of log entries in file.

        Args:
            package: Package name
            event_type: Event type

        Returns:
            Number of entries in log file
        """
        return len(self.read_log_entries(package, event_type))


# =============================================================================
# Example Test (can be removed or kept as reference)
# =============================================================================

class TestLoggingTestCase(LoggingTestCase):
    """Test the LoggingTestCase base class itself."""

    def test_temp_directory_creation(self):
        """Test temporary directory is created."""
        self.assertTrue(self.temp_dir.exists())
        self.assertTrue(self.log_dir.exists())

    def test_write_and_read_log_entry(self):
        """Test writing and reading log entries."""
        entry = {
            "timestamp": "2026-02-11T10:00:00Z",
            "event": "test_event",
            "package": "test-package",
            "level": "info"
        }

        self.write_log_entry("test-package", "test-event", entry)
        self.assert_log_file_exists("test-package", "test-event")

        entries = self.read_log_entries("test-package", "test-event")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["event"], "test_event")

    def test_no_secrets_validation_passes(self):
        """Test no secrets validation passes with clean logs."""
        entry = {
            "timestamp": "2026-02-11T10:00:00Z",
            "event": "test",
            "level": "info",
            "message": "This is a safe log entry"
        }
        self.write_log_entry("test-package", "test-event", entry)

        # Should not raise AssertionError
        self.assert_no_secrets_logged()

    def test_no_secrets_validation_detects_password(self):
        """Test no secrets validation detects passwords."""
        entry = {
            "timestamp": "2026-02-11T10:00:00Z",
            "event": "test",
            "level": "info",
            "password": "secret123",
            "config": "password=mypass123"  # Explicit pattern match
        }
        self.write_log_entry("test-package", "test-event", entry)

        with self.assertRaises(AssertionError) as ctx:
            self.assert_no_secrets_logged()

        self.assertIn("Secrets detected", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
