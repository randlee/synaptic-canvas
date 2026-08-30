"""Tests for eval-fixture report routing to site/reports/evals/."""
from __future__ import annotations

import re
from pathlib import Path

from harness.pytest_plugin import _eval_report_destination


def test_eval_fixture_routes_to_site_with_date_stamp():
    dest = _eval_report_destination("sc-gh-stack-evals", report_dir=None)
    assert dest is not None
    path, basename = dest
    assert path.parts[-4:] == ("site", "reports", "evals", "sc-gh-stack")
    assert re.fullmatch(r"\d{8}-\d{6}-sc-gh-stack-evals", basename)
    # Repo-root anchored, independent of cwd
    repo_root = Path(__file__).resolve().parents[3]
    assert path == repo_root / "site" / "reports" / "evals" / "sc-gh-stack"


def test_non_eval_fixture_unrouted():
    assert _eval_report_destination("sc-startup", report_dir=None) is None


def test_explicit_report_dir_overrides():
    assert _eval_report_destination("sc-gh-stack-evals", report_dir="/tmp/custom") is None
