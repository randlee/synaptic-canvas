# Validation Quick Reference

A comprehensive guide to the Synaptic Canvas validation system, providing quick access to all validation scripts, their purposes, and common troubleshooting steps.

## Overview

The Synaptic Canvas validation system ensures consistency, quality, and security across all marketplace artifacts. Validators run both locally during development and automatically in CI/CD pipelines to catch issues before they reach production.

**Key Benefits:**
- Consistent version management across packages
- Security vulnerability detection
- Frontmatter schema compliance
- Cross-reference integrity
- Manifest artifact verification

## Validation Scripts

All validation scripts are located in the `scripts/` directory and follow consistent patterns for exit codes and output formatting.

### Script Reference Table

| Script | Purpose | Exit Codes |
|--------|---------|------------|
| `audit-versions.py` | Check version consistency across the codebase | 0=pass, 1=fail |
| `compare-versions.py` | Compare versions across packages and detect mismatches | 0=pass, 1=fail |
| `validate-agents.py` | Validate agent registry entries and configurations | 0=pass, 1=fail |
| `security-scan.py` | Security scanning for vulnerabilities and sensitive data | 0=pass, 1=warn, 2=fail |
| `validate-manifest-artifacts.py` | Verify manifest artifacts match declared files | 0=pass, 1=fail |
| `validate-marketplace-sync.py` | Check marketplace synchronization status | 0=pass, 1=fail |
| `validate-frontmatter-schema.py` | Validate frontmatter against JSON schemas | 0=pass, 1=fail |
| `validate-script-references.py` | Check that script references resolve correctly | 0=pass, 1=fail |
| `validate-cross-references.py` | Validate cross-references between artifacts | 0=pass, 1=fail |
| `validate-all.py` | Run all validators in sequence | 0=pass, 1=fail |
| `generate-validation-report.py` | Generate comprehensive HTML validation report | 0=success |

### Detailed Script Descriptions

#### audit-versions.py
Scans the codebase for version declarations and ensures consistency.

```bash
python scripts/audit-versions.py [--verbose] [--fix]
```

**Options:**
- `--verbose`: Show detailed output for each version check
- `--fix`: Automatically fix minor version inconsistencies

#### compare-versions.py
Compares version numbers across multiple packages and configuration files.

```bash
python scripts/compare-versions.py [--baseline VERSION]
```

**Options:**
- `--baseline`: Compare against a specific baseline version

#### validate-agents.py
Validates agent registry entries for required fields and proper formatting.

```bash
python scripts/validate-agents.py [--registry PATH]
```

**Options:**
- `--registry`: Path to agent registry file (default: `.claude-plugin/agents/`)

#### security-scan.py
Performs security scanning for vulnerabilities, secrets, and sensitive data exposure.

```bash
python scripts/security-scan.py [--severity LEVEL] [--exclude PATTERN]
```

**Options:**
- `--severity`: Minimum severity to report (low, medium, high, critical)
- `--exclude`: Glob pattern to exclude files from scanning

**Exit Codes:**
- `0`: No security issues found
- `1`: Warnings found (non-blocking)
- `2`: Critical issues found (blocking)

#### validate-manifest-artifacts.py
Verifies that all artifacts declared in manifests exist and are properly configured.

```bash
python scripts/validate-manifest-artifacts.py [--manifest PATH]
```

**Options:**
- `--manifest`: Path to manifest file (default: auto-detect)

#### validate-marketplace-sync.py
Checks that marketplace entries are synchronized with local artifacts.

```bash
python scripts/validate-marketplace-sync.py [--check-remote]
```

**Options:**
- `--check-remote`: Also verify against remote marketplace registry

#### validate-frontmatter-schema.py
Validates frontmatter in all markdown artifacts against JSON schemas.

```bash
python scripts/validate-frontmatter-schema.py [--type TYPE] [--path PATH]
```

**Options:**
- `--type`: Artifact type to validate (command, skill, agent, reference)
- `--path`: Specific path to validate

#### validate-script-references.py
Ensures all script references in artifacts resolve to existing files.

```bash
python scripts/validate-script-references.py [--fix-paths]
```

**Options:**
- `--fix-paths`: Attempt to fix broken path references

#### validate-cross-references.py
Validates cross-references between artifacts, ensuring all links resolve.

```bash
python scripts/validate-cross-references.py [--include-external]
```

**Options:**
- `--include-external`: Also check external URL references

#### validate-all.py
Master script that runs all validators in the correct sequence.

```bash
python scripts/validate-all.py [--stop-on-failure] [--report]
```

**Options:**
- `--stop-on-failure`: Stop immediately on first validation failure
- `--report`: Generate HTML report after validation

#### generate-validation-report.py
Generates a comprehensive HTML report of all validation results.

```bash
python scripts/generate-validation-report.py [--output PATH] [--format FORMAT]
```

**Options:**
- `--output`: Output file path (default: `validation-report.html`)
- `--format`: Output format (html, json, markdown)

## When to Run Each Script

### During Development

