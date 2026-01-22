# GitHub Issue Skill v2 Plan Review Report

**Review Date**: 2025-12-03
**Plan Document**: `/Users/randlee/Documents/github/synaptic-canvas/plans/github-issue-skill-v2.md`
**Plan Version**: v2 (Preliminary)
**Plan Revision**: v2 (artifacts target version 0.1.0)
**Guidelines Reference**: v0.4 (`docs/claude-code-skills-agents-guidelines-0.4.md`)
**Reviewer**: Claude Code Review Agent

---

## Executive Summary

This v2 plan represents a **significant improvement** over v1, addressing all critical blocking issues and most major concerns. The plan demonstrates strong understanding of v0.4 guidelines and comprehensive coverage of required architectural elements.

### Findings Summary

| Severity | Count | Status |
|----------|-------|--------|
| **ERROR** | 2 | Critical blocking issues requiring immediate attention |
| **WARNING** | 8 | Major improvements recommended before implementation |
| **INFO** | 12 | Suggestions for enhancement and best practices |

### Overall Assessment: **NEEDS REVISION**

**Rationale**: While the plan is well-structured and addresses most v0.4 requirements, 2 critical errors and 8 warnings must be resolved before implementation begins. The plan shows excellent understanding of:
- Frontmatter structure and versioning requirements
- Registry patterns and dependency constraints
- Data contracts and envelope selection
- Error handling with proper namespacing
- Safety validation and worktree hygiene

**Recommendation**: Address ERROR and WARNING items below, then upgrade status from "Preliminary" to "Proposed" for stakeholder review.

---

## Detailed Findings

### ERROR Severity (Critical Blocking Issues)

#### E1: Command Frontmatter Versioning Inconsistency

**Location**: Lines 22-28, 399, 432-438, 464
**Rule**: v0.4 Section "File Organization" - Frontmatter requirements
**Severity**: ERROR

**Issue**:
The plan contradicts itself regarding command version handling:
- Line 30 states: "Keep commands at version 0.1.0 unless explicitly overridden"
- Lines 399, 432-438, 464 correctly state: "Commands: name, description (NO version)"
- v0.4 guidelines are clear: Commands have `name` and `description` only (NO version field)

The statement at line 30 and line 601 ("default version 0.1.0 if used") creates confusion about whether commands should have versions.

**Impact**: Implementation confusion leading to incorrect frontmatter structure.

**Recommendation**:
Remove all references to command versioning. Commands NEVER have a version field. Update lines 30 and 601 to remove mentions of "version 0.1.0" for commands. Only agents require version fields.

**Correct statement**: "Commands are unversioned; only agents require explicit version fields in frontmatter."

---

#### E2: Skill Frontmatter Versioning Inconsistency

**Location**: Lines 48-60, 402, 440-449, 464
**Rule**: v0.4 Section "Skills: The Discovery Layer" - SKILL.md Requirements
**Severity**: ERROR

**Issue**:
Similar to E1, the plan has conflicting statements about skill versioning:
- Line 59 states: "Keep skills at version 0.1.0 unless explicitly overridden"
- Lines 402, 440-449, 464 correctly state: "Skills: name, description (NO version)"
- v0.4 guidelines: Skills have `name` and `description` only (NO version field)

The statement at line 59 and line 604 ("default version 0.1.0 if used") contradicts the explicit "NO version" statements elsewhere.

**Impact**: Implementation confusion leading to incorrect SKILL.md frontmatter structure.

**Recommendation**:
Remove all references to skill versioning. Skills NEVER have a version field. Update lines 59 and 604 to remove mentions of "version 0.1.0" for skills. Only agents are versioned.

**Correct statement**: "Skills are unversioned; version management applies only to agents they invoke."

---

### WARNING Severity (Major Improvements Needed)

#### W1: Agent Runner Pattern - Missing Implementation Details

**Location**: Lines 133-163, 168-194
**Rule**: v0.4 Section "Architecture Overview" - Agent Runner pattern
**Severity**: WARNING

