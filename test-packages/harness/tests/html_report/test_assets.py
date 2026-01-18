"""
Tests for HTML Report Builder CSS and JavaScript assets.

These tests verify that:
1. CSS contains required selectors and rules
2. JavaScript contains required functions
3. No placeholder comments or TODOs remain
4. Assets are properly combined
"""

import pytest

from harness.html_report.assets import (
    # CSS constants
    CSS_VARIABLES,
    CSS_BASE,
    CSS_HEADER,
    CSS_TABS,
    CSS_STATUS_BANNER,
    CSS_METADATA,
    CSS_SECTIONS,
    CSS_COPY_BUTTON,
    CSS_EXPECTATIONS,
    CSS_TIMELINE,
    CSS_RESPONSE,
    CSS_DEBUG,
    CSS_ASSESSMENT,
    CSS_FILE_LINKS,
    get_all_css,
    # JavaScript constants
    JS_EDITOR_UTILS,
    JS_TAB_SWITCHING,
    JS_COPY_FUNCTIONS,
    JS_TOGGLE_FUNCTIONS,
    JS_MARKDOWN_RENDERER,
    JS_ASSESSMENT_LOADER,
    JS_INITIALIZATION,
    get_all_scripts,
    # Manager class
    AssetManager,
)


class TestCSSVariables:
    """Tests for CSS variable definitions."""

    def test_contains_root_selector(self):
        """Verify :root selector is present."""
        assert ":root" in CSS_VARIABLES

    def test_contains_pass_color(self):
        """Verify pass color variable is defined."""
        assert "--pass: #059669" in CSS_VARIABLES

    def test_contains_fail_color(self):
        """Verify fail color variable is defined."""
        assert "--fail: #dc2626" in CSS_VARIABLES

    def test_contains_partial_color(self):
        """Verify partial color variable is defined."""
        assert "--partial: #d97706" in CSS_VARIABLES

    def test_contains_skipped_color(self):
        """Verify skipped color variable is defined."""
        assert "--skipped: #6b7280" in CSS_VARIABLES

    def test_contains_border_color(self):
        """Verify border color variable is defined."""
        assert "--border: #e5e7eb" in CSS_VARIABLES

    def test_contains_text_colors(self):
        """Verify text color variables are defined."""
        assert "--text: #111827" in CSS_VARIABLES
        assert "--text-muted: #6b7280" in CSS_VARIABLES


class TestCSSBase:
    """Tests for base CSS styles."""

    def test_contains_box_sizing(self):
        """Verify box-sizing reset is present."""
        assert "box-sizing: border-box" in CSS_BASE

    def test_contains_body_styles(self):
        """Verify body styles are defined."""
        assert "body {" in CSS_BASE
        assert "font-family:" in CSS_BASE
        assert "max-width: 1200px" in CSS_BASE


class TestCSSHeader:
    """Tests for fixture header CSS styles."""

    def test_contains_fixture_header(self):
        """Verify .fixture-header selector is present."""
        assert ".fixture-header {" in CSS_HEADER

    def test_contains_gradient_background(self):
        """Verify gradient background is defined."""
        assert "linear-gradient(135deg, #1e293b 0%, #334155 100%)" in CSS_HEADER

    def test_contains_fixture_meta(self):
        """Verify .fixture-meta grid is defined."""
        assert ".fixture-meta {" in CSS_HEADER
        assert "display: grid" in CSS_HEADER


class TestCSSTabs:
    """Tests for tab navigation CSS styles."""

    def test_contains_tabs_container(self):
        """Verify .tabs-container selector is present."""
        assert ".tabs-container {" in CSS_TABS

    def test_contains_tab_button(self):
        """Verify .tab-button selector is present."""
        assert ".tab-button {" in CSS_TABS

    def test_contains_active_tab_style(self):
        """Verify active tab styles are defined."""
        assert ".tab-button.active {" in CSS_TABS

    def test_contains_tab_icon_colors(self):
        """Verify tab icon status colors are defined."""
        assert ".tab-icon.pass" in CSS_TABS
        assert ".tab-icon.fail" in CSS_TABS
        assert ".tab-icon.partial" in CSS_TABS
        assert ".tab-icon.skipped" in CSS_TABS


