"""Tests for set-package-version.py marketplace regeneration."""

import importlib.util
import json
from pathlib import Path

import yaml

spec = importlib.util.spec_from_file_location(
    "set_package_version",
    Path(__file__).parent.parent.parent / "scripts" / "set-package-version.py",
)
set_version_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(set_version_module)

regenerate_marketplace_json = set_version_module.regenerate_marketplace_json

FORWARDED = {
    "name": "aa-forwarded",
    "description": "Hosted in another repo.",
    "author": {"name": "randlee"},
    "category": "tools",
    "source": {
        "source": "git-subdir",
        "url": "https://github.com/randlee/aa-forwarded.git",
        "path": "packages/aa-forwarded",
        "ref": "main",
    },
}


def make_repo(tmp_path: Path, plugins: list[dict]) -> Path:
    pkg_dir = tmp_path / "packages" / "sc-local"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "sc-local",
                "version": "2.0.0",
                "description": "Local package.",
                "author": "randlee",
                "license": "MIT",
                "tags": ["local"],
                "category": "tools",
            }
        )
    )
    (tmp_path / "packages" / "shared").mkdir()
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "marketplace.json").write_text(
        json.dumps(
            {"name": "synaptic-canvas", "metadata": {"version": "1.0.0"}, "plugins": plugins}
        )
    )
    return tmp_path


def read_plugins(repo: Path) -> list[dict]:
    return json.loads((repo / ".claude-plugin" / "marketplace.json").read_text())["plugins"]


def test_forwarded_entries_survive_regeneration(tmp_path):
    local = {"name": "sc-local", "source": "./packages/sc-local", "version": "1.0.0"}
    repo = make_repo(tmp_path, [FORWARDED, local])

    regenerate_marketplace_json(repo)

    plugins = read_plugins(repo)
    assert [p["name"] for p in plugins] == ["aa-forwarded", "sc-local"]
    assert plugins[0] == FORWARDED
    assert plugins[1]["version"] == "2.0.0"


def test_stale_local_entries_are_still_removed(tmp_path):
    stale = {"name": "sc-gone", "source": "./packages/sc-gone", "version": "1.0.0"}
    repo = make_repo(tmp_path, [stale, FORWARDED])

    regenerate_marketplace_json(repo)

    assert [p["name"] for p in read_plugins(repo)] == ["aa-forwarded", "sc-local"]
