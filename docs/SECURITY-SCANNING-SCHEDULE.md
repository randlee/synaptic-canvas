# Security Scanning Schedule

## Overview

This document outlines when and how security scans are performed on the Synaptic Canvas marketplace repository. Automated security scanning is a key component of our security commitment, helping identify vulnerabilities early and maintain package quality.

## Scan Types

### Full Security Scan

**What It Includes**:
- Secrets detection
- Script quality checks
- Python safety analysis
- Package documentation verification
- License file validation
- Complete dependency audit

**Duration**: ~2-5 minutes depending on repository size

**Command**: `./scripts/security-scan.sh`

### Quick Scan

**What It Includes**:
- Secrets detection
- Script quality checks
- Python safety analysis
- Package documentation verification
- License file validation

**Excludes**: Dependency audit (time-consuming)

**Duration**: ~30-60 seconds

**Command**: `./scripts/security-scan.sh --quick`

## Scan Schedule

### 1. On Every Release (Automated)

**Trigger**: Git tag creation or version bump

**Type**: Full security scan

**Purpose**: Ensure no security issues in released versions

**Process**:
1. Version bump or tag detected
2. Automated CI/CD pipeline triggered
3. Full security scan executed
4. Results recorded in artifacts
5. Release blocked if critical issues found

**Pass Criteria**:
- No HIGH severity issues
- Zero hardcoded secrets
- All packages have required documentation
- All license files present

**Failure Action**:
- Release blocked
- Maintainer notified
- Issues must be fixed before retry

### 2. Weekly Scheduled Scans (Automated)

**Schedule**: Every Sunday at 00:00 UTC

**Type**: Full security scan

**Purpose**: Catch newly discovered vulnerabilities in dependencies

**Process**:
1. GitHub Actions cron trigger
2. Full security scan on main branch
3. Results compared to previous week
4. Report generated and archived
5. Notifications sent if new issues found

**Why Weekly**:
- New CVEs published regularly
- Dependencies may become vulnerable over time
- Catch configuration drift
- Maintain security baseline

**Notification**:
- GitHub Issues created for new HIGH severity
- Summary in weekly repository digest
- Archived in repository Actions tab

### 3. On Pull Requests (Automated)

**Trigger**: PR opened or updated

**Type**: Quick scan + targeted full scan on changed files

**Purpose**: Prevent security regressions

**Process**:
1. PR created or updated
2. Quick scan runs immediately
3. Changed packages get full scan
4. Results posted as PR comment
5. Checks must pass for merge

**Checked**:
- Only changed files and packages
- No new secrets introduced
- Script quality maintained
- Documentation updated appropriately

**Pass Criteria**:
- Quick scan passes
- No new HIGH severity issues
- All checks green

**Developer Experience**:
- Fast feedback (< 2 minutes)
- Clear actionable results
- Blockers explained with remediation

### 4. Manual On-Demand Scans

**Trigger**: Developer runs script locally

**Type**: Full or quick (developer choice)

**Purpose**: Pre-commit validation, troubleshooting

**Process**:
```bash
# Full scan
./scripts/security-scan.sh

# Quick scan
./scripts/security-scan.sh --quick

# Single package
./scripts/security-scan.sh --package delay-tasks

# JSON output
./scripts/security-scan.sh --json > results.json
```

**When to Run**:
- Before committing changes
- After dependency updates
- When troubleshooting issues
- Before opening PR

**Best Practice**: Run quick scan pre-commit, full scan pre-PR

### 5. Post-Incident Scans

**Trigger**: Security incident or vulnerability report

**Type**: Comprehensive audit (full scan + manual review)

**Purpose**: Verify fix completeness and identify related issues

**Process**:
1. Incident reported or detected
2. Immediate targeted scan
3. Fix developed and applied
4. Full scan to verify fix
5. Extended manual review
6. Additional targeted scans

**Scope**:
- All packages (not just affected)
- Historical commits if needed
- Related code patterns
- Documentation accuracy

## What Is Checked

### Secrets Detection

