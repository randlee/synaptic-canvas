"""
CSS styles for HTML Report Builder.

This module contains all CSS styles extracted from the target HTML report,
organized by section for modularity and maintainability.
"""

# CSS Variables - :root with all hex values
CSS_VARIABLES = """:root {
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
}"""

# Base styles - body, general styles
CSS_BASE = """* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  color: var(--text);
}

/* Normalize whitespace for copy/paste - prevents excessive newlines when copying text.
   Block elements collapse HTML source whitespace so copied text is clean.
   Pre tags are excluded to preserve intentional code formatting. */
div, p, li, span, h1, h2, h3, h4, h5, h6, td, th, label, summary, button, a {
  white-space: normal;
}

/* Ensure pre and code blocks preserve whitespace for code display */
pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}
code {
  white-space: pre;
}"""

# Fixture header styles
CSS_HEADER = """.fixture-header {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  color: white;
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 24px;
}
.fixture-header h1 {
  margin: 0 0 16px 0;
  font-size: 1.5rem;
}
.fixture-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  font-size: 0.9rem;
}
.fixture-meta-item {
  display: flex;
  flex-direction: column;
}
.fixture-meta-item.wide {
  grid-column: span 2;
}
.fixture-meta-label {
  color: #94a3b8;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.fixture-meta-value {
  color: #f1f5f9;
  font-weight: 500;
}

/* File links in header */
.fixture-meta-value a.file-link {
  color: #93c5fd;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.fixture-meta-value a.file-link:hover {
  color: #bfdbfe;
  text-decoration: underline;
}
.fixture-meta-value a.file-link .link-icon {
  font-size: 0.8em;
  opacity: 0.7;
}"""

# Tab navigation styles
CSS_TABS = """.tabs-container {
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}
.tabs-header {
  display: flex;
  background: var(--tab-inactive-bg);
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
}
.tab-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 3px solid transparent;
  white-space: nowrap;
  transition: all 0.2s;
}
.tab-button:hover {
  background: rgba(255,255,255,0.5);
}
.tab-button.active {
  background: var(--tab-active-bg);
  color: var(--text);
  border-bottom-color: #3b82f6;
}
.tab-icon {
  font-size: 1rem;
}
.tab-icon.pass { color: var(--pass); }
.tab-icon.fail { color: var(--fail); }
.tab-icon.partial { color: var(--partial); }
.tab-icon.skipped { color: var(--skipped); }
.tab-content {
  display: none;
  padding: 24px;
  background: white;
}
.tab-content.active {
  display: block;
}"""

# Status banner styles
CSS_STATUS_BANNER = """.status-banner {
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.status-banner.pass { background: var(--pass-bg); border: 2px solid var(--pass); }
.status-banner.fail { background: var(--fail-bg); border: 2px solid var(--fail); }
.status-banner.partial { background: var(--partial-bg); border: 2px solid var(--partial); }
.status-banner.skipped { background: var(--skipped-bg); border: 2px solid var(--skipped); }
.status-badge {
  font-size: 1.5rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 12px;
}
.status-banner.pass .status-badge { color: var(--pass); }
.status-banner.fail .status-badge { color: var(--fail); }
.status-banner.partial .status-badge { color: var(--partial); }
.status-banner.skipped .status-badge { color: var(--skipped); }
.status-meta {
  text-align: right;
  color: var(--text-muted);
}
.status-meta .duration { font-size: 1.1rem; font-weight: 600; color: var(--text); }"""

# Token display styles for status banner
CSS_TOKEN_DISPLAY = """.token-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.token-summary {
  display: flex;
  gap: 16px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 0.9rem;
}
.token-details {
  margin-top: 8px;
  border: none;
}
.token-details summary {
  font-size: 0.8rem;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 0;
  background: transparent;
  border: none;
  font-weight: normal;
}
.token-details summary:hover {
  color: var(--text);
}
.token-detail {
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--bg-subtle);
  border-radius: 4px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 0.85rem;
}
.token-detail > div {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
}
.token-detail dt {
  color: var(--text-muted);
}
.token-detail dd {
  font-weight: 500;
  margin-left: 8px;
}"""

