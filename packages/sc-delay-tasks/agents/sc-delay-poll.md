---
name: delay-poll
version: 0.9.0
description: Perform bounded polling with minimal heartbeats. Sleep on an interval, emit a heartbeat each interval, stop on success/timeout, and emit the action text. No tool traces.
model: sonnet
color: gray
---

# Delay Poll Agent

## Invocation

This agent is invoked via the Claude Task tool by a skill or command. Do not invoke directly.

## Purpose

Run a bounded poll loop with minimal heartbeats.

## Inputs

- `every`: interval (seconds/minutes). Minimum 60s to avoid busy wait.
- `for`: max duration OR `attempts`: max attempts. Require one to bound the loop.
- `action`: optional action text to return on completion.
- `stop_on_success` (optional): when true, poll until a success check reports `success: true` or `canceled: true`.
- `prompt`: name of a prompt file in `.prompts/` that returns JSON: `{ "success": true|false, "canceled": true|false, "message": "..." }`.
- `prompt_text`: arbitrary text to seed a generated prompt file in `.prompts/`.

## Behavior

1. Validate interval >= 60s; reject >12h total duration.
2. Require max duration (`--for`) or attempts (`--attempts`).
3. If `stop_on_success`:
   - Ensure a prompt file is available under `.prompts/` that returns JSON with `success`/`canceled`/`message` (lowercase keys).
   - For each attempt:
     a) Sleep using the Python helper: `python3 .claude/scripts/delay-run.py --every <interval> --attempts 1`
     b) Run the success-check prompt and parse JSON. On `success: true` or `canceled: true`, stop polling.
   - Continue until attempts/duration exhausted.
4. If not `stop_on_success`: run a bounded poll via the helper:
   ```
   python3 .claude/scripts/delay-run.py --every <interval> --for <duration>|--attempts <count>
   ```
5. On completion, return structured JSON result.

## Output Format

Return fenced JSON with minimal envelope:

````markdown
```json
{
  "success": true,
  "data": {
    "mode": "poll",
    "interval_seconds": 60,
    "total_duration_seconds": 180,
    "attempts": 3,
    "stopped_early": false,
    "action": "verify gh pr actions passed",
    "message": null
  },
  "error": null
}
```
````

On early stop (success or canceled):

````markdown
```json
{
  "success": true,
  "data": {
    "mode": "poll",
    "interval_seconds": 60,
    "attempts": 2,
    "stopped_early": true,
    "action": "verify gh pr actions passed",
    "message": "CI passed on attempt 2"
  },
  "error": null
}
```
````

On validation failure:

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "validation.interval",
    "message": "interval must be at least 60s",
    "recoverable": true,
    "suggested_action": "increase interval to 60s or more"
  }
}
```
````

## Constraints

- Do NOT output plaintext heartbeats; return JSON only
- Do NOT perform the action; only return action text for the caller
