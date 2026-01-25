#!/usr/bin/env python3
"""Unit tests for shared script sync/validate tools."""

import importlib.util
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_sync_shared_scripts(tmp_path: Path):
    canonical = tmp_path / "packages" / "shared" / "scripts" / "sc_shared.py"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("print('shared')\n")

    packages_dir = tmp_path / "packages"
    pkg_a = packages_dir / "sc-a" / "scripts"
    pkg_b = packages_dir / "sc-b" / "scripts"
    pkg_a.mkdir(parents=True)
    pkg_b.mkdir(parents=True)

    sync_mod = load_module(Path("scripts/sync-shared-scripts.py"), "sync_shared")
    changed = sync_mod.sync_shared_script(canonical, packages_dir)

    assert set(changed) == {"sc-a", "sc-b"}
    assert (pkg_a / "sc_shared.py").read_text() == "print('shared')\n"
    assert (pkg_b / "sc_shared.py").read_text() == "print('shared')\n"


def test_validate_shared_scripts(tmp_path: Path):
    canonical = tmp_path / "packages" / "shared" / "scripts" / "sc_shared.py"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("print('shared')\n")

    packages_dir = tmp_path / "packages"
    pkg_a = packages_dir / "sc-a" / "scripts"
    pkg_b = packages_dir / "sc-b" / "scripts"
    pkg_a.mkdir(parents=True)
    pkg_b.mkdir(parents=True)

    (pkg_a / "sc_shared.py").write_text("print('shared')\n")
    (pkg_b / "sc_shared.py").write_text("print('different')\n")

    validate_mod = load_module(Path("scripts/validate-shared-scripts.py"), "validate_shared")
    mismatched, missing = validate_mod.compare_shared_script(canonical, packages_dir)

    assert mismatched == ["sc-b"]
    assert missing == []
