"""Tests for html_report.components module.

These tests verify the HTML component builders generate correct output.
"""

import pytest
from datetime import datetime

from harness.models import TestStatus, TimelineEntryType
from harness.html_report.models import (
    BuilderConfig,
    HeaderDisplayModel,
    StatusBannerDisplayModel,
    ExpectationDisplayModel,
    ExpectationsDisplayModel,
    TimelineItemDisplayModel,
    TimelineDisplayModel,
    ReproduceDisplayModel,
    DebugDisplayModel,
    AssessmentDisplayModel,
    TabDisplayModel,
    PluginVerificationDisplayModel,
    PluginInstallResultDisplayModel,
)
from harness.html_report.components import (
    BaseBuilder,
    CopyButtonBuilder,
    HeaderBuilder,
    TabsBuilder,
    StatusBannerBuilder,
    ExpectationsBuilder,
    TimelineBuilder,
    ReproduceBuilder,
    DebugBuilder,
    AssessmentBuilder,
    PluginVerificationBuilder,
)
from harness.html_report.components.base import FileLinkBuilder


class TestCopyButtonBuilder:
    """Tests for CopyButtonBuilder utility."""

    def test_basic_copy_button(self):
        """Test basic copy button generation."""
        html = CopyButtonBuilder.build(
            tooltip="Copy content",
            onclick="copyElement('test')"
        )
        assert 'class="copy-icon-btn"' in html
        assert 'data-tooltip="Copy content"' in html
        assert "copyElement('test')" in html
        assert "clipboard" in html  # SVG class
        assert "checkmark" in html  # SVG class

    def test_copy_button_with_stop_propagation(self):
        """Test copy button with event.stopPropagation()."""
        html = CopyButtonBuilder.build(
            tooltip="Copy",
            onclick="copyElement('test')",
            stop_propagation=True
        )
        assert "event.stopPropagation();" in html


class TestFileLinkBuilder:
    """Tests for FileLinkBuilder utility."""

    def test_vscode_link(self):
        """Test VS Code file link generation."""
        html = FileLinkBuilder.build("/path/to/file.js")
        assert 'href="vscode://file//path/to/file.js"' in html
        assert 'class="file-link vscode"' in html
        assert 'title="Open in VS Code"' in html

    def test_pycharm_link(self):
        """Test PyCharm file link generation."""
        html = FileLinkBuilder.build("/path/to/file.py")
        assert 'href="pycharm://open?file=' in html
        assert 'class="file-link pycharm"' in html
        assert 'title="Open in PyCharm"' in html

    def test_link_with_line_number(self):
        """Test file link with line number."""
        html = FileLinkBuilder.build("/path/to/file.py", line_number=42)
        assert "&line=42" in html

    def test_html_escaping(self):
        """Test that file names are HTML escaped."""
        html = FileLinkBuilder.build("/path/to/<file>.py", display_text="<file>.py")
        assert "&lt;file&gt;.py" in html


class TestHeaderBuilder:
    """Tests for HeaderBuilder component."""

    def test_header_structure(self):
        """Test header HTML structure."""
        builder = HeaderBuilder()
        data = HeaderDisplayModel(
            fixture_name="Test Fixture",
            package="sc-startup",
            agent_or_skill="startup",
            total_tests=5,
            summary_text="3 passed, 2 failed",
            generated_at=datetime(2024, 1, 15, 10, 30, 0),
            report_path="/path/to/report.html"
        )
        html = builder.build(data)

        assert 'class="fixture-header"' in html
        assert "Test Fixture Test Suite" in html
        assert "sc-startup" in html
        assert "startup" in html
        assert "5 tests" in html
        assert "3 passed, 2 failed" in html

    def test_header_with_file_links(self):
        """Test header with file path links.

        Agent/skill paths always open in VS Code (for .md files).
        Fixture paths always open in PyCharm (for .yaml files).
        """
        builder = HeaderBuilder()
        data = HeaderDisplayModel(
            fixture_name="Test Fixture",
            package="sc-startup",
            agent_or_skill="startup",
            agent_or_skill_path="/path/to/skill.md",
            fixture_path="/path/to/fixture.yaml",
            total_tests=3,
            summary_text="3 passed",
            generated_at=datetime(2024, 1, 15, 10, 30, 0),
            report_path="/path/to/report.html"
        )
        html = builder.build(data)
        # Agent/skill should open in VS Code
        assert "vscode://file//path/to/skill.md" in html
        # Fixture should open in PyCharm
        assert "pycharm://open" in html
        assert "fixture.yaml" in html


