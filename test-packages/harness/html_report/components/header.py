"""
Fixture header component builder.

Builds the dark gradient header that appears at the top of the report,
containing fixture metadata, file links, and summary statistics.
"""

from ..models import HeaderDisplayModel, BuilderConfig
from .base import BaseBuilder, FileLinkBuilder


class HeaderBuilder(BaseBuilder[HeaderDisplayModel]):
    """Builds the fixture header HTML component.

    The header displays:
    - Fixture name as title
    - Package name
    - Agent/skill name with file link
    - Fixture path with file link
    - Test count and summary
    - Generation timestamp
    - Report path with file link
    """

    def build(self, data: HeaderDisplayModel) -> str:
        """Build fixture header HTML from display model.

        Args:
            data: HeaderDisplayModel containing fixture metadata

        Returns:
            Complete fixture header HTML string
        """
        self.validate(data)

        # Build agent/skill file link if path is available
        agent_skill_html = self.escape(data.agent_or_skill)
        if data.agent_or_skill_path:
            agent_skill_html = FileLinkBuilder.build(
                data.agent_or_skill_path,
                data.agent_or_skill,
                config=self.config
            )

        # Build fixture file link if path is available
        fixture_html = self.escape(data.fixture_name)
        if data.fixture_path:
            fixture_html = FileLinkBuilder.build(
                data.fixture_path,
                data.fixture_name,
                config=self.config
            )

        # Build report path file link
        report_link_html = FileLinkBuilder.build(
            data.report_path,
            data.report_path,
            config=self.config
        )

        # Format timestamp
        formatted_time = data.generated_at.strftime("%Y-%m-%d %H:%M:%S")

        return f'''<div class="fixture-header">
  <h1>{self.escape(data.fixture_name)} Test Suite</h1>
  <div class="fixture-meta">
    <div class="fixture-meta-item">
      <span class="fixture-meta-label">Package</span>
      <span class="fixture-meta-value">{self.escape(data.package)}</span>
    </div>
    <div class="fixture-meta-item">
      <span class="fixture-meta-label">Agent/Skill</span>
      <span class="fixture-meta-value">{agent_skill_html}</span>
    </div>
    <div class="fixture-meta-item">
      <span class="fixture-meta-label">Fixture</span>
      <span class="fixture-meta-value">{fixture_html}</span>
    </div>
    <div class="fixture-meta-item">
      <span class="fixture-meta-label">Total Tests</span>
      <span class="fixture-meta-value">{data.total_tests} tests ({self.escape(data.summary_text)})</span>
    </div>
    <div class="fixture-meta-item">
      <span class="fixture-meta-label">Report Generated</span>
      <span class="fixture-meta-value">{formatted_time}</span>
    </div>
    <div class="fixture-meta-item wide">
      <span class="fixture-meta-label">Report Path</span>
      <span class="fixture-meta-value" style="font-family: monospace; font-size: 0.8rem;">{report_link_html}</span>
    </div>
  </div>
</div>'''
