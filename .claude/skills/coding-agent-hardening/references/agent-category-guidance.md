# Agent Category Guidance

Use this file after reading `hardening-policy.md`.

## Coding agents

### What to eliminate
- asking whether to fix simple findings
- stopping for false decisions
- proposing technical debt for small or medium fixes
- ignoring adjacent defects in files already open

### What to add
- explicit fix-first language
- requirement to analyze reasonable alternatives before escalating
- instruction to correct obvious mistakes directly
- instruction to keep working unless the remaining issue is a real architectural or product decision
- requirement to run relevant validation after code changes before stopping
- requirement to fix regression or root-cause it before stopping

### Good hardened behavior
- fixes a wrong version in a test instead of asking whether to leave it
- cleans up a small validation gap while already editing the same module
- refuses to frame ordinary cleanup as technical debt
- runs the relevant tests before reporting completion
- if a test regresses, keeps working until the defect is fixed or the root cause is identified

## QA and review agents

### What to eliminate
- blocker-only or high-importance-only framing
- confidence filters that suppress too many real issues
- "pre-existing" dismissal
- language that treats minor findings as optional noise

### What to add
- aggressively pursue quality violations rather than merely triaging them
- report all real findings with remediation guidance
- treat non-blocking findings as work to close when feasible
- make severity affect ordering, not whether the issue matters at all
- note architectural trade-offs separately when a small-looking issue hides a larger concern
- wording close to:
  - Aggressively pursue quality violations and do not normalize them away.
  - Do NOT dismiss violations as "pre-existing" or "not worsened."
  - Every violation found is a finding regardless of whether it predates this sprint.
  - List each finding with file:line and a remediation note.
  - The pre-existing/new distinction is informational only. It does not change severity or blocking status.

### Good hardened behavior
- reports a small but real config defect instead of omitting it as low priority
- flags pre-existing issues encountered in the touched area rather than dismissing them
- frames the default response to findings as remediation, not triage

## Orchestration and planning agents

### What to eliminate
- "summarize and wait" by default
- routine conversion of findings into backlog or follow-up tasks
- asking the user whether to accept technical debt for ordinary fixes
- treating QA output as advisory unless blocking

### What to add
- default routing toward immediate closure
- requirement to distinguish real blockers from false blockers
- instruction to keep the system moving unless there is a genuine scope or approval boundary
- expectation that quality findings are fixed unless a real boundary prevents it
- requirement to demand executed validation after code changes
- requirement to reject "changed code, did not run tests" style outcomes
- requirement to push remediation forward until regression is fixed or root-caused
- wording close to:
  - Do NOT dismiss quality findings as "pre-existing" or "not worsened."
  - Treat findings as work that should move toward closure, not as metadata to classify and drop.
  - The expectation is that quality findings are fixed unless a real scope, architecture, or approval boundary prevents it.
  - Run the full relevant validation suite and verify no regression before stopping.
  - Do not report "I changed the code but did not run tests."
  - If validation fails, continue by fixing the issue or root-causing it before stopping.

### Good hardened behavior
- sends straightforward QA findings back for immediate fix instead of carrying them as debt
- continues remediation after blockers are fixed rather than stopping once the gate passes
- escalates only when the next step changes architecture, product behavior, or schedule materially
- rejects completion reports that do not include executed validation
- treats unresolved regression as ongoing work unless a true external blocker exists
