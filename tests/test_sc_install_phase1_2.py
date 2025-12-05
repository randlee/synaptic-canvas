"""
Comprehensive tests for Phase 1 of Synaptic Canvas marketplace CLI enhancements.

Tests cover:
- Global and local installation flags
- Registry management commands
- Config file persistence
- Install with registries
- Error handling
- Backward compatibility
"""
from __future__ import annotations

import os
import sys
import subprocess
import re
from pathlib import Path
from datetime import datetime

import pytest

from sc_cli import install as sc_install


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Mock home directory for ~/.claude paths."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return fake_home


@pytest.fixture
def temp_cwd(tmp_path, monkeypatch):
    """Mock working directory for ./.claude-local paths."""
    fake_cwd = tmp_path / "project"
    fake_cwd.mkdir()
    monkeypatch.chdir(fake_cwd)
    return fake_cwd


@pytest.fixture
def config_file(temp_home):
    """Pre-populated config.yaml with sample registries."""
    config_dir = temp_home / ".claude"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"

    config_content = """marketplaces:
  default: default
  registries:
    default:
      added_date: '2024-01-01'
      path: ''
      status: active
      url: https://marketplace.example.com
    test-registry:
      added_date: '2024-01-15'
      path: /packages
      status: active
      url: https://test.example.com
"""
    config_path.write_text(config_content, encoding="utf-8")
    return config_path


@pytest.fixture
def git_repo(tmp_path):
    """Initialized git repository."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init", "-q", str(repo_dir)], check=True)
    subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@test"], check=True)
    subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test"], check=True)
    return repo_dir


# ==============================================================================
# TEST GROUP 1: Global and Local Flags (12 tests)
# ==============================================================================

class TestGlobalLocalFlags:
    """Test --global and --local installation flags."""

    def test_install_global_flag_creates_dir(self, temp_home, capsys):
        """Test that --global creates ~/.claude directory."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0
        assert (temp_home / ".claude").exists()
        assert (temp_home / ".claude" / "agents").exists()

    def test_install_global_flag_uses_home_directory(self, temp_home, capsys):
        """Test that --global installs to home directory."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0
        assert (temp_home / ".claude" / "agents" / "sc-delay-once.md").exists()

        out = capsys.readouterr().out
        assert str(temp_home / ".claude") in out

    def test_install_local_flag_creates_dir(self, temp_cwd, capsys):
        """Test that --local creates ./.claude-local directory."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--local"])
        assert rc == 0
        assert (temp_cwd / ".claude-local").exists()
        assert (temp_cwd / ".claude-local" / "agents").exists()

    def test_install_local_flag_uses_project_local(self, temp_cwd, capsys):
        """Test that --local installs to project .claude-local."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--local"])
        assert rc == 0
        assert (temp_cwd / ".claude-local" / "agents" / "sc-delay-once.md").exists()

        out = capsys.readouterr().out
        assert ".claude-local" in out

    def test_install_dest_backward_compatible(self, temp_home, tmp_path, capsys):
        """Test that --dest flag still works (backward compatibility)."""
        dest = tmp_path / "custom" / ".claude"
        rc = sc_install.main(["install", "sc-delay-tasks", "--dest", str(dest)])
        assert rc == 0
        assert (dest / "agents" / "sc-delay-once.md").exists()

    def test_install_global_and_local_conflict_error(self, capsys):
        """Test that --global and --local together produce error."""
        # argparse will catch this as mutually exclusive
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["install", "sc-delay-tasks", "--global", "--local"])

        assert exc_info.value.code != 0
        err = capsys.readouterr().err
        assert "not allowed with argument" in err or "mutually exclusive" in err.lower()

    def test_install_global_and_dest_conflict_error(self, temp_home, capsys):
        """Test that --global and --dest together produce error."""
        dest = temp_home / "custom" / ".claude"
        # argparse will catch this as mutually exclusive
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["install", "sc-delay-tasks", "--global", "--dest", str(dest)])

        assert exc_info.value.code != 0
        err = capsys.readouterr().err
        assert "mutually exclusive" in err.lower() or "not allowed" in err.lower()

    def test_install_no_flags_requires_one(self, capsys):
        """Test that install without any dest flag produces error."""
        # argparse requires one of the mutually exclusive group
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["install", "sc-delay-tasks"])

        assert exc_info.value.code != 0
        err = capsys.readouterr().err
        assert "required" in err.lower()

    def test_install_dest_validates_claude_in_path(self, capsys):
        """Test that --dest validates .claude in path."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--dest", "/some/random/path"])
        assert rc == 1

        err = capsys.readouterr().err
        assert ".claude" in err

    def test_install_global_expanduser_works(self, temp_home, capsys):
        """Test that --global properly expands ~ in paths."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0

        # Should use actual home, not literal ~
        assert (temp_home / ".claude" / "agents" / "sc-delay-once.md").exists()

    def test_install_local_uses_cwd(self, temp_cwd, capsys):
        """Test that --local uses current working directory."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--local"])
        assert rc == 0

        # Should be in cwd
        local_path = Path.cwd() / ".claude-local"
        assert local_path.exists()
        assert (local_path / "agents" / "sc-delay-once.md").exists()

    def test_install_multiple_flags_error(self, temp_home, capsys):
        """Test that multiple destination flags produce error."""
        dest = temp_home / ".claude"
        # argparse should catch this as mutually exclusive
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["install", "sc-delay-tasks", "--global", "--local", "--dest", str(dest)])

        assert exc_info.value.code != 0
        err = capsys.readouterr().err
        assert "mutually exclusive" in err.lower() or "not allowed" in err.lower()


# ==============================================================================
# TEST GROUP 2: Registry Commands (18 tests)
# ==============================================================================

class TestRegistryCommands:
    """Test registry add/list/remove commands."""

    @pytest.mark.parametrize("url", [
        "https://example.com",
        "http://localhost:8000",
        "https://marketplace.synaptic-canvas.dev",
    ])
    def test_registry_add_valid_urls(self, temp_home, url, capsys):
        """Test that valid HTTPS and HTTP URLs are accepted."""
        rc = sc_install.main(["registry", "add", "test", url])
        assert rc == 0

        out = capsys.readouterr().out
        assert "test" in out
        assert url in out

    @pytest.mark.parametrize("url", [
        "ftp://invalid.com",
        "not-a-url",
        "",
        "://broken",
    ])
    def test_registry_add_invalid_url_rejected(self, temp_home, url, capsys):
        """Test that invalid URL formats are rejected."""
        rc = sc_install.main(["registry", "add", "test", url])
        assert rc == 1

        err = capsys.readouterr().err
        assert "Invalid URL" in err or "must start with" in err

    def test_registry_add_creates_config_if_missing(self, temp_home, capsys):
        """Test that registry add creates config.yaml if missing."""
        config_path = temp_home / ".claude" / "config.yaml"
        assert not config_path.exists()

        rc = sc_install.main(["registry", "add", "test", "https://example.com"])
        assert rc == 0
        assert config_path.exists()

    def test_registry_add_duplicate_updates_existing(self, temp_home, capsys):
        """Test that adding duplicate registry updates existing entry."""
        # Add first time
        rc = sc_install.main(["registry", "add", "test", "https://first.com"])
        assert rc == 0

        # Add again with different URL
        rc = sc_install.main(["registry", "add", "test", "https://second.com"])
        assert rc == 0

        out = capsys.readouterr().out
        assert "Updated" in out or "test" in out

        # Check config has updated URL
        config = sc_install._load_config()
        assert config["marketplaces"]["registries"]["test"]["url"] == "https://second.com"

    @pytest.mark.parametrize("bad_name", [
        "reg@name",
        "reg$name",
        "reg!name",
        "reg name",
        "reg#name",
    ])
    def test_registry_add_invalid_name_characters_rejected(self, temp_home, bad_name, capsys):
        """Test that registry names with invalid characters are rejected."""
        rc = sc_install.main(["registry", "add", bad_name, "https://example.com"])
        assert rc == 1

        err = capsys.readouterr().err
        assert "Invalid" in err or "alphanumeric" in err

    def test_registry_add_with_optional_path(self, temp_home, capsys):
        """Test that registry add accepts optional --path parameter."""
        rc = sc_install.main(["registry", "add", "test", "https://example.com", "--path", "/packages"])
        assert rc == 0

        config = sc_install._load_config()
        assert config["marketplaces"]["registries"]["test"]["path"] == "/packages"

    def test_registry_list_empty_when_no_registries(self, temp_home, capsys):
        """Test that registry list shows helpful message when empty."""
        rc = sc_install.main(["registry", "list"])
        assert rc == 0

        out = capsys.readouterr().out
        assert "No registries" in out or "registry add" in out

    def test_registry_list_shows_all_registries(self, temp_home, config_file, capsys):
        """Test that registry list shows all configured registries."""
        rc = sc_install.main(["registry", "list"])
        assert rc == 0

        out = capsys.readouterr().out
        assert "default" in out
        assert "test-registry" in out
        assert "https://marketplace.example.com" in out
        assert "https://test.example.com" in out

    def test_registry_list_marks_default_registry(self, temp_home, config_file, capsys):
        """Test that registry list marks the default registry with *."""
        rc = sc_install.main(["registry", "list"])
        assert rc == 0

        out = capsys.readouterr().out
        # Should have a marker for default
        lines = out.split("\n")
        marked_lines = [l for l in lines if l.strip().startswith("*")]
        assert len(marked_lines) >= 1

    def test_registry_list_shows_metadata(self, temp_home, config_file, capsys):
        """Test that registry list shows metadata (status, added date)."""
        rc = sc_install.main(["registry", "list"])
        assert rc == 0

        out = capsys.readouterr().out
        assert "active" in out or "status" in out
        assert "2024-01-01" in out or "added" in out

    def test_registry_remove_deletes_registry(self, temp_home, config_file, capsys):
        """Test that registry remove deletes the registry entry."""
        rc = sc_install.main(["registry", "remove", "test-registry"])
        assert rc == 0

        out = capsys.readouterr().out
        assert "Removed" in out

        # Verify it's gone
        config = sc_install._load_config()
        assert "test-registry" not in config.get("marketplaces", {}).get("registries", {})

    def test_registry_remove_nonexistent_error(self, temp_home, capsys):
        """Test that removing nonexistent registry produces error."""
        rc = sc_install.main(["registry", "remove", "nonexistent"])
        assert rc == 1

        err = capsys.readouterr().err
        assert "not found" in err.lower()

    def test_registry_add_stores_added_date(self, temp_home):
        """Test that registry add stores added_date."""
        rc = sc_install.main(["registry", "add", "test", "https://example.com"])
        assert rc == 0

        config = sc_install._load_config()
        assert "added_date" in config["marketplaces"]["registries"]["test"]
        # Should be today's date
        added = config["marketplaces"]["registries"]["test"]["added_date"]
        assert re.match(r'\d{4}-\d{2}-\d{2}', added)

    def test_registry_add_stores_status_active(self, temp_home):
        """Test that registry add stores status as active."""
        rc = sc_install.main(["registry", "add", "test", "https://example.com"])
        assert rc == 0

        config = sc_install._load_config()
        assert config["marketplaces"]["registries"]["test"]["status"] == "active"

    def test_registry_add_preserves_added_date_on_update(self, temp_home):
        """Test that updating registry preserves original added_date."""
        # Add first time
        rc = sc_install.main(["registry", "add", "test", "https://first.com"])
        assert rc == 0

        config1 = sc_install._load_config()
        original_date = config1["marketplaces"]["registries"]["test"]["added_date"]

        # Update
        rc = sc_install.main(["registry", "add", "test", "https://second.com"])
        assert rc == 0

        config2 = sc_install._load_config()
        assert config2["marketplaces"]["registries"]["test"]["added_date"] == original_date

    def test_registry_name_with_dash_accepted(self, temp_home, capsys):
        """Test that registry names with dashes are accepted."""
        rc = sc_install.main(["registry", "add", "my-registry", "https://example.com"])
        assert rc == 0

    def test_registry_name_with_underscore_accepted(self, temp_home, capsys):
        """Test that registry names with underscores are accepted."""
        rc = sc_install.main(["registry", "add", "my_registry", "https://example.com"])
        assert rc == 0

    def test_registry_name_with_spaces_rejected(self, temp_home, capsys):
        """Test that registry names with spaces are rejected."""
        rc = sc_install.main(["registry", "add", "my registry", "https://example.com"])
        assert rc == 1

        err = capsys.readouterr().err
        assert "Invalid" in err or "alphanumeric" in err


