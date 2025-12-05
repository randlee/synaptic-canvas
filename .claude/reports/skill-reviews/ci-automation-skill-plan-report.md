# CI Automation Skill Plan Review Report

**Plan:** `/Users/randlee/Documents/github/synaptic-canvas/plans/ci-automation-skill-plan.md`
**Status:** Preliminary (v0.1.0)
**Review Date:** 2025-01-22
**Guidelines Version:** v0.4
**Reviewer:** Claude Code (Skill Review Agent)

---

## Executive Summary

The CI Automation Skill plan is **well-structured and mostly compliant** with v0.4 guidelines. It demonstrates strong understanding of skill/agent architecture, safety concerns, and progressive disclosure principles. However, several **critical issues** must be addressed before implementation:

- **Missing registry entries** for 6 planned agents
- **No fenced JSON examples** in data contracts section
- **Insufficient error handling specification** for agent boundaries
- **Missing progressive disclosure guidance** for SKILL.md size constraints
- **Incomplete Agent Runner invocation patterns**

**Recommendation:** Address the 3 ERROR-level and 5 WARNING-level issues before proceeding to implementation phase. The plan is solid but needs refinement in contract specifications and registry alignment.

---

## Compliance Assessment

### Overall Score: 7.5/10

| Category | Score | Notes |
|----------|-------|-------|
| Architecture Alignment | 9/10 | Excellent skill/agent separation |
| Version Management | 4/10 | Version present but no registry entries |
| Output Contracts | 5/10 | Described but not fenced/complete |
| Safety & Approvals | 8/10 | Good default-safe behavior |
| Progressive Disclosure | 7/10 | Good intent, needs size guidance |
| Agent Design | 8/10 | Well-scoped single-responsibility agents |

---

## Issues Detected

### Severity Levels
- **ERROR**: Must fix before implementation
- **WARNING**: Should fix for best practices
- **INFO**: Consider for improvement

---

### ERROR Issues (3)

#### E1: Missing Registry Entries
**Severity:** ERROR
**Rule:** `registry-alignment`
**Location:** Lines 41-47 (Agents section)

**Description:**
The plan proposes 6 agents but none are defined in `.claude/agents/registry.yaml`. Per v0.4 guidelines, all agents must be registered before invocation.

**Current State:**
```yaml
# registry.yaml does not contain:
# - ci-pull-agent
# - ci-build-agent
# - ci-test-agent
# - ci-fix-agent
# - ci-root-cause-agent
# - ci-pr-agent
```

**Required Fix:**
Add to `.claude/agents/registry.yaml`:
```yaml
agents:
  ci-pull-agent:
    version: 0.1.0
    path: .claude/agents/ci-pull-agent.md
  ci-build-agent:
    version: 0.1.0
    path: .claude/agents/ci-build-agent.md
  ci-test-agent:
    version: 0.1.0
    path: .claude/agents/ci-test-agent.md
  ci-fix-agent:
    version: 0.1.0
    path: .claude/agents/ci-fix-agent.md
  ci-root-cause-agent:
    version: 0.1.0
    path: .claude/agents/ci-root-cause-agent.md
  ci-pr-agent:
    version: 0.1.0
    path: .claude/agents/ci-pr-agent.md

skills:
  ci-automation:
    depends_on:
      ci-pull-agent: 0.x
      ci-build-agent: 0.x
      ci-test-agent: 0.x
      ci-fix-agent: 0.x
      ci-root-cause-agent: 0.x
      ci-pr-agent: 0.x
```

---

#### E2: Unfenced JSON in Data Contracts
**Severity:** ERROR
**Rule:** `json-fencing-required`
**Location:** Lines 49-55 (Data Contracts section)

