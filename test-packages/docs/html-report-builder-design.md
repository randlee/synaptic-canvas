# HTML Report Builder Design Document

**Version:** 1.0
**Date:** 2026-01-16
**Status:** Design Phase
**Author:** Claude Code Test Harness Team

---

## 1. Architecture Overview

The HTML Report Builder uses a **Builder Pattern** to construct modular, composable HTML report components. This design separates data transformation from HTML rendering, enabling unit-testable components and flexible report customization.

### 1.1 High-Level Architecture Diagram

```
                              +-------------------+
                              |   FixtureReport   |
                              |   (Pydantic)      |
                              +--------+----------+
                                       |
                                       v
                          +------------+-----------+
                          |    HTMLReportBuilder   |
                          |    (Orchestrator)      |
                          +------------+-----------+
                                       |
           +---------------------------+---------------------------+
           |               |               |               |       |
           v               v               v               v       v
    +-----------+   +-----------+   +-----------+   +-----------+  |
    |  Header   |   | TestCase  |   | Timeline  |   |Assessment |  |
    |  Builder  |   |  Builder  |   |  Builder  |   |  Builder  |  |
    +-----------+   +-----------+   +-----------+   +-----------+  |
           |               |               |               |       |
           v               v               v               v       v
    +-----------+   +-----------+   +-----------+   +-----------+  |
    |  Header   |   | TestCase  |   | Timeline  |   |Assessment |  |
    | Component |   | Component |   | Component |   | Component |  |
    +-----------+   +-----------+   +-----------+   +-----------+  |
                                                                   |
                          +----------------------------------------+
                          |
                          v
                    +------------+
                    |   Assets   |
                    | (CSS, JS)  |
                    +------------+
                          |
                          v
                    +------------+
                    | Final HTML |
                    +------------+
```

### 1.2 Component Flow

```
Data Flow:
==========

FixtureReport (Pydantic Model)
        |
        +---> HTMLReportBuilder.build()
                    |
                    +---> HeaderBuilder.build(fixture_meta)
                    |           |
                    |           +---> HeaderComponent (HTML string)
                    |
                    +---> TabsBuilder.build(tests)
                    |           |
                    |           +---> TabHeaderComponent (HTML string)
                    |           |
                    |           +---> For each TestResult:
                    |                     |
                    |                     +---> TestCaseBuilder.build(test)
                    |                               |
                    |                               +---> StatusBannerComponent
                    |                               +---> MetadataComponent
                    |                               +---> ReproduceComponent
                    |                               +---> ExpectationsBuilder
                    |                               +---> TimelineBuilder
                    |                               +---> ResponseComponent
                    |                               +---> DebugComponent
                    |                               +---> AssessmentBuilder
                    |
                    +---> AssetManager.get_styles()
                    +---> AssetManager.get_scripts()
                    |
                    +---> Assemble final HTML document
```

---

## 2. Class/Module Structure

### 2.1 Module Organization

```
test-packages/harness/
    html_report/
        __init__.py           # Public API exports
        builder.py            # Main HTMLReportBuilder orchestrator
        components/
            __init__.py
            base.py           # BaseComponent abstract class
            header.py         # HeaderBuilder, HeaderComponent
            tabs.py           # TabsBuilder, TabHeaderComponent
            test_case.py      # TestCaseBuilder (orchestrates sub-components)
            status_banner.py  # StatusBannerBuilder
            metadata.py       # MetadataBuilder
            reproduce.py      # ReproduceBuilder
            expectations.py   # ExpectationsBuilder, ExpectationItemComponent
            timeline.py       # TimelineBuilder, TimelineItemComponent
            response.py       # ResponseBuilder
            debug.py          # DebugBuilder
            assessment.py     # AssessmentBuilder (lazy-loading support)
        assets/
            __init__.py
            manager.py        # AssetManager for CSS/JS
            styles.py         # CSS generation/constants
            scripts.py        # JavaScript generation/constants
        models.py             # HTML-specific Pydantic models (display models)
        utils.py              # HTML escaping, formatting utilities
```

### 2.2 Class Hierarchy

```
BaseComponent (ABC)
    |
    +-- HeaderComponent
    +-- TabsComponent
    +-- StatusBannerComponent
    +-- MetadataComponent
    +-- ReproduceComponent
    +-- ExpectationsComponent
    |       +-- ExpectationItemComponent
    +-- TimelineComponent
    |       +-- TimelineItemComponent
    +-- ResponseComponent
    +-- DebugComponent
    +-- AssessmentComponent

BaseBuilder (ABC)
    |
    +-- HeaderBuilder
    +-- TabsBuilder
    +-- TestCaseBuilder
    +-- StatusBannerBuilder
    +-- MetadataBuilder
    +-- ReproduceBuilder
    +-- ExpectationsBuilder
    +-- TimelineBuilder
    +-- ResponseBuilder
    +-- DebugBuilder
    +-- AssessmentBuilder
```

---

## 3. Builder Pattern Implementation

### 3.1 Base Builder Protocol

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)
H = TypeVar('H', bound=str)  # HTML string