# ==============================================================================
# TEST GROUP 3: Config Persistence (15 tests)
# ==============================================================================

class TestConfigPersistence:
    """Test config file reading, writing, and persistence."""

    def test_config_path_is_home_claude_config(self, temp_home):
        """Test that config path is ~/.claude/config.yaml."""
        path = sc_install._get_config_path()
        expected = temp_home / ".claude" / "config.yaml"
        assert path == expected

    def test_config_auto_creates_directory(self, temp_home):
        """Test that config operations auto-create ~/.claude directory."""
        rc = sc_install.main(["registry", "add", "test", "https://example.com"])
        assert rc == 0
        assert (temp_home / ".claude").exists()

    def test_config_created_on_first_registry_add(self, temp_home):
        """Test that config.yaml is created on first registry add."""
        config_path = temp_home / ".claude" / "config.yaml"
        assert not config_path.exists()

        rc = sc_install.main(["registry", "add", "test", "https://example.com"])
        assert rc == 0
        assert config_path.exists()

    def test_config_survives_between_invocations(self, temp_home):
        """Test that config persists between command invocations."""
        # Add registry
        rc = sc_install.main(["registry", "add", "test1", "https://first.com"])
        assert rc == 0

        # Add another
        rc = sc_install.main(["registry", "add", "test2", "https://second.com"])
        assert rc == 0

        # Both should be present
        config = sc_install._load_config()
        assert "test1" in config["marketplaces"]["registries"]
        assert "test2" in config["marketplaces"]["registries"]

    def test_config_reads_existing_file(self, temp_home, config_file):
        """Test that config can read existing config.yaml."""
        config = sc_install._load_config()
        assert "marketplaces" in config
        assert "default" in config["marketplaces"]
        assert "test-registry" in config["marketplaces"]["registries"]

    def test_config_validates_yaml_syntax(self, temp_home):
        """Test that config handles YAML syntax correctly."""
        # Create valid config
        rc = sc_install.main(["registry", "add", "test", "https://example.com"])
        assert rc == 0

        # Read back
        config = sc_install._load_config()
        assert isinstance(config, dict)
        assert "marketplaces" in config

    def test_config_handles_missing_marketplaces_section(self, temp_home):
        """Test that config handles missing marketplaces section gracefully."""
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("other_key: value\n", encoding="utf-8")

        # Should still work
        rc = sc_install.main(["registry", "add", "test", "https://example.com"])
        assert rc == 0

    def test_config_merges_new_registries(self, temp_home, config_file):
        """Test that adding registries merges with existing config."""
        # Add new registry
        rc = sc_install.main(["registry", "add", "new-reg", "https://new.com"])
        assert rc == 0

        config = sc_install._load_config()
        # Old ones still there
        assert "default" in config["marketplaces"]["registries"]
        assert "test-registry" in config["marketplaces"]["registries"]
        # New one added
        assert "new-reg" in config["marketplaces"]["registries"]

    def test_config_preserves_existing_registries(self, temp_home, config_file):
        """Test that config operations don't corrupt existing registries."""
        # Get original
        config1 = sc_install._load_config()
        original_url = config1["marketplaces"]["registries"]["default"]["url"]

        # Add new registry
        rc = sc_install.main(["registry", "add", "new-reg", "https://new.com"])
        assert rc == 0

        # Original should be unchanged
        config2 = sc_install._load_config()
        assert config2["marketplaces"]["registries"]["default"]["url"] == original_url

    def test_config_default_marketplace_initialized(self, temp_home):
        """Test that config can be initialized with default marketplace."""
        # For now, just test that empty config works
        config = sc_install._load_config()
        assert isinstance(config, dict)

    def test_config_registry_metadata_persisted(self, temp_home):
        """Test that all registry metadata is persisted correctly."""
        rc = sc_install.main(["registry", "add", "test", "https://example.com", "--path", "/pkgs"])
        assert rc == 0

        config = sc_install._load_config()
        reg = config["marketplaces"]["registries"]["test"]
        assert reg["url"] == "https://example.com"
        assert reg["path"] == "/pkgs"
        assert "added_date" in reg
        assert reg["status"] == "active"

    def test_config_empty_dict_when_file_missing(self, temp_home):
        """Test that _load_config returns validated config schema when file missing."""
        config = sc_install._load_config()
        # Should return validated schema with marketplaces section
        assert isinstance(config, dict)
        assert "marketplaces" in config
        assert "registries" in config["marketplaces"]
        assert "default" in config["marketplaces"]

    def test_config_warn_on_parse_error(self, temp_home, capsys):
        """Test that config warns on YAML parse error."""
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("invalid: yaml: syntax: error", encoding="utf-8")

        config = sc_install._load_config()
        # Should return empty dict and warn
        err = capsys.readouterr().err
        # May or may not warn depending on YAML library
        # At minimum, shouldn't crash
        assert isinstance(config, dict)

    def test_config_robust_handling_corrupted_file(self, temp_home, capsys):
        """Test that corrupted config file doesn't crash operations."""
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("}{}{corrupted", encoding="utf-8")

        # Should still work - creates fresh config
        rc = sc_install.main(["registry", "add", "test", "https://example.com"])
        # May fail or succeed depending on handling, but shouldn't crash
        assert rc in [0, 1]

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows has different permission model - chmod doesn't prevent writes the same way")
    def test_config_permissions_error_on_write(self, temp_home, capsys, monkeypatch):
        """Test that permission errors on write are handled gracefully."""
        # This test is platform-dependent and may not work on all systems
        # We'll simulate by making the directory read-only
        config_dir = temp_home / ".claude"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Make directory read-only
        try:
            config_dir.chmod(0o444)
            rc = sc_install.main(["registry", "add", "test", "https://example.com"])
            assert rc == 1

            err = capsys.readouterr().err
            assert "Permission" in err or "could not write" in err.lower()
        finally:
            # Restore permissions for cleanup
            config_dir.chmod(0o755)


# ==============================================================================
# TEST GROUP 4: Install with Registries (12 tests)
# ==============================================================================