**Description:**
The plan shows JSON examples without markdown code fences. Per v0.4 guidelines, ALL JSON output must be wrapped in fenced code blocks (````json ... ```).

**Current (Line 51-53):**
```
```json
{ "success": true, "data": { "summary": "", "actions": [] }, "error": null }
```
```

**Problem:** The markdown rendering is ambiguous. The plan document itself should demonstrate proper fencing.

**Required Fix:**
Replace line 51-53 with:
````markdown
All agents return fenced JSON using the minimal envelope:

```json
{
  "success": true,
  "data": {
    "summary": "Operation completed successfully",
    "actions": ["action1", "action2"]
  },
  "error": null
}
```
````

---

#### E3: Incomplete Error Contract Specification
**Severity:** ERROR
**Rule:** `error-boundary-clarity`
**Location:** Lines 49-55 (Data Contracts section)

**Description:**
The data contract section doesn't specify the error object structure when `success: false`. This is critical for skill error handling.

**Current State:**
Only success case is shown. No error schema defined.

**Required Fix:**
Add to Data Contracts section (after line 55):
````markdown
### Error Response Schema

When `success: false`, agents must return:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "NAMESPACE.CODE",
    "message": "Human-friendly error description",
    "recoverable": false,
    "suggested_action": "What the user/skill should do next"
  }
}
```

#### Error Code Namespaces
- `BUILD.*` - Build-related errors (BUILD.COMPILE_FAILED, BUILD.DEPENDENCY_MISSING)
- `TEST.*` - Test-related errors (TEST.ASSERTION_FAILED, TEST.TIMEOUT)
- `GIT.*` - Git operation errors (GIT.MERGE_CONFLICT, GIT.PROTECTED_BRANCH)
- `PR.*` - PR creation errors (PR.NO_CHANGES, PR.AUTHENTICATION_FAILED)
- `EXECUTION.*` - Runtime errors (EXECUTION.TIMEOUT, EXECUTION.TOOL_LIMIT)
```
````

---

### WARNING Issues (5)

#### W1: No Agent Runner Invocation Pattern
**Severity:** WARNING
**Rule:** `agent-runner-preferred`
**Location:** Lines 27-33 (Default Flow section)

**Description:**
The plan mentions "invoke fix agent via Task tool" but doesn't specify using Agent Runner for registry enforcement and audit logging.

**Current (Line 29):**
> "invoke fix agent via Task tool"

**Recommended Fix:**
Update flow description to:
```markdown
3) If build fails and fix is straightforward, invoke ci-fix-agent via Agent Runner
   (enforces registry.yaml path/version, logs audit record), then restart at step 2.
```

**Example for SKILL.md:**
```markdown
To invoke the fix agent:
1. Use Agent Runner to invoke `ci-fix-agent` as defined in `.claude/agents/registry.yaml`
2. Pass parameters: error_type, error_message, affected_files
3. Agent returns fenced JSON with patch_summary and risk assessment
4. Apply fixes if risk is "low" and user confirms
```

---

#### W2: Missing SKILL.md Size Constraint Guidance
**Severity:** WARNING
**Rule:** `progressive-disclosure`
**Location:** Line 59 (File Layout section)

**Description:**
The plan states "SKILL.md (<2KB, references heavy)" but doesn't specify what content should be in SKILL.md vs. reference files.

**Current (Line 59):**
> Skill: `.claude/skills/ci-automation/SKILL.md` (<2KB, references heavy)

**Recommended Enhancement:**
Add after line 59:
```markdown
**SKILL.md Content Guidance:**
- Frontmatter (name, description, version) - ~100 bytes
- Capabilities list - ~200 bytes
- Agent delegation table - ~300 bytes
- Usage workflow (high-level) - ~400 bytes
- Link to references/ci-automation-commands.md for detailed command specs
- Link to references/ci-automation-checklists.md for gate criteria
- Total: ~1KB, leaving room for examples

Keep heavy content in references:
- Build/test command detection heuristics → references/
- Detailed fix heuristics and patterns → references/
- Troubleshooting guides → references/
```

---

#### W3: Insufficient Parallel Execution Guidance
**Severity:** WARNING
**Rule:** `parallel-guardrails`
**Location:** Lines 27-33 (Default Flow section)

**Description:**
The flow is sequential, which is appropriate for CI gates, but the plan doesn't address whether any agents could run in parallel (e.g., `ci-build-agent` + `ci-test-agent` on separate worktrees).

**Recommendation:**
Add to Scope & Defaults section (after line 39):
```markdown
## Parallelism Policy
- **Sequential by default**: Pull → Build → Test → Fix → PR (gates must pass in order)
- **Parallel option** (future enhancement): Allow `--parallel-worktrees` to run build+test
  in isolated worktrees simultaneously. Cap concurrency at 2, set 120s timeout per agent.
