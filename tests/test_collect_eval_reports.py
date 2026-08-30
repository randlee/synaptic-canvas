"""Tests for scripts/collect-eval-reports.py (site publication of eval reports)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "collect_eval_reports", REPO_ROOT / "scripts" / "collect-eval-reports.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_run(pkg_dir: Path, run_name: str, cases: list[str], suite: str = "sc-gh-stack"):
    run = pkg_dir / "evals" / "results" / run_name
    run.mkdir(parents=True)
    (run / "report.html").write_text("<h1>report</h1>")
    (run / "aggregate-result.json").write_text(json.dumps({
        "schemaVersion": "1",
        "suite": {"name": suite, "caseCount": len(cases)},
        "cases": [{"name": c} for c in cases],
    }))
    return run


def _setup(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "PACKAGES_DIR", tmp_path / "packages")
    monkeypatch.setattr(mod, "SITE_EVALS_DIR", tmp_path / "site" / "reports" / "evals")
    pkg = tmp_path / "packages" / "demo-pkg"
    pkg.mkdir(parents=True)
    return mod, pkg


def test_single_case_run_named_by_case(tmp_path, monkeypatch):
    mod, pkg = _setup(tmp_path, monkeypatch)
    _fake_run(pkg, "2026-08-30T14-22-05", ["merge-verify-outcome"])
    copied = mod.collect()
    assert [p.name for p in copied] == ["20260830-142205-merge-verify-outcome.html"]
    assert copied[0].parent.name == "demo-pkg"
    assert copied[0].read_text() == "<h1>report</h1>"


def test_multi_case_run_named_by_suite(tmp_path, monkeypatch):
    mod, pkg = _setup(tmp_path, monkeypatch)
    _fake_run(pkg, "20260830143000", ["a", "b"], suite="sc-gh-stack")
    copied = mod.collect()
    assert [p.name for p in copied] == ["20260830-143000-sc-gh-stack.html"]


def test_idempotent_without_force(tmp_path, monkeypatch):
    mod, pkg = _setup(tmp_path, monkeypatch)
    _fake_run(pkg, "20260830143000", ["a"])
    assert len(mod.collect()) == 1
    assert mod.collect() == []          # second sweep copies nothing
    assert len(mod.collect(force=True)) == 1


def test_unparseable_timestamp_and_missing_aggregate(tmp_path, monkeypatch):
    mod, pkg = _setup(tmp_path, monkeypatch)
    run = pkg / "evals" / "results" / "latest"
    run.mkdir(parents=True)
    (run / "report.html").write_text("x")
    copied = mod.collect()
    assert [p.name for p in copied] == ["latest-suite.html"]


def test_package_filter(tmp_path, monkeypatch):
    mod, pkg = _setup(tmp_path, monkeypatch)
    other = tmp_path / "packages" / "other-pkg"
    other.mkdir()
    _fake_run(pkg, "20260830143000", ["a"])
    _fake_run(other, "20260830143000", ["b"])
    copied = mod.collect(package="demo-pkg")
    assert all(p.parent.name == "demo-pkg" for p in copied) and len(copied) == 1