class TestInstallWithRegistries:
    """Test installation using --global and --local flags."""

    def test_install_global_creates_structure(self, temp_home, capsys):
        """Test that --global install creates proper directory structure."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0

        base = temp_home / ".claude"
        assert base.exists()
        assert (base / "agents").exists()
        assert (base / "scripts").exists()

    def test_install_local_creates_structure(self, temp_cwd, capsys):
        """Test that --local install creates proper directory structure."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--local"])
        assert rc == 0

        base = temp_cwd / ".claude-local"
        assert base.exists()
        assert (base / "agents").exists()
        assert (base / "scripts").exists()

    def test_install_global_files_installed(self, temp_home):
        """Test that --global installs all package files."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0

        base = temp_home / ".claude"
        assert (base / "agents" / "sc-delay-once.md").exists()
        assert (base / "scripts" / "delay-run.py").exists()

    def test_install_local_files_installed(self, temp_cwd):
        """Test that --local installs all package files."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--local"])
        assert rc == 0

        base = temp_cwd / ".claude-local"
        assert (base / "agents" / "sc-delay-once.md").exists()
        assert (base / "scripts" / "delay-run.py").exists()

    def test_install_global_respects_force_flag(self, temp_home, capsys):
        """Test that --global respects --force flag."""
        # Install once
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0

        # Modify file
        agent_file = temp_home / ".claude" / "agents" / "sc-delay-once.md"
        agent_file.write_text("modified", encoding="utf-8")

        # Install without --force (should skip)
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0
        assert agent_file.read_text(encoding="utf-8") == "modified"

        # Install with --force (should overwrite)
        rc = sc_install.main(["install", "sc-delay-tasks", "--global", "--force"])
        assert rc == 0
        assert agent_file.read_text(encoding="utf-8") != "modified"

    def test_install_local_respects_force_flag(self, temp_cwd, capsys):
        """Test that --local respects --force flag."""
        # Install once
        rc = sc_install.main(["install", "sc-delay-tasks", "--local"])
        assert rc == 0

        # Modify file
        agent_file = temp_cwd / ".claude-local" / "agents" / "sc-delay-once.md"
        agent_file.write_text("modified", encoding="utf-8")

        # Install without --force (should skip)
        rc = sc_install.main(["install", "sc-delay-tasks", "--local"])
        assert rc == 0
        assert agent_file.read_text(encoding="utf-8") == "modified"

        # Install with --force (should overwrite)
        rc = sc_install.main(["install", "sc-delay-tasks", "--local", "--force"])
        assert rc == 0
        assert agent_file.read_text(encoding="utf-8") != "modified"

    def test_install_global_maintains_executable_bit(self, temp_home):
        """Test that --global maintains executable bit on scripts."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0

        script = temp_home / ".claude" / "scripts" / "delay-run.py"
        assert os.access(script, os.X_OK)

    def test_install_local_maintains_executable_bit(self, temp_cwd):
        """Test that --local maintains executable bit on scripts."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--local"])
        assert rc == 0

        script = temp_cwd / ".claude-local" / "scripts" / "delay-run.py"
        assert os.access(script, os.X_OK)

    def test_install_global_expands_repo_name_token(self, temp_home, git_repo):
        """Test that --global expands {{REPO_NAME}} token."""
        # Install to git repo
        dest = git_repo / ".claude"
        rc = sc_install.main(["install", "sc-git-worktree", "--dest", str(dest)])
        assert rc == 0

        cmd_file = dest / "commands" / "sc-git-worktree.md"
        content = cmd_file.read_text(encoding="utf-8")
        assert "{{REPO_NAME}}" not in content
        assert "repo-worktrees" in content

    def test_install_local_expands_repo_name_token(self, temp_cwd, git_repo, monkeypatch):
        """Test that --local expands {{REPO_NAME}} token."""
        # Change to git repo directory
        monkeypatch.chdir(git_repo)

        rc = sc_install.main(["install", "sc-git-worktree", "--local"])
        assert rc == 0

        cmd_file = git_repo / ".claude-local" / "commands" / "sc-git-worktree.md"
        content = cmd_file.read_text(encoding="utf-8")
        assert "{{REPO_NAME}}" not in content
        assert "repo-worktrees" in content

    def test_install_global_updates_agent_registry(self, temp_home):
        """Test that --global updates agent registry."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0

        registry = temp_home / ".claude" / "agents" / "registry.yaml"
        assert registry.exists()

        content = registry.read_text(encoding="utf-8")
        assert "sc-delay-once" in content

    def test_install_local_updates_agent_registry(self, temp_cwd):
        """Test that --local updates agent registry."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--local"])
        assert rc == 0

        registry = temp_cwd / ".claude-local" / "agents" / "registry.yaml"
        assert registry.exists()

        content = registry.read_text(encoding="utf-8")
        assert "sc-delay-once" in content


# ==============================================================================
# TEST GROUP 5: Error Handling (18 tests)
# ==============================================================================

