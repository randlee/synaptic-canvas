# GitHub Issue Skill Plan Review Report

**Target**: `/Users/randlee/Documents/github/synaptic-canvas/plans/github-issue-skill.md`
**Reviewer**: Claude Code (Sonnet 4.5)
**Guidelines**: v0.4 (`docs/claude-code-skills-agents-guidelines-0.4.md`)
**Date**: 2025-12-02
**Status**: Preliminary Review Complete

---

## Executive Summary

The GitHub issue skill plan demonstrates **good foundational understanding** of v0.4 guidelines with strong safety practices, correct agent versioning (0.1.0), and proper progressive disclosure patterns. However, the plan requires **clarifications and corrections** in several areas before implementation:

**Overall Assessment**: ⚠️ **NEEDS REVISION** before implementation

**Compliance Score**: 7/10
- ✅ Agent versioning (0.1.0) correctly specified
- ✅ Safety practices align with v0.4
- ✅ Progressive disclosure pattern correct
- ⚠️ Frontmatter requirements incomplete
- ⚠️ Registry structure underspecified
- ⚠️ Fenced JSON emphasis missing
- ⚠️ Error contracts need definition

---

## Critical Issues (Must Fix Before Implementation)

### 1. ❌ Command Frontmatter Misunderstanding
**Location**: Line 44 (implicit in file layout)
**Rule**: v0.4 Section 6 - Agent frontmatter requirements
**Severity**: ERROR

**Issue**: Plan doesn't clarify that commands DO NOT have version frontmatter.

**Current State**: Unclear if command will have version field
**Required State**:
```yaml
# .claude/commands/github-issue.md
---
name: github-issue
description: Manage GitHub issues end-to-end with list, fix, and PR workflows
---
```

**Impact**: Commands are invoked directly by users and don't need versioning. Only agents require version frontmatter for registry management.

---

### 2. ❌ Registry Structure Incomplete
**Location**: Line 32
**Rule**: v0.4 Section 8.6 - Version Management
**Severity**: ERROR

**Issue**: Plan mentions registry but doesn't specify the complete structure including skill dependency constraints.

**Current State**:
```markdown
- Agent Runner required; resolve via `.claude/agents/registry.yaml` with versions.
```

**Required State**:
```yaml
# .claude/agents/registry.yaml
agents:
  gh-issue-intake-agent:
    version: 0.1.0
    path: .claude/agents/gh-issue-intake-agent.md
  gh-issue-fix-agent:
    version: 0.1.0
    path: .claude/agents/gh-issue-fix-agent.md
  gh-issue-pr-agent:
    version: 0.1.0
    path: .claude/agents/gh-issue-pr-agent.md

skills:
  github-issue:
    depends_on:
      gh-issue-intake-agent: "0.x"
      gh-issue-fix-agent: "0.x"
      gh-issue-pr-agent: "0.x"
```

**Impact**: Without skill dependency constraints, the registry cannot enforce version compatibility between skills and agents.

---

### 3. ❌ Fenced JSON Requirement Not Emphasized
**Location**: Lines 34-41 (Data Contracts section)
**Rule**: v0.4 Section 8.1 - Standard Response Schema
**Severity**: ERROR

**Issue**: Plan shows minimal envelope correctly but doesn't explicitly state that ALL JSON must be fenced in markdown code blocks.

**Current State**:
```markdown
- Minimal envelope (fenced JSON):
```json
{ "success": true, "data": { "summary": "", "actions": [] }, "error": null }
```
```

**Required State**: Add explicit instruction:
```markdown
## Data Contracts

**CRITICAL**: All agents MUST return JSON wrapped in markdown code fences:

````markdown
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```
````

This is mandatory for reliable parsing by skills.
```

**Impact**: Unfenced JSON can cause parsing failures in skill orchestration layer.

---

### 4. ❌ Envelope Type Guidelines Missing
**Location**: Lines 34-41 (Data Contracts section)
**Rule**: v0.4 Section 8.1 - Standard Response Schema
**Severity**: ERROR

**Issue**: Plan doesn't specify when to use minimal vs full envelope.

**Required Addition**:
```markdown
## Envelope Selection Guidelines

**Minimal Envelope** (use for simple agents):
- gh-issue-intake-agent: fetch metadata, no retries needed
- gh-issue-pr-agent: create PR, straightforward operation
- Structure: { success, data, error }

**Full Envelope** (use ONLY if needed):
- gh-issue-fix-agent: IF tracking duration/retries is required
- Structure: { success, canceled, aborted_by, data, error, metadata }