class BaseBuilder(ABC, Generic[T, H]):
    """Abstract base class for all HTML component builders.

    Builders transform Pydantic data models into HTML string components.
    Each builder is responsible for:
    - Validating input data
    - Escaping HTML content safely
    - Generating well-formed HTML fragments
    - Supporting optional configuration
    """

    def __init__(self, config: BuilderConfig | None = None):
        """Initialize builder with optional configuration.

        Args:
            config: Optional configuration for customizing output
        """
        self.config = config or BuilderConfig()

    @abstractmethod
    def build(self, data: T) -> H:
        """Build HTML component from data model.

        Args:
            data: Pydantic model containing component data

        Returns:
            HTML string fragment
        """
        pass

    def validate(self, data: T) -> bool:
        """Validate input data before building.

        Args:
            data: Data to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        if data is None:
            raise ValueError(f"{self.__class__.__name__}: data cannot be None")
        return True


class BuilderConfig(BaseModel):
    """Configuration options for builders."""

    # Editor preferences
    default_editor: str = "vscode"  # vscode, pycharm, or auto
    pycharm_extensions: list[str] = [".py"]

    # Copy button behavior
    include_source_attribution: bool = True
    source_attribution_format: str = "---\nsource: {path}#{fragment}"

    # Collapsible sections
    default_collapsed: bool = True

    # Timeline
    show_elapsed_time: bool = True
    show_sequence_numbers: bool = True

    # Assessment
    enable_lazy_loading: bool = True
    assessment_file_pattern: str = "{test_id}.assessment.md"
```

### 3.2 Concrete Builder Example (TimelineBuilder)

```python
from datetime import datetime
from typing import Sequence
from pydantic import BaseModel

from ..models import TimelineEntry, TimelineEntryType
from .base import BaseBuilder, BuilderConfig
from ..utils import escape_html, format_elapsed_time


class TimelineDisplayModel(BaseModel):
    """Display model for timeline component."""

    entries: list[TimelineEntry]
    timeline_id: str
    tool_call_count: int
    total_duration_ms: int


class TimelineBuilder(BaseBuilder[TimelineDisplayModel, str]):
    """Builds timeline component HTML from timeline entries.

    The timeline displays the chronological sequence of events
    during test execution (prompts, tool calls, responses).

    Example:
        builder = TimelineBuilder()
        html = builder.build(TimelineDisplayModel(
            entries=test_result.timeline,
            timeline_id="timeline-1",
            tool_call_count=6,
            total_duration_ms=13770
        ))
    """

    TYPE_STYLES = {
        TimelineEntryType.PROMPT: ("prompt", "#3b82f6", "Prompt"),
        TimelineEntryType.TOOL_CALL: ("tool_call", "#8b5cf6", None),  # Use tool name
        TimelineEntryType.RESPONSE: ("response", "#10b981", "Response"),
        TimelineEntryType.SUBAGENT_START: ("subagent", "#f59e0b", "Subagent Start"),
        TimelineEntryType.SUBAGENT_STOP: ("subagent", "#f59e0b", "Subagent Stop"),
    }

    def build(self, data: TimelineDisplayModel) -> str:
        """Build timeline HTML from entries."""
        self.validate(data)

        items_html = "\n".join(
            self._build_item(entry) for entry in data.entries
        )

        return f'''
        <details>
          <summary>
            <span class="summary-text">Timeline ({data.tool_call_count} tool calls)</span>
            {self._build_copy_button(data.timeline_id)}
          </summary>
          <div class="content">
            <div class="timeline" id="{data.timeline_id}">
              {items_html}
            </div>
          </div>
        </details>
        '''

    def _build_item(self, entry: TimelineEntry) -> str:
        """Build single timeline item HTML."""
        type_class, color, label = self.TYPE_STYLES.get(
            entry.type,
            ("unknown", "#6b7280", str(entry.type))
        )

        # Use tool name for tool_call type
        display_label = entry.tool if entry.type == TimelineEntryType.TOOL_CALL else label

        elapsed = format_elapsed_time(entry.elapsed_ms)

        content_html = self._build_content(entry)
        intent_html = ""
        if entry.intent:
            intent_html = f'<div class="timeline-intent">{escape_html(entry.intent)}</div>'

        return f'''
        <div class="timeline-item {type_class}" data-seq="{entry.seq}" data-elapsed="{entry.elapsed_ms}ms">
          <div class="timeline-dot"></div>
          <div class="timeline-header">
            <span class="timeline-type">{escape_html(display_label)}</span>
            <div class="timeline-right">
              <span class="timeline-elapsed">{elapsed}</span>
              <span class="timeline-seq">#{entry.seq}</span>
              {self._build_copy_button(f"timeline-item-{entry.seq}", onclick="copyTimelineItem(this)")}
            </div>
          </div>
          <div class="timeline-content">
            {intent_html}
            {content_html}
          </div>
        </div>
        '''

    def _build_content(self, entry: TimelineEntry) -> str:
        """Build content section for timeline entry."""
        if entry.type == TimelineEntryType.PROMPT:
            return f'<pre>{escape_html(entry.content or "")}</pre>'

        if entry.type == TimelineEntryType.TOOL_CALL and entry.input:
            command = entry.input.command or ""
            output = ""
            if entry.output:
                output = entry.output.stdout or entry.output.content or ""
            return f'<pre>$ {escape_html(command)}\n\n{escape_html(output)}</pre>'

        if entry.type == TimelineEntryType.RESPONSE:
            return f'<pre>{escape_html(entry.content or entry.content_preview or "")}</pre>'

        return ""

    def _build_copy_button(self, element_id: str, onclick: str = "") -> str:
        """Build copy button HTML."""
        if not onclick:
            onclick = f"copyTimeline('{element_id}')"

        return f'''
        <button class="copy-icon-btn" data-tooltip="Copy" onclick="event.stopPropagation(); {onclick}">
          <svg class="clipboard" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          <svg class="checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </button>
        '''
```

---

## 4. Pydantic Models for Report Data

### 4.1 Display Models (HTML-specific)

These models wrap the core data models with HTML-specific display attributes.

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, computed_field

from .models import (
    FixtureMeta,
    FixtureSummary,
    TestResult,
    TestStatus,
    TimelineEntry,
    Expectation,
)


class StatusDisplay(BaseModel):
    """Display attributes for status rendering."""

    status: TestStatus

    @computed_field
    @property
    def css_class(self) -> str:
        return self.status.value

    @computed_field
    @property
    def icon_html(self) -> str:
        icons = {
            TestStatus.PASS: "&#10003;",      # Checkmark
            TestStatus.FAIL: "&#10060;",      # X
            TestStatus.PARTIAL: "&#9888;",    # Warning
            TestStatus.SKIPPED: "&#9675;",    # Circle
        }
        return icons.get(self.status, "&#63;")

    @computed_field
    @property
    def label(self) -> str:
        return self.status.value.upper()


class TabDisplay(BaseModel):
    """Display model for a test case tab."""

    tab_id: str
    label: str
    status: StatusDisplay
    is_active: bool = False


class FixtureHeaderDisplay(BaseModel):
    """Display model for fixture header."""

    fixture_name: str
    package: str
    agent_or_skill: str
    agent_link: str | None = None
    fixture_link: str | None = None
    total_tests: int
    passed: int
    failed: int
    partial: int
    skipped: int
    report_path: str
    generated_at: datetime

    @computed_field
    @property
    def summary_text(self) -> str:
        parts = []
        if self.passed > 0:
            parts.append(f"{self.passed} passed")
        if self.failed > 0:
            parts.append(f"{self.failed} failed")
        if self.partial > 0:
            parts.append(f"{self.partial} partial")
        if self.skipped > 0:
            parts.append(f"{self.skipped} skipped")
        return f"{self.total_tests} tests ({', '.join(parts)})"


class ExpectationDisplay(BaseModel):
    """Display model for a single expectation."""

    expectation: Expectation
    index: int

    @computed_field
    @property
    def exp_id(self) -> str:
        return self.expectation.id or f"exp-{self.index + 1:03d}"

    @computed_field
    @property
    def status_display(self) -> StatusDisplay:
        return StatusDisplay(status=self.expectation.status)

    @computed_field
    @property
    def has_details(self) -> bool:
        return bool(self.expectation.actual or self.expectation.failure_reason)

    @computed_field
    @property
    def details_text(self) -> str:
        if self.expectation.status == TestStatus.PASS:
            actual = self.expectation.actual or {}
            if "command" in actual:
                return f"Matched: <code>{actual['command']}</code>"
            if "matched_text" in actual:
                return f"Matched: <code>{actual['matched_text']}</code>"
        elif self.expectation.failure_reason:
            return self.expectation.failure_reason
        return ""


class TestCaseDisplay(BaseModel):
    """Display model for a complete test case tab content."""

    test: TestResult
    tab_index: int
    report_path: str

    @computed_field
    @property
    def tab_id(self) -> str:
        return f"test-{self.tab_index + 1}"

    @computed_field
    @property
    def status_display(self) -> StatusDisplay:
        return StatusDisplay(status=self.test.status)

    @computed_field
    @property
    def expectation_displays(self) -> list[ExpectationDisplay]:
        return [
            ExpectationDisplay(expectation=exp, index=i)
            for i, exp in enumerate(self.test.expectations)
        ]

    @computed_field
    @property
    def passed_count(self) -> int:
        return sum(1 for e in self.test.expectations if e.status == TestStatus.PASS)

    @computed_field
    @property
    def failed_count(self) -> int:
        return len(self.test.expectations) - self.passed_count

    @computed_field
    @property
    def timeline_id(self) -> str:
        return f"timeline-{self.tab_index + 1}"

    @computed_field
    @property
    def tool_call_count(self) -> int:
        from .models import TimelineEntryType
        return sum(1 for e in self.test.timeline if e.type == TimelineEntryType.TOOL_CALL)


class ReportDisplay(BaseModel):
    """Top-level display model for the entire report."""

    fixture: FixtureMeta
    tests: list[TestResult]
    report_path: str

    @computed_field
    @property
    def header_display(self) -> FixtureHeaderDisplay:
        summary = self.fixture.summary
        return FixtureHeaderDisplay(
            fixture_name=self.fixture.fixture_name,
            package=self.fixture.package,
            agent_or_skill=self.fixture.agent_or_skill,
            total_tests=summary.total_tests,
            passed=summary.passed,
            failed=summary.failed,
            partial=summary.partial,
            skipped=summary.skipped,
            report_path=self.report_path,
            generated_at=self.fixture.generated_at,
        )

    @computed_field
    @property
    def tab_displays(self) -> list[TabDisplay]:
        return [
            TabDisplay(
                tab_id=f"test-{i + 1}",
                label=test.tab_label,
                status=StatusDisplay(status=test.status),
                is_active=(i == 0),
            )
            for i, test in enumerate(self.tests)
        ]

    @computed_field
    @property
    def test_case_displays(self) -> list[TestCaseDisplay]:
        return [
            TestCaseDisplay(test=test, tab_index=i, report_path=self.report_path)
            for i, test in enumerate(self.tests)
        ]
```

---

## 5. Component Breakdown

### 5.1 HeaderBuilder

**Purpose:** Renders the fixture-level header with metadata grid.

**Input:** `FixtureHeaderDisplay`

**Output HTML Structure:**
```html
<div class="fixture-header">
  <h1>{fixture_name} Test Suite</h1>
  <div class="fixture-meta">
    <div class="fixture-meta-item">...</div>
    ...
  </div>
</div>
```

**Features:**
- Editor links (VS Code/PyCharm) for file paths
- Summary statistics display
- Report path with clickable link
- Generated timestamp

### 5.2 TabsBuilder

**Purpose:** Renders the tab navigation header.

**Input:** `list[TabDisplay]`

**Output HTML Structure:**
```html
<div class="tabs-container">
  <div class="tabs-header">
    <button class="tab-button active" onclick="switchTab('test-1')">
      <span class="tab-icon pass">&#10003;</span>
      <span>Tab Label</span>
    </button>
    ...
  </div>
  <!-- Tab contents rendered by TestCaseBuilder -->
</div>
```

### 5.3 TestCaseBuilder (Orchestrator)

**Purpose:** Orchestrates sub-builders to render complete test case content.

**Input:** `TestCaseDisplay`

**Sub-builders Used:**
1. `StatusBannerBuilder` - Status banner with pass/fail badge
2. `MetadataBuilder` - Test metadata grid
3. `ReproduceBuilder` - Reproduction commands section
4. `ExpectationsBuilder` - Expectations list with details
5. `TimelineBuilder` - Execution timeline
6. `ResponseBuilder` - Claude's full response (collapsible)
7. `DebugBuilder` - Debug information (collapsible)
8. `AssessmentBuilder` - Agent assessment section (lazy-loadable)

**Output HTML Structure:**
```html
<div id="test-1" class="tab-content active">
  <!-- Status Banner -->
  <div class="status-banner pass">...</div>

  <!-- Metadata -->
  <div class="test-metadata">...</div>

  <!-- Title & Description -->
  <h1>{test_name}</h1>
  <p class="description">{description}</p>

  <!-- Reproduce -->
  <div class="reproduce-section">...</div>

  <!-- Expectations -->
  <div class="section-header">...</div>
  <ul class="expectations-list">...</ul>

  <!-- Timeline (collapsible) -->
  <details>...</details>

  <!-- Response (collapsible) -->
  <details>...</details>

  <!-- Debug (collapsible) -->
  <details>...</details>

  <!-- Assessment (collapsible, lazy-loadable) -->
  <details class="agent-assessment-section">...</details>
</div>
```

### 5.4 ExpectationsBuilder

**Purpose:** Renders the expectations list with pass/fail status.

**Input:** `list[ExpectationDisplay]`

**Features:**
- Pass/fail icons
- Expandable details with expected/actual comparison
- Copy buttons for individual expectations
- Conditional detail toggle visibility

### 5.5 TimelineBuilder

**Purpose:** Renders the execution timeline with tool calls.

**Input:** `TimelineDisplayModel`

**Features:**
- Visual timeline with colored dots
- Sequence numbers and elapsed times
- Intent annotations
- Command and output display
- Copy buttons for timeline items

### 5.6 AssessmentBuilder

**Purpose:** Renders the Agent Assessment section with lazy-loading support.

**Input:** `AssessmentDisplayModel`

**Features:**
- Embedded content OR lazy-loading placeholder
- Markdown rendering (for loaded .assessment.md files)
- AI badge indicator
- Generation metadata display

---

## 6. Agent Assessment Lazy-Loading Strategy

### 6.1 Overview

The Agent Assessment section supports two modes:
1. **Embedded Mode:** Content is rendered directly in the HTML (for `file://` compatibility)
2. **Lazy-Load Mode:** Content is loaded from external `.assessment.md` files

### 6.2 HTML Placeholder Structure

```html
<details class="agent-assessment-section"
         id="agent-assessment-section-{tab_index}"
         data-test-id="{test_id}"
         data-assessment-loaded="false">
  <summary>
    <span class="summary-text">Agent Assessment</span>
    {copy_button}
  </summary>
  <div class="content">
    <div class="agent-assessment" id="agent-assessment-{tab_index}">
      <div class="agent-assessment-header">
        <h3>Agent Assessment <span class="ai-badge">AI Review</span></h3>
        <span class="agent-assessment-meta" id="agent-assessment-meta-{tab_index}">
          <!-- Populated by JS or embedded -->
        </span>
      </div>
      <div class="agent-assessment-content" id="agent-assessment-content-{tab_index}">
        <!-- Either embedded HTML or loading placeholder -->
        <p class="agent-assessment-loading">Loading assessment...</p>
      </div>
    </div>
  </div>
</details>
```

### 6.3 File Naming Convention

Assessment files are searched in order:
1. `{report-name}.assessment.md` - Same directory as report
2. `{test-id}.assessment.md` - Same directory as report
3. `assessments/{report-name}.assessment.md` - Subdirectory
4. `assessments/{test-id}.assessment.md` - Subdirectory

### 6.4 JavaScript Loading Logic

```javascript
function loadAgentAssessments() {
  const sections = document.querySelectorAll('.agent-assessment-section');

  sections.forEach(section => {
    // Skip if already has embedded content
    if (section.dataset.assessmentLoaded === 'true') return;

    const testId = section.dataset.testId;
    const contentEl = section.querySelector('.agent-assessment-content');

    // Try loading from external file
    tryLoadAssessment(testId, contentEl, section);
  });
}

function tryLoadAssessment(testId, contentEl, section) {
  const basePath = getBasePath();
  const files = [
    `${basePath}${getReportName()}.assessment.md`,
    `${basePath}${testId}.assessment.md`,
    `${basePath}assessments/${getReportName()}.assessment.md`,
    `${basePath}assessments/${testId}.assessment.md`,
  ];

  fetchFirstAvailable(files)
    .then(markdown => {
      contentEl.innerHTML = renderMarkdown(markdown);
      section.classList.add('visible');
      section.dataset.assessmentLoaded = 'true';
    })
    .catch(() => {
      // No external file found - hide if no embedded content
      if (!contentEl.innerHTML.trim()) {
        section.classList.remove('visible');
      }
    });
}
```

### 6.5 AssessmentBuilder Implementation

```python
class AssessmentBuilder(BaseBuilder):
    """Builds Agent Assessment section with optional embedded content."""

    def build(self, data: AssessmentDisplayModel) -> str:
        """Build assessment section HTML.

        Args:
            data: Assessment display model with optional embedded content

        Returns:
            HTML string for assessment section
        """
        # Determine visibility class
        visibility = "visible" if data.has_content else ""

        # Build content (either embedded or placeholder)
        if data.embedded_html:
            content = data.embedded_html
            loaded = "true"
        else:
            content = '<p class="agent-assessment-loading">Loading assessment...</p>'
            loaded = "false"

        return f'''
        <details class="agent-assessment-section {visibility}"
                 id="agent-assessment-section-{data.tab_index}"
                 data-test-id="{data.test_id}"
                 data-assessment-loaded="{loaded}">
          <summary>
            <span class="summary-text">Agent Assessment</span>
            {self._build_copy_button(data.tab_index)}
          </summary>
          <div class="content">
            <div class="agent-assessment" id="agent-assessment-{data.tab_index}">
              <div class="agent-assessment-header">
                <h3>Agent Assessment <span class="ai-badge">AI Review</span></h3>
                <span class="agent-assessment-meta" id="agent-assessment-meta-{data.tab_index}">
                  {data.meta_text or ""}
                </span>
              </div>
              <div class="agent-assessment-content" id="agent-assessment-content-{data.tab_index}">
                {content}
              </div>
            </div>
          </div>
        </details>
        '''
```

---

## 7. CSS/JS Modularization Approach

### 7.1 Asset Manager

```python
class AssetManager:
    """Manages CSS and JavaScript assets for HTML reports.

    Supports:
    - Inline embedding (self-contained HTML)
    - External file references
    - Minification (optional)
    """

    def __init__(self, mode: Literal["inline", "external"] = "inline"):
        self.mode = mode
        self._css_modules: list[str] = []
        self._js_modules: list[str] = []

    def register_css(self, module_name: str, css: str) -> None:
        """Register a CSS module."""
        self._css_modules.append((module_name, css))

    def register_js(self, module_name: str, js: str) -> None:
        """Register a JavaScript module."""
        self._js_modules.append((module_name, js))

    def get_style_tag(self) -> str:
        """Get combined CSS in a style tag."""
        if self.mode == "inline":
            combined = "\n".join(css for _, css in self._css_modules)
            return f"<style>\n{combined}\n</style>"
        else:
            # External mode - return link tags
            links = [f'<link rel="stylesheet" href="{name}.css">'
                     for name, _ in self._css_modules]
            return "\n".join(links)

    def get_script_tag(self) -> str:
        """Get combined JavaScript in a script tag."""
        if self.mode == "inline":
            combined = "\n".join(js for _, js in self._js_modules)
            return f"<script>\n{combined}\n</script>"
        else:
            scripts = [f'<script src="{name}.js"></script>'
                       for name, _ in self._js_modules]
            return "\n".join(scripts)
```

### 7.2 CSS Modules

```python
# assets/styles.py

CSS_ROOT_VARS = """
:root {
  --pass: #059669;
  --pass-bg: #d1fae5;
  --fail: #dc2626;
  --fail-bg: #fee2e2;
  --partial: #d97706;
  --partial-bg: #fef3c7;
  --skipped: #6b7280;
  --skipped-bg: #f3f4f6;
  --border: #e5e7eb;
  --bg-subtle: #f9fafb;
  --text: #111827;
  --text-muted: #6b7280;
  --tab-active-bg: #ffffff;
  --tab-inactive-bg: #f3f4f6;
}
"""

CSS_BASE = """
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  color: var(--text);
}
"""

CSS_HEADER = """/* Fixture Header styles */..."""
CSS_TABS = """/* Tab styles */..."""
CSS_STATUS = """/* Status banner styles */..."""
CSS_METADATA = """/* Metadata styles */..."""
CSS_REPRODUCE = """/* Reproduce section styles */..."""
CSS_EXPECTATIONS = """/* Expectations styles */..."""
CSS_TIMELINE = """/* Timeline styles */..."""
CSS_RESPONSE = """/* Response styles */..."""
CSS_DEBUG = """/* Debug styles */..."""
CSS_ASSESSMENT = """/* Assessment styles */..."""
CSS_COPY_BUTTON = """/* Copy button styles */..."""
CSS_COLLAPSIBLE = """/* Collapsible details styles */..."""
CSS_FILE_LINKS = """/* File link styles */..."""
CSS_TOOLTIPS = """/* Tooltip styles */..."""


def get_all_css() -> str:
    """Combine all CSS modules."""
    return "\n".join([
        CSS_ROOT_VARS,
        CSS_BASE,
        CSS_HEADER,
        CSS_TABS,
        CSS_STATUS,
        CSS_METADATA,
        CSS_REPRODUCE,
        CSS_EXPECTATIONS,
        CSS_TIMELINE,
        CSS_RESPONSE,
        CSS_DEBUG,
        CSS_ASSESSMENT,
        CSS_COPY_BUTTON,
        CSS_COLLAPSIBLE,
        CSS_FILE_LINKS,
        CSS_TOOLTIPS,
    ])
```

### 7.3 JavaScript Modules

```python
# assets/scripts.py

JS_UTILITIES = """
// Utility functions
function getEditorUrl(filePath) { ... }
function getEditorType(filePath) { ... }
function createFileLink(filePath, displayText) { ... }
function showCopyFeedback(btn) { ... }
"""

JS_TAB_SWITCHING = """
// Tab switching
function switchTab(tabId) { ... }
"""

JS_COPY_FUNCTIONS = """
// Copy to clipboard functions
function copyElement(elementId) { ... }
function copySection(elementId, sectionTitle) { ... }
function copyExpectation(expId) { ... }
function copyTimelineItem(btn) { ... }
function copyTimeline(timelineId) { ... }
function copyAssessment(elementId) { ... }
"""

JS_EXPECTATION_TOGGLE = """
// Expectation details toggle
function toggleExpectation(id) { ... }
"""

JS_MARKDOWN_RENDERER = """
// Simple markdown to HTML renderer
function renderMarkdown(markdown) { ... }
"""

JS_ASSESSMENT_LOADER = """
// Agent Assessment lazy loading
function loadAgentAssessments() { ... }
function tryFetchAssessment(paths, index, section, contentEl, metaEl) { ... }
"""

JS_INITIALIZATION = """
// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  loadAgentAssessments();

  // Disable no-content toggle buttons
  document.querySelectorAll('.expectation-toggle.no-content').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
  });
});
"""


def get_all_js() -> str:
    """Combine all JavaScript modules."""
    return "\n".join([
        JS_UTILITIES,
        JS_TAB_SWITCHING,
        JS_COPY_FUNCTIONS,
        JS_EXPECTATION_TOGGLE,
        JS_MARKDOWN_RENDERER,
        JS_ASSESSMENT_LOADER,
        JS_INITIALIZATION,
    ])
```

---

## 8. Unit Test Strategy

### 8.1 Test Organization

```
test-packages/harness/tests/html_report/
    __init__.py
    conftest.py              # Shared fixtures
    test_builders/
        __init__.py
        test_header_builder.py
        test_tabs_builder.py
        test_test_case_builder.py
        test_expectations_builder.py
        test_timeline_builder.py
        test_assessment_builder.py
    test_components/
        __init__.py
        test_status_display.py
        test_copy_buttons.py
        test_file_links.py
    test_integration/
        __init__.py
        test_full_report.py
        test_report_output.py
    test_utils/
        __init__.py
        test_html_escaping.py
        test_time_formatting.py
```

### 8.2 Test Fixtures

```python
# conftest.py

import pytest
from datetime import datetime
from harness.models import (
    FixtureReport, FixtureMeta, FixtureSummary, TestResult,
    TestStatus, Expectation, TimelineEntry, TimelineEntryType,
)


@pytest.fixture
def sample_timeline_entry():
    """Create a sample timeline entry for testing."""
    return TimelineEntry(
        seq=1,
        type=TimelineEntryType.TOOL_CALL,
        timestamp=datetime.now(),
        elapsed_ms=45,
        tool="Bash",
        intent="Check file exists",
    )


@pytest.fixture
def sample_expectation_pass():
    """Create a passing expectation for testing."""
    return Expectation(
        id="exp-001",
        description="Tool should be called",
        type=ExpectationType.TOOL_CALL,
        status=TestStatus.PASS,
        expected={"tool": "Bash", "pattern": "cat.*file"},
        actual={"tool": "Bash", "command": "cat file.txt"},
    )


@pytest.fixture
def sample_expectation_fail():
    """Create a failing expectation for testing."""
    return Expectation(
        id="exp-002",
        description="Should output message",
        type=ExpectationType.OUTPUT_CONTAINS,
        status=TestStatus.FAIL,
        expected={"pattern": "success"},
        actual=None,
        failure_reason="Pattern not found in output",
    )


@pytest.fixture
def sample_test_result(sample_expectation_pass, sample_expectation_fail, sample_timeline_entry):
    """Create a sample test result with mixed expectations."""
    return TestResult(
        test_id="test-001",
        test_name="Sample Test",
        tab_label="Sample",
        description="A sample test for testing",
        timestamp=datetime.now(),
        duration_ms=5000,
        status=TestStatus.PARTIAL,
        status_icon=StatusIcon.WARNING,
        pass_rate="1/2",
        expectations=[sample_expectation_pass, sample_expectation_fail],
        timeline=[sample_timeline_entry],
        # ... other required fields
    )


@pytest.fixture
def sample_fixture_report(sample_test_result):
    """Create a sample fixture report."""
    return FixtureReport(
        fixture=FixtureMeta(
            fixture_id="test-fixture",
            fixture_name="Test Fixture",
            package="test-package",
            agent_or_skill="test-command",
            report_path="/path/to/report.html",
            generated_at=datetime.now(),
            summary=FixtureSummary(total_tests=1, passed=0, failed=0, partial=1, skipped=0),
        ),
        tests=[sample_test_result],
    )
```

### 8.3 Builder Tests

```python
# test_builders/test_timeline_builder.py

import pytest
from harness.html_report.components.timeline import TimelineBuilder, TimelineDisplayModel
from harness.models import TimelineEntry, TimelineEntryType


class TestTimelineBuilder:
    """Tests for TimelineBuilder."""

    def test_build_empty_timeline(self):
        """Empty timeline should render without errors."""
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            entries=[],
            timeline_id="timeline-1",
            tool_call_count=0,
            total_duration_ms=0,
        )

        html = builder.build(data)

        assert "timeline" in html
        assert "0 tool calls" in html

    def test_build_with_tool_call(self, sample_timeline_entry):
        """Timeline with tool call should include tool name."""
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            entries=[sample_timeline_entry],
            timeline_id="timeline-1",
            tool_call_count=1,
            total_duration_ms=45,
        )

        html = builder.build(data)

        assert "Bash" in html
        assert "+45ms" in html
        assert "#1" in html

    def test_html_escaping(self):
        """Special characters should be escaped."""
        entry = TimelineEntry(
            seq=1,
            type=TimelineEntryType.PROMPT,
            timestamp=datetime.now(),
            elapsed_ms=0,
            content="<script>alert('xss')</script>",
        )
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            entries=[entry],
            timeline_id="timeline-1",
            tool_call_count=0,
            total_duration_ms=0,
        )

        html = builder.build(data)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_copy_button_included(self, sample_timeline_entry):
        """Copy button should be rendered for each item."""
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            entries=[sample_timeline_entry],
            timeline_id="timeline-1",
            tool_call_count=1,
            total_duration_ms=45,
        )

        html = builder.build(data)

        assert "copy-icon-btn" in html
        assert "copyTimelineItem" in html
```

### 8.4 Integration Tests

```python
# test_integration/test_full_report.py

import pytest
from harness.html_report import HTMLReportBuilder
from harness.models import FixtureReport


class TestFullReportGeneration:
    """Integration tests for complete report generation."""

    def test_generates_valid_html(self, sample_fixture_report):
        """Generated HTML should be well-formed."""
        builder = HTMLReportBuilder()
        html = builder.build(sample_fixture_report)

        assert html.startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "</html>" in html
        assert html.count("<div") == html.count("</div>")

    def test_includes_all_sections(self, sample_fixture_report):
        """Report should include all required sections."""
        builder = HTMLReportBuilder()
        html = builder.build(sample_fixture_report)

        assert "fixture-header" in html
        assert "tabs-container" in html
        assert "status-banner" in html
        assert "reproduce-section" in html
        assert "expectations-list" in html
        assert "timeline" in html

    def test_tab_switching_javascript(self, sample_fixture_report):
        """Tab switching JS should be included."""
        builder = HTMLReportBuilder()
        html = builder.build(sample_fixture_report)

        assert "function switchTab" in html

    def test_assessment_loader_javascript(self, sample_fixture_report):
        """Assessment loader JS should be included."""
        builder = HTMLReportBuilder()
        html = builder.build(sample_fixture_report)

        assert "loadAgentAssessments" in html
```

---

## 9. Example Usage Code

### 9.1 Basic Report Generation

```python
from pathlib import Path
from harness.html_report import HTMLReportBuilder
from harness.models import FixtureReport

# Load fixture report from JSON
report_json = Path("reports/fixture-report.json").read_text()
fixture_report = FixtureReport.model_validate_json(report_json)

# Build HTML report
builder = HTMLReportBuilder()
html = builder.build(fixture_report, report_path="/path/to/output.html")

# Write to file
Path("reports/fixture-report.html").write_text(html)
```

### 9.2 Custom Configuration

```python
from harness.html_report import HTMLReportBuilder, BuilderConfig

# Custom configuration
config = BuilderConfig(
    default_editor="pycharm",
    default_collapsed=False,  # Expand all sections by default
    enable_lazy_loading=False,  # Embed all assessment content
)

builder = HTMLReportBuilder(config=config)
html = builder.build(fixture_report)
```

### 9.3 Building Individual Components

```python
from harness.html_report.components import (
    TimelineBuilder,
    TimelineDisplayModel,
    ExpectationsBuilder,
)

# Build just the timeline
timeline_builder = TimelineBuilder()
timeline_html = timeline_builder.build(TimelineDisplayModel(
    entries=test_result.timeline,
    timeline_id="timeline-custom",
    tool_call_count=len([e for e in test_result.timeline if e.type == "tool_call"]),
    total_duration_ms=test_result.duration_ms,
))

# Build just the expectations
expectations_builder = ExpectationsBuilder()
expectations_html = expectations_builder.build(test_result.expectations)
```

### 9.4 Programmatic Assessment Injection

```python
from harness.html_report import HTMLReportBuilder
from harness.html_report.components import AssessmentBuilder, AssessmentDisplayModel

# Generate assessment content (e.g., via Claude API)
assessment_markdown = """
## Summary
The test demonstrates correct behavior with 4/5 expectations passing.