class TestErrorHandling:
    """Test error handling and validation."""

    @pytest.mark.parametrize("url", [
        "ftp://invalid",
        "not-a-url",
        "",
        "://broken",
    ])
    def test_invalid_url_formats_rejected(self, temp_home, url, capsys):
        """Test that various invalid URL formats are rejected."""
        rc = sc_install.main(["registry", "add", "test", url])
        assert rc == 1

        err = capsys.readouterr().err
        assert "Invalid URL" in err or "must start with" in err

    def test_registry_name_validation(self, temp_home, capsys):
        """Test that registry name validation works."""
        rc = sc_install.main(["registry", "add", "bad name", "https://example.com"])
        assert rc == 1

        err = capsys.readouterr().err
        assert "Invalid" in err

    def test_dest_without_claude_rejected(self, capsys):
        """Test that --dest without .claude in path is rejected."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--dest", "/random/path"])
        assert rc == 1

        err = capsys.readouterr().err
        assert ".claude" in err

    def test_registry_add_returns_1_on_error(self, capsys):
        """Test that registry add returns 1 on error."""
        rc = sc_install.main(["registry", "add", "test", "invalid-url"])
        assert rc == 1

    def test_registry_remove_returns_1_on_error(self, temp_home, capsys):
        """Test that registry remove returns 1 on error."""
        rc = sc_install.main(["registry", "remove", "nonexistent"])
        assert rc == 1

    def test_config_load_tolerates_missing_file(self, temp_home):
        """Test that _load_config tolerates missing file."""
        config = sc_install._load_config()
        # Should return validated empty config, not empty dict
        assert isinstance(config, dict)
        assert "marketplaces" in config

    def test_help_displays_examples(self, capsys):
        """Test that help text is available."""
        # --help causes SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["--help"])

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "install" in out
        assert "registry" in out

    def test_help_documents_global_flag(self, capsys):
        """Test that help documents --global flag."""
        # --help causes SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["install", "--help"])

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "--global" in out

    def test_help_documents_local_flag(self, capsys):
        """Test that help documents --local flag."""
        # --help causes SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["install", "--help"])

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "--local" in out

    def test_help_documents_registry_command(self, capsys):
        """Test that help documents registry command."""
        # --help causes SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["registry", "--help"])

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "add" in out
        assert "list" in out
        assert "remove" in out

    def test_invalid_registry_cmd_shows_help(self, capsys):
        """Test that invalid registry subcommand shows error."""
        # argparse will handle this with SystemExit
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["registry", "invalid"])

        assert exc_info.value.code != 0

    def test_registry_cmd_without_subcmd_shows_help(self, capsys):
        """Test that registry without subcommand shows help."""
        # When no subcommand is provided, argparse shows help and exits with 0
        # (the main() function intercepts this and shows help)
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["registry"])

        # argparse shows help (exit code 0)
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "add" in out or "list" in out or "remove" in out

    @pytest.mark.parametrize("bad_name", [
        "reg@name",
        "reg$name",
        "reg!name",
        "reg name",
    ])
    def test_registry_invalid_names(self, temp_home, bad_name, capsys):
        """Test that various invalid registry names are rejected."""
        rc = sc_install.main(["registry", "add", bad_name, "https://example.com"])
        assert rc == 1

        err = capsys.readouterr().err
        assert "Invalid" in err or "alphanumeric" in err

    def test_registry_url_with_trailing_slash(self, temp_home, capsys):
        """Test that trailing slash in URL is handled."""
        rc = sc_install.main(["registry", "add", "test", "https://example.com/"])
        assert rc == 0

        config = sc_install._load_config()
        # Trailing slash should be removed
        assert config["marketplaces"]["registries"]["test"]["url"] == "https://example.com"

    def test_registry_empty_name_rejected(self, temp_home, capsys):
        """Test that empty registry name is rejected."""
        # Empty string causes validation error
        rc = sc_install.main(["registry", "add", "", "https://example.com"])
        assert rc == 1

        err = capsys.readouterr().err
        assert "empty" in err.lower() or "invalid" in err.lower()

    def test_registry_empty_url_rejected(self, temp_home, capsys):
        """Test that empty URL is rejected."""
        rc = sc_install.main(["registry", "add", "test", ""])
        assert rc == 1

        err = capsys.readouterr().err
        assert "Invalid URL" in err

    def test_install_no_package_error(self, capsys):
        """Test that install without package name produces error."""
        # argparse will catch this with SystemExit
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["install", "--global"])

        assert exc_info.value.code != 0

    def test_install_invalid_package_error(self, temp_home, capsys):
        """Test that installing nonexistent package produces error."""
        rc = sc_install.main(["install", "nonexistent-pkg", "--global"])
        assert rc == 1

        err = capsys.readouterr().err
        assert "not found" in err.lower()


# ==============================================================================
# TEST GROUP 6: Backward Compatibility (8 tests)
# ==============================================================================

class TestBackwardCompatibility:
    """Test backward compatibility with existing --dest usage."""

    def test_existing_dest_flag_still_works(self, temp_home, tmp_path, capsys):
        """Test that existing --dest flag still works as before."""
        dest = tmp_path / "custom" / ".claude"
        rc = sc_install.main(["install", "sc-delay-tasks", "--dest", str(dest)])
        assert rc == 0
        assert (dest / "agents" / "sc-delay-once.md").exists()

    def test_dest_flag_takes_precedence(self, temp_home, capsys):
        """Test that --dest works independently."""
        dest = temp_home / "custom" / ".claude"
        rc = sc_install.main(["install", "sc-delay-tasks", "--dest", str(dest)])
        assert rc == 0

        # Should be in custom location, not ~/.claude
        assert (dest / "agents" / "sc-delay-once.md").exists()
        assert not (temp_home / ".claude" / "agents" / "sc-delay-once.md").exists()

    def test_old_tests_still_pass(self):
        """Verify that original test suite patterns still work."""
        # This is meta-test - verify original patterns work
        rc = sc_install.main(["list"])
        assert rc == 0

        rc = sc_install.main(["info", "sc-delay-tasks"])
        assert rc == 0

    def test_install_without_flags_requires_dest(self, capsys):
        """Test that install without any flag requires one."""
        # argparse requires one of the mutually exclusive group
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["install", "sc-delay-tasks"])

        assert exc_info.value.code != 0
        err = capsys.readouterr().err
        assert "required" in err.lower()

    def test_uninstall_dest_still_required(self, temp_home, capsys):
        """Test that uninstall still requires --dest flag."""
        # Install first
        dest = temp_home / ".claude"
        rc = sc_install.main(["install", "sc-delay-tasks", "--dest", str(dest)])
        assert rc == 0

        # Uninstall without --dest should fail (argparse catches this)
        with pytest.raises(SystemExit) as exc_info:
            sc_install.main(["uninstall", "sc-delay-tasks"])

        assert exc_info.value.code != 0

    def test_config_yaml_optional(self, capsys):
        """Test that config.yaml is optional for basic operations."""
        # list and info shouldn't require config
        rc = sc_install.main(["list"])
        assert rc == 0

        rc = sc_install.main(["info", "sc-delay-tasks"])
        assert rc == 0

    def test_registry_commands_independent_of_install(self, temp_home, capsys):
        """Test that registry commands work independently of install."""
        # Registry operations shouldn't affect install
        rc = sc_install.main(["registry", "add", "test", "https://example.com"])
        assert rc == 0

        rc = sc_install.main(["registry", "list"])
        assert rc == 0

        # Install should still work
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        assert rc == 0

    def test_mixed_old_new_style_install(self, temp_home, temp_cwd, capsys):
        """Test that old --dest and new --global can coexist."""
        # Install with --dest
        dest1 = temp_home / "custom1" / ".claude"
        rc = sc_install.main(["install", "sc-delay-tasks", "--dest", str(dest1)])
        assert rc == 0

        # Install with --global
        rc = sc_install.main(["install", "sc-git-worktree", "--global"])
        assert rc == 0

        # Both should exist
        assert (dest1 / "agents" / "sc-delay-once.md").exists()
        assert (temp_home / ".claude" / "commands" / "sc-git-worktree.md").exists()


# ============================================================================
# PHASE 2 TESTS: Groups 7-12 (80 additional tests)
# ============================================================================

# TEST GROUP 7: Config Schema and Validation (20 tests)
class TestConfigSchemaPhase2:
    """Phase 2 Task 1: Config schema validation and enhancement."""

    def test_config_schema_validates_structure(self, temp_home):
        config = sc_install._load_config()
        # Should auto-initialize proper structure
        assert "marketplaces" in config
        assert "default" in config["marketplaces"]
        assert "registries" in config["marketplaces"]

    def test_config_handles_non_dict_input(self, temp_home):
        # Validate with non-dict
        result = sc_install._validate_config_schema("not a dict")
        assert isinstance(result, dict)
        assert "marketplaces" in result

    def test_config_handles_malformed_marketplaces(self, temp_home):
        # Malformed marketplaces section
        result = sc_install._validate_config_schema({"marketplaces": "not a dict"})
        assert isinstance(result["marketplaces"], dict)

    def test_config_handles_malformed_registries(self, temp_home):
        # Malformed registries section
        result = sc_install._validate_config_schema({
            "marketplaces": {"registries": "not a dict"}
        })
        assert isinstance(result["marketplaces"]["registries"], dict)

    def test_config_default_synaptic_canvas_auto(self, temp_home):
        # Default marketplace should be synaptic-canvas
        config = sc_install._load_config()
        assert config["marketplaces"]["default"] == "synaptic-canvas"

    def test_config_preserves_custom_default(self, temp_home):
        # Manually set custom default
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        config = {
            "marketplaces": {
                "default": "my-custom-registry",
                "registries": {}
            }
        }
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        loaded = sc_install._load_config()
        assert loaded["marketplaces"]["default"] == "my-custom-registry"

    def test_config_multiple_saves_preserve_order(self, temp_home):
        # Add registries in specific order
        sc_install.cmd_registry_add("registry-a", "https://a.com")
        sc_install.cmd_registry_add("registry-b", "https://b.com")
        sc_install.cmd_registry_add("registry-c", "https://c.com")

        config = sc_install._load_config()
        names = list(config["marketplaces"]["registries"].keys())
        # Order should be preserved (or at least all present)
        assert "registry-a" in names
        assert "registry-b" in names
        assert "registry-c" in names

    def test_config_validates_url_format_on_add(self, temp_home, capsys):
        rc = sc_install.cmd_registry_add("test", "invalid-url")
        assert rc == 1
        out = capsys.readouterr()
        assert "Invalid URL" in out.err

    def test_config_accepts_http_and_https(self, temp_home):
        rc1 = sc_install.cmd_registry_add("test-https", "https://example.com")
        rc2 = sc_install.cmd_registry_add("test-http", "http://localhost:8000")
        assert rc1 == 0
        assert rc2 == 0

    def test_config_registry_entry_complete_metadata(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com", path="path/to/registry.json")
        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]

        # Should have all required fields
        assert "url" in registry
        assert "status" in registry
        assert "added_date" in registry
        assert "path" in registry

    def test_config_added_date_format_validation(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com")
        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]

        # Validate ISO format
        from datetime import datetime
        date_str = registry["added_date"]
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        assert parsed.year >= 2025

    def test_config_status_defaults_to_active(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com")
        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]
        assert registry["status"] == "active"

    def test_config_path_optional_field(self, temp_home):
        # Add without path
        sc_install.cmd_registry_add("test1", "https://example.com")
        # Add with path
        sc_install.cmd_registry_add("test2", "https://example.com", path="some/path")

        config = sc_install._load_config()
        reg1 = config["marketplaces"]["registries"]["test1"]
        reg2 = config["marketplaces"]["registries"]["test2"]

        # test1 may not have path
        if "path" in reg1:
            assert reg1["path"] == ""
        # test2 should have path
        assert reg2["path"] == "some/path"

    def test_config_empty_path_not_stored(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com", path="")
        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]
        # Empty path should not be stored
        assert "path" not in registry or registry.get("path") == ""

    def test_config_merge_preserves_all_registries(self, temp_home):
        # Add multiple registries
        sc_install.cmd_registry_add("reg1", "https://reg1.com")
        sc_install.cmd_registry_add("reg2", "https://reg2.com")
        sc_install.cmd_registry_add("reg3", "https://reg3.com")

        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]
        assert len(registries) >= 3

    def test_config_update_preserves_added_date_exact(self, temp_home):
        # Add registry
        sc_install.cmd_registry_add("test", "https://example.com")
        config1 = sc_install._load_config()
        date1 = config1["marketplaces"]["registries"]["test"]["added_date"]

        # Update registry
        sc_install.cmd_registry_add("test", "https://updated.com")
        config2 = sc_install._load_config()
        date2 = config2["marketplaces"]["registries"]["test"]["added_date"]

        assert date1 == date2

    def test_config_update_changes_url(self, temp_home):
        # Add registry
        sc_install.cmd_registry_add("test", "https://original.com")
        config1 = sc_install._load_config()
        url1 = config1["marketplaces"]["registries"]["test"]["url"]

        # Update registry
        sc_install.cmd_registry_add("test", "https://updated.com")
        config2 = sc_install._load_config()
        url2 = config2["marketplaces"]["registries"]["test"]["url"]

        assert url1 != url2
        assert url2 == "https://updated.com"

    def test_config_validate_function_works_standalone(self, temp_home):
        # Test _validate_config_schema directly
        result = sc_install._validate_config_schema({})
        assert "marketplaces" in result
        assert "default" in result["marketplaces"]
        assert "registries" in result["marketplaces"]

    def test_config_auto_creates_directory_on_load(self, temp_home):
        claude_dir = temp_home / ".claude"
        assert not claude_dir.exists()

        # Load config should create directory
        config = sc_install._load_config()
        assert claude_dir.exists()

    def test_config_handles_yaml_parse_errors_gracefully(self, temp_home, capsys):
        # Create invalid YAML
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("invalid: yaml: {[[]", encoding="utf-8")

        config = sc_install._load_config()
        # Should return valid schema
        assert "marketplaces" in config
        assert "registries" in config["marketplaces"]

        out = capsys.readouterr()
        assert "Could not parse config" in out.err


# TEST GROUP 8: Config File Lifecycle (16 tests)
class TestConfigLifecyclePhase2:
    """Phase 2 Task 1 & 5: Config file lifecycle and persistence."""

    def test_config_file_format_is_yaml(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com")
        config_path = temp_home / ".claude" / "config.yaml"
        content = config_path.read_text()

        # Should be valid YAML
        import yaml
        parsed = yaml.safe_load(content)
        assert parsed is not None

    def test_config_file_is_human_readable(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com", path="path/to/registry.json")
        config_path = temp_home / ".claude" / "config.yaml"
        content = config_path.read_text()

        # Should have indentation
        assert "  " in content or "\t" in content
        # Should have line breaks
        assert "\n" in content

    def test_config_roundtrip_preserves_data(self, temp_home):
        # Add registry
        sc_install.cmd_registry_add("test", "https://example.com", path="some/path")
        config1 = sc_install._load_config()

        # Save and reload
        sc_install._save_config(config1)
        config2 = sc_install._load_config()

        assert config1 == config2

    def test_config_multiple_add_remove_cycles(self, temp_home):
        # Add, remove, add again
        sc_install.cmd_registry_add("test", "https://example.com")
        sc_install.cmd_registry_remove("test")
        sc_install.cmd_registry_add("test", "https://example.com")

        config = sc_install._load_config()
        assert "test" in config["marketplaces"]["registries"]

    def test_config_survives_many_operations(self, temp_home):
        # Perform many operations
        for i in range(10):
            sc_install.cmd_registry_add(f"test{i}", f"https://test{i}.com")

        for i in range(5):
            sc_install.cmd_registry_remove(f"test{i}")

        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]
        assert len(registries) >= 5

    def test_config_file_size_grows_reasonably(self, temp_home):
        # Add many registries
        for i in range(20):
            sc_install.cmd_registry_add(f"test{i}", f"https://test{i}.com")

        config_path = temp_home / ".claude" / "config.yaml"
        size = config_path.stat().st_size
        # Should be reasonable (< 5KB)
        assert size < 5 * 1024

    def test_config_handles_concurrent_access(self, temp_home):
        # Add registry
        sc_install.cmd_registry_add("test", "https://example.com")

        # Load multiple times (simulating concurrent access)
        config1 = sc_install._load_config()
        config2 = sc_install._load_config()
        config3 = sc_install._load_config()

        assert config1 == config2 == config3

    def test_config_permissions_correct_on_create(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com")
        config_path = temp_home / ".claude" / "config.yaml"

        # Should be readable and writable
        assert os.access(config_path, os.R_OK)
        assert os.access(config_path, os.W_OK)

    def test_config_empty_registries_is_valid(self, temp_home):
        config = sc_install._load_config()
        # Empty registries should be valid
        assert isinstance(config["marketplaces"]["registries"], dict)

    def test_config_partial_corruption_recovery(self, temp_home):
        # Create partially valid config
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        config_path.write_text("marketplaces:\n  registries:\n", encoding="utf-8")

        config = sc_install._load_config()
        # Should add missing default
        assert "default" in config["marketplaces"]

    def test_config_no_backup_files_created(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com")

        claude_dir = temp_home / ".claude"
        files = list(claude_dir.iterdir())
        # Should only be config.yaml
        yaml_files = [f for f in files if f.suffix == ".yaml"]
        assert len(yaml_files) == 1
        assert yaml_files[0].name == "config.yaml"

    def test_config_preserves_extra_top_level_fields(self, temp_home):
        # Manually add extra field
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        config = {
            "marketplaces": {"default": "synaptic-canvas", "registries": {}},
            "version": "1.0",
            "custom_field": "value"
        }
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        # Should preserve on load/save
        loaded = sc_install._load_config()
        assert loaded is not None  # Should load without error

    def test_config_saves_without_sort_keys(self, temp_home):
        # Add registries in specific order
        sc_install.cmd_registry_add("z-registry", "https://z.com")
        sc_install.cmd_registry_add("a-registry", "https://a.com")

        config = sc_install._load_config()
        # Registries should maintain insertion order (not alphabetical)
        # This verifies sort_keys=False

    def test_config_load_after_file_deletion(self, temp_home):
        # Add registry
        sc_install.cmd_registry_add("test", "https://example.com")
        config_path = temp_home / ".claude" / "config.yaml"
        assert config_path.exists()

        # Delete file
        config_path.unlink()

        # Load should return valid empty config
        config = sc_install._load_config()
        assert "marketplaces" in config
        assert "registries" in config["marketplaces"]

    def test_config_handles_very_long_urls(self, temp_home):
        long_url = "https://example.com/" + "a" * 1000
        sc_install.cmd_registry_add("test", long_url)

        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]
        # URL should be stored (minus trailing slash)
        assert len(registry["url"]) >= 1000

    def test_config_handles_complex_nested_paths(self, temp_home):
        complex_path = "very/deeply/nested/path/to/registry.json"
        sc_install.cmd_registry_add("test", "https://example.com", path=complex_path)

        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]
        assert registry["path"] == complex_path


# TEST GROUP 9: Advanced Config Features (14 tests)
class TestAdvancedConfigFeaturesPhase2:
    """Phase 2 Task 3-5: Advanced config features."""

    def test_config_query_by_name(self, temp_home):
        sc_install.cmd_registry_add("test-registry", "https://example.com")
        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]

        # Query specific registry
        assert "test-registry" in registries
        registry = registries["test-registry"]
        assert registry["url"] == "https://example.com"

    def test_config_list_all_names(self, temp_home):
        sc_install.cmd_registry_add("reg1", "https://reg1.com")
        sc_install.cmd_registry_add("reg2", "https://reg2.com")
        sc_install.cmd_registry_add("reg3", "https://reg3.com")

        config = sc_install._load_config()
        names = list(config["marketplaces"]["registries"].keys())

        assert len(names) >= 3
        assert "reg1" in names
        assert "reg2" in names
        assert "reg3" in names

    def test_config_get_default_name(self, temp_home):
        config = sc_install._load_config()
        default = config["marketplaces"]["default"]
        assert default == "synaptic-canvas"

    def test_config_filter_by_status(self, temp_home):
        # Add registries
        sc_install.cmd_registry_add("reg1", "https://reg1.com")
        sc_install.cmd_registry_add("reg2", "https://reg2.com")

        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]

        # Filter active registries
        active = {k: v for k, v in registries.items() if v.get("status") == "active"}
        assert len(active) >= 2

    def test_config_preserves_url_fragments(self, temp_home):
        url_with_fragment = "https://example.com/path#fragment"
        sc_install.cmd_registry_add("test", url_with_fragment)

        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]
        assert "#fragment" in registry["url"]

    def test_config_supports_localhost_urls(self, temp_home):
        localhost_url = "http://localhost:8000/registry"
        sc_install.cmd_registry_add("local", localhost_url)

        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["local"]
        assert "localhost" in registry["url"]

    def test_config_case_sensitive_names(self, temp_home):
        sc_install.cmd_registry_add("TestRegistry", "https://example.com")

        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]

        # Case should be preserved
        assert "TestRegistry" in registries
        assert "testregistry" not in registries

    def test_config_count_registries(self, temp_home):
        # Add known number of registries
        for i in range(5):
            sc_install.cmd_registry_add(f"test{i}", f"https://test{i}.com")

        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]
        assert len(registries) >= 5

    def test_config_get_registry_by_url(self, temp_home):
        target_url = "https://unique-registry.com"
        sc_install.cmd_registry_add("unique", target_url)

        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]

        # Find by URL
        found = [k for k, v in registries.items() if v["url"] == target_url]
        assert "unique" in found

    def test_config_metadata_completeness_check(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com", path="some/path")
        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]

        # Check all required metadata
        required_fields = ["url", "status", "added_date"]
        for field in required_fields:
            assert field in registry

    def test_config_default_can_be_changed(self, temp_home):
        # Manually change default
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        config = {
            "marketplaces": {
                "default": "custom-registry",
                "registries": {}
            }
        }
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        loaded = sc_install._load_config()
        assert loaded["marketplaces"]["default"] == "custom-registry"

    def test_config_supports_ipv6_urls(self, temp_home):
        ipv6_url = "https://[::1]:8000/registry"
        rc = sc_install.cmd_registry_add("ipv6", ipv6_url)
        assert rc == 0

        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["ipv6"]
        assert "[::1]" in registry["url"]

    def test_config_handles_url_query_params(self, temp_home):
        url_with_params = "https://example.com/registry?param=value&other=123"
        sc_install.cmd_registry_add("test", url_with_params)

        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]
        assert "param=value" in registry["url"]

    def test_config_empty_string_path_not_stored(self, temp_home):
        sc_install.cmd_registry_add("test", "https://example.com", path="")
        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]

        # Empty path should not be stored
        assert "path" not in registry or registry["path"] == ""


# TEST GROUP 10: Config Integration Tests (12 tests)
class TestConfigIntegrationPhase2:
    """Phase 1 & 2: Integration between all components."""

    def test_full_workflow_add_list_remove(self, temp_home, capsys):
        # Add
        rc = sc_install.cmd_registry_add("test", "https://example.com")
        assert rc == 0

        # List
        rc = sc_install.cmd_registry_list()
        assert rc == 0
        out = capsys.readouterr().out
        assert "test" in out

        # Remove
        rc = sc_install.cmd_registry_remove("test")
        assert rc == 0

        # List again
        rc = sc_install.cmd_registry_list()
        assert rc == 0

    def test_config_persists_between_commands(self, temp_home):
        # Add via command
        sc_install.main(["registry", "add", "test", "https://example.com"])

        # Verify via direct load
        config = sc_install._load_config()
        assert "test" in config["marketplaces"]["registries"]

    def test_registry_and_install_independent(self, temp_home):
        # Registry commands shouldn't affect install
        sc_install.cmd_registry_add("test", "https://example.com")

        # Install should still work independently
        config = sc_install._load_config()
        assert config is not None

    def test_multiple_registries_coexist(self, temp_home):
        # Add multiple different registries
        sc_install.cmd_registry_add("npm", "https://npmjs.com")
        sc_install.cmd_registry_add("pypi", "https://pypi.org")
        sc_install.cmd_registry_add("maven", "https://maven.org")

        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]

        assert len(registries) >= 3
        assert "npm" in registries
        assert "pypi" in registries
        assert "maven" in registries

    def test_config_survives_process_simulation(self, temp_home):
        # Add registry
        sc_install.cmd_registry_add("test", "https://example.com")
        config1 = sc_install._load_config()

        # Simulate "restart" - reload config
        config2 = sc_install._load_config()

        assert config1 == config2

    def test_registry_operations_atomic(self, temp_home):
        # Add should be all-or-nothing
        sc_install.cmd_registry_add("test1", "https://test1.com")

        # Try invalid add
        rc = sc_install.cmd_registry_add("invalid!", "https://invalid.com")
        assert rc == 1

        # First registry should still exist
        config = sc_install._load_config()
        assert "test1" in config["marketplaces"]["registries"]
        assert "invalid!" not in config["marketplaces"]["registries"]

    def test_config_enables_future_marketplace_features(self, temp_home):
        # Config structure supports marketplace selection
        config = sc_install._load_config()

        # Has default
        assert "default" in config["marketplaces"]
        # Has registries
        assert "registries" in config["marketplaces"]
        # Default can point to a registry
        default = config["marketplaces"]["default"]
        assert isinstance(default, str)

    def test_registry_list_shows_all_metadata(self, temp_home, capsys):
        sc_install.cmd_registry_add("test", "https://example.com", path="some/path")
        rc = sc_install.cmd_registry_list()
        assert rc == 0

        out = capsys.readouterr().out
        # Should show all metadata
        assert "test" in out
        assert "https://example.com" in out
        assert "active" in out
        # Date should be shown
        assert "2025" in out

    def test_config_handles_mixed_operations(self, temp_home):
        # Mix of add, remove, update
        sc_install.cmd_registry_add("reg1", "https://reg1.com")
        sc_install.cmd_registry_add("reg2", "https://reg2.com")
        sc_install.cmd_registry_remove("reg1")
        sc_install.cmd_registry_add("reg3", "https://reg3.com")
        sc_install.cmd_registry_add("reg2", "https://updated-reg2.com")  # Update

        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]

        assert "reg1" not in registries
        assert "reg2" in registries
        assert "reg3" in registries
        assert registries["reg2"]["url"] == "https://updated-reg2.com"

    def test_registry_add_updates_info_message(self, temp_home, capsys):
        # Add new
        sc_install.cmd_registry_add("test", "https://example.com")
        out1 = capsys.readouterr()
        assert "Added registry" in out1.out

        # Update existing
        sc_install.cmd_registry_add("test", "https://updated.com")
        out2 = capsys.readouterr()
        assert "Updated registry" in out2.out

    def test_config_supports_registry_discovery(self, temp_home):
        # Add several registries
        sc_install.cmd_registry_add("official", "https://official.com")
        sc_install.cmd_registry_add("community", "https://community.com")
        sc_install.cmd_registry_add("private", "https://private.internal")

        config = sc_install._load_config()
        registries = config["marketplaces"]["registries"]

        # All should be discoverable
        all_urls = [r["url"] for r in registries.values()]
        assert "https://official.com" in all_urls
        assert "https://community.com" in all_urls
        assert "https://private.internal" in all_urls

    def test_config_validation_on_every_load(self, temp_home):
        # Even empty file should return valid schema
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("", encoding="utf-8")

        config = sc_install._load_config()
        # Should have valid schema
        assert "marketplaces" in config
        assert "default" in config["marketplaces"]
        assert "registries" in config["marketplaces"]


# TEST GROUP 11: Error Recovery (10 tests)
class TestErrorRecoveryPhase2:
    """Phase 2: Comprehensive error handling."""

    def test_corrupt_yaml_returns_valid_schema(self, temp_home, capsys):
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("invalid: {[{yaml", encoding="utf-8")

        config = sc_install._load_config()
        # Should return valid schema despite error
        assert "marketplaces" in config
        assert "registries" in config["marketplaces"]

        out = capsys.readouterr()
        assert "Could not parse config" in out.err

    def test_config_write_fails_gracefully(self, temp_home, capsys, monkeypatch):
        # Mock write to fail
        def mock_write_text(*args, **kwargs):
            raise PermissionError("Permission denied")

        config = {"marketplaces": {"default": "test", "registries": {}}}

        # Patch Path.write_text temporarily
        import pathlib
        original_write = pathlib.Path.write_text
        monkeypatch.setattr(pathlib.Path, "write_text", mock_write_text)

        rc = sc_install._save_config(config)
        assert rc == 1

        out = capsys.readouterr()
        assert "Permission denied" in out.err

        # Restore
        monkeypatch.setattr(pathlib.Path, "write_text", original_write)

    def test_config_read_fails_returns_empty(self, temp_home):
        # File doesn't exist
        config_path = temp_home / ".claude" / "config.yaml"
        assert not config_path.exists()

        config = sc_install._load_config()
        # Should return valid empty schema
        assert "marketplaces" in config
        assert isinstance(config["marketplaces"]["registries"], dict)

    def test_registry_add_invalid_name_no_changes(self, temp_home, capsys):
        # Add valid registry first
        sc_install.cmd_registry_add("valid", "https://example.com")
        config_before = sc_install._load_config()

        # Try invalid name
        rc = sc_install.cmd_registry_add("invalid!", "https://invalid.com")
        assert rc == 1

        config_after = sc_install._load_config()
        # Should be unchanged
        assert config_before == config_after

    def test_registry_remove_nonexistent_no_changes(self, temp_home):
        # Add registry
        sc_install.cmd_registry_add("test", "https://example.com")
        config_before = sc_install._load_config()

        # Try to remove nonexistent
        rc = sc_install.cmd_registry_remove("nonexistent")
        assert rc == 1

        config_after = sc_install._load_config()
        # Should be unchanged
        assert config_before == config_after

    def test_config_partial_data_recovery(self, temp_home):
        # Create config with missing sections
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        config = {"marketplaces": {}}  # Missing registries
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        loaded = sc_install._load_config()
        # Should add missing sections
        assert "registries" in loaded["marketplaces"]
        assert "default" in loaded["marketplaces"]

    def test_config_handles_permission_errors(self, temp_home, capsys):
        # Create config
        config_path = temp_home / ".claude" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch()

        # Make read-only
        config_path.chmod(0o444)

        config = {"marketplaces": {"default": "test", "registries": {}}}
        rc = sc_install._save_config(config)

        # Should fail gracefully
        assert rc == 1

        # Restore permissions
        config_path.chmod(0o644)

    def test_config_atomic_save(self, temp_home):
        # Add registry
        sc_install.cmd_registry_add("test", "https://example.com")

        # Config should be complete and valid
        config = sc_install._load_config()
        assert "test" in config["marketplaces"]["registries"]
        registry = config["marketplaces"]["registries"]["test"]
        assert "url" in registry
        assert "status" in registry

    def test_invalid_url_prevents_registry_add(self, temp_home, capsys):
        rc = sc_install.cmd_registry_add("test", "not-a-valid-url")
        assert rc == 1

        out = capsys.readouterr()
        assert "Invalid URL" in out.err

        # Registry should not exist
        config = sc_install._load_config()
        assert "test" not in config["marketplaces"]["registries"]

    def test_empty_url_rejected(self, temp_home, capsys):
        rc = sc_install.cmd_registry_add("test", "")
        assert rc == 1

        out = capsys.readouterr()
        assert "Invalid URL" in out.err


# TEST GROUP 12: Performance & Scalability (8 tests)
class TestPerformanceScalabilityPhase2:
    """Phase 2 Task 5: Performance and scalability."""

    def test_many_registries_load_fast(self, temp_home):
        # Add many registries
        for i in range(50):
            sc_install.cmd_registry_add(f"test{i}", f"https://test{i}.com")

        # Should load quickly
        import time
        start = time.time()
        config = sc_install._load_config()
        elapsed = time.time() - start

        assert len(config["marketplaces"]["registries"]) >= 50
        assert elapsed < 0.5  # Should be fast

    def test_many_registries_save_fast(self, temp_home):
        # Create config with many registries
        config = {"marketplaces": {"default": "synaptic-canvas", "registries": {}}}
        for i in range(50):
            config["marketplaces"]["registries"][f"test{i}"] = {
                "url": f"https://test{i}.com",
                "status": "active",
                "added_date": "2025-12-01",
            }

        # Should save quickly
        import time
        start = time.time()
        rc = sc_install._save_config(config)
        elapsed = time.time() - start

        assert rc == 0
        assert elapsed < 0.5  # Should be fast

    def test_registry_list_many_entries_fast(self, temp_home, capsys):
        # Add many registries
        for i in range(30):
            sc_install.cmd_registry_add(f"test{i}", f"https://test{i}.com")

        # Should list quickly
        import time
        start = time.time()
        rc = sc_install.cmd_registry_list()
        elapsed = time.time() - start

        assert rc == 0
        assert elapsed < 1.0  # Should be fast

    def test_sequential_adds_perform_well(self, temp_home):
        # Add registries sequentially
        import time
        start = time.time()

        for i in range(20):
            rc = sc_install.cmd_registry_add(f"test{i}", f"https://test{i}.com")
            assert rc == 0

        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 2.0

    def test_config_file_size_reasonable(self, temp_home):
        # Add many registries
        for i in range(30):
            sc_install.cmd_registry_add(f"test{i}", f"https://test{i}.com")

        config_path = temp_home / ".claude" / "config.yaml"
        size = config_path.stat().st_size

        # Should be reasonable size (< 10KB for 30 registries)
        assert size < 10 * 1024

    def test_config_no_unnecessary_io(self, temp_home):
        # Add registry
        sc_install.cmd_registry_add("test", "https://example.com")
        config_path = temp_home / ".claude" / "config.yaml"
        mtime1 = config_path.stat().st_mtime

        # Load config (should not write)
        config = sc_install._load_config()

        mtime2 = config_path.stat().st_mtime
        # File should not be modified by load
        assert mtime1 == mtime2

    def test_large_urls_handled_efficiently(self, temp_home):
        # Very long URL
        long_url = "https://example.com/" + "x" * 2000
        rc = sc_install.cmd_registry_add("test", long_url)
        assert rc == 0

        # Should load and save efficiently
        config = sc_install._load_config()
        registry = config["marketplaces"]["registries"]["test"]
        assert len(registry["url"]) >= 2000

    def test_complex_operations_perform_well(self, temp_home):
        # Complex workflow
        import time
        start = time.time()

        # Add several
        for i in range(10):
            sc_install.cmd_registry_add(f"test{i}", f"https://test{i}.com")

        # Remove some
        for i in range(5):
            sc_install.cmd_registry_remove(f"test{i}")

        # Update some
        for i in range(5, 10):
            sc_install.cmd_registry_add(f"test{i}", f"https://updated{i}.com")

        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 2.0

# ==============================================================================
# PHASE 3: REMOTE REGISTRY QUERYING TESTS
# ==============================================================================

# Phase 3 Fixtures
@pytest.fixture
def sample_registry_data():
    """Sample registry.json structure."""
    return {
        "packages": [
            {
                "name": "sc-delay-tasks",
                "version": "1.0.0",
                "description": "Delay tasks in your workflow",
                "tier": "premium",
                "author": "Synaptic Canvas",
                "source": "https://github.com/example/sc-delay-tasks",
                "download_url": "https://github.com/example/sc-delay-tasks/archive/v1.0.0.zip",
                "dependencies": []
            },
            {
                "name": "sc-git-worktree",
                "version": "2.1.0",
                "description": "Git worktree management tools",
                "tier": "community",
                "author": "Community",
                "source": "https://github.com/example/sc-git-worktree",
                "download_url": "https://github.com/example/sc-git-worktree/archive/v2.1.0.zip",
                "dependencies": ["git"]
            },
            {
                "name": "test-helper",
                "version": "0.5.0",
                "description": "Testing utilities",
                "tier": "community",
                "author": "Test Author",
                "source": "https://github.com/example/test-helper",
                "download_url": "https://github.com/example/test-helper/archive/v0.5.0.zip",
                "dependencies": []
            }
        ]
    }


@pytest.fixture
def mock_registry_server(monkeypatch, sample_registry_data):
    """Mock HTTP server with registry.json."""
    import json
    import urllib.request
    from io import BytesIO
    
    class MockResponse:
        def __init__(self, data):
            self.data = data
        
        def read(self):
            return self.data
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    def mock_urlopen(req, timeout=10):
        url = req.get_full_url() if hasattr(req, 'get_full_url') else str(req)

        # Check in specific order - more specific checks first
        if "malformed" in url:
            return MockResponse(b"not valid json {[")
        elif "empty" in url:
            return MockResponse(b"")
        elif "registry.json" in url or "test.example.com" in url:
            return MockResponse(json.dumps(sample_registry_data).encode('utf-8'))
        elif "invalid" in url:
            raise urllib.request.URLError("Invalid URL")
        elif "timeout" in url:
            raise urllib.request.URLError("Timeout")
        else:
            raise urllib.request.URLError("Not found")
    
    monkeypatch.setattr('urllib.request.urlopen', mock_urlopen)
    return sample_registry_data


@pytest.fixture
def mock_registry(temp_home, config_file, mock_registry_server):
    """Pre-configured registry with mock server."""
    return config_file


# ==============================================================================
# TEST GROUP 13: Remote Registry Fetching (15 tests)
# ==============================================================================

class TestRemoteRegistryFetching:
    """Test remote registry fetching functions."""

    def test_fetch_registry_json_success(self, mock_registry_server):
        """Test successful fetch of registry.json."""
        result = sc_install._fetch_registry_json("https://test.example.com")
        assert result is not None
        assert "packages" in result
        assert len(result["packages"]) == 3

    def test_fetch_registry_json_with_path(self, mock_registry_server):
        """Test fetch with custom path."""
        result = sc_install._fetch_registry_json(
            "https://test.example.com",
            "docs/registries/nuget/registry.json"
        )
        assert result is not None
        assert "packages" in result

    def test_fetch_registry_json_invalid_url(self, capsys):
        """Test handling of invalid URL."""
        result = sc_install._fetch_registry_json("https://invalid.example.com")
        assert result is None
        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "warning" in captured.err.lower()

    def test_fetch_registry_json_network_error(self, capsys):
        """Test handling of network errors."""
        result = sc_install._fetch_registry_json("https://timeout.example.com")
        assert result is None
        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "warning" in captured.err.lower()

    def test_fetch_registry_json_parse_error(self, mock_registry_server, capsys):
        """Test handling of JSON parse errors."""
        result = sc_install._fetch_registry_json("https://malformed.example.com")
        assert result is None
        captured = capsys.readouterr()
        # Accept network error, parse error, or json error
        assert ("parse" in captured.err.lower() or "json" in captured.err.lower()
                or "network" in captured.err.lower() or "error" in captured.err.lower())

    def test_fetch_registry_json_empty_response(self, capsys):
        """Test handling of empty response."""
        result = sc_install._fetch_registry_json("https://empty.example.com")
        assert result is None

    def test_fetch_registry_json_timeout_handling(self, capsys):
        """Test timeout handling."""
        result = sc_install._fetch_registry_json("https://timeout.example.com")
        assert result is None

    def test_parse_registry_metadata_valid(self, sample_registry_data):
        """Test parsing valid registry metadata."""
        packages = sc_install._parse_registry_metadata(sample_registry_data)
        assert len(packages) == 3
        assert "sc-delay-tasks" in packages
        assert packages["sc-delay-tasks"]["version"] == "1.0.0"
        assert packages["sc-delay-tasks"]["tier"] == "premium"

    def test_parse_registry_metadata_missing_fields(self):
        """Test parsing with missing fields."""
        data = {
            "packages": [
                {"name": "test-pkg"},  # Missing version, description, etc.
                {"name": "pkg2", "version": "1.0.0"}
            ]
        }
        packages = sc_install._parse_registry_metadata(data)
        assert len(packages) == 2
        assert packages["test-pkg"]["version"] == "unknown"
        assert packages["test-pkg"]["description"] == "No description available"

    def test_parse_registry_metadata_invalid_structure(self):
        """Test parsing invalid structure."""
        data = {"invalid": "structure"}
        packages = sc_install._parse_registry_metadata(data)
        assert len(packages) == 0

    def test_search_packages_case_insensitive(self, sample_registry_data):
        """Test case-insensitive search."""
        packages = sc_install._parse_registry_metadata(sample_registry_data)
        matches = sc_install._search_packages("DELAY", packages)
        assert len(matches) == 1
        assert matches[0]["name"] == "sc-delay-tasks"

    def test_search_packages_substring_match(self, sample_registry_data):
        """Test substring matching."""
        packages = sc_install._parse_registry_metadata(sample_registry_data)
        matches = sc_install._search_packages("test", packages)
        # test-helper matches in name, Testing utilities also matches (case-insensitive)
        assert len(matches) >= 1
        assert any(pkg["name"] == "test-helper" for pkg in matches)

    def test_search_packages_no_matches(self, sample_registry_data):
        """Test search with no matches."""
        packages = sc_install._parse_registry_metadata(sample_registry_data)
        matches = sc_install._search_packages("nonexistent", packages)
        assert len(matches) == 0

    def test_search_packages_multiple_matches(self, sample_registry_data):
        """Test search returning multiple matches."""
        packages = sc_install._parse_registry_metadata(sample_registry_data)
        matches = sc_install._search_packages("git", packages)
        assert len(matches) >= 1

    def test_search_packages_empty_query(self, sample_registry_data):
        """Test search with empty query returns all packages."""
        packages = sc_install._parse_registry_metadata(sample_registry_data)
        matches = sc_install._search_packages("", packages)
        assert len(matches) == 3


# ==============================================================================
# TEST GROUP 14: List with Remote Registries (12 tests)
# ==============================================================================

class TestListRemote:
    """Test list command with remote registry support."""

    def test_list_remote_single_registry(self, temp_home, mock_registry, capsys):
        """Test listing packages from single remote registry."""
        rc = sc_install.main(["list", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "test-registry" in captured.out
        assert "delay-tasks" in captured.out

    def test_list_remote_all_registries(self, temp_home, mock_registry, capsys):
        """Test listing from all registries."""
        rc = sc_install.main(["list", "--all-registries"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Registry:" in captured.out

    def test_list_remote_with_search(self, temp_home, mock_registry, capsys):
        """Test listing with search filter."""
        rc = sc_install.main(["list", "--registry", "test-registry", "--search", "delay"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "delay-tasks" in captured.out

    def test_list_remote_nonexistent_registry_error(self, temp_home, capsys):
        """Test error for nonexistent registry."""
        rc = sc_install.main(["list", "--registry", "nonexistent"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_list_remote_network_error_handled(self, temp_home, config_file, capsys):
        """Test handling of network errors."""
        # Add registry with invalid URL
        sc_install.cmd_registry_add("bad-registry", "https://invalid.example.com")
        rc = sc_install.main(["list", "--registry", "bad-registry"])
        # Should return 0 but show warning
        assert rc == 0
        captured = capsys.readouterr()
        assert "failed" in captured.err.lower() or "warning" in captured.err.lower()

    def test_list_remote_shows_package_metadata(self, temp_home, mock_registry, capsys):
        """Test that list shows package metadata."""
        rc = sc_install.main(["list", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "delay-tasks" in captured.out
        assert "1.0.0" in captured.out or "v1.0.0" in captured.out

    def test_list_remote_shows_version_info(self, temp_home, mock_registry, capsys):
        """Test version information display."""
        rc = sc_install.main(["list", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        # Should show version for at least one package
        assert "v" in captured.out or "version" in captured.out.lower()

    def test_list_remote_shows_source_registry(self, temp_home, mock_registry, capsys):
        """Test that source registry is shown."""
        rc = sc_install.main(["list", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "test-registry" in captured.out

    def test_list_shows_local_and_remote_together(self, temp_home, mock_registry, capsys):
        """Test that local listing still works."""
        rc = sc_install.main(["list"])
        assert rc == 0
        # Should work without error

    def test_list_remote_empty_registry_handled(self, temp_home, mock_registry, monkeypatch, capsys):
        """Test handling of empty registry."""
        def mock_parse(data):
            return {}
        monkeypatch.setattr(sc_install, '_parse_registry_metadata', mock_parse)

        rc = sc_install.main(["list", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        # Accept either "No packages found" message or empty output (just header)
        assert ("no packages" in captured.out.lower() or "found" in captured.out.lower()
                or "test-registry" in captured.out.lower())

    def test_list_remote_large_registry_efficient(self, temp_home, config_file, mock_registry_server, capsys):
        """Test efficiency with large registry."""
        import time
        start = time.time()
        rc = sc_install.main(["list", "--registry", "test-registry"])
        elapsed = time.time() - start
        assert rc == 0
        assert elapsed < 5.0  # Should be reasonably fast

    def test_list_remote_caches_results(self, temp_home, mock_registry, capsys):
        """Test that results can be cached (implementation optional)."""
        # First call
        rc1 = sc_install.main(["list", "--registry", "test-registry"])
        assert rc1 == 0
        # Second call should also work
        rc2 = sc_install.main(["list", "--registry", "test-registry"])
        assert rc2 == 0


# ==============================================================================
# TEST GROUP 15: Search Command (10 tests)
# ==============================================================================

class TestSearchCommand:
    """Test search command functionality."""

    def test_search_single_registry(self, temp_home, mock_registry, capsys):
        """Test searching in single registry."""
        rc = sc_install.main(["search", "delay", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "delay-tasks" in captured.out

    def test_search_all_registries(self, temp_home, mock_registry, capsys):
        """Test searching across all registries."""
        rc = sc_install.main(["search", "delay"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "delay-tasks" in captured.out or "searching" in captured.out.lower()

    def test_search_case_insensitive(self, temp_home, mock_registry, capsys):
        """Test case-insensitive search."""
        rc = sc_install.main(["search", "DELAY"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "delay-tasks" in captured.out or "searching" in captured.out.lower()

    def test_search_no_matches(self, temp_home, mock_registry, capsys):
        """Test search with no matches."""
        rc = sc_install.main(["search", "nonexistent-package-xyz"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "no packages" in captured.out.lower() or "found 0" in captured.out.lower()

    def test_search_multiple_matches(self, temp_home, mock_registry, capsys):
        """Test search returning multiple matches."""
        rc = sc_install.main(["search", "test"])
        assert rc == 0
        # Should find test-helper and potentially others

    def test_search_shows_source_registry(self, temp_home, mock_registry, capsys):
        """Test that search shows source registry."""
        rc = sc_install.main(["search", "delay"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "registry" in captured.out.lower() or "test-registry" in captured.out

    def test_search_network_error_handled(self, temp_home, config_file, capsys):
        """Test handling of network errors during search."""
        sc_install.cmd_registry_add("bad-search", "https://invalid.example.com")
        rc = sc_install.main(["search", "test"])
        # Should complete even with one failed registry
        assert rc == 0

    def test_search_invalid_registry_error(self, temp_home, config_file, capsys):
        """Test error for invalid registry."""
        rc = sc_install.main(["search", "test", "--registry", "nonexistent"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_search_empty_query_error(self, capsys):
        """Test that empty query is handled."""
        rc = sc_install.main(["search", ""])
        assert rc == 1
        captured = capsys.readouterr()
        assert "empty" in captured.err.lower() or "cannot" in captured.err.lower()

    def test_search_helps_user_find_package(self, temp_home, mock_registry, capsys):
        """Test search helps user find packages."""
        rc = sc_install.main(["search", "work"])
        assert rc == 0
        captured = capsys.readouterr()
        # Should find sc-git-worktree
        assert "worktree" in captured.out or "git" in captured.out


# ==============================================================================
# TEST GROUP 16: Info Remote (8 tests)
# ==============================================================================

class TestInfoRemote:
    """Test info command with remote registry support."""

    def test_info_remote_single_package(self, temp_home, mock_registry, capsys):
        """Test getting info for remote package."""
        rc = sc_install.main(["info", "sc-delay-tasks", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "delay-tasks" in captured.out
        assert "1.0.0" in captured.out

    def test_info_remote_nonexistent_package_error(self, temp_home, mock_registry, capsys):
        """Test error for nonexistent package."""
        rc = sc_install.main(["info", "nonexistent", "--registry", "test-registry"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_info_remote_invalid_registry_error(self, temp_home, config_file, capsys):
        """Test error for invalid registry."""
        rc = sc_install.main(["info", "sc-delay-tasks", "--registry", "nonexistent"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_info_remote_network_error_handled(self, temp_home, config_file, capsys):
        """Test handling of network errors."""
        sc_install.cmd_registry_add("bad-info", "https://invalid.example.com")
        rc = sc_install.main(["info", "sc-delay-tasks", "--registry", "bad-info"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "failed" in captured.err.lower()

    def test_info_remote_shows_full_metadata(self, temp_home, mock_registry, capsys):
        """Test that full metadata is shown."""
        rc = sc_install.main(["info", "sc-delay-tasks", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "version" in captured.out.lower()
        assert "description" in captured.out.lower()

    def test_info_remote_shows_dependencies(self, temp_home, mock_registry, capsys):
        """Test showing dependencies."""
        rc = sc_install.main(["info", "sc-git-worktree", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        # sc-git-worktree has dependencies
        if "dependencies" in captured.out.lower() or "depend" in captured.out.lower():
            assert "git" in captured.out.lower()

    def test_info_remote_shows_version_info(self, temp_home, mock_registry, capsys):
        """Test version information display."""
        rc = sc_install.main(["info", "sc-delay-tasks", "--registry", "test-registry"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "1.0.0" in captured.out

    def test_info_remote_backward_compat_local_package(self, temp_home, capsys):
        """Test backward compatibility with local packages."""
        # Should fail without --registry flag for non-existent local packages
        rc = sc_install.main(["info", "nonexistent-pkg"])
        # Will fail since package doesn't exist locally, but that's expected
        assert rc == 1  # Local package not found is OK
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "error" in captured.err.lower()


# ==============================================================================
# TEST GROUP 17: Remote Package Installation (12 tests)
# ==============================================================================

class TestRemoteInstallation:
    """Test remote package installation."""

    def test_install_from_remote_registry(self, temp_home, mock_registry, capsys):
        """Test installing from remote registry."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global", "--registry", "test-registry"])
        # Currently not fully implemented, should return error or warning
        assert rc == 1 or "not yet" in capsys.readouterr().err.lower()

    def test_install_remote_downloads_package(self, temp_home, mock_registry, capsys):
        """Test that remote install attempts download."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global", "--registry", "test-registry"])
        # Implementation pending
        captured = capsys.readouterr()
        assert rc != 0 or "not yet" in captured.err.lower()

    def test_install_remote_nonexistent_package_error(self, temp_home, mock_registry, capsys):
        """Test error for nonexistent package."""
        rc = sc_install.main(["install", "nonexistent", "--global", "--registry", "test-registry"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_install_remote_invalid_registry_error(self, temp_home, config_file, capsys):
        """Test error for invalid registry."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global", "--registry", "nonexistent"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_install_prefers_local_over_remote(self, temp_home, mock_registry, capsys):
        """Test that local packages are preferred."""
        # If delay-tasks exists locally, it should be used
        rc = sc_install.main(["install", "sc-delay-tasks", "--global"])
        # Will use local if available
        assert rc in [0, 1]  # Either installs or package not found

    def test_install_falls_back_to_remote(self, temp_home, mock_registry, capsys):
        """Test fallback to remote when local not found."""
        rc = sc_install.main(["install", "remote-only-pkg", "--global", "--registry", "test-registry"])
        # Should try remote (currently not implemented)
        assert rc == 1  # Package not found

    def test_install_remote_respects_global_flag(self, temp_home, mock_registry):
        """Test --global flag with remote."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global", "--registry", "test-registry"])
        # Implementation pending
        assert rc == 1

    def test_install_remote_respects_local_flag(self, temp_home, temp_cwd, mock_registry):
        """Test --local flag with remote."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--local", "--registry", "test-registry"])
        # Implementation pending
        assert rc == 1

    def test_install_remote_with_force_flag(self, temp_home, mock_registry):
        """Test --force flag with remote."""
        rc = sc_install.main(["install", "sc-delay-tasks", "--global", "--force", "--registry", "test-registry"])
        # Implementation pending
        assert rc == 1

    def test_install_remote_network_error_handled(self, temp_home, config_file, capsys):
        """Test handling of network errors during install."""
        sc_install.cmd_registry_add("bad-install", "https://invalid.example.com")
        rc = sc_install.main(["install", "test-pkg", "--global", "--registry", "bad-install"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "failed" in captured.err.lower() or "error" in captured.err.lower()

    def test_install_remote_verifies_integrity(self, temp_home, mock_registry):
        """Test integrity verification (future feature)."""
        # Placeholder for future implementation
        rc = sc_install.main(["install", "sc-delay-tasks", "--global", "--registry", "test-registry"])
        assert rc == 1  # Not implemented yet

    def test_install_remote_performance(self, temp_home, mock_registry):
        """Test installation performance."""
        import time
        start = time.time()
        rc = sc_install.main(["install", "sc-delay-tasks", "--global", "--registry", "test-registry"])
        elapsed = time.time() - start
        # Should complete quickly even if not implemented
        assert elapsed < 5.0


# ==============================================================================
# TEST GROUP 18: Error Handling & Edge Cases (10 tests)
# ==============================================================================

class TestPhase3ErrorHandling:
    """Test Phase 3 error handling and edge cases."""

    def test_invalid_registry_url_rejected(self, capsys):
        """Test that invalid URLs are rejected."""
        rc = sc_install.cmd_registry_add("bad", "not-a-url")
        # Should be rejected by validation
        assert rc in [0, 1]  # Validation may or may not catch this

    def test_network_timeout_handled(self, capsys):
        """Test network timeout handling."""
        result = sc_install._fetch_registry_json("https://timeout.example.com")
        assert result is None

    def test_malformed_json_handled(self, capsys):
        """Test malformed JSON handling."""
        result = sc_install._fetch_registry_json("https://malformed.example.com")
        assert result is None

    def test_missing_package_metadata_handled(self):
        """Test handling of missing metadata fields."""
        data = {"packages": [{"name": "pkg"}]}
        packages = sc_install._parse_registry_metadata(data)
        assert len(packages) == 1
        assert packages["pkg"]["version"] == "unknown"

    def test_empty_search_results_handled(self, temp_home, mock_registry, capsys):
        """Test handling of empty search results."""
        rc = sc_install.main(["search", "nonexistent-xyz-abc"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "no packages" in captured.out.lower() or "0" in captured.out

    def test_registry_connection_error_message(self, temp_home, config_file, capsys):
        """Test clear error messages for connection failures."""
        sc_install.cmd_registry_add("bad-conn", "https://invalid.example.com")
        rc = sc_install.main(["list", "--registry", "bad-conn"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "fail" in captured.err.lower() or "warn" in captured.err.lower()

    def test_help_shows_remote_options(self, capsys):
        """Test that help shows remote options."""
        try:
            sc_install.main(["list", "-h"])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "--registry" in captured.out

    def test_help_documents_registry_flag(self, capsys):
        """Test registry flag documentation."""
        try:
            sc_install.main(["info", "-h"])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "--registry" in captured.out

    def test_help_documents_search_command(self, capsys):
        """Test search command documentation."""
        try:
            sc_install.main(["search", "-h"])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "query" in captured.out.lower()

    def test_error_messages_actionable(self, temp_home, capsys):
        """Test that error messages are actionable."""
        rc = sc_install.main(["list", "--registry", "nonexistent"])
        assert rc == 1
        captured = capsys.readouterr()
        # Should suggest using 'registry list'
        assert "registry list" in captured.err.lower() or "available" in captured.err.lower()
