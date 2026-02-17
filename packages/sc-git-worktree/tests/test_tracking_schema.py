"""Tests for TrackingEntry Pydantic schema validation.

These tests ensure the JSONL tracking schema is correctly defined
and validates input appropriately.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

import sys
from pathlib import Path

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from worktree_shared import TrackingEntry


class TestTrackingEntrySchema:
    """Test TrackingEntry Pydantic model."""

    def test_valid_entry_minimal(self):
        """Test creating entry with minimal required fields."""
        entry = TrackingEntry(
            branch="feature/test",
            path="/path/to/worktree",
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
        )
        assert entry.branch == "feature/test"
        assert entry.owner == "test-user"
        assert entry.status == "active"  # default
        assert entry.remote_exists == False  # default
        assert entry.local_worktree == True  # default
        assert entry.remote_ahead == 0  # default

    def test_valid_entry_all_fields(self):
        """Test creating entry with all fields."""
        entry = TrackingEntry(
            branch="feature/login",
            path="/path/to/worktree",
            base="develop",
            owner="Claude",
            purpose="implement OAuth login",
            created="2024-01-15T10:30:00Z",
            status="active",
            last_checked="2024-01-15T12:00:00Z",
            notes="WIP - needs review",
            remote_exists=True,
            local_worktree=True,
            remote_ahead=3,
        )
        assert entry.purpose == "implement OAuth login"
        assert entry.remote_ahead == 3
        assert entry.notes == "WIP - needs review"

    def test_entry_serialization(self):
        """Test entry can be serialized to dict for JSONL."""
        entry = TrackingEntry(
            branch="feature/test",
            path="/path/to/worktree",
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
        )
        data = entry.model_dump()
        assert isinstance(data, dict)
        assert data["branch"] == "feature/test"
        assert "remote_ahead" in data

    def test_entry_from_dict(self):
        """Test entry can be created from dict (JSONL parsing)."""
        data = {
            "branch": "feature/test",
            "path": "/path/to/worktree",
            "base": "main",
            "owner": "test-user",
            "created": "2024-01-15T10:30:00Z",
            "last_checked": "2024-01-15T10:30:00Z",
            "status": "merged",
            "remote_exists": True,
            "local_worktree": False,
            "remote_ahead": 0,
        }
        entry = TrackingEntry.model_validate(data)
        assert entry.branch == "feature/test"
        assert entry.status == "merged"
        assert entry.local_worktree == False

    def test_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            TrackingEntry(
                branch="feature/test",
                # missing path, base, owner, created, last_checked
            )

    def test_empty_branch_name(self):
        """Test that empty branch name is rejected."""
        # The model itself doesn't validate empty strings,
        # but the input validators in the scripts do
        entry = TrackingEntry(
            branch="",  # allowed by schema, validated by script
            path="/path",
            base="main",
            owner="test",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
        )
        assert entry.branch == ""

    def test_remote_ahead_negative(self):
        """Test that negative remote_ahead is technically allowed but unusual."""
        entry = TrackingEntry(
            branch="feature/test",
            path="/path",
            base="main",
            owner="test",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
            remote_ahead=-1,  # -1 often means error state
        )
        assert entry.remote_ahead == -1

    def test_status_values(self):
        """Test various status values are accepted."""
        for status in ["active", "merged", "abandoned", "discovered"]:
            entry = TrackingEntry(
                branch="feature/test",
                path="/path",
                base="main",
                owner="test",
                created="2024-01-15T10:30:00Z",
                last_checked="2024-01-15T10:30:00Z",
                status=status,
            )
            assert entry.status == status

    def test_boolean_fields(self):
        """Test boolean fields accept proper values."""
        entry = TrackingEntry(
            branch="feature/test",
            path="/path",
            base="main",
            owner="test",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
            remote_exists=True,
            local_worktree=False,
        )
        assert entry.remote_exists is True
        assert entry.local_worktree is False

    def test_roundtrip_serialization(self):
        """Test entry survives JSON roundtrip."""
        import json

        original = TrackingEntry(
            branch="feature/test",
            path="/path/to/worktree",
            base="main",
            owner="test-user",
            purpose="testing roundtrip",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
            remote_exists=True,
            local_worktree=True,
            remote_ahead=5,
        )

        # Serialize to JSON string
        json_str = json.dumps(original.model_dump())

        # Parse back
        data = json.loads(json_str)
        restored = TrackingEntry.model_validate(data)

        assert restored.branch == original.branch
        assert restored.owner == original.owner
        assert restored.remote_ahead == original.remote_ahead
        assert restored.purpose == original.purpose
