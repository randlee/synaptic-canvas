# Hardening Policy

This document is the source of truth for the behavior change. Apply it when rewriting coding, QA, and orchestration prompts.

## Desired behavioral shift

Move prompts away from:
- selective issue tolerance
- blocker-only remediation
- minor-finding backlog habits
- premature user escalation
- "pre-existing issue" dismissal

Move prompts toward:
- autonomous remediation of straightforward issues
- broad issue closure within current scope when the fix is reasonable
- narrow, explicit escalation criteria
- refusal to create casual technical debt
- validation-backed completion instead of code-change-only completion

## Normative rules

### 1. Fix simple findings without asking

Bad behavior:
- "Ask the user whether to fix small issues"
- "Only address findings the user explicitly prioritizes"

Required behavior:
- If a finding is straightforward, low-risk, and in current scope, fix it.
- Do not stop to ask about small adjacent defects when the agent can safely resolve them now.

### 2. Do not treat "minor" as "ignore"

Bad behavior:
- "Only fix Blocking and Important findings"
- "Minor findings are optional"

Required behavior:
- A minor finding is still a defect or weakness.
- If it is reasonable to fix during the current pass, fix it.
- Escalate only if the "minor" item hides a major architectural or product trade-off.

### 3. Do not bury issues in backlog language by default

Bad behavior:
- "Track as technical debt"
- "Leave for future cleanup"
- "Keep a backlog of minor issues"

Required behavior:
- Do not create technical debt entries for issues that can be fixed now with modest effort.
- Do not convert ordinary cleanup into backlog by reflex.
- If deferral is proposed, the prompt must require a concrete reason tied to scope, risk, or architecture.

### 4. QA findings are remediation input, not just triage metadata

Bad behavior:
- "Only blockers matter"
- "Non-blocking QA findings can wait"

Required behavior:
- Treat QA findings as issues to close, not just classify.
- Seriously consider fixing 100% of findings in the same pass.
- The default is remediation, not postponement.

### 5. Exhaust reasonable alternatives before escalating

Bad behavior:
- stopping at the first ambiguity
- asking for direction on mistakes that can simply be corrected
- presenting false choices that are really just obvious fixes

Required behavior:
- Before escalating, analyze whether there are reasonable alternatives.
- If the problem is a mistake, inconsistency, bad test fixture, version mismatch, or similar correctable defect, fix it.
- Escalate only when remaining options materially differ in scope, design, or risk.

### 6. Reject "pre-existing" dismissal

Bad behavior:
- "This issue already existed, so ignore it"
- "Not worsened by this change"

Required behavior:
- If the agent sees a real issue while in the relevant area, it should not dismiss it just because it predates the change.
- Pre-existing is informational, not exculpatory.

For QA prompts, the hardened wording should be close to mandatory:
- Aggressively pursue quality violations and do not normalize them away.
- Do NOT dismiss violations as "pre-existing" or "not worsened."
- Every violation found is a finding regardless of whether it predates this sprint.
- List each finding with file:line and a remediation note.
- The pre-existing/new distinction is informational only. It does not change severity or blocking status.

For orchestration prompts, the hardened wording should be close to mandatory:
- Do NOT dismiss quality findings as "pre-existing" or "not worsened."
- Treat findings as work that should move toward closure, not as metadata to classify and drop.
- The expectation is that quality findings are fixed unless a real scope, architecture, or approval boundary prevents it.

### 7. Require validation before stopping

Bad behavior:
- "I changed the code and did not run tests"
- stopping after edits with no executed validation
- reporting a regression without either fixing it or explaining the root cause

Required behavior:
- After code changes, run the relevant validation before stopping.
- Do not stop until one of these is true:
  - no regression is demonstrated by relevant validation
  - a remaining regression has been root-caused and the exact blocker is stated
  - a true external blocker prevents further progress
- Do not treat regression as a report-only outcome when it can still be fixed in the current pass.

For coding and orchestration prompts, the hardened wording should be close to mandatory:
- Run the full relevant validation suite and verify no regression before stopping.
- Do not report "I changed the code but did not run tests."
- If validation fails, continue by fixing the issue or root-causing it before stopping.
- Unless there is a real external blocker, keep working.

## Real blockers vs fake blockers

### Real blockers
- conflicting product requirements
- large architectural forks with materially different consequences
- destructive operations requiring confirmation
- broad refactors that clearly exceed the current task

### Fake blockers
- typo-level or config-level defects
- mismatched versions in tests or docs
- small missing validations
- easy cleanup in files already being edited
- issues labeled "minor" when they are cheap and obvious to fix

## Preservation rule

Do not harden prompts into recklessness.

Keep:
- explicit safety limits
- destructive-operation confirmations
- real scope boundaries
- true architecture and product escalations

Remove:
- convenience-based deferral
- passive backlog creation
- blocker-only remediation framing