**Advanced Metadata** (avoid unless specifically needed):
- timestamp, max_tool_calls, idempotency_key
- Only add if explicit requirement exists
```

**Impact**: Without guidance, agents may include unnecessary metadata fields, increasing token consumption.

---

## Major Issues (Address Before First Release)

### 5. ⚠️ SKILL.md Frontmatter Underspecified
**Location**: Line 45
**Rule**: v0.4 Section 5 - Skills: The Discovery Layer
**Severity**: WARNING

**Issue**: Plan mentions SKILL.md but doesn't clarify its frontmatter requirements.

**Required Clarification**:
```markdown
## File Layout

- Skill: `.claude/skills/github-issue/SKILL.md`
  - Frontmatter: name, description (NO version field for skills)
  - Example:
    ```yaml
    ---
    name: github-issue
    description: Manage GitHub issues end-to-end with list/read, auto-fix,
      and PR creation. Use when triaging issues, implementing fixes, or
      automating issue workflows.
    ---
    ```
```

---

### 6. ⚠️ Error Contract Definition Missing
**Location**: Lines 34-41 (Data Contracts section)
**Rule**: v0.4 Section 9 - Error Handling and Validation
**Severity**: WARNING

**Issue**: Plan shows error structure but doesn't define error code namespaces or recovery strategies.

**Required Addition**:
```markdown
## Error Contracts

All agents must return structured errors with this format:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "NAMESPACE.CODE",
    "message": "Human-friendly error description",
    "recoverable": boolean,
    "suggested_action": "Next step for user/skill"
  }
}
```

### Error Code Namespaces

**GITHUB.*** - GitHub API errors
- `GITHUB.AUTH_FAILED`: Invalid/expired GitHub token
- `GITHUB.RATE_LIMIT`: API rate limit exceeded
- `GITHUB.NOT_FOUND`: Issue/repo not found
- `GITHUB.PERMISSION_DENIED`: Insufficient permissions

**WORKTREE.*** - Worktree operation errors
- `WORKTREE.DIRTY`: Uncommitted changes present
- `WORKTREE.ALREADY_EXISTS`: Worktree path already exists
- `WORKTREE.INVALID_BASE`: Base branch doesn't exist

**VALIDATION.*** - Input validation errors
- `VALIDATION.INVALID_ISSUE_ID`: Issue ID format invalid
- `VALIDATION.INVALID_REPO`: Repository format invalid

**EXECUTION.*** - Runtime errors
- `EXECUTION.TIMEOUT`: Agent exceeded timeout
- `EXECUTION.TOOL_LIMIT`: Max tool calls reached
```

---

### 7. ⚠️ Agent Runner Invocation Pattern Unclear
**Location**: Line 32
**Rule**: v0.4 Section 2 - How Skills Invoke Agents
**Severity**: WARNING

**Issue**: Plan mentions "Agent Runner required" but doesn't explain the invocation pattern.

**Required Addition to SKILL.md Section**:
```markdown
## Agent Delegation Pattern

Skills invoke agents via Agent Runner (which uses Task tool under the hood).

**Invocation Template**:
```markdown
Use the Agent Runner to invoke `<agent-name>` as defined in
`.claude/agents/registry.yaml` with parameters:
- param1: value1
- param2: value2
```

**What Agent Runner Does**:
1. Resolves agent path and version from registry.yaml
2. Validates version constraints (e.g., "0.x" matches 0.1.0)
3. Computes agent file hash for audit
4. Launches Task tool with agent instructions
5. Writes redacted audit record to .claude/state/logs/
6. Returns fenced JSON result to skill

**Example**:
```markdown
To analyze an issue:
Use the Agent Runner to invoke `gh-issue-intake-agent` with parameters:
- issue_id: "123"
- repo: "owner/repo"
```
```

---

### 8. ⚠️ References Load-On-Demand Pattern Missing
**Location**: Line 47
**Rule**: v0.4 Section 12 - File Organization
**Severity**: WARNING

**Issue**: Plan uses .claude/references/ correctly but doesn't specify on-demand loading pattern.

**Required Addition**:
```markdown
## Progressive Disclosure & References

SKILL.md should **link** to references but NOT instruct Claude to always read them.
References load **on-demand** when needed.

**Correct Pattern**:
```markdown
## GitHub API Integration

This skill uses GitHub's REST API v3. For detailed API schemas and examples,
see `.claude/references/github-issue-apis.md`.

For issue triage checklists and fix workflows, see
`.claude/references/github-issue-checklists.md`.
```

**Incorrect Pattern** (avoid):
```markdown
1. First, read .claude/references/github-issue-apis.md
2. Then, read .claude/references/github-issue-checklists.md
3. Then, invoke the agent
```

This keeps SKILL.md concise and loads references only when agents/skills need them.
```

---

## Minor Issues (Recommendations)

### 9. ℹ️ Validation Script Implementation
**Location**: Line 70
**Rule**: v0.4 Section 8.6 - Version Management
**Severity**: INFO

