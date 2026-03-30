---
status: Active
created: 2026-03-29
version: 0.1.0
owner: randlee
---

# Rust Service Hardening Skill – Plan (Active)

## Intent
Add a new skill to the existing `sc-rust` plugin focused on production-hardening Rust services before or alongside business-logic work. The skill should help with readiness, resilience, observability, and safe operational defaults for networked/backend Rust services.

## Proposed Skill
- Package: `packages/sc-rust`
- Path: `packages/sc-rust/skills/rust-service-hardening/SKILL.md`
- Version: 0.1.0
- Name: `rust-service-hardening`
- Plan status rationale: `sc-rust` is already on this branch via merge from `develop` on 2026-03-29, so this work is implementation-ready rather than speculative.

## Naming Rationale
`rust-service-hardening` is preferred over `rust-production-baseline` and `rust-production-hardening` because it makes the intended scope clearer:
- It is for Rust services, not all Rust code.
- It fits Tokio, Axum, Hyper, Tonic, and Reqwest-oriented backend work well.
- It avoids over-claiming applicability to embedded, library-only, or sync-only projects.

## Skill Description Draft

```yaml
description: Harden Rust backend services for production readiness. Use when working on Tokio, Axum, Hyper, Tonic, or Reqwest-based services and you need guidance or review for config validation, structured tracing, request IDs, timeouts, retries, graceful shutdown, backpressure, body limits, health checks, metrics, and dependency hygiene. Not for non-service Rust crates, embedded Rust, pure sync CLI tools, or low-level libraries without runtime, network, or server concerns.
```

This wording should remain close to final because it improves automatic self-selection and self-exclusion.

## Applicability

### Best fit
- Tokio-based services
- Axum, Hyper, Tonic, and Reqwest-based applications
- API servers, workers, background processors, and service-to-service components
- Projects preparing for deployment, load, incident response, or operational review

### Do not use for
- non-service Rust crates
- embedded Rust
- pure sync CLI tools
- low-level libraries with no runtime/network/server concerns

These exclusions should appear in both:
- the `description` frontmatter in concise form
- an explicit scope section in `SKILL.md`

## Activation Triggers
Signals that should help an orchestrating session choose this skill instead of `rust-development` or `rust-best-practices`:

- user asks to make a Rust service production-ready
- user mentions Tokio service hardening
- user mentions Axum, Hyper, Tonic, or Reqwest service concerns
- user asks about graceful shutdown, request IDs, timeouts, retries, backpressure, or health endpoints
- user is reviewing service readiness before deploy, load, or incident response
- user wants a checklist or review of runtime/operational defaults before business logic work

Negative signals:
- pure library/API surface design without service runtime concerns
- idiomatic Rust implementation help not tied to service operation
- embedded or sync-only CLI work

## Core Topics
Derived from the source checklist document, ordered by implementation priority:

### Tier 1: blocking-critical defaults
1. Validate config at startup
2. Timeouts on clients and servers
3. Graceful shutdown and draining

### Tier 2: high-value runtime safety and operability
4. Structured logging and tracing
5. Request ID generation and propagation
6. Retries only for idempotent operations, with backoff and jitter
7. Bounded queues and backpressure
8. `spawn_blocking` for blocking or CPU-heavy work
9. Input size limits and streaming parsing

### Tier 3: readiness and maintenance defaults
10. Dependency hygiene (`cargo audit`, `cargo deny`)
11. Health endpoints and basic metrics
12. CI checks and release checklist

## Relationship to Existing Rust Skills
- `rust-development`: broad implementation and review guidance for Rust code
- `rust-best-practices`: structural patterns and architecture-level Rust design
- `rust-service-hardening`: service operability, resilience, and production defaults

This skill should complement the existing Rust skills rather than duplicate them.

## Progressive Disclosure Layout
- `SKILL.md`: concise orchestration, activation rules, scope, exclusions, delegation rules
- `references/production-checklist.md`: distilled checklist and review criteria
- `references/framework-notes.md`: one shared reference file with H2 sections for Tokio/Axum/Hyper/Tonic/Reqwest in v0.1; split into per-framework files only if the document grows beyond roughly 300 lines

Keep `SKILL.md` short and move implementation details into references.

## Agent Strategy
Phase 1 should avoid overbuilding. Start by reusing existing `sc-rust` agents where possible.

### Phase 1
- Use existing architecture/review agents if present in `sc-rust`
- Lock v0.1 to guidance and review only; do not generate scaffolds or config snippets in the first release
- For sprint review or diff-scoped review, use a single reviewer that covers only applicable topics

### Phase 2
If generic Rust review is too broad, add specialized review agents:
- `rust-observability-review`
- `rust-resilience-review`
- `rust-safety-release-review`

If added, they should:
- run only for relevant domains; skip irrelevant domains rather than force all three
- run in parallel for full-review or phase-ending review
- return fenced JSON with deterministic aggregation

## Suggested SKILL.md Scope Section

```md
## Scope

Use this skill for Rust services that handle network traffic, async workloads, request lifecycles, or deployment/runtime concerns.

Best fit:
- Tokio-based services
- Axum, Hyper, Tonic, or Reqwest-based backends
- API servers, workers, and service processes

Do not use this skill for:
- non-service Rust crates
- embedded Rust
- pure sync CLI tools
- low-level libraries with no runtime/network/server concerns
```

## Implementation Decisions
1. `sc-rust` is already present in this branch, so the skill should be implemented directly in the package rather than planned as a future add-on.
2. Start with one `references/framework-notes.md` file using H2 sections per framework; split later only if the file becomes too large.
3. v0.1 is review-and-guidance only. Do not add generators or scaffolding until real usage shows the need.

## Next Steps
- Keep this plan as the source of truth for naming and scope.
- Create `packages/sc-rust/skills/rust-service-hardening/SKILL.md` from this plan.
- Add `references/production-checklist.md` and `references/framework-notes.md` in the same package.
- Update `packages/sc-rust/manifest.yaml` artifact lists to include the new skill and references.
- Bump the `sc-rust` package version from `0.9.0` when the new skill is added.
- Preserve the exclusion list verbatim unless the skill scope changes intentionally.
