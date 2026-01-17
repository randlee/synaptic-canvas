"""
Reproduce section component builder.

Builds the dark-themed section showing commands to reproduce the test,
including setup, test execution, and cleanup steps.
"""

from ..models import ReproduceDisplayModel
from .base import BaseBuilder, CopyButtonBuilder


class ReproduceBuilder(BaseBuilder[ReproduceDisplayModel]):
    """Builds the reproduce section HTML component.

    The reproduce section displays:
    - Dark themed container
    - Setup commands with copy button
    - Test command with copy button
    - Optional cleanup commands
    """

    def build(self, data: ReproduceDisplayModel) -> str:
        """Build reproduce section HTML from display model.

        Args:
            data: ReproduceDisplayModel containing reproduction steps

        Returns:
            Complete reproduce section HTML string
        """
        self.validate(data)

        n = data.test_index

        # Build section header copy button
        section_copy_btn = CopyButtonBuilder.build(
            tooltip="Copy all reproduction steps",
            onclick=f"copySection('reproduce-{n}', 'Reproduce This Test')"
        )

        # Build setup step
        setup_copy_btn = CopyButtonBuilder.build(
            tooltip="Copy setup commands",
            onclick=f"copyElement('setup-commands-{n}')"
        )
        setup_commands = "\n".join(data.setup_commands) if data.setup_commands else "# No setup required"
        setup_html = f'''<div class="reproduce-step">
      <div class="reproduce-step-header">
        <span class="reproduce-step-label">1. Setup</span>
        {setup_copy_btn}
      </div>
      <pre id="setup-commands-{n}">{self.escape(setup_commands)}</pre>
    </div>'''

        # Build test command step
        test_copy_btn = CopyButtonBuilder.build(
            tooltip="Copy test command",
            onclick=f"copyElement('test-command-{n}')"
        )
        test_html = f'''<div class="reproduce-step">
      <div class="reproduce-step-header">
        <span class="reproduce-step-label">2. Run Test</span>
        {test_copy_btn}
      </div>
      <pre id="test-command-{n}">{self.escape(data.test_command)}</pre>
    </div>'''

        # Build cleanup step (optional)
        cleanup_html = ""
        if data.cleanup_command:
            cleanup_html = f'''<div class="reproduce-step">
      <div class="reproduce-step-header">
        <span class="reproduce-step-label">3. Cleanup (optional)</span>
      </div>
      <pre>{self.escape(data.cleanup_command)}</pre>
    </div>'''

        return f'''<div class="reproduce-section">
  <div class="section-header">
    <h2>Reproduce This Test</h2>
    {section_copy_btn}
  </div>
  <p style="color: #94a3b8; margin-bottom: 16px;">Copy and run these commands to reproduce this test exactly:</p>

  <div id="reproduce-{n}">
    {setup_html}

    {test_html}

    {cleanup_html}
  </div>
</div>'''
