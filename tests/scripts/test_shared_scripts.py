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

    assert set(changed) == {"sc-a:scripts/sc_shared.py", "sc-b:scripts/sc_shared.py"}
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
    mismatched, missing, invalid_sources = validate_mod.compare_shared_script(canonical, packages_dir)

    assert mismatched == ["sc-b:scripts/sc_shared.py"]
    assert missing == []
    assert invalid_sources == []


def test_sync_explicit_shared_script_mapping(tmp_path: Path):
    canonical = tmp_path / "packages" / "shared" / "scripts" / "launchpad_shared.py"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("print('launchpad shared')\n")

    packages_dir = tmp_path / "packages"
    package_dir = packages_dir / "sc-launchpad"
    (package_dir / "scripts").mkdir(parents=True)
    (package_dir / "manifest.yaml").write_text(
        "\n".join(
            [
                "name: sc-launchpad",
                "version: 0.1.0",
                "description: test",
                "author: test",
                "license: MIT",
                "artifacts:",
                "  scripts:",
                "    - scripts/launchpad_shared.py",
                "shared_scripts:",
                "  - source: packages/shared/scripts/launchpad_shared.py",
                "    target: scripts/launchpad_shared.py",
                "",
            ]
        )
    )

    sync_mod = load_module(Path("scripts/sync-shared-scripts.py"), "sync_shared_explicit")
    changed = sync_mod.sync_shared_script(
        tmp_path / "packages" / "shared" / "scripts" / "sc_shared.py",
        packages_dir,
    )

    assert changed == ["sc-launchpad:scripts/launchpad_shared.py"]
    assert (package_dir / "scripts" / "launchpad_shared.py").read_text() == "print('launchpad shared')\n"


def test_validate_explicit_shared_script_mapping(tmp_path: Path):
    default_canonical = tmp_path / "packages" / "shared" / "scripts" / "sc_shared.py"
    default_canonical.parent.mkdir(parents=True)
    default_canonical.write_text("print('shared')\n")

    explicit_canonical = tmp_path / "packages" / "shared" / "scripts" / "launchpad_shared.py"
    explicit_canonical.write_text("print('launchpad shared')\n")

    packages_dir = tmp_path / "packages"
    package_dir = packages_dir / "sc-launchpad"
    scripts_dir = package_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    (package_dir / "manifest.yaml").write_text(
        "\n".join(
            [
                "name: sc-launchpad",
                "version: 0.1.0",
                "description: test",
                "author: test",
                "license: MIT",
                "artifacts:",
                "  scripts:",
                "    - scripts/launchpad_shared.py",
                "shared_scripts:",
                "  - source: packages/shared/scripts/launchpad_shared.py",
                "    target: scripts/launchpad_shared.py",
                "",
            ]
        )
    )
    (scripts_dir / "launchpad_shared.py").write_text("print('different')\n")

    validate_mod = load_module(Path("scripts/validate-shared-scripts.py"), "validate_shared_explicit")
    mismatched, missing, invalid_sources = validate_mod.compare_shared_script(default_canonical, packages_dir)

    assert mismatched == ["sc-launchpad:scripts/launchpad_shared.py"]
    assert missing == []
    assert invalid_sources == []
