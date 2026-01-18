"""
Status banner component builder.

Builds the colored status banner that appears at the top of each test case,
showing pass/fail status, expectations summary, duration, and timestamp.
"""

from ..models import StatusBannerDisplayModel
from .base import BaseBuilder


class StatusBannerBuilder(BaseBuilder[StatusBannerDisplayModel]):
    """Builds the status banner HTML component.

    The banner displays:
    - Large status label (PASS, FAIL, PARTIAL, SKIPPED)
    - Expectations passed summary (e.g., "4 of 7 expectations passed")
    - Test duration in seconds
    - Test execution timestamp
    """

    def build(self, data: StatusBannerDisplayModel) -> str:
        """Build status banner HTML from display model.

        Args:
            data: StatusBannerDisplayModel containing status info

        Returns:
            Complete status banner HTML string
        """
        self.validate(data)

        status_display = data.status_display

        return f'''<div class="status-banner {status_display.css_class}">
  <div class="status-badge">
    <span>{status_display.label}</span>
    <span style="font-size: 0.9rem; font-weight: normal;">{data.expectations_text}</span>
  </div>
  <div class="status-meta">
    <div class="duration">{data.formatted_duration}</div>
    <div>{data.formatted_timestamp}</div>
  </div>
</div>'''
