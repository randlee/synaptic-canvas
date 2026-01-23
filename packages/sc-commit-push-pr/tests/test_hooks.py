#!/usr/bin/env python3
"""Unit tests for preflight hook scripts.

Tests cover:
- Settings file found (exit 0)
- Git-flow detection and auto-creation (exit 0)
- No config anywhere (exit 2)
- Git auth failure (exit 2)
- Logging works correctly
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).parent.parent / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from preflight_utils import (
    PACKAGE_NAME,
    detect_gitflow_branches,
    get_log_dir,
    get_protected_branches,
    get_repo_root,
    load_shared_settings,
    log_preflight,
    run_preflight_check,
    save_shared_settings,
    validate_git_auth,
)


class TestLoadSharedSettings:
    """Tests for load_shared_settings function."""

    def test_load_from_repo_settings(self, tmp_path: Path):
        """Test loading settings from .sc/shared-settings.yaml."""
        # Create repo settings
        sc_dir = tmp_path / ".sc"
        sc_dir.mkdir()
        settings_file = sc_dir / "shared-settings.yaml"
        settings_file.write_text(yaml.dump({
            "git": {"protected_branches": ["main", "develop"]}
        }))

        settings = load_shared_settings(tmp_path)

        assert settings is not None
        assert settings["git"]["protected_branches"] == ["main", "develop"]

    def test_load_from_user_settings_fallback(self, tmp_path: Path, monkeypatch):
        """Test fallback to ~/.sc/shared-settings.yaml."""
        # Create user-global settings
        user_sc_dir = tmp_path / ".sc"
        user_sc_dir.mkdir()
        user_settings = user_sc_dir / "shared-settings.yaml"
        user_settings.write_text(yaml.dump({
            "git": {"protected_branches": ["master"]}
        }))

        # Mock Path.home() to return our temp directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create a different repo root with no settings
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        settings = load_shared_settings(repo_root)

        assert settings is not None
        assert settings["git"]["protected_branches"] == ["master"]

    def test_returns_none_when_no_settings(self, tmp_path: Path, monkeypatch):
        """Test returns None when no settings file exists."""
        # Mock home to avoid reading real user settings
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "empty_home")

        settings = load_shared_settings(tmp_path)

        assert settings is None

    def test_returns_none_for_empty_file(self, tmp_path: Path, monkeypatch):
        """Test returns None for empty settings file."""
        sc_dir = tmp_path / ".sc"
        sc_dir.mkdir()
        settings_file = sc_dir / "shared-settings.yaml"
        settings_file.write_text("")

        # Mock home to avoid fallback
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "empty_home")

        settings = load_shared_settings(tmp_path)

        assert settings is None

    def test_returns_none_for_invalid_yaml(self, tmp_path: Path, monkeypatch):
        """Test returns None for invalid YAML."""
        sc_dir = tmp_path / ".sc"
        sc_dir.mkdir()
        settings_file = sc_dir / "shared-settings.yaml"
        settings_file.write_text("invalid: yaml: content: [")

        monkeypatch.setattr(Path, "home", lambda: tmp_path / "empty_home")

        settings = load_shared_settings(tmp_path)

        assert settings is None


class TestGetProtectedBranches:
    """Tests for get_protected_branches function."""

    def test_extracts_protected_branches(self):
        """Test extracting protected branches from settings."""
        settings = {"git": {"protected_branches": ["main", "develop"]}}

        branches = get_protected_branches(settings)

        assert branches == ["main", "develop"]

    def test_returns_none_for_none_settings(self):
        """Test returns None when settings is None."""
        assert get_protected_branches(None) is None

    def test_returns_none_for_empty_settings(self):
        """Test returns None for empty settings."""
        assert get_protected_branches({}) is None

    def test_returns_none_for_missing_git_key(self):
        """Test returns None when git key is missing."""
        settings = {"other": "value"}

        assert get_protected_branches(settings) is None

    def test_returns_none_for_empty_branches_list(self):
        """Test returns None for empty branches list."""
        settings = {"git": {"protected_branches": []}}

        assert get_protected_branches(settings) is None

    def test_returns_none_for_non_list_branches(self):
        """Test returns None when protected_branches is not a list."""
        settings = {"git": {"protected_branches": "main"}}

        assert get_protected_branches(settings) is None


class TestDetectGitflowBranches:
    """Tests for detect_gitflow_branches function."""

    def test_detects_both_branches(self, monkeypatch):
        """Test detecting both master and develop from git-flow."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            result.returncode = 0
            if "gitflow.branch.master" in cmd:
                result.stdout = "main\n"
            elif "gitflow.branch.develop" in cmd:
                result.stdout = "develop\n"
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        branches = detect_gitflow_branches()

        assert branches == ["main", "develop"]

    def test_detects_only_master(self, monkeypatch):
        """Test detecting only master branch."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "gitflow.branch.master" in cmd:
                result.returncode = 0
                result.stdout = "main\n"
            else:
                result.returncode = 1
                result.stdout = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        branches = detect_gitflow_branches()

        assert branches == ["main"]

    def test_detects_only_develop(self, monkeypatch):
        """Test detecting only develop branch."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "gitflow.branch.develop" in cmd:
                result.returncode = 0
                result.stdout = "develop\n"
            else:
                result.returncode = 1
                result.stdout = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        branches = detect_gitflow_branches()

        assert branches == ["develop"]

    def test_returns_none_when_not_configured(self, monkeypatch):
        """Test returns None when git-flow is not configured."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            result.returncode = 1
            result.stdout = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        branches = detect_gitflow_branches()

        assert branches is None

    def test_handles_subprocess_exception(self, monkeypatch):
        """Test handles subprocess exceptions gracefully."""
        def mock_run(cmd, *args, **kwargs):
            raise subprocess.SubprocessError("Command failed")

        monkeypatch.setattr(subprocess, "run", mock_run)

        branches = detect_gitflow_branches()

        assert branches is None


class TestSaveSharedSettings:
    """Tests for save_shared_settings function."""

    def test_creates_settings_file(self, tmp_path: Path):
        """Test creating a new settings file."""
        settings = {"git": {"protected_branches": ["main", "develop"]}}

        result_path = save_shared_settings(settings, tmp_path)

        assert result_path.exists()
        saved = yaml.safe_load(result_path.read_text())
        assert saved["git"]["protected_branches"] == ["main", "develop"]

    def test_creates_sc_directory(self, tmp_path: Path):
        """Test creates .sc directory if it doesn't exist."""
        settings = {"git": {"protected_branches": ["main"]}}

        save_shared_settings(settings, tmp_path)

        assert (tmp_path / ".sc").is_dir()

    def test_merges_with_existing_settings(self, tmp_path: Path):
        """Test merging with existing settings."""
        # Create existing settings
        sc_dir = tmp_path / ".sc"
        sc_dir.mkdir()
        settings_file = sc_dir / "shared-settings.yaml"
        settings_file.write_text(yaml.dump({
            "other": {"key": "value"},
            "git": {"some_other_setting": True}
        }))

        # Save new settings
        new_settings = {"git": {"protected_branches": ["main"]}}
        save_shared_settings(new_settings, tmp_path)

        # Verify merge
        saved = yaml.safe_load(settings_file.read_text())
        assert saved["other"]["key"] == "value"
        assert saved["git"]["protected_branches"] == ["main"]
        assert saved["git"]["some_other_setting"] is True


