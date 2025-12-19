# Handoff Prompt: Kanban Skill Design and Implementation

## Context for ARCH-SC

You are **ARCH-SC**, the architecture and skill creation specialist for the Synaptic Canvas project. Your role is to review project status, design system architecture, and guide implementation of new skills following proven guidelines.

---

## Session Objective

Design and plan the implementation of the **sc-kanban** package - a configurable state machine for task card management that follows the Synaptic Canvas v0.4 architecture guidelines.

---

## Required Reading

Before beginning the discussion, please read these documents in order:

### 1. Project Status and Backlog
**File:** `/Users/randlee/Documents/github/synaptic-canvas/pm/plans/2025-12-04-ongoing-maintenance-backlog.md`

**Focus on:**
- Executive Summary (current project status)
- Section 4.3: SC-CI-Automation Package (✅ COMPLETED - reference example)
- Section 4.4: Kanban Task Management Skill (⏳ NEXT - your task)

**Key Context:**
- Marketplace is at v0.6.0 with 6 packages (sc-delay-tasks, sc-ci-automation, sc-git-worktree, sc-manage, sc-repomix-nuget, sc-github-issue)
- Latest addition: sc-ci-automation (v0.1.0) - released 2025-12-09, commit 8568280
- Kanban skill is the next planned package for development

### 2. Kanban Design Specification
**File:** `/Users/randlee/Documents/github/synaptic-canvas/docs/kanban-design.md`

**Focus on:**
- Overview and design principles (pure state machine, configuration-driven)
- File structure (`.kanban/` directory layout)
- Configuration schema (`config.json`)
- Card formats (directory vs aggregate columns)
- Agent interface (kanban-update, kanban-query)
- State transition validation (preconditions, postconditions, WIP limits)

**Key Design Decisions to Review:**
- Column types: aggregate (single file) vs directory (file per card)
- Transition validation: preconditions vs postconditions
- Field scrubbing: transient vs permanent fields
- Rule categories: field_required, tasks_complete, external_state
- Alternative board configurations (4-state, 5-state, 6-state)

### 3. Architecture Guidelines
**File:** `/Users/randlee/Documents/github/synaptic-canvas/docs/claude-code-skills-agents-guidelines-0.4.md`

**Focus on:**
- Two-tier skill/agent architecture (Skills = discovery layer, Agents = execution layer)
- Agent design principles (single responsibility, minimal instructions, fenced JSON output)
- Structured response contracts (success/error envelope, version management)
- Context efficiency patterns (agent as disposable context, planning/execution split)
- File organization and naming conventions

**Apply These Patterns:**
- SKILL.md with YAML frontmatter (name, version, description, entry_point)
- Agents return fenced JSON with minimal envelope: `{success, data, error}`
- Registry-based version management (external validation)
- Clear separation: skill orchestrates, agents execute
- Local-only installation scope (state management per-repo)

---

## Your Tasks

### Phase 1: Status Assessment and Context Review (5-10 minutes)

1. **Read the three documents above** in the order listed
2. **Summarize current project status:**
   - What packages exist in the marketplace?
   - What was most recently completed (sc-ci-automation)?
   - What patterns can we learn from sc-ci-automation for kanban?
3. **Confirm understanding of kanban design:**
   - What problem does sc-kanban solve?
   - What is in scope vs out of scope?
   - What are the core design principles?

### Phase 2: Architecture Review and Design Discussion (15-20 minutes)

Review the kanban design and discuss:

1. **Agent Decomposition:**
   - Is the 2-agent split (kanban-update, kanban-query) optimal?
   - Should we split kanban-update further? (e.g., separate create/move/archive agents?)
   - Trade-offs: simplicity vs granularity

2. **Configuration Schema:**
   - Review the `config.json` structure
   - Is it flexible enough for different board types?
   - Are the transition rules clear and enforceable?
   - Should we support custom rule types beyond the 6 defined?

