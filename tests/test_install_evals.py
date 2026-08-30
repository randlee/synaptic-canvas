"""cmd_install must skip a package's evals/ folder unless --include-evals is passed."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sc_cli import install as sc_install  # noqa: E402


def _fake_package(packages_dir: Path) -> Path:
    pkg = packages_dir / "demo-pkg"
    (pkg / "scripts").mkdir(parents=True)
    (pkg / "scripts" / "tool.py").write_text("print('hi')\n")
    (pkg / "manifest.yaml").write_text(
        "name: demo-pkg\nversion: 0.1.0\nartifacts:\n  scripts:\n    - scripts/tool.py\n"
    )
    case = pkg / "evals" / "case-one"
    (case / "graders").mkdir(parents=True)
    (case / "prompt.md").write_text("---\nname: x\n---\nprompt\n")
    (case / "graders" / "g.md").write_text("---\ntype: regex\npattern: x\n---\n")
    (case / "scaffold.sh").write_text("#!/bin/sh\ntrue\n")
    results = pkg / "evals" / "results" / "20260830"
    results.mkdir(parents=True)
    (results / "aggregate-result.json").write_text("{}")
    return pkg


def _install(tmp_path, monkeypatch, **kwargs) -> Path:
    packages = tmp_path / "packages"
    _fake_package(packages)
    monkeypatch.setattr(sc_install, "PACKAGES_DIR", packages)
    dest = tmp_path / "proj" / ".claude"
    assert sc_install.cmd_install("demo-pkg", str(dest), **kwargs) == 0
    return dest


def test_default_install_skips_evals(tmp_path, monkeypatch):
    dest = _install(tmp_path, monkeypatch)
    assert (dest / "scripts" / "tool.py").exists()
    assert not (dest / "evals").exists()


def test_include_evals_copies_suite_but_not_results(tmp_path, monkeypatch):
    dest = _install(tmp_path, monkeypatch, include_evals=True)
    base = dest / "evals" / "demo-pkg"
    assert (base / "case-one" / "prompt.md").exists()
    assert (base / "case-one" / "graders" / "g.md").exists()
    assert (base / "case-one" / "scaffold.sh").exists()
    # results/ (prior run output) never travels with an install
    assert not (base / "results").exists()


def test_uninstall_removes_installed_evals(tmp_path, monkeypatch):
    dest = _install(tmp_path, monkeypatch, include_evals=True)
    assert sc_install.cmd_uninstall("demo-pkg", str(dest)) == 0
    assert not (dest / "evals" / "demo-pkg").exists()
    assert not (dest / "scripts" / "tool.py").exists()


def test_cli_flag_wires_through(tmp_path, monkeypatch):
    packages = tmp_path / "packages"
    _fake_package(packages)
    monkeypatch.setattr(sc_install, "PACKAGES_DIR", packages)
    dest = tmp_path / "p2" / ".claude"
    assert sc_install.main(["install", "demo-pkg", "--dest", str(dest),
                            "--include-evals"]) == 0
    assert (dest / "evals" / "demo-pkg" / "case-one" / "prompt.md").exists()
    dest2 = tmp_path / "p3" / ".claude"
    assert sc_install.main(["install", "demo-pkg", "--dest", str(dest2)]) == 0
    assert not (dest2 / "evals").exists()