class TestValidateGitAuth:
    """Tests for validate_git_auth function."""

    def test_success_with_valid_auth(self, monkeypatch):
        """Test successful git authentication."""
        call_count = 0

        def mock_run(cmd, *args, **kwargs):
            nonlocal call_count
            result = mock.Mock()
            if "get-url" in cmd:
                result.returncode = 0
                result.stdout = "https://github.com/user/repo.git"
            elif "ls-remote" in cmd:
                result.returncode = 0
                result.stdout = "abc123\tHEAD"
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        success, message = validate_git_auth()

        assert success is True
        assert "successful" in message.lower()

    def test_failure_no_remote(self, monkeypatch):
        """Test failure when no origin remote."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            result.returncode = 1
            result.stderr = "fatal: No such remote 'origin'"
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        success, message = validate_git_auth()

        assert success is False
        assert "origin" in message.lower()

    def test_failure_auth_error(self, monkeypatch):
        """Test failure with authentication error."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "get-url" in cmd:
                result.returncode = 0
                result.stdout = "https://github.com/user/repo.git"
            else:
                result.returncode = 128
                result.stderr = "Authentication failed for 'https://github.com/user/repo.git'"
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        success, message = validate_git_auth()

        assert success is False
        assert "authentication" in message.lower()

    def test_failure_permission_denied(self, monkeypatch):
        """Test failure with permission denied."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "get-url" in cmd:
                result.returncode = 0
                result.stdout = "git@github.com:user/repo.git"
            else:
                result.returncode = 128
                result.stderr = "Permission denied (publickey)"
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        success, message = validate_git_auth()

        assert success is False
        assert "authentication" in message.lower() or "denied" in message.lower()

    def test_failure_network_error(self, monkeypatch):
        """Test failure with network error."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "get-url" in cmd:
                result.returncode = 0
                result.stdout = "https://github.com/user/repo.git"
            else:
                result.returncode = 128
                result.stderr = "Could not resolve host: github.com"
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        success, message = validate_git_auth()

        assert success is False
        assert "resolve" in message.lower() or "access" in message.lower()

    def test_handles_timeout(self, monkeypatch):
        """Test handles timeout gracefully."""
        def mock_run(cmd, *args, **kwargs):
            if "get-url" in cmd:
                result = mock.Mock()
                result.returncode = 0
                result.stdout = "https://github.com/user/repo.git"
                return result
            raise subprocess.TimeoutExpired(cmd, 30)

        monkeypatch.setattr(subprocess, "run", mock_run)

        success, message = validate_git_auth()

        assert success is False
        assert "timed out" in message.lower()


