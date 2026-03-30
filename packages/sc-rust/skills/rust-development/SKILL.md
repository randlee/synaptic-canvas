---
name: rust-development
version: 1.0.0
description: Develop, review, and explore Rust code with strict adherence to Pragmatic Rust Guidelines. Use when the user mentions Rust, .rs files, Cargo, clippy, rustdoc, or requests Rust architecture, implementation, or review.
---

# Rust Development

This skill coordinates Rust development workflows and enforces Rust coding standards and best practices when creating or modifying Rust code.

## Capabilities

- Rust architecture planning
- Rust code exploration and feature tracing
- Rust code review with high-confidence findings
- Rust implementation and refactoring

## Instructions

When asked about generating new code or making code changes to existing code, make
sure that edits are conformant to the Rust guidelines at `.claude/skills/rust-development/guidelines.txt` if the language to generate is Rust.

Key areas to enforce:
- Idiomatic Rust patterns and conventions
- Proper error handling (Result types, custom errors)
- Memory safety and lifetime management
- Async/await patterns when applicable
- FFI best practices for interop scenarios
- Documentation standards (rustdoc conventions)
- Testing patterns and practices

Only add a compliance comment when the user explicitly asks for a compliance annotation or a compliance-focused review. If requested, add:
```rust
// Rust guideline compliant {date}
```
where {date} is the guideline date/version.

## Agent Delegation

Use these agents for Rust workflows. Always set `run_in_background` to `true` in the invocation payloads.

- `rust-architect`: Architecture and implementation blueprints
- `rust-code-reviewer`: High-confidence Rust code reviews
- `rust-code-explorer`: Feature tracing and architecture mapping
- `rust-developer`: Rust implementation and refactoring

Invocation template (always keep `run_in_background: true`):
```json
{
  "description": "Short description of what the agent will do",
  "prompt": "Detailed task description",
  "subagent_type": "rust-architect | rust-code-reviewer | rust-code-explorer | rust-developer",
  "run_in_background": true
}
```

## When to Activate

This skill activates automatically when:
- Creating new Rust source files (.rs)
- Modifying existing Rust code
- Reviewing Rust code for compliance
- Answering questions about Rust best practices
- Working with Cargo projects

## Guidelines Source

The detailed guidelines are maintained in `.claude/skills/rust-development/guidelines.txt`.
