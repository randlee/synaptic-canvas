"""
Agent assessment section component builder.

Builds the dark purple-themed assessment section showing AI-generated
analysis of the test results. Supports both lazy-loading (for HTTP) and
embedded content (for file:// compatibility).
"""

from ..models import AssessmentDisplayModel
from .base import BaseBuilder, CopyButtonBuilder


class AssessmentBuilder(BaseBuilder[AssessmentDisplayModel]):
    """Builds the agent assessment section HTML component.

    The assessment section displays:
    - Collapsible details element with purple gradient theme
    - AI badge indicating automated analysis
    - Metadata (model, timestamp)
    - Markdown content (either embedded or lazy-loaded)

    Supports two modes:
    - Lazy-loading: Placeholder shown, JS fetches .assessment.md file
    - Embedded: Content pre-rendered as HTML
    """

    def build(self, data: AssessmentDisplayModel) -> str:
        """Build assessment section HTML from display model.

        Args:
            data: AssessmentDisplayModel containing assessment content

        Returns:
            Complete assessment section HTML string
        """
        self.validate(data)

        n = data.test_index

        # Build copy button
        copy_btn = CopyButtonBuilder.build(
            tooltip="Copy assessment",
            onclick=f"copyAssessment('agent-assessment-{n}')",
            stop_propagation=True
        )

        # Determine visibility class
        visible_class = " visible" if data.is_embedded else ""

        # Build metadata text
        meta_html = ""
        if data.meta_text:
            meta_html = self.escape(data.meta_text)

        # Build content - either embedded HTML or loading placeholder
        if data.is_embedded and data.content_html:
            content_html = data.content_html
        else:
            content_html = '<p class="agent-assessment-loading">Loading assessment...</p>'

        # Use 'open' attribute if content is embedded
        open_attr = " open" if data.is_embedded else ""

        return f'''<details class="agent-assessment-section{visible_class}"
         id="agent-assessment-section-{n}"
         data-test-id="{self.escape(data.test_id)}"{open_attr}>
  <summary>
    <span class="summary-text">Agent Assessment</span>
    {copy_btn}
  </summary>
  <div class="content">
    <div class="agent-assessment" id="agent-assessment-{n}">
      <div class="agent-assessment-header">
        <h3>
          Agent Assessment
          <span class="ai-badge">AI Review</span>
        </h3>
        <span class="agent-assessment-meta" id="agent-assessment-meta-{n}">{meta_html}</span>
      </div>
      <div class="agent-assessment-content" id="agent-assessment-content-{n}">
        {content_html}
      </div>
    </div>
  </div>
</details>'''

    def build_with_embedded_markdown(
        self,
        data: AssessmentDisplayModel,
        markdown_content: str
    ) -> str:
        """Build assessment with pre-rendered markdown content.

        This method renders markdown to HTML and embeds it directly,
        which is necessary for file:// URLs where fetch() doesn't work.

        Args:
            data: AssessmentDisplayModel
            markdown_content: Raw markdown to render

        Returns:
            Complete assessment section with embedded content
        """
        # Convert markdown to basic HTML
        # (For full markdown rendering, consider using a library)
        html_content = self._simple_markdown_to_html(markdown_content)

        # Create new data model with embedded content
        embedded_data = AssessmentDisplayModel(
            test_index=data.test_index,
            test_id=data.test_id,
            content_html=html_content,
            model=data.model,
            timestamp=data.timestamp,
            is_embedded=True
        )

        return self.build(embedded_data)

    def _simple_markdown_to_html(self, markdown: str) -> str:
        """Simple markdown to HTML conversion.

        This is a basic implementation. For production use, consider
        using a proper markdown library.

        Args:
            markdown: Raw markdown text

        Returns:
            Basic HTML rendering
        """
        import re

        html = self.escape(markdown)

        # Code blocks
        html = re.sub(
            r'```(\w*)\n(.*?)```',
            r'<pre><code class="language-\1">\2</code></pre>',
            html,
            flags=re.DOTALL
        )

        # Inline code
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # Headers
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Bold
        html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)

        # Italic
        html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)

        # Unordered lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # Paragraphs (simple approach)
        paragraphs = html.split('\n\n')
        result = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if p.startswith('<'):
                result.append(p)
            else:
                result.append(f'<p>{p}</p>')

        return '\n'.join(result)
