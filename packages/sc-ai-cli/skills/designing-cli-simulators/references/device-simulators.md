# Device and Protocol Simulators

Use this reference for serial, USB, TCP, HTTP, RPC, and similar external integrations.

## Placement

Prefer the lowest practical simulation boundary:
- transport abstraction
- protocol adapter
- device client

Avoid simulating only the final service call if the real behavior depends on protocol semantics, connection state, retries, framing, or device status transitions.

## Required Properties

Device and protocol simulators should usually support:
- persistent connection or session state when the real integration has it
- realistic command/response sequencing
- controllable error injection
- realistic timing or delayed responses when timing affects behavior
- observable device state for readback verification

## Behavior Mutation Examples

Make it possible to configure:
- timeouts
- disconnects
- corrupted or invalid responses
- retryable transient failures
- permanent failures
- busy or locked states
- stale reads or delayed state convergence if the real system has them

## State Model

Document:
- what state lives on the device or service
- what transitions mutate that state
- what read operations expose it
- what invalid transitions should be rejected

Tests should be able to verify state after mutations using the same read commands the real CLI would use.

## Fidelity Guidance

Aim for enough fidelity to verify normal flows and the failures the CLI claims to handle. Do not overbuild hardware-level emulation if the CLI only depends on a narrower application contract, but do not collapse meaningful protocol behavior into unrealistic one-line mocks.

For a concrete starting point, see `simulator-examples.md`, especially the map-backed request-handler pattern.
