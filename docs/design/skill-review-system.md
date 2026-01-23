# Skill Review System Design Document

**Version:** 1.0.0
**Status:** Design Proposal
**Date:** January 22, 2026
**Author:** ARCH-SKILL Expert

---

## Executive Summary

This document specifies a comprehensive skill review system comprising three specialized review agents and one orchestrating skill. The system validates Claude Code skills and agents against three orthogonal concerns:

1. **Metadata & Storage** — Frontmatter and persistence patterns
2. **Implementation** — Code mechanics and technical correctness
3. **Architecture** — Design patterns and structural compliance

Each agent is designed for single responsibility, minimal complexity, and parallel execution. Together they provide comprehensive validation against v0.5 Architecture Guidelines, Tool Use Best Practices, and Plugin Storage Conventions.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Agent 1: Metadata & Storage Reviewer](#agent-1-metadata--storage-reviewer)
3. [Agent 2: Implementation Reviewer](#agent-2-implementation-reviewer)
4. [Agent 3: Architecture Reviewer](#agent-3-architecture-reviewer)
5. [Orchestrating Skill: Skill Reviewing](#orchestrating-skill-skill-reviewing)
6. [Response Contracts](#response-contracts)
7. [Error Codes](#error-codes)
8. [File Organization](#file-organization)
9. [Implementation Checklist](#implementation-checklist)
10. [Testing Strategy](#testing-strategy)
11. [Example Outputs](#example-outputs)
12. [References](#references)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Claude Session                       │
│  User: "Review the sc-worktree package"                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ invokes via Skill tool
┌─────────────────────────────────────────────────────────────┐
│            Skill: skill-reviewing (SKILL.md)                 │
│  • Accepts package name or file paths                        │
│  • Invokes three reviewers in parallel via Agent Runner      │
│  • Aggregates findings by concern area                       │
│  • Formats comprehensive report for user                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Metadata &       │ │ Implementation   │ │ Architecture     │
│ Storage Reviewer │ │ Reviewer         │ │ Reviewer         │
│                  │ │                  │ │                  │
│ Validates:       │ │ Validates:       │ │ Validates:       │
│ • Frontmatter    │ │ • JSON fencing   │ │ • Two-tier       │
│ • Versions       │ │ • Hook impl      │ │ • Response       │
│ • Storage paths  │ │ • Dependencies   │ │   contracts      │
│ • TTL policies   │ │ • Security       │ │ • Agent size     │
│ • Documentation  │ │ • Error handling │ │ • Naming         │
└──────────────────┘ └──────────────────┘ └──────────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼ returns fenced JSON
┌─────────────────────────────────────────────────────────────┐
│                 Aggregated Review Report                     │
│                                                              │
│ ✅ Metadata & Storage: 12 checks passed, 2 warnings         │
│ ⚠️  Implementation: 8 checks passed, 3 issues               │
│ ✅ Architecture: 15 checks passed                           │
│                                                              │
│ [Detailed findings by category with file:line references]   │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles Applied

- **Single Responsibility** (Agent Design Principle #1) — Each reviewer focuses on one concern domain
- **Clear and Concise Agents** (Design Principle #4) — Minimal branching, straightforward execution paths
- **Context Efficiency** (Design Principle #2) — All three run in parallel, isolated contexts
- **Design Before Code** (Design Principle #3) — Contracts defined first in this document
- **Progressive Disclosure** (Design Principle #5) — Skill orchestrates, agents execute detailed checks

---

## Agent 1: Metadata & Storage Reviewer

### Purpose
Validates declarative metadata (YAML frontmatter) and persistence patterns against NORMATIVE storage conventions.

### Location
`.claude/agents/skill-metadata-storage-review.md`

### Frontmatter
```yaml
---
name: skill-metadata-storage-review
version: 0.1.0
description: Validates frontmatter and storage conventions for skills and agents.
---
```

### Input Contract

Agent receives a JSON payload via the Agent Runner:

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

### Validation Checklist

#### Frontmatter Validation (Agents & Skills)
- [ ] YAML frontmatter present and parseable
- [ ] Required field: `name` (string, matches filename/dirname)
- [ ] Required field: `version` (string, valid semver X.Y.Z)
- [ ] Required field: `description` (string, 1-3 sentences)
- [ ] Optional field: `hooks` (if present, well-formed array)
- [ ] Optional field: `allowed-tools` (for commands only, valid patterns)
- [ ] Version matches entry in `.claude/agents/registry.yaml`

#### Storage Conventions (Packages)
- [ ] Logs written to `.claude/state/logs/<package>/`
- [ ] Log format is JSON (newline-delimited or individual files)
- [ ] Log events include: `timestamp`, `level`, `message`, `context`
- [ ] Settings stored in `.sc/<package>/settings.yaml`
- [ ] Settings format is YAML (not JSON)
- [ ] Outputs written to `.sc/<package>/output/`
- [ ] No hardcoded secrets in default settings
- [ ] No secrets logged (scan for common patterns: `token`, `key`, `password`)
- [ ] `.gitignore` excludes `.claude/state/logs/`
- [ ] Storage locations documented in README

#### Documentation Requirements
- [ ] README includes "Logs" section with location
- [ ] README includes "Configuration" section with settings location
- [ ] README shows example configuration
- [ ] README documents fallback chain (if applicable)
- [ ] Default values documented in README or code comments

### Output Contract

Returns fenced JSON with minimal envelope:

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

### Error Codes

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

### Execution Steps

1. **Load target file(s)**
   - Read frontmatter from markdown files
   - Parse YAML using stdlib or pyyaml

2. **Validate frontmatter**
   - Check required fields present
   - Validate semver format
   - If `check_registry: true`, load registry.yaml and compare versions

3. **Validate storage patterns** (if package)
   - Scan code for log/settings/output paths
   - Check against normative locations
   - Scan for secret patterns in logs and settings

4. **Validate documentation** (if package)
   - Read README.md
   - Check for "Logs" and "Configuration" sections
   - Verify storage paths are documented

5. **Return structured result**
   - Categorize findings: errors, warnings, info
   - Include file:line references
   - Provide actionable suggestions

### Constraints
- **Do NOT** modify files (read-only analysis)
- **Do NOT** load entire codebase into context (targeted reads only)
- **Do NOT** validate code logic (that's Implementation Reviewer's job)

---

## Agent 2: Implementation Reviewer

### Purpose
Validates code mechanics and technical correctness against Tool Use Best Practices.

### Location
`.claude/agents/skill-implementation-review.md`

### Frontmatter
```yaml
---
name: skill-implementation-review
version: 0.1.0
description: Validates code implementation against tool use best practices.
---
```

### Input Contract

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

### Validation Checklist

#### JSON Fencing
- [ ] All JSON output wrapped in markdown code fences (````json`...`````)
- [ ] No unfenced JSON in agent instructions
- [ ] Agent explicitly instructed to return fenced JSON

#### Hook Implementation
- [ ] PreToolUse hooks use Python (not bash/shell)
- [ ] Hook scripts use stdlib or declared dependencies only
- [ ] Exit code semantics correct:
  - Exit 0 = allow tool execution
  - Exit 2 = block tool execution
- [ ] Error messages written to stderr
- [ ] Hook error messages are actionable

#### Dependencies
- [ ] All Python imports declared in `manifest.yaml` `requires.python`
- [ ] All CLI tools declared in `manifest.yaml` `requires.cli`
- [ ] No imports of packages not in requirements
- [ ] Pydantic used for schema validation (if applicable)

#### Security Patterns
- [ ] No hardcoded credentials (scan for patterns)
- [ ] Secrets retrieved from environment variables
- [ ] Path validation uses allowed directory patterns
- [ ] No command injection vulnerabilities (basic scan)
- [ ] Secrets not echoed to stdout/logs

#### Error Handling
- [ ] Error messages are clear and actionable
- [ ] Suggested actions provided for common failures
- [ ] Fail-fast pattern used appropriately (exit 2 for unsafe ops)
- [ ] Soft-fail pattern used appropriately (exit 0 with guidance)

#### Cross-Platform Compatibility
- [ ] Forward slashes used in paths (not backslashes)
- [ ] No Windows-specific commands (unless documented)
- [ ] Python hooks preferred over shell scripts

### Output Contract

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

### Error Codes

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

### Execution Steps

1. **Load target files**
   - Read markdown files
   - Identify JSON blocks and hook scripts

2. **Validate JSON fencing**
   - Find all JSON-like patterns
   - Check if wrapped in ````json ... ````
   - Flag unfenced JSON

3. **Validate hooks** (if present)
   - Parse hook declarations from frontmatter
   - Read referenced hook scripts
   - Check language (Python preferred)
   - Validate exit code usage
   - Check error message quality

4. **Validate dependencies** (if manifest exists)
   - Load manifest.yaml
   - Scan scripts for imports
   - Cross-reference with `requires.python` and `requires.cli`

5. **Security scan**
   - Pattern match for hardcoded secrets
   - Check for env var usage
   - Basic command injection detection

6. **Return structured result**
   - Categorize by severity
   - Include code context snippets
   - Provide fix suggestions

### Constraints
- **Do NOT** execute hooks (static analysis only)
- **Do NOT** modify files
- **Do NOT** validate design patterns (that's Architecture Reviewer's job)

---

## Agent 3: Architecture Reviewer

### Purpose
Validates design patterns and structural compliance against v0.5 Architecture Guidelines.

### Location
`.claude/agents/skill-architecture-review.md`

### Frontmatter
```yaml
---
name: skill-architecture-review
version: 0.1.0
description: Validates architecture patterns against v0.5 design guidelines.
---
```

### Input Contract

```json
{
  "target_type": "agent|skill|package",
  "target_path": "/path/to/.claude/skills/managing-worktrees/",
  "check_two_tier": true,
  "check_contracts": true,
  "check_naming": true,
  "registry_path": ".claude/agents/registry.yaml"
}
```

**Field Definitions:**
- `target_type` (required): What to review
- `target_path` (required): Path to target
- `check_two_tier` (optional, default true): Validate skill/agent separation
- `check_contracts` (optional, default true): Validate response envelopes
- `check_naming` (optional, default true): Check naming conventions
- `registry_path` (optional): Path to registry for dependency validation

### Validation Checklist

#### Two-Tier Pattern
- [ ] Skills orchestrate, do not perform tool-heavy work
- [ ] Skills invoke agents via Agent Runner (not direct Task tool)
- [ ] Agents return fenced JSON only (no prose to users)
- [ ] Skills format agent results for user consumption
- [ ] Clear delegation boundaries in SKILL.md

#### Response Contracts
- [ ] Agents use minimal envelope: `{success, data, error}`
- [ ] Complex agents use standard envelope: adds `canceled`, `aborted_by`, `metadata`
- [ ] Error object structure correct: `{code, message, recoverable, suggested_action}`
- [ ] Error codes use namespaced format (e.g., `VALIDATION.INPUT`)
- [ ] Success/error semantics followed:
  - `success: true` → `error` must be `null`
  - `success: false` → `error` must be populated

#### Agent Design
- [ ] Single responsibility per agent
- [ ] Agent size appropriate:
  - 1-3KB: ideal
  - 4-8KB: acceptable
  - 10KB+: flag for splitting
- [ ] Minimal branching and conditional logic
- [ ] Clear execution steps documented
- [ ] Constraints section defines boundaries

#### Invocation Patterns
- [ ] Skills use Agent Runner (preferred) or Task tool
- [ ] Agent names referenced match registry.yaml
- [ ] Version constraints specified (if using registry)
- [ ] No agents calling other agents directly

#### File Organization
- [ ] Skills in `.claude/skills/<name>/SKILL.md`
- [ ] Agents in `.claude/agents/<name>.md`
- [ ] Registry at `.claude/agents/registry.yaml`
- [ ] Naming conventions followed:
  - Skills: `<verb-ing>-<noun>` (e.g., `managing-worktrees`)
  - Agents: `<noun>-<verb>` (e.g., `worktree-create`)

#### Registry Structure
- [ ] Registry includes version for each agent
- [ ] Registry includes path for each agent
- [ ] Skills declare `depends_on` with version constraints
- [ ] Version constraints are valid (exact or `X.x`)

### Output Contract

```json
{
  "success": true,
  "data": {
    "checks_performed": 25,
    "checks_passed": 22,
    "warnings": [],
    "errors": [
      {
        "code": "ARCH.AGENT_TOO_LARGE",
        "message": "Agent file is 12KB (ideal: 1-3KB, max recommended: 8KB)",
        "location": "sc-worktree-create.md",
        "severity": "warning",
        "suggested_action": "Consider splitting into planning and execution agents"
      },
      {
        "code": "ARCH.MISSING_ERROR_OBJECT",
        "message": "Agent returns success:false without error object",
        "location": "sc-worktree-create.md:145",
        "severity": "error",
        "suggested_action": "Add error object with code, message, recoverable, suggested_action"
      },
      {
        "code": "ARCH.DIRECT_TASK_TOOL",
        "message": "Skill uses Task tool directly instead of Agent Runner",
        "location": "SKILL.md:67",
        "severity": "warning",
        "suggested_action": "Use Agent Runner for registry validation and audit logging"
      }
    ]
  },
  "error": null
}
```

### Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| `ARCH.TOOL_HEAVY_SKILL` | error | Skill performs tool-heavy work |
| `ARCH.AGENT_RETURNS_PROSE` | error | Agent returns prose instead of JSON |
| `ARCH.MISSING_ENVELOPE` | error | Agent does not use response envelope |
| `ARCH.WRONG_ENVELOPE` | error | Response envelope missing required fields |
| `ARCH.MISSING_ERROR_OBJECT` | error | success:false without error object |
| `ARCH.INVALID_ERROR_CODE` | warning | Error code not namespaced |
| `ARCH.AGENT_TOO_LARGE` | warning | Agent file exceeds recommended size |
| `ARCH.MULTIPLE_RESPONSIBILITIES` | warning | Agent has multiple responsibilities |
| `ARCH.DIRECT_TASK_TOOL` | warning | Uses Task tool instead of Agent Runner |
| `ARCH.WRONG_LOCATION` | error | File in wrong directory |
| `ARCH.WRONG_NAMING` | warning | File name does not follow conventions |
| `ARCH.MISSING_REGISTRY` | error | Agent not in registry.yaml |
| `ARCH.AGENT_CALLS_AGENT` | error | Agent tries to invoke another agent |

### Execution Steps

1. **Load target files**
   - Read SKILL.md and/or agent .md files
   - Load registry.yaml

2. **Validate two-tier pattern** (if skill)
   - Check if skill delegates to agents
   - Look for agent invocation patterns
   - Ensure skill does not do tool-heavy work

3. **Validate response contracts** (if agent)
   - Find JSON output examples in agent
   - Validate envelope structure
   - Check error object compliance

4. **Validate agent design**
   - Check file size (in bytes and KB)
   - Analyze for single responsibility
   - Count branching points and complexity

5. **Validate file organization**
   - Check file paths
   - Validate naming conventions
   - Cross-reference with registry

6. **Return structured result**
   - Categorize findings
   - Reference specific guideline sections
   - Suggest architectural improvements

### Constraints
- **Do NOT** suggest code-level fixes (that's Implementation Reviewer's job)
- **Do NOT** validate storage patterns (that's Metadata & Storage Reviewer's job)
- **Focus on** design patterns and structure

---

## Orchestrating Skill: Skill Reviewing

### Purpose
Orchestrates all three review agents to provide comprehensive skill/agent validation.

### Location
`.claude/skills/skill-reviewing/SKILL.md`

### Frontmatter
```yaml
---
name: skill-reviewing
description: Comprehensive review of Claude Code skills and agents against v0.5
  guidelines. Validates metadata, implementation, and architecture. Use when
  reviewing existing packages or during skill development.
---
```

### SKILL.md Content

```markdown
---
name: skill-reviewing
description: Comprehensive review of Claude Code skills and agents against v0.5
  guidelines. Validates metadata, implementation, and architecture. Use when
  reviewing existing packages or during skill development.
---

# Skill Reviewing

Provides comprehensive validation of Claude Code skills and agents against:
- Plugin Storage Conventions (NORMATIVE)
- Agent Tool Use Best Practices
- Architecture Guidelines v0.5

## Capabilities

This skill orchestrates three specialized review agents, each focusing on a distinct concern:

| Agent | Focus | Source Document |
|-------|-------|-----------------|
| `skill-metadata-storage-review` | Frontmatter & persistence | PLUGIN-STORAGE-CONVENTIONS.md |
| `skill-implementation-review` | Code mechanics & security | agent-tool-use-best-practices.md |
| `skill-architecture-review` | Design patterns & structure | claude-code-skills-agents-guidelines-0.4.md |

## Agent Delegation

All three agents are invoked via Agent Runner for parallel execution:

### Metadata & Storage Reviewer
**Validates:**
- YAML frontmatter (name, version, description)
- Version consistency with registry.yaml
- Storage paths (logs, settings, outputs)
- Secret handling
- Documentation completeness

**Returns:** `{success, data: {checks_performed, checks_passed, warnings, errors}, error}`

### Implementation Reviewer
**Validates:**
- JSON fencing
- Hook implementation (Python preferred)
- Dependency declarations
- Security patterns
- Cross-platform compatibility

**Returns:** `{success, data: {checks_performed, checks_passed, warnings, errors}, error}`

### Architecture Reviewer
**Validates:**
- Two-tier skill/agent separation
- Response contract compliance
- Single responsibility principle
- Agent size and complexity
- File organization

**Returns:** `{success, data: {checks_performed, checks_passed, warnings, errors}, error}`

## Orchestration Pattern

When user requests a review:

1. **Determine target**
   - Package name (e.g., `sc-managing-worktrees`)
   - Specific file (e.g., `.claude/agents/sc-worktree-create.md`)
   - Directory (e.g., `.claude/skills/managing-worktrees/`)

2. **Invoke agents in parallel**
   ```
   Use Agent Runner to invoke all three reviewers concurrently:
   - skill-metadata-storage-review with target_path
   - skill-implementation-review with target_path
   - skill-architecture-review with target_path
   ```

3. **Aggregate results**
   - Collect findings from all three agents
   - Group by severity: errors, warnings, info
   - Organize by concern area

4. **Format report**
   Present findings to user:
   ```
   ## Review Summary: [package-name]

   ✅ Metadata & Storage: X checks passed, Y warnings
   ⚠️  Implementation: X checks passed, Y issues
   ✅ Architecture: X checks passed

   ### Critical Issues (must fix)
   [List all errors with file:line and suggested actions]

   ### Warnings (should fix)
   [List all warnings with suggestions]

   ### Info (optional improvements)
   [List all info-level findings]
   ```

## Usage Examples

**Review entire package:**
```
/skill-reviewing sc-managing-worktrees
```

**Review specific agent:**
```
/skill-reviewing .claude/agents/sc-worktree-create.md
```

**Review during development:**
```
Review the skill I just created in .claude/skills/my-new-skill/
```

## Error Handling

If any reviewer fails:
- Report which reviewer failed and why
- Include partial results from successful reviewers
- Suggest corrective action (e.g., "Registry file not found")

If all reviewers return no issues:
- Congratulate user on clean implementation
- Optionally suggest next steps (testing, documentation)

## Notes

- All three agents run in parallel (independent execution)
- Each agent returns structured JSON
- This skill formats and presents findings
- No agent modifies files (read-only analysis)
```

---

## Response Contracts

### Minimal Envelope (All Three Agents)

All agents use the minimal response envelope since they are single-step analyzers:

```json
{
  "success": boolean,
  "data": {
    "checks_performed": number,
    "checks_passed": number,
    "warnings": Array<Finding>,
    "errors": Array<Finding>
  },
  "error": null | ErrorObject
}
```

### Finding Object

```json
{
  "code": "NAMESPACE.CODE",
  "message": "Human-readable description",
  "location": "file.md:line" | "file.md" | "directory/",
  "severity": "error" | "warning" | "info",
  "suggested_action": "Concrete next step",
  "context": "Optional code snippet or additional detail"
}
```

### Error Object (for agent failures)

```json
{
  "code": "EXECUTION.FILE_NOT_FOUND",
  "message": "Target file does not exist",
  "recoverable": false,
  "suggested_action": "Verify the file path and try again"
}
```

---

## Error Codes

### Cross-Agent Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| `EXECUTION.FILE_NOT_FOUND` | error | Target file/directory not found |
| `EXECUTION.PARSE_ERROR` | error | Could not parse YAML/JSON |
| `EXECUTION.PERMISSION_DENIED` | error | Cannot read target file |

### Agent-Specific Codes

See individual agent sections above for detailed error code tables.

---

## File Organization

```
.claude/
├── skills/
│   └── skill-reviewing/
│       ├── SKILL.md                              # Orchestrating skill
│       └── examples.md                           # (Optional) Example outputs
├── agents/
│   ├── registry.yaml                             # Register all three agents
│   ├── skill-metadata-storage-review.md          # Agent 1
│   ├── skill-implementation-review.md            # Agent 2
│   └── skill-architecture-review.md              # Agent 3
└── state/
    └── logs/
        └── skill-reviewing/                      # Review execution logs
            └── 2026-01-22-review-sc-worktree.json
```

### Registry Entry

Add to `.claude/agents/registry.yaml`:

```yaml
agents:
  skill-metadata-storage-review:
    version: 0.1.0
    path: .claude/agents/skill-metadata-storage-review.md
  skill-implementation-review:
    version: 0.1.0
    path: .claude/agents/skill-implementation-review.md
  skill-architecture-review:
    version: 0.1.0
    path: .claude/agents/skill-architecture-review.md

skills:
  skill-reviewing:
    depends_on:
      skill-metadata-storage-review: "0.1.0"
      skill-implementation-review: "0.1.0"
      skill-architecture-review: "0.1.0"
```

---

## Implementation Checklist

### Phase 1: Agent Stubs (Week 1)
- [ ] Create `.claude/agents/skill-metadata-storage-review.md`
  - [ ] Add frontmatter with version 0.1.0
  - [ ] Define input contract
  - [ ] Define output contract
  - [ ] List validation checks
  - [ ] Define error codes
- [ ] Create `.claude/agents/skill-implementation-review.md`
  - [ ] Add frontmatter with version 0.1.0
  - [ ] Define input contract
  - [ ] Define output contract
  - [ ] List validation checks
  - [ ] Define error codes
- [ ] Create `.claude/agents/skill-architecture-review.md`
  - [ ] Add frontmatter with version 0.1.0
  - [ ] Define input contract
  - [ ] Define output contract
  - [ ] List validation checks
  - [ ] Define error codes
- [ ] Update `.claude/agents/registry.yaml`
  - [ ] Add all three agents with version 0.1.0

### Phase 2: Orchestrating Skill (Week 1)
- [ ] Create `.claude/skills/skill-reviewing/SKILL.md`
  - [ ] Add frontmatter with description
  - [ ] Document capabilities
  - [ ] Define orchestration pattern
  - [ ] Add usage examples
- [ ] Update registry.yaml with skill dependencies

### Phase 3: Agent Implementation (Week 2-3)
- [ ] Implement Metadata & Storage Reviewer
  - [ ] Frontmatter validation logic
  - [ ] Storage path scanning
  - [ ] Documentation checks
  - [ ] Secret pattern detection
- [ ] Implement Implementation Reviewer
  - [ ] JSON fence detection
  - [ ] Hook validation
  - [ ] Dependency cross-reference
  - [ ] Security scanning
- [ ] Implement Architecture Reviewer
  - [ ] Two-tier pattern detection
  - [ ] Response contract validation
  - [ ] File size checks
  - [ ] Naming convention validation

### Phase 4: Testing (Week 4)
- [ ] Test on `sc-managing-worktrees` package (baseline)
- [ ] Test on `sc-delay-tasks` package (Tier 0 example)
- [ ] Test on `sc-github-issue` package (complex example)
- [ ] Test on intentionally broken examples
- [ ] Validate parallel execution works
- [ ] Verify aggregation logic

### Phase 5: Documentation (Week 4)
- [ ] Add examples.md with sample outputs
- [ ] Update package README
- [ ] Add troubleshooting guide
- [ ] Document known limitations

### Phase 6: Integration (Week 5)
- [ ] Add to existing skill-review workflow
- [ ] Integrate with CI validation
- [ ] Create pre-commit hook (optional)
- [ ] Add to package publishing checklist

---

## Testing Strategy

### Test Cases

#### Test Case 1: Perfect Package
**Target:** `sc-delay-tasks` (known good Tier 0 package)

**Expected Results:**
- All three agents return `success: true`
- Zero errors, zero warnings
- All checks passed

**Validates:** Baseline accuracy

---

#### Test Case 2: Missing Frontmatter
**Target:** Agent file with no YAML frontmatter

**Expected Results:**
- Metadata & Storage Reviewer: `METADATA.MISSING_FRONTMATTER` error
- Implementation Reviewer: success (no code issues)
- Architecture Reviewer: may flag missing version

**Validates:** Frontmatter detection

---

#### Test Case 3: Version Mismatch
**Target:** Agent with version 1.0.0 in frontmatter, 1.0.1 in registry

**Expected Results:**
- Metadata & Storage Reviewer: `METADATA.VERSION_MISMATCH` error
- Other reviewers: success

**Validates:** Registry cross-reference

---

#### Test Case 4: Unfenced JSON
**Target:** Agent that returns JSON without code fences

**Expected Results:**
- Implementation Reviewer: `IMPL.UNFENCED_JSON` error
- Architecture Reviewer: may flag response contract issue

**Validates:** JSON fence detection

---

#### Test Case 5: Wrong Storage Paths
**Target:** Package writing logs to `.sc/logs/` instead of `.claude/state/logs/`

**Expected Results:**
- Metadata & Storage Reviewer: `STORAGE.WRONG_LOG_PATH` error

**Validates:** Storage convention enforcement

---

#### Test Case 6: Monolithic Agent
**Target:** 15KB agent file with multiple responsibilities

**Expected Results:**
- Architecture Reviewer: `ARCH.AGENT_TOO_LARGE` warning
- Architecture Reviewer: `ARCH.MULTIPLE_RESPONSIBILITIES` warning

**Validates:** Agent size and SRP checks

---

#### Test Case 7: Security Issues
**Target:** Agent with `API_KEY = "hardcoded-secret"`

**Expected Results:**
- Implementation Reviewer: `IMPL.HARDCODED_SECRET` error

**Validates:** Security scanning

---

#### Test Case 8: Missing Dependencies
**Target:** Script imports `pydantic` but manifest.yaml does not declare it

**Expected Results:**
- Implementation Reviewer: `IMPL.MISSING_DEPENDENCY` error

**Validates:** Dependency validation

---

### Test Execution

```bash
# Test individual agents
python3 tools/agent-runner.py validate --agent skill-metadata-storage-review
python3 tools/agent-runner.py validate --agent skill-implementation-review
python3 tools/agent-runner.py validate --agent skill-architecture-review

# Test orchestrating skill
/skill-reviewing sc-delay-tasks

# Test with broken examples
/skill-reviewing tests/fixtures/broken-agent.md
```

### Success Criteria

- [ ] All 8 test cases pass
- [ ] Parallel execution completes in <30 seconds
- [ ] No false positives on known-good packages
- [ ] Clear, actionable error messages
- [ ] Aggregated report is readable and useful

---

## Example Outputs

### Example 1: Perfect Package

```
## Review Summary: sc-delay-tasks

✅ **Metadata & Storage:** 14 checks passed
✅ **Implementation:** 12 checks passed
✅ **Architecture:** 18 checks passed

**Result:** No issues found. Package complies with all v0.5 guidelines.

### Recommendations
- Consider adding more examples to README
- Optional: Add integration tests
```

---

### Example 2: Package with Issues

```
## Review Summary: sc-worktree-create

⚠️  **Metadata & Storage:** 12 checks passed, 2 warnings
❌ **Implementation:** 8 checks passed, 3 errors, 1 warning
✅ **Architecture:** 15 checks passed

### Critical Issues (must fix)

**IMPL.UNFENCED_JSON** (sc-worktree-create.md:87)
JSON output not wrapped in markdown code fence

Suggested action: Wrap JSON in ````json ... ```` code fence

Context:
```
{ "success": true, "data": { "path": "/repo-feature-x" } }
```

**IMPL.MISSING_DEPENDENCY** (scripts/validate-hook.py:3)
Script imports 'pydantic' but not declared in manifest.yaml

Suggested action: Add 'pydantic' to manifest.yaml requires.python

**METADATA.VERSION_MISMATCH** (sc-worktree-create.md:3)
Version in frontmatter (1.0.0) does not match registry (1.0.1)

Suggested action: Update frontmatter version to 1.0.1 or update registry.yaml

### Warnings (should fix)

**IMPL.WINDOWS_PATH** (sc-worktree-create.md:45)
Windows-style path found (use forward slashes)

Suggested action: Replace .claude\agents with .claude/agents

**STORAGE.MISSING_DOCUMENTATION** (README.md)
README does not document log location

Suggested action: Add 'Logs' section to README showing .claude/state/logs/<package>/

**STORAGE.MISSING_DOCUMENTATION** (README.md)
README does not document settings location

Suggested action: Add 'Configuration' section with .sc/<package>/settings.yaml
```

---

### Example 3: Skill Review

```
## Review Summary: skill-reviewing

✅ **Metadata & Storage:** 10 checks passed, 1 info
✅ **Implementation:** 6 checks passed
⚠️  **Architecture:** 12 checks passed, 1 warning

### Warnings

**ARCH.DIRECT_TASK_TOOL** (SKILL.md:67)
Skill uses Task tool directly instead of Agent Runner

Suggested action: Use Agent Runner for registry validation and audit logging

Example:
"Use the Agent Runner to invoke `skill-metadata-storage-review` as defined
in .claude/agents/registry.yaml with parameters: ..."

### Info

**STORAGE.MISSING_GITIGNORE** (.gitignore)
.gitignore does not exclude .claude/state/logs/

Suggested action: Add `.claude/state/logs/` to .gitignore (optional)
```

---

## References

### Source Documents
- [Plugin Storage Conventions](../PLUGIN-STORAGE-CONVENTIONS.md) — NORMATIVE storage patterns
- [Agent Tool Use Best Practices](../agent-tool-use-best-practices.md) — Implementation mechanics
- [Architecture Guidelines v0.5](../claude-code-skills-agents-guidelines-0.4.md) — Design patterns
- [ARCH-SKILL Expert](../../pm/ARCH-SKILL.md) — Review methodology

### Related Tools
- `scripts/validate-agents.py` — Version validation
- `tools/agent-runner.py` — Agent invocation with audit
- `scripts/audit-versions.py` — Version consistency check

### Example Packages
- `packages/sc-delay-tasks/` — Tier 0 baseline
- `packages/sc-git-worktree/` — Tier 1 example
- `packages/sc-github-issue/` — Complex multi-agent

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-22 | Initial design document |

---

**Document Status:** Ready for implementation
**Next Steps:** Begin Phase 1 (Agent Stubs)
**Owner:** ARCH-SKILL Expert
**Reviewers:** TBD
