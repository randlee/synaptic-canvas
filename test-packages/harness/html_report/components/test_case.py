"""
Test case component builder.

Orchestrates the building of a complete test case tab content by
composing multiple sub-builders for status banner, metadata, reproduce,
expectations, timeline, response, debug, and assessment sections.
"""

from ..models import (
    TestCaseDisplayModel,
    TestMetadataDisplayModel,
    ResponseDisplayModel,
    BuilderConfig,
)
from .base import BaseBuilder, CopyButtonBuilder
from .status_banner import StatusBannerBuilder
from .expectations import ExpectationsBuilder
from .timeline import TimelineBuilder
from .reproduce import ReproduceBuilder
from .debug import DebugBuilder
from .assessment import AssessmentBuilder
from .plugin_verification import PluginVerificationBuilder


class TestCaseBuilder(BaseBuilder[TestCaseDisplayModel]):
    """Builds a complete test case tab content by orchestrating sub-builders.

    The test case contains all sections:
    - Test title and description
    - Status banner
    - Test metadata grid
    - Reproduce section
    - Plugin verification (if plugins configured)
    - Expectations list
    - Timeline (collapsible)
    - Claude response (collapsible)
    - Debug information (collapsible)
    - Agent assessment (collapsible, optional)
    """

    def __init__(self, config: BuilderConfig | None = None):
        """Initialize test case builder with sub-builders.

        Args:
            config: Optional configuration for customizing output
        """
        super().__init__(config)

        # Initialize sub-builders
        self.status_banner_builder = StatusBannerBuilder(config)
        self.expectations_builder = ExpectationsBuilder(config)
        self.timeline_builder = TimelineBuilder(config)
        self.reproduce_builder = ReproduceBuilder(config)
        self.debug_builder = DebugBuilder(config)
        self.assessment_builder = AssessmentBuilder(config)
        self.plugin_verification_builder = PluginVerificationBuilder(config)

    def build(self, data: TestCaseDisplayModel) -> str:
        """Build complete test case HTML from display model.

        Args:
            data: TestCaseDisplayModel containing all test data

        Returns:
            Complete test case HTML string
        """
        self.validate(data)

        # Build each section
        status_banner_html = self.status_banner_builder.build(data.status_banner)
        metadata_html = self._build_metadata(data.metadata)
        reproduce_html = self.reproduce_builder.build(data.reproduce)

        # Build plugin verification if present
        plugin_verification_html = ""
        if data.plugin_verification and data.plugin_verification.has_plugins:
            plugin_verification_html = self.plugin_verification_builder.build(
                data.plugin_verification
            )

        expectations_html = self.expectations_builder.build(data.expectations)
        timeline_html = self.timeline_builder.build(data.timeline)
        response_html = self._build_response(data.response)
        debug_html = self.debug_builder.build(data.debug)

        # Build assessment if present
        assessment_html = ""
        if data.assessment:
            assessment_html = self.assessment_builder.build(data.assessment)

        return f'''<h1>{self.escape(data.test_name)}</h1>
<p class="description">{self.escape(data.description)}</p>

{status_banner_html}

{metadata_html}

{reproduce_html}

{plugin_verification_html}

{expectations_html}

{timeline_html}

{response_html}

{debug_html}

{assessment_html}'''

    def _build_metadata(self, data: TestMetadataDisplayModel) -> str:
        """Build test metadata grid section.

        Args:
            data: TestMetadataDisplayModel containing test metadata

        Returns:
            Test metadata HTML string
        """
        session_id_html = ""
        if data.session_id:
            session_id_html = f'''<div class="test-metadata-item">
      <span class="test-metadata-label">Session ID</span>
      <span class="test-metadata-value" style="font-family: monospace;">{self.escape(data.session_id)}</span>
    </div>'''

        return f'''<div class="test-metadata">
  <div class="test-metadata-grid">
    <div class="test-metadata-item">
      <span class="test-metadata-label">Test ID</span>
      <span class="test-metadata-value">{self.escape(data.test_id)}</span>
    </div>
    <div class="test-metadata-item">
      <span class="test-metadata-label">Test Name</span>
      <span class="test-metadata-value">{self.escape(data.test_name)}</span>
    </div>
    <div class="test-metadata-item">
      <span class="test-metadata-label">Fixture</span>
      <span class="test-metadata-value">{self.escape(data.fixture)}</span>
    </div>
    <div class="test-metadata-item">
      <span class="test-metadata-label">Package</span>
      <span class="test-metadata-value">{self.escape(data.package)}</span>
    </div>
    <div class="test-metadata-item">
      <span class="test-metadata-label">Model</span>
      <span class="test-metadata-value">{self.escape(data.model)}</span>
    </div>
    {session_id_html}
  </div>
</div>'''

    def _build_response(self, data: ResponseDisplayModel) -> str:
        """Build Claude response section.

        Args:
            data: ResponseDisplayModel containing response text

        Returns:
            Response section HTML string
        """
        n = data.test_index

        copy_btn = CopyButtonBuilder.build(
            tooltip="Copy full response",
            onclick=f"copySection('response-{n}', 'Claude Response')",
            stop_propagation=True
        )

        return f'''<details>
  <summary>
    <span class="summary-text">Claude's Full Response</span>
    {copy_btn}
  </summary>
  <div class="content">
    <div class="response-preview" id="response-{n}">
      <pre>{self.escape(data.full_text)}</pre>
    </div>
  </div>
</details>'''
