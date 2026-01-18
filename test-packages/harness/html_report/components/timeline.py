"""
Timeline section component builder.

Builds the collapsible timeline showing the chronological sequence of
prompts, tool calls, and responses during test execution.
"""

from ..models import TimelineDisplayModel, TimelineItemDisplayModel, TimelineEntryType
from .base import BaseBuilder, CopyButtonBuilder


class TimelineBuilder(BaseBuilder[TimelineDisplayModel]):
    """Builds the timeline section HTML component.

    The timeline displays:
    - Collapsible details element with tool call count
    - Vertical line connecting timeline entries
    - Colored dots for each entry type (prompt, tool_call, response)
    - Elapsed time and sequence numbers
    - Content previews with copy buttons
    """

    def build(self, data: TimelineDisplayModel) -> str:
        """Build timeline section HTML from display model.

        Args:
            data: TimelineDisplayModel containing timeline entries

        Returns:
            Complete timeline section HTML string
        """
        self.validate(data)

        # Build copy button for entire timeline
        copy_btn = CopyButtonBuilder.build(
            tooltip="Copy entire timeline",
            onclick=f"copyTimeline('{data.timeline_id}')",
            stop_propagation=True
        )

        # Build timeline items
        items_html = []
        for entry in data.entries:
            items_html.append(self._build_timeline_item(entry))

        return f'''<details>
  <summary>
    <span class="summary-text">Timeline ({data.tool_call_count} tool calls)</span>
    {copy_btn}
  </summary>
  <div class="content">
    <div class="timeline" id="{data.timeline_id}">
      {"".join(items_html)}
    </div>
  </div>
</details>'''

    def _build_timeline_item(self, entry: TimelineItemDisplayModel) -> str:
        """Build a single timeline item HTML.

        Args:
            entry: TimelineItemDisplayModel for single entry

        Returns:
            Timeline item HTML string
        """
        type_display = entry.type_display

        # Build copy button
        copy_btn = CopyButtonBuilder.build(
            tooltip="Copy this step",
            onclick="copyTimelineItem(this)"
        )

        # Build content section
        content_html = self._build_content(entry)

        # Build intent line if present
        intent_html = ""
        if entry.intent:
            intent_html = f'<div class="timeline-intent">{self.escape(entry.intent)}</div>'

        # Build meta line with pid and agent info
        meta_parts = []
        if entry.pid:
            meta_parts.append(f"pid:{entry.pid}")
        if entry.agent_type:
            agent_text = f"{entry.agent_type}"
            if entry.agent_id:
                agent_text += f" ({entry.agent_id})"
            meta_parts.append(f"agent:{agent_text}")
        meta_html = ""
        if meta_parts:
            meta_html = f'<div class="timeline-meta">{" | ".join(meta_parts)}</div>'

        return f'''<div class="timeline-item {type_display.css_class}" data-seq="{entry.seq}" data-elapsed="{entry.elapsed_ms}ms">
        <div class="timeline-dot"></div>
        <div class="timeline-header">
          <span class="timeline-type">{self.escape(type_display.display_label)}</span>
          <div class="timeline-right">
            <span class="timeline-elapsed">{entry.formatted_elapsed}</span>
            <span class="timeline-seq">#{entry.seq}</span>
            {copy_btn}
          </div>
        </div>
        <div class="timeline-content">
          {meta_html}
          {intent_html}
          {content_html}
        </div>
      </div>'''

    def _build_content(self, entry: TimelineItemDisplayModel) -> str:
        """Build the content section for a timeline entry.

        Args:
            entry: TimelineItemDisplayModel

        Returns:
            Content HTML string (pre tag with content)
        """
        if entry.entry_type == TimelineEntryType.PROMPT:
            return f'<pre>{self.escape(entry.content or "")}</pre>'

        if entry.entry_type == TimelineEntryType.TOOL_CALL:
            # Show command and output for tool calls
            command = entry.command or ""
            output = entry.output or ""
            if command and output:
                return f'<pre>$ {self.escape(command)}\n\n{self.escape(output)}</pre>'
            elif command:
                return f'<pre>$ {self.escape(command)}</pre>'
            elif output:
                return f'<pre>{self.escape(output)}</pre>'
            return ''

        if entry.entry_type == TimelineEntryType.RESPONSE:
            return f'<pre>{self.escape(entry.content or "")}</pre>'

        # For other types, show content if available
        if entry.content:
            return f'<pre>{self.escape(entry.content)}</pre>'

        return ''
