# Pytest HTML Reporter Comparison

**Sprint 3 - Publishing Validation Enhancement**
**Date:** 2026-01-19
**Purpose:** Evaluate pytest HTML reporters for integration with validation reports

---

## Executive Summary

After testing three pytest HTML reporters, **pytest-html** is the clear recommendation for Sprint 3. It is the only reporter that:
- Works reliably with modern Python (3.11+) and pytest 9.x
- Is actively maintained (last release: Jan 2026)
- Provides self-contained HTML output
- Offers robust filtering, sorting, and collapsible sections

The other two reporters (pytest-html-reporter and pytest-reporter-html1) have compatibility issues with current Python/pytest versions.

---

## Reporters Tested

| Reporter | Version | Last Release | Python Support | Downloads/Month |
|----------|---------|--------------|----------------|-----------------|
| pytest-html | 4.2.0 | Jan 2026 | 3.9-3.14 | ~1.2M |
| pytest-html-reporter | 0.2.9 | Feb 2022 | 3.5+ | ~50K |
| pytest-reporter-html1 | 0.9.5 | Oct 2025 | 3.10+ | ~10K |

---

## 1. pytest-html (RECOMMENDED)

### Installation
```bash
pip install pytest-html
```

### Command Line Options
```bash
# Basic usage
pytest --html=report.html

# Self-contained (all CSS/JS embedded)
pytest --html=report.html --self-contained-html

# With custom CSS
pytest --html=report.html --css=custom.css
```

### Report Features
- **Expandable test details**: Click any test row to expand/collapse output
- **Status filtering**: Checkbox filters for passed/failed/skipped/xfailed/error
- **Sortable columns**: Sort by Result, Test name, or Duration
- **Collapse all/Expand all**: Quick buttons to toggle all test details
- **Environment metadata**: Shows Python version, platform, installed packages
- **ANSI color support**: Terminal colors preserved in output
- **Self-contained option**: Single HTML file with embedded CSS/JS

### Generated Report Size
- 68 tests (all passing): **116 KB**
- 6 tests (mixed outcomes): **72 KB**

### Visual Appearance
- Clean, professional styling
- Color-coded status badges (green=pass, red=fail, orange=skip)
- Readable monospace font for test output
- Responsive table layout
- Clear test hierarchy display

### Cross-Linking Capabilities
- Test IDs include full module path (e.g., `tests/scripts/test_audit_versions.py::test_name`)
- Can add custom links via pytest hooks (`pytest_html_results_table_header`, `pytest_html_results_table_row`)
- Supports extras (images, URLs, text) attached to test results

### Pros
- Most popular and well-maintained
- Works with pytest 9.x and Python 3.14
- Self-contained HTML option for easy sharing
- Extensive customization via hooks
- Official pytest-dev project
- Good documentation

### Cons
- Slightly larger file size due to embedded resources
- No built-in dark mode
- No test search functionality

---

## 2. pytest-html-reporter

### Installation
```bash
pip install pytest-html-reporter
```

### Command Line Options
```bash
pytest --html-report=./reports --title="My Report"
```

### Compatibility Status: FAILED

**Critical Issue:** Incompatible with pytest 9.x

```
AttributeError: 'TerminalReporter' object has no attribute '_sessionstarttime'.
Did you mean: '_session_start'?
```

The plugin uses deprecated pytest internals that were changed in recent pytest versions.

### Report Features (from documentation)
- Pie charts for test distribution
- Historical trend tracking
- Screenshot attachment support
- Suite-level grouping

### Maintenance Status
- **Last release:** February 2022 (nearly 4 years old)
- **Open issues:** Multiple compatibility issues reported
- **Not recommended** due to lack of maintenance

### Pros
- Rich visual features (charts, trends)
- Screenshot support for UI testing

### Cons
- **BROKEN** with modern pytest versions
- No recent maintenance
- Uses deprecated pytest APIs

---

## 3. pytest-reporter-html1

