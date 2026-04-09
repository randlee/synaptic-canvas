# Plan Review

Use this reference when reviewing a CLI design or plan before implementation.

## Required Design Commitments

The plan should state explicitly:
- every command supports `--json`
- request and response schemas are defined before human formatting
- error results are typed and actionable
- MCP wrappers reuse the same business payloads
- mutating commands have readback paths
- external integrations have a simulator strategy

## Gaps to Flag Early

Flag plans that:
- mention JSON only as an output option for some commands
- defer error modeling until implementation
- describe the MCP wrapper as a separate translation layer
- define set/apply/create commands without get/list/status counterparts
- assume tests will use live infrastructure

## Approval Standard

Do not consider the plan sound until it is clear:
- what the public JSON contract is
- how errors are modeled
- how state changes are audited
- how CLI and MCP parity is verified
- how external dependencies are simulated in tests
