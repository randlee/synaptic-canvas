# Use Cases

## Design a new Rust feature

Use `rust-architect` to produce an implementation blueprint before writing code.

```
Design a connection pool with configurable retry policy and backpressure support.
```

The agent analyzes existing codebase patterns and returns a structured plan: files to create/modify, component designs, data flows, and build sequence.

## Review Rust code for issues

Use `rust-code-reviewer` for a high-confidence review focused on bugs, security, and convention adherence.

```
Review the changes in src/daemon/session_registry.rs for correctness and safety.
```

The agent uses confidence-based filtering — only reports findings it is confident about, reducing noise.

## Trace how a feature works

Use `rust-code-explorer` to map execution paths and architecture before implementing changes.

```
Trace how a SendMessage call flows from the CLI through to the daemon socket.
```

## Implement a Rust feature

Use `rust-developer` for implementation that follows the Pragmatic Rust Guidelines.

```
Implement the retry policy described in the architecture plan.
```

## Run a full QA pass

Use `rust-qa-agent` to enforce first-principles QA, run quality gates, and report execution-backed findings.

```
Run a full QA pass on the changes from the last sprint.
```

The agent:
1. Reads `guidelines.txt` and `cross-platform-guidelines.md`
2. Runs fmt/clippy/tests and optional coverage
3. Checks for portability and guideline violations surfaced directly by changed code
4. Reports execution facts without taking over structural-pattern or service-hardening review policy
5. Returns a structured fenced JSON report with PASS/FAIL gate and all findings

## Run a dedicated Rust best-practices review

Use `rust-best-practices-agent` when the goal is structural pattern review rather than general QA execution.

```
Run a sprint-scope best-practices review on the changed Rust files using RBP-001, RBP-004, RBP-006, and RBP-007.
```

The agent:
1. Reads the canonical best-practices inventory and enforcement strategy
2. Loads the specific per-pattern references needed for the selected practice ids
3. Reviews only the assigned Rust patterns
4. Returns a fenced JSON findings report keyed by stable practice id

## Enforce design patterns during planning

Use `rust-best-practices` during design review to catch structural issues before implementation.

```
Review this design plan for state machine encoding and error propagation patterns.
```

The skill checks for typestate opportunities, error inventory completeness, sealed trait candidates, and newtype wrapping needs.

## Review a Rust service for production gaps

Use `rust-service-hardening` or `rust-service-hardening-agent` when the code in question is a service rather than a general-purpose crate.

```
Review this Axum service for production hardening gaps before we ship it.
```

Start with the skill's Tier 1 checks:
1. Startup config validation
2. Client and server timeouts
3. Graceful shutdown and draining

Then continue through tracing, request IDs, retries, backpressure, `spawn_blocking`, body limits, dependency hygiene, health checks, and CI/release gates.

## Run a dedicated Rust service-hardening review

Use `rust-service-hardening-agent` when you want a runtime-hardening review separate from generic Rust QA.

```
Run a phase-end service-hardening review on this Tokio/Axum service.
```

The agent:
1. Performs a quick service-indicator check before reviewing
2. Returns `skipped` immediately when the target is not actually service-like
3. Uses the service-hardening checklist and framework notes for findings
4. Returns fenced JSON only

## Harden a Tokio service before rollout

Use `rust-service-hardening` when the user asks for production readiness, deploy-readiness, or service-operability guidance rather than general Rust style advice.

```
Make this Tokio worker production-ready. I want request IDs, bounded queues, timeout rules, and a shutdown plan.
```

The skill is intentionally not for:
- non-service Rust crates
- embedded Rust
- pure sync CLI tools
- low-level libraries with no runtime/network/server concerns

## Catch cross-platform issues

`rust-qa-agent` automatically checks for:
- Hardcoded `/tmp/` paths (blocking)
- `.env("HOME", ...)` in tests (blocking)
- String path concatenation instead of `PathBuf::join()` (blocking)
