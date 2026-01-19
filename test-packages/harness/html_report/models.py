"""
Pydantic display models for HTML report generation.

These models extend or transform the core harness models for display purposes,
providing computed properties for HTML rendering like CSS classes, icons, and
formatted strings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, Field, computed_field

from ..models import TestStatus, TimelineEntryType


class BuilderConfig(BaseModel):
    """Configuration options for HTML builders."""

    # Editor preferences
    default_editor: str = Field(
        default="vscode",
        description="Default editor for file links (vscode, pycharm, or auto)"
    )
    pycharm_extensions: list[str] = Field(
        default_factory=lambda: [".py"],
        description="File extensions that should open in PyCharm"
    )

    # Copy button behavior
    include_source_attribution: bool = Field(
        default=True,
        description="Include source path in copied content"
    )
    source_attribution_format: str = Field(
        default="---\nsource: {path}#{fragment}",
        description="Format for source attribution"
    )

    # Collapsible sections
    default_collapsed: bool = Field(
        default=True,
        description="Whether collapsible sections start collapsed"
    )

    # Timeline
    show_elapsed_time: bool = Field(
        default=True,
        description="Show elapsed time in timeline"
    )
    show_sequence_numbers: bool = Field(
        default=True,
        description="Show sequence numbers in timeline"
    )

    # Assessment
    enable_lazy_loading: bool = Field(
        default=True,
        description="Enable lazy-loading for agent assessments"
    )
    assessment_file_pattern: str = Field(
        default="{test_id}.assessment.md",
        description="Pattern for assessment file names"
    )


class StatusDisplay(BaseModel):
    """Display attributes for status rendering."""

    status: TestStatus

    @computed_field
    @property
    def css_class(self) -> str:
        """CSS class for the status."""
        return self.status.value

    @computed_field
    @property
    def icon_html(self) -> str:
        """HTML entity for tab icons."""
        icons = {
            TestStatus.PASS: "&#10003;",      # Checkmark
            TestStatus.FAIL: "&#10060;",      # X
            TestStatus.PARTIAL: "&#9888;",    # Warning triangle
            TestStatus.SKIPPED: "&#9675;",    # Circle
        }
        return icons.get(self.status, "&#63;")

    @computed_field
    @property
    def expectation_icon_html(self) -> str:
        """HTML entity for expectation list icons."""
        icons = {
            TestStatus.PASS: "&#9989;",       # Green checkmark emoji
            TestStatus.FAIL: "&#10060;",      # X
            TestStatus.PARTIAL: "&#9888;",    # Warning triangle
            TestStatus.SKIPPED: "&#9675;",    # Circle
        }
        return icons.get(self.status, "&#63;")

    @computed_field
    @property
    def label(self) -> str:
        """Uppercase label for the status."""
        return self.status.value.upper()


class TimelineTypeDisplay(BaseModel):
    """Display attributes for timeline entry types."""

    entry_type: TimelineEntryType
    tool_name: str | None = None
    agent_type: str | None = None

    @computed_field
    @property
    def css_class(self) -> str:
        """CSS class for the timeline type."""
        type_classes = {
            TimelineEntryType.PROMPT: "prompt",
            TimelineEntryType.TOOL_CALL: "tool_call",
            TimelineEntryType.RESPONSE: "response",
            TimelineEntryType.SUBAGENT_START: "subagent",
            TimelineEntryType.SUBAGENT_STOP: "subagent",
        }
        return type_classes.get(self.entry_type, "unknown")

    @computed_field
    @property
    def display_label(self) -> str:
        """Label to display for this timeline type."""
        if self.entry_type == TimelineEntryType.TOOL_CALL and self.tool_name:
            if self.agent_type:
                return f"{self.tool_name} ({self.agent_type})"
            return self.tool_name

        labels = {
            TimelineEntryType.PROMPT: "Prompt",
            TimelineEntryType.TOOL_CALL: "Tool Call",
            TimelineEntryType.RESPONSE: "Response",
            TimelineEntryType.SUBAGENT_START: "Subagent Start",
            TimelineEntryType.SUBAGENT_STOP: "Subagent Stop",
        }
        return labels.get(self.entry_type, str(self.entry_type))


class FileLinkDisplay(BaseModel):
    """Display model for file links with editor URLs."""

    file_path: str
    display_text: str | None = None
    line_number: int | None = None
    config: BuilderConfig = Field(default_factory=BuilderConfig)

    @computed_field
    @property
    def editor_type(self) -> str:
        """Determine editor type based on file extension."""
        if any(self.file_path.endswith(ext) for ext in self.config.pycharm_extensions):
            return "pycharm"
        return self.config.default_editor if self.config.default_editor != "auto" else "vscode"

    @computed_field
    @property
    def editor_name(self) -> str:
        """Human-readable editor name."""
        return "PyCharm" if self.editor_type == "pycharm" else "VS Code"

    @computed_field
    @property
    def editor_url(self) -> str:
        """URL to open the file in the editor."""
        if self.editor_type == "pycharm":
            url = f"pycharm://open?file={quote(self.file_path)}"
            if self.line_number:
                url += f"&line={self.line_number}"
            return url
        else:
            url = f"vscode://file/{self.file_path}"
            if self.line_number:
                url += f":{self.line_number}"
            return url

    @computed_field
    @property
    def label(self) -> str:
        """Text to display for the link."""
        return self.display_text or self.file_path


class HeaderDisplayModel(BaseModel):
    """Display model for fixture header component."""

    fixture_name: str
    package: str
    agent_or_skill: str
    agent_or_skill_path: str | None = None
    fixture_path: str | None = None
    total_tests: int
    summary_text: str
    generated_at: datetime
    report_path: str


class StatusBannerDisplayModel(BaseModel):
    """Display model for status banner component."""

    status: TestStatus
    passed_count: int
    total_count: int
    duration_seconds: float
    timestamp: datetime

    # Token usage fields (populated from timeline_tree.stats.token_usage if available)
    token_input: int = 0
    token_output: int = 0
    token_cache_creation: int = 0
    token_cache_read: int = 0
    token_subagent: int = 0
    token_total_billable: int = 0
    token_total_all: int = 0

    @computed_field
    @property
    def status_display(self) -> StatusDisplay:
        """Get status display attributes."""
        return StatusDisplay(status=self.status)

    @computed_field
    @property
    def expectations_text(self) -> str:
        """Text describing expectations passed."""
        return f"{self.passed_count} of {self.total_count} expectations passed"

    @computed_field
    @property
    def formatted_duration(self) -> str:
        """Duration formatted as seconds."""
        return f"{self.duration_seconds:.2f}s"

    @computed_field
    @property
    def formatted_timestamp(self) -> str:
        """Timestamp formatted for display."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @computed_field
    @property
    def has_token_data(self) -> bool:
        """Whether token data is available."""
        return self.token_total_all > 0

    @computed_field
    @property
    def formatted_token_input(self) -> str:
        """Input tokens formatted with commas."""
        return f"{self.token_input:,}"

    @computed_field
    @property
    def formatted_token_output(self) -> str:
        """Output tokens formatted with commas."""
        return f"{self.token_output:,}"

    @computed_field
    @property
    def formatted_token_total(self) -> str:
        """Total tokens formatted with commas."""
        return f"{self.token_total_all:,}"


