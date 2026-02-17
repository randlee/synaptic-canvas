---
name: delay
description: Schedule a delayed one-shot or bounded polling action with minimal heartbeats. Emits the action text on completion for follow-up checks.
version: 0.9.0
options:
  - name: --minutes
    description: One-shot delay in minutes (or use --seconds for short waits).
  - name: --seconds
    description: One-shot delay in seconds (min 10s).
  - name: --every
    description: Poll interval (min 60s) for bounded polling.
  - name: --for
    description: Max duration for polling (e.g., 10m); required with --every unless --attempts is provided.
  - name: --attempts
    description: Max attempts for polling; required with --every unless --for is provided.
  - name: --until
    description: One-shot until a target time (HH:MM or ISO); converted to seconds; ignores seconds/minutes if provided.
  - name: --action
    description: Action text to emit on completion (e.g., \"Verify GH PR actions passed\").
  - name: --stop-on-success
    description: Enable polling that stops early when a success check passes or reports cancellation (requires a prompt file).
  - name: --prompt
    description: Name of a prompt file in `.prompts/` (relative to Claude startup dir) that defines the success/cancel check and returns JSON with Success/Cancelled/Message.
  - name: --prompt-text
    description: Arbitrary text to seed a generated prompt file in `.prompts/`; the command will wrap it with the required JSON output contract.
  - name: --help
    description: Show options concisely; no extra commentary.
---

# /delay command

Use this command to wait once or run a bounded poll with minimal heartbeat output. Delegate to the delay skill/agents (`delay-once`, `delay-poll`).

## Modes
- One-shot delay: `/delay --minutes N [--action \"text\"]` (or `--seconds` for short waits) or `/delay --until HH:MM|ISO [--action \"text\"]`
- Bounded polling: `/delay --every 1m --for 10m [--action \"text\"]` or `/delay --every 1m --attempts 10 [--action \"text\"]`
- Stop-on-success polling: add `--stop-on-success` with `--prompt <name>` (uses `.prompts/<name>.md`) or `--prompt-text \"...\"` (auto-creates `.prompts/delay-success-<ts>.md` wrapping the text). The prompt must return JSON: `{ \"Success\": true|\"true\"|false|\"false\", \"Cancelled\": true|false|\"true\"|\"false\", \"Message\": \"...\" }`. `Cancelled=true` stops immediately.
- If run with no options or `--help`: print concise options and usage; no repo-state chatter.

## Behavior
- Heartbeats: emit “Waiting Xm...” each minute/interval (or a single line for short waits).
- Completion: emit `Action: <action>` so the caller can run the follow-up check; heartbeats + final line only (no extra chatter).
- Bounds: require max duration or attempts for polling; reject intervals < 60s and durations < 10s or > 12h.
- No tool traces; concise outputs only.
- Stop-on-success: between checks, use `.claude/scripts/delay-run.sh --every <interval> --attempts 1 --suppress-action` for real waits; after each wait, run the success-check prompt from `.prompts/`. Stop early when Success=true or Cancelled=true; otherwise continue until attempts/duration exhaust.
- Implementation detail: agents invoke `.claude/scripts/delay-run.sh` to perform waits; do not shortcut or skip the helper. Only the final overall completion emits the `Action:` line.
