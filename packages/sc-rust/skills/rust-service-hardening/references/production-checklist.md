# Rust Service Hardening Checklist

Use this checklist when reviewing a Rust service for production readiness. Apply items in priority order and skip topics that are genuinely irrelevant to the service type.

## How to use this checklist

- Start with Tier 1 and treat gaps there as blocking-critical.
- For each topic, look for real evidence in code, config loading, middleware, server startup, background workers, and client construction.
- Prefer concrete findings over aspirational advice.
- If a topic does not apply, mark it skipped and state why.

## Tier 1: blocking-critical defaults

### 1. Config validation at startup

Look for:
- config parsed once at startup
- invalid config causing startup failure rather than degraded runtime behavior
- required URLs, ports, credentials, and limits validated before serving traffic

Common gaps:
- lazy config parsing deep in handlers
- invalid defaults that only fail on first request
- partial startup where the process is "alive" but unusable

### 2. Timeouts on clients and servers

Look for:
- outbound HTTP/gRPC/database clients with explicit timeouts
- request-level or handler-level timeouts where appropriate
- no "infinite wait" defaults on critical paths

Common gaps:
- shared `reqwest::Client` without a timeout
- long-lived tasks or handlers with no cancellation boundary
- relying entirely on upstream infrastructure to enforce timeouts

### 3. Graceful shutdown and draining

Look for:
- signal handling or coordinated shutdown trigger
- stop accepting new work before process exit
- in-flight work drained or canceled intentionally
- background tasks joined or shut down cleanly

Common gaps:
- abrupt process exit on SIGTERM
- background workers orphaned during shutdown
- no separation between "stop intake" and "finish in-flight work"

## Tier 2: runtime resilience and operability

### 4. Structured logging and tracing

Look for:
- `tracing` or structured logging rather than ad hoc `println!`
- consistent fields across requests and tasks
- spans or contextual fields around key operations

Common gaps:
- free-form logs without machine-parseable fields
- inconsistent field names across request lifecycle events
- critical error paths with no context attached

### 5. Request ID generation and propagation

Look for:
- request IDs generated or accepted at ingress
- request IDs attached to logs and spans
- request IDs propagated to downstream calls where practical

Common gaps:
- request IDs present only at the edge but not in service logs
- per-log context that omits the request or correlation ID
- new IDs generated mid-request without linkage

### 6. Retries only for idempotent operations

Look for:
- retry policy scoped to transient failures
- idempotency checks before retrying writes or side effects
- backoff and jitter rather than immediate tight loops

Common gaps:
- blanket retries for all HTTP methods
- retry storms around overloaded dependencies
- retries implemented without max-attempt bounds

### 7. Bounded queues and backpressure

Look for:
- bounded channels or queue limits
- explicit decision when saturated: await, shed, or degrade
- queue depth treated as an operational concern

Common gaps:
- unbounded channels in hot paths
- producer fan-out with no backpressure strategy
- best-effort buffering that silently grows until memory pressure

### 8. `spawn_blocking` for blocking or CPU-heavy work

Look for:
- blocking I/O, compression, parsing, or CPU-heavy work isolated from async executors
- explicit use of `spawn_blocking` or dedicated worker pools where needed

Common gaps:
- filesystem, compression, or expensive serialization inside async handlers
- CPU-heavy loops on executor threads
- mixed blocking/async code that only fails under load

### 9. Input size limits and streaming parsing

Look for:
- body-size limits or frame-size limits at ingress
- streaming parse approach for large inputs
- avoidance of "read whole body into memory" on untrusted or large payloads

Common gaps:
- unlimited request bodies
- eager buffering of uploads or large JSON blobs
- implicit trust in reverse proxy defaults

## Tier 3: maintenance and release readiness

### 10. Dependency hygiene

Look for:
- `cargo audit` and `cargo deny` in normal workflow or CI
- lockfile discipline
- dependency additions justified rather than casual

Common gaps:
- no supply-chain checks in CI
- stale vulnerable dependencies accepted as background noise
- unnecessary crates for simple problems

### 11. Health endpoints and basic metrics

Look for:
- liveness and readiness distinctions where relevant
- at least minimal metrics for request count, latency, error rate, or saturation
- readiness depending on actual dependency health when appropriate

Common gaps:
- `/healthz` always returns 200 regardless of real state
- no visibility into queue depth or error spikes
- readiness that reports healthy before dependencies are usable

### 12. CI checks and release checklist

Look for:
- `cargo fmt --check`
- clippy with warnings treated seriously
- tests in CI
- release checklist or equivalent release discipline

Common gaps:
- local-only quality gates
- warnings normalized into background noise
- no rollback or deploy-readiness checklist

## Review output guidance

When reporting findings:
- lead with Tier 1 issues
- explain the operational failure mode
- note what evidence supports the finding
- keep recommendations concrete and bounded

Good example:
- "Outbound `reqwest::Client` in `client.rs` has no timeout, so a stalled downstream can pin request tasks indefinitely."

Weak example:
- "Consider adding more resilience."
