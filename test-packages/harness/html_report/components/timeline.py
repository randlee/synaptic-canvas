"""
Timeline section component builder.

Builds the collapsible timeline showing the chronological sequence of
prompts, tool calls, and responses during test execution.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import json
import re

from ..models import TimelineDisplayModel, TimelineItemDisplayModel, TimelineEntryType
from .base import BaseBuilder, CopyButtonBuilder


@dataclass
class SubagentGroup:
    """Represents a group of timeline items belonging to one subagent."""

    agent_id: str
    agent_type: str
    items: List[TimelineItemDisplayModel] = field(default_factory=list)

    @property
    def tool_call_count(self) -> int:
        """Count of tool calls in this subagent group."""
        return sum(
            1 for item in self.items
            if item.entry_type == TimelineEntryType.TOOL_CALL
        )

    @property
    def duration_ms(self) -> int:
        """Total duration in milliseconds (max elapsed - min elapsed)."""
        if not self.items:
            return 0
        return max(item.elapsed_ms for item in self.items) - min(item.elapsed_ms for item in self.items)

    @property
    def formatted_duration(self) -> str:
        """Format duration for display."""
        ms = self.duration_ms
        if ms < 1000:
            return f"+{ms}ms"
        return f"+{ms / 1000:.1f}s"


class TimelineBuilder(BaseBuilder[TimelineDisplayModel]):
    """Builds the timeline section HTML component.

    The timeline displays:
    - Collapsible details element with tool call count
    - Vertical line connecting timeline entries
    - Colored dots for each entry type (prompt, tool_call, response)
    - Elapsed time and sequence numbers
    - Content previews with copy buttons
    - Collapsible subagent sections grouping tool calls by agent
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

        # Build timeline items with subagent grouping
        items_html = self._build_timeline_with_subagent_groups(data.entries)

        return f'''<details>
  <summary>
    <span class="summary-text">Timeline ({data.tool_call_count} tool calls)</span>
    {copy_btn}
  </summary>
  <div class="content">
    <div class="timeline" id="{data.timeline_id}">
      {items_html}
    </div>
  </div>
</details>'''

    def _build_timeline_with_subagent_groups(
        self,
        entries: List[TimelineItemDisplayModel]
    ) -> str:
        """Build timeline HTML with subagent items wrapped in collapsible sections.

        Detects subagent boundaries from agent_id transitions and wraps
        subagent tool calls in <details class="subagent-section"> elements.

        Args:
            entries: List of timeline items to render

        Returns:
            HTML string with subagent groupings
        """
        if not entries:
            return ""

        # Calculate total items for smart collapse decision
        total_items = len(entries)

        # Group consecutive items by agent_id
        html_parts: List[str] = []
        current_group: Optional[SubagentGroup] = None
        non_agent_items: List[TimelineItemDisplayModel] = []

        for entry in entries:
            if entry.agent_id:
                # This item belongs to a subagent
                if current_group and current_group.agent_id == entry.agent_id:
                    # Continue current group
                    current_group.items.append(entry)
                else:
                    # Flush any non-agent items first
                    if non_agent_items:
                        for item in non_agent_items:
                            html_parts.append(self._build_timeline_item(item))
                        non_agent_items = []

                    # Flush previous group if different agent
                    if current_group:
                        html_parts.append(
                            self._build_subagent_section(current_group, total_items)
                        )

                    # Start new group
                    current_group = SubagentGroup(
                        agent_id=entry.agent_id,
                        agent_type=entry.agent_type or "Subagent",
                        items=[entry]
                    )
            else:
                # This item does not belong to a subagent
                # Flush current group if any
                if current_group:
                    html_parts.append(
                        self._build_subagent_section(current_group, total_items)
                    )
                    current_group = None

                non_agent_items.append(entry)

        # Flush remaining items
        if non_agent_items:
            for item in non_agent_items:
                html_parts.append(self._build_timeline_item(item))

        if current_group:
            html_parts.append(
                self._build_subagent_section(current_group, total_items)
            )

        return "".join(html_parts)

    def _build_subagent_section(
        self,
        group: SubagentGroup,
        total_timeline_items: int
    ) -> str:
        """Build a collapsible subagent section.

        Args:
            group: SubagentGroup containing items for this subagent
            total_timeline_items: Total items in timeline for smart collapse decision

        Returns:
            HTML string with <details class="subagent-section"> wrapper
        """
        # Smart collapse: expand if subagent has >66% of activity
        expand_threshold = 0.66
        should_expand = (len(group.items) / total_timeline_items) > expand_threshold if total_timeline_items > 0 else False
        open_attr = "open" if should_expand else ""

        # Build items HTML
        items_html = []
        for item in group.items:
            items_html.append(self._build_timeline_item(item))

        # Tool count text
        tool_count = group.tool_call_count
        tool_text = f"{tool_count} tool call{'s' if tool_count != 1 else ''}"

        return f'''<details class="subagent-section" data-agent-id="{self.escape(group.agent_id)}" {open_attr}>
  <summary>
    <span class="agent-badge">{self.escape(group.agent_type)}</span>
    <span class="tool-count">{tool_text}</span>
    <span class="subagent-duration">{group.formatted_duration}</span>
  </summary>
  <div class="subagent-timeline">
    {"".join(items_html)}
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

        # Build depth class for tree indentation
        depth_class = f"depth-{entry.depth}" if entry.depth else "depth-0"

        # Build data attributes for tree structure
        agent_attr = f'data-agent-id="{entry.agent_id}"' if entry.agent_id else ''
        uuid_attr = f'data-uuid="{entry.uuid}"' if entry.uuid else ''
        parent_uuid_attr = f'data-parent-uuid="{entry.parent_uuid}"' if entry.parent_uuid else ''

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

        # Build meta line with pid, tool_use_id, and agent info
        meta_parts = []
        if entry.pid:
            meta_parts.append(f"pid:{entry.pid}")
        if entry.tool_use_id:
            # Truncate tool_use_id to first 8 chars for readability
            truncated_id = entry.tool_use_id[:8] if len(entry.tool_use_id) > 8 else entry.tool_use_id
            meta_parts.append(f"id:{truncated_id}")
        if entry.agent_type:
            agent_text = f"{entry.agent_type}"
            if entry.agent_id:
                agent_text += f" ({entry.agent_id})"
            meta_parts.append(f"agent:{agent_text}")
        meta_html = ""
        if meta_parts:
            meta_html = f'<div class="timeline-meta">{" | ".join(meta_parts)}</div>'

        return f'''<div class="timeline-item {type_display.css_class} {depth_class}"
        data-seq="{entry.seq}"
        data-elapsed="{entry.elapsed_ms}ms"
        {agent_attr}
        {uuid_attr}
        {parent_uuid_attr}>
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
            command = self._format_command(entry.command or "")
            output = self._format_output(entry.output or "")
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

    def _format_command(self, command: str) -> str:
        """Pretty-print embedded JSON passed via --json in a command string."""
        if not command:
            return command
        pattern = re.compile(r"--json\\s+(?P<quote>['\"])(?P<payload>.*?)(?P=quote)")
        match = pattern.search(command)
        if not match:
            return command
        payload = match.group("payload")
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return command
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        replacement = f"--json {pretty}"
        return command[: match.start()] + replacement + command[match.end() :]

    def _format_output(self, output: str) -> str:
        """Pretty-print JSONL output when detected."""
        if not output:
            return output
        lines = []
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    lines.append(line)
                else:
                    lines.append(json.dumps(parsed, indent=2, ensure_ascii=False))
            else:
                lines.append(line)
        return "\n".join(lines)