| Scenario | Script(s) to Run |
|----------|-----------------|
| Creating a new command | `validate-frontmatter-schema.py`, `validate-manifest-artifacts.py` |
| Creating a new skill | `validate-frontmatter-schema.py`, `validate-script-references.py` |
| Creating a new agent | `validate-agents.py`, `validate-frontmatter-schema.py` |
| Updating versions | `audit-versions.py`, `compare-versions.py` |
| Before committing | `validate-all.py` |
| Before PR submission | `validate-all.py`, `security-scan.py` |

### Before Release

Run the full validation suite:

```bash
python scripts/validate-all.py --report
python scripts/security-scan.py --severity high
```

### CI/CD Pipeline Triggers

| Pipeline Stage | Scripts Run |
|----------------|-------------|
| Pull Request | `validate-all.py`, `security-scan.py` |
| Merge to develop | `validate-all.py`, `security-scan.py --severity medium` |
| Release branch | Full suite with `--strict` flags |
| Production deploy | `validate-all.py`, `security-scan.py --severity low` |

## Common Validation Errors

### Version Mismatch Errors

**Error:** `Version mismatch: package.json (1.2.0) != pyproject.toml (1.1.0)`

**Fix:**
1. Determine the correct version
2. Update all version declarations to match
3. Run `audit-versions.py --fix` for automatic correction

### Frontmatter Schema Errors

**Error:** `Missing required field 'entry_point' in skill frontmatter`

**Fix:**
1. Open the skill file
2. Add the missing `entry_point` field to frontmatter
3. Ensure the path starts with `/`

**Error:** `Invalid value for 'model': expected one of [sonnet, opus, haiku]`

**Fix:**
1. Check the `model` field in agent frontmatter
2. Use only allowed values: `sonnet`, `opus`, or `haiku`

### Manifest Artifact Errors

**Error:** `Declared artifact 'commands/my-command.md' not found`

**Fix:**
1. Verify the file exists at the declared path
2. Check for typos in the manifest entry
3. Create the missing file if needed

### Cross-Reference Errors

**Error:** `Broken reference: skill 'data-processing' references non-existent command 'parse-data'`

**Fix:**
1. Create the missing referenced artifact
2. Or update the reference to point to an existing artifact
3. Or remove the invalid reference

### Security Scan Errors

**Error:** `[HIGH] Potential secret detected in config.py line 42`

**Fix:**
1. Remove the hardcoded secret
2. Use environment variables or secret management
3. Add the file to `.gitignore` if it contains local-only secrets

## CI/CD Integration

### GitHub Actions Integration

The validation suite is integrated into GitHub Actions workflows:

```yaml
# .github/workflows/validate.yml
name: Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run validation suite
        run: python scripts/validate-all.py --report

      - name: Run security scan
        run: python scripts/security-scan.py --severity medium

      - name: Upload validation report
        uses: actions/upload-artifact@v4
        with:
          name: validation-report
          path: validation-report.html
```

### Pre-commit Hook

Add validation to pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-frontmatter
        name: Validate Frontmatter
        entry: python scripts/validate-frontmatter-schema.py
        language: python
        types: [markdown]
```

### Exit Code Handling

All validators return consistent exit codes:

- `0`: Validation passed
- `1`: Validation failed (or warnings for security-scan)
- `2`: Critical failure (security-scan only)

CI pipelines should fail on any non-zero exit code from validators.

## Troubleshooting

### Script Not Found

**Problem:** `python: can't open file 'scripts/validate-all.py'`

**Solution:**
1. Ensure you're running from the repository root
2. Check that scripts directory exists
3. Verify script permissions: `chmod +x scripts/*.py`

### Missing Dependencies

**Problem:** `ModuleNotFoundError: No module named 'jsonschema'`

**Solution:**
```bash
pip install -r requirements.txt
# Or for specific packages:
pip install jsonschema pyyaml
```

### Schema Validation Failures on Valid Files

**Problem:** Frontmatter appears correct but validation fails

**Solution:**
1. Check for invisible characters (copy-paste issues)
2. Verify YAML indentation (spaces, not tabs)
3. Ensure quotes around special characters
4. Run with `--verbose` for detailed error messages

### Slow Validation

**Problem:** Validation takes too long

**Solution:**
1. Use `--path` to validate specific files
2. Use `--type` to validate specific artifact types
3. Run individual validators instead of `validate-all.py`

### False Positives in Security Scan

**Problem:** Security scan flags legitimate code

**Solution:**
1. Add false positives to `.security-ignore`
2. Use `--exclude` to skip specific patterns
3. Add inline comments: `# nosec` (if supported)

### Permissions Errors

**Problem:** `Permission denied` when running scripts

**Solution:**
```bash
chmod +x scripts/*.py
# Or run with python explicitly:
python scripts/validate-all.py
```

## Related Documentation

- [FRONTMATTER-SCHEMA.md](./FRONTMATTER-SCHEMA.md) - Detailed frontmatter schema documentation
- [SECURITY-SCANNING-GUIDE.md](./SECURITY-SCANNING-GUIDE.md) - Security scanning deep dive
- [VERSION-CHECKING-GUIDE.md](./VERSION-CHECKING-GUIDE.md) - Version management guide
- [DEPENDENCY-VALIDATION.md](./DEPENDENCY-VALIDATION.md) - Dependency validation details
