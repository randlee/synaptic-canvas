"""
Compatibility layer for migration from reporter.py to html_report module.

This module provides backward-compatible wrappers for the old API:
- HTMLReportGenerator: Wraps HTMLReportBuilder
- write_html_report: Uses HTMLReportBuilder internally

These are deprecated and will be removed in a future version.
Use HTMLReportBuilder and BuilderConfig directly for new code.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from .builder import HTMLReportBuilder
from .models import BuilderConfig

if TYPE_CHECKING:
    from ..models import FixtureReport

logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """Legacy HTML report generator (DEPRECATED).

    This class provides backward compatibility with the old HTMLReportGenerator
    API from harness.reporter. It delegates to HTMLReportBuilder internally.

    DEPRECATED: Use HTMLReportBuilder from harness.html_report instead.

    Example migration:
        # Old (deprecated):
        from harness.reporter import HTMLReportGenerator
        generator = HTMLReportGenerator()
        html = generator.generate(report)

        # New (recommended):
        from harness.html_report import HTMLReportBuilder
        builder = HTMLReportBuilder()
        html = builder.build(report)
    """

    def __init__(self):
        """Initialize the HTML generator."""
        warnings.warn(
            "HTMLReportGenerator is deprecated. "
            "Use HTMLReportBuilder from harness.html_report instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._builder = HTMLReportBuilder()

    def generate(self, report: "FixtureReport") -> str:
        """Generate HTML report from fixture report.

        Args:
            report: FixtureReport to convert to HTML

        Returns:
            Complete HTML document as string
        """
        return self._builder.build(report)


def write_html_report(
    report: "FixtureReport",
    output_path: Path | str,
) -> Path:
    """Write a fixture report to HTML file.

    This function provides backward compatibility with the old write_html_report
    function from harness.reporter. It uses HTMLReportBuilder internally.

    Args:
        report: FixtureReport to convert to HTML
        output_path: Path for output file

    Returns:
        Path to written file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    builder = HTMLReportBuilder()
    html_content = builder.build(report)

    with open(output_path, "w") as f:
        f.write(html_content)

    logger.info(f"Wrote HTML report to: {output_path}")
    return output_path