class TestLogging:
    """Tests for logging functions."""

    def test_log_preflight_creates_log_file(self, tmp_path: Path):
        """Test that log_preflight creates a log file."""
        log_path = log_preflight(
            level="info",
            message="Test message",
            context={"key": "value"},
            repo_root=tmp_path,
        )

        assert log_path.exists()

    def test_log_preflight_correct_format(self, tmp_path: Path):
        """Test that log entries have correct format."""
        log_path = log_preflight(
            level="error",
            message="Test error",
            context={"error_code": "TEST.ERROR"},
            repo_root=tmp_path,
        )

        content = log_path.read_text()
        entry = json.loads(content.strip())

        assert "timestamp" in entry
        assert entry["level"] == "error"
        assert entry["message"] == "Test error"
        assert entry["context"]["error_code"] == "TEST.ERROR"

    def test_log_preflight_appends_to_file(self, tmp_path: Path):
        """Test that multiple log entries are appended."""
        log_preflight(level="info", message="First", repo_root=tmp_path)
        log_preflight(level="info", message="Second", repo_root=tmp_path)

        log_dir = tmp_path / ".claude" / "state" / "logs" / PACKAGE_NAME
        log_files = list(log_dir.glob("preflight-*.jsonl"))
        assert len(log_files) == 1

        lines = log_files[0].read_text().strip().split("\n")
        assert len(lines) == 2

        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["message"] == "First"
        assert second["message"] == "Second"

    def test_get_log_dir_creates_directory(self, tmp_path: Path):
        """Test that get_log_dir creates the directory."""
        log_dir = get_log_dir(tmp_path)

        assert log_dir.exists()
        assert log_dir.is_dir()
        assert log_dir == tmp_path / ".claude" / "state" / "logs" / PACKAGE_NAME


