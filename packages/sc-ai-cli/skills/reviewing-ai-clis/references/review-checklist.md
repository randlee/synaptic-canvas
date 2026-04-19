# Review Checklist

Use this checklist for critical review of an existing AI-facing CLI.

Default stance:
- stay language-agnostic at the contract level first
- only reach for language-specific implementation guidance when a concrete implementation detail requires it

## Findings Format

Present findings first and order them by severity:
- critical
- high
- medium
- low

Each finding should include:
- what is wrong
- why it matters for AI or automation use
- file reference or plan section
- remediation direction

## Contract Checks

Check whether:
- every relevant command supports `--json`
- commands that accept structured input define a request model rather than relying only on prose-oriented flags and implicit parsing
- JSON output is complete enough for automation
- machine-significant data exists in JSON, not only prose
- human-readable mode does not expose machine-significant data that is missing from JSON mode
- success and error shapes are stable across commands
- exit behavior and JSON behavior are deterministic
- the same command keeps a stable JSON envelope across different operating modes
- partial results are surfaced explicitly rather than silently skipped
- success-path JSON coverage and failure-path JSON coverage are both present
- tests assert the JSON contract directly across command families rather than only checking exit codes or human-readable text

## Error Checks

Check whether:
- errors are typed or discriminated
- callers can branch on error code or category
- error details are structured
- messages help the caller recover or correct input
- `--json` mode preserves the error contract instead of falling back to plain stderr prose
- top-level failures use the same machine-contract family as success paths

## MCP Checks

Check whether:
- the CLI request models are reusable outside the CLI entrypoint
- the MCP wrapper shares the same request and response models
- business payloads are not reshaped between CLI and MCP
- tests compare shared fixtures across CLI and MCP paths
- the wrapper is thin rather than a second implementation
- provider-specific fields are isolated from the canonical machine contract or clearly namespaced as extensions

## Mutation and Auditability Checks

Check whether:
- every mutating command has a corresponding read command
- tests verify state after mutation
- mutation responses include enough detail to support automation
- state can be confirmed without relying only on logs
- the read path is as rich as the mutating path, not a thin afterthought
- each mutation family has audit symmetry: immediate result, retained audit/log if applicable, and follow-up query/read path

## Simulation Checks

If the tool integrates with external systems, check whether:
- simulator-backed tests exist
- the simulator is stateful rather than rebuilt per call
- the simulator is below the CLI layer
- the same business logic runs against real and simulated backends
- failure modes like timeouts, invalid state, and dependency errors are exercised
- alternate behaviors and fault injection are possible without patching business logic
- deterministic seeded fixtures or explicit starting-state controls exist when simulator state matters to test reproducibility
- partial-success or degraded-mode scenarios are exercised when the real backend can produce them
- device and service integrations use a swappable adapter boundary
- database-backed integrations use a realistic local persistence simulator such as a JSON store or SQLite when query or schema behavior matters

## Warning Signs

- JSON output added only for a subset of commands
- one generic error string used for many failure modes
- separate MCP DTOs that diverge from CLI DTOs
- mutating commands with no readback path
- tests that require live infrastructure for routine verification
- stateless fakes used where persistent backend state is central to CLI behavior
- help/examples that advertise flags or shapes the implementation does not actually support
- human-readable output that includes machine-significant detail unavailable through `--json`
- machine payloads that use display sentinels like `(main)` instead of typed/null fields
- unknown machine fields are dropped in a way that breaks forward compatibility
- branching results exposed as unrelated JSON shapes instead of explicit tagged unions
- CLI output DTOs that directly re-export storage or third-party wire models without a stable CLI boundary

## Calibration Rule

Existing repos may contain useful patterns without meeting the target bar end to end.

Do not excuse a weak CLI because another internal CLI does the same thing. Review against the desired AI-first standard:
- universal machine-readable output
- typed, stable, corrective error contracts
- CLI/MCP parity
- auditable mutations
- simulator-backed tests where external systems exist