class TestCSSStatusBanner:
    """Tests for status banner CSS styles."""

    def test_contains_status_banner(self):
        """Verify .status-banner selector is present."""
        assert ".status-banner {" in CSS_STATUS_BANNER

    def test_contains_all_status_variants(self):
        """Verify all status variants are styled."""
        assert ".status-banner.pass {" in CSS_STATUS_BANNER
        assert ".status-banner.fail {" in CSS_STATUS_BANNER
        assert ".status-banner.partial {" in CSS_STATUS_BANNER
        assert ".status-banner.skipped {" in CSS_STATUS_BANNER

    def test_contains_status_badge(self):
        """Verify .status-badge selector is present."""
        assert ".status-badge {" in CSS_STATUS_BANNER


class TestCSSMetadata:
    """Tests for test metadata CSS styles."""

    def test_contains_test_metadata(self):
        """Verify .test-metadata selector is present."""
        assert ".test-metadata {" in CSS_METADATA

    def test_contains_metadata_grid(self):
        """Verify .test-metadata-grid selector is present."""
        assert ".test-metadata-grid {" in CSS_METADATA
        assert "display: grid" in CSS_METADATA

    def test_contains_section_header(self):
        """Verify .section-header selector is present."""
        assert ".section-header {" in CSS_METADATA

    def test_contains_reproduce_section(self):
        """Verify .reproduce-section selector is present."""
        assert ".reproduce-section {" in CSS_METADATA


class TestCSSSections:
    """Tests for collapsible details/summary CSS styles."""

    def test_contains_details_selector(self):
        """Verify details selector is present."""
        assert "details {" in CSS_SECTIONS

    def test_contains_summary_selector(self):
        """Verify details summary selector is present."""
        assert "details summary {" in CSS_SECTIONS

    def test_contains_marker_hiding(self):
        """Verify default marker is hidden."""
        assert "::marker" in CSS_SECTIONS
        assert "::-webkit-details-marker" in CSS_SECTIONS

    def test_contains_arrow_indicator(self):
        """Verify custom arrow indicator is present."""
        assert ".summary-text::before" in CSS_SECTIONS
        assert "\\25B6" in CSS_SECTIONS  # Right-pointing triangle

    def test_contains_open_state_rotation(self):
        """Verify arrow rotation on open state."""
        assert "details[open] .summary-text::before" in CSS_SECTIONS
        assert "rotate(90deg)" in CSS_SECTIONS


class TestCSSCopyButton:
    """Tests for copy button CSS styles."""

    def test_contains_copy_icon_btn(self):
        """Verify .copy-icon-btn selector is present."""
        assert ".copy-icon-btn {" in CSS_COPY_BUTTON

    def test_contains_hover_state(self):
        """Verify hover state is defined."""
        assert ".copy-icon-btn:hover {" in CSS_COPY_BUTTON

    def test_contains_copied_state(self):
        """Verify copied state is defined."""
        assert ".copy-icon-btn.copied {" in CSS_COPY_BUTTON
        assert ".copy-icon-btn.copied .clipboard" in CSS_COPY_BUTTON
        assert ".copy-icon-btn.copied .checkmark" in CSS_COPY_BUTTON

    def test_contains_tooltip(self):
        """Verify tooltip styles are defined."""
        assert "[data-tooltip]" in CSS_COPY_BUTTON
        assert "[data-tooltip]:hover::after" in CSS_COPY_BUTTON


class TestCSSExpectations:
    """Tests for expectation CSS styles."""

    def test_contains_expectations_list(self):
        """Verify .expectations-list selector is present."""
        assert ".expectations-list {" in CSS_EXPECTATIONS

    def test_contains_expectation_item(self):
        """Verify .expectation-item selector is present."""
        assert ".expectation-item {" in CSS_EXPECTATIONS

    def test_contains_toggle_button(self):
        """Verify .expectation-toggle selector is present."""
        assert ".expectation-toggle {" in CSS_EXPECTATIONS

    def test_contains_toggle_states(self):
        """Verify toggle button states are defined."""
        assert ".expectation-toggle.no-content" in CSS_EXPECTATIONS
        assert ".expectation-toggle.has-content" in CSS_EXPECTATIONS

    def test_contains_expanded_section(self):
        """Verify .expectation-expanded selector is present."""
        assert ".expectation-expanded {" in CSS_EXPECTATIONS
        assert ".expectation-expanded.show" in CSS_EXPECTATIONS

    def test_contains_expected_actual_grid(self):
        """Verify expected/actual grid is defined."""
        assert ".expected-actual {" in CSS_EXPECTATIONS
        assert "grid-template-columns: 1fr 1fr" in CSS_EXPECTATIONS


