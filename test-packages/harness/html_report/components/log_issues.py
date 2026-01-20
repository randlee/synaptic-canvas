"""
Log issues section component builder.

Builds the section showing log warnings and errors captured during test execution.
This section is always shown (even on pass) for visibility into potential issues.
"""

from ..models import LogIssuesDisplayModel
from .base import BaseBuilder, CopyButtonBuilder


class LogIssuesBuilder(BaseBuilder[LogIssuesDisplayModel]):
    """Builds the log issues section HTML component.

    The log issues section displays:
    - Warning and error entries from test execution logs
    - Count badges for warnings and errors
    - Collapsible details for each log entry
    - Visual indicators (yellow for warnings, red for errors)

    This section is displayed even when tests pass, to ensure visibility
    into warnings that may indicate future problems.
    """

    def build(self, data: LogIssuesDisplayModel) -> str:
        """Build log issues section HTML from display model.

        Args:
            data: LogIssuesDisplayModel containing log issues

        Returns:
            Complete log issues section HTML string
        """
        self.validate(data)

        n = data.test_index

        # If no issues and warnings aren't allowed, show clean status
        if not data.has_issues:
            return self._build_clean_section(data)

        # Build copy button for entire section
        copy_btn = CopyButtonBuilder.build(
            tooltip="Copy log issues",
            onclick=f"copySection('log-issues-{n}', 'Log Issues')",
            stop_propagation=True
        )

        # Build issues list
        issues_html = []
        for i, issue in enumerate(data.issues):
            source_badge = ""
            if issue.source:
                source_badge = f'<span class="log-source-badge">{self.escape(issue.source)}</span>'

            line_info = ""
            if issue.line_number:
                line_info = f'<span class="log-line-number">Line {issue.line_number}</span>'

            timestamp_info = ""
            if issue.timestamp:
                timestamp_info = f'<span class="log-timestamp">{self.escape(issue.timestamp)}</span>'

            issues_html.append(f'''<div class="log-issue-item {issue.level_class}">
      <span class="log-issue-icon">{issue.level_icon}</span>
      <span class="log-issue-level">{issue.level.upper()}</span>
      {source_badge}
      <span class="log-issue-message">{self.escape(issue.message)}</span>
      <div class="log-issue-meta">
        {line_info}
        {timestamp_info}
      </div>
    </div>''')

        issues_list_html = "\n".join(issues_html)

        # Determine section state (open if there are issues)
        open_attr = "open" if data.has_issues else ""

        # Build summary badge with counts
        badge_parts = []
        if data.error_count > 0:
            badge_parts.append(f'<span class="log-count-badge log-error-badge">{data.error_count} error{"s" if data.error_count != 1 else ""}</span>')
        if data.warning_count > 0:
            badge_parts.append(f'<span class="log-count-badge log-warning-badge">{data.warning_count} warning{"s" if data.warning_count != 1 else ""}</span>')
        badges_html = " ".join(badge_parts)

        # Show override notice if warnings are allowed
        override_notice = ""
        if data.allow_warnings:
            override_notice = '''
    <div class="log-override-notice">
      <span class="log-override-icon">&#9888;</span>
      <span>Warning override enabled (<code>allow_warnings: true</code>) - these issues did not cause test failure</span>
    </div>'''

        raw_context_html = ""
        if data.raw_context:
            raw_context_html = self._build_raw_context(data.raw_context)

        return f'''<details class="log-issues-section {data.severity_class}" {open_attr}>
  <summary>
    <span class="summary-text">Log Warnings &amp; Errors</span>
    <span class="log-badges">{badges_html}</span>
    {copy_btn}
  </summary>
  <div class="content" id="log-issues-{n}">{override_notice}
    <div class="log-issues-list">
      {issues_list_html}
    </div>
    {raw_context_html}
  </div>
</details>'''

    def _build_clean_section(self, data: LogIssuesDisplayModel) -> str:
        """Build a minimal section showing no issues found.

        Args:
            data: LogIssuesDisplayModel with raw context, if present

        Returns:
            Clean log section HTML string
        """
        raw_context_html = ""
        if data.raw_context:
            raw_context_html = self._build_raw_context(data.raw_context)

        return f'''<details class="log-issues-section log-severity-clean">
  <summary>
    <span class="summary-text">Log Warnings &amp; Errors</span>
    <span class="log-count-badge log-clean-badge">No issues</span>
  </summary>
  <div class="content" id="log-issues-{data.test_index}">
    <p class="log-clean-message">No warnings or errors were captured during test execution.</p>
    {raw_context_html}
  </div>
</details>'''

    def _build_raw_context(self, raw_context: str) -> str:
        lines = []
        for line in raw_context.splitlines():
            escaped = self.escape(line)
            if "ERROR" in line or "CRITICAL" in line:
                lines.append(f'<span class="log-line log-line-error">{escaped}</span>')
            elif "WARNING" in line:
                lines.append(f'<span class="log-line log-line-warning">{escaped}</span>')
            else:
                lines.append(f'<span class="log-line">{escaped}</span>')

        rendered = "\n".join(lines)
        return f'''
    <details class="log-raw-context" open>
      <summary>
        <span class="summary-text">Raw Log Context</span>
      </summary>
      <div class="content">
        <pre>{rendered}</pre>
      </div>
    </details>'''
