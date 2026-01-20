---
name: validate
version: 0.7.0
description: Run complete validation suite and generate HTML reports. Use for pre-release validation, after configuration changes, or to debug version mismatches.
allowed-tools: Bash(python3 scripts/validate-all.py*), Bash(python3 scripts/generate-validation-report.py*), Read, Glob
options:
  - name: --quick
    description: Run quick validation without unit tests
  - name: --open
    description: Open HTML reports in browser after generation
  - name: --keep-reports
    description: Number of reports to keep (default 5)
  - name: --skip-cleanup
    description: Keep all old reports
  - name: --report
    description: Generate HTML report after validation
  - name: --help
    description: Show usage information
---

# /validate - Synaptic Canvas Validation Suite

Run the complete validation suite for the Synaptic Canvas marketplace. This command orchestrates multiple validators to check agent registry consistency, cross-references, frontmatter schemas, manifest artifacts, and more.

## Pre-Execution

Validation output:
!`python3 scripts/validate-all.py $ARGUMENTS`

## Interpreting Results

After running the validation suite, analyze the output:

### Pass/Fail Status
- **[+]** indicates a passed validator
- **[x]** indicates a failed validator
- **[-]** indicates a skipped validator

### If All Validators Pass
Report success to the user with a brief summary:
- Number of validators passed
- Total duration
- Any skipped validators and why

### If Any Validators Fail
1. Identify which validators failed
2. Summarize the error messages
3. Suggest remediation steps based on the failure type:
   - **Agent Registry**: Check `.claude/agents/registry.yaml` matches agent frontmatter versions
   - **Cross-References**: Verify all referenced files exist and paths are correct
   - **Frontmatter Schema**: Check YAML frontmatter follows required schema
   - **Manifest Artifacts**: Ensure package manifests reference valid files
   - **Marketplace Sync**: Verify marketplace.json is in sync with packages
   - **Script References**: Check that referenced scripts exist
   - **Unit Tests**: Review pytest output for test failures

## HTML Report Generation

If the user requests a report (via `--report` flag or explicitly), generate an HTML report:

```bash
python3 scripts/generate-validation-report.py --keep-reports 5
```

With `--open` flag, the report opens in the default browser:
```bash
python3 scripts/generate-validation-report.py --open --keep-reports 5
```

Reports are saved to `.claude/reports/validation/` with timestamps.

## Examples

Basic validation:
```
/validate
```

Quick validation (skip pytest):
```
/validate --quick
```

Validation with HTML report:
```
/validate --report
```

Full validation with report opened in browser:
```
/validate --report --open
```

## Help Output

```
/validate - Run complete validation suite

Usage:
  /validate [flags]

Flags:
  --quick          Skip unit tests (pytest), run validators only
  --report         Generate HTML report after validation
  --open           Open HTML report in browser (implies --report)
  --keep-reports N Keep only the last N reports (default: 5)
  --skip-cleanup   Keep all old reports
  --help           Show this help message

Validators run:
  - validate-agents.py: Agent frontmatter/registry consistency
  - validate-cross-references.py: Cross-reference integrity
  - validate-frontmatter-schema.py: Frontmatter schema validation
  - validate-manifest-artifacts.py: Manifest artifact validation
  - validate-marketplace-sync.py: Marketplace sync validation
  - validate-script-references.py: Script reference validation
  - pytest tests/ (unless --quick): Unit tests

Examples:
  /validate                  Run full validation suite
  /validate --quick          Skip pytest, run validators only
  /validate --report --open  Generate and open HTML report
```