**Issue**:
While the plan mentions Agent Runner extensively, it lacks critical implementation details:
1. No mention of the reference implementation in `docs/agent-runner-comprehensive.md` (cited in v0.4 line 696)
2. No guidance on whether Agent Runner is a CLI tool, a wrapper function, or integrated into skills
3. No error handling when Agent Runner itself fails (vs. agent failure)
4. No specification of how Agent Runner resolves version constraints ("0.x" matching logic)

**Impact**: Implementation teams may build inconsistent Agent Runner solutions or bypass it entirely.

**Recommendation**:
Add a dedicated section "Agent Runner Implementation" that:
- References `docs/agent-runner-comprehensive.md` as the implementation guide
- Specifies Agent Runner as a wrapper tool/function (not a Claude tool itself)
- Documents error codes for Agent Runner failures (e.g., `RUNNER.VERSION_MISMATCH`, `RUNNER.AGENT_NOT_FOUND`)
- Clarifies version constraint resolution algorithm
- Provides example of Agent Runner invocation vs. direct Task tool invocation

**Suggested addition** (after line 194):
```markdown
### Agent Runner Implementation

**Reference**: See `docs/agent-runner-comprehensive.md` for complete implementation guide.

**What Agent Runner Is**:
- A wrapper function/tool that enforces registry policy before invoking Task tool
- NOT a Claude tool itself; it's infrastructure code that skills invoke

**Error Handling**:
```json
{
  "success": false,
  "error": {
    "code": "RUNNER.VERSION_MISMATCH",
    "message": "Agent gh-issue-fix-agent version 0.2.0 incompatible with constraint '0.1.x'",
    "recoverable": false,
    "suggested_action": "Update skill constraint to '0.2.x' or revert agent to 0.1.x"
  }
}
```
```

---

#### W2: Missing Commands Directory in File Layout

**Location**: Lines 393-427
**Rule**: v0.4 Section "File Organization" - Recommended Structure
**Severity**: WARNING

**Issue**:
The "Complete Registry Definition" at lines 168-188 and frontmatter examples at lines 432-438 reference `.claude/commands/github-issue.md`, but the file layout diagram at lines 396-426 does NOT include a `commands/` directory. This is inconsistent.

Additionally, the plan documents a command at lines 19-44 but doesn't consistently show it in the file structure.

**Impact**: Implementation teams may be unsure where to place command files, leading to inconsistent organization.

**Recommendation**:
Update the file layout (lines 396-426) to include:
```
.claude/
├── commands/
│   └── github-issue.md              # Frontmatter: name, description (NO version)
├── skills/
│   └── github-issue/
│       └── SKILL.md                  # Frontmatter: name, description (NO version)
```

This aligns with the v0.4 convention where commands are entry points that delegate to skills.

---

#### W3: Registry Dependency Constraint Format Ambiguity

**Location**: Lines 182-188, 629-638
**Rule**: v0.4 Section "Dependency Constraint Syntax"
**Severity**: WARNING

**Issue**:
The plan uses dependency constraint `"0.x"` throughout (lines 184-187), but v0.4 guidelines at line 631 show `"1.x"` format and define it as "equivalent to `>=1.0.0 <2.0.0`".

For version 0.x.y (pre-1.0), the semantics differ from 1.x versions:
- `"0.x"` could mean `>=0.0.0 <1.0.0` (any 0.y.z)
- OR it could mean each minor version is breaking (0.1.x incompatible with 0.2.x)

The plan doesn't clarify whether `"0.x"` follows SemVer's pre-1.0 semantics (where minor bumps can be breaking) or if it's treated as `"1.x"` would be.

**Impact**: Version constraint resolution may fail or allow incompatible versions during agent invocation.

**Recommendation**:
Add explicit clarification in the Registry Structure section (after line 193):

```markdown
### Version Constraint Semantics for 0.x Agents

For agents at version 0.y.z (pre-1.0):
- Constraint `"0.x"` matches ANY version `>=0.0.0 <1.0.0`
- This assumes minor version changes (0.1 → 0.2) are compatible during initial development
- If stricter compatibility is needed, use `"0.1.x"` to lock to specific minor version

**Recommendation**: Keep all related agents at the same minor version during 0.x phase (e.g., all at 0.1.z) to avoid compatibility issues.
```

---

#### W4: Missing Error Handling for Agent Runner Failures

