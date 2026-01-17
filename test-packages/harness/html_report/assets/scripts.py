"""
JavaScript functions for HTML Report Builder.

This module contains all JavaScript code extracted from the target HTML report,
organized by functionality for modularity and maintainability.
"""

# Editor utility functions - getEditorUrl, getEditorType, createFileLink
JS_EDITOR_UTILS = """// Get the report path for source attribution
const reportPath = window.location.pathname || '/path/to/report.html';

/**
 * Get the appropriate editor URL for a file path.
 * - .py files open in PyCharm (URL-encoded path)
 * - All other files open in VS Code
 * @param {string} filePath - Absolute path to the file
 * @returns {string} Editor URL
 */
function getEditorUrl(filePath) {
  const ext = filePath.split('.').pop().toLowerCase();
  if (ext === 'py') {
    return `pycharm://open?file=${encodeURIComponent(filePath)}`;
  }
  return `vscode://file/${filePath}`;
}

/**
 * Get the editor type for a file path.
 * @param {string} filePath - Absolute path to the file
 * @returns {string} 'pycharm' or 'vscode'
 */
function getEditorType(filePath) {
  const ext = filePath.split('.').pop().toLowerCase();
  return ext === 'py' ? 'pycharm' : 'vscode';
}

/**
 * Create a file link element.
 * @param {string} filePath - Absolute path to the file
 * @param {string} displayText - Text to display (optional, defaults to filePath)
 * @returns {string} HTML string for the link
 */
function createFileLink(filePath, displayText) {
  const url = getEditorUrl(filePath);
  const editorType = getEditorType(filePath);
  const editorName = editorType === 'pycharm' ? 'PyCharm' : 'VS Code';
  const text = displayText || filePath;
  return `<a href="${url}" class="file-link ${editorType}" title="Open in ${editorName}">${text}<span class="link-icon">&#8599;</span></a>`;
}"""

# Tab switching function
JS_TAB_SWITCHING = """// Tab switching
function switchTab(tabId) {
  // Hide all tabs
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  document.querySelectorAll('.tab-button').forEach(btn => {
    btn.classList.remove('active');
  });

  // Show selected tab
  document.getElementById(tabId).classList.add('active');
  event.target.closest('.tab-button').classList.add('active');
}"""

