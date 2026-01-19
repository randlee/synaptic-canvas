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
    - Token usage (if available)
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

        # Build token display section if token data is available
        token_html = ""
        if data.has_token_data:
            token_html = f'''
  <div class="token-section">
    <div class="token-summary">
      <span>Tokens: Input {data.formatted_token_input} | Output {data.formatted_token_output} | Total {data.formatted_token_total}</span>
    </div>
    <details class="token-details">
      <summary>Token Details</summary>
      <dl class="token-detail">
        <div><dt>Input tokens</dt><dd>{data.token_input:,}</dd></div>
        <div><dt>Output tokens</dt><dd>{data.token_output:,}</dd></div>
        <div><dt>Cache creation tokens</dt><dd>{data.token_cache_creation:,}</dd></div>
        <div><dt>Cache read tokens</dt><dd>{data.token_cache_read:,}</dd></div>
        <div><dt>Subagent tokens</dt><dd>{data.token_subagent:,}</dd></div>
        <div><dt>Total billable</dt><dd>{data.token_total_billable:,}</dd></div>
        <div><dt>Total all</dt><dd>{data.token_total_all:,}</dd></div>
      </dl>
    </details>
  </div>'''

        return f'''<div class="status-banner {status_display.css_class}">
  <div class="status-badge">
    <span>{status_display.label}</span>
    <span style="font-size: 0.9rem; font-weight: normal;">{data.expectations_text}</span>
  </div>
  <div class="status-meta">
    <div class="duration">{data.formatted_duration}</div>
    <div>{data.formatted_timestamp}</div>{token_html}
  </div>
</div>'''
