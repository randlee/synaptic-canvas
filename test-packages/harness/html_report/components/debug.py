"""
Debug information section component builder.

Builds the collapsible debug section showing pytest output, test metadata,
side effects, and trace file links.
"""

from ..models import DebugDisplayModel
from .base import BaseBuilder, CopyButtonBuilder, FileLinkBuilder


class DebugBuilder(BaseBuilder[DebugDisplayModel]):
    """Builds the debug information section HTML component.

    The debug section displays:
    - Collapsible details element
    - Pytest output
    - Test metadata table
    - Side effects summary
    - Raw trace file link
    """

    def build(self, data: DebugDisplayModel) -> str:
        """Build debug section HTML from display model.

        Args:
            data: DebugDisplayModel containing debug information

        Returns:
            Complete debug section HTML string
        """
        self.validate(data)

        n = data.test_index

        # Build copy button for entire section
        copy_btn = CopyButtonBuilder.build(
            tooltip="Copy debug info",
            onclick=f"copySection('debug-{n}', 'Debug Information')",
            stop_propagation=True
        )

        # Build pytest output section
        pytest_html = ""
        if data.pytest_output:
            pytest_html = f'''<h3>Pytest Output</h3>
    <pre>{self.escape(data.pytest_output)}</pre>'''

        # Build test metadata table
        test_repo_link = ""
        if data.test_repo:
            test_repo_link = FileLinkBuilder.build(
                data.test_repo,
                data.test_repo,
                config=self.config
            )

        table_rows = []
        if data.test_script:
            table_rows.append(f'<tr><td>Test Script</td><td><code>{self.escape(data.test_script)}</code></td></tr>')
        if data.package:
            table_rows.append(f'<tr><td>Package</td><td>{self.escape(data.package)}</td></tr>')
        if data.test_repo:
            table_rows.append(f'<tr><td>Test Repo</td><td>{test_repo_link}</td></tr>')
        if data.session_id:
            table_rows.append(f'<tr><td>Session ID</td><td>{self.escape(data.session_id)}</td></tr>')

        table_html = ""
        if table_rows:
            table_html = f'''<h3>Test Metadata</h3>
    <table class="debug-table">
      {"".join(table_rows)}
    </table>'''

        # Build side effects section
        side_effects_color = "var(--fail)" if data.has_side_effects else "var(--pass)"
        side_effects_html = f'''<h3>Side Effects</h3>
    <p style="color: {side_effects_color};">{self.escape(data.side_effects_text)}</p>'''

        # Build trace file section
        trace_html = ""
        if data.trace_file:
            trace_link = FileLinkBuilder.build(
                data.trace_file,
                data.trace_file,
                config=self.config
            )
            trace_html = f'''<h3>Raw Trace File</h3>
    <p>{trace_link}</p>'''

        return f'''<details>
  <summary>
    <span class="summary-text">Debug Information</span>
    {copy_btn}
  </summary>
  <div class="content" id="debug-{n}">
    {pytest_html}

    {table_html}

    {side_effects_html}

    {trace_html}
  </div>
</details>'''
