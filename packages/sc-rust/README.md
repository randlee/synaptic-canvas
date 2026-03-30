# sc-rust

Rust development toolkit for Claude Code. Provides idiomatic guidelines, design pattern enforcement, and specialized agents for architecture, code review, exploration, implementation, and QA.

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

## Agents

| Agent | Model | Role |
|-------|-------|------|
| `rust-architect` | Opus | Architecture blueprints and implementation plans |
| `rust-code-reviewer` | Sonnet | High-confidence code review with confidence-based filtering |
| `rust-code-explorer` | Sonnet | Feature tracing and architecture mapping |
| `rust-developer` | Sonnet | Implementation and refactoring per Pragmatic Rust Guidelines |
| `rust-qa-agent` | Sonnet | Testing, coverage, clippy, and guideline compliance |

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
| `patterns/error-context-recovery-plan.md` | Error handling implementation plan |
| `patterns/typestate-plan.md` | Typestate pattern implementation guide |
| `patterns/sealed-traits-plan.md` | Sealed trait pattern implementation guide |