# Test metadata grid styles
CSS_METADATA = """.test-metadata {
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}
.test-metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.test-metadata-item {
  display: flex;
  flex-direction: column;
}
.test-metadata-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.test-metadata-value {
  font-weight: 500;
  font-size: 0.9rem;
}

/* Section headers with copy buttons */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 28px 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--border);
}
.section-header h2 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}
h1 { margin: 0 0 8px 0; font-size: 1.3rem; }
.description { color: var(--text-muted); margin-bottom: 20px; font-size: 0.95rem; }

/* Cards */
.card {
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.card-title {
  font-weight: 600;
  font-size: 1rem;
}

/* Reproduce Section */
.reproduce-section {
  background: #1e293b;
  color: #e2e8f0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}
.reproduce-section .section-header {
  border-bottom-color: #475569;
  margin-top: 0;
}
.reproduce-section .section-header h2 {
  color: #f8fafc;
}
.reproduce-section pre {
  background: #0f172a;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 0.85rem;
}
.reproduce-step {
  margin-bottom: 16px;
}
.reproduce-step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.reproduce-step-label {
  color: #94a3b8;
  font-weight: 600;
}
.reproduce-section .copy-icon-btn {
  border-color: #475569;
  color: #94a3b8;
}
.reproduce-section .copy-icon-btn:hover {
  background: #334155;
  color: #f1f5f9;
}"""

# Collapsible details/summary with arrow styles
CSS_SECTIONS = """details {
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 16px;
}
details summary {
  padding: 12px 16px;
  cursor: pointer;
  font-weight: 600;
  background: var(--bg-subtle);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
details summary::marker {
  display: none;
}
details summary::-webkit-details-marker {
  display: none;
}
details[open] summary {
  border-bottom: 1px solid var(--border);
  border-radius: 8px 8px 0 0;
}
details .content {
  padding: 16px;
}
.summary-text {
  display: flex;
  align-items: center;
  gap: 8px;
}
.summary-text::before {
  content: '\\25B6';
  font-size: 0.7rem;
  transition: transform 0.2s;
}
details[open] .summary-text::before {
  transform: rotate(90deg);
}"""

# Copy button states and tooltip styles
CSS_COPY_BUTTON = """.copy-icon-btn {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 4px 6px;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 0.9rem;
  line-height: 1;
  transition: all 0.2s;
  position: relative;
}
.copy-icon-btn:hover {
  background: var(--bg-subtle);
  color: var(--text);
  border-color: #94a3b8;
}
.copy-icon-btn:active {
  transform: scale(0.95);
}
.copy-icon-btn.copied {
  color: var(--pass);
  border-color: var(--pass);
}
.copy-icon-btn svg {
  width: 14px;
  height: 14px;
  vertical-align: middle;
}
.copy-icon-btn .checkmark {
  display: none;
}
.copy-icon-btn.copied .clipboard {
  display: none;
}
.copy-icon-btn.copied .checkmark {
  display: inline;
}

/* Tooltip */
[data-tooltip] {
  position: relative;
}
[data-tooltip]:hover::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  padding: 4px 8px;
  background: #1e293b;
  color: white;
  font-size: 0.75rem;
  border-radius: 4px;
  white-space: nowrap;
  z-index: 100;
  margin-bottom: 4px;
}"""

# Expectation table and toggle button styles
CSS_EXPECTATIONS = """.expectations-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.expectation-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 8px;
  background: white;
}
.expectation-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}
.expectation-content { flex: 1; }
.expectation-label { font-weight: 500; }
.expectation-details {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 4px;
}
.expectation-actions {
  display: flex;
  gap: 4px;
  align-items: center;
}
.expectation-toggle {
  background: none;
  border: 1px solid var(--border);
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--text-muted);
}
.expectation-toggle:hover { background: var(--bg-subtle); }
.expectation-toggle.no-content {
  opacity: 0.4;
  cursor: default;
}
.expectation-toggle.no-content:hover {
  background: transparent;
}
.expectation-toggle.has-content {
  color: #3b82f6;
  border-color: #93c5fd;
}
.expectation-expanded {
  margin-top: 12px;
  padding: 12px;
  background: var(--bg-subtle);
  border-radius: 6px;
  font-size: 0.85rem;
  display: none;
}
.expectation-expanded.show { display: block; }
.expected-actual {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.expected-actual h4 {
  margin: 0 0 8px 0;
  font-size: 0.85rem;
  color: var(--text-muted);
}
.expected-actual pre {
  background: white;
  padding: 8px;
  border-radius: 4px;
  margin: 0;
  font-size: 0.8rem;
  overflow-x: auto;
}

/* Pass/Fail counts */
.pass-count { color: var(--pass); font-weight: 600; }
.fail-count { color: var(--fail); font-weight: 600; }"""