**Frequency**: Every scan (full and quick)

**What We Look For**:
- Hardcoded passwords
- API keys and tokens
- AWS/cloud credentials
- Private keys
- Database connection strings
- OAuth secrets

**Tools**:
- Pattern matching (regex)
- Common secret formats
- Configuration file scanning

**Impact**: HIGH severity, immediate fix required

### Script Quality

**Frequency**: Every scan (full and quick)

**What We Check**:
- Executable permissions
- Shebang lines present
- Error handling (`set -e`)
- Shellcheck validation (if available)

**Tools**:
- Shellcheck
- Custom validation scripts
- Permission checks

**Impact**: MEDIUM severity, fix before release

### Python Safety

**Frequency**: Every scan (full and quick)

**What We Check**:
- `eval()` and `exec()` calls
- `shell=True` in subprocess
- `pickle.loads()` usage
- Unsafe deserialization

**Tools**:
- Pattern matching
- AST analysis (future)

**Impact**: HIGH severity, immediate fix required

### Package Documentation

**Frequency**: Every scan (full and quick)

**What We Verify**:
- README.md exists
- Security section in README
- LICENSE file present
- manifest.yaml valid
- CHANGELOG.md exists (recommended)

**Tools**:
- File existence checks
- YAML validation
- Content validation

**Impact**: HIGH for missing LICENSE, MEDIUM for others

### License Files

**Frequency**: Every scan (full and quick)

**What We Check**:
- LICENSE in each package
- LICENSE not empty
- Repository root LICENSE

**Tools**:
- File existence checks
- Size validation

**Impact**: HIGH severity, required for distribution

### Dependency Audit

**Frequency**: Full scans only (weekly, release, post-incident)

**What We Check**:
- npm vulnerabilities
- Python package vulnerabilities
- Outdated dependencies
- Insecure git URLs

**Tools**:
- `npm audit`
- Known vulnerability databases
- Version checking

**Impact**: Varies by severity (HIGH to LOW)

## How Results Are Published

### For Automated Scans

**Location**: GitHub Actions Artifacts

**Format**: JSON + text report

**Retention**: 90 days

**Access**:
```bash
# Via GitHub CLI
gh run list --workflow=security-scan.yml
gh run view RUN_ID
gh run download RUN_ID
```

### For PR Scans

**Location**: PR comments

**Format**: Formatted text with status emojis

**Content**:
- Summary of checks
- Failed checks with details
- Remediation guidance
- Links to documentation

**Example**:
```
🔍 Security Scan Results

✅ Secrets Detection: PASSED
✅ Script Quality: PASSED
❌ Python Safety: FAILED (2 issues)
   - eval() call in packages/example/script.py:42

Please fix the issues above before merging.
```

### For Release Scans

**Location**:
- GitHub Release notes
- CI/CD logs
- Archived artifacts

**Format**:
- Summary in release notes
- Full report in artifacts

**Example Release Note**:
```
## Security

✅ All security scans passed
- 0 secrets detected
- 0 unsafe code patterns
- All documentation current
- All dependencies secure

View full scan results in CI artifacts.
```

### For Weekly Scans

**Location**:
- GitHub Issues (if problems found)
- Repository Actions tab
- Archived artifacts

**Format**:
- Issue created for new problems
- Weekly summary report

**Example Issue**:
```
Title: [Security] Weekly Scan Found 2 New Issues

Weekly security scan on 2025-12-04 found:

1. HIGH: New npm vulnerability in lodash < 4.17.12
   - Package: lodash
   - Severity: High
   - Fix: Update to 4.17.12+

2. MEDIUM: Shellcheck warning in scripts/example.sh
   - Line 42: Unquoted variable
   - Fix: Add quotes around $variable

See full report: [link to artifacts]
```

## Scan History

### Historical Data

**Storage**: GitHub Actions artifacts and Issues

**Tracked Metrics**:
- Total scans run
- Pass/fail rate
- Issues found by type
- Issues fixed
- Mean time to fix

**Analysis**: Monthly security reports

### Example Historical Scan Data