3. **State Transition Validation:**
   - Review preconditions vs postconditions
   - Are external state checks (worktree_exists, pr_merged) feasible?
   - How should we handle postcondition failures? (warnings vs errors)
   - WIP limit enforcement: blocking vs advisory?

4. **File Storage Strategy:**
   - Review aggregate (single file) vs directory (file per card) column types
   - What are the performance implications?
   - Should we support hybrid approaches?
   - How do we handle concurrent writes?

5. **JSON Interface:**
   - Review the agent input/output formats
   - Are the error codes clear and actionable?
   - Should we add more metadata to responses?
   - How do we handle partial failures (e.g., some postconditions fail)?

6. **Integration Points:**
   - How should kanban integrate with sc-git-worktree?
   - How should kanban integrate with sc-github-issue?
   - Should these be hard dependencies or optional?
   - How do we validate external state without tight coupling?

7. **v0.4 Compliance:**
   - Does the design follow the two-tier architecture?
   - Are agents focused and single-responsibility?
   - Will agents return proper fenced JSON envelopes?
   - Is the skill thin and orchestration-focused?

### Phase 3: Implementation Planning (10-15 minutes)

1. **Package Structure:**
   - Confirm directory layout for `packages/sc-kanban/`
   - What goes in agents/ vs commands/ vs skills/?
   - What documentation files are needed?

2. **Development Order:**
   - What should be built first? (config schema? kanban-update? kanban-query?)
   - What are the critical path items?
   - What can be iterated on later?

3. **Testing Strategy:**
   - What test scenarios are critical?
   - How do we test state transition validation?
   - How do we test external state checks?
   - What edge cases should we cover?

4. **Success Criteria:**
   - What defines "done" for v0.1.0 of sc-kanban?
   - What features are MVP vs nice-to-have?
   - How do we validate it's ready for marketplace release?

---

## Discussion Format

After reading the documents, initiate a structured discussion:

1. **Start with status summary:**
   - "I've reviewed the backlog. Here's where we are..."
   - "sc-ci-automation provides a good reference for..."

2. **Present architecture analysis:**
   - "The kanban design proposes X. Here are my thoughts..."
   - "I see three key architectural decisions to discuss..."

3. **Ask clarifying questions:**
   - "The design shows Y. Have you considered Z?"
   - "For transition validation, should we...?"

4. **Recommend approach:**
   - "Based on v0.4 guidelines and sc-ci-automation example..."
   - "I recommend we start with..."

5. **Create implementation plan:**
   - "Here's the proposed development order..."
   - "Critical path: A → B → C"
   - "Success criteria for v0.1.0: ..."

---

## Output Expectations

By the end of this session, we should have:

1. ✅ Confirmed understanding of project context and kanban design
2. ✅ Resolved key architectural decisions
3. ✅ Validated v0.4 compliance
4. ✅ Created implementation plan with clear next steps
5. ✅ Identified any design changes needed before implementation

---

## Reference Examples

**SC-CI-Automation (Recently Completed):**
- Location: `packages/sc-ci-automation/`
- Agents: 7 (validate, pull, build, test, fix, root-cause, pr)
- Command: `/sc-ci-automation` with flags
- Documentation: README, CHANGELOG, USE-CASES, TROUBLESHOOTING
- Followed v0.4 guidelines successfully

**SC-Git-Worktree (Mature Package):**
- Location: `packages/sc-git-worktree/`
- Agents: 5 (create, scan, cleanup, abort, update)
- Command: `/sc-git-worktree`
- Shows good state management patterns

Use these as reference for structure and patterns.

---

## Ready to Begin?

Please confirm:
1. ✅ You have read all three documents
2. ✅ You understand your role as ARCH-SC
3. ✅ You're ready to discuss kanban skill design

Then begin with your status assessment and architecture analysis.

---

**Session Date:** 2025-12-09
**Prepared by:** Claude (previous session)
**Working Directory:** `/Users/randlee/Documents/github/synaptic-canvas`
