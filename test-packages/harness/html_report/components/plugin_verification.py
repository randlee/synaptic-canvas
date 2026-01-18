"""
Plugin verification section component builder.

Builds the section showing plugin installation status including
expected vs installed plugins and CLI output for debugging.
"""

from ..models import PluginVerificationDisplayModel
from .base import BaseBuilder, CopyButtonBuilder


class PluginVerificationBuilder(BaseBuilder[PluginVerificationDisplayModel]):
    """Builds the plugin verification section HTML component.

    The plugin verification section displays:
    - Expected plugins from fixture setup
    - Installation status for each plugin
    - Collapsible CLI output for debugging
    """

    def build(self, data: PluginVerificationDisplayModel) -> str:
        """Build plugin verification section HTML from display model.

        Args:
            data: PluginVerificationDisplayModel containing plugin data

        Returns:
            Complete plugin verification section HTML string
        """
        self.validate(data)

        # If no plugins are expected, return a minimal section
        if not data.has_plugins:
            return ""

        n = data.test_index

        # Build copy button for entire section
        copy_btn = CopyButtonBuilder.build(
            tooltip="Copy plugin info",
            onclick=f"copySection('plugin-verification-{n}', 'Plugin Verification')",
            stop_propagation=True
        )

        # Determine overall status styling
        status_class = "pass" if data.all_successful else "fail"
        status_icon = "&#9989;" if data.all_successful else "&#10060;"

        # Build plugin list
        plugin_items_html = []
        for result in data.install_results:
            # Build collapsible output section if there's stdout or stderr
            output_html = ""
            if result.stdout or result.stderr:
                output_parts = []
                if result.stdout:
                    output_parts.append(f"<strong>STDOUT:</strong>\n{self.escape(result.stdout)}")
                if result.stderr:
                    output_parts.append(f"<strong>STDERR:</strong>\n{self.escape(result.stderr)}")
                output_content = "\n\n".join(output_parts)

                output_html = f'''
      <details class="plugin-output">
        <summary>CLI Output (return code: {result.return_code})</summary>
        <pre>{output_content}</pre>
      </details>'''

            plugin_items_html.append(f'''<div class="plugin-item {result.status_class}">
      <span class="plugin-status">{result.status_icon}</span>
      <span class="plugin-name">{self.escape(result.plugin_name)}</span>
      <span class="plugin-result">{"Installed" if result.success else "Failed"}</span>
      {output_html}
    </div>''')

        plugins_list_html = "\n".join(plugin_items_html)

        # Build expected plugins list for reference
        expected_html = ", ".join(f"<code>{self.escape(p)}</code>" for p in data.expected_plugins)

        return f'''<details class="plugin-verification-section" open>
  <summary>
    <span class="summary-text">Plugin Verification</span>
    <span class="plugin-summary {status_class}">{status_icon} {data.summary_text}</span>
    {copy_btn}
  </summary>
  <div class="content" id="plugin-verification-{n}">
    <div class="plugin-expected">
      <strong>Expected Plugins:</strong> {expected_html}
    </div>
    <div class="plugin-results">
      <strong>Installation Results:</strong>
      <div class="plugin-list">
        {plugins_list_html}
      </div>
    </div>
  </div>
</details>'''