class TestRunPreflightCheck:
    """Integration tests for run_preflight_check function."""

    def test_exit_0_with_settings_file(self, tmp_path: Path, monkeypatch, capsys):
        """Test exit 0 when settings file exists."""
        # Setup repo with settings
        sc_dir = tmp_path / ".sc"
        sc_dir.mkdir()
        settings_file = sc_dir / "shared-settings.yaml"
        settings_file.write_text(yaml.dump({
            "git": {"protected_branches": ["main", "develop"]}
        }))

        # Mock git commands
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "rev-parse" in cmd and "--show-toplevel" in cmd:
                result.returncode = 0
                result.stdout = str(tmp_path)
                return result
            if "get-url" in cmd:
                result.returncode = 0
                result.stdout = "https://github.com/user/repo.git"
                return result
            if "ls-remote" in cmd:
                result.returncode = 0
                result.stdout = "abc123\tHEAD"
                return result
            result.returncode = 0
            result.stdout = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        exit_code = run_preflight_check("test_hook")

        assert exit_code == 0

        # Verify logging
        log_dir = tmp_path / ".claude" / "state" / "logs" / PACKAGE_NAME
        log_files = list(log_dir.glob("preflight-*.jsonl"))
        assert len(log_files) >= 1

    def test_exit_0_with_gitflow_detection(self, tmp_path: Path, monkeypatch, capsys):
        """Test exit 0 when git-flow is detected and settings auto-created."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "rev-parse" in cmd and "--show-toplevel" in cmd:
                result.returncode = 0
                result.stdout = str(tmp_path)
                return result
            if "gitflow.branch.master" in cmd:
                result.returncode = 0
                result.stdout = "main"
                return result
            if "gitflow.branch.develop" in cmd:
                result.returncode = 0
                result.stdout = "develop"
                return result
            if "get-url" in cmd:
                result.returncode = 0
                result.stdout = "https://github.com/user/repo.git"
                return result
            if "ls-remote" in cmd:
                result.returncode = 0
                result.stdout = "abc123\tHEAD"
                return result
            result.returncode = 1
            result.stdout = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        exit_code = run_preflight_check("test_hook")

        assert exit_code == 0

        # Verify settings file was created
        settings_file = tmp_path / ".sc" / "shared-settings.yaml"
        assert settings_file.exists()

        saved = yaml.safe_load(settings_file.read_text())
        assert "main" in saved["git"]["protected_branches"]
        assert "develop" in saved["git"]["protected_branches"]

    def test_exit_2_no_config(self, tmp_path: Path, monkeypatch, capsys):
        """Test exit 2 when no config anywhere."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "rev-parse" in cmd and "--show-toplevel" in cmd:
                result.returncode = 0
                result.stdout = str(tmp_path)
                return result
            # All other git commands fail (no gitflow)
            result.returncode = 1
            result.stdout = ""
            result.stderr = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        exit_code = run_preflight_check("test_hook")

        assert exit_code == 2

        # Check error message
        captured = capsys.readouterr()
        assert "Protected branches not configured" in captured.err
        assert ".sc/shared-settings.yaml" in captured.err

    def test_exit_2_git_auth_failure(self, tmp_path: Path, monkeypatch, capsys):
        """Test exit 2 when git auth fails."""
        # Setup settings so we pass the config check
        sc_dir = tmp_path / ".sc"
        sc_dir.mkdir()
        settings_file = sc_dir / "shared-settings.yaml"
        settings_file.write_text(yaml.dump({
            "git": {"protected_branches": ["main"]}
        }))

        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "rev-parse" in cmd and "--show-toplevel" in cmd:
                result.returncode = 0
                result.stdout = str(tmp_path)
                return result
            if "get-url" in cmd:
                result.returncode = 0
                result.stdout = "https://github.com/user/repo.git"
                return result
            if "ls-remote" in cmd:
                result.returncode = 128
                result.stderr = "Authentication failed"
                return result
            result.returncode = 0
            result.stdout = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        exit_code = run_preflight_check("test_hook")

        assert exit_code == 2

        # Check error message
        captured = capsys.readouterr()
        assert "authentication" in captured.err.lower()

        # Verify error was logged
        log_dir = tmp_path / ".claude" / "state" / "logs" / PACKAGE_NAME
        log_files = list(log_dir.glob("preflight-*.jsonl"))
        assert len(log_files) >= 1

        log_content = log_files[0].read_text()
        assert "GIT.AUTH" in log_content

    def test_logging_contains_hook_name(self, tmp_path: Path, monkeypatch):
        """Test that log entries contain the hook name."""
        sc_dir = tmp_path / ".sc"
        sc_dir.mkdir()
        settings_file = sc_dir / "shared-settings.yaml"
        settings_file.write_text(yaml.dump({
            "git": {"protected_branches": ["main"]}
        }))

        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            if "rev-parse" in cmd and "--show-toplevel" in cmd:
                result.returncode = 0
                result.stdout = str(tmp_path)
                return result
            if "get-url" in cmd:
                result.returncode = 0
                result.stdout = "https://github.com/user/repo.git"
                return result
            if "ls-remote" in cmd:
                result.returncode = 0
                result.stdout = "abc123\tHEAD"
                return result
            result.returncode = 0
            result.stdout = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        run_preflight_check("my_custom_hook")

        log_dir = tmp_path / ".claude" / "state" / "logs" / PACKAGE_NAME
        log_files = list(log_dir.glob("preflight-*.jsonl"))
        log_content = log_files[0].read_text()

        assert "my_custom_hook" in log_content


