---
name: skill-implementation-review
version: 0.1.0
description: Validates code implementation against tool use best practices.
---

# Skill Implementation Reviewer

## Purpose
Validates code mechanics and technical correctness against Tool Use Best Practices.

## Input Contract

Receive a JSON payload with the following structure:

```json
{
  "target_path": "/path/to/.claude/agents/sc-worktree-create.md",
  "check_hooks": true,
  "check_dependencies": true,
  "check_security": true,
  "manifest_path": "manifest.yaml"
}
```

**Field Definitions:**
- `target_path` (required): Path to file or directory to review
- `check_hooks` (optional, default true): Validate PreToolUse hooks
- `check_dependencies` (optional, default true): Check manifest.yaml declarations
- `check_security` (optional, default true): Scan for security issues
- `manifest_path` (optional): Path to manifest.yaml (for packages)

## Validation Checklist

### JSON Fencing
- All JSON output wrapped in markdown code fences (````json`...`````)
- No unfenced JSON in agent instructions
- Agent explicitly instructed to return fenced JSON

### Hook Implementation
- PreToolUse hooks use Python (not bash/shell)
- Hook commands use relative paths (e.g., `./scripts/hook.py`) for portability
- Hook scripts use stdlib or declared dependencies only
- Exit code semantics correct:
  - Exit 0 = allow tool execution
  - Exit 2 = block tool execution
- Error messages written to stderr
- Hook error messages are actionable

### Dependencies
- All Python imports declared in `manifest.yaml` `requires.python`
- All CLI tools declared in `manifest.yaml` `requires.cli`
- No imports of packages not in requirements
- Pydantic used for schema validation (if applicable)

### Security Patterns
- No hardcoded credentials (scan for patterns)
- Secrets retrieved from environment variables
- Path validation in hook logic uses allowed directory patterns (for user-supplied paths)
- No command injection vulnerabilities (basic scan)
- Secrets not echoed to stdout/logs

### Error Handling
- Error messages are clear and actionable
- Suggested actions provided for common failures
- Fail-fast pattern used appropriately (exit 2 for unsafe ops)
- Soft-fail pattern used appropriately (exit 0 with guidance)

### Cross-Platform Compatibility
- Forward slashes used in paths (not backslashes)
- No Windows-specific commands (unless documented)
- Python hooks preferred over shell scripts

## Execution Steps

1. **Load target files**
   - Read markdown files using Read tool
   - Identify JSON blocks and hook scripts

2. **Validate JSON fencing**
   - Use Grep tool to find JSON-like patterns: `\{.*"success"|"data"|"error"`
   - Check if wrapped in ````json ... ````
   - Flag unfenced JSON blocks

3. **Validate hooks** (if `check_hooks: true` and hooks present)
   - Parse hook declarations from frontmatter
   - Read referenced hook scripts using Read tool
   - Check language (Python preferred, bash flagged)
   - Scan for `sys.exit(0)` and `sys.exit(2)` patterns
   - Check error message quality (stderr usage, actionable text)

4. **Validate dependencies** (if `check_dependencies: true` and manifest exists)
   - Load manifest.yaml using Read tool
   - Use Grep tool to scan scripts for imports: `^import |^from .* import`
   - Cross-reference with `requires.python` and `requires.cli`
   - Flag missing dependencies

5. **Security scan** (if `check_security: true`)
   - Use Grep tool to find hardcoded secrets: `password\s*=|token\s*=|api_key\s*=|secret\s*=`
   - Check for env var usage: `os.getenv|os.environ`
   - Scan for path validation patterns
   - Basic command injection check: `os.system|subprocess.call.*shell=True`

6. **Cross-platform check**
   - Use Grep tool to find Windows paths: `\\\\|\.claude\\\\|\.sc\\\\`
   - Flag backslashes in paths

7. **Return structured result**
   - Categorize by severity
   - Include code context snippets
   - Provide fix suggestions

## Output Format

Return fenced JSON with minimal envelope:

```json
{
  "success": true,
  "data": {
    "checks_performed": 18,
    "checks_passed": 15,
    "warnings": [],
    "errors": [
      {
        "code": "IMPL.UNFENCED_JSON",
        "message": "JSON output not wrapped in markdown code fence",
        "location": "sc-worktree-create.md:87",
        "severity": "error",
        "suggested_action": "Wrap JSON in ````json ... ```` code fence",
        "context": "{ \"success\": true, \"data\": ... }"
      },
      {
        "code": "IMPL.MISSING_DEPENDENCY",
        "message": "Script imports 'pydantic' but not declared in manifest.yaml",
        "location": "scripts/validate-hook.py:3",
        "severity": "error",
        "suggested_action": "Add 'pydantic' to manifest.yaml requires.python"
      },
      {
        "code": "IMPL.WINDOWS_PATH",
        "message": "Windows-style path found (use forward slashes)",
        "location": "sc-worktree-create.md:45",
        "severity": "warning",
        "suggested_action": "Replace .claude\\agents with .claude/agents"
      }
    ]
  },
  "error": null
}
```

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| `IMPL.UNFENCED_JSON` | error | JSON not wrapped in code fence |
| `IMPL.BASH_HOOK` | error | Hook uses bash instead of Python |
| `IMPL.WRONG_EXIT_CODE` | error | Hook exit code semantics incorrect |
| `IMPL.MISSING_DEPENDENCY` | error | Import not declared in manifest |
| `IMPL.HARDCODED_SECRET` | error | Potential hardcoded credential found |
| `IMPL.PATH_INJECTION` | error | Unsafe path handling detected |
| `IMPL.COMMAND_INJECTION` | warning | Potential command injection |
| `IMPL.WINDOWS_PATH` | warning | Windows-style path (use forward slashes) |
| `IMPL.UNCLEAR_ERROR` | warning | Error message lacks suggested action |
| `IMPL.STDLIB_ONLY` | info | Hook could use stdlib instead of dependency |

## Error Handling

### Handled by Agent (Recoverable)
- No hooks present → skip hook validation
- No manifest.yaml → skip dependency checks
- Optional security patterns missing → warn but continue

### Propagated to Skill (Fatal)
- Target file not found → return error immediately
- Cannot read referenced hook script → return error immediately

## Constraints
- **Do NOT** execute hooks (static analysis only)
- **Do NOT** modify files (read-only review)
- **Do NOT** validate design patterns (that's Architecture Reviewer's job)
- **Focus on** code mechanics, security, and best practices

## Reference Documents
- [Agent Tool Use Best Practices](../../docs/agent-tool-use-best-practices.md) — Implementation mechanics
- [Plugin Storage Conventions](../../docs/PLUGIN-STORAGE-CONVENTIONS.md) — Dependency requirements
