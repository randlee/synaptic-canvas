#!/usr/bin/env python3
"""Collect `claude plugin eval` HTML reports into the site tree.

Scans packages/*/evals/results/<run>/report.html and copies each to

    site/reports/evals/<package>/<date-time>-<eval-name>.html

where <date-time> is the run directory's timestamp normalized to
YYYYMMDD-HHMMSS when parseable (kept verbatim otherwise) and <eval-name> is
the single case's name when the run covered one case, else the suite name
from aggregate-result.json (fallback: "suite").

Idempotent: an existing destination file is left alone (re-runs of the
collector never clobber a published report); use --force to overwrite.

Usage: python3 scripts/collect-eval-reports.py [--package NAME] [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = REPO_ROOT / "packages"
SITE_EVALS_DIR = REPO_ROOT / "site" / "reports" / "evals"


def _slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-")
    return s or "suite"


def _normalize_timestamp(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 14:  # YYYYMMDDHHMMSS...
        return f"{digits[:8]}-{digits[8:14]}"
    if len(digits) == 8:  # date only
        return digits
    return _slug(raw)


def _eval_name(run_dir: Path) -> str:
    agg = run_dir / "aggregate-result.json"
    try:
        data = json.loads(agg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "suite"
    cases = data.get("cases") or []
    if len(cases) == 1 and cases[0].get("name"):
        return _slug(cases[0]["name"])
    suite = (data.get("suite") or {}).get("name")
    return _slug(suite) if suite else "suite"


HARNESS_REPORTS_DIR = REPO_ROOT / "test-packages" / "reports"


def _collect_harness_reports(package: str | None, force: bool) -> list[Path]:
    """Publish test-packages harness reports for <pkg>-evals fixtures.

    The harness writes test-packages/reports/<pkg>-evals.html per run; the
    copy is stamped with the report file's mtime so successive runs archive
    side by side.
    """
    copied: list[Path] = []
    if not HARNESS_REPORTS_DIR.is_dir():
        return copied
    import datetime as _dt
    for report in sorted(HARNESS_REPORTS_DIR.glob("*-evals.html")):
        pkg = report.stem[: -len("-evals")]
        if package and pkg != package:
            continue
        stamp = _dt.datetime.fromtimestamp(report.stat().st_mtime).strftime("%Y%m%d-%H%M%S")
        dst = SITE_EVALS_DIR / pkg / f"{stamp}-harness.html"
        if dst.exists() and not force:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(report, dst)
        copied.append(dst)
    return copied


def collect(package: str | None = None, force: bool = False) -> list[Path]:
    copied: list[Path] = _collect_harness_reports(package, force)
    pkg_dirs = [PACKAGES_DIR / package] if package else sorted(PACKAGES_DIR.iterdir())
    for pkg_dir in pkg_dirs:
        results = pkg_dir / "evals" / "results"
        if not results.is_dir():
            continue
        for run_dir in sorted(p for p in results.iterdir() if p.is_dir()):
            report = run_dir / "report.html"
            if not report.is_file():
                continue
            name = f"{_normalize_timestamp(run_dir.name)}-{_eval_name(run_dir)}.html"
            dst = SITE_EVALS_DIR / pkg_dir.name / name
            if dst.exists() and not force:
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report, dst)
            copied.append(dst)
    return copied


REPORT_NAME_RE = re.compile(r"^(\d{8}-\d{6})-(.+)\.html$")

_PAGE_STYLE = (
    "<style>body{font-family:system-ui;margin:2rem;max-width:60rem}"
    "h2{margin:1.2rem 0 .3rem}table{border-collapse:collapse;width:100%}"
    "td,th{border:1px solid #ccc;padding:.3rem .6rem;text-align:left}"
    "a{text-decoration:none}small{color:#666}</style>"
)


def _scan_reports(pkg_dir: Path) -> list[tuple[str, str, str]]:
    """(stamp, eval_name, filename) for each report, newest first.

    Filenames follow <YYYYMMDD-HHMMSS>-<eval-name>.html; anything else is kept
    with an empty stamp (sorted last) and the stem as its eval name.
    """
    entries = []
    for report in pkg_dir.glob("*.html"):
        if report.name in ("history.html", "index.html"):
            continue
        m = REPORT_NAME_RE.match(report.name)
        if m:
            entries.append((m.group(1), m.group(2), report.name))
        else:
            entries.append(("", report.stem, report.name))
    return sorted(entries, key=lambda e: e[0], reverse=True)


def _fmt_stamp(stamp: str) -> str:
    if len(stamp) == 15:  # YYYYMMDD-HHMMSS
        d, t = stamp.split("-")
        return f"{d[:4]}-{d[4:6]}-{d[6:8]} {t[:2]}:{t[2:4]}:{t[4:6]}"
    return stamp or "(unstamped)"


def write_evals_pages() -> list[Path]:
    """(Re)generate the autogenerated eval pages under site/reports/evals/:

    - evals.html: one section per plugin that produced reports, listing the
      MOST RECENT report for each distinct eval (with run count and a link to
      that plugin's full history)
    - <plugin>/history.html: every report for that plugin, newest first
    - index.html: redirect to evals.html (the Pages landing for this folder)

    GitHub Pages serves these statically; regenerate after any eval run.
    """
    import html as _html

    SITE_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    sections = []
    for pkg_dir in sorted(p for p in SITE_EVALS_DIR.iterdir() if p.is_dir()):
        entries = _scan_reports(pkg_dir)
        if not entries:
            continue
        pkg = pkg_dir.name

        # Full history page (newest first).
        hist_rows = "".join(
            f'<tr><td>{_fmt_stamp(stamp)}</td><td>{_html.escape(name)}</td>'
            f'<td><a href="{fname}">{_html.escape(fname)}</a></td></tr>'
            for stamp, name, fname in entries)
        history = pkg_dir / "history.html"
        history.write_text(
            f"<!doctype html><meta charset='utf-8'>"
            f"<title>{_html.escape(pkg)} eval history</title>{_PAGE_STYLE}"
            f"<h1>{_html.escape(pkg)} — full eval history</h1>"
            f"<p><a href='../evals.html'>&larr; all plugins</a> · "
            f"{len(entries)} report(s), newest first</p>"
            f"<table><tr><th>run</th><th>eval</th><th>report</th></tr>{hist_rows}</table>",
            encoding="utf-8")
        written.append(history)

        # Latest report per distinct eval (entries are newest-first).
        latest: dict[str, tuple[str, str]] = {}
        counts: dict[str, int] = {}
        for stamp, name, fname in entries:
            counts[name] = counts.get(name, 0) + 1
            latest.setdefault(name, (stamp, fname))
        rows = "".join(
            f'<tr><td><a href="{pkg}/{fname}">{_html.escape(name)}</a></td>'
            f'<td>{_fmt_stamp(stamp)}</td><td>{counts[name]}</td></tr>'
            for name, (stamp, fname) in sorted(latest.items()))
        sections.append(
            f"<section><h2>{_html.escape(pkg)}</h2>"
            f"<table><tr><th>eval</th><th>latest run</th><th>runs</th></tr>{rows}</table>"
            f"<p><small><a href='{pkg}/history.html'>full history "
            f"({len(entries)} reports)</a></small></p></section>")

    evals_page = SITE_EVALS_DIR / "evals.html"
    evals_page.write_text(
        "<!doctype html><meta charset='utf-8'><title>Plugin eval reports</title>"
        + _PAGE_STYLE
        + "<h1>Plugin eval reports</h1>"
        "<p>Latest report per eval, per plugin. Autogenerated by "
        "<code>scripts/collect-eval-reports.py</code> — do not edit.</p>"
        + "".join(sections), encoding="utf-8")
    written.append(evals_page)

    index = SITE_EVALS_DIR / "index.html"
    index.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='0; url=evals.html'>"
        "<title>Eval reports</title><a href='evals.html'>Eval reports</a>",
        encoding="utf-8")
    written.append(index)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--package", help="collect only this package's reports")
    parser.add_argument("--force", action="store_true", help="overwrite existing site reports")
    args = parser.parse_args(argv)
    if args.package and not (PACKAGES_DIR / args.package).is_dir():
        print(f"error: unknown package: {args.package}", file=sys.stderr)
        return 1
    copied = collect(args.package, args.force)
    for path in copied:
        print(f"collected: {path.relative_to(REPO_ROOT)}")
    pages = write_evals_pages()
    print(f"{len(copied)} report(s) collected; regenerated "
          + ", ".join(str(p.relative_to(REPO_ROOT)) for p in pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