class TestCommitPushAgentStartHook:
    """Tests for commit_push_agent_start_hook.py script."""

    def test_hook_script_imports(self):
        """Test that the hook script can be imported."""
        # This verifies the script is syntactically correct
        import commit_push_agent_start_hook
        assert hasattr(commit_push_agent_start_hook, "main")

    def test_hook_script_main_calls_preflight(self, monkeypatch):
        """Test that main() calls run_preflight_check with correct hook name."""
        import commit_push_agent_start_hook

        called_with = []

        def mock_preflight(hook_name):
            called_with.append(hook_name)
            return 0

        monkeypatch.setattr(
            "commit_push_agent_start_hook.run_preflight_check",
            mock_preflight
        )

        result = commit_push_agent_start_hook.main()

        assert result == 0
        assert called_with == ["commit_push_agent_start"]


class TestCreatePrAgentStartHook:
    """Tests for create_pr_agent_start_hook.py script."""

    def test_hook_script_imports(self):
        """Test that the hook script can be imported."""
        import create_pr_agent_start_hook
        assert hasattr(create_pr_agent_start_hook, "main")

    def test_hook_script_main_calls_preflight(self, monkeypatch):
        """Test that main() calls run_preflight_check with correct hook name."""
        import create_pr_agent_start_hook

        called_with = []

        def mock_preflight(hook_name):
            called_with.append(hook_name)
            return 0

        monkeypatch.setattr(
            "create_pr_agent_start_hook.run_preflight_check",
            mock_preflight
        )

        result = create_pr_agent_start_hook.main()

        assert result == 0
        assert called_with == ["create_pr_agent_start"]


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_yaml_with_non_dict_git_key(self):
        """Test handles settings where git key is not a dict."""
        settings = {"git": "not a dict"}

        branches = get_protected_branches(settings)

        assert branches is None

    def test_log_preflight_handles_special_characters(self, tmp_path: Path):
        """Test logging handles special characters in messages."""
        message = 'Test with "quotes" and\nnewlines\tand\ttabs'

        log_path = log_preflight(
            level="info",
            message=message,
            context={"path": "/some/path/with spaces"},
            repo_root=tmp_path,
        )

        content = log_path.read_text()
        entry = json.loads(content.strip())
        assert entry["message"] == message

    def test_save_settings_with_existing_invalid_yaml(self, tmp_path: Path):
        """Test save_shared_settings handles existing invalid YAML gracefully."""
        sc_dir = tmp_path / ".sc"
        sc_dir.mkdir()
        settings_file = sc_dir / "shared-settings.yaml"
        settings_file.write_text("invalid: yaml: [")

        # Should overwrite the invalid file
        new_settings = {"git": {"protected_branches": ["main"]}}
        save_shared_settings(new_settings, tmp_path)

        saved = yaml.safe_load(settings_file.read_text())
        assert saved["git"]["protected_branches"] == ["main"]

    def test_validate_git_auth_handles_general_exception(self, monkeypatch):
        """Test validate_git_auth handles unexpected exceptions."""
        def mock_run(cmd, *args, **kwargs):
            raise RuntimeError("Unexpected error")

        monkeypatch.setattr(subprocess, "run", mock_run)

        success, message = validate_git_auth()

        assert success is False
        assert "error" in message.lower()


class TestGetRepoRoot:
    """Tests for get_repo_root function."""

    def test_returns_repo_root(self, monkeypatch):
        """Test returns correct repo root."""
        def mock_run(cmd, *args, **kwargs):
            result = mock.Mock()
            result.returncode = 0
            result.stdout = "/path/to/repo\n"
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        root = get_repo_root()

        assert root == Path("/path/to/repo")

    def test_raises_for_non_git_directory(self, monkeypatch):
        """Test raises RuntimeError when not in git repo."""
        def mock_run(cmd, *args, **kwargs):
            raise subprocess.CalledProcessError(
                128, cmd, stderr="fatal: not a git repository"
            )

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(RuntimeError, match="Not in a git repository"):
            get_repo_root()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
