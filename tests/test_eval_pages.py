"""Tests for the page-generation half of scripts/collect-eval-reports.py:
_scan_reports, _fmt_stamp, and write_evals_pages.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "collect_eval_reports", REPO_ROOT / "scripts" / "collect-eval-reports.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _setup(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "PACKAGES_DIR", tmp_path / "packages")
    monkeypatch.setattr(mod, "SITE_EVALS_DIR", tmp_path / "site" / "reports" / "evals")
    monkeypatch.setattr(mod, "HARNESS_REPORTS_DIR", tmp_path / "test-packages" / "reports")
    return mod


def _write_report(site_dir: Path, pkg: str, filename: str, content: str = "<h1>r</h1>") -> Path:
    pkg_dir = site_dir / pkg
    pkg_dir.mkdir(parents=True, exist_ok=True)
    f = pkg_dir / filename
    f.write_text(content, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# _fmt_stamp
# ---------------------------------------------------------------------------

def test_fmt_stamp_formats_full_stamp():
    mod = _load()
    assert mod._fmt_stamp("20260830-110903") == "2026-08-30 11:09:03"


def test_fmt_stamp_unstamped():
    mod = _load()
    assert mod._fmt_stamp("") == "(unstamped)"


def test_fmt_stamp_passthrough_for_odd_length():
    mod = _load()
    # Not the expected 15-char "YYYYMMDD-HHMMSS" shape: returned verbatim.
    assert mod._fmt_stamp("weird") == "weird"


# ---------------------------------------------------------------------------
# _scan_reports
# ---------------------------------------------------------------------------

def test_scan_reports_splits_stamp_and_eval_name(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    pkg_dir = mod.SITE_EVALS_DIR / "demo-pkg"
    pkg_dir.mkdir(parents=True)
    m = mod.REPORT_NAME_RE.match("20260830-110903-merge-verify-outcome.html")
    assert m is not None
    assert m.group(1) == "20260830-110903"
    assert m.group(2) == "merge-verify-outcome"


def test_scan_reports_dashed_eval_and_suite_names(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    pkg_dir = mod.SITE_EVALS_DIR / "demo-pkg"
    pkg_dir.mkdir(parents=True)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-110903-merge-verify-outcome.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260829-090000-sc-gh-stack-evals.html")
    entries = mod._scan_reports(pkg_dir)
    by_name = {name: (stamp, fname) for stamp, name, fname in entries}
    assert by_name["merge-verify-outcome"] == (
        "20260830-110903", "20260830-110903-merge-verify-outcome.html")
    assert by_name["sc-gh-stack-evals"] == (
        "20260829-090000", "20260829-090000-sc-gh-stack-evals.html")


def test_scan_reports_excludes_history_and_index(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    pkg_dir = mod.SITE_EVALS_DIR / "demo-pkg"
    pkg_dir.mkdir(parents=True)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-110903-merge-verify-outcome.html")
    (pkg_dir / "history.html").write_text("<h1>stale history</h1>", encoding="utf-8")
    (pkg_dir / "index.html").write_text("<h1>stale index</h1>", encoding="utf-8")
    entries = mod._scan_reports(pkg_dir)
    names = [fname for _, _, fname in entries]
    assert "history.html" not in names
    assert "index.html" not in names
    assert names == ["20260830-110903-merge-verify-outcome.html"]


def test_scan_reports_unstamped_sorts_last(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    pkg_dir = mod.SITE_EVALS_DIR / "demo-pkg"
    pkg_dir.mkdir(parents=True)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-110903-merge-verify-outcome.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "latest-suite.html")
    entries = mod._scan_reports(pkg_dir)
    assert entries[-1] == ("", "latest-suite", "latest-suite.html")
    assert entries[0][0] == "20260830-110903"


def test_scan_reports_newest_first_ordering(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    pkg_dir = mod.SITE_EVALS_DIR / "demo-pkg"
    pkg_dir.mkdir(parents=True)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260828-000000-a.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-000000-a.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260829-000000-a.html")
    entries = mod._scan_reports(pkg_dir)
    stamps = [e[0] for e in entries]
    assert stamps == sorted(stamps, reverse=True)
    assert stamps[0] == "20260830-000000"


# ---------------------------------------------------------------------------
# write_evals_pages
# ---------------------------------------------------------------------------

def test_no_section_for_plugin_dir_without_html_reports(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    mod.SITE_EVALS_DIR.mkdir(parents=True)
    empty_pkg = mod.SITE_EVALS_DIR / "empty-pkg"
    empty_pkg.mkdir()
    mod.write_evals_pages()
    evals_html = (mod.SITE_EVALS_DIR / "evals.html").read_text(encoding="utf-8")
    assert "empty-pkg" not in evals_html
    assert not (empty_pkg / "history.html").exists()


def test_section_shows_only_most_recent_report_per_distinct_eval(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260828-000000-merge-verify-outcome.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-000000-merge-verify-outcome.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260829-000000-sc-gh-stack-evals.html")
    mod.write_evals_pages()
    evals_html = (mod.SITE_EVALS_DIR / "evals.html").read_text(encoding="utf-8")

    # Most recent report for merge-verify-outcome is linked (not the older one).
    assert "20260830-000000-merge-verify-outcome.html" in evals_html
    assert "20260828-000000-merge-verify-outcome.html" not in evals_html
    # Correct run count for the eval with two runs.
    idx = evals_html.index("merge-verify-outcome")
    # find the row containing the count "2"
    row_end = evals_html.index("</tr>", idx)
    row = evals_html[idx:row_end]
    assert ">2<" in row

    # Single-run eval also appears with count 1.
    idx2 = evals_html.index("sc-gh-stack-evals")
    row_end2 = evals_html.index("</tr>", idx2)
    row2 = evals_html[idx2:row_end2]
    assert ">1<" in row2


def test_evals_links_carry_pkg_prefix_and_history_links_are_relative(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-000000-merge-verify-outcome.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260829-000000-merge-verify-outcome.html")
    mod.write_evals_pages()

    evals_html = (mod.SITE_EVALS_DIR / "evals.html").read_text(encoding="utf-8")
    assert 'href="demo-pkg/20260830-000000-merge-verify-outcome.html"' in evals_html
    assert "href='demo-pkg/history.html'" in evals_html

    history_html = (mod.SITE_EVALS_DIR / "demo-pkg" / "history.html").read_text(encoding="utf-8")
    assert 'href="20260830-000000-merge-verify-outcome.html"' in history_html
    assert 'href="demo-pkg/20260830-000000-merge-verify-outcome.html"' not in history_html


def test_history_lists_all_reports_in_descending_stamp_order(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260828-000000-a.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-000000-b.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260829-000000-c.html")
    mod.write_evals_pages()
    history_html = (mod.SITE_EVALS_DIR / "demo-pkg" / "history.html").read_text(encoding="utf-8")

    idx_30 = history_html.index("20260830-000000-b.html")
    idx_29 = history_html.index("20260829-000000-c.html")
    idx_28 = history_html.index("20260828-000000-a.html")
    assert idx_30 < idx_29 < idx_28
    assert "3 report(s)" in history_html


def test_history_and_index_excluded_from_scanning_after_stale_write(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    pkg_dir = mod.SITE_EVALS_DIR / "demo-pkg"
    pkg_dir.mkdir(parents=True)
    # Write a stale history.html before regenerating, plus one real report.
    (pkg_dir / "history.html").write_text("<h1>stale</h1>", encoding="utf-8")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-000000-a.html")

    mod.write_evals_pages()

    history_html = (pkg_dir / "history.html").read_text(encoding="utf-8")
    # Regenerated history.html should list only the real report, not itself.
    assert "1 report(s)" in history_html
    assert history_html.count("<tr>") == 2  # header row + one data row
    assert "stale" not in history_html


def test_unstamped_filenames_sort_last_and_render_unstamped(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-000000-a.html")
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "latest-suite.html")
    mod.write_evals_pages()

    history_html = (mod.SITE_EVALS_DIR / "demo-pkg" / "history.html").read_text(encoding="utf-8")
    idx_stamped = history_html.index("20260830-000000-a.html")
    idx_unstamped = history_html.index("latest-suite.html")
    assert idx_stamped < idx_unstamped
    assert "(unstamped)" in history_html

    evals_html = (mod.SITE_EVALS_DIR / "evals.html").read_text(encoding="utf-8")
    assert "(unstamped)" in evals_html or "latest-suite" in evals_html


def test_index_redirects_to_evals_and_evals_links_to_history(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-000000-a.html")
    mod.write_evals_pages()

    index_html = (mod.SITE_EVALS_DIR / "index.html").read_text(encoding="utf-8")
    assert "url=evals.html" in index_html
    assert "href='evals.html'" in index_html

    evals_html = (mod.SITE_EVALS_DIR / "evals.html").read_text(encoding="utf-8")
    assert "href='demo-pkg/history.html'" in evals_html


def test_multiple_plugins_produce_sorted_sections(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    _write_report(mod.SITE_EVALS_DIR, "zeta-pkg", "20260830-000000-a.html")
    _write_report(mod.SITE_EVALS_DIR, "alpha-pkg", "20260830-000000-b.html")
    mod.write_evals_pages()

    evals_html = (mod.SITE_EVALS_DIR / "evals.html").read_text(encoding="utf-8")
    assert "alpha-pkg" in evals_html and "zeta-pkg" in evals_html
    assert evals_html.index("alpha-pkg") < evals_html.index("zeta-pkg")
    assert (mod.SITE_EVALS_DIR / "alpha-pkg" / "history.html").exists()
    assert (mod.SITE_EVALS_DIR / "zeta-pkg" / "history.html").exists()


def test_write_evals_pages_returns_written_paths(tmp_path, monkeypatch):
    mod = _setup(tmp_path, monkeypatch)
    _write_report(mod.SITE_EVALS_DIR, "demo-pkg", "20260830-000000-a.html")
    written = mod.write_evals_pages()
    names = {p.name for p in written}
    assert {"evals.html", "history.html", "index.html"} <= names
