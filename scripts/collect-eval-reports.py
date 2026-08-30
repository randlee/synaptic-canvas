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


def write_index() -> Path:
    """(Re)generate site/reports/evals/index.html listing every published report,
    grouped by package, newest first — GitHub Pages has no directory listing."""
    import html as _html
    rows = []
    for pkg_dir in sorted(p for p in SITE_EVALS_DIR.iterdir()
                          if p.is_dir()) if SITE_EVALS_DIR.is_dir() else []:
        reports = sorted(pkg_dir.glob("*.html"), reverse=True)
        if not reports:
            continue
        items = "".join(
            f'<li><a href="{pkg_dir.name}/{r.name}">{_html.escape(r.name)}</a></li>'
            for r in reports)
        rows.append(f"<section><h2>{_html.escape(pkg_dir.name)}</h2>"
                    f"<ul>{items}</ul></section>")
    SITE_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    index = SITE_EVALS_DIR / "index.html"
    index.write_text(
        "<!doctype html><meta charset='utf-8'><title>Eval reports</title>"
        "<style>body{font-family:system-ui;margin:2rem;max-width:50rem}"
        "h2{margin-bottom:.3rem}ul{margin-top:.3rem}</style>"
        "<h1>Plugin eval reports</h1>"
        "<p>Newest first per package. Naming: "
        "<code>&lt;date-time&gt;-&lt;eval-name&gt;.html</code>; "
        "<code>-harness</code> = test-packages harness run.</p>"
        + "".join(rows), encoding="utf-8")
    return index


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
    index = write_index()
    print(f"{len(copied)} report(s) collected; index: {index.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
