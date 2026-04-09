# Review Checklist

Use this checklist for critical review of an existing AI-facing CLI.

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
- JSON output is complete enough for automation
- machine-significant data exists in JSON, not only prose
- success and error shapes are stable across commands
- exit behavior and JSON behavior are deterministic

## Error Checks

Check whether:
- errors are typed or discriminated
- callers can branch on error code or category
- error details are structured
- messages help the caller recover or correct input
- `--json` mode preserves the error contract instead of falling back to plain stderr prose

## MCP Checks

Check whether:
- the MCP wrapper shares the same request and response models
- business payloads are not reshaped between CLI and MCP
- tests compare shared fixtures across CLI and MCP paths
- the wrapper is thin rather than a second implementation

## Mutation and Auditability Checks

Check whether:
- every mutating command has a corresponding read command
- tests verify state after mutation
- mutation responses include enough detail to support automation
- state can be confirmed without relying only on logs

## Simulation Checks

If the tool integrates with external systems, check whether:
- simulator-backed tests exist
- the simulator is below the CLI layer
- the same business logic runs against real and simulated backends
- failure modes like timeouts, invalid state, and dependency errors are exercised

## Warning Signs

- JSON output added only for a subset of commands
- one generic error string used for many failure modes
- separate MCP DTOs that diverge from CLI DTOs
- mutating commands with no readback path
- tests that require live infrastructure for routine verification
