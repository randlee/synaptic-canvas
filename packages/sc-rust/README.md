# sc-rust

Rust development toolkit for Claude Code. Provides idiomatic guidelines, service-hardening guidance, design pattern enforcement, and specialized agents for architecture, code review, exploration, implementation, and QA.

## Skills

### rust-development
Activates automatically when working with Rust files, Cargo projects, or clippy. Enforces the Pragmatic Rust Guidelines (`guidelines.txt`) and cross-platform portability rules. Delegates to specialized agents for implementation, review, and exploration.

### rust-best-practices
Enforces high-value Rust design patterns at the right lifecycle stage — design review, code review, and CI. Covers:
- **Error Context + Recovery** — structured errors with cause chains and recovery steps
- **Typestate Pattern** — encode state machines in types; compiler prevents invalid transitions
- **Sealed Trait Pattern** — prevent external trait implementation; freedom to evolve APIs
- **Newtype/Zero-Cost Abstraction** — wrap primitives in domain types
- **Cow, Interior Mutability, Infallible, Trait Object Safety**

Complements `rust-development` (style/guidelines) by focusing on architecture and design patterns.

### rust-service-hardening
Guides production-readiness reviews for Rust services. Best fit for Tokio, Axum, Hyper, Tonic, and Reqwest-based backends where runtime behavior matters as much as code style.

Covers:
- **Blocking-critical defaults** — startup config validation, timeouts, graceful shutdown
- **Runtime resilience** — request tracing, request IDs, retries, backpressure, `spawn_blocking`
- **Operational safety** — input limits, dependency hygiene, health checks, metrics, CI/release gates

Not intended for:
- non-service Rust crates
- embedded Rust
- pure sync CLI tools
- low-level libraries with no runtime, network, or server concerns

## Agents

| Agent | Model | Role |
|-------|-------|------|
| `rust-architect` | Opus | Architecture blueprints and implementation plans |
| `rust-best-practices-agent` | Sonnet | Dedicated structural pattern review using stable practice ids |
| `rust-code-reviewer` | Sonnet | High-confidence code review with confidence-based filtering |
| `rust-code-explorer` | Sonnet | Feature tracing and architecture mapping |
| `rust-developer` | Sonnet | Implementation and refactoring per Pragmatic Rust Guidelines |
| `rust-qa-agent` | Sonnet | Testing, coverage, clippy, portability, and first-principles QA |
| `rust-service-hardening-agent` | Sonnet | Dedicated service-runtime hardening review with service applicability checks |

## Requirements

- `cargo` >= 1.87
- `cargo-llvm-cov` (for coverage in rust-qa-agent)

## Storage

This package installs into `.claude/` only. No project-level state is written.

## Reference Files

Installed alongside the skills:

| File | Purpose |
|------|---------|
| `guidelines.txt` | Pragmatic Rust Guidelines — style, idioms, error handling, async, FFI |
| `cross-platform-guidelines.md` | Portability rules for Ubuntu, macOS, and Windows |
| `patterns/enforcement-strategy.md` | Master pattern inventory — when and where to enforce each pattern |
| `patterns/practice-inventory.md` | Stable practice ids and canonical best-practices inventory |
| `patterns/error-context-recovery-plan.md` | Error handling implementation plan |
| `patterns/typestate-plan.md` | Typestate pattern implementation guide |
| `patterns/sealed-traits-plan.md` | Sealed trait pattern implementation guide |
| `references/production-checklist.md` | Prioritized service-hardening checklist for production reviews |
| `references/framework-notes.md` | Tokio/Axum/Hyper/Tonic/Reqwest notes for service hardening |
| `assets/sc-rust/quality-mgr/quality-mgr.rust.md` | Rust-specific quality-mgr supplement listing Rust reviewers and launch rules |
