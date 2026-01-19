---
allowed-tools: Bash(python3 scripts/sc_codex_task.py*)
name: sc-codex
description: Run Codex tasks via the ai_cli runner (supports JSON input, background runs, and model selection).
version: 0.7.0
options:
  - name: --model
    args:
      - name: model
        description: Codex model or alias (e.g., codex, max, mini, gpt-5).
    description: Select the Codex model.
  - name: --background
    description: Run in background mode (returns output_file).
  - name: --json
    description: Treat remaining arguments as JSON Task Tool input.
  - name: --help
    description: Show usage.
---

# /sc-codex

Run a Codex task using the Task Tool-compatible runner.

Usage:
- `/sc-codex write a haiku about rain`
- `/sc-codex --model mini write a haiku about rain`
- `/sc-codex --background write a haiku about rain`
- `/sc-codex --json {"description":"Compose haiku","prompt":"compose a haiku","subagent_type":"sc-codex"}`

## Context

- Execute: !`python3 scripts/sc_codex_task.py $ARGUMENTS`