class TestTabsBuilder:
    """Tests for TabsBuilder component."""

    def test_tabs_header(self):
        """Test tabs header generation."""
        builder = TabsBuilder()
        tabs = [
            TabDisplayModel(tab_id="test-1", tab_label="Test 1", status=TestStatus.PASS, is_active=True),
            TabDisplayModel(tab_id="test-2", tab_label="Test 2", status=TestStatus.FAIL, is_active=False),
        ]
        html = builder.build(tabs)

        assert 'class="tabs-header"' in html
        assert 'onclick="switchTab(\'test-1\')"' in html
        assert 'onclick="switchTab(\'test-2\')"' in html
        assert "active" in html
        assert "Test 1" in html
        assert "Test 2" in html

    def test_tab_content_wrapper(self):
        """Test tab content wrapper generation."""
        builder = TabsBuilder()
        html = builder.build_tab_content_wrapper(
            "test-1",
            "<p>Content</p>",
            is_active=True
        )
        assert 'id="test-1"' in html
        assert 'class="tab-content active"' in html
        assert "<p>Content</p>" in html


class TestStatusBannerBuilder:
    """Tests for StatusBannerBuilder component."""

    def test_pass_banner(self):
        """Test PASS status banner."""
        builder = StatusBannerBuilder()
        data = StatusBannerDisplayModel(
            status=TestStatus.PASS,
            passed_count=5,
            total_count=5,
            duration_seconds=1.5,
            timestamp=datetime(2024, 1, 15, 10, 30, 0)
        )
        html = builder.build(data)

        assert 'class="status-banner pass"' in html
        assert "PASS" in html
        assert "5 of 5 expectations passed" in html
        assert "1.50s" in html

    def test_fail_banner(self):
        """Test FAIL status banner."""
        builder = StatusBannerBuilder()
        data = StatusBannerDisplayModel(
            status=TestStatus.FAIL,
            passed_count=0,
            total_count=3,
            duration_seconds=0.5,
            timestamp=datetime(2024, 1, 15, 10, 30, 0)
        )
        html = builder.build(data)

        assert 'class="status-banner fail"' in html
        assert "FAIL" in html


class TestExpectationsBuilder:
    """Tests for ExpectationsBuilder component."""

    def test_expectations_list(self):
        """Test expectations list generation."""
        builder = ExpectationsBuilder()
        data = ExpectationsDisplayModel(
            test_index=1,
            expectations=[
                ExpectationDisplayModel(
                    exp_id="exp-1",
                    description="Should call Bash",
                    status=TestStatus.PASS,
                    details_text="Type: tool_call"
                ),
                ExpectationDisplayModel(
                    exp_id="exp-2",
                    description="Should not fail",
                    status=TestStatus.FAIL,
                    details_text="Expected true, got false",
                    has_details=True,
                    expected_content="true",
                    actual_content="false"
                ),
            ]
        )
        html = builder.build(data)

        assert 'class="expectations-list"' in html
        assert "1 passed" in html
        assert "1 failed" in html
        assert "Should call Bash" in html
        assert "Should not fail" in html
        assert 'data-exp-id="exp-1"' in html
        assert 'data-exp-id="exp-2"' in html

    def test_expectation_with_details(self):
        """Test expectation with expandable details."""
        builder = ExpectationsBuilder()
        data = ExpectationsDisplayModel(
            test_index=1,
            expectations=[
                ExpectationDisplayModel(
                    exp_id="exp-1",
                    description="Test",
                    status=TestStatus.FAIL,
                    details_text="Details",
                    has_details=True,
                    expected_content="expected value",
                    actual_content="actual value"
                ),
            ]
        )
        html = builder.build(data)

        assert 'class="expectation-expanded"' in html
        assert "Expected" in html
        assert "Actual" in html
        assert "expected value" in html
        assert "actual value" in html


