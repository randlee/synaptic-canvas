# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.14.0] - 2026-09-27
### Added
- gpt-6 model support. Aliases: `sol` -> `gpt-6-sol`, `astra` -> `gpt-6-astra`,
  `luna` -> `gpt-6-luna`, `terra` -> `gpt-5.6-terra`, `codex` -> default. Full slugs
  `gpt-6-sol`, `gpt-6-astra`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`,
  `gpt-5.5` are accepted as-is.
- `--effort {low,medium,high,xhigh,max,ultra}` on `sc_codex_task.py` and `ai_cli run`, and an
  optional `reasoning_effort` payload/schema field. Passed to Codex as
  `-c model_reasoning_effort="<level>"`; omitted when unset so `~/.codex/config.toml` applies.
  Levels are validated per model. Effort is carried in the payload (background runs keep it)
  and logged as a top-level `reasoning_effort` field. Ignored by the Claude runner.
- Command-line `--model` / `--effort` override the JSON payload.
- `sc-codex` agent added to `.claude/agents/registry.yaml`.

### Changed
- Default Codex model is now `gpt-6-astra` (was `gpt-5.2-codex`).
- ChatGPT-account fallback now retries once on `gpt-5.5` for any other model (was
  `gpt-5.2` for codex-native models only), clamping effort to `xhigh`, and logs a
  `model_fallback` event.
- Docs: README Quick Start uses real flags; command/skill docs describe models, effort and the
  actual background default (background for `sc_codex_task.py`, blocking for `ai_cli run`).

### Removed (breaking)
- Legacy model aliases `gpt-5.2-codex`, `codex-max`/`max`, `codex-mini`/`mini`, `gpt-5`,
  `gpt-5.2`, `gtp-5`. Unknown models now fail with an error listing valid aliases and slugs.

## [0.8.0 - 0.13.0]
- Intermediate versions (repo-wide version bumps) were not recorded in this changelog.

## [0.7.0] - 2026-01-20
### Added
- Task Tool-compatible Codex runner with hook emulation.
- `ai_cli` module for schema validation, command execution, and JSONL output.
- Input/output JSON schemas for task payloads and results.

### Notes
- Initial release of sc-codex.
