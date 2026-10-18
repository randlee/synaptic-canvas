# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.14.1] - 2026-10-17
### Fixed
- The launched `codex`/`claude` process no longer inherits the caller's
  `ATM_IDENTITY` (two agents would share one ATM identity). `ATM_TEAM` is kept,
  so the child stays on the caller's team.

## [0.14.0] - 2026-10-17
Model selection and reasoning effort, based on the design of PR #116 by Erik Hauan (@ehrvs),
re-implemented on the shared model table.

### Added
- `--effort {low,medium,high,xhigh,max,ultra}` on `sc_codex_task.py` and `ai_cli run`, and an
  optional, nullable `reasoning_effort` payload/schema field. Codex gets
  `-c model_reasoning_effort=<level>`, the Claude runner gets `--effort <level>`; when unset no
  flag is passed and the CLI's own configuration applies. Levels are validated per model.
- `--model` / `--effort` flags override the JSON payload (applied before validation). The
  resolved full model id is written back into the payload for background runs and logs.
- `reasoning_effort` in every task start/end/error log event.
- Tests that keep the input schema and the docs in sync with the model table.

### Changed
- Models, aliases, defaults, and per-model efforts now come from the shared
  `agent_models.py` (synced to `scripts/ai_cli/agent_models.py`); sc-codex has no private model
  table. See the README table.
- Default Codex model is `gpt-6.1-sol` (alias `sol`; `codex` points at it too). Aliases: `astra`,
  `sol`, `terra`, `luna`. Claude runner default is `claude-fable-5-1` (alias `fable`); Claude
  aliases `fable`, `opus`, `sonnet`, `haiku` now resolve to full ids.
- Unknown models, including in the JSON payload, fail before launch with a message listing the
  valid aliases and ids, instead of a raw pydantic error.
- The CLI is started through its `shutil.which` path (Windows `codex.cmd`/`claude.cmd`), and the
  prompt is sent as UTF-8 bytes on stdin instead of argv.
- Docs: README Quick Start uses flags that exist; one model/effort table in the README, linked
  from the command, skill, and `ai_cli` docs.

### Removed (breaking)
- Legacy model names `gpt-5.2-codex`, `gpt-5.1-codex-max`, `gpt-5.1-codex-mini`, `codex-max`/`max`,
  `codex-mini`/`mini`, `gpt-5`, `gpt-5.2`, `gtp-5`. `max` is now only an effort level.
- The ChatGPT-account retry on a fallback model: codex no longer serves `gpt-5.5`, so the retry
  could not succeed. Failures are reported as-is.

### Notes
- Versions 0.8.0-0.13.0 were released without changelog entries.

## [0.7.0] - 2026-01-20
### Added
- Task Tool-compatible Codex runner with hook emulation.
- `ai_cli` module for schema validation, command execution, and JSONL output.
- Input/output JSON schemas for task payloads and results.

### Notes
- Initial release of sc-codex.