- **Not implemented in v0.1.0**: Focus on reliable sequential flow first.
```

---

#### W4: No Explicit --help Flag Behavior
**Severity:** WARNING
**Rule:** `safety-help-clarity`
**Location:** Lines 17-24 (Proposed Command section)

**Description:**
Flags list includes `--help` but doesn't specify what it outputs or whether it exits immediately.

**Current (Line 24):**
> - `--help`

**Recommended Fix:**
Replace line 24 with:
```markdown
- `--help`: Display usage, flag descriptions, and examples. Exits without execution.

  Example output:
  ```
  /ci-automation - Run end-to-end CI quality gates

  Usage:
    /ci-automation [flags]

  Flags:
    --build              Run pull + build only (skip tests/PR)
    --test               Run pull + build + test (skip commit/push/PR)
    --dest <branch>      Override target branch for PR (default: inferred from tracking)
    --src <branch>       Override source branch/worktree (default: current branch)
    --allow-warnings     Allow warnings to pass quality gates
    --yolo               Enable auto-commit/push/PR (requires clean gates)
    --help               Show this help message

  Examples:
    /ci-automation --test          # Validate build+tests without PR
    /ci-automation --yolo          # Full automation (use with caution)
    /ci-automation --dest main     # PR directly to main (rare)
  ```
```

---

#### W5: Missing Validation Agent in Plan
**Severity:** WARNING
**Rule:** `validation-gate-pattern`
**Location:** Lines 41-47 (Agents section)

**Description:**
The plan includes build/test/fix/root-cause/pr agents but no dedicated **validation agent** to check preconditions before expensive operations.

**Rationale:**
Per v0.4 Pattern 3 (Validation Gates), it's recommended to validate environment/config/permissions before running full CI flow.

**Recommended Addition:**
Add `ci-validate-agent` (0.1.0):
```markdown
## Agents (updated minimal set, v0.1.0)
- `ci-validate-agent`: Check prerequisites (git clean, config present, auth valid); report blocking issues.
- `ci-pull-agent`: pull upstream, attempt straightforward conflict resolution; report status.
- [... rest of agents ...]
```

**Updated Flow:**
```markdown
## Default Flow (no flags)
0) **VALIDATION**: Invoke ci-validate-agent to check:
   - Repository is clean (no uncommitted changes unless --allow-dirty flag)
   - Config exists or can be inferred
   - Auth tokens present for PR creation
   - Stop immediately if validation fails with actionable error
1) Pull from inferred upstream branch...
[... rest of flow ...]
```

---

### INFO Issues (4)

#### I1: Consider Idempotency Keys for Retry Safety
**Severity:** INFO
**Rule:** `advanced-metadata-optional`
**Location:** Lines 49-55 (Data Contracts section)

**Description:**
For agents that create resources (PR, commits), consider supporting idempotency keys to prevent duplicate operations on retry.

**Enhancement Suggestion:**
```markdown
### Advanced Metadata (Optional for v0.1.0, recommended for v0.2.0)

Agents may include:
```json
{
  "metadata": {
    "idempotency_key": "ci-automation-20250122-abc123",
    "correlation_id": "user-session-xyz"
  }
}
```

Use cases:
- `ci-pr-agent`: Use idempotency key to avoid duplicate PRs if invoked twice
- `ci-fix-agent`: Use correlation_id to group related fix attempts
```

---

#### I2: Config File Detection Examples
**Severity:** INFO
**Rule:** `progressive-disclosure`
**Location:** Line 62 (References section)

**Description:**
The plan mentions "detection guidance for common stacks (.NET, Python, Node)" but doesn't provide examples.

**Enhancement Suggestion:**
Add to `.claude/references/ci-automation-commands.md`:
```markdown
## Stack Detection Heuristics

### .NET Detection
- Presence of `*.csproj` or `*.sln` in repo root
- Suggested build: `dotnet build`
- Suggested test: `dotnet test`
- Warn patterns: `warning CS\d+`, `warning NU\d+`

### Python Detection
- Presence of `setup.py`, `pyproject.toml`, or `requirements.txt`
- Suggested build: `pip install -e .` or `poetry install`
- Suggested test: `pytest` or `python -m unittest`
- Warn patterns: `DeprecationWarning`, `FutureWarning`

