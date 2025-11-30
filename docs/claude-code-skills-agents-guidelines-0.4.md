# Claude Code Skills and Agents Architecture Guidelines (v0.4)

A practical guide for designing and implementing a two-tier skill/agent architecture that optimizes context efficiency, maintains clean separation of concerns, and enables scalable AI-assisted workflows.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Scope of Applicability](#scope-of-applicability)
4. [Design Principles](#design-principles)
5. [Skills: The Discovery Layer](#skills-the-discovery-layer)
6. [Agents: The Execution Layer](#agents-the-execution-layer)
7. [Context Efficiency Patterns](#context-efficiency-patterns)
8. [Structured Response Contracts](#structured-response-contracts)
9. [Error Handling and Validation](#error-handling-and-validation)
10. [Security & Safety](#security--safety)
11. [State Management](#state-management)
12. [File Organization](#file-organization)
13. [Best Practices](#best-practices)
14. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
15. [References](#references)

---

## Quick Start

This section helps you upgrade existing skills/agents to v2.4 patterns. For comprehensive examples, see the companion document: `skills-agents-examples.md`.

### Minimum Viable Upgrade: Add Versioning and JSON Fencing

**Step 1: Add version to agent YAML frontmatter**

```yaml
---
name: worktree-create
version: 1.0.0
description: Creates a git worktree for parallel development.
---
```

**Step 2: Fence all JSON output in markdown code blocks**

Before (unfenced):
```
{ "success": true, "path": "/repo-feature-x" }
```

After (fenced):
````markdown
```json
{
  "success": true,
  "data": { "path": "/repo-feature-x" },
  "error": null
}
```
````

**Step 3: Use minimal response envelope**

For simple agents, use this minimal envelope:

```json
{
  "success": true,
  "data": { /* operation-specific results */ },
  "error": null
}
```

For complex/stateful agents, use the full envelope (see [Standard Response Schema](#standard-response-schema)).

**Step 4: Validate versions externally**

Create `.claude/agents/registry.yaml`:

```yaml
agents:
  worktree-create:
    version: 1.0.0
    path: .claude/agents/worktree-create.md
  worktree-scan:
    version: 1.0.0
    path: .claude/agents/worktree-scan.md
```

Run validation via CI or pre-commit hook (see [Version Management](#version-management)).

### Maturity Levels

This document supports progressive adoption:

| Level | What to Implement | When to Use |
|-------|-------------------|-------------|
| **Basic** | YAML frontmatter with version, fenced JSON output, minimal envelope | Upgrading existing agents |
| **Standard** | Full response envelope, error contracts, registry.yaml | Production workflows |
| **Advanced** | State management, checkpoints, parallel execution, attestation & audit | Complex multi-agent pipelines |

---

## Architecture Overview

This architecture separates AI assistance into two distinct tiers:

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Claude Session                       │
│  • Accumulates conversation history                          │
│  • Reasons about user intent                                 │
│  • Discovers and invokes skills                              │
│  • Receives distilled results (not tool traces)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ delegates via skill
┌─────────────────────────────────────────────────────────────┐
│                         Skill                                │
│  • Discoverable by main session                              │
│  • Translates intent to agent invocation                     │
│  • Orchestrates multiple agents if needed                    │
│  • Formats output for user consumption                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ invokes via Task tool (prefer Agent Runner)
┌─────────────────────────────────────────────────────────────┐
│                         Agent                                │
│  • Loads specific instructions                               │
│  • Performs tool-heavy work                                  │
│  • Returns structured JSON outputs                           │
│  • Context isolated from main session                        │
└─────────────────────────────────────────────────────────────┘
```

### Key Benefits

- **Context quarantine**: Tool calls, errors, and retries stay in agent context
- **Distilled results**: Main session sees summaries, not mechanics
- **Preserved reasoning space**: Conversation stays focused on intent and decisions
- **Granular agents without discovery overhead**: Dozens of agents don't clutter decision space
- **Cost efficiency**: Smaller, focused contexts reduce token consumption
- **Reduced correction cycles**: Narrow agent scope minimizes errors and corrective iterations

### How Skills Invoke Agents (Task Tool)

Skills invoke agents using Claude's **Task tool**, which starts a new Claude instance with isolated context. Prefer invoking via an **Agent Runner** wrapper that enforces registry policy (path + version) and records an audit entry.

When a skill's SKILL.md instructs to invoke an agent, Claude uses the Task tool (or Agent Runner) to:

1. Load the agent's instructions (`.claude/agents/<agent-name>.md`)
2. Execute in a fresh, isolated context
3. Return the structured (fenced) JSON result to the skill

**Invocation syntax in SKILL.md (safe):**

```markdown
## Agent Delegation

To create a worktree:
1. Use the Agent Runner tool to invoke the `worktree-create` agent.
2. Provide parameters: branch name, base branch.
3. The agent returns JSON; format the result for the user.

Runner prompt example:
"Invoke agent 'worktree-create' as defined in .claude/agents/registry.yaml
with params:
- branch: feature-x
- base: main"
```

**What happens:**

```
Skill instructs: "Use Agent Runner to invoke worktree-create agent"
    ↓
Agent Runner: Resolves path+version from registry, computes file hash, launches Task tool
    ↓
Agent context (isolated):
    - Loads worktree-create.md instructions
    - Runs git commands
    - Handles errors/retries internally
    - Returns fenced JSON result
    ↓
Agent Runner: Writes redacted audit record (.claude/state/logs/) and forwards JSON
    ↓
Skill formats for user: "✓ Worktree created at /repo-feature-x"
```

---

## Scope of Applicability

### When to Use This Pattern

The two-tier skill/agent architecture is most valuable when:

✓ **Routine operations with predictable outputs**
- Package publishing, code formatting, file organization
- Operations where you want minimal verbosity in the main session

✓ **Tool-heavy workflows**
- Operations requiring 10+ tool calls to complete
- Complex git operations, database migrations, build orchestration

✓ **Repeatable automation**
- Tasks performed frequently with similar parameters
- Workflows that benefit from standardized execution

✓ **Context isolation is beneficial**
- Experimental operations that might fail and retry multiple times
- Operations where failure traces would clutter the main conversation

### When NOT to Use This Pattern

This architecture can be counterproductive for:

✗ **Exploratory or investigative work**
- Debugging unknown issues where tool traces provide valuable insight
- Research tasks where you want to see the discovery process

✗ **Interactive decision-making**
- Workflows requiring frequent human input or approval
- Tasks where intermediate results influence next steps

✗ **One-off simple operations**
- Single tool calls or straightforward tasks
- Operations that don't justify the overhead of agent orchestration

✗ **Debugging and troubleshooting**
- When you need full visibility into what tools were called and why
- Error investigation where hiding details makes diagnosis harder

### The Trade-off

The two-tier pattern hides details and verbosity to keep the main session focused. This is excellent for routine tasks but problematic when those details contain valuable information. Choose this pattern when efficiency and predictability matter more than transparency and exploration.

---

## Design Principles

### 1. Skills Provide Abstraction, Agents Provide Implementation

Skills are the public interface—what Claude discovers and reasons about. Agents are private implementation details that skills invoke via the Task tool (prefer Agent Runner).

```
User thinks: "I need to manage my git worktrees"
           ↓
Skill:     "manage-worktrees" (orchestrates workflow)
           ↓
Agents:    worktree-create, worktree-scan, worktree-cleanup
           (invoked via Agent Runner from the skill)
```

### 2. Optimize for Context Efficiency

Tool calls are context-expensive. A single file search generates substantial tokens. By pushing tool-heavy work into agents:

- Tool call traces stay in agent's isolated context
- Main session receives: "worktree created at `/path`"
- Not: the 15 tool calls it took to get there

### 3. Design Before Code

Before implementing a skill or agent:

1. Define the contract (inputs, outputs, error cases)
2. Identify what context the agent actually needs
3. Determine the minimal output the skill requires
4. Plan error handling across the boundary

### 4. Clear and Concise Agents

Very clear, concise prompts with minimal logic and branching are significantly more likely to succeed. Agents should:

- Focus on a single responsibility
- Have straightforward execution paths
- Avoid complex conditional logic
- Minimize decision points

When an agent grows complex, split it into multiple focused agents rather than adding branching logic.

### 5. Progressive Disclosure

Skills and agents should reveal complexity only as needed:

- SKILL.md serves as table of contents, pointing to details
- Reference files load on demand
- Scripts execute without loading into context

---

## Skills: The Discovery Layer

### Structure

```
.claude/skills/
├── manage-worktrees/
│   ├── SKILL.md              # Entry point with YAML frontmatter
│   ├── workflows.md          # Detailed workflow documentation
│   └── troubleshooting.md    # Error handling guide
```

### SKILL.md Requirements

```yaml
---
name: manage-worktrees
description: Create, manage, and clean up git worktrees for parallel development. 
  Use when working on multiple features simultaneously or when isolating 
  experimental changes.
---

# Managing Git Worktrees

This skill orchestrates git worktree operations for parallel development workflows.

## Capabilities

- Create isolated worktrees for feature development
- Scan existing worktrees and their status
- Clean up completed or abandoned worktrees

## Agent Delegation

This skill delegates to specialized agents via the Agent Runner (Task tool under the hood):

| Operation | Agent | Returns |
|-----------|-------|---------|
| Create    | `worktree-create`  | JSON: path, branch, success |
| Scan      | `worktree-scan`    | JSON: list of worktrees |
| Cleanup   | `worktree-cleanup` | JSON: cleanup summary |

To invoke an agent, instruct:
"Use the Agent Runner to invoke `<agent-name>` as defined in `.claude/agents/registry.yaml` with parameters: ..."

## Usage

When the user requests worktree operations:
1. Use Agent Runner to invoke the appropriate agent
2. Receive fenced JSON response from agent
3. Format and present results to the user
```

### Skill Naming Conventions

Use gerund form (verb + -ing) for clarity:

- ✓ `processing-pdfs`, `managing-worktrees`, `publishing-nuget`
- ✗ `pdf-processor`, `worktree-manager`, `nuget-publisher`

### Description Best Practices

The description field is critical—Claude uses it to select from potentially 100+ skills.

```yaml
# Good: Specific, includes triggers
description: Create, manage, and clean up git worktrees for parallel development.
  Use when working on multiple features simultaneously, isolating experiments,
  or when user mentions "worktree", "parallel branches", or "feature isolation".

# Bad: Vague
description: Helps with git operations.
```

---

## Agents: The Execution Layer

### Structure

```
.claude/agents/
├── worktree-create.md
├── worktree-scan.md
├── worktree-cleanup.md
├── nuget-publish.md
└── nuget-validation.md
```

### Agent Design Principles

#### 1. Single Responsibility

Each agent does ONE thing well.

#### 2. Minimal Instructions

Agents should be as small as possible while remaining effective:
- 1–3KB is ideal for focused operations
- 4–8KB acceptable for complex workflows
- 10KB+ consider splitting into planning/execution phases

#### 3. YAML Frontmatter with Version

Every agent MUST declare version in YAML frontmatter:

```yaml
---
name: worktree-create
version: 1.0.0
description: Creates a git worktree for parallel development.
---
```

#### 4. Fenced JSON Output

Agents ALWAYS return JSON wrapped in markdown code fences. Skills are responsible for user presentation.

````markdown
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```
````

### Agent Template

```markdown
---
name: [agent-name]
version: X.Y.Z
description: [One sentence describing what this agent does]
---

# [Agent Name]

## Purpose
[One sentence describing what this agent does]

## Inputs
- `param1`: [description, type, constraints]
- `param2`: [description, type, constraints]

## Execution Steps
1. [Validate inputs]
2. [Perform operation]
3. [Handle errors]
4. [Return structured result]

## Output Format

Return fenced JSON:

```json
{
  "success": boolean,
  "data": { ... },
  "error": null
}
```

## Error Handling

### Handled by agent (recoverable):
- [Error type]: [Recovery strategy]

### Propagated to skill (fatal):
- [Error type]: [Why it can't be handled]

## Constraints
- [What this agent should NOT do]
- [Boundaries of responsibility]
```

---

## Context Efficiency Patterns

### Pattern 1: Agent as Disposable Context

Each agent invocation via Agent Runner (Task tool under the hood) is a disposable execution context:

```
Main Session: "Create a worktree for feature-x"
    ↓
Skill: Use Agent Runner to invoke worktree-create agent
    ↓
Agent Context (temporary, isolated):
    - Loads worktree-create.md instructions
    - Runs git commands
    - Handles errors/retries
    - Returns fenced JSON
    ↓
Agent Runner: Audit → forwards JSON
    ↓
Skill: "✓ Worktree created at /repo-feature-x"
```

### Pattern 2: Planning/Execution Split

For complex operations, split into phases.

### Pattern 3: Validation Gates

Enforce quality gates before expensive operations.

### Pattern 4: Multi-Step Workflows

Orchestrate complex workflows across multiple agents.

### Pattern 5: Parallel Agent Execution (with guardrails)

When operations are independent, invoke agents in parallel using background executions:

- Set per-task timeouts (e.g., 120s default)
- Cap concurrency to 3–4 by default (override only when safe)
- Attach a correlation_id per invocation; aggregate results deterministically
- On timeout, return a synthetic failure:
  ```json
  {
    "success": false,
    "error": {
      "code": "EXECUTION.TIMEOUT",
      "message": "Agent exceeded per-task timeout",
      "recoverable": false,
      "suggested_action": "Increase timeout parameter or split agent into smaller tasks"
    }
  }
  ```

Example aggregation policy (informative):

```json
{
  "parallel": true,
  "concurrency": 4,
  "per_task_timeout_s": 120,
  "results": [
    { "correlation_id": "style", "success": true,  "data": { /* ... */ } },
{ "correlation_id": "security", "success": false, "error": { "code": "EXECUTION.TIMEOUT", "message": "Agent exceeded per-task timeout", "recoverable": false, "suggested_action": "Increase timeout parameter or split agent into smaller tasks" } }
  ]
}
```

---

## Structured Response Contracts

### Why Structured Outputs Matter

Structured outputs (fenced JSON) provide predictable error handling, version compatibility (via frontmatter), interface contracts, and composability.

### Standard Response Schema

**Minimal envelope** (for simple agents):

```json
{
  "success": true,
  "data": { },
  "error": null
}
```

**Full envelope (Standard)** (for complex/stateful agents):

```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": { },
  "error": null,
  "metadata": {
    "duration_ms": 0,
    "tool_calls": 0,
    "retry_count": 0
  }
}
```

**Advanced optional metadata** (enable when needed):

```json
{
  "metadata": {
    "timestamp": "2025-11-29T23:58:00Z",
    "max_tool_calls": 200,
    "idempotency_key": null
  }
}
```

**Error object** (when `success: false`):

```json
{
  "code": "NAMESPACE.CODE",
  "message": "Human-friendly summary",
  "recoverable": false,
  "suggested_action": "Next step for user/skill"
}
```

### Version Management

**Strategy: External registry validation (zero runtime tokens)**

Agents declare version in YAML frontmatter only. Version checking happens outside agent execution via registry and tooling.

1) Registry with skill constraints (source of truth)

```yaml
# .claude/agents/registry.yaml
agents:
  worktree-create:
    version: 1.0.0
    path: .claude/agents/worktree-create.md
  worktree-scan:
    version: 1.0.0
    path: .claude/agents/worktree-scan.md
  nuget-validation:
    version: 1.2.0
    path: .claude/agents/nuget-validation.md

skills:
  managing-worktrees:
    depends_on:
      worktree-create: "1.x"
      worktree-scan: "1.x"
      worktree-cleanup: "1.x"
```

**Path format**: Registry paths are relative to the project root (e.g., `.claude/agents/worktree-create.md`).

### Dependency Constraint Syntax

Supported formats:
- `1.x`: Any version with major=1 (equivalent to `>=1.0.0 <2.0.0`)
- Future: `^1.2.0`, `>=1.0.0`, etc. (semver ranges)

Validation:
- CI script checks that referenced agents exist in registry
- Agent Runner resolves constraints at invocation time
- Constraint mismatches fail fast before Task tool execution

2) Robust validation script (frontmatter-aware)

```bash
#!/usr/bin/env bash
# scripts/validate-agents.sh
set -euo pipefail
REG=".claude/agents/registry.yaml"

frontmatter() {
  awk 'f{print} /^---/{f=1;c++} c==2{exit}' "$1" | sed '1d'
}

fail=0
for agent in .claude/agents/*.md; do
  name=$(basename "$agent" .md)
  file_ver=$(frontmatter "$agent" | yq -r '.version' || echo "")
  reg_ver=$(yq -r ".agents.\"$name\".version" "$REG" || echo "")

  if [[ -z "$file_ver" || -z "$reg_ver" ]]; then
    echo "ERROR: $name missing version (file='$file_ver' registry='$reg_ver')"
    fail=1; continue
  fi
  if [[ "$file_ver" != "$reg_ver" ]]; then
    echo "ERROR: $name version mismatch: file=$file_ver registry=$reg_ver"
    fail=1
  fi
done

[[ $fail -eq 0 ]] && echo "All agent versions validated"
exit $fail
```

3) Runtime attestation (optional, zero tokens)

Use an **Agent Runner** wrapper (CLI or tool) that:
- Resolves path and allowed version from registry.yaml
- Computes the agent file hash (e.g., SHA-256)
- Launches the Task tool with that path
- Writes a redacted audit record to `.claude/state/logs/`
- Returns only the agent’s JSON to the skill

Audit record example:

```json
{
  "timestamp": "2025-11-29T23:58:00Z",
  "agent": "worktree-create",
  "version_frontmatter": "1.0.0",
  "file_sha256": "1f3a...c9",
  "invoker": "agent-runner",
  "outcome": "success",
  "duration_ms": 3280
}
```

Why: Ensures the invoked artifact matched policy at runtime without adding tokens to the agent’s prompt.

**Implementation reference**: See `docs/agent-runner.md` in this repository for a working Python implementation of the Agent Runner pattern.

### Cancellation Semantics

- `canceled: true` indicates deliberate abort (user request, timeout, policy)
- Populate `aborted_by` with: `"user"`, `"timeout"`, or `"policy"`
- Fatal errors use `success: false`, `canceled: false` with error object

---

## Error Handling and Validation

### Structured Error Responses

```json
{
  "success": false,
  "canceled": false,
  "data": null,
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "NuGet API key is invalid or expired",
    "recoverable": false,
    "suggested_action": "Provide a valid API key via environment variable NUGET_API_KEY"
  }
}
```

### Execution Flags

Agents should support flag-style parameters for different execution modes.

#### --validate (alias: --dry-run)

Perform validation without executing actual changes.

#### --auto-fix (alias: --yolo)

Apply safe, bounded fixes automatically. Never bypass confirmations for destructive operations.

Do NOT auto-fix authentication failures, data loss scenarios, or security violations.

---

## Security & Safety

This section covers baseline security requirements. Complex scenarios (input sanitization, command injection prevention, sandboxing) are implementation-specific and outside the scope of this architecture document.

### Secret Handling

- Retrieve credentials from environment variables (e.g., `NUGET_API_KEY`)
- Never hardcode or echo secrets
- Agents must not include secrets in JSON outputs

### Destructive Operations

- Default to validation/dry-run mode
- Require explicit confirmation for publish, delete, or mutate operations
- Support `--validate` and `--auto-fix` flags appropriately

### Boundaries & Budgets

- Restrict file operations to repository root unless explicitly allowed
- Fail closed on missing credentials
- Respect `max_tool_calls` budgets when specified; on breach, return `canceled: true` with `aborted_by: "policy"`

### Observability

- Prefer Agent Runner to record a redacted audit record per invocation (timestamp, agent, frontmatter version, hash, outcome, duration)

---

## State Management

This section covers architectural patterns for state. Complex scenarios (concurrency, locking, corruption recovery) are implementation-specific and outside the scope of this document.

- Skill-managed (simple): Single conversation, no resume needed
- File-based (durable): `.claude/state/` for resume capability
- Git-based (versioned): state tracked alongside code
- Cleanup: TTL-based expiration, explicit cleanup agent, or user command

---

## File Organization

### Recommended Structure

```
.claude/
├── skills/
│   ├── managing-worktrees/
│   │   ├── SKILL.md
│   │   └── workflows.md
│   └── publishing-nuget/
│       ├── SKILL.md
│       └── registry-config.md
├── agents/
│   ├── registry.yaml           # Version registry + skill constraints
│   ├── worktree-create.md
│   ├── worktree-scan.md
│   ├── nuget-publish.md
│   └── nuget-validation.md
├── state/                      # Optional: for file-based state
│   └── .gitignore
└── scripts/
    └── validate-agents.sh      # Version validation script
```

### Naming Conventions

- **Skills**: `<verb-ing>-<noun>/` e.g., `managing-worktrees/`
- **Agents**: `<noun>-<verb>.md` e.g., `worktree-create.md`
- **State files**: `<operation>-<identifier>.json`

---

## Best Practices

1. **Start with the Contract**: Define inputs, outputs, error handling before implementing
2. **Version in Frontmatter**: Every agent declares version in YAML frontmatter
3. **Fence All JSON**: Always wrap JSON output in markdown code fences
4. **Use Minimal Envelope**: Start with minimal response schema, add fields as needed
5. **Validate Externally**: Use registry.yaml + CI for version validation
6. **Prefer Agent Runner**: Enforce registry policy and capture audit logs; do not load arbitrary paths
7. **Single Responsibility**: One agent, one task
8. **Document Error Boundaries**: Clear separation of agent vs. skill error handling
9. **Parallel Guardrails**: Cap concurrency, set timeouts, use correlation_ids

---

## Anti-Patterns to Avoid

1. **Monolithic Agents**: Split into focused agents
2. **Leaky Abstractions**: Don't return raw tool output; structure and interpret
3. **Unfenced JSON**: Always wrap JSON in markdown code fences
4. **In-Agent Version Checks**: Version validation belongs in external tooling
5. **Over-Communication**: Keep agent output minimal and structured
6. **Agents Returning Markdown for Users**: Agents return JSON; skills present to users
7. **Complex Branching**: When an agent grows complex, split it
8. **Windows-Style Paths**: Use forward slashes

---

## References

### Official Documentation

- [Skill Authoring Best Practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Agent Skills Engineering Blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

### Repositories

- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Awesome Claude Skills](https://github.com/travisvn/awesome-claude-skills)

### Community Resources

- [Simon Willison's Skills Analysis](https://simonwillison.net/2025/Oct/16/claude-skills/)
- [Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

---

Document version: 0.4  
Last updated: November 2025  
Changes from v2.3:
- Added Agent Runner runtime attestation (zero-token) and audit recommendation
- Replaced version validation script with frontmatter-aware, robust variant
- Extended registry.yaml to include skill dependency constraints
- Added parallel execution guardrails (timeouts, concurrency cap, correlation_ids)
- Marked advanced optional metadata fields (timestamp, max_tool_calls, idempotency_key)
- Updated SKILL.md invocation wording to prefer Agent Runner