class TestMetadataDisplayModel(BaseModel):
    """Display model for test metadata component."""

    test_id: str
    test_name: str
    fixture: str
    package: str
    model: str
    session_id: str | None = None


class ReproduceDisplayModel(BaseModel):
    """Display model for reproduce section component."""

    test_index: int
    setup_commands: list[str]
    test_command: str
    cleanup_command: str | None = None


class ExpectationDisplayModel(BaseModel):
    """Display model for a single expectation."""

    exp_id: str
    description: str
    status: TestStatus
    details_text: str
    has_details: bool = False
    expected_content: str | None = None
    actual_content: str | None = None

    @computed_field
    @property
    def status_display(self) -> StatusDisplay:
        """Get status display attributes."""
        return StatusDisplay(status=self.status)


class ExpectationsDisplayModel(BaseModel):
    """Display model for expectations section component."""

    test_index: int
    expectations: list[ExpectationDisplayModel]

    @computed_field
    @property
    def passed_count(self) -> int:
        """Count of passed expectations."""
        return sum(1 for e in self.expectations if e.status == TestStatus.PASS)

    @computed_field
    @property
    def failed_count(self) -> int:
        """Count of failed expectations."""
        return sum(1 for e in self.expectations if e.status != TestStatus.PASS)


class TimelineItemDisplayModel(BaseModel):
    """Display model for a single timeline item."""

    seq: int
    entry_type: TimelineEntryType
    tool_name: str | None = None
    agent_id: str | None = None
    agent_type: str | None = None
    elapsed_ms: int
    content: str | None = None
    intent: str | None = None
    command: str | None = None
    output: str | None = None
    pid: int | None = None
    tool_use_id: str | None = None
    # Tree structure fields
    depth: int = 0
    uuid: str | None = None
    parent_uuid: str | None = None

    @computed_field
    @property
    def type_display(self) -> TimelineTypeDisplay:
        """Get timeline type display attributes."""
        return TimelineTypeDisplay(
            entry_type=self.entry_type,
            tool_name=self.tool_name,
            agent_type=self.agent_type
        )

    @computed_field
    @property
    def formatted_elapsed(self) -> str:
        """Format elapsed time for display."""
        if self.elapsed_ms < 1000:
            return f"+{self.elapsed_ms}ms"
        return f"+{self.elapsed_ms / 1000:.2f}s"


