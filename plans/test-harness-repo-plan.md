# Test Harness Repo Plan (Draft)

> **⚠️ SUPERSEDED**: This draft plan has been superseded by the formal design specification at:
> `/Users/randlee/Documents/github/synaptic-canvas/docs/requirements/test-harness-design-spec.md`
>
> **Implementation Status**: Phase 1 Complete (2026-01-16)
> - Harness code: `test-packages/harness/` (~6,000 lines)
> - Unit tests: 103 passing
> - See design spec for current architecture and implementation details.

---

## Goal
Create a dedicated, instrumented test repository with Claude hooks enabled to capture tool/agent activity and provide a stable, resettable environment for package/agent testing.

## Hook Research (Claude Code)
Claude Code supports hooks configured via `hooks/hooks.json` at the plugin root (or in standalone `.claude/` setups). Hooks can be triggered on events such as `PreToolUse`, `PostToolUse`, `PreTask`, `PostTask`, `PreCommand`, and `PostCommand`. Hooks can run commands/scripts to log or inspect activity. The plugin documentation notes hooks live in `hooks/hooks.json` at the plugin root; only `plugin.json` lives in `.claude-plugin/`.

Assumption: hooks are JSON-configured with event matchers and commands. We will implement logging hooks that append JSON lines to a trace file in the test repo.

## Proposed Repo Layout (test repo)
```
<test-repo>/
├── .claude/
│   ├── settings.json (optional)
│   └── ...
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── reset-test-repo.sh
│   └── bootstrap-test-repo.sh
├── pm/
│   ├── ARCH-SC.md
│   └── checklist.md
├── README.md
└── .gitignore
```

## Hook Strategy
- Log to `test-packages/reports/trace.jsonl` (path is configurable; default to test repo local `reports/trace.jsonl`).
- Capture command name, args, timestamp, and tool result summary for `PreToolUse`/`PostToolUse`.
- Capture high-level task lifecycle via `PreTask`/`PostTask`.

## Hook Implementation (Draft)
1) `hooks/hooks.json` with entries for:
   - `PreToolUse`
   - `PostToolUse`
   - `PreTask`
   - `PostTask`
   - `PreCommand`
   - `PostCommand`
2) Each hook runs a small script, e.g. `scripts/log-hook.sh` or `scripts/log-hook.py`, that appends a JSONL record.

Example record:
```json
{"ts":"2025-01-16T04:12:00Z","event":"PostToolUse","tool":"Task","args":{...},"status":"success","summary":"agent sc-startup-init"}
```

## Reset Strategy
- `scripts/reset-test-repo.sh`:
  - `git reset --hard` to a known commit
  - `git clean -fdx` to remove artifacts
  - recreate `reports/` dir
- Use a fixed base commit as a fixture snapshot.

## Bootstrap Strategy
- `scripts/bootstrap-test-repo.sh`:
  - install plugins into a local test path
  - set `CLAUDE_CLI_PATH`, `ANTHROPIC_API_KEY` (if available)
  - configure hook output path

## Local Test Harness Integration
- `test-packages/run_local_tests.py` will accept `--test-repo <path>` to point tests at the instrumented repo.
- Integration tests will:
  - copy plugin bundle to test repo
  - run `claude -p` commands with `--plugin-dir`
  - collect stdout and `trace.jsonl` for review
- Reports will aggregate:
  - pytest output
  - captured prompts/responses
  - hook traces

## Open Questions
- Exact hook schema field names (e.g., matcher syntax and variables passed to hooks). Confirm from Claude docs.
- Whether hooks are supported in local `.claude/` for non-plugin installs.
- Best location for trace output file.

## Next Actions
- After test repo is created, clone it locally.
- Implement hook config + logging script.
- Add reset/bootstrap scripts.
- Wire tests to use `--test-repo` path.
- Expand integration tests to validate hook traces include expected agent calls.