| Date | Scan Type | Status | Issues Found | Critical Issues |
|------|-----------|--------|--------------|----------------|
| 2025-12-04 | Release | PASSED | 0 | 0 |
| 2025-12-03 | PR | PASSED | 2 (LOW) | 0 |
| 2025-12-01 | Weekly | PASSED | 0 | 0 |
| 2025-11-30 | Manual | PASSED | 1 (MEDIUM) | 0 |
| 2025-11-28 | Release | PASSED | 0 | 0 |

### Trend Analysis

**Monitored Trends**:
- Issue frequency over time
- Types of issues most common
- Time to fix by severity
- Scan pass rate
- Dependency vulnerability rate

**Goals**:
- Maintain 95%+ pass rate
- < 24 hour fix for critical
- < 1 week fix for high
- Zero hardcoded secrets
- 100% documentation coverage

## Integration with CI/CD

### GitHub Actions Workflow

```yaml
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  release:
    types: [created]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run security scan
        run: |
          chmod +x scripts/security-scan.sh
          ./scripts/security-scan.sh --json > scan-results.json

      - name: Check results
        run: |
          if [ $? -eq 2 ]; then
            echo "Critical security issues found"
            exit 1
          fi

      - name: Upload results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-scan-results
          path: scan-results.json

      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('scan-results.json'));
            // Post comment with results
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running quick security scan..."
./scripts/security-scan.sh --quick

if [ $? -ne 0 ]; then
    echo ""
    echo "Security scan failed. Commit aborted."
    echo "Fix the issues above or run with --no-verify to skip (not recommended)"
    exit 1
fi

echo "Security scan passed ✅"
```

## Compliance and Auditing

### Audit Trail

All security scans create an audit trail:

**Recorded Information**:
- Scan timestamp
- Scan type (full/quick)
- Triggering event
- Results summary
- Issues found
- Actions taken

**Retention**: 90 days in Actions, longer in Issues

**Access**: Repository maintainers and auditors

### Compliance Reports

**Frequency**: Monthly

**Content**:
- All scans performed
- Issues found and resolved
- Outstanding issues
- Trend analysis
- Compliance status

**Distribution**: Repository security documentation

## Troubleshooting Scans

### Scan Failures

**Issue**: Scan script not executable
```bash
chmod +x scripts/security-scan.sh
```

**Issue**: shellcheck not found
```bash
# Install shellcheck (optional but recommended)
brew install shellcheck  # macOS
apt-get install shellcheck  # Ubuntu
```

**Issue**: npm not found
```bash
# Install Node.js for npm audit
brew install node  # macOS
```

### False Positives

**Issue**: Test fixtures flagged as secrets

**Solution**:
- Use obviously fake values
- Add explanatory comments
- Document in code review

**Issue**: Legacy code patterns flagged

**Solution**:
- Refactor to safer patterns
- Document why pattern is safe
- Plan migration timeline

## Future Enhancements

### Planned Improvements

**Q1 2025**:
- SAST (Static Application Security Testing) integration
- Dependency graph analysis
- Automated dependency updates
- Enhanced reporting dashboard

**Q2 2025**:
- Container scanning (if Docker used)
- Infrastructure as Code scanning
- License compliance checking
- SBOM generation

**Q3 2025**:
- Security scorecard integration
- Continuous monitoring
- Threat modeling automation
- Security metrics API

## Questions and Feedback

For questions about security scanning:

1. Review this schedule document
2. Check [SECURITY-SCANNING-GUIDE.md](SECURITY-SCANNING-GUIDE.md)
3. See scan output for specific issues
4. Open GitHub Issue for unresolved questions

## Related Documentation

- [SECURITY.md](../SECURITY.md) - Overall security policy
- [SECURITY-SCANNING-GUIDE.md](SECURITY-SCANNING-GUIDE.md) - Detailed scanning guide
- [PUBLISHER-VERIFICATION.md](PUBLISHER-VERIFICATION.md) - Publisher verification

---

**Last Updated**: 2025-12-04
**Version**: 1.0