# Copy functions with stopPropagation
JS_COPY_FUNCTIONS = """// Copy feedback animation
function showCopyFeedback(btn) {
  btn.classList.add('copied');
  setTimeout(() => {
    btn.classList.remove('copied');
  }, 1500);
}

// Copy element text by ID
function copyElement(elementId) {
  const element = document.getElementById(elementId);
  const text = element.textContent;
  navigator.clipboard.writeText(text).then(() => {
    showCopyFeedback(event.target.closest('.copy-icon-btn'));
  });
}

// Copy section with title and source attribution
function copySection(elementId, sectionTitle) {
  const element = document.getElementById(elementId);
  const content = element.textContent.trim();
  const activeTab = document.querySelector('.tab-content.active');
  const tabId = activeTab ? activeTab.id : 'test-1';
  const fragmentId = elementId;

  const markdown = `## ${sectionTitle}

${content}

---
source: ${reportPath}#${fragmentId}`;

  navigator.clipboard.writeText(markdown).then(() => {
    showCopyFeedback(event.target.closest('.copy-icon-btn'));
  });
}

// Copy expectation
function copyExpectation(expId) {
  const item = document.querySelector(`[data-exp-id="${expId}"]`);
  const label = item.querySelector('.expectation-label').textContent;
  const details = item.querySelector('.expectation-details').textContent;
  const icon = item.querySelector('.expectation-icon').textContent;
  const status = icon.includes('\\u2705') ? 'PASS' : (icon.includes('\\u274C') ? 'FAIL' : 'WARNING');

  let markdown = `### Expectation: ${label}

**Status:** ${status}
**Details:** ${details}`;

  const expanded = item.querySelector('.expectation-expanded');
  if (expanded && expanded.innerHTML.trim()) {
    const expectedPre = expanded.querySelector('.expected-actual > div:first-child pre');
    const actualPre = expanded.querySelector('.expected-actual > div:last-child pre');
    if (expectedPre && actualPre) {
      markdown += `

**Expected:**
\\`\\`\\`
${expectedPre.textContent.trim()}
\\`\\`\\`

**Actual:**
\\`\\`\\`
${actualPre.textContent.trim()}
\\`\\`\\``;
    }
  }

  markdown += `

---
source: ${reportPath}#${expId}`;

  navigator.clipboard.writeText(markdown).then(() => {
    showCopyFeedback(event.target.closest('.copy-icon-btn'));
  });
}

// Copy timeline item
function copyTimelineItem(btn) {
  const item = btn.closest('.timeline-item');
  const type = item.querySelector('.timeline-type').textContent;
  const seq = item.querySelector('.timeline-seq').textContent;
  const elapsed = item.querySelector('.timeline-elapsed').textContent;
  const intent = item.querySelector('.timeline-intent');
  const pre = item.querySelector('.timeline-content pre');

  let markdown = `### Timeline ${seq}: ${type} (${elapsed})`;

  if (intent) {
    markdown += `\\n**Intent:** ${intent.textContent}`;
  }

  if (pre) {
    markdown += `\\n\\n\\`\\`\\`\\n${pre.textContent.trim()}\\n\\`\\`\\``;
  }

  markdown += `

---
source: ${reportPath}#timeline-item-${item.dataset.seq}`;

  navigator.clipboard.writeText(markdown).then(() => {
    showCopyFeedback(btn);
  });
}

// Copy entire timeline
function copyTimeline(timelineId) {
  const timeline = document.getElementById(timelineId);
  const items = timeline.querySelectorAll('.timeline-item');

  let markdown = `## Timeline\\n\\n`;

  items.forEach(item => {
    const type = item.querySelector('.timeline-type').textContent;
    const seq = item.querySelector('.timeline-seq').textContent;
    const elapsed = item.querySelector('.timeline-elapsed').textContent;
    const intent = item.querySelector('.timeline-intent');
    const pre = item.querySelector('.timeline-content pre');

    markdown += `### ${seq}: ${type} (${elapsed})\\n`;

    if (intent) {
      markdown += `**Intent:** ${intent.textContent}\\n`;
    }

    if (pre) {
      markdown += `\\n\\`\\`\\`\\n${pre.textContent.trim()}\\n\\`\\`\\`\\n`;
    }

    markdown += `\\n`;
  });

  markdown += `---
source: ${reportPath}#${timelineId}`;

  navigator.clipboard.writeText(markdown).then(() => {
    showCopyFeedback(event.target.closest('.copy-icon-btn'));
  });
}

// Copy assessment content
function copyAssessment(elementId) {
  const contentEl = document.getElementById(elementId.replace('agent-assessment', 'agent-assessment-content'));
  const metaEl = document.getElementById(elementId.replace('agent-assessment', 'agent-assessment-meta'));

  let markdown = `## Agent Assessment\\n\\n`;
  if (metaEl && metaEl.textContent) {
    markdown += `*${metaEl.textContent}*\\n\\n`;
  }
  // Get the raw markdown if stored, otherwise extract text
  const rawMarkdown = contentEl.dataset.rawMarkdown || contentEl.textContent;
  markdown += rawMarkdown;

  markdown += `\\n\\n---\\nsource: ${reportPath}#${elementId}`;

  navigator.clipboard.writeText(markdown).then(() => {
    showCopyFeedback(event.target.closest('.copy-icon-btn'));
  });
}"""

# Toggle functions - toggleExpectation
JS_TOGGLE_FUNCTIONS = """// Toggle expectation details
function toggleExpectation(id) {
  const element = document.getElementById(id);
  if (element) {
    element.classList.toggle('show');
  }
}"""

# Markdown renderer - renderMarkdown function
JS_MARKDOWN_RENDERER = """/**
 * Simple markdown to HTML renderer.
 * Handles common markdown syntax: headers, bold, italic, code, lists, links, blockquotes.
 * @param {string} markdown - The markdown text to render
 * @returns {string} HTML string
 */
function renderMarkdown(markdown) {
  let html = markdown;

  // Escape HTML entities first (but not in code blocks)
  html = html.replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // Code blocks (```...```)
  html = html.replace(/```(\\w*)\\n([\\s\\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
  });

  // Inline code (`...`)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headers (# through ####)
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold (**...**)
  html = html.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');

  // Italic (*...*)
  html = html.replace(/\\*([^*]+)\\*/g, '<em>$1</em>');

  // Links [text](url)
  html = html.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2" target="_blank">$1</a>');

  // Horizontal rules (--- or ***)
  html = html.replace(/^(---|\\*\\*\\*)$/gm, '<hr>');

  // Blockquotes (> ...)
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  // Merge consecutive blockquotes
  html = html.replace(/<\\/blockquote>\\n<blockquote>/g, '\\n');

  // Unordered lists (- item)
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  // Wrap consecutive <li> elements in <ul>
  html = html.replace(/(<li>.*<\\/li>\\n?)+/g, (match) => {
    return '<ul>' + match + '</ul>';
  });

  // Ordered lists (1. item, 2. item, etc.)
  html = html.replace(/^\\d+\\. (.+)$/gm, '<li>$1</li>');

  // Paragraphs - wrap text blocks that aren't already wrapped
  html = html.split('\\n\\n').map(block => {
    block = block.trim();
    if (!block) return '';
    // Don't wrap if it's already an HTML element
    if (/^<(h[1-4]|ul|ol|li|pre|blockquote|hr|p)/.test(block)) {
      return block;
    }
    // Wrap in paragraph
    return '<p>' + block.replace(/\\n/g, '<br>') + '</p>';
  }).join('\\n');

  return html;
}"""