### Node.js Detection
- Presence of `package.json`
- Suggested build: `npm install` or `npm run build`
- Suggested test: `npm test`
- Warn patterns: `npm WARN`, `eslint warnings`

### Rust Detection
- Presence of `Cargo.toml`
- Suggested build: `cargo build`
- Suggested test: `cargo test`
- Warn patterns: `warning: .*\n.*\|`
```

---

#### I3: Root Cause Report Format Specification
**Severity:** INFO
**Rule:** `structured-contracts`
**Location:** Line 55 (Data Contracts section)

**Description:**
The plan mentions root-cause agent output includes `root_causes[]`, `recommendations[]`, `blocking=true/false` but doesn't provide full schema.

**Enhancement Suggestion:**
```markdown
### ci-root-cause-agent Output Schema

```json
{
  "success": true,
  "data": {
    "summary": "Build failed due to missing dependency and type mismatch",
    "root_causes": [
      {
        "category": "BUILD.DEPENDENCY_MISSING",
        "description": "Package 'foo' version 2.0.0 not found",
        "affected_files": ["src/main.py"],
        "confidence": "high"
      },
      {
        "category": "BUILD.TYPE_MISMATCH",
        "description": "Expected int, got str in function bar()",
        "affected_files": ["src/utils.py:42"],
        "confidence": "medium"
      }
    ],
    "recommendations": [
      {
        "action": "Add 'foo>=2.0.0' to requirements.txt",
        "rationale": "Missing dependency in manifest",
        "estimated_effort": "1 minute",
        "risk": "low"
      },
      {
        "action": "Update bar() signature to accept Union[int, str]",
        "rationale": "Type annotations don't match actual usage",
        "estimated_effort": "5 minutes",
        "risk": "medium"
      }
    ],
    "blocking": true,
    "requires_human_input": true
  },
  "error": null
}
```
```

---

#### I4: Fix Agent Heuristics Need Formalization
**Severity:** INFO
**Rule:** `safety-auto-fix-boundaries`
**Location:** Lines 72-73 (Open Questions section)

**Description:**
Open question #1 identifies "straightforward" fix heuristics but doesn't formalize them.

**Enhancement Suggestion:**
```markdown
## Fix Agent Heuristics (v0.1.0)

### Automatically Fixable (Low Risk)
- **Import/dependency additions**: Add missing import statements
- **Formatting**: Apply automated formatters (black, prettier, gofmt)
- **Unused variables**: Remove clearly unused declarations
- **Type hints**: Add missing type annotations when obvious from usage
- **Deprecation warnings**: Update to non-deprecated API equivalents (with version checks)

### Requires Human Review (Medium Risk)
- **Logic changes**: Any modification to control flow or business logic
- **API signature changes**: Function parameter additions/removals
- **Data structure changes**: Schema or type modifications
- **Concurrent fixes**: More than 3 unrelated issues in single file

### Never Auto-Fix (High Risk)
- **Security-sensitive code**: Authentication, authorization, crypto
- **Data persistence**: Database migrations, schema changes
- **External API calls**: Changes to third-party integrations
- **Test assertions**: Changing expected values (only add/remove tests)