class TestTimelineBuilder:
    """Tests for TimelineBuilder component."""

    def test_timeline_structure(self):
        """Test timeline HTML structure."""
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-1",
            entries=[
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.PROMPT,
                    elapsed_ms=0,
                    content="Hello"
                ),
                TimelineItemDisplayModel(
                    seq=2,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Bash",
                    elapsed_ms=100,
                    command="echo hello",
                    output="hello"
                ),
            ],
            tool_call_count=1
        )
        html = builder.build(data)

        assert '<details>' in html
        assert "Timeline (1 tool calls)" in html
        assert 'id="timeline-1"' in html
        # Check for timeline-item classes with depth (depth-0 is default)
        assert 'class="timeline-item prompt depth-0"' in html
        assert 'class="timeline-item tool_call depth-0"' in html
        assert "#1" in html
        assert "#2" in html

    def test_timeline_tool_call_content(self):
        """Test tool call entry content."""
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-1",
            entries=[
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Bash",
                    elapsed_ms=100,
                    command="ls -la",
                    output="file1.txt\nfile2.txt"
                ),
            ],
            tool_call_count=1
        )
        html = builder.build(data)

        assert "$ ls -la" in html
        assert "file1.txt" in html

    def test_timeline_generates_subagent_sections(self):
        """Verify <details class="subagent-section"> wrappers are generated.

        When timeline entries have agent_id set (indicating subagent activity),
        they should be wrapped in collapsible <details class="subagent-section">
        elements for better organization and readability.
        """
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-subagent",
            entries=[
                # Main agent prompt
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.PROMPT,
                    elapsed_ms=0,
                    content="Initial prompt"
                ),
                # Subagent tool calls (should be wrapped)
                TimelineItemDisplayModel(
                    seq=2,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Read",
                    agent_id="agent-123",
                    agent_type="Explore",
                    elapsed_ms=100,
                    depth=1,
                    command="read file.py"
                ),
                TimelineItemDisplayModel(
                    seq=3,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Grep",
                    agent_id="agent-123",
                    agent_type="Explore",
                    elapsed_ms=200,
                    depth=1,
                    command="grep pattern"
                ),
                # Main agent response
                TimelineItemDisplayModel(
                    seq=4,
                    entry_type=TimelineEntryType.RESPONSE,
                    elapsed_ms=300,
                    content="Response"
                ),
            ],
            tool_call_count=2
        )
        html = builder.build(data)

        # Subagent entries should be wrapped in a details element
        assert '<details class="subagent-section"' in html
        assert 'data-agent-id="agent-123"' in html

    def test_subagent_section_contains_agent_badge(self):
        """Verify summary contains agent type badge.

        The <summary> element of a subagent section should contain:
        - Agent type badge (e.g., "Explore")
        - Styled with class="agent-badge"
        """
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-badge",
            entries=[
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Read",
                    agent_id="agent-456",
                    agent_type="CodeReview",
                    elapsed_ms=100,
                    depth=1
                ),
            ],
            tool_call_count=1
        )
        html = builder.build(data)

        # Summary should contain agent badge with the agent type
        assert '<span class="agent-badge">' in html
        assert "CodeReview" in html

    def test_subagent_section_tool_count(self):
        """Verify tool count is accurate in summary.

        The summary should display the count of tool calls within
        that subagent section (e.g., "3 tool calls").
        """
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-count",
            entries=[
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Read",
                    agent_id="agent-789",
                    agent_type="Explore",
                    elapsed_ms=100,
                    depth=1
                ),
                TimelineItemDisplayModel(
                    seq=2,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Grep",
                    agent_id="agent-789",
                    agent_type="Explore",
                    elapsed_ms=200,
                    depth=1
                ),
                TimelineItemDisplayModel(
                    seq=3,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Bash",
                    agent_id="agent-789",
                    agent_type="Explore",
                    elapsed_ms=300,
                    depth=1
                ),
            ],
            tool_call_count=3
        )
        html = builder.build(data)

        # Summary should show accurate tool count for this subagent
        assert '<span class="tool-count">' in html
        assert "3 tool call" in html

    def test_smart_collapse_expands_dominant_agent(self):
        """Agent with >66% of tools should be expanded by default.

        When a subagent accounts for more than 66% of the total tool calls,
        its section should have the 'open' attribute to be expanded by default.
        This helps users see the most significant activity immediately.
        """
        builder = TimelineBuilder()
        # 8 out of 10 tool calls (80%) belong to the subagent - should be expanded
        entries = [
            TimelineItemDisplayModel(
                seq=1,
                entry_type=TimelineEntryType.PROMPT,
                elapsed_ms=0,
                content="Start"
            ),
        ]
        # Add 8 subagent tool calls
        for i in range(8):
            entries.append(TimelineItemDisplayModel(
                seq=i + 2,
                entry_type=TimelineEntryType.TOOL_CALL,
                tool_name="Tool",
                agent_id="dominant-agent",
                agent_type="Worker",
                elapsed_ms=(i + 1) * 100,
                depth=1
            ))
        # Add 2 main agent tool calls
        for i in range(2):
            entries.append(TimelineItemDisplayModel(
                seq=i + 10,
                entry_type=TimelineEntryType.TOOL_CALL,
                tool_name="MainTool",
                elapsed_ms=(i + 10) * 100,
                depth=0
            ))

        data = TimelineDisplayModel(
            timeline_id="timeline-expand",
            entries=entries,
            tool_call_count=10
        )
        html = builder.build(data)

        # Dominant agent section should have 'open' attribute
        # The section with >66% of tools should be expanded by default
        assert '<details class="subagent-section"' in html
        assert 'data-agent-id="dominant-agent"' in html
        # Check for 'open' attribute on the dominant section
        # The subagent-section with dominant-agent should have open
        import re
        dominant_section = re.search(
            r'<details class="subagent-section"[^>]*data-agent-id="dominant-agent"[^>]*>',
            html
        )
        assert dominant_section is not None, "Dominant agent section not found"
        assert 'open' in dominant_section.group(0), \
            "Dominant agent section (>66% activity) should be expanded by default"

    def test_smart_collapse_collapses_minor_agents(self):
        """Agents with <66% of tools should be collapsed.

        When a subagent accounts for less than 66% of the total tool calls,
        its section should be collapsed by default to reduce visual noise.
        """
        builder = TimelineBuilder()
        # 2 out of 10 tool calls (20%) belong to the subagent - should be collapsed
        entries = [
            TimelineItemDisplayModel(
                seq=1,
                entry_type=TimelineEntryType.PROMPT,
                elapsed_ms=0,
                content="Start"
            ),
        ]
        # Add 2 subagent tool calls (minor activity)
        for i in range(2):
            entries.append(TimelineItemDisplayModel(
                seq=i + 2,
                entry_type=TimelineEntryType.TOOL_CALL,
                tool_name="MinorTool",
                agent_id="minor-agent",
                agent_type="Helper",
                elapsed_ms=(i + 1) * 100,
                depth=1
            ))
        # Add 8 main agent tool calls (majority)
        for i in range(8):
            entries.append(TimelineItemDisplayModel(
                seq=i + 4,
                entry_type=TimelineEntryType.TOOL_CALL,
                tool_name="MainTool",
                elapsed_ms=(i + 4) * 100,
                depth=0
            ))

        data = TimelineDisplayModel(
            timeline_id="timeline-collapse",
            entries=entries,
            tool_call_count=10
        )
        html = builder.build(data)

        # Minor agent section should NOT have 'open' attribute
        assert '<details class="subagent-section"' in html
        assert 'data-agent-id="minor-agent"' in html
        # Check that the minor agent section does NOT have 'open'
        import re
        minor_section = re.search(
            r'<details class="subagent-section"[^>]*data-agent-id="minor-agent"[^>]*>',
            html
        )
        assert minor_section is not None, "Minor agent section not found"
        assert 'open' not in minor_section.group(0), \
            "Minor agent section (<66% activity) should be collapsed by default"

    def test_timeline_with_multiple_subagents(self):
        """Test timeline with multiple different subagents.

        Each distinct subagent (by agent_id) should get its own
        collapsible section, maintaining separation of concerns.
        """
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-multi",
            entries=[
                # First subagent's activity
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Read",
                    agent_id="explore-agent",
                    agent_type="Explore",
                    elapsed_ms=100,
                    depth=1
                ),
                TimelineItemDisplayModel(
                    seq=2,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Grep",
                    agent_id="explore-agent",
                    agent_type="Explore",
                    elapsed_ms=200,
                    depth=1
                ),
                # Second subagent's activity
                TimelineItemDisplayModel(
                    seq=3,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Edit",
                    agent_id="edit-agent",
                    agent_type="CodeEdit",
                    elapsed_ms=300,
                    depth=1
                ),
            ],
            tool_call_count=3
        )
        html = builder.build(data)

        # Should have two separate subagent sections
        assert 'data-agent-id="explore-agent"' in html
        assert 'data-agent-id="edit-agent"' in html
        # Both agent types should appear in badges
        assert "Explore" in html
        assert "CodeEdit" in html

    def test_timeline_no_subagent_sections_without_agents(self):
        """Test that no subagent sections are created for main agent only.

        When all entries belong to the main agent (no agent_id set),
        no subagent-section wrappers should be generated.
        """
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-main-only",
            entries=[
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.PROMPT,
                    elapsed_ms=0,
                    content="Hello"
                ),
                TimelineItemDisplayModel(
                    seq=2,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Bash",
                    elapsed_ms=100,
                    command="echo hello"
                ),
                TimelineItemDisplayModel(
                    seq=3,
                    entry_type=TimelineEntryType.RESPONSE,
                    elapsed_ms=200,
                    content="Done"
                ),
            ],
            tool_call_count=1
        )
        html = builder.build(data)

        # No subagent sections should be present
        assert 'class="subagent-section"' not in html

    def test_subagent_section_duration_display(self):
        """Test that subagent section summary shows duration.

        The summary should include the total duration of the subagent's
        activity (difference between first and last tool call elapsed_ms).
        """
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-duration",
            entries=[
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Read",
                    agent_id="timed-agent",
                    agent_type="Explore",
                    elapsed_ms=1000,  # Start at 1s
                    depth=1
                ),
                TimelineItemDisplayModel(
                    seq=2,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Grep",
                    agent_id="timed-agent",
                    agent_type="Explore",
                    elapsed_ms=3500,  # End at 3.5s -> 2.5s duration
                    depth=1
                ),
            ],
            tool_call_count=2
        )
        html = builder.build(data)

        # Summary should show duration
        assert '<span class="subagent-duration">' in html
        # Duration should be approximately 2.5s (3500 - 1000)
        assert "+2.5s" in html or "+2500ms" in html


