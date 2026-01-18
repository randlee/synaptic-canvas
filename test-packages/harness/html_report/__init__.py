"""
HTML Report Builder for Claude Code Test Harness.

This module provides a modular, builder-pattern based HTML report generator
for test results. The design separates data transformation from HTML rendering,
enabling unit-testable components and flexible report customization.

Public API:
    HTMLReportBuilder - Main orchestrator for building complete HTML reports
    BuilderConfig - Configuration options for customizing report output
    write_html_report - Convenience function to write report to file

Compatibility API (deprecated):
    HTMLReportGenerator - Legacy class, wraps HTMLReportBuilder

Example:
    from harness.html_report import HTMLReportBuilder, BuilderConfig
    from harness.models import FixtureReport

    # Load or create a fixture report
    report = FixtureReport(...)

    # Build HTML with custom config
    config = BuilderConfig(default_editor="pycharm")
    builder = HTMLReportBuilder(config=config)
    html = builder.build(report)

    # Write to file
    with open("report.html", "w") as f:
        f.write(html)

    # Or use convenience function
    from harness.html_report import write_html_report
    write_html_report(report, "output/report.html")
"""

from .builder import HTMLReportBuilder
from .models import BuilderConfig, StatusDisplay
from .compat import HTMLReportGenerator, write_html_report

__all__ = [
    # New API
    "HTMLReportBuilder",
    "BuilderConfig",
    "StatusDisplay",
    # Compatibility (deprecated)
    "HTMLReportGenerator",
    "write_html_report",
]
