"""
Expectations section component builder.

Builds the list of test expectations with pass/fail icons, descriptions,
expandable details, and copy buttons.
"""

from ..models import ExpectationsDisplayModel, ExpectationDisplayModel
from .base import BaseBuilder, CopyButtonBuilder


class ExpectationsBuilder(BaseBuilder[ExpectationsDisplayModel]):
    """Builds the expectations section HTML component.

    The expectations section displays:
    - Section header with pass/fail counts
    - List of expectations with status icons
    - Expandable details showing expected vs actual values
    - Copy buttons for each expectation
    """

    def build(self, data: ExpectationsDisplayModel) -> str:
        """Build expectations section HTML from display model.

        Args:
            data: ExpectationsDisplayModel containing expectations list

        Returns:
            Complete expectations section HTML string
        """
        self.validate(data)

        # Build section header with counts
        copy_btn = CopyButtonBuilder.build(
            tooltip="Copy expectations summary",
            onclick=f"copySection('expectations-{data.test_index}', 'Expectations')"
        )

        header = f'''<div class="section-header">
  <h2>Expectations <span class="pass-count">({data.passed_count} passed)</span> <span class="fail-count">({data.failed_count} failed)</span></h2>
  {copy_btn}
</div>'''

        # Build expectation items
        items_html = []
        for exp in data.expectations:
            items_html.append(self._build_expectation_item(exp))

        return f'''{header}

<ul class="expectations-list" id="expectations-{data.test_index}">
  {"".join(items_html)}
</ul>'''

    def _build_expectation_item(self, exp: ExpectationDisplayModel) -> str:
        """Build a single expectation item HTML.

        Args:
            exp: ExpectationDisplayModel for single expectation

        Returns:
            Expectation list item HTML string
        """
        status_display = exp.status_display

        # Build copy button
        copy_btn = CopyButtonBuilder.build(
            tooltip="Copy expectation",
            onclick=f"copyExpectation('{exp.exp_id}')"
        )

        # Build toggle button
        toggle_class = "has-content" if exp.has_details else "no-content"
        toggle_onclick = f"toggleExpectation('{exp.exp_id}')" if exp.has_details else ""
        toggle_btn = f'''<button class="expectation-toggle {toggle_class}" onclick="{toggle_onclick}">Details</button>'''

        # Build expanded details section
        expanded_html = ""
        if exp.has_details and (exp.expected_content or exp.actual_content):
            expected_pre = f"<pre>{self.escape(exp.expected_content or '')}</pre>"
            actual_pre = f"<pre>{self.escape(exp.actual_content or '')}</pre>"

            expanded_html = f'''
      <div class="expectation-expanded" id="{exp.exp_id}">
        <div class="expected-actual">
          <div>
            <h4>Expected</h4>
            {expected_pre}
          </div>
          <div>
            <h4>Actual</h4>
            {actual_pre}
          </div>
        </div>
      </div>'''
        elif exp.has_details:
            # Has details but no expected/actual content - just an empty expanded section
            expanded_html = f'''
      <div class="expectation-expanded" id="{exp.exp_id}">
      </div>'''

        return f'''<li class="expectation-item" data-exp-id="{exp.exp_id}">
    <span class="expectation-icon">{status_display.expectation_icon_html}</span>
    <div class="expectation-content">
      <div class="expectation-label">{self.escape(exp.description)}</div>
      <div class="expectation-details">{self.escape(exp.details_text)}</div>{expanded_html}
    </div>
    <div class="expectation-actions">
      {copy_btn}
      {toggle_btn}
    </div>
  </li>'''