# Assessment lazy loader - loadAgentAssessments, tryFetchAssessment
JS_ASSESSMENT_LOADER = """/**
 * Load and render assessment markdown files for all assessment sections.
 * Looks for files named {report-name}.assessment.md or {test-id}.assessment.md
 */
function loadAgentAssessments() {
  // Get the base path for the report
  const currentPath = window.location.pathname;
  const basePath = currentPath.substring(0, currentPath.lastIndexOf('/') + 1);
  const reportName = currentPath.substring(currentPath.lastIndexOf('/') + 1).replace('.html', '');

  // Find all assessment sections
  const assessmentSections = document.querySelectorAll('.agent-assessment-section');

  assessmentSections.forEach(section => {
    const testId = section.dataset.testId;
    const contentEl = section.querySelector('.agent-assessment-content');
    const metaEl = section.querySelector('.agent-assessment-meta');

    // Try multiple file naming conventions
    const filesToTry = [
      `${basePath}${reportName}.assessment.md`,           // {report-name}.assessment.md
      `${basePath}${testId}.assessment.md`,               // {test-id}.assessment.md
      `${basePath}assessments/${reportName}.assessment.md`, // assessments/{report-name}.assessment.md
      `${basePath}assessments/${testId}.assessment.md`    // assessments/{test-id}.assessment.md
    ];

    // Try each file path until one succeeds
    tryFetchAssessment(filesToTry, 0, section, contentEl, metaEl);
  });
}

/**
 * Recursively try to fetch assessment files from a list of paths
 */
function tryFetchAssessment(paths, index, section, contentEl, metaEl) {
  if (index >= paths.length) {
    // No assessment file found via fetch - but check if content is already embedded
    // Don't hide if content already exists (e.g., embedded for file:// compatibility)
    if (contentEl.children.length === 0 && !contentEl.textContent.trim()) {
      section.classList.remove('visible');
    }
    return;
  }

  fetch(paths[index])
    .then(response => {
      if (!response.ok) {
        throw new Error('Not found');
      }
      return response.text();
    })
    .then(markdown => {
      // Successfully loaded assessment
      contentEl.dataset.rawMarkdown = markdown;
      contentEl.innerHTML = renderMarkdown(markdown);
      section.classList.add('visible');

      // Try to extract metadata from the markdown (look for YAML frontmatter)
      const frontmatterMatch = markdown.match(/^---\\n([\\s\\S]*?)\\n---/);
      if (frontmatterMatch) {
        const frontmatter = frontmatterMatch[1];
        const generatedBy = frontmatter.match(/generated_by:\\s*(.+)/);
        const timestamp = frontmatter.match(/timestamp:\\s*(.+)/);
        if (generatedBy || timestamp) {
          let metaText = [];
          if (generatedBy) metaText.push(`Generated by ${generatedBy[1]}`);
          if (timestamp) metaText.push(timestamp[1]);
          metaEl.textContent = metaText.join(' | ');
        }
      }
    })
    .catch(() => {
      // Try next path
      tryFetchAssessment(paths, index + 1, section, contentEl, metaEl);
    });
}"""

# Initialization - DOMContentLoaded setup, no-content prevention
JS_INITIALIZATION = """// Prevent toggle buttons with no content from doing anything
document.querySelectorAll('.expectation-toggle.no-content').forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
  });
});

// Load assessments when the page loads
document.addEventListener('DOMContentLoaded', loadAgentAssessments);

// Also try loading immediately in case DOMContentLoaded already fired
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  loadAgentAssessments();
}"""


def get_all_scripts() -> str:
    """
    Combine all JavaScript sections into a single script block.

    Returns:
        Complete JavaScript code as a string.
    """
    sections = [
        JS_EDITOR_UTILS,
        JS_TAB_SWITCHING,
        JS_COPY_FUNCTIONS,
        JS_TOGGLE_FUNCTIONS,
        JS_MARKDOWN_RENDERER,
        JS_ASSESSMENT_LOADER,
        JS_INITIALIZATION,
    ]
    return "\n\n".join(sections)
