# Security Scanning Guide

## Overview

This guide explains the automated security scanning procedures used in the Synaptic Canvas marketplace. Security scanning helps identify potential vulnerabilities, coding issues, and policy violations before they reach users.

## Purpose

Automated security scanning serves several critical functions:

1. **Early Detection**: Identify security issues during development
2. **Consistent Standards**: Apply uniform security checks across all packages
3. **Risk Reduction**: Prevent vulnerable code from reaching users
4. **Compliance**: Ensure packages meet marketplace security requirements
5. **Transparency**: Provide visibility into security practices

## The Security Scanner

The security scanner is implemented in `scripts/security-scan.sh` and performs six categories of checks:

1. Secrets Detection
2. Script Quality
3. Python Safety
4. Package Documentation
5. License Files
6. Dependency Audit

### Quick Reference

```bash
# Full security scan
./scripts/security-scan.sh

# Quick scan (skip slow checks)
./scripts/security-scan.sh --quick

# JSON output for CI/CD
./scripts/security-scan.sh --json

# Scan single package
./scripts/security-scan.sh --package delay-tasks
```

## Check Categories

### 1. Secrets Detection

**Purpose**: Identify hardcoded credentials, API keys, and other sensitive data

**What It Checks**:
- Hardcoded passwords (`password = "..."`)
- API keys (`api_key = "..."`)
- Secret tokens (`secret = "..."`, `token = "..."`)
- AWS credentials (`AWS_KEY`, `AWS_SECRET`)
- GitHub tokens (`GITHUB_TOKEN`)
- Private keys (`private_key`, `BEGIN PRIVATE KEY`)
- Credentials in markdown documentation

**Why It Matters**:

Hardcoded secrets are a critical security vulnerability. If committed to a repository:
- Credentials are visible to anyone with access
- They remain in git history even if deleted
- Automated scanners can find and exploit them
- Rotating compromised credentials is difficult and expensive

**Common Violations**:

```python
# BAD: Hardcoded API key
api_key = "sk_live_abc123xyz789"

# BAD: Password in configuration
db_password = "MySecretPassword123"

# GOOD: Use environment variables
api_key = os.environ.get('API_KEY')
db_password = os.environ['DB_PASSWORD']
```

```bash
# BAD: Token in script
GITHUB_TOKEN="ghp_abc123xyz789"

# GOOD: Read from secure source
GITHUB_TOKEN="${GITHUB_TOKEN:-$(security find-generic-password -s github-token -w)}"
```

**How to Fix**:

1. **Never commit secrets**: Use environment variables or secure vaults
2. **Use .gitignore**: Exclude config files with secrets
3. **Rotate exposed credentials**: If you accidentally commit a secret, rotate it immediately
4. **Use secret managers**: AWS Secrets Manager, Azure Key Vault, etc.

**False Positives**:

The scanner may flag:
- Example code showing the pattern (not actual secrets)
- Test fixtures with dummy credentials
- Documentation explaining secret handling

To address false positives:
- Make examples obviously fake: `password = "YOUR_PASSWORD_HERE"`
- Add comments: `# Example only, not a real credential`
- Use clearly fake values: `api_key = "test_key_not_real"`

### 2. Script Quality

**Purpose**: Ensure shell scripts follow best practices and are maintainable

**What It Checks**:
- Scripts are executable (`chmod +x`)
- Shellcheck validation (if available)
- Shebang line present (`#!/usr/bin/env bash`)
- Error handling enabled (`set -e` or `set -euo pipefail`)

**Why It Matters**:

Quality shell scripts:
- Fail fast when errors occur (prevent cascading failures)
- Are portable across systems (proper shebang)
- Are discoverable and runnable (executable permission)
- Follow community best practices (shellcheck)

**Shellcheck Integration**:

If [shellcheck](https://github.com/koalaman/shellcheck) is installed, the scanner runs it on all `.sh` files:

```bash
# Install shellcheck
brew install shellcheck  # macOS
apt-get install shellcheck  # Ubuntu
```

Shellcheck catches common issues:
- Unquoted variables
- Incorrect conditionals
- Unsafe word splitting
- Command substitution issues

**Best Practices**:

```bash
#!/usr/bin/env bash
# Good: Portable shebang, strict error handling

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Quote variables to prevent word splitting
file_name="my file.txt"
cat "$file_name"  # GOOD
cat $file_name    # BAD - breaks with spaces

# Use [[ ]] for conditionals (bash)
if [[ -f "$file_name" ]]; then  # GOOD
if [ -f $file_name ]; then      # OK but less robust

# Handle errors explicitly
if ! command; then
    echo "Command failed"
    exit 1
fi
```

**Common Issues**:

```bash
# Missing shebang
# IMPACT: Script may run with wrong shell
# FIX: Add #!/usr/bin/env bash at top

# Not executable
# IMPACT: Must run as "bash script.sh" instead of "./script.sh"
# FIX: chmod +x script.sh

# No error handling
# IMPACT: Script continues after failures
# FIX: Add "set -e" or "set -euo pipefail"
```

### 3. Python Safety

**Purpose**: Detect unsafe Python patterns that could lead to security vulnerabilities

**What It Checks**:
- `eval()` calls - arbitrary code execution
- `exec()` calls - arbitrary code execution
- `shell=True` in subprocess - shell injection risk
- `pickle.loads()` - arbitrary code execution via deserialization

**Why It Matters**:

These patterns can allow attackers to:
- Execute arbitrary code on your system
- Read/modify sensitive files
- Escalate privileges
- Create backdoors

**Unsafe Patterns**:

```python
# 1. eval() - NEVER USE
user_input = "print('hello')"
eval(user_input)  # DANGER: Could be "__import__('os').system('rm -rf /')"

# 2. exec() - NEVER USE
code = request.get('code')
exec(code)  # DANGER: Arbitrary code execution

# 3. shell=True - AVOID
import subprocess
file = user_input
subprocess.call(f"cat {file}", shell=True)  # DANGER: Shell injection

# 4. pickle.loads() - AVOID
import pickle
data = pickle.loads(untrusted_data)  # DANGER: Can execute code during load
```

**Safe Alternatives**:

```python
# Instead of eval() for math
from ast import literal_eval
result = literal_eval("1 + 2")  # Safe: Only evaluates literals

# Instead of exec() for dynamic behavior
# Use: dispatch tables, getattr(), or plugin systems
handlers = {
    'action1': handle_action1,
    'action2': handle_action2
}
handlers[user_choice]()  # Safe: Controlled options

# Instead of shell=True
import subprocess
# Use list arguments (no shell)
subprocess.run(['cat', file])  # Safe: No shell injection

# Instead of pickle
import json
data = json.loads(untrusted_json)  # Safer: Data only, no code
```

**When These Patterns Are Acceptable**:

The scanner may flag legitimate uses in:
- Development/debug scripts (not production)
- Controlled environments with trusted input only
- Legacy code being refactored

If you must use these patterns:
1. Document why it's necessary
2. Validate and sanitize all input
3. Run in isolated environment
4. Add extra security layers (sandboxing, permissions)
5. Plan migration to safer alternatives

### 4. Package Documentation

**Purpose**: Ensure all packages have complete, accurate documentation

**What It Checks**:
- `README.md` exists in each package
- README mentions security
- `LICENSE` file present
- `manifest.yaml` exists and is valid YAML
- `CHANGELOG.md` exists (recommended)

**Why It Matters**:

Complete documentation:
- Helps users understand package purpose and usage
- Provides security information and best practices
- Establishes legal terms (license)
- Tracks changes and versioning (changelog)
- Meets marketplace requirements

**Required Files**:

```
packages/
  your-package/
    README.md        # REQUIRED: Package description, usage
    LICENSE          # REQUIRED: Legal terms
    manifest.yaml    # REQUIRED: Package metadata
    CHANGELOG.md     # RECOMMENDED: Version history
```

**README.md Requirements**:

Must include:
- Package name and brief description
- Installation instructions
- Usage examples
- Security mention (link to SECURITY.md or security section)
- License information

Example:
```markdown
# my-package

Brief description of what it does.

## Installation

\`\`\`bash
python3 tools/sc-install.py install my-package
\`\`\`

## Usage

Examples here...

## Security

See [SECURITY.md](../../SECURITY.md) for security practices.

## License

MIT
```

**manifest.yaml Requirements**:

Must be valid YAML with required fields:

```yaml
name: my-package
version: 1.0.0
description: What it does
author: your-handle
tags: [relevant, tags]

artifacts:
  commands:
    - commands/my-command.md
  skills:
    - skills/my-skill/SKILL.md
```

**Common Issues**:

```
Missing README.md
→ Create README with installation and usage

README exists but no security mention
→ Add security section or link to SECURITY.md

LICENSE missing
→ Copy LICENSE from another package or repo root

manifest.yaml invalid YAML
→ Check syntax with: python3 -m yaml manifest.yaml

CHANGELOG.md missing (warning only)
→ Create CHANGELOG to track version history
```

### 5. License Files

**Purpose**: Ensure all packages have proper legal licensing

**What It Checks**:
- Each package has `LICENSE` file
- LICENSE files are not empty
- Repository root has LICENSE

**Why It Matters**:

License files:
- Define legal terms for package use
- Protect maintainers from liability
- Clarify user rights and obligations
- Meet marketplace and legal requirements
- Enable open source distribution

**License Requirements**:

All Synaptic Canvas packages should use MIT License for consistency:

```
MIT License

Copyright (c) 2025 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

[... full MIT license text ...]
```

**Best Practices**:

1. **Consistent Licensing**: Use same license across all packages
2. **Copy LICENSE**: Each package should have its own LICENSE file
3. **Update Copyright**: Use current year and correct author
4. **Include Full Text**: Don't abbreviate or truncate license
5. **Match README**: LICENSE mentioned in README should match actual file

### 6. Dependency Audit

**Purpose**: Identify vulnerable or outdated dependencies

**What It Checks**:
- npm dependencies (if package.json exists)
- Python dependencies (if requirements.txt exists)
- Git URLs using insecure protocols
- Known vulnerable package versions

**Why It Matters**:

Vulnerable dependencies can:
- Introduce security holes into your packages
- Expose user systems to attacks
- Violate security policies
- Damage reputation and trust

**npm Audit**:

If Node.js packages exist, runs `npm audit`:

```bash
cd project-root
npm audit

# Example output:
# High severity vulnerability in lodash < 4.17.12
# Run npm audit fix to resolve
```

**Python Dependencies**:

Checks for known vulnerable packages:
- pyyaml < 5.4 (YAML parsing vulnerabilities)
- requests < 2.20.0 (Security issues)
- urllib3 < 1.26.5 (Multiple CVEs)

**How to Fix**:

```bash
# Node.js: Auto-fix vulnerabilities
npm audit fix

# Python: Update to safe versions
pip3 install --upgrade pyyaml requests urllib3

# Verify fixes
npm audit  # Should show 0 vulnerabilities
pip3 check  # Should show no issues
```

**Insecure Git URLs**:

```yaml
# BAD: Insecure git:// protocol
dependencies:
  - git://github.com/user/repo.git

# GOOD: Secure https:// protocol
dependencies:
  - https://github.com/user/repo.git
```

**Severity Levels**:

- **HIGH**: Critical vulnerabilities, known exploits, immediate fix required
- **MEDIUM**: Moderate risk, should fix soon
- **LOW**: Minor issues, fix when convenient

## Running Security Scans

### Local Development

Run before committing code:

```bash
# Full scan
./scripts/security-scan.sh

# Quick scan (faster, skips dependency audit)
./scripts/security-scan.sh --quick

# Scan specific package
./scripts/security-scan.sh --package your-package
```

### Continuous Integration

Integrate into CI/CD pipeline:

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run security scan
        run: ./scripts/security-scan.sh --json > scan-results.json
      - name: Check results
        run: |
          if [ $? -ne 0 ]; then
            echo "Security scan failed"
            exit 1
          fi
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: security-scan-results
          path: scan-results.json
```

### Pre-Commit Hooks

Run automatically on commit:

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Running security scan..."
./scripts/security-scan.sh --quick
if [ $? -ne 0 ]; then
    echo "Security scan failed. Commit aborted."
    exit 1
fi
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

### Scheduled Scans

Run weekly to catch new vulnerabilities:

```yaml
# .github/workflows/weekly-security.yml
name: Weekly Security Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday at midnight

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run full security scan
        run: ./scripts/security-scan.sh
```

## Interpreting Results

### Exit Codes

```
0 - All checks passed
1 - Warnings found (non-critical issues)
2 - Failures found (critical issues requiring attention)
```

### Output Format

**Text Output** (default):

```
═══════════════════════════════════════════════════════════
Security Scan Report - 2025-12-04T12:34:56Z
═══════════════════════════════════════════════════════════

✅ Secrets Detection: PASSED (0 potential secrets found)
✅ Script Quality: PASSED (all 3 scripts valid)
✅ Python Safety: PASSED (no unsafe patterns found)
✅ Package Documentation: PASSED (all 4 packages have required docs)
✅ License Files: PASSED (all packages have LICENSE)
⚠️  Dependency Audit: WARNING (2 medium severity warnings)
   [MEDIUM] Check version of requests (known vulnerabilities in old versions)

─────────────────────────────────────────────────────────

OVERALL STATUS: ⚠️  PASSED (with warnings)
Total Issues Found: 2
Scan Date: 2025-12-04T12:34:56Z
```

**JSON Output**:

```json
{
  "scan_date": "2025-12-04T12:34:56Z",
  "overall_status": "WARNING",
  "issues_found": 2,
  "checks": {
    "secrets_detection": "PASSED",
    "script_quality": "PASSED",
    "python_safety": "PASSED",
    "package_documentation": "PASSED",
    "license_files": "PASSED",
    "dependency_audit": "WARNING"
  },
  "scan_configuration": {
    "quick_mode": false,
    "single_package": null,
    "repo_root": "/path/to/repo"
  }
}
```

### Status Indicators

- **PASSED** ✅: No issues found
- **WARNING** ⚠️: Non-critical issues that should be addressed
- **FAILED** ❌: Critical issues requiring immediate attention
- **SKIPPED** ⊘: Check was skipped (e.g., quick mode)

### Issue Severity

- **HIGH**: Critical security risk, fix immediately
- **MEDIUM**: Moderate risk, plan fix soon
- **LOW**: Minor issue, fix when convenient

## Troubleshooting

### Common Issues

**Issue**: "shellcheck: command not found"
```bash
# Scanner works without shellcheck, but install for better checks
brew install shellcheck  # macOS
apt-get install shellcheck  # Ubuntu
```

**Issue**: "npm: command not found"
```bash
# Dependency audit skipped if npm not installed
# Install Node.js to enable npm audit
brew install node  # macOS
```

**Issue**: "Permission denied: ./scripts/security-scan.sh"
```bash
# Make script executable
chmod +x scripts/security-scan.sh
```

**Issue**: "Package not found: my-package"
```bash
# Verify package exists
ls packages/my-package

# Check package name spelling
./scripts/security-scan.sh --package delay-tasks  # Correct name
```

### False Positives

If scan flags legitimate code:

1. **Verify it's actually safe**: Double-check the flagged code
2. **Add comments**: Explain why pattern is acceptable
3. **Refactor if possible**: Use safer alternatives
4. **Document exception**: Note in SECURITY.md why it's necessary

Example:
```python
# This eval() is safe because input is sanitized and validated
# against whitelist before evaluation. Used only for math expressions
# in controlled development environment.
if is_safe_math_expression(user_input):
    result = eval(user_input)
```

## Best Practices

### For Package Authors

1. **Run Before Committing**: Always scan locally before pushing
2. **Fix Issues Promptly**: Don't accumulate security debt
3. **Document Exceptions**: Explain any flagged patterns
4. **Keep Dependencies Updated**: Regular dependency audits
5. **Review Scan Results**: Understand each finding

### For Reviewers

1. **Require Clean Scans**: PRs should pass security scan
2. **Question Exceptions**: Verify documented exceptions are legitimate
3. **Check Fixes**: Ensure issues were actually resolved
4. **Consider Context**: Some warnings acceptable in specific contexts

### For CI/CD

1. **Fail Fast**: Block deployments on security failures
2. **Store Results**: Archive scan results for audit trail
3. **Notify Team**: Alert on new security issues
4. **Trend Analysis**: Track security metrics over time

## Security Scanning Schedule

The security scanner runs:

1. **On Every Release**: Automated scan before package publication
2. **Weekly Scheduled**: Sunday midnight UTC via GitHub Actions
3. **On Pull Requests**: All PRs must pass security scan
4. **Manual Runs**: Developers can run anytime locally

See [SECURITY-SCANNING-SCHEDULE.md](SECURITY-SCANNING-SCHEDULE.md) for detailed schedule.

## Additional Resources

- [SECURITY.md](../SECURITY.md) - Overall security policy
- [PUBLISHER-VERIFICATION.md](PUBLISHER-VERIFICATION.md) - Publisher verification process
- [Shellcheck Documentation](https://github.com/koalaman/shellcheck/wiki)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)

## Questions

For questions about security scanning:

1. Review this guide thoroughly
2. Check scan output for specific guidance
3. See SECURITY.md for general security policy
4. Open GitHub Issue for unresolved questions