**Location**: Lines 310-391 (Error Contracts section)
**Rule**: v0.4 Section "Error Handling and Validation"
**Severity**: WARNING

**Issue**:
The error contract section defines 4 namespaces (GITHUB.*, WORKTREE.*, VALIDATION.*, EXECUTION.*) but does NOT define errors for Agent Runner failures:
- Agent file not found in registry
- Version constraint mismatch
- Agent file hash validation failure
- Registry.yaml parsing errors

These are distinct from agent execution errors and should have their own namespace.

**Impact**: Skills won't know how to handle Agent Runner infrastructure failures vs. agent logic failures.

**Recommendation**:
Add a new error namespace section after line 376:

```markdown
#### **RUNNER.*** - Agent Runner infrastructure errors
- `RUNNER.AGENT_NOT_FOUND`: Agent not registered in registry.yaml
  - **Recoverable**: false
  - **Suggested Action**: "Add agent '{agent_name}' to .claude/agents/registry.yaml or check spelling"
- `RUNNER.VERSION_MISMATCH`: Agent version incompatible with constraint
  - **Recoverable**: false
  - **Suggested Action**: "Update skill constraint to match agent version or revert agent"
- `RUNNER.REGISTRY_INVALID`: registry.yaml is malformed or unreadable
  - **Recoverable**: false
  - **Suggested Action**: "Fix YAML syntax errors in .claude/agents/registry.yaml"
- `RUNNER.FILE_NOT_FOUND`: Agent file missing at registry path
  - **Recoverable**: false
  - **Suggested Action**: "Verify agent file exists at path: {path}"
```

---

#### W5: Incomplete Safety Validation for --yolo Flag

**Location**: Lines 516-546
**Rule**: v0.4 Section "Security & Safety" - Destructive Operations
**Severity**: WARNING

**Issue**:
The `--yolo` safety constraints are well-defined, but the plan lacks:
1. **Validation sequence**: No step-by-step validation checklist before auto-fix begins
2. **Rollback mechanism**: No mention of how to undo failed auto-fixes
3. **Approval mechanism**: No UX pattern for "almost auto" scenarios (show plan, one-click approve)
4. **Rate limiting**: No protection against --yolo being invoked repeatedly in error loops

**Impact**: --yolo implementations may be unsafe or lack necessary guardrails.

**Recommendation**:
Add a "Yolo Validation Checklist" subsection after line 546:

```markdown
### Yolo Validation Checklist

Before any --yolo auto-fix executes, validate:
1. ✅ Current worktree is clean (no uncommitted changes)
2. ✅ Target issue labeled "good first issue" or equivalent low-risk label
3. ✅ Target branch is NOT main/master or protected branch
4. ✅ Worktree location is under configured worktree root (not project root)
5. ✅ No other --yolo operation in progress (check lockfile)
6. ✅ User has not disabled --yolo via config (safety escape hatch)

**On validation failure**: Exit immediately with descriptive error; do NOT proceed.

**Rollback mechanism**: Create a backup commit before applying fixes; provide `/github-issue --rollback <operation-id>` to undo.

**Rate limiting**: Max 1 --yolo operation per 5 minutes (configurable); prevents error loops.
```

---

#### W6: Reference Files Lack Size/Content Specifications

**Location**: Lines 492-497
**Rule**: v0.4 Section "Progressive Disclosure & References"
**Severity**: WARNING

**Issue**:
The plan identifies two required reference files:
- `.claude/references/github-issue-apis.md`: "API schemas, auth patterns, rate limiting, example requests/responses"
- `.claude/references/github-issue-checklists.md`: "Triage steps, fix workflow phases, PR checklist, testing requirements"

However, it provides NO guidance on:
1. Target size for each reference file (v0.4 emphasizes context efficiency)
2. What level of detail is appropriate
3. How to balance completeness vs. conciseness
4. Whether these should link to external GitHub docs or duplicate content

**Impact**: Reference files may become bloated, defeating progressive disclosure goals.

**Recommendation**:
Update lines 492-497 with size and content targets:

```markdown
### Reference Files

#### Required Reference Files (must be created)

1. **`.claude/references/github-issue-apis.md`** (target: 2-3KB)
   - GitHub REST API v3 authentication (token vs gh CLI)
   - Rate limiting rules and headers
   - Essential endpoints: GET/POST/PATCH issues, GET labels, POST pull requests
   - Example request/response for each endpoint
   - Link to official GitHub API docs for comprehensive reference

2. **`.claude/references/github-issue-checklists.md`** (target: 1-2KB)
   - Issue triage decision tree (low/medium/high risk assessment)
   - Fix workflow phases (analyze → implement → test → PR)
   - PR creation checklist (branch naming, description template, labels)
   - Testing requirements by issue type (docs, bugfix, feature)

**Progressive disclosure**: Link to official GitHub docs rather than duplicating full API reference.
```

---

#### W7: Missing Guidance on Multi-File Agent Organization

**Location**: Lines 69-131 (Agent Inventory)
**Rule**: v0.4 Section "Agents: The Execution Layer" - Minimal Instructions
**Severity**: WARNING

**Issue**:
The plan mentions agent size targets (<8KB ideal, 10KB+ consider splitting) at line 109-111, but doesn't address:
1. When to split a large agent into multiple files vs. multiple agents
2. How to organize shared logic between agents (e.g., common GitHub API helpers)
3. Whether agents can include/reference other files (or if everything must be inline)

v0.4 emphasizes single-file agents, but complex domains may need shared utilities.

**Impact**: Implementers may create redundant code across agents or violate single-file constraints.

**Recommendation**:
Add a subsection after line 131:

```markdown
### Agent Organization Patterns

**Single-file rule**: Each agent is a single `.md` file; agents do NOT import from shared files.

**Handling shared logic**:
- **Option 1 (preferred)**: Duplicate small utility functions across agents (keep agents self-contained)
- **Option 2**: Extract shared logic to scripts in `.claude/scripts/` and invoke via Bash tool
- **Option 3**: Use Claude's built-in tools (Bash, Read, Write, Grep) rather than custom helpers

**When to split large agents**:
- Agent exceeds 10KB → Split by operation phase (analyze-agent, implement-agent, test-agent)
- Agent has >3 distinct workflows → Create one agent per workflow
- Agent requires different error handling per operation → Separate agents

**Anti-pattern**: DO NOT create "base agents" with shared frontmatter/instructions that other agents extend.
```

---

#### W8: Validation Script Missing Test Examples

**Location**: Lines 549-563
**Rule**: v0.4 Section "Version Management" - Validation script
**Severity**: WARNING

**Issue**:
The plan describes requirements for `scripts/validate-agents.py` (lines 549-563) and references the v0.4 example script (lines 642-669), but provides NO:
1. Example test cases showing expected pass/fail scenarios
2. Integration guidance for pre-commit hooks or CI pipelines
3. How to run the validation script locally during development

**Impact**: Developers may not test the validation script adequately or integrate it incorrectly.

**Recommendation**:
Add a subsection after line 563:

```markdown
### Validation Script Testing

**Test scenarios** (recommended test suite):
1. ✅ All agents have matching versions (should pass)
2. ❌ Agent missing `version` field in frontmatter (should fail)
3. ❌ Agent file version != registry version (should fail)
4. ❌ Agent in registry but file doesn't exist (should fail)
5. ❌ Agent file exists but not in registry (should warn)

**Local testing**:
```bash
# From project root
./scripts/validate-agents.py
echo "Exit code: $?"  # 0 = pass, 1 = fail
```

**CI Integration** (GitHub Actions example):
```yaml
- name: Validate Agent Versions
  run: ./scripts/validate-agents.py
```

**Pre-commit hook** (`.git/hooks/pre-commit`):
```bash
#!/bin/bash
./scripts/validate-agents.py || exit 1
```
```

---

### INFO Severity (Suggestions and Best Practices)

#### I1: Consider Adding Command Help Text Examples

**Location**: Lines 32-44 (Command Options)
**Rule**: v0.4 Best Practice - Clear documentation
**Severity**: INFO

**Issue**:
The plan lists command options but doesn't show what the `--help` output should look like for the `/github-issue` command.

**Suggestion**:
Add example help text after line 44:

```markdown
### Example Help Output

```
/github-issue --help