class TestReproduceBuilder:
    """Tests for ReproduceBuilder component."""

    def test_reproduce_section(self):
        """Test reproduce section generation."""
        builder = ReproduceBuilder()
        data = ReproduceDisplayModel(
            test_index=1,
            setup_commands=["cd /path/to/test", "git checkout main"],
            test_command="claude --model haiku 'Run the test'"
        )
        html = builder.build(data)

        assert 'class="reproduce-section"' in html
        assert "Reproduce This Test" in html
        assert "1. Setup" in html
        assert "2. Run Test" in html
        assert "cd /path/to/test" in html
        assert "claude --model haiku" in html


class TestDebugBuilder:
    """Tests for DebugBuilder component."""

    def test_debug_section(self):
        """Test debug section generation."""
        builder = DebugBuilder()
        data = DebugDisplayModel(
            test_index=1,
            pytest_output="PASSED",
            package="sc-startup",
            test_repo="/path/to/repo",
            side_effects_text="No files were created, modified, or deleted."
        )
        html = builder.build(data)

        assert '<details>' in html
        assert "Debug Information" in html
        assert "PASSED" in html
        assert "Side Effects" in html
        assert "No files were created" in html


class TestAssessmentBuilder:
    """Tests for AssessmentBuilder component."""

    def test_lazy_loading_assessment(self):
        """Test assessment with lazy loading placeholder."""
        builder = AssessmentBuilder()
        data = AssessmentDisplayModel(
            test_index=1,
            test_id="test-001",
            is_embedded=False
        )
        html = builder.build(data)

        assert 'class="agent-assessment-section"' in html
        assert 'data-test-id="test-001"' in html
        assert "Loading assessment..." in html
        assert 'open' not in html  # Should not be open by default

    def test_embedded_assessment(self):
        """Test assessment with embedded content."""
        builder = AssessmentBuilder()
        data = AssessmentDisplayModel(
            test_index=1,
            test_id="test-001",
            content_html="<p>Assessment content</p>",
            model="claude-3-opus",
            timestamp="2024-01-15 10:30:00",
            is_embedded=True
        )
        html = builder.build(data)

        assert 'class="agent-assessment-section visible"' in html
        assert "Assessment content" in html
        assert "Generated by claude-3-opus" in html
        assert "2024-01-15 10:30:00" in html
        assert "open" in html  # Should be open for embedded


