"""Tests for scripts/set-package-version.py.

Sets package versions across manifest.yaml / plugin.json / commands / skills /
agents for one or all packages, and regenerates marketplace/registry JSON
files. Blocks version decrements unless --force is passed.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "set-package-version.py"


def _load():
    spec = importlib.util.spec_from_file_location("set_package_version", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- version parsing/comparison --------------------------------------------


def test_parse_version_valid():
    mod = _load()
    assert mod.parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_invalid_raises():
    mod = _load()
    with pytest.raises(ValueError):
        mod.parse_version("1.2")


def test_compare_versions_orders_correctly():
    mod = _load()
    assert mod.compare_versions("1.0.0", "1.0.1") == -1
    assert mod.compare_versions("2.0.0", "1.0.0") == 1
    assert mod.compare_versions("1.2.3", "1.2.3") == 0


# --- file update helpers ----------------------------------------------------


def test_update_yaml_version_replaces_quoted_and_unquoted(tmp_path):
    mod = _load()
    quoted = tmp_path / "manifest.yaml"
    quoted.write_text('name: demo\nversion: "0.1.0"\n')
    assert mod.update_yaml_version(quoted, "0.2.0") is True
    assert 'version: "0.2.0"' in quoted.read_text()

    unquoted = tmp_path / "SKILL.md"
    unquoted.write_text("---\nversion: 0.1.0\n---\n")
    assert mod.update_yaml_version(unquoted, "0.2.0") is True
    assert "version: 0.2.0" in unquoted.read_text()


def test_update_yaml_version_missing_file_returns_false(tmp_path):
    mod = _load()
    assert mod.update_yaml_version(tmp_path / "missing.yaml", "1.0.0") is False


def test_update_yaml_version_dry_run_does_not_write(tmp_path):
    mod = _load()
    f = tmp_path / "manifest.yaml"
    f.write_text('version: "0.1.0"\n')
    changed = mod.update_yaml_version(f, "0.2.0", dry_run=True)
    assert changed is True
    assert '0.1.0' in f.read_text()  # unchanged on disk


def test_update_json_version_updates_and_skips_when_same(tmp_path):
    mod = _load()
    f = tmp_path / "plugin.json"
    f.write_text(json.dumps({"name": "demo", "version": "0.1.0"}))

    assert mod.update_json_version(f, "0.2.0") is True
    assert json.loads(f.read_text())["version"] == "0.2.0"

    # Now already at target version: no-op
    assert mod.update_json_version(f, "0.2.0") is False


def test_get_current_version_reads_and_missing_file(tmp_path):
    mod = _load()
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text('version: "1.5.0"\n')
    assert mod.get_current_version(manifest) == "1.5.0"
    assert mod.get_current_version(tmp_path / "nope.yaml") is None


# --- update_package ----------------------------------------------------------


def _make_package(repo_root: Path, name: str, version: str = "0.1.0"):
    pkg_dir = repo_root / "packages" / name
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "manifest.yaml").write_text(f'name: {name}\nversion: "{version}"\n')
    plugin_dir = pkg_dir / ".claude-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({"name": name, "version": version}))
    return pkg_dir


def test_update_package_happy_path_updates_manifest_and_plugin(tmp_path):
    mod = _load()
    _make_package(tmp_path, "demo-pkg")

    result = mod.update_package(tmp_path, "demo-pkg", "0.2.0")

    assert not result.errors
    assert result.old_version == "0.1.0"
    assert any("manifest.yaml" in f for f in result.files_updated)
    assert any("plugin.json" in f for f in result.files_updated)


def test_update_package_blocks_decrement_without_force(tmp_path):
    mod = _load()
    _make_package(tmp_path, "demo-pkg", version="1.0.0")

    result = mod.update_package(tmp_path, "demo-pkg", "0.5.0")

    assert result.errors
    assert "decrement" in result.errors[0].lower()


def test_update_package_allows_decrement_with_force(tmp_path):
    mod = _load()
    _make_package(tmp_path, "demo-pkg", version="1.0.0")

    result = mod.update_package(tmp_path, "demo-pkg", "0.5.0", force=True)

    assert not result.errors
    assert result.old_version == "1.0.0"


def test_update_package_skips_when_already_at_target(tmp_path):
    mod = _load()
    _make_package(tmp_path, "demo-pkg", version="0.5.0")

    result = mod.update_package(tmp_path, "demo-pkg", "0.5.0")

    assert result.skipped is True
    assert not result.files_updated


def test_update_package_missing_package_dir_errors(tmp_path):
    mod = _load()
    (tmp_path / "packages").mkdir()

    result = mod.update_package(tmp_path, "ghost-pkg", "1.0.0")

    assert result.errors
    assert "not found" in result.errors[0].lower()


# --- main() ------------------------------------------------------------------


def test_main_invalid_version_format_exits_1(tmp_path, monkeypatch, capsys):
    mod = _load()
    fake_script = tmp_path / "scripts" / "set-package-version.py"
    monkeypatch.setattr(mod, "__file__", str(fake_script))
    monkeypatch.setattr(sys, "argv", ["set-package-version.py", "demo-pkg", "not-a-version"])

    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1


def test_main_happy_path_updates_single_package(tmp_path, monkeypatch, capsys):
    mod = _load()
    fake_script = tmp_path / "scripts" / "set-package-version.py"
    monkeypatch.setattr(mod, "__file__", str(fake_script))
    _make_package(tmp_path, "demo-pkg")
    # marketplace.json is optional and regenerate_marketplace_json() no-ops
    # when absent, but regenerate_registry_json() always writes
    # .claude-plugin/registry.json, so that directory must pre-exist.
    (tmp_path / ".claude-plugin").mkdir()
    monkeypatch.setattr(sys, "argv", ["set-package-version.py", "demo-pkg", "0.2.0"])

    mod.main()  # should not raise / sys.exit

    manifest = tmp_path / "packages" / "demo-pkg" / "manifest.yaml"
    assert '0.2.0' in manifest.read_text()
    out = capsys.readouterr().out
    assert "demo-pkg: 0.1.0 -> 0.2.0" in out