### Stop Conditions
- If any fix requires understanding broader context (e.g., "why is this variable used here?")
- If fix would propagate changes to >10 files
- If fix risk assessment returns "high" or "medium" without explicit user approval
```

---

## Strengths

### 1. Excellent Agent Scope Definition
The plan defines 6 single-responsibility agents with clear boundaries:
- Pull → Build → Test → Fix → Root Cause → PR
- Each agent has one job; no monolithic workflows

### 2. Strong Safety Posture
- Default conservative path (stop before commit/PR)
- Explicit `--yolo` flag for aggressive automation
- Protected branch awareness
- Never force-push policy
- Warnings block PRs by default

### 3. Good Progressive Disclosure Intent
- SKILL.md designed to be <2KB
- Heavy content moved to references
- Agents isolated from main session context
- Clear separation of discovery vs. execution

### 4. Thoughtful Config Management
- Accepts `.claude/ci-automation.yaml` (specific) and `.claude/config.yaml` (fallback)
- Stack detection with user confirmation
- Avoids unnecessary metadata storage

### 5. Clear Versioning Strategy
- All agents start at 0.1.0
- Plan version tracked (0.1.0)
- Status clearly marked (Preliminary)

---

## Recommendations

### Before Implementation (Critical)
1. **Add registry entries** for all 6 agents (E1)
2. **Fence all JSON examples** in plan document (E2)
3. **Define error contract schema** with code namespaces (E3)
4. **Add ci-validate-agent** for precondition checks (W5)

### Before First Release (Important)
5. **Document Agent Runner usage** in SKILL.md (W1)
6. **Specify SKILL.md content breakdown** to stay under 2KB (W2)
7. **Define --help output format** (W4)
8. **Formalize fix heuristics** (I4)

### Future Enhancements (Optional)
9. Consider idempotency keys for ci-pr-agent (I1)
10. Add stack detection examples to references (I2)
11. Specify root-cause report schema (I3)
12. Design parallel execution option for v0.2.0 (W3)

---

## Approval Status

**Current Status:** Preliminary
**Recommended Next Status:** Proposed (after addressing ERROR and WARNING issues)

**Approval Checklist:**
- [ ] E1: Registry entries added
- [ ] E2: JSON examples fenced
- [ ] E3: Error contracts defined
- [ ] W1: Agent Runner documented
- [ ] W2: SKILL.md breakdown specified
- [ ] W4: --help behavior defined
- [ ] W5: ci-validate-agent added
- [ ] Update plan status to "Proposed"
- [ ] Run `/skill-create` with updated plan

---

## Version Alignment Matrix

| Component | Planned Version | Registry Status | Guidelines Compliance |
|-----------|----------------|-----------------|----------------------|
| ci-automation command | 0.1.0 | ⚠️ Not in registry | Compliant (commands not required) |
| ci-automation skill | 0.1.0 | ⚠️ Not in registry | Needs `depends_on` entries |
| ci-pull-agent | 0.1.0 | ❌ Missing | Must add before implementation |
| ci-build-agent | 0.1.0 | ❌ Missing | Must add before implementation |
| ci-test-agent | 0.1.0 | ❌ Missing | Must add before implementation |
| ci-fix-agent | 0.1.0 | ❌ Missing | Must add before implementation |
| ci-root-cause-agent | 0.1.0 | ❌ Missing | Must add before implementation |
| ci-pr-agent | 0.1.0 | ❌ Missing | Must add before implementation |

---

## File Layout Validation

Proposed layout (Line 57-63):

✅ **Good:**
- `.claude/commands/ci-automation.md` - Correct location
- `.claude/skills/ci-automation/SKILL.md` - Correct location and structure
- `.claude/agents/ci-*.md` - Correct naming pattern
- `.claude/references/` - Appropriate for heavy content
- `.claude/config.yaml.example` - Good practice

⚠️ **Needs Clarification:**
- Reports location: `.claude/reports/skill-reviews/` vs `.claude/.tmp/skill-reviews/`
  - Recommendation: Use `.claude/reports/ci-automation/` for execution reports
  - Use `.claude/reports/skill-reviews/` only for this review-style document

---

## Data Flow Validation

```
User invokes: /ci-automation

Command (.claude/commands/ci-automation.md)
    ↓ expands to
Skill (.claude/skills/ci-automation/SKILL.md)
    ↓ uses Agent Runner to invoke
ci-validate-agent → fenced JSON
    ↓ if success
ci-pull-agent → fenced JSON
    ↓ if success
ci-build-agent → fenced JSON
    ↓ on failure
ci-fix-agent → fenced JSON (patch_summary, risk)
    ↓ apply fixes, rebuild
ci-test-agent → fenced JSON
    ↓ on failure
ci-fix-agent → fenced JSON
    ↓ if still failing
ci-root-cause-agent → fenced JSON (root_causes[], recommendations[])
    ↓ user decides to proceed
ci-pr-agent → fenced JSON (pr_url)
    ↓ skill formats for user
