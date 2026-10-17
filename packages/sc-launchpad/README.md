# sc-launchpad

Launch Claude (including the `fable` model), Codex (including `sol`, `terra`, and `luna`), or Gemini as a background sub-agent runtime without
opening a visible terminal window.

## Included Artifacts

- `skills/launchpad/SKILL.md`
- `agents/launchpad.md`
- `scripts/sc_launchpad_task.py`
- `scripts/launchpad_shared.py`

## What It Does

`sc-launchpad` is the background-runtime counterpart to `sc-launch-term`.

Use it when another workflow needs to:

- start Claude, Codex, or Gemini as a child runtime
- keep the parent session responsive
- normalize ATM teammate-mode state before spawning the child
- return a machine-readable launch envelope instead of interactive terminal output

## Invocation Model

The skill spawns the `launchpad` agent with `run_in_background: true`.

The agent forwards one JSON payload to the runtime script, which launches the
selected CLI and returns a JSON envelope describing success, exit code, stdout,
stderr, and teammate-mode state.

## ATM Teammate Mode

Teammate mode is enabled only when:

1. the parent environment includes `ATM_TEAM`
2. the payload includes `atm_identity`

When both are present, the runtime:

- runs `atm teams add-member <team> <identity> --model <tool-or-model> --cwd <cwd>`
- launches the child process with both `ATM_TEAM` and `ATM_IDENTITY` set

Otherwise, the runtime clears both ATM variables before spawning the child.

## Security and Runtime Notes

- `sc-launchpad` launches only locally installed `claude`, `codex`, or `gemini` executables.
- The runtime preserves most of the parent environment, but explicitly normalizes `ATM_TEAM` and `ATM_IDENTITY` to avoid leaking partial teammate state.
- The `launchpad` agent is intentionally thin: it should make one runtime call and return the runtime stdout exactly as emitted.
- The runtime expects absolute working-directory paths in launch payloads.
- Structured, resumable, and isolated launches are described in "Sessions, Resume, and Isolation" below.
- This package depends on local Python 3 plus whichever AI CLI you are launching.

For Claude launches, `model` accepts `sonnet`, `haiku`, `opus`, or `fable`,
plus the corresponding supported full model names.

For Codex launches, `model` accepts `sol`, `terra`, or `luna`. The deprecated
`codex` alias routes to `gpt-5.6-terra`; the runtime also accepts the known
legacy Codex aliases for compatibility. The canonical model IDs are
`gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna`.

## Installation

```bash
/marketplace install sc-launchpad
```

This package is intended for local installation into a repository `.claude/`
surface where orchestrator skills or agents need background launch support.

## Example

```json
{
  "description": "Run a background code review",
  "prompt": "Review the changed files for risks and missing tests.",
  "tool": "codex",
  "model": "terra",
  "cwd": "/abs/path/to/repo",
  "atm_identity": "reviewer-1",
  "extra_args": ["--skip-git-repo-check"]
}
```

## Sessions, Resume, and Isolation (claude and codex)

Payloads that use none of the fields below behave exactly as before (text
mode, same command line, same envelope keys).

### Input fields (all optional)

| Field | Type | Meaning |
|-------|------|---------|
| `output_format` | `"text"` \| `"json"` | `json` runs the harness in its structured mode (`claude --print --output-format json`, `codex exec --json`) and fills `data.session_id` / `data.result_text`. Default: `json` when `resume_session_id` or `isolation` is present, otherwise `text`. |
| `resume_session_id` | string | Continue that session with `prompt` (`claude --print --resume <id>`, `codex exec resume <id> -`). Requires `isolation` (explicit keep/relax) and JSON output. Letters, digits, `.`, `_`, `:`, `-` only. |
| `isolation.tools` | `"default"` \| `"none"` | `none` removes the harness tool surface (see guarantees below). |
| `isolation.cwd` | `"given"` \| `"temp"` | `temp` creates a fresh empty directory for a **new** session and returns it as `data.cwd`; omit `cwd` in that case. |
| `timeout_seconds` | number > 0 | Kill the child process tree after this many seconds and return `CLI.TIMEOUT`. |

`cwd` stays required unless `isolation.cwd` is `"temp"`.

**Prompt delivery.** In JSON mode (claude and codex) the prompt is written to
the child's stdin (`claude --print` with no positional prompt; `codex exec ... -`),
never put on the command line, so prompts of any size work on Windows (whose
command line is limited to about 32K characters). Verified live with an 86 KB
prompt on both harnesses. Text mode keeps the prompt on the command line exactly
as before.