class TestCSSTimeline:
    """Tests for timeline CSS styles."""

    def test_contains_timeline(self):
        """Verify .timeline selector is present."""
        assert ".timeline {" in CSS_TIMELINE

    def test_contains_before_pseudo_element(self):
        """Verify ::before vertical line is defined."""
        assert ".timeline::before {" in CSS_TIMELINE
        assert "width: 2px" in CSS_TIMELINE

    def test_contains_timeline_dot(self):
        """Verify .timeline-dot selector is present."""
        assert ".timeline-dot {" in CSS_TIMELINE
        assert "border-radius: 50%" in CSS_TIMELINE

    def test_contains_dot_colors_for_types(self):
        """Verify dot colors for different entry types."""
        assert ".timeline-item.prompt .timeline-dot" in CSS_TIMELINE
        assert ".timeline-item.tool_call .timeline-dot" in CSS_TIMELINE
        assert ".timeline-item.response .timeline-dot" in CSS_TIMELINE
        assert "#3b82f6" in CSS_TIMELINE  # prompt color
        assert "#8b5cf6" in CSS_TIMELINE  # tool_call color
        assert "#10b981" in CSS_TIMELINE  # response color

    def test_contains_timeline_type_colors(self):
        """Verify type label colors."""
        assert ".timeline-item.prompt .timeline-type" in CSS_TIMELINE
        assert ".timeline-item.tool_call .timeline-type" in CSS_TIMELINE
        assert ".timeline-item.response .timeline-type" in CSS_TIMELINE


class TestCSSResponse:
    """Tests for response preview CSS styles."""

    def test_contains_response_preview(self):
        """Verify .response-preview selector is present."""
        assert ".response-preview {" in CSS_RESPONSE
        assert "max-height: 300px" in CSS_RESPONSE
        assert "overflow-y: auto" in CSS_RESPONSE


class TestCSSDebug:
    """Tests for debug table CSS styles."""

    def test_contains_debug_table(self):
        """Verify .debug-table selector is present."""
        assert ".debug-table {" in CSS_DEBUG
        assert "border-collapse: collapse" in CSS_DEBUG


class TestCSSAssessment:
    """Tests for agent assessment CSS styles."""

    def test_contains_agent_assessment_section(self):
        """Verify .agent-assessment-section selector is present."""
        assert ".agent-assessment-section {" in CSS_ASSESSMENT
        assert ".agent-assessment-section.visible" in CSS_ASSESSMENT

    def test_contains_gradient_background(self):
        """Verify dark gradient background is defined."""
        assert "linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)" in CSS_ASSESSMENT

    def test_contains_ai_badge(self):
        """Verify .ai-badge selector is present."""
        assert ".ai-badge {" in CSS_ASSESSMENT

    def test_contains_content_typography(self):
        """Verify content typography styles are present."""
        assert ".agent-assessment-content h1" in CSS_ASSESSMENT
        assert ".agent-assessment-content h2" in CSS_ASSESSMENT
        assert ".agent-assessment-content code" in CSS_ASSESSMENT
        assert ".agent-assessment-content pre" in CSS_ASSESSMENT

    def test_contains_loading_and_error_states(self):
        """Verify loading and error states are styled."""
        assert ".agent-assessment-loading" in CSS_ASSESSMENT
        assert ".agent-assessment-error" in CSS_ASSESSMENT


class TestCSSFileLinks:
    """Tests for file link CSS styles."""

    def test_contains_file_link(self):
        """Verify a.file-link selector is present."""
        assert "a.file-link {" in CSS_FILE_LINKS

    def test_contains_hover_state(self):
        """Verify hover state is defined."""
        assert "a.file-link:hover {" in CSS_FILE_LINKS

    def test_contains_editor_icon_colors(self):
        """Verify editor-specific icon colors."""
        assert "a.file-link.pycharm .link-icon" in CSS_FILE_LINKS
        assert "#21d789" in CSS_FILE_LINKS  # PyCharm green
        assert "a.file-link.vscode .link-icon" in CSS_FILE_LINKS
        assert "#007acc" in CSS_FILE_LINKS  # VS Code blue


class TestJSEditorUtils:
    """Tests for editor utility JavaScript functions."""

    def test_contains_get_editor_url(self):
        """Verify getEditorUrl function is present."""
        assert "function getEditorUrl(filePath)" in JS_EDITOR_UTILS

    def test_contains_get_editor_type(self):
        """Verify getEditorType function is present."""
        assert "function getEditorType(filePath)" in JS_EDITOR_UTILS

    def test_contains_create_file_link(self):
        """Verify createFileLink function is present."""
        assert "function createFileLink(filePath, displayText)" in JS_EDITOR_UTILS

    def test_handles_pycharm_for_python(self):
        """Verify PyCharm URL format for .py files."""
        assert "pycharm://open?file=" in JS_EDITOR_UTILS
        assert "encodeURIComponent" in JS_EDITOR_UTILS

    def test_handles_vscode_for_other_files(self):
        """Verify VS Code URL format for non-.py files."""
        assert "vscode://file/" in JS_EDITOR_UTILS


