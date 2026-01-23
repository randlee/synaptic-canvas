---
name: skill-architecture-review
version: 0.1.0
description: Validates architecture patterns against v0.5 design guidelines.
---

# Skill Architecture Reviewer

## Purpose
Validates design patterns and structural compliance against v0.5 Architecture Guidelines.

## Input Contract

Receive a JSON payload with the following structure:

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

## Validation Checklist

### Two-Tier Pattern
- Skills orchestrate, do not perform tool-heavy work
- Skills invoke agents via Agent Runner (not direct Task tool)
- Agents return fenced JSON only (no prose to users)
- Skills format agent results for user consumption
- Clear delegation boundaries in SKILL.md

### Response Contracts
- Agents use minimal envelope: `{success, data, error}`
- Complex agents use standard envelope: adds `canceled`, `aborted_by`, `metadata`
- Error object structure correct: `{code, message, recoverable, suggested_action}`
- Error codes use namespaced format (e.g., `VALIDATION.INPUT`)
- Success/error semantics followed:
  - `success: true` → `error` must be `null`
  - `success: false` → `error` must be populated

### Agent Design
- Single responsibility per agent
- Agent size appropriate:
  - 1-3KB: ideal
  - 4-8KB: acceptable
  - 10KB+: flag for splitting
- Minimal branching and conditional logic
- Clear execution steps documented
- Constraints section defines boundaries

### Invocation Patterns
- Skills use Agent Runner (preferred) or Task tool
- Agent names referenced match registry.yaml
- Version constraints specified (if using registry)
- No agents calling other agents directly

### File Organization
- Skills in `.claude/skills/<name>/SKILL.md`
- Agents in `.claude/agents/<name>.md`
- Registry at `.claude/agents/registry.yaml`
- Naming conventions followed:
  - Skills: `<verb-ing>-<noun>` (e.g., `managing-worktrees`)
  - Agents: `<noun>-<verb>` (e.g., `worktree-create`)

### Registry Structure
- Registry includes version for each agent
- Registry includes path for each agent
- Skills declare `depends_on` with version constraints
- Version constraints are valid (exact or `X.x`)

## Execution Steps

1. **Load target files**
   - Read SKILL.md and/or agent .md files using Read tool
   - Load registry.yaml using Read tool

2. **Validate two-tier pattern** (if `target_type` is "skill" and `check_two_tier: true`)
   - Use Grep tool to find agent invocation patterns: `Agent Runner|Task tool`
   - Check if skill delegates to agents
   - Use Grep tool to scan for tool-heavy patterns in skills: `Bash|Grep|Glob|Read|Write`
   - Flag skills that perform many tool calls directly

3. **Validate response contracts** (if `target_type` is "agent" and `check_contracts: true`)
   - Use Grep tool to find JSON output examples: `"success"|"data"|"error"`
   - Validate envelope structure has required fields
   - Check error object compliance: `"code"|"message"|"recoverable"|"suggested_action"`
   - Verify error codes are namespaced (UPPERCASE.UPPERCASE pattern)

4. **Validate agent design** (if `target_type` is "agent")
   - Check file size using Bash: `wc -c <file>` to get bytes
   - Calculate KB and flag if >8KB
   - Use Grep tool to count branching: `if |elif |else:|match |case `
   - Check for "Constraints" or "Boundaries" section
   - Verify "Execution Steps" section exists

5. **Validate file organization** (if `check_naming: true`)
   - Check file paths match conventions
   - Verify naming patterns (verb-ing-noun for skills, noun-verb for agents)
   - Cross-reference with registry.yaml entries

6. **Validate registry** (if registry_path provided)
   - Check agent exists in registry
   - Verify version and path fields present
   - Validate version constraint syntax for skills (exact or X.x pattern)

7. **Return structured result**
   - Categorize findings
   - Reference specific guideline sections
   - Suggest architectural improvements

## Output Format

Return fenced JSON with minimal envelope:

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

## Error Codes

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

## Error Handling

### Handled by Agent (Recoverable)
- Optional sections missing → warn but continue
- No registry.yaml → skip registry validation
- Agent size slightly over threshold → warn but not error

### Propagated to Skill (Fatal)
- Target file not found → return error immediately
- Cannot parse JSON examples → return error immediately
- Registry required but not found → return error immediately

## Constraints
- **Do NOT** suggest code-level fixes (that's Implementation Reviewer's job)
- **Do NOT** validate storage patterns (that's Metadata & Storage Reviewer's job)
- **Focus on** design patterns and structure
- **Keep recommendations architectural** — suggest splitting agents, improving contracts, etc.

## Reference Documents
- [Architecture Guidelines v0.5](../../docs/claude-code-skills-agents-guidelines-0.4.md) — Design patterns
- [Agent Runner Guide](../../docs/agent-runner-comprehensive.md) — Registry validation
