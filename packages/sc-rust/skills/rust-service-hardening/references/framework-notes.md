# Framework Notes

Use only the sections that match the service under review. Skip irrelevant frameworks rather than loading the whole file mentally into every task.

## Tokio

Focus areas:
- signal handling and coordinated shutdown
- bounded `mpsc` channels and saturation behavior
- `spawn_blocking` for blocking or CPU-heavy work
- task cancellation and timeout boundaries

Review prompts:
- Where does the service stop accepting work during shutdown?
- Which tasks outlive a request, and how are they canceled or drained?
- Are queues bounded and intentionally handled on saturation?

## Axum / Hyper

Focus areas:
- request/response middleware
- request ID injection and propagation
- body-size limiting
- server-level timeout and shutdown handling

Review prompts:
- Is there middleware for request IDs, tracing, auth, and body limits where needed?
- Are handlers depending on proxy defaults instead of app-level safeguards?
- Is graceful shutdown wired through the server entrypoint rather than left to process exit?

## Tonic

Focus areas:
- interceptor-based request context propagation
- deadlines and timeouts
- graceful server shutdown
- streaming request and response behavior

Review prompts:
- Are RPC deadlines enforced intentionally?
- Are correlation IDs or trace context propagated through interceptors or spans?
- Are long-lived streams bounded, cancelable, and observable?

## Reqwest

Focus areas:
- shared client reuse
- client timeouts and per-request overrides
- retry boundaries
- outbound request tagging with request IDs or trace context

Review prompts:
- Is the service constructing a shared client once rather than rebuilding it in hot paths?
- Are timeouts explicit?
- Are retries restricted to transient failures and safe operations?
- Is downstream traffic traceable back to an ingress request or job ID?
