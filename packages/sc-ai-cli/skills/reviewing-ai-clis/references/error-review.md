# Error Review

Error handling is a primary review area for AI-facing CLIs.

This review is contract-first and language-agnostic by default. Do not reach for language-specific implementation guidance unless the problem requires it.

## Review Questions

Ask:
- Does the public contract expose typed success and error results?
- Are error categories stable enough for automation?
- Are validation, state, dependency, timeout, and internal failures distinguishable?
- Does the error message tell the caller what to do next when recovery is possible?
- Does the same error contract appear in CLI and MCP paths?

## Strong Patterns

Strong implementations usually have:
- explicit result envelopes or discriminated unions
- stable error codes
- structured `details`
- `suggested_action` or equivalent corrective guidance
- tests that assert error shape, not just the presence of failure

## Weak Patterns

Weak implementations usually have:
- catch-all `anyhow` or exception text leaked directly into the contract
- prose-only stderr behavior in `--json` mode
- no stable error category
- stack traces or debug formatting in machine output
- different error schemas in CLI and MCP wrappers

## Review Output

When you find an error-contract issue, say specifically whether the problem is:
- missing typing
- missing structure
- missing actionable guidance
- schema drift between CLI and MCP
- insufficient test coverage of failure modes

## Example Finding Shapes

- `High`: `set-profile --json` returns a flat error string with no stable code, so automation cannot distinguish validation failure from transport failure.
- `Medium`: the CLI exposes `details`, but the message gives no corrective direction such as valid command alternatives or required argument names.
- `High`: the MCP wrapper replaces CLI error codes with transport-specific prose, breaking contract identity between the two surfaces.
