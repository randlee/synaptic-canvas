# Rust Quality Manager Supplement

This file augments `quality-mgr.md` for Rust repositories. It does not replace the core quality-manager prompt.

Use this supplement to decide when to launch Rust-specific reviewers and how to render their fenced-JSON assignments.

## Rust Reviewers

- `rust-qa-agent` — tests, clippy, coverage, portability, artifact checks, and first-principles QA
- `rust-best-practices-agent` — structural Rust pattern review keyed by stable practice ids
- `rust-service-hardening-agent` — runtime/service-hardening review with a required service-indicator fast-exit check

Generic, repo-defined reviewers remain language-independent and continue to run under `quality-mgr.md`; this supplement only adds Rust-specific reviewers.

## Assignment Types

### Plan Gate

`quality-mgr.md` already covers the generic launch set for plan review.

For Rust work, add:
- `rust-best-practices-agent` in `doc_review` mode when requirements or architecture documents imply best-practices concerns from `rust-best-practices/patterns/enforcement-strategy.md`
- `rust-service-hardening-agent` in `doc_review` mode when service/runtime architecture is in scope

Do not launch `rust-qa-agent` for docs-only plan review.

### Sprint QA

For sprint reviews of Rust implementation work:
- always launch `rust-qa-agent`
- launch `rust-best-practices-agent` in `sprint_review` mode when changed Rust code is in scope
- launch `rust-service-hardening-agent` in `sprint_review` mode when the changed scope is service-like or when service indicators are already known

Default sprint best-practices scope should follow the cadence matrix in `rust-best-practices/patterns/enforcement-strategy.md`. The usual sprint set is:
- `RBP-001`
- `RBP-004`
- `RBP-006`
- `RBP-007`

### Fix QA

A fix is not a sprint review. Only the agent necessary to confirm its original
finding is dispatched, normally the filing reviewer. Do not automatically
launch rust-qa-agent, best-practices, hardening, or another reviewer merely
because Rust code or tests changed. The verifier runs the focused checks needed
to confirm the original acceptance criterion and reports fixed/open/regressed
for that finding only. It files no new findings. Required CI is separate.

#### Fix-Round Dispatch Gate for Subjective Reviewers

The subjective reviewers are designed to dig aggressively and may surface new
issues even when the assigned fix is correct. Letting every fix round re-run
them open-ended prevents QA from converging. The control point is scoped
dispatch, not omission of findings that still require verification:

- During a **fix round** (re-checking a previously fixed/assigned finding), only dispatch `rust-best-practices-agent` or `rust-service-hardening-agent` when there is a specific, already-triaged finding of that reviewer's own category (`RBP-*` or `RSH-*`) explicitly assigned to verify this round. If no such finding is in scope for the task, do not dispatch that reviewer at all this round.
- When dispatching under that condition, pass `carry_forward_findings_json` populated with the assigned finding ids so the rendered assignment sets `findings_scope_locked: true` — this instructs the reviewer to report a disposition for those ids only and to keep any unsolicited new observation out of its canonical `findings` output.
- This gate does not apply to an initial/open `sprint_review` or `phase_end` review with no prior findings in scope — dispatch normally there, with `carry_forward_findings_json` omitted (defaults to `"[]"`, `findings_scope_locked: false`).
- Do not fold an unsolicited new finding any reviewer surfaces during a scope-locked verification round into this round's findings. Surface it informationally to the lead for a future dedicated triage pass instead.
- Apply the same gate to any repo-defined subjective reviewer that supports `carry_forward_findings`.
- Every `rust-best-practices-agent` and `rust-service-hardening-agent` assignment takes `qa_round`: 1 only for an open round-1 review, 2 or higher on every fix verification, including the first QA of a `fix/` layer; above round 1 the template refuses to render without that reviewer's own carried ids. The refusal shows as `ERR_RENDER_JSON_MALFORMED` (the template puts `FIX_ROUND_SCOPE_LOCK_REQUIRED` ahead of the JSON); an empty, `null` or whitespace-only `carry_forward_findings_json` counts as no carried ids.

### Phase-Ending Review

For Rust phase-end review:
- always launch `rust-qa-agent`
- launch `rust-best-practices-agent` in `phase_end` mode
- launch `rust-service-hardening-agent` in `phase_end` mode when the repo or crate is service-like

## Rendering Assignments

Render Rust reviewer assignments with `sc-compose` from these installed templates:

- `.claude/assets/sc-rust/quality-mgr/templates/rust-qa-assignment.json.j2`
- `.claude/assets/sc-rust/quality-mgr/templates/rust-best-practices-assignment.json.j2`
- `.claude/assets/sc-rust/quality-mgr/templates/rust-service-hardening-assignment.json.j2`

The rendered output is JSON and should be passed directly to the worker prompt. Keep the worker prompts sparse; do not push orchestration logic down into the workers.

### QA Assignment Example

```bash
_VARS=$(mktemp)
cat > "$_VARS" <<'JSON'
{
  "review_mode": "sprint_review",
  "worktree_path": "/absolute/path/to/worktree",
  "review_targets": ["src/", "Cargo.toml"]
}
JSON
sc-compose render \
  --root .claude/assets/sc-rust/quality-mgr/templates \
  --file rust-qa-assignment.json.j2 \
  --var-file "$_VARS"
rm -f "$_VARS"
```

### Best-Practices Assignment Example

```bash
_VARS=$(mktemp)
cat > "$_VARS" <<'JSON'
{
  "review_mode": "sprint_review",
  "worktree_path": "/absolute/path/to/worktree",
  "review_targets": ["src/", "Cargo.toml"],
  "qa_round": 1,
  "practice_mode": "selected",
  "practice_ids": ["RBP-001", "RBP-004", "RBP-006", "RBP-007"]
}
JSON
sc-compose render \
  --root .claude/assets/sc-rust/quality-mgr/templates \
  --file rust-best-practices-assignment.json.j2 \
  --var-file "$_VARS"
rm -f "$_VARS"
```

### Service-Hardening Assignment Example

```bash
_VARS=$(mktemp)
cat > "$_VARS" <<'JSON'
{
  "review_mode": "phase_end",
  "worktree_path": "/absolute/path/to/worktree",
  "review_targets": ["src/", "Cargo.toml"],
  "qa_round": 1
}
JSON
sc-compose render \
  --root .claude/assets/sc-rust/quality-mgr/templates \
  --file rust-service-hardening-assignment.json.j2 \
  --var-file "$_VARS"
rm -f "$_VARS"
```

## Render Verification Rule

When editing either Rust assignment template, verify rendering with `sc-compose` before stopping.

At minimum, render:
- `doc_review`
- `sprint_review`
- `phase_end`

Do not rely on visual inspection of the template source alone.

Use native array values for list-shaped fields such as `review_targets`, `practice_ids`, and `topics`.