Manage GitHub issues end-to-end with list, fix, and PR workflows.

Usage:
  /github-issue [options]

Options:
  --list                    List and triage issues
  --fix --issue <id/url>    Fix specified issue
  --yolo                    Auto-pick easiest issue and run fix (safe defaults)
  --repo <owner/repo>       Target repository (default: current repo)
  --create                  Create new issue (interactive)
  --update <id>             Update existing issue fields/body
  --help                    Show this help message

Examples:
  /github-issue --list
  /github-issue --fix --issue 123
  /github-issue --yolo --repo anthropics/claude-code
```
```

This provides implementation guidance for the command stub.

---

#### I2: Open Questions Should Reference Decision Log

**Location**: Lines 565-585 (Open Questions)
**Rule**: v0.4 Best Practice - Documentation
**Severity**: INFO

**Issue**:
The "Open Questions" section lists 5 important decisions but doesn't indicate:
1. Who makes the final decision
2. Where decisions are documented once resolved
3. Timeline for resolution

**Suggestion**:
Add guidance at the end of the Open Questions section (after line 585):

```markdown
### Decision Process

**Decision authority**: Skill owner (TBD) with stakeholder review
**Timeline**: Resolve all open questions before status changes from "Proposed" to "Approved"
**Documentation**: Record decisions in `.claude/skills/github-issue/DECISIONS.md` with rationale

**Template**:
```
## Decision: Default Base Branch
**Date**: 2025-12-XX
**Decision**: Use `develop` if exists, else `main`
**Rationale**: Matches git-flow convention; safe for most repos
**Implementation**: Check for `develop` branch in agent logic
```
```

---

#### I3: Consider Adding Observability Section

**Location**: Lines 492-563 (between References and Safety sections)
**Rule**: v0.4 Section "Security & Safety" - Observability
**Severity**: INFO

**Issue**:
v0.4 line 763-764 recommends Agent Runner audit logs, but this plan doesn't address:
1. What should be logged during GitHub issue operations (issue IDs, branch names, PR URLs)
2. How to query/analyze audit logs after execution
3. Retention policy for audit logs

**Suggestion**:
Add a new section after line 497:

```markdown
## Observability & Audit

### Audit Logging

**Agent Runner logs** (`.claude/state/logs/agent-runner-<timestamp>.json`):
- Timestamp, agent name, version, file hash
- Parameters (redacted: no secrets)
- Outcome (success/failure), duration
- Correlation ID for multi-agent workflows

**Skill-specific logs** (`.claude/state/logs/github-issue-<timestamp>.json`):
- Issue ID, repository, operation type (list/fix/create)
- Branch created, PR URL (if applicable)
- Error codes and recovery actions taken

**Retention**: Auto-cleanup logs older than 30 days; configurable via `.claude/config.yaml`

**Query examples**:
```bash
# Find all failed operations
jq 'select(.outcome == "failure")' .claude/state/logs/*.json

# Find operations for issue #123
jq 'select(.issue_id == "123")' .claude/state/logs/github-issue-*.json
```
```

---

#### I4: Envelope Selection Could Be More Prescriptive

**Location**: Lines 213-248 (Envelope Selection Guidelines)
**Rule**: v0.4 Section "Structured Response Contracts" - Standard Response Schema
**Severity**: INFO

**Issue**:
The plan describes minimal vs. full envelopes but doesn't provide a clear decision tree. Line 106 says "unless duration/retry tracking is explicitly required" but doesn't define "explicitly required."

**Suggestion**:
Replace lines 213-248 with a decision flowchart:

```markdown
### Envelope Selection Decision Tree

```
START: Choose envelope for agent output
    ↓
Q1: Does operation take >5 seconds typically?
    Yes → Consider Full envelope (track duration)
    No → Continue
    ↓
Q2: Does operation retry on transient failures?
    Yes → Use Full envelope (track retry_count)
    No → Continue
    ↓
Q3: Can operation be canceled by user/timeout?
    Yes → Use Full envelope (track canceled, aborted_by)
    No → Continue
    ↓
Q4: Is operation idempotent and needs deduplication?
    Yes → Use Full envelope (track idempotency_key)
    No → Use Minimal envelope
```

**Result for this skill**:
- `gh-issue-intake-agent`: Minimal (fast, no retries)
- `gh-issue-fix-agent`: Minimal (unless fix takes >5s → Full)
- `gh-issue-pr-agent`: Minimal (straightforward API call)
```

This makes envelope selection deterministic.

---

#### I5: Add Example of Skill Formatting Agent JSON

**Location**: Lines 255-308 (Agent-Specific Data Contracts)
**Rule**: v0.4 Section "Agents: The Execution Layer" - Fenced JSON Output
**Severity**: INFO

**Issue**:
The plan shows agent JSON output format but doesn't demonstrate how skills transform this JSON into user-friendly messages.

**Suggestion**:
Add after line 308:

```markdown
### Example: Skill Transforms Agent JSON to User Message

**Agent returns** (gh-issue-intake-agent):
```json
{
  "success": true,
  "data": {
    "summary": "Retrieved 5 open issues, 2 marked 'good first issue'",
    "issues": [
      { "id": "123", "title": "Fix typo in README", "labels": ["documentation", "good first issue"], "risk": "low" }
    ]
  }
}
```

**Skill formats for user**:
```
Found 5 open issues in current repository:

🟢 Low Risk:
  #123: Fix typo in README
    Labels: documentation, good first issue
    Status: Unassigned
    Recommended for --yolo: Yes

Run `/github-issue --yolo` to auto-fix issue #123
```

**Why this matters**: Users never see raw JSON; skills provide context-rich presentation.
```

---

#### I6: Clarify Repository Detection Logic

**Location**: Lines 41-44 (Command Defaults), Line 38 (--repo flag)
**Rule**: v0.4 Best Practice - Clear defaults
**Severity**: INFO

**Issue**:
Line 42 states "Repository: current repo from git remote" but doesn't specify:
1. Which remote if multiple exist (origin? upstream?)
2. Behavior if not in a git repository
3. How to override if detected repo is wrong

**Suggestion**:
Expand line 42-44:

```markdown
- **Defaults**:
  - **Repository**: Detected from `git remote -v` (priority: origin > upstream > first listed)
    - If not in git repo: Error with `VALIDATION.INVALID_CONTEXT` ("Run from git repository or specify --repo")
    - To override: Use `--repo owner/repo` flag
  - **Base branch**: development/integration if exists, else main (configurable in `.claude/config.yaml`)
  - **Mode**: dry-run preview when possible (use --auto-fix to apply changes)
```

---

#### I7: Add Examples of Registry Constraint Mismatches

**Location**: Lines 168-194 (Registry Structure)
**Rule**: v0.4 Section "Version Management" - Validation
**Severity**: INFO

**Issue**:
The registry section explains constraints but doesn't show what happens when constraints are violated.

**Suggestion**:
Add after line 194:

```markdown
### Registry Constraint Examples

**Scenario 1: Agent updated but constraint not updated**
- Registry: `gh-issue-fix-agent: "0.x"`
- Agent frontmatter: `version: 0.2.0`
- Result: ✅ Passes (0.2.0 matches "0.x")

**Scenario 2: Agent version exceeds constraint**
- Registry: `gh-issue-fix-agent: "0.1.x"`
- Agent frontmatter: `version: 0.2.0`
- Result: ❌ Fails with `RUNNER.VERSION_MISMATCH`

**Scenario 3: Major version mismatch**
- Registry: `gh-issue-fix-agent: "0.x"`
- Agent frontmatter: `version: 1.0.0`
- Result: ❌ Fails with `RUNNER.VERSION_MISMATCH` (1.0.0 does not match "0.x")

**Best practice**: Update skill constraints in `registry.yaml` whenever agent major/minor versions change.
```

---

#### I8: Progressive Disclosure Section Could Link to v0.4

**Location**: Lines 466-491 (Progressive Disclosure & References)
**Rule**: v0.4 Section "Design Principles" - Progressive Disclosure
**Severity**: INFO

**Issue**:
The progressive disclosure section demonstrates correct patterns but doesn't reference where this concept comes from in v0.4.

**Suggestion**:
Add a note at line 468:

```markdown
### Load-On-Demand Pattern

> **Reference**: v0.4 Section "Design Principles" #5 - Progressive Disclosure
> Skills reveal complexity only as needed; reference files load on demand.

SKILL.md should **link** to references but NOT instruct Claude to always read them...
```

---

#### I9: Consider Adding Skill Size Target

**Location**: Lines 46-67 (Skill Definition)
**Rule**: v0.4 Section "Context Efficiency Patterns"
**Severity**: INFO

**Issue**:
The plan mentions agent size targets (lines 109-111) and reference file size targets (if W6 is addressed), but doesn't specify a size target for SKILL.md itself.

V0.4 emphasizes keeping skills concise as they're loaded into main context.

**Suggestion**:
Add after line 60:

```markdown
**Size target**: SKILL.md should be <2KB to minimize main context consumption. Use progressive disclosure—link to references rather than embedding details.

**Content breakdown**:
- Frontmatter: ~0.1KB
- Overview & Capabilities: ~0.3KB
- Agent Delegation table: ~0.4KB
- Usage instructions: ~0.5KB
- References (links only): ~0.2KB
- Total: ~1.5KB ✅
```

---

#### I10: Testing Phase Could Include Negative Test Cases

**Location**: Lines 629-650 (Testing Phase)
**Rule**: v0.4 Best Practice - Comprehensive testing
**Severity**: INFO

**Issue**:
The testing checklist at lines 637-642 focuses on happy path scenarios but lacks negative test cases (authentication failures, invalid inputs, etc.).

**Suggestion**:
Add after line 642:

```markdown
    - [ ] Test negative scenarios:
      - Invalid issue ID format (e.g., "abc" instead of "123")
      - Non-existent repository
      - Authentication failure (invalid/missing GITHUB_TOKEN)
      - Rate limit exceeded
      - Permission denied (read-only repository)
      - Dirty worktree state
      - Protected branch violation attempt
```

---

#### I11: Release Phase Could Include Packaging Checklist

**Location**: Lines 651-663 (Release Phase)
**Rule**: v0.4 Best Practice - Production readiness
**Severity**: INFO

**Issue**:
The release phase mentions packaging (lines 658-663) but doesn't specify what "package" means for skills in the Claude Code context.

**Suggestion**:
Expand lines 658-663:

```markdown
13. 🚀 **Package (Future)**
    - [ ] Create standalone skill package structure:
      - `.claude/skills/github-issue/` (complete)
      - `.claude/agents/` (subset: gh-issue-*.md only)
      - `.claude/agents/registry.yaml` (filtered to github-issue agents)
      - `README.md` (installation instructions)
    - [ ] Add package metadata (package.json or equivalent):
      ```json
      {
        "name": "github-issue-skill",
        "version": "0.1.0",
        "description": "Manage GitHub issues end-to-end",
        "author": "TBD",
        "requires": {
          "manage-worktree": "0.x"
        }
      }
      ```
    - [ ] Test installation in fresh `.claude/` directory
    - [ ] Write installation instructions (manual copy vs. future registry)
    - [ ] Publish to skill registry (when available)
```

---

#### I12: Consider Adding Skill Composition Example

**Location**: Lines 61-67 (Skill Content Structure)
**Rule**: v0.4 Section "Context Efficiency Patterns" - Multi-Step Workflows
**Severity**: INFO

**Issue**:
The plan shows how this skill delegates to agents (lines 133-163) but doesn't demonstrate how this skill might compose with other skills (e.g., `manage-worktree`).

**Suggestion**:
Add after line 67:

```markdown
### Skill Composition

This skill depends on the `manage-worktree` skill for git operations. Example workflow:

```
User: "Fix issue #123"
    ↓
/github-issue skill:
  1. Delegate to gh-issue-intake-agent (fetch issue details)
  2. Delegate to manage-worktree skill (create clean worktree)
  3. Delegate to gh-issue-fix-agent (implement fix)
  4. Delegate to gh-issue-pr-agent (create PR)
  5. Delegate to manage-worktree skill (cleanup)
```

**Registry declares dependency**:
```yaml
skills:
  github-issue:
    depends_on:
      gh-issue-intake-agent: "0.x"
      gh-issue-fix-agent: "0.x"
      gh-issue-pr-agent: "0.x"
      manage-worktree: "0.x"   # External skill dependency
```

**Skill invocation from SKILL.md**:
"To create a clean worktree, use the manage-worktree skill with parameters: branch={branch}, base={base}"
```

This clarifies skill-to-skill delegation vs. skill-to-agent delegation.

---

## Compliance Matrix

| Guideline Area | Status | Notes |
|----------------|--------|-------|
| **Frontmatter Structure** | ⚠️ Warning | E1, E2: Command/skill version inconsistencies |
| **Registry & Dependencies** | ⚠️ Warning | W3: Constraint format ambiguity for 0.x |
| **Data Contracts (Fenced JSON)** | ✅ Compliant | All agents return fenced JSON with proper envelopes |
| **Error Contracts** | ⚠️ Warning | W4: Missing RUNNER.* error namespace |
| **Safety & --yolo** | ⚠️ Warning | W5: Incomplete validation checklist |
| **Progressive Disclosure** | ✅ Compliant | Correct link pattern; references load on-demand |
| **File Layout** | ⚠️ Warning | W2: Missing commands/ in file structure |
| **Agent Runner Pattern** | ⚠️ Warning | W1: Missing implementation details |
| **Version Management** | ⚠️ Warning | W8: Missing validation test examples |
| **Context Efficiency** | ✅ Compliant | Proper agent size targets; minimal envelopes |
| **Agent Organization** | ⚠️ Warning | W7: Missing multi-file guidance |
| **Reference Files** | ⚠️ Warning | W6: Missing size/content specs |

---

## Recommendations by Priority

### Before Status Change to "Proposed"
1. **[E1, E2]** Remove all command/skill versioning references (CRITICAL)
2. **[W1]** Add Agent Runner implementation details section
3. **[W2]** Update file layout to include commands/ directory
4. **[W3]** Clarify 0.x version constraint semantics
5. **[W4]** Add RUNNER.* error namespace
6. **[W5]** Add --yolo validation checklist

### Before Implementation Begins
7. **[W6]** Add reference file size/content specifications
8. **[W7]** Add agent organization patterns
9. **[W8]** Add validation script test examples
10. **[I1-I3]** Add command help text, decision log, observability section

### Nice-to-Have Enhancements
11. **[I4-I12]** Address remaining INFO items for completeness

---

## Positive Observations

This v2 plan demonstrates exceptional quality in several areas:

1. **Comprehensive Error Handling**: 4 well-defined error namespaces with recovery strategies
2. **Strong Safety Boundaries**: Excellent --yolo constraints with clear allowed/forbidden operations
3. **Clear Data Contracts**: All agents have specific input/output examples
4. **Progressive Disclosure**: Correct link pattern; avoids forcing reference reads
5. **Explicit Frontmatter Examples**: Clear differentiation between command/skill/agent metadata
6. **Registry Integration**: Proper dependency constraints with version ranges
7. **Agent Size Awareness**: Acknowledges size targets and splitting strategies
8. **Worktree Hygiene**: Reuses existing manage-worktree skill; no duplication
9. **Improvements from v1**: Addresses all critical issues from previous review

---

## Conclusion

The GitHub Issue Skill v2 plan is **well-conceived and substantially compliant** with v0.4 guidelines. The 2 ERROR items are straightforward to fix (remove version references for commands/skills), and the 8 WARNING items are quality improvements rather than fundamental flaws.

**Recommended Path Forward**:
1. Address E1, E2, W1-W5 immediately (estimated: 2-3 hours)
2. Upgrade plan status from "Preliminary" to "Proposed"
3. Circulate for stakeholder review
4. Address W6-W8 based on stakeholder feedback
5. Upgrade to "Approved" and begin implementation
6. Consider INFO items (I1-I12) as continuous improvements during implementation

**Overall Assessment**: This is a **high-quality plan** that demonstrates strong understanding of v0.4 architecture. With minor corrections, it will serve as an excellent reference for implementation teams.

---

**Report Generated**: 2025-12-03
**Review Methodology**: Systematic comparison against v0.4 guidelines with severity-based categorization
**Next Review**: After ERROR/WARNING items are addressed and status changes to "Proposed"