**Recommendation**: Ensure `scripts/validate-agents.py` uses the robust frontmatter-aware implementation from v0.4 guidelines (lines 641-669).

**Key Requirements**:
- Extract frontmatter using awk
- Parse YAML with yq
- Compare file version vs registry version
- Check for missing versions
- Report mismatches

---

### 10. ℹ️ Yolo Flag Safety Constraints
**Location**: Line 22
**Rule**: v0.4 Section 9.2 - Execution Flags
**Severity**: INFO

**Current State**: Plan includes `--yolo` flag for auto-pick and fix.

**Required Safety Note**:
```markdown
## Safety Constraints for --yolo

Per v0.4 guidelines, --yolo must respect safety boundaries:

**ALLOWED auto-fixes**:
- Pick "good first issue" labeled issues
- Apply fixes to non-protected branches
- Create worktrees in safe locations
- Run tests to validate changes

**FORBIDDEN auto-fixes**:
- Push directly to main/master without approval
- Bypass authentication failures
- Override protected branch rules
- Delete data or worktrees without confirmation
- Bypass dirty worktree checks

Default behavior: --yolo creates PR but does NOT push or merge.
```

---

### 11. ℹ️ Agent Responsibility Review
**Location**: Lines 29-31
**Rule**: v0.4 Section 6.1 - Single Responsibility
**Severity**: INFO

**Current State**: `gh-issue-fix-agent` handles "propose/code fix; may call codegen; returns patch summary, risks, tests."

**Consideration**: This may be multiple responsibilities. Consider splitting:
1. `gh-issue-analyze-agent`: Read issue, determine fix approach, identify risks
2. `gh-issue-implement-agent`: Apply code changes, generate patches
3. `gh-issue-test-agent`: Run tests, validate changes

**Current Design is Acceptable If**:
- Agent stays under 8KB
- Execution path remains straightforward
- No complex branching logic

**Monitor for Split Triggers**:
- Agent exceeds 10KB
- More than 3 distinct phases
- Complex error recovery logic

---

## Strengths of Current Plan

### ✅ What's Done Well

1. **Version Markers Correct**
   - All agents specify 0.1.0 in frontmatter ✓
   - Matches v0.4 initial version convention ✓

2. **Safety Practices Strong**
   - Clean worktree validation required ✓
   - No auto-push without confirmation ✓
   - Protected branch respect ✓
   - Input validation before agent calls ✓

3. **Progressive Disclosure Pattern**
   - SKILL.md concise, references for details ✓
   - API schemas in separate files ✓
   - Checklists externalized ✓

4. **Data Contract Structure**
   - Minimal envelope correctly specified ✓
   - Success/error fields present ✓
   - Operation-specific data sections ✓

5. **Orchestration Awareness**
   - Agent Runner mentioned ✓
   - Worktree skill reuse planned ✓
   - Registry validation in next actions ✓

6. **Command UX Design**
   - Clear help text required ✓
   - Safe defaults specified ✓
   - Options well-organized ✓

---

## Recommended Changes Summary

### High Priority (Before Implementation Starts)

1. **Clarify Frontmatter Requirements**
   ```markdown
   - Commands: name, description (no version)
   - Skills: name, description (no version)
   - Agents: name, version, description
   ```

2. **Complete Registry Specification**
   - Add agents section with paths
   - Add skills section with dependency constraints
   - Specify version range format ("0.x")

3. **Emphasize Fenced JSON**
   - Add "CRITICAL" marker
   - Show example with fencing
   - Explain parsing requirement

4. **Define Envelope Selection Rules**
   - Minimal for simple agents
   - Full only when metadata needed
   - Avoid advanced fields by default

5. **Specify Error Contract**
   - Define error code namespaces
   - Include recoverable field
   - Add suggested_action field

### Medium Priority (Before First Release)

6. **Document Agent Runner Pattern**
   - Invocation template
   - What Runner does
   - Example usage

7. **Clarify Reference Loading**
   - Link, don't auto-read
   - On-demand pattern
   - Keep SKILL.md concise

8. **Add Yolo Safety Constraints**
   - What's allowed
   - What's forbidden
   - Default behavior

### Low Priority (Ongoing Improvements)

9. **Verify Validation Script**
   - Use v0.4 frontmatter-aware version
   - Test with sample agents
   - Add to CI pipeline

10. **Monitor Agent Complexity**
    - Watch fix-agent size
    - Split if exceeds 10KB
    - Keep execution straightforward

---

## Next Actions (Updated)

### Immediate (Before Writing Code)

1. ✅ **Update Plan Document**
   - [ ] Add frontmatter clarifications (commands vs skills vs agents)
   - [ ] Expand registry.yaml specification with skill constraints
   - [ ] Add fenced JSON emphasis with examples
   - [ ] Define envelope selection guidelines
   - [ ] Specify error code namespaces and contracts