## Recommendations
- Fix the failing expectation by...
"""

# Build report with embedded assessment
builder = HTMLReportBuilder()
html = builder.build(
    fixture_report,
    assessments={
        "test-001": assessment_markdown,
        "test-002": None,  # Will use lazy-loading
    }
)
```

---

## 10. Migration Plan from Current reporter.py

### 10.1 Migration Phases

```
Phase 1: Foundation (Week 1)
============================
- [ ] Create html_report/ package structure
- [ ] Implement BaseBuilder and BuilderConfig
- [ ] Implement display models
- [ ] Port CSS to modular structure
- [ ] Port JavaScript to modular structure
- [ ] Unit tests for base components

Phase 2: Core Builders (Week 2)
===============================
- [ ] Implement HeaderBuilder
- [ ] Implement TabsBuilder
- [ ] Implement StatusBannerBuilder
- [ ] Implement MetadataBuilder
- [ ] Unit tests for each builder

Phase 3: Content Builders (Week 3)
==================================
- [ ] Implement ReproduceBuilder
- [ ] Implement ExpectationsBuilder
- [ ] Implement TimelineBuilder
- [ ] Implement ResponseBuilder
- [ ] Implement DebugBuilder
- [ ] Unit tests for each builder

Phase 4: Assessment & Integration (Week 4)
==========================================
- [ ] Implement AssessmentBuilder with lazy-loading
- [ ] Implement HTMLReportBuilder orchestrator
- [ ] Integration tests
- [ ] Visual regression testing against example-report-v2.html

Phase 5: Migration & Cleanup (Week 5)
=====================================
- [ ] Update all callers to use new HTMLReportBuilder
- [ ] Deprecate old HTMLReportGenerator
- [ ] Documentation updates
- [ ] Performance benchmarks
```

### 10.2 Backward Compatibility

```python
# harness/reporter.py (maintain backward compatibility)

from .html_report import HTMLReportBuilder as _NewBuilder

# Deprecation warning wrapper
class HTMLReportGenerator:
    """DEPRECATED: Use HTMLReportBuilder from harness.html_report instead."""

    def __init__(self, *args, **kwargs):
        import warnings
        warnings.warn(
            "HTMLReportGenerator is deprecated. "
            "Use HTMLReportBuilder from harness.html_report instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._builder = _NewBuilder(*args, **kwargs)

    def generate(self, fixture_report, **kwargs):
        """Generate HTML report (deprecated interface)."""
        return self._builder.build(fixture_report, **kwargs)
```

### 10.3 Testing Migration

```python
# tests/test_migration.py

def test_new_builder_matches_old_output():
    """New builder should produce equivalent output to old generator."""
    from harness.reporter import HTMLReportGenerator  # Old
    from harness.html_report import HTMLReportBuilder  # New

    # Same fixture report
    fixture_report = load_test_fixture_report()

    # Generate with both
    old_html = HTMLReportGenerator().generate(fixture_report)
    new_html = HTMLReportBuilder().build(fixture_report)

    # Compare structure (not exact match due to formatting)
    old_soup = BeautifulSoup(old_html, 'html.parser')
    new_soup = BeautifulSoup(new_html, 'html.parser')

    # Key elements should match
    assert len(old_soup.select('.tab-content')) == len(new_soup.select('.tab-content'))
    assert len(old_soup.select('.expectation-item')) == len(new_soup.select('.expectation-item'))
    assert len(old_soup.select('.timeline-item')) == len(new_soup.select('.timeline-item'))
```

---

## Appendix A: HTML Template Reference

The target HTML structure is based on `example-report-v2.html`. Key structural elements:

| Section | CSS Class | Description |
|---------|-----------|-------------|
| Header | `.fixture-header` | Dark gradient header with metadata grid |
| Tabs | `.tabs-container`, `.tabs-header`, `.tab-button` | Horizontal tab navigation |
| Tab Content | `.tab-content` | Individual test case content |
| Status Banner | `.status-banner.{status}` | Pass/fail/partial/skipped banner |
| Metadata | `.test-metadata`, `.test-metadata-grid` | Test metadata key-value grid |
| Reproduce | `.reproduce-section` | Dark section with copy-able commands |
| Expectations | `.expectations-list`, `.expectation-item` | List of expectations with details |
| Timeline | `.timeline`, `.timeline-item` | Visual timeline with dots |
| Response | `.response-preview` | Claude's full response |
| Debug | `.debug-table` | Debug info table |
| Assessment | `.agent-assessment-section`, `.agent-assessment` | AI review section |

---

## Appendix B: CSS Color Palette

```css
:root {
  /* Status colors */
  --pass: #059669;       /* Green */
  --pass-bg: #d1fae5;
  --fail: #dc2626;       /* Red */
  --fail-bg: #fee2e2;
  --partial: #d97706;    /* Orange/Amber */
  --partial-bg: #fef3c7;
  --skipped: #6b7280;    /* Gray */
  --skipped-bg: #f3f4f6;

  /* UI colors */
  --border: #e5e7eb;
  --bg-subtle: #f9fafb;
  --text: #111827;
  --text-muted: #6b7280;

  /* Tab colors */
  --tab-active-bg: #ffffff;
  --tab-inactive-bg: #f3f4f6;

  /* Timeline type colors */
  --prompt: #3b82f6;     /* Blue */
  --tool-call: #8b5cf6;  /* Purple */
  --response: #10b981;   /* Emerald */
  --subagent: #f59e0b;   /* Amber */

  /* Assessment colors */
  --assessment-bg: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  --assessment-text: #e0e7ff;
  --assessment-border: #4338ca;
}
```

---

## Appendix C: JavaScript Function Reference

| Function | Purpose |
|----------|---------|
| `switchTab(tabId)` | Switch active tab |
| `copyElement(elementId)` | Copy element text to clipboard |
| `copySection(elementId, title)` | Copy section with attribution |
| `copyExpectation(expId)` | Copy expectation details |
| `copyTimelineItem(btn)` | Copy single timeline item |
| `copyTimeline(timelineId)` | Copy entire timeline |
| `copyAssessment(elementId)` | Copy assessment content |
| `toggleExpectation(id)` | Toggle expectation details |
| `showCopyFeedback(btn)` | Show copy success animation |
| `getEditorUrl(filePath)` | Get VS Code/PyCharm URL |
| `createFileLink(filePath, text)` | Create editor link HTML |
| `renderMarkdown(markdown)` | Convert markdown to HTML |
| `loadAgentAssessments()` | Load external assessment files |
| `tryFetchAssessment(paths, ...)` | Recursive assessment fetcher |

---

*End of Design Document*