✓ PR created: https://github.com/org/repo/pull/123
```

**Assessment:** Flow is logical and follows v0.4 patterns. Add validation step at start.

---

## Configuration Schema Validation

Proposed config keys (Line 62):
- `upstream_branch`
- `build_command`
- `test_command`
- `warn_patterns`
- `repo_root` (optional)

**Recommendations:**
1. Add `validate_command` (optional pre-flight check, e.g., `lint`)
2. Add `allow_warnings: false` (default)
3. Add `auto_fix_enabled: false` (default, override with --yolo)
4. Add `pr_template_path` (optional, e.g., `.github/PULL_REQUEST_TEMPLATE.md`)

**Example `.claude/ci-automation.yaml`:**
```yaml
ci_automation:
  upstream_branch: develop
  build_command: dotnet build
  test_command: dotnet test
  validate_command: dotnet format --verify-no-changes
  warn_patterns:
    - "warning CS\\d+"
    - "warning NU\\d+"
  allow_warnings: false
  auto_fix_enabled: false
  pr_template_path: .github/PULL_REQUEST_TEMPLATE.md
```

---

## Security & Safety Assessment

### ✅ Compliant Areas
- Never force-push (Line 66)
- Respect protected branches (Line 66)
- Default conservative path (Lines 67-68)
- Explicit `--yolo` flag requirement (Line 68)
- Fix agent limited to straightforward patterns (Line 69)

### ⚠️ Needs Enhancement
1. **Secret handling**: Plan doesn't mention how ci-pr-agent handles GitHub tokens
   - Recommendation: Document environment variable requirements (e.g., `GITHUB_TOKEN`)
   - Document that tokens must never appear in JSON outputs or logs

2. **Destructive operation approval**: Plan doesn't specify if `--yolo` requires confirmation
   - Recommendation: Even with `--yolo`, require confirmation before:
     - Creating PRs to main/master (unless `--dest main` explicitly provided)
     - Pushing to shared branches
     - Deleting worktrees with uncommitted changes

3. **Audit logging**: Plan doesn't mention audit trail
   - Recommendation: Agent Runner should log all invocations to `.claude/state/logs/ci-automation/`

---

## Testing Strategy (Not in Plan)

**Recommendation:** Add testing guidance before implementation:

```markdown
## Testing Strategy (v0.1.0)

### Unit Testing (Per Agent)
- Mock git/build/test commands
- Test error handling paths
- Validate JSON schema compliance

### Integration Testing (Skill Level)
- Test full flow with sample repository
- Test flag combinations (--build, --test, --yolo)
- Test detection of .NET/Python/Node projects

### Safety Testing
- Verify protected branch detection
- Verify warnings block PRs by default
- Verify `--yolo` behavior with clean/dirty repos

### Validation Testing
- Verify registry.yaml alignment
- Verify version frontmatter in all agents
- Run scripts/validate-agents.sh
```

---

## Conclusion

This is a **high-quality preliminary plan** that demonstrates solid understanding of v0.4 guidelines. The architecture is sound, safety considerations are thoughtful, and agent scope is well-defined.

**Critical Path to Implementation:**
1. Address 3 ERROR issues (registry, fencing, error contracts)
2. Address 5 WARNING issues (Agent Runner, size guidance, help text, validation agent)
3. Update plan status to "Proposed"
4. Obtain stakeholder approval
5. Run `/skill-create plans/ci-automation-skill-plan.md`

**Estimated Effort to Resolve Issues:**
- ERROR fixes: 1-2 hours
- WARNING fixes: 2-3 hours
- INFO enhancements: 3-4 hours (optional for v0.1.0)

**Timeline:**
- Address ERRORs + WARNINGs: 1 day
- Update plan and get approval: 1 day
- Implementation via `/skill-create`: 2-3 days
- Testing and refinement: 2-3 days
- **Total to v0.1.0 release: 6-8 days**

---

## Next Steps

1. Review this report with plan owner (TBD per Line 5)
2. Create tracking issues for ERROR and WARNING fixes
3. Update plan with fixes
4. Re-run validation: `/skill-review plans/ci-automation-skill-plan.md --report-only`
5. On clean validation, set status to "Proposed"
6. Obtain approval and proceed to `/skill-create`

---

**Report Generated:** 2025-01-22
**Validation Command:** `/skill-review plans/ci-automation-skill-plan.md`
**Guidelines Reference:** `docs/claude-code-skills-agents-guidelines-0.4.md`
**Registry Reference:** `.claude/agents/registry.yaml`