2. ✅ **Review and Approve**
   - [ ] Get plan approval from team/owner
   - [ ] Mark status as "Approved" in plan
   - [ ] Create tracking issue/ticket

### Implementation Phase

3. 📝 **Create Stubs**
   - [ ] Command: `.claude/commands/github-issue.md` (name/description frontmatter)
   - [ ] Skill: `.claude/skills/github-issue/SKILL.md` (name/description frontmatter)
   - [ ] Agents: All three with name/version/description frontmatter (0.1.0)

4. 📝 **Create Registry**
   - [ ] Write `.claude/agents/registry.yaml` with complete structure
   - [ ] Add all three agents with versions and paths
   - [ ] Add skill dependency constraints

5. 📝 **Create References**
   - [ ] `.claude/references/github-issue-apis.md` (API schemas)
   - [ ] `.claude/references/github-issue-checklists.md` (triage/fix steps)

6. 🔍 **Implement Validation**
   - [ ] Copy v0.4 validate-agents.py to `scripts/`
   - [ ] Test validation with stub agents
   - [ ] Add to pre-commit hook or CI

### Testing Phase

7. ✅ **Validate Implementation**
   - [ ] Run `scripts/validate-agents.py`
   - [ ] Test Agent Runner invocation from SKILL
   - [ ] Verify fenced JSON parsing
   - [ ] Test error contract handling

8. 📋 **Documentation Review**
   - [ ] Verify SKILL.md is concise (<2KB target)
   - [ ] Check references load on-demand
   - [ ] Validate agent size (<8KB target)
   - [ ] Review command help text

---

## Appendix: Guidelines Compliance Checklist

### Architecture (v0.4 Section 2)
- [x] Two-tier skill/agent separation understood
- [x] Skills provide abstraction, agents provide implementation
- [ ] Agent Runner invocation pattern documented (needs addition)
- [x] Context efficiency principles applied

### Skills (v0.4 Section 5)
- [ ] SKILL.md frontmatter clarified (needs correction)
- [x] Progressive disclosure planned
- [x] Gerund naming convention used
- [x] Description includes triggers

### Agents (v0.4 Section 6)
- [x] Single responsibility maintained
- [x] YAML frontmatter with version specified (0.1.0)
- [ ] Fenced JSON output emphasized (needs addition)
- [x] Agent size targets reasonable
- [ ] Agent template can be followed (needs clarification)

### Structured Responses (v0.4 Section 8)
- [x] Minimal envelope structure correct
- [ ] Envelope selection guidelines needed (missing)
- [ ] Error object structure incomplete (needs error codes)
- [x] Success/error fields present

### Version Management (v0.4 Section 8.6)
- [x] Agents declare version in frontmatter
- [ ] Registry structure incomplete (needs skill constraints)
- [ ] Validation script needs v0.4 implementation
- [x] External validation approach correct

### Error Handling (v0.4 Section 9)
- [ ] Error code namespaces undefined (needs addition)
- [ ] Recoverable flag not specified
- [ ] Suggested_action field not planned
- [x] Validation/dry-run mode planned

### Security & Safety (v0.4 Section 10)
- [x] Secret handling via environment variables
- [x] Destructive operations require confirmation
- [x] Validation mode supported
- [ ] Yolo safety constraints need specification

### File Organization (v0.4 Section 12)
- [x] Skills directory structure correct
- [x] Agents directory structure correct
- [x] Registry location correct
- [x] References directory planned

### Best Practices (v0.4 Section 13)
- [ ] Contract-first design (needs complete error contract)
- [x] Version in frontmatter
- [ ] Fence all JSON (needs emphasis)
- [x] Single responsibility
- [x] Prefer Agent Runner

---

## Conclusion

The GitHub issue skill plan is **well-structured and safety-conscious** but requires **clarifications and additions** before implementation. The plan demonstrates understanding of v0.4's core concepts but needs explicit details on frontmatter requirements, registry structure, fenced JSON emphasis, envelope selection, and error contracts.

**Recommendation**: **UPDATE PLAN** with the high-priority changes listed above, then proceed to implementation. The architectural approach is sound; the gaps are in specification details rather than fundamental design flaws.

**Estimated Revision Time**: 2-3 hours to update plan with all recommended changes.

**Next Reviewer**: Plan owner should review this report and update the plan document accordingly.

---

**Report Generated**: 2025-12-02
**Reviewer**: Claude Code (Sonnet 4.5)
**Guidelines Version**: v0.4
**Report Path**: `/Users/randlee/Documents/github/synaptic-canvas/reports/skill-reviews/github-issue-report.md`