class TestJSTabSwitching:
    """Tests for tab switching JavaScript."""

    def test_contains_switch_tab(self):
        """Verify switchTab function is present."""
        assert "function switchTab(tabId)" in JS_TAB_SWITCHING

    def test_removes_active_class(self):
        """Verify active class removal logic."""
        assert "classList.remove('active')" in JS_TAB_SWITCHING

    def test_adds_active_class(self):
        """Verify active class addition logic."""
        assert "classList.add('active')" in JS_TAB_SWITCHING


class TestJSCopyFunctions:
    """Tests for copy functionality JavaScript."""

    def test_contains_show_copy_feedback(self):
        """Verify showCopyFeedback function is present."""
        assert "function showCopyFeedback(btn)" in JS_COPY_FUNCTIONS

    def test_contains_copy_element(self):
        """Verify copyElement function is present."""
        assert "function copyElement(elementId)" in JS_COPY_FUNCTIONS

    def test_contains_copy_section(self):
        """Verify copySection function is present."""
        assert "function copySection(elementId, sectionTitle)" in JS_COPY_FUNCTIONS

    def test_contains_copy_expectation(self):
        """Verify copyExpectation function is present."""
        assert "function copyExpectation(expId)" in JS_COPY_FUNCTIONS

    def test_contains_copy_timeline_item(self):
        """Verify copyTimelineItem function is present."""
        assert "function copyTimelineItem(btn)" in JS_COPY_FUNCTIONS

    def test_contains_copy_timeline(self):
        """Verify copyTimeline function is present."""
        assert "function copyTimeline(timelineId)" in JS_COPY_FUNCTIONS

    def test_contains_copy_assessment(self):
        """Verify copyAssessment function is present."""
        assert "function copyAssessment(elementId)" in JS_COPY_FUNCTIONS

    def test_uses_clipboard_api(self):
        """Verify navigator.clipboard.writeText is used."""
        assert "navigator.clipboard.writeText" in JS_COPY_FUNCTIONS


class TestJSToggleFunctions:
    """Tests for toggle functionality JavaScript."""

    def test_contains_toggle_expectation(self):
        """Verify toggleExpectation function is present."""
        assert "function toggleExpectation(id)" in JS_TOGGLE_FUNCTIONS

    def test_toggles_show_class(self):
        """Verify classList.toggle('show') is used."""
        assert "classList.toggle('show')" in JS_TOGGLE_FUNCTIONS


class TestJSMarkdownRenderer:
    """Tests for markdown rendering JavaScript."""

    def test_contains_render_markdown(self):
        """Verify renderMarkdown function is present."""
        assert "function renderMarkdown(markdown)" in JS_MARKDOWN_RENDERER

    def test_handles_headers(self):
        """Verify header parsing."""
        assert "<h1>" in JS_MARKDOWN_RENDERER
        assert "<h2>" in JS_MARKDOWN_RENDERER
        assert "<h3>" in JS_MARKDOWN_RENDERER
        assert "<h4>" in JS_MARKDOWN_RENDERER

    def test_handles_code_blocks(self):
        """Verify code block parsing."""
        assert "<pre><code" in JS_MARKDOWN_RENDERER

    def test_handles_inline_code(self):
        """Verify inline code parsing."""
        assert "<code>$1</code>" in JS_MARKDOWN_RENDERER

    def test_handles_bold_and_italic(self):
        """Verify bold and italic parsing."""
        assert "<strong>" in JS_MARKDOWN_RENDERER
        assert "<em>" in JS_MARKDOWN_RENDERER

    def test_handles_lists(self):
        """Verify list parsing."""
        assert "<li>" in JS_MARKDOWN_RENDERER
        assert "<ul>" in JS_MARKDOWN_RENDERER