class TimelineDisplayModel(BaseModel):
    """Display model for timeline section component."""

    timeline_id: str
    entries: list[TimelineItemDisplayModel]
    tool_call_count: int

    @classmethod
    def from_timeline_entries(cls, timeline_id: str, entries: list[Any]) -> "TimelineDisplayModel":
        """Create from raw TimelineEntry list."""
        display_entries = []
        tool_call_count = 0

        for entry in entries:
            item = TimelineItemDisplayModel(
                seq=entry.seq,
                entry_type=entry.type,
                tool_name=entry.tool,
                agent_id=entry.agent_id,
                agent_type=entry.agent_type,
                elapsed_ms=entry.elapsed_ms,
                content=entry.content or entry.content_preview,
                intent=entry.intent,
                command=entry.input.command if entry.input else None,
                output=(entry.output.stdout or entry.output.content) if entry.output else None,
                pid=entry.pid,
            )
            display_entries.append(item)

            if entry.type == TimelineEntryType.TOOL_CALL:
                tool_call_count += 1

        return cls(
            timeline_id=timeline_id,
            entries=display_entries,
            tool_call_count=tool_call_count
        )


class ResponseDisplayModel(BaseModel):
    """Display model for Claude response section component."""

    test_index: int
    full_text: str


class PluginInstallResultDisplayModel(BaseModel):
    """Display model for a single plugin installation result."""

    plugin_name: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0

    @computed_field
    @property
    def status_class(self) -> str:
        """CSS class for the status indicator."""
        return "pass" if self.success else "fail"

    @computed_field
    @property
    def status_icon(self) -> str:
        """HTML entity for status icon."""
        return "&#9989;" if self.success else "&#10060;"  # Green check or red X


class PluginVerificationDisplayModel(BaseModel):
    """Display model for plugin verification section component."""

    test_index: int
    expected_plugins: list[str] = []
    install_results: list[PluginInstallResultDisplayModel] = []
    has_plugins: bool = False

    @computed_field
    @property
    def all_successful(self) -> bool:
        """Check if all plugin installations succeeded."""
        if not self.expected_plugins:
            return True
        return all(r.success for r in self.install_results)

    @computed_field
    @property
    def summary_text(self) -> str:
        """Summary text for the section header."""
        if not self.expected_plugins:
            return "No plugins required"
        successful = sum(1 for r in self.install_results if r.success)
        total = len(self.expected_plugins)
        return f"{successful}/{total} plugins installed"


class DebugDisplayModel(BaseModel):
    """Display model for debug information section component."""

    test_index: int
    pytest_output: str | None = None
    test_script: str | None = None
    package: str | None = None
    test_repo: str | None = None
    session_id: str | None = None
    trace_file: str | None = None
    side_effects_text: str = "No files were created, modified, or deleted."
    has_side_effects: bool = False


class AssessmentDisplayModel(BaseModel):
    """Display model for agent assessment section component."""

    test_index: int
    test_id: str
    content_html: str | None = None
    model: str | None = None
    timestamp: str | None = None
    is_embedded: bool = False

    @computed_field
    @property
    def meta_text(self) -> str | None:
        """Formatted metadata text."""
        if self.model and self.timestamp:
            return f"Generated by {self.model} | {self.timestamp}"
        elif self.model:
            return f"Generated by {self.model}"
        elif self.timestamp:
            return self.timestamp
        return None


class TabDisplayModel(BaseModel):
    """Display model for a single tab."""

    tab_id: str
    tab_label: str
    status: TestStatus
    is_active: bool = False

    @computed_field
    @property
    def status_display(self) -> StatusDisplay:
        """Get status display attributes."""
        return StatusDisplay(status=self.status)


class TestCaseDisplayModel(BaseModel):
    """Display model for a complete test case tab content."""

    test_index: int
    test_id: str
    test_name: str
    description: str
    status_banner: StatusBannerDisplayModel
    metadata: TestMetadataDisplayModel
    reproduce: ReproduceDisplayModel
    plugin_verification: PluginVerificationDisplayModel | None = None
    expectations: ExpectationsDisplayModel
    timeline: TimelineDisplayModel
    response: ResponseDisplayModel
    debug: DebugDisplayModel
    assessment: AssessmentDisplayModel | None = None
