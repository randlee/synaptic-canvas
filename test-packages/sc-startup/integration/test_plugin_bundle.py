import json
import subprocess
from pathlib import Path
import sys

import pytest

# Add deprecated path to sys.path for test_fixtures module
_TEST_PACKAGES_ROOT = Path(__file__).resolve().parents[2]
if str(_TEST_PACKAGES_ROOT / "deprecated") not in sys.path:
    sys.path.insert(0, str(_TEST_PACKAGES_ROOT / "deprecated"))

from test_fixtures.helpers import require_yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_plugin_json(plugin_root: Path) -> dict:
    plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
    return json.loads(plugin_json.read_text(encoding="utf-8"))


def _build_bundle(plugin_root: Path, dest_root: Path, harness: Path) -> Path:
    cmd = ["python3", str(harness), "--plugin-root", str(plugin_root), "--dest", str(dest_root)]
    subprocess.run(cmd, check=True, capture_output=True)
    return dest_root


def test_sc_startup_bundle_contains_manifest_entries(tmp_path: Path, plugin_harness_path: Path) -> None:
    plugin_root = REPO_ROOT / "packages" / "sc-startup"
    manifest = _load_plugin_json(plugin_root)
    dest_root = tmp_path / "bundle"
    _build_bundle(plugin_root, dest_root, plugin_harness_path)
    # plugin.json must exist
    assert (dest_root / ".claude-plugin" / "plugin.json").is_file()
    # all manifest entries must be present
    for section in ("commands", "agents", "skills"):
        for rel_path in manifest.get(section, []) or []:
            assert (dest_root / rel_path).exists()


def test_agent_scripts_do_not_touch_global_home(
    tmp_path: Path,
    monkeypatch,
    clean_env: dict,
    plugin_harness_path: Path,
    temp_home: Path,
) -> None:
    require_yaml(clean_env)
    plugin_root = REPO_ROOT / "packages" / "sc-startup"
    dest_root = tmp_path / "bundle"
    _build_bundle(plugin_root, dest_root, plugin_harness_path)
    monkeypatch.setenv("HOME", str(temp_home))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".claude").mkdir()
    (repo_root / ".claude" / "sc-startup.yaml").write_text("startup-prompt: pm/a.md\ncheck-list: pm/b.md\n", encoding="utf-8")
    (repo_root / ".claude-plugin").mkdir()
    (repo_root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "sc-startup", "version": "0.7.0"}]}),
        encoding="utf-8",
    )
    # run init agent directly from source to keep deterministic behavior
    init_script = REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_startup_init.py"
    res = subprocess.run(
        ["python3", str(init_script)],
        input=json.dumps({"repo_root": str(repo_root), "detect_plugins": True}),
        text=True,
        capture_output=True,
        check=False,
        env=clean_env,
    )
    payload = json.loads(res.stdout)
    assert payload["success"] is True
    # no global state should be written under HOME
    assert not any(temp_home.rglob("*"))
