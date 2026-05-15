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

### Sprint / Fix QA

For Rust implementation work:
- always launch `rust-qa-agent`
- launch `rust-best-practices-agent` in `sprint_review` mode when changed Rust code is in scope
- launch `rust-service-hardening-agent` in `sprint_review` mode when the changed scope is service-like or when service indicators are already known

Default sprint best-practices scope should follow the cadence matrix in `rust-best-practices/patterns/enforcement-strategy.md`. The usual sprint set is:
- `RBP-001`
- `RBP-004`
- `RBP-006`
- `RBP-007`

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
  "review_targets": ["src/", "Cargo.toml"]
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