# Timeline with ::before line and colored dots
CSS_TIMELINE = """.timeline {
  position: relative;
  padding-left: 24px;
}
.timeline::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--border);
}
.timeline-item {
  position: relative;
  padding: 12px 0 12px 24px;
  border-bottom: 1px solid var(--border);
}
.timeline-item:last-child { border-bottom: none; }
.timeline-dot {
  position: absolute;
  left: -20px;
  top: 16px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
  border: 2px solid var(--border);
}
.timeline-item.prompt .timeline-dot { background: #3b82f6; border-color: #3b82f6; }
.timeline-item.tool_call .timeline-dot { background: #8b5cf6; border-color: #8b5cf6; }
.timeline-item.response .timeline-dot { background: #10b981; border-color: #10b981; }
.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.timeline-type {
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.timeline-item.prompt .timeline-type { color: #3b82f6; }
.timeline-item.tool_call .timeline-type { color: #8b5cf6; }
.timeline-item.response .timeline-type { color: #10b981; }
.timeline-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.timeline-elapsed {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: 'SF Mono', Monaco, monospace;
}
.timeline-seq {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-subtle);
  padding: 2px 8px;
  border-radius: 10px;
}
.timeline-content {
  margin-top: 8px;
}
.timeline-content pre {
  background: var(--bg-subtle);
  padding: 10px;
  border-radius: 6px;
  margin: 8px 0 0 0;
  font-size: 0.85rem;
  overflow-x: auto;
}
.timeline-intent {
  font-style: italic;
  color: var(--text-muted);
  font-size: 0.85rem;
}
.timeline-meta {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-subtle);
  padding: 2px 6px;
  border-radius: 3px;
  margin-bottom: 4px;
  display: inline-block;
}"""

# Timeline tree depth indentation and subagent styles
CSS_TIMELINE_TREE = """/* Timeline tree depth indentation */
.timeline-item.depth-0 { margin-left: 0; }
.timeline-item.depth-1 { margin-left: 24px; border-left: 2px solid #8b5cf6; padding-left: 12px; }
.timeline-item.depth-2 { margin-left: 48px; border-left: 2px solid #a78bfa; padding-left: 12px; }
.timeline-item.depth-3 { margin-left: 72px; border-left: 2px solid #c4b5fd; padding-left: 12px; }
.timeline-item.depth-4 { margin-left: 96px; border-left: 2px solid #ddd6fe; padding-left: 12px; }
.timeline-item.depth-5 { margin-left: 120px; border-left: 2px solid #ede9fe; padding-left: 12px; }

/* Subagent section collapsible */
.subagent-section {
  margin: 8px 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-subtle);
}
.subagent-section > summary {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
}
.subagent-section > summary:hover {
  background: rgba(139, 92, 246, 0.1);
}
.agent-badge {
  background: #8b5cf6;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}
.tool-count {
  color: var(--text-muted);
  font-size: 0.85rem;
}
.subagent-duration {
  font-family: monospace;
  font-size: 0.8rem;
  color: var(--text-muted);
}

/* Timeline item dot colors for subagent context */
.timeline-item.depth-1 .timeline-dot,
.timeline-item.depth-2 .timeline-dot,
.timeline-item.depth-3 .timeline-dot {
  border-color: #8b5cf6;
}

/* Highlighted path for debugging */
.timeline-item.highlighted {
  background: rgba(59, 130, 246, 0.1);
  border-left-color: #3b82f6 !important;
}

/* Agent filter dropdown */
.agent-filter-select {
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg);
  color: var(--text);
  font-size: 0.85rem;
}
"""

# Response preview styles
CSS_RESPONSE = """.response-preview {
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  max-height: 300px;
  overflow-y: auto;
}
.response-preview pre {
  margin: 0;
  white-space: pre-wrap;
  font-size: 0.9rem;
}"""

# Debug table styles
CSS_DEBUG = """.debug-table {
  width: 100%;
  border-collapse: collapse;
}
.debug-table td {
  padding: 8px;
  border: 1px solid var(--border);
}
.debug-table td:first-child {
  font-weight: 600;
  width: 150px;
}
.debug-table a.file-link {
  word-break: break-all;
}"""