class TestJSAssessmentLoader:
    """Tests for assessment loading JavaScript."""

    def test_contains_load_agent_assessments(self):
        """Verify loadAgentAssessments function is present."""
        assert "function loadAgentAssessments()" in JS_ASSESSMENT_LOADER

    def test_contains_try_fetch_assessment(self):
        """Verify tryFetchAssessment function is present."""
        assert "function tryFetchAssessment(paths, index, section, contentEl, metaEl)" in JS_ASSESSMENT_LOADER

    def test_uses_fetch_api(self):
        """Verify fetch API is used."""
        assert "fetch(paths[index])" in JS_ASSESSMENT_LOADER

    def test_handles_multiple_file_paths(self):
        """Verify multiple file naming conventions are tried."""
        assert "assessment.md" in JS_ASSESSMENT_LOADER
        assert "filesToTry" in JS_ASSESSMENT_LOADER

    def test_extracts_yaml_frontmatter(self):
        """Verify YAML frontmatter extraction."""
        assert "frontmatterMatch" in JS_ASSESSMENT_LOADER
        assert "generated_by" in JS_ASSESSMENT_LOADER


class TestJSInitialization:
    """Tests for initialization JavaScript."""

    def test_prevents_no_content_toggle(self):
        """Verify no-content buttons are disabled."""
        assert ".expectation-toggle.no-content" in JS_INITIALIZATION
        assert "e.preventDefault()" in JS_INITIALIZATION
        assert "e.stopPropagation()" in JS_INITIALIZATION

    def test_loads_assessments_on_dom_ready(self):
        """Verify DOMContentLoaded listener."""
        assert "DOMContentLoaded" in JS_INITIALIZATION
        assert "loadAgentAssessments" in JS_INITIALIZATION

    def test_handles_already_loaded_dom(self):
        """Verify fallback for already loaded DOM."""
        assert "document.readyState" in JS_INITIALIZATION


class TestGetAllCss:
    """Tests for combined CSS output."""

    def test_returns_string(self):
        """Verify get_all_css returns a string."""
        css = get_all_css()
        assert isinstance(css, str)

    def test_contains_all_sections(self):
        """Verify all CSS sections are included."""
        css = get_all_css()
        assert ":root" in css
        assert ".fixture-header" in css
        assert ".tabs-container" in css
        assert ".status-banner" in css
        assert ".test-metadata" in css
        assert ".copy-icon-btn" in css
        assert ".expectations-list" in css
        assert ".timeline" in css
        assert ".response-preview" in css
        assert ".debug-table" in css
        assert ".agent-assessment" in css
        assert "a.file-link" in css

    def test_no_placeholder_comments(self):
        """Verify no placeholder comments remain."""
        css = get_all_css()
        assert "TODO" not in css
        assert "FIXME" not in css
        assert "placeholder" not in css.lower()


class TestGetAllScripts:
    """Tests for combined JavaScript output."""

    def test_returns_string(self):
        """Verify get_all_scripts returns a string."""
        scripts = get_all_scripts()
        assert isinstance(scripts, str)

    def test_contains_all_functions(self):
        """Verify all JS functions are included."""
        scripts = get_all_scripts()
        assert "getEditorUrl" in scripts
        assert "getEditorType" in scripts
        assert "createFileLink" in scripts
        assert "switchTab" in scripts
        assert "showCopyFeedback" in scripts
        assert "copyElement" in scripts
        assert "copySection" in scripts
        assert "copyExpectation" in scripts
        assert "copyTimelineItem" in scripts
        assert "copyTimeline" in scripts
        assert "copyAssessment" in scripts
        assert "toggleExpectation" in scripts
        assert "renderMarkdown" in scripts
        assert "loadAgentAssessments" in scripts
        assert "tryFetchAssessment" in scripts

    def test_no_placeholder_comments(self):
        """Verify no placeholder comments remain."""
        scripts = get_all_scripts()
        assert "TODO" not in scripts
        assert "FIXME" not in scripts
        assert "placeholder" not in scripts.lower()


class TestAssetManager:
    """Tests for AssetManager class."""

    def test_get_css_returns_css(self):
        """Verify get_css returns CSS."""
        css = AssetManager.get_css()
        assert ":root" in css
        assert ".fixture-header" in css

    def test_get_scripts_returns_js(self):
        """Verify get_scripts returns JavaScript."""
        scripts = AssetManager.get_scripts()
        assert "function" in scripts
        assert "getEditorUrl" in scripts

    def test_get_style_tag_wrapped(self):
        """Verify get_style_tag wraps in style tags."""
        style_tag = AssetManager.get_style_tag()
        assert style_tag.startswith("<style>")
        assert style_tag.endswith("</style>")
        assert ":root" in style_tag

    def test_get_script_tag_wrapped(self):
        """Verify get_script_tag wraps in script tags."""
        script_tag = AssetManager.get_script_tag()
        assert script_tag.startswith("<script>")
        assert script_tag.endswith("</script>")
        assert "function" in script_tag
