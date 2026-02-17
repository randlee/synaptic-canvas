"""Tests for JSONL tracking file operations.

These tests ensure JSONL files are read and written correctly,
handling edge cases like empty files, malformed lines, etc.
"""

import pytest
import json
import tempfile
from pathlib import Path

import sys

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from worktree_shared import (
    TrackingEntry,
    load_tracking_jsonl,
    save_tracking_jsonl,
    add_tracking_entry,
    update_tracking_entry,
    remove_tracking_entry,
    get_default_tracking_path,
)


class TestLoadTrackingJsonl:
    """Test loading JSONL tracking files."""

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file returns empty list."""
        path = tmp_path / "nonexistent.jsonl"
        entries = load_tracking_jsonl(path)
        assert entries == []

    def test_load_empty_file(self, tmp_path):
        """Test loading empty file returns empty list."""
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        entries = load_tracking_jsonl(path)
        assert entries == []

    def test_load_single_entry(self, tmp_path):
        """Test loading file with single entry."""
        path = tmp_path / "single.jsonl"
        entry_data = {
            "branch": "feature/test",
            "path": "/path/to/wt",
            "base": "main",
            "owner": "test-user",
            "purpose": "",
            "created": "2024-01-15T10:30:00Z",
            "status": "active",
            "last_checked": "2024-01-15T10:30:00Z",
            "notes": "",
            "remote_exists": False,
            "local_worktree": True,
            "remote_ahead": 0,
        }
        path.write_text(json.dumps(entry_data) + "\n")
        entries = load_tracking_jsonl(path)
        assert len(entries) == 1
        assert entries[0].branch == "feature/test"

    def test_load_multiple_entries(self, tmp_path):
        """Test loading file with multiple entries."""
        path = tmp_path / "multi.jsonl"
        entries_data = [
            {"branch": "feature/a", "path": "/a", "base": "main", "owner": "user1",
             "purpose": "", "created": "2024-01-15T10:30:00Z", "status": "active",
             "last_checked": "2024-01-15T10:30:00Z", "notes": "",
             "remote_exists": True, "local_worktree": True, "remote_ahead": 0},
            {"branch": "feature/b", "path": "/b", "base": "main", "owner": "user2",
             "purpose": "", "created": "2024-01-15T11:30:00Z", "status": "active",
             "last_checked": "2024-01-15T11:30:00Z", "notes": "",
             "remote_exists": False, "local_worktree": True, "remote_ahead": 0},
        ]
        content = "\n".join(json.dumps(e) for e in entries_data) + "\n"
        path.write_text(content)

        entries = load_tracking_jsonl(path)
        assert len(entries) == 2
        assert entries[0].branch == "feature/a"
        assert entries[1].branch == "feature/b"

    def test_load_skips_malformed_lines(self, tmp_path):
        """Test that malformed JSON lines are skipped."""
        path = tmp_path / "malformed.jsonl"
        valid_entry = {"branch": "feature/valid", "path": "/valid", "base": "main",
                       "owner": "user", "purpose": "", "created": "2024-01-15T10:30:00Z",
                       "status": "active", "last_checked": "2024-01-15T10:30:00Z",
                       "notes": "", "remote_exists": False, "local_worktree": True,
                       "remote_ahead": 0}
        content = f"""
{json.dumps(valid_entry)}
not valid json
{{"incomplete": true
"""
        path.write_text(content)

        entries = load_tracking_jsonl(path)
        assert len(entries) == 1
        assert entries[0].branch == "feature/valid"

    def test_load_skips_empty_lines(self, tmp_path):
        """Test that empty lines are skipped."""
        path = tmp_path / "empty_lines.jsonl"
        entry_data = {"branch": "feature/test", "path": "/test", "base": "main",
                      "owner": "user", "purpose": "", "created": "2024-01-15T10:30:00Z",
                      "status": "active", "last_checked": "2024-01-15T10:30:00Z",
                      "notes": "", "remote_exists": False, "local_worktree": True,
                      "remote_ahead": 0}
        content = f"\n\n{json.dumps(entry_data)}\n\n\n"
        path.write_text(content)

        entries = load_tracking_jsonl(path)
        assert len(entries) == 1


class TestSaveTrackingJsonl:
    """Test saving JSONL tracking files."""

    def test_save_empty_list(self, tmp_path):
        """Test saving empty list creates empty file."""
        path = tmp_path / "empty.jsonl"
        save_tracking_jsonl(path, [])
        assert path.exists()
        assert path.read_text() == ""

    def test_save_creates_parent_dirs(self, tmp_path):
        """Test save creates parent directories if needed."""
        path = tmp_path / "subdir" / "deep" / "tracking.jsonl"
        entry = TrackingEntry(
            branch="feature/test", path="/test", base="main", owner="user",
            created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(path, [entry])
        assert path.exists()

    def test_save_single_entry(self, tmp_path):
        """Test saving single entry."""
        path = tmp_path / "single.jsonl"
        entry = TrackingEntry(
            branch="feature/test", path="/test", base="main", owner="user",
            created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(path, [entry])

        content = path.read_text()
        lines = [l for l in content.strip().split("\n") if l]
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["branch"] == "feature/test"

    def test_save_overwrites_existing(self, tmp_path):
        """Test save overwrites existing content."""
        path = tmp_path / "overwrite.jsonl"
        path.write_text("old content\n")

        entry = TrackingEntry(
            branch="feature/new", path="/new", base="main", owner="user",
            created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(path, [entry])

        content = path.read_text()
        assert "old content" not in content
        assert "feature/new" in content

    def test_save_load_roundtrip(self, tmp_path):
        """Test entries survive save/load roundtrip."""
        path = tmp_path / "roundtrip.jsonl"
        original = [
            TrackingEntry(branch="feature/a", path="/a", base="main", owner="user1",
                          created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
                          remote_exists=True, remote_ahead=5),
            TrackingEntry(branch="feature/b", path="/b", base="develop", owner="user2",
                          created="2024-01-15T11:30:00Z", last_checked="2024-01-15T11:30:00Z",
                          local_worktree=False),
        ]

        save_tracking_jsonl(path, original)
        loaded = load_tracking_jsonl(path)

        assert len(loaded) == 2
        assert loaded[0].branch == "feature/a"
        assert loaded[0].remote_ahead == 5
        assert loaded[1].local_worktree == False


class TestAddTrackingEntry:
    """Test appending entries to JSONL file."""

    def test_add_to_nonexistent_file(self, tmp_path):
        """Test adding to non-existent file creates it."""
        path = tmp_path / "new.jsonl"
        entry = TrackingEntry(
            branch="feature/test", path="/test", base="main", owner="user",
            created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
        )
        add_tracking_entry(path, entry)

        assert path.exists()
        entries = load_tracking_jsonl(path)
        assert len(entries) == 1

    def test_add_appends_to_existing(self, tmp_path):
        """Test adding appends to existing file."""
        path = tmp_path / "existing.jsonl"
        entry1 = TrackingEntry(
            branch="feature/first", path="/first", base="main", owner="user",
            created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(path, [entry1])

        entry2 = TrackingEntry(
            branch="feature/second", path="/second", base="main", owner="user",
            created="2024-01-15T11:30:00Z", last_checked="2024-01-15T11:30:00Z",
        )
        add_tracking_entry(path, entry2)

        entries = load_tracking_jsonl(path)
        assert len(entries) == 2
        assert entries[0].branch == "feature/first"
        assert entries[1].branch == "feature/second"


class TestUpdateTrackingEntry:
    """Test updating entries in JSONL file."""

    def test_update_existing_entry(self, tmp_path):
        """Test updating an existing entry."""
        path = tmp_path / "update.jsonl"
        entry = TrackingEntry(
            branch="feature/test", path="/test", base="main", owner="user",
            created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
            remote_exists=False, remote_ahead=0,
        )
        save_tracking_jsonl(path, [entry])

        result = update_tracking_entry(path, "feature/test", {
            "remote_exists": True,
            "remote_ahead": 3,
            "last_checked": "2024-01-15T15:00:00Z",
        })

        assert result == True
        entries = load_tracking_jsonl(path)
        assert entries[0].remote_exists == True
        assert entries[0].remote_ahead == 3

    def test_update_nonexistent_entry(self, tmp_path):
        """Test updating non-existent entry returns False."""
        path = tmp_path / "update.jsonl"
        entry = TrackingEntry(
            branch="feature/existing", path="/test", base="main", owner="user",
            created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(path, [entry])

        result = update_tracking_entry(path, "feature/nonexistent", {
            "remote_exists": True,
        })

        assert result == False

    def test_update_preserves_other_entries(self, tmp_path):
        """Test update doesn't affect other entries."""
        path = tmp_path / "update.jsonl"
        entries = [
            TrackingEntry(branch="feature/a", path="/a", base="main", owner="user",
                          created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z"),
            TrackingEntry(branch="feature/b", path="/b", base="main", owner="user",
                          created="2024-01-15T11:30:00Z", last_checked="2024-01-15T11:30:00Z"),
        ]
        save_tracking_jsonl(path, entries)

        update_tracking_entry(path, "feature/a", {"status": "merged"})

        loaded = load_tracking_jsonl(path)
        assert loaded[0].status == "merged"
        assert loaded[1].status == "active"  # unchanged


class TestRemoveTrackingEntry:
    """Test removing entries from JSONL file."""

    def test_remove_existing_entry(self, tmp_path):
        """Test removing an existing entry."""
        path = tmp_path / "remove.jsonl"
        entries = [
            TrackingEntry(branch="feature/a", path="/a", base="main", owner="user",
                          created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z"),
            TrackingEntry(branch="feature/b", path="/b", base="main", owner="user",
                          created="2024-01-15T11:30:00Z", last_checked="2024-01-15T11:30:00Z"),
        ]
        save_tracking_jsonl(path, entries)

        result = remove_tracking_entry(path, "feature/a")

        assert result == True
        loaded = load_tracking_jsonl(path)
        assert len(loaded) == 1
        assert loaded[0].branch == "feature/b"

    def test_remove_nonexistent_entry(self, tmp_path):
        """Test removing non-existent entry returns False."""
        path = tmp_path / "remove.jsonl"
        entry = TrackingEntry(
            branch="feature/existing", path="/test", base="main", owner="user",
            created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(path, [entry])

        result = remove_tracking_entry(path, "feature/nonexistent")

        assert result == False
        loaded = load_tracking_jsonl(path)
        assert len(loaded) == 1

    def test_remove_last_entry(self, tmp_path):
        """Test removing last entry leaves empty file."""
        path = tmp_path / "remove.jsonl"
        entry = TrackingEntry(
            branch="feature/only", path="/test", base="main", owner="user",
            created="2024-01-15T10:30:00Z", last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(path, [entry])

        result = remove_tracking_entry(path, "feature/only")

        assert result == True
        loaded = load_tracking_jsonl(path)
        assert len(loaded) == 0


class TestGetDefaultTrackingPath:
    """Test default tracking path generation."""

    def test_default_path(self, tmp_path):
        """Test default tracking path is worktree-tracking.jsonl."""
        path = get_default_tracking_path(tmp_path)
        assert path == tmp_path / "worktree-tracking.jsonl"

    def test_path_is_absolute(self, tmp_path):
        """Test returned path is absolute."""
        path = get_default_tracking_path(tmp_path)
        assert path.is_absolute()