# Agent assessment dark theme styles
CSS_ASSESSMENT = """.agent-assessment-section {
  display: none;
}
.agent-assessment-section.visible {
  display: block;
}
.agent-assessment {
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  border-radius: 8px;
  padding: 20px;
  color: #e0e7ff;
}
.agent-assessment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #4338ca;
}
.agent-assessment-header h3 {
  margin: 0;
  color: #c7d2fe;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 8px;
}
.agent-assessment-header .ai-badge {
  background: #4338ca;
  color: #c7d2fe;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.agent-assessment-meta {
  font-size: 0.75rem;
  color: #a5b4fc;
}
.agent-assessment-content {
  line-height: 1.7;
  font-size: 0.9rem;
}
.agent-assessment-content h1,
.agent-assessment-content h2,
.agent-assessment-content h3,
.agent-assessment-content h4 {
  color: #e0e7ff;
  margin-top: 16px;
  margin-bottom: 8px;
}
.agent-assessment-content h1 { font-size: 1.3rem; }
.agent-assessment-content h2 { font-size: 1.1rem; }
.agent-assessment-content h3 { font-size: 1rem; }
.agent-assessment-content h4 { font-size: 0.9rem; }
.agent-assessment-content p {
  margin: 8px 0;
}
.agent-assessment-content ul,
.agent-assessment-content ol {
  margin: 8px 0;
  padding-left: 24px;
}
.agent-assessment-content li {
  margin: 4px 0;
}
.agent-assessment-content code {
  background: rgba(99, 102, 241, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 0.85em;
}
.agent-assessment-content pre {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 0.85rem;
  margin: 12px 0;
}
.agent-assessment-content pre code {
  background: none;
  padding: 0;
}
.agent-assessment-content blockquote {
  border-left: 3px solid #6366f1;
  margin: 12px 0;
  padding-left: 16px;
  color: #c7d2fe;
  font-style: italic;
}
.agent-assessment-content strong {
  color: #f0f0ff;
}
.agent-assessment-content a {
  color: #818cf8;
}
.agent-assessment-content a:hover {
  color: #a5b4fc;
}
.agent-assessment-content hr {
  border: none;
  border-top: 1px solid #4338ca;
  margin: 16px 0;
}
.agent-assessment .copy-icon-btn {
  border-color: #4338ca;
  color: #a5b4fc;
}
.agent-assessment .copy-icon-btn:hover {
  background: #4338ca;
  color: #e0e7ff;
}
.agent-assessment-loading {
  color: #a5b4fc;
  font-style: italic;
}
.agent-assessment-error {
  color: #fca5a5;
  font-style: italic;
}"""

# Plugin verification section styles
CSS_PLUGIN_VERIFICATION = """.plugin-verification-section {
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 20px;
}
.plugin-verification-section > summary {
  padding: 12px 16px;
  cursor: pointer;
  font-weight: 600;
  background: var(--bg-subtle);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.plugin-verification-section[open] > summary {
  border-bottom: 1px solid var(--border);
  border-radius: 8px 8px 0 0;
}
.plugin-summary {
  font-size: 0.85rem;
  padding: 4px 10px;
  border-radius: 4px;
  margin-left: auto;
  margin-right: 8px;
}
.plugin-summary.pass {
  background: var(--pass-bg);
  color: var(--pass);
}
.plugin-summary.fail {
  background: var(--fail-bg);
  color: var(--fail);
}
.plugin-expected {
  margin-bottom: 16px;
}
.plugin-expected code {
  background: #e2e8f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.85rem;
}
.plugin-results {
  margin-top: 12px;
}
.plugin-list {
  margin-top: 8px;
}
.plugin-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 8px;
  background: white;
}
.plugin-item.pass {
  border-left: 3px solid var(--pass);
}
.plugin-item.fail {
  border-left: 3px solid var(--fail);
}
.plugin-status {
  font-size: 1.1rem;
  flex-shrink: 0;
}
.plugin-name {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-weight: 500;
}
.plugin-result {
  font-size: 0.85rem;
  color: var(--text-muted);
}
.plugin-item.pass .plugin-result {
  color: var(--pass);
}
.plugin-item.fail .plugin-result {
  color: var(--fail);
}
.plugin-output {
  width: 100%;
  margin-top: 8px;
  border: none;
  background: transparent;
}
.plugin-output summary {
  font-size: 0.8rem;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 0;
}
.plugin-output pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  overflow-x: auto;
  margin: 8px 0 0 0;
}"""

# Editor link colors
CSS_FILE_LINKS = """a.file-link {
  color: #3b82f6;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
a.file-link:hover {
  color: #2563eb;
  text-decoration: underline;
}
a.file-link .link-icon {
  font-size: 0.85em;
  opacity: 0.6;
}
a.file-link.pycharm .link-icon {
  color: #21d789;
}
a.file-link.vscode .link-icon {
  color: #007acc;
}"""


def get_all_css() -> str:
    """
    Combine all CSS sections into a single stylesheet.

    Returns:
        Complete CSS stylesheet as a string.
    """
    sections = [
        CSS_VARIABLES,
        CSS_BASE,
        CSS_HEADER,
        CSS_FILE_LINKS,
        CSS_TABS,
        CSS_STATUS_BANNER,
        CSS_TOKEN_DISPLAY,
        CSS_METADATA,
        CSS_COPY_BUTTON,
        CSS_EXPECTATIONS,
        CSS_PLUGIN_VERIFICATION,
        CSS_TIMELINE,
        CSS_TIMELINE_TREE,
        CSS_SECTIONS,
        CSS_RESPONSE,
        CSS_DEBUG,
        CSS_ASSESSMENT,
    ]
    return "\n\n".join(sections)
