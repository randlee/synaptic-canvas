"""
HTML Report component builders.

This module provides builder classes for each section of the HTML test report.
Each builder follows the Builder pattern, transforming Pydantic models into
HTML string fragments.

Usage:
    from harness.html_report.components import HeaderBuilder, TabsBuilder

    header_builder = HeaderBuilder()
    html = header_builder.build(header_data)
"""

from .base import BaseBuilder, CopyButtonBuilder
from .header import HeaderBuilder
from .tabs import TabsBuilder
from .test_case import TestCaseBuilder
from .status_banner import StatusBannerBuilder
from .expectations import ExpectationsBuilder
from .timeline import TimelineBuilder
from .assessment import AssessmentBuilder
from .reproduce import ReproduceBuilder
from .debug import DebugBuilder
from .plugin_verification import PluginVerificationBuilder

__all__ = [
    "BaseBuilder",
    "CopyButtonBuilder",
    "HeaderBuilder",
    "TabsBuilder",
    "TestCaseBuilder",
    "StatusBannerBuilder",
    "ExpectationsBuilder",
    "TimelineBuilder",
    "AssessmentBuilder",
    "ReproduceBuilder",
    "DebugBuilder",
    "PluginVerificationBuilder",
]