### Output fields added to `data`

`output_format`, `session_id`, `result_text`, `resumed_session_id`,
`isolation` (`{tools, cwd, flags}` or `null`), `timeout_seconds`, `timed_out`,
`duration_seconds`, `warnings` (non-fatal harness notices), `temp_cwd_created`
(`true` when this launch created `data.cwd` for `isolation.cwd: "temp"`). Existing keys
(`tool`, `model`, `cwd`, `teammate_mode`, `atm_team`, `atm_identity`,
`exit_code`, `stdout`, `stderr`) are unchanged; `stdout` is still the raw child
stdout (the JSON / JSONL stream in structured mode).

On failure `error` gains an optional `details` object (for example
`stderr_tail`, `exit_code`, `searched_path`, `reported_error`,
`resume_session_id`, `partial_session_id`).

### Multi-turn example

Turn 1 (no tools, empty temp directory):

```json
{
  "description": "anchor stand-in turn 1",
  "prompt": "<state + questions>. Answer with fenced JSON matching the schema.",
  "tool": "claude",
  "model": "haiku",
  "isolation": {"tools": "none", "cwd": "temp"},
  "timeout_seconds": 120
}
```

Turn 2..N (same session, same directory, isolation kept explicitly):

```json
{
  "description": "anchor stand-in follow-up",
  "prompt": "Why that answer? Which part of the plan or anchor drove it?",
  "tool": "claude",
  "model": "haiku",
  "cwd": "<data.cwd from turn 1>",
  "resume_session_id": "<data.session_id from turn 1>",
  "isolation": {"tools": "none", "cwd": "given"},
  "timeout_seconds": 120
}
```

Use `"isolation": {"tools": "default", "cwd": "given"}` on a resumed turn to
relax isolation; a resume without `isolation` is rejected so isolation never
changes implicitly.

**Temp directory ownership.** The caller owns cleanup. When
`data.temp_cwd_created` is `true`, sc-launchpad leaves `data.cwd` in place
(every resumed turn must run in it) and never deletes it; delete it yourself
after the last turn (for example `shutil.rmtree(cwd, ignore_errors=True)`). It is
also kept, and reported in `data.cwd`, when the first turn fails after the child
started (the session may exist). It is removed automatically only when the launch
fails before any child process started.

Claude stores sessions per project directory, so always resume with the
`data.cwd` the first turn reported. Codex resolves a thread id globally, but
the same rule keeps both harnesses uniform.

### Isolation guarantees

Verified on macOS with `claude` 2.1.302 and `codex-cli` 0.162.1. Flags are
listed in `data.isolation.flags`. If a future CLI rejects a flag, the launch
fails with `CLI.UNSUPPORTED_FLAG` naming the rejected flag or feature
(`error.details.rejected`, `error.details.rejected_is_isolation_flag`); nothing is
silently dropped and there is no runtime probing that could weaken isolation.

**Claude, `tools: "none"`** — adds `--tools "" --strict-mcp-config --safe-mode
--disable-slash-commands` and omits `--dangerously-skip-permissions`.

- The session has no built-in tools (stream-json `init` reports `tools: []`)
  and no MCP servers (`mcp_servers: []`), so the model cannot read files, run
  commands, or fetch URLs.
- `--safe-mode` disables CLAUDE.md, skills, installed plugins, hooks, custom
  agents, and MCP configuration (per CLI help); admin-managed policy settings
  still apply.
- Not removed: Claude Code's default system prompt, which includes environment
  facts such as the working directory, platform, and date. Use `cwd: "temp"`
  so the directory reveals nothing.

**Codex, `tools: "none"`** — adds `--skip-git-repo-check --ignore-user-config
--ignore-rules -c sandbox_mode="read-only" -c web_search="disabled"` and
`--disable` for `shell_tool unified_exec code_mode_host apps plugins
multi_agent image_generation computer_use browser_use in_app_browser view_image
goals tool_suggest skill_search`; `--yolo` is omitted.

- The remaining tool surface is `exec`, `wait`, and `request_user_input`;
  `exec` fails closed because the code-mode host is disabled (verified: a
  request to read `~/.zshrc` returned `code-mode host is disabled`). Codex
  reports this as an error item, which sc-launchpad returns in
  `data.warnings`.
- Defense in depth: the read-only sandbox blocks writes and network for any
  command that did run, but **does not block reads**. Codex has no single
  "no tools" switch, so this guarantee depends on the feature names above.
