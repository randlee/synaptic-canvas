"""Tests for scripts/sync-marketplace-json.py (marketplace/registry sync)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "sync_marketplace_json", REPO_ROOT / "scripts" / "sync-marketplace-json.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_registry(path: Path, packages: list[dict]) -> None:
    path.write_text(json.dumps({
        "name": "registry",
        "packages": packages,
    }))


def _write_marketplace(path: Path, plugins: list[dict]) -> None:
    path.write_text(json.dumps({
        "name": "marketplace",
        "plugins": plugins,
    }))


def _pkg(name="demo-pkg", version="1.0.0", description="A demo package",
         keywords=None, license="MIT", category="tools", author=None):
    return {
        "name": name,
        "source": f"./packages/{name}",
        "version": version,
        "description": description,
        "author": author if author is not None else {"name": "randlee"},
        "license": license,
        "keywords": keywords if keywords is not None else [],
        "category": category,
    }


def test_keywords_survive_sync_round_trip(tmp_path):
    """When registry and marketplace already agree on keywords, syncing must
    not disturb them (round-trip identity)."""
    mod = _load()
    registry_path = tmp_path / "registry.json"
    marketplace_path = tmp_path / "marketplace.json"

    keywords = ["cli", "ai", "mcp"]
    _write_registry(registry_path, [_pkg(keywords=keywords)])
    _write_marketplace(marketplace_path, [_pkg(keywords=keywords)])

    result = mod.sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert isinstance(result, mod.Success)

    marketplace = json.loads(marketplace_path.read_text())
    assert marketplace["plugins"][0]["keywords"] == keywords


def test_regression_empty_registry_keywords_do_not_blank_marketplace(tmp_path):
    """Regression test for the known bug: registry.json's "keywords" field is
    frequently an empty list (update-registry.py does not yet populate it
    from manifest.yaml's "tags"). Running the sync must NOT wipe out real
    keywords that already exist in marketplace.json just because the
    registry's copy is empty."""
    mod = _load()
    registry_path = tmp_path / "registry.json"
    marketplace_path = tmp_path / "marketplace.json"

    real_keywords = ["cli", "ai", "mcp", "templates", "simulator", "review", "skills"]
    # Registry has the (buggy) empty keywords list, as seen in production.
    _write_registry(registry_path, [_pkg(keywords=[])])
    _write_marketplace(marketplace_path, [_pkg(keywords=real_keywords)])

    result = mod.sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert isinstance(result, mod.Success)

    marketplace = json.loads(marketplace_path.read_text())
    assert marketplace["plugins"][0]["keywords"] == real_keywords, (
        "sync-marketplace-json.py blanked out marketplace.json keywords "
        "using an empty registry.json value"
    )


def test_nonempty_registry_keywords_update_marketplace(tmp_path):
    """When the registry genuinely has different, non-empty keywords, the
    sync should still apply them (registry remains the source of truth for
    real data, just not for accidental empties)."""
    mod = _load()
    registry_path = tmp_path / "registry.json"
    marketplace_path = tmp_path / "marketplace.json"

    old_keywords = ["cli"]
    new_keywords = ["cli", "ai", "mcp"]
    _write_registry(registry_path, [_pkg(keywords=new_keywords)])
    _write_marketplace(marketplace_path, [_pkg(keywords=old_keywords)])

    result = mod.sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert isinstance(result, mod.Success)

    marketplace = json.loads(marketplace_path.read_text())
    assert marketplace["plugins"][0]["keywords"] == new_keywords


def test_missing_package_added_with_registry_keywords(tmp_path):
    """A package present in registry but absent from marketplace should be
    added, carrying over whatever keywords the registry has."""
    mod = _load()
    registry_path = tmp_path / "registry.json"
    marketplace_path = tmp_path / "marketplace.json"

    keywords = ["new", "package"]
    _write_registry(registry_path, [_pkg(name="new-pkg", keywords=keywords)])
    _write_marketplace(marketplace_path, [])

    result = mod.sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert isinstance(result, mod.Success)

    marketplace = json.loads(marketplace_path.read_text())
    assert marketplace["plugins"][0]["name"] == "new-pkg"
    assert marketplace["plugins"][0]["keywords"] == keywords


def test_dry_run_does_not_write_file(tmp_path):
    mod = _load()
    registry_path = tmp_path / "registry.json"
    marketplace_path = tmp_path / "marketplace.json"

    _write_registry(registry_path, [_pkg(version="2.0.0")])
    _write_marketplace(marketplace_path, [_pkg(version="1.0.0")])
    original = marketplace_path.read_text()

    result = mod.sync_marketplace(registry_path, marketplace_path, dry_run=True)
    assert isinstance(result, mod.Success)
    assert marketplace_path.read_text() == original


def test_other_fields_still_sync_from_registry(tmp_path):
    """license/category should still sync normally (only keywords gets the
    empty-value guard)."""
    mod = _load()
    registry_path = tmp_path / "registry.json"
    marketplace_path = tmp_path / "marketplace.json"

    _write_registry(registry_path, [_pkg(license="Apache-2.0", category="testing")])
    _write_marketplace(marketplace_path, [_pkg(license="MIT", category="tools")])

    result = mod.sync_marketplace(registry_path, marketplace_path, dry_run=False)
    assert isinstance(result, mod.Success)

    marketplace = json.loads(marketplace_path.read_text())
    assert marketplace["plugins"][0]["license"] == "Apache-2.0"
    assert marketplace["plugins"][0]["category"] == "testing"
