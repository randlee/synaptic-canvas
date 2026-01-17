import json
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _copy_plugin_root(src_root: Path, dest_root: Path) -> None:
    if dest_root.exists():
        shutil.rmtree(dest_root)
    shutil.copytree(src_root, dest_root)


def _build_bundle(plugin_root: Path, dest_root: Path) -> None:
    harness = REPO_ROOT / "test-packages" / "test_fixtures" / "plugin_test_harness.py"
    cmd = ["python3", str(harness), "--plugin-root", str(plugin_root), "--dest", str(dest_root)]
    subprocess.run(cmd, check=True, capture_output=True)


def test_local_install_bundle_is_relative(tmp_path: Path) -> None:
    plugin_root = REPO_ROOT / "packages" / "sc-startup"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    dest_root = workspace / "plugins" / "sc-startup"
    _build_bundle(plugin_root, dest_root)
    assert dest_root.is_dir()
    assert dest_root.is_relative_to(workspace)
    assert (dest_root / ".claude-plugin" / "plugin.json").is_file()


def test_bundle_excludes_unlisted_files(tmp_path: Path) -> None:
    plugin_root = REPO_ROOT / "packages" / "sc-startup"
    scratch = tmp_path / "plugin_copy"
    _copy_plugin_root(plugin_root, scratch)
    extra = scratch / "EXTRA.txt"
    extra.write_text("do not ship\n", encoding="utf-8")
    dest_root = tmp_path / "bundle"
    _build_bundle(scratch, dest_root)
    manifest = json.loads((scratch / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert (dest_root / ".claude-plugin" / "plugin.json").is_file()
    assert not (dest_root / "EXTRA.txt").exists()
    # ensure all listed entries exist
    for section in ("commands", "agents", "skills"):
        for rel_path in manifest.get(section, []) or []:
            assert (dest_root / rel_path).exists()
