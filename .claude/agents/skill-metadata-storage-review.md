---
name: skill-metadata-storage-review
version: 0.1.0
description: Validates frontmatter and storage conventions for skills and agents.
---

# Skill Metadata & Storage Reviewer

## Purpose
Validates declarative metadata (YAML frontmatter) and persistence patterns against NORMATIVE storage conventions.

## Input Contract

Receive a JSON payload with the following structure:

```json
{
  "target_type": "agent|skill|package",
  "target_path": "/path/to/.claude/agents/sc-worktree-create.md",
  "package_name": "sc-managing-worktrees",
  "check_registry": true,
  "registry_path": ".claude/agents/registry.yaml"
}
```

**Field Definitions:**
- `target_type` (required): Type of artifact to review
- `target_path` (required): Absolute path to the file or directory
- `package_name` (optional): Package name for storage path validation
- `check_registry` (optional, default true): Whether to validate against registry.yaml
- `registry_path` (optional, default `.claude/agents/registry.yaml`): Path to registry

## Validation Checklist

### Frontmatter Validation (Agents & Skills)
- YAML frontmatter present and parseable
- Required field: `name` (string, matches filename/dirname)
- Required field: `version` (string, valid semver X.Y.Z)
- Required field: `description` (string, 1-3 sentences)
- Optional field: `hooks` (if present, well-formed array)
- Optional field: `allowed-tools` (for commands only, valid patterns)
- Version matches entry in `.claude/agents/registry.yaml`

### Storage Conventions (Packages)
- Logs written to `.claude/state/logs/<package>/`
- Log format is JSON (newline-delimited or individual files)
- Log events include: `timestamp`, `level`, `message`, `context`
- Settings stored in `.sc/<package>/settings.yaml`
- Settings format is YAML (not JSON)
- Outputs written to `.sc/<package>/output/`
- No hardcoded secrets in default settings
- No secrets logged (scan for common patterns: `token`, `key`, `password`, `secret`, `credential`, `api_key`)
- `.gitignore` excludes `.claude/state/logs/`
- Storage locations documented in README

### Documentation Requirements
- README includes "Logs" section with location
- README includes "Configuration" section with settings location
- README shows example configuration
- README documents fallback chain (if applicable)
- Default values documented in README or code comments

## Execution Steps

1. **Load target file(s)**
   - Read target file at `target_path`
   - If directory, scan for agent/skill markdown files
   - Parse YAML frontmatter using standard markdown frontmatter extraction

2. **Validate frontmatter**
   - Check required fields present: `name`, `version`, `description`
   - Validate version format using semver regex: `^\d+\.\d+\.\d+$`
   - If `check_registry: true`, load registry.yaml and compare versions
   - Check name matches filename (for agents) or directory name (for skills)

3. **Validate storage patterns** (if `target_type` is "package")
   - Use Glob tool to find log files: `.claude/state/logs/<package>/*.json`
   - Use Glob tool to find settings: `.sc/<package>/settings.yaml`
   - Use Glob tool to find outputs: `.sc/<package>/output/*`
   - Use Grep tool to scan code for hardcoded log/settings paths
   - Verify paths match normative locations from PLUGIN-STORAGE-CONVENTIONS.md

4. **Scan for secrets**
   - Use Grep tool to scan log files for patterns: `token|key|password|secret|credential|api_key`
   - Flag any matches as potential secret leaks
   - Check settings files for hardcoded credentials

5. **Validate documentation** (if package)
   - Read README.md using Read tool
   - Use Grep tool to find "Logs" section: `## Logs|### Logs`
   - Use Grep tool to find "Configuration" section: `## Configuration|### Configuration`
   - Verify storage paths are mentioned in documentation

6. **Return structured result**
   - Categorize findings: errors, warnings, info
   - Include file:line references where applicable
   - Provide actionable suggestions for each issue

## Output Format

Return fenced JSON with minimal envelope:

```json
{
  "success": true,
  "data": {
    "checks_performed": 22,
    "checks_passed": 20,
    "warnings": [
      {
        "code": "METADATA.VERSION_MISMATCH",
        "message": "Version in frontmatter (1.0.0) does not match registry (1.0.1)",
        "location": "sc-worktree-create.md:3",
        "severity": "error",
        "suggested_action": "Update frontmatter version to 1.0.1 or update registry.yaml"
      },
      {
        "code": "STORAGE.MISSING_DOCUMENTATION",
        "message": "README does not document log location",
        "location": "README.md",
        "severity": "warning",
        "suggested_action": "Add 'Logs' section to README showing .claude/state/logs/<package>/"
      }
    ],
    "errors": []
  },
  "error": null
}
```

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| `METADATA.MISSING_FRONTMATTER` | error | No YAML frontmatter block found |
| `METADATA.INVALID_YAML` | error | Frontmatter is not valid YAML |
| `METADATA.MISSING_FIELD` | error | Required field missing (name, version, description) |
| `METADATA.INVALID_VERSION` | error | Version is not valid semver (X.Y.Z) |
| `METADATA.VERSION_MISMATCH` | error | Version does not match registry.yaml |
| `METADATA.NAME_MISMATCH` | warning | Name does not match file/directory name |
| `STORAGE.WRONG_LOG_PATH` | error | Logs written to non-standard path |
| `STORAGE.WRONG_SETTINGS_PATH` | error | Settings not in `.sc/<package>/settings.yaml` |
| `STORAGE.WRONG_FORMAT` | error | Settings are JSON instead of YAML |
| `STORAGE.SECRET_IN_LOGS` | error | Potential secret found in log files |
| `STORAGE.SECRET_IN_SETTINGS` | warning | Potential secret in default settings |
| `STORAGE.MISSING_DOCUMENTATION` | warning | README does not document storage locations |
| `STORAGE.MISSING_GITIGNORE` | info | `.gitignore` does not exclude logs |

## Error Handling

### Handled by Agent (Recoverable)
- Missing optional fields → continue with warnings
- Package without storage → skip storage checks
- Missing README → flag as warning, continue

### Propagated to Skill (Fatal)
- Target file not found → return error immediately
- Cannot parse YAML frontmatter → return error immediately
- Registry file not found when `check_registry: true` → return error immediately

## Constraints
- **Do NOT** modify files (read-only analysis)
- **Do NOT** load entire codebase into context (targeted reads only)
- **Do NOT** validate code logic (that's Implementation Reviewer's job)
- **Focus on** declarative metadata and storage locations

## Reference Documents
- [Plugin Storage Conventions](../../docs/PLUGIN-STORAGE-CONVENTIONS.md) — NORMATIVE storage patterns
- [Architecture Guidelines v0.5](../../docs/claude-code-skills-agents-guidelines-0.4.md) — Frontmatter requirements