class TestPluginVerificationBuilder:
    """Tests for PluginVerificationBuilder component."""

    def test_no_plugins_returns_empty(self):
        """Test that empty plugins list returns empty string."""
        builder = PluginVerificationBuilder()
        data = PluginVerificationDisplayModel(
            test_index=1,
            expected_plugins=[],
            install_results=[],
            has_plugins=False
        )
        html = builder.build(data)
        assert html == ""

    def test_successful_plugin_installation(self):
        """Test plugin verification section with successful installation."""
        builder = PluginVerificationBuilder()
        data = PluginVerificationDisplayModel(
            test_index=1,
            expected_plugins=["sc-startup@synaptic-canvas"],
            install_results=[
                PluginInstallResultDisplayModel(
                    plugin_name="sc-startup@synaptic-canvas",
                    success=True,
                    stdout="Successfully installed plugin: sc-startup",
                    stderr="",
                    return_code=0
                )
            ],
            has_plugins=True
        )
        html = builder.build(data)

        assert 'class="plugin-verification-section"' in html
        assert "Plugin Verification" in html
        assert "1/1 plugins installed" in html
        assert "sc-startup@synaptic-canvas" in html
        assert "Installed" in html
        assert "&#9989;" in html  # Checkmark
        assert 'class="plugin-item pass"' in html

    def test_failed_plugin_installation(self):
        """Test plugin verification section with failed installation."""
        builder = PluginVerificationBuilder()
        data = PluginVerificationDisplayModel(
            test_index=1,
            expected_plugins=["nonexistent-plugin"],
            install_results=[
                PluginInstallResultDisplayModel(
                    plugin_name="nonexistent-plugin",
                    success=False,
                    stdout="",
                    stderr='Plugin "nonexistent-plugin" not found',
                    return_code=1
                )
            ],
            has_plugins=True
        )
        html = builder.build(data)

        assert "0/1 plugins installed" in html
        assert "Failed" in html
        assert "&#10060;" in html  # Red X
        assert 'class="plugin-item fail"' in html
        # HTML escaping converts quotes to &quot;
        assert 'nonexistent-plugin' in html
        assert 'not found' in html
        assert "return code: 1" in html

    def test_multiple_plugins(self):
        """Test plugin verification with multiple plugins."""
        builder = PluginVerificationBuilder()
        data = PluginVerificationDisplayModel(
            test_index=1,
            expected_plugins=["plugin-1", "plugin-2", "plugin-3"],
            install_results=[
                PluginInstallResultDisplayModel(
                    plugin_name="plugin-1",
                    success=True,
                    stdout="Installed",
                    stderr="",
                    return_code=0
                ),
                PluginInstallResultDisplayModel(
                    plugin_name="plugin-2",
                    success=True,
                    stdout="Installed",
                    stderr="",
                    return_code=0
                ),
                PluginInstallResultDisplayModel(
                    plugin_name="plugin-3",
                    success=False,
                    stdout="",
                    stderr="Error",
                    return_code=1
                ),
            ],
            has_plugins=True
        )
        html = builder.build(data)

        assert "2/3 plugins installed" in html
        # Should show failure status
        assert 'class="plugin-summary fail"' in html

    def test_cli_output_collapsible(self):
        """Test that CLI output is in collapsible details element."""
        builder = PluginVerificationBuilder()
        data = PluginVerificationDisplayModel(
            test_index=1,
            expected_plugins=["test-plugin"],
            install_results=[
                PluginInstallResultDisplayModel(
                    plugin_name="test-plugin",
                    success=True,
                    stdout="Some output",
                    stderr="Some warning",
                    return_code=0
                )
            ],
            has_plugins=True
        )
        html = builder.build(data)

        assert '<details class="plugin-output">' in html
        assert "CLI Output" in html
        assert "Some output" in html
        assert "Some warning" in html
