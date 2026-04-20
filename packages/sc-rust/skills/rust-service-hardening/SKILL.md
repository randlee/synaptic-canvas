---
name: rust-service-hardening
version: 0.11.0
description: Harden Rust backend services for production readiness. Use when working on Tokio, Axum, Hyper, Tonic, or Reqwest-based services and you need guidance or review for config validation, structured tracing, request IDs, timeouts, retries, graceful shutdown, backpressure, body limits, health checks, metrics, and dependency hygiene. Not for non-service Rust crates, embedded Rust, pure sync CLI tools, or low-level libraries without runtime, network, or server concerns.
depends_on:
  rust-service-hardening-agent: 0.x
  rust-architect: 0.x
  rust-code-reviewer: 0.x
  rust-code-explorer: 0.x
  rust-qa-agent: 0.x
---

# Rust Service Hardening

This skill focuses on runtime behavior and service operability. Use it when the main question is "is this Rust service safe to run under load and during deploys?" rather than "is this Rust code idiomatic?"

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

## Activation Triggers

Prefer this skill when the user mentions:
- making a Rust service production-ready
- Tokio service hardening
- graceful shutdown, request IDs, timeouts, retries, backpressure, or health endpoints
- deploy-readiness, runtime readiness, or production hardening for Axum, Hyper, Tonic, or Reqwest-based code

Prefer other Rust skills when the task is mostly about:
- idiomatic implementation details or general Rust coding standards → `rust-development`
- crate boundaries, typestate, sealed traits, or structural design patterns → `rust-best-practices`

## Priority Order

Apply checks in this order and stop early only if the higher-priority gaps make the rest of the review misleading.

### Tier 1: blocking-critical defaults
1. Config validation at startup
2. Timeouts on clients and servers
3. Graceful shutdown and draining

### Tier 2: runtime resilience and operability
4. Structured logging and tracing
5. Request ID generation and propagation
6. Retries only for idempotent operations
7. Bounded queues and backpressure
8. `spawn_blocking` for blocking or CPU-heavy work
9. Input size limits and streaming parsing

### Tier 3: maintenance and release readiness
10. Dependency hygiene
11. Health endpoints and basic metrics
12. CI checks and release checklist

## References

- `references/production-checklist.md` — primary review checklist and evidence to look for
- `references/framework-notes.md` — framework-specific notes for Tokio, Axum/Hyper, Tonic, and Reqwest

Read `production-checklist.md` first. Read `framework-notes.md` only for the frameworks that actually appear in the codebase or task.

## Agent Delegation

Use these existing `sc-rust` agents for service-hardening workflows:

| Operation | Agent | Returns |
|-----------|-------|---------|
| Dedicated service-hardening review | `rust-service-hardening-agent` | Fenced JSON `{success,data,error}` findings or a structured `skipped` result when service indicators are absent |
| Design review or rollout hardening plan | `rust-architect` | Fenced JSON `{success,data,error}` architecture blueprint or hardening plan |
| Sprint review or diff-scoped service-hardening review | `rust-code-reviewer` | Fenced JSON `{success,data,error}` findings limited to applicable service-hardening topics |
| Codebase tracing before review | `rust-code-explorer` | Fenced JSON `{success,data,error}` codepath map for startup, request handling, clients, queues, and shutdown behavior |
| Validation pass after changes | `rust-qa-agent` | Fenced JSON `{success,data,error}` QA report covering tests, quality gates, and broader validation after hardening work |

Invoke these agents via Agent Runner using `.claude/agents/registry.yaml`, and keep the prompt focused on service-hardening concerns rather than general Rust style issues.

Dedicated `rust-service-hardening-agent` assignment template:

```json
{
  "review_mode": "doc_review | sprint_review | phase_end",
  "worktree_path": "/absolute/path/to/worktree",
  "review_targets": [
    "src/",
    "Cargo.toml"
  ],
  "topics": [
    "config_validation",
    "timeouts",
    "graceful_shutdown"
  ],
  "service_indicator_dependencies": [
    "tokio",
    "axum",
    "hyper",
    "tonic",
    "warp",
    "actix-web",
    "reqwest"
  ],
  "notes": "optional context"
}
```

## Review Modes

### Design or readiness review

Use this mode when reviewing a plan, service design, or rollout readiness:

1. Read `references/production-checklist.md`
2. Identify which tiers and topics are actually relevant to the service
3. Read the applicable sections from `references/framework-notes.md`
4. Use `rust-architect` when the user wants architecture advice, a rollout hardening plan, or a gap analysis before code changes

### Sprint review or diff-scoped review

Use this mode for review of recent changes or a narrow file set:

1. Read `references/production-checklist.md`
2. Prefer `rust-service-hardening-agent` for dedicated runtime-hardening review
3. Use `rust-code-reviewer` only when the request is a broader Rust review that should include service-hardening concerns
4. Limit findings to applicable service-hardening topics only
5. Prioritize issues with clear operational impact over general style commentary

### Codebase tracing before review

If the service boundaries are unclear, use `rust-code-explorer` first to locate:
- server startup and config loading
- HTTP/gRPC client construction
- middleware and request lifecycle hooks
- background workers, queues, and task boundaries
- shutdown handling and signal paths

### Validation pass after changes

Use `rust-qa-agent` when the user wants a QA run after hardening changes or asks for broader validation beyond review guidance.

Suggested `rust-qa-agent` assignment:

```json
{
  "worktree_path": "/absolute/path/to/worktree",
  "review_mode": "sprint_review | phase_end",
  "review_targets": [
    "src/",
    "Cargo.toml"
  ],
  "run_checks": {
    "fmt": true,
    "clippy": true,
    "tests": true,
    "coverage": false
  },
  "baseline_ref": "optional git ref",
  "artifact_regeneration_required": false,
  "artifact_commands": "",
  "notes": "optional context"
}
```

## Relationship to Other Skills

- `rust-development` handles broad Rust implementation standards.
- `rust-best-practices` handles structural Rust design patterns.
- `rust-service-hardening` handles runtime, resilience, and service-operability defaults.

These skills complement each other, but this skill should win when the main concern is operating a Rust service safely in production.