- `--ignore-user-config` skips `$CODEX_HOME/config.toml` (MCP servers, profiles,
  custom providers); authentication still uses `CODEX_HOME`. Global
  `AGENTS.md` instructions are not covered by this flag.

**Both, `cwd: "temp"`** — the child runs in a new empty directory from
`tempfile.mkdtemp(prefix="sc-launchpad-")`, outside any git repository (codex
gets `--skip-git-repo-check` whenever `isolation` is present).

**`tools: "default"`** — the harness's normal tools and the existing automation
flags (`--dangerously-skip-permissions`, `--yolo`).

**Gemini** — `output_format: "json"`, `resume_session_id`, and `isolation` return
`CAPABILITY.UNSUPPORTED`. Gemini text-mode launches (and `timeout_seconds`)
work as before.

### Error codes

| Code | When |
|------|------|
| `VALIDATION.MISSING_INPUT` / `VALIDATION.INVALID_JSON` / `VALIDATION.INVALID_PAYLOAD` / `VALIDATION.INVALID_CWD` / `VALIDATION.INVALID_MODEL` | Payload problems (unknown fields are rejected). |
| `CLI.NOT_FOUND` | The CLI (or `atm` in teammate mode) is not on PATH; `details.searched_path` lists the PATH directories. |
| `CLI.LAUNCH_FAILED` | The executable could not be started. |
| `CLI.NON_ZERO_EXIT` | The child exited non-zero for an unclassified reason. |
| `CLI.TIMEOUT` | `timeout_seconds` elapsed; the child tree was killed. `details.partial_session_id` is set when the session id had already been emitted (codex). |
| `CLI.OUTPUT_UNPARSEABLE` | Structured output was not valid JSON / JSONL. |
| `CLI.SESSION_ID_MISSING` | Structured output had no session id. |
| `CLI.RESULT_MISSING` | Structured output had no final assistant message. |
| `CLI.RESUME_SESSION_NOT_FOUND` | The harness does not know `resume_session_id`. |
| `CLI.AUTH_FAILED` | Authentication failure detected (claude `api_error_status` 401/403 or auth text in stderr / error events). |
| `CLI.REPORTED_ERROR` | Exit 0 but the harness reported an error (claude `is_error`, codex `turn.failed`). |
| `CLI.UNSUPPORTED_FLAG` | The CLI rejected a flag or feature name (version drift or bad `extra_args`); `details.rejected` names it. |
| `CAPABILITY.UNSUPPORTED` | The tool does not support a requested field (gemini). |
| `ATM.ADD_MEMBER_FAILED` | Teammate registration failed. |
| `RUNTIME.INTERRUPTED` | The runtime received SIGINT/SIGTERM/SIGHUP (or Ctrl-Break) while the child ran; the child tree was killed. |
| `RUNTIME.TEMP_CWD_FAILED` / `RUNTIME.UNEXPECTED` | Runtime problems. |

Every failure sets `success: false`, `error.code`, `error.message`,
`error.suggested_action`, and, when a child ran, `error.details.stderr_tail`
plus the usual `data` block.

## Direct Script Invocation

The agent path (skill -> `launchpad` agent -> one Bash call) is unchanged and
remains the way an LLM session should launch background agents.

A **program** (not the main LLM session) may also invoke the runtime directly
as a subprocess, for example to fan out the same prompt to several harnesses
in parallel:

```bash
python3 .claude/scripts/sc_launchpad_task.py --json '<payload JSON>'
python3 .claude/scripts/sc_launchpad_task.py --json - < payload.json   # large payloads
```

Contract:

- Input: exactly one payload object (the fields above), as the argument after
  `--json` or on stdin with `--json -` (UTF-8). Use stdin for large prompts: an
  argument is subject to the OS command-line limit (about 32K characters on
  Windows).
- Output: exactly one JSON envelope on stdout,
  `{"success": bool, "data": object|null, "error": object|null}`.
- Exit status is always `0` when the envelope was printed; branch on
  `success`, never on the exit status.
- Each invocation is one child process with its own working directory, so
  parallel invocations do not share state. The child never inherits the
  caller's stdin: it receives the prompt through a pipe (JSON mode) or an
  empty stdin (text mode).
- The child runs in its own process group. `timeout_seconds` kills the whole
  tree; terminating the runtime with SIGTERM/SIGINT (POSIX) or Ctrl-Break
  (Windows) also kills the tree and still prints an envelope
  (`RUNTIME.INTERRUPTED`). A hard kill (SIGKILL / `TerminateProcess`) of the
  runtime cannot be intercepted, so bound run time with `timeout_seconds`.