### Installation
```bash
pip install pytest-reporter-html1
```

### Command Line Options
```bash
pytest --template=html1 --report=report.html
pytest --template=html1 --report=report.html --split-report  # Separate CSS
```

### Compatibility Status: PARTIAL FAILURE

**Issue:** Template loading fails in multi-Python environments

```
UserWarning: No template found with name 'html1'
```

The plugin's template discovery mechanism has issues with:
- Complex virtual environments
- Multiple Python versions in the same venv
- Indirect plugin loading

### Report Features (from documentation)
- Clean, modern design
- Multi-page reports (index + per-module pages)
- RST docstring rendering
- ANSI color conversion
- Custom Jinja2 templates

### Maintenance Status
- **Last release:** October 2025 (recent)
- **Actively maintained** but with edge case bugs

### Pros
- Modern, clean design
- Flexible Jinja2 templating
- Active development

### Cons
- Template discovery issues
- Requires pytest-reporter base plugin
- More complex setup
- Less documentation

---

## Feature Comparison Matrix

| Feature | pytest-html | pytest-html-reporter | pytest-reporter-html1 |
|---------|------------|---------------------|----------------------|
| Works with pytest 9.x | YES | NO | PARTIAL |
| Works with Python 3.14 | YES | NO | PARTIAL |
| Self-contained HTML | YES | YES | YES |
| Filtering | YES | YES | YES |
| Sorting | YES | NO | YES |
| Collapsible sections | YES | YES | YES |
| Search | NO | YES | NO |
| Screenshots | Via hooks | Built-in | Via extras |
| Charts/Trends | NO | YES | NO |
| Custom templates | Via hooks | Limited | Jinja2 |
| Cross-linking | Via hooks | Limited | Via templates |
| Active maintenance | YES | NO | YES |

---

## Sample Reports Generated

| File | Reporter | Size | Tests | Status |
|------|----------|------|-------|--------|
| `sample-pytest-html.html` | pytest-html | 116 KB | 68 | All Pass |
| `sample-pytest-html-failures.html` | pytest-html | 72 KB | 6 | Mixed |

---

## Recommendation

### Primary Choice: **pytest-html**

**Rationale:**
1. **Reliability**: Only reporter that works consistently with current Python/pytest versions
2. **Maintenance**: Actively maintained by pytest-dev team with releases in 2026
3. **Features**: Provides all essential features (filtering, sorting, collapsible details)
4. **Self-contained**: Single HTML file for easy sharing and archival
5. **Extensibility**: Hook-based customization for cross-linking with validation reports
6. **Community**: Large user base (1.2M downloads/month) ensures issues get fixed quickly

### Integration with Validation Reports

For Sprint 3 cross-linking with validation reports:

```python
# conftest.py
import pytest

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    # Add link to validation report
    if hasattr(item, 'validation_report_path'):
        report.extra = getattr(report, 'extra', [])
        report.extra.append(pytest_html.extras.url(
            item.validation_report_path,
            name='Validation Report'
        ))
```

### Installation for Sprint 3

```bash
pip install pytest-html>=4.2.0
```

### Recommended pytest.ini Configuration

```ini
[pytest]
addopts = --html=reports/pytest-report.html --self-contained-html
```

---

## Appendix: Test Commands Used

```bash
# pytest-html (SUCCESS)
pytest tests/scripts/test_audit_versions.py -v \
    --html=reports/pytest-comparison/sample-pytest-html.html \
    --self-contained-html

# pytest-html-reporter (FAILED - compatibility issue)
pytest tests/scripts/test_audit_versions.py -v \
    -p pytest_html_reporter.plugin \
    --html-report=reports/pytest-comparison/sample-html-reporter

# pytest-reporter-html1 (FAILED - template not found)
pytest tests/scripts/test_audit_versions.py -v \
    --template=html1 \
    --report=reports/pytest-comparison/sample-reporter-html1.html
```
