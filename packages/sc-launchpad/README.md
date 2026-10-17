# sc-launchpad

Launch Claude, Codex, or Gemini, with model and reasoning-effort selection, as a background sub-agent runtime without
opening a visible terminal window.

## Included Artifacts

- `skills/launchpad/SKILL.md`
- `agents/launchpad.md`
- `scripts/sc_launchpad_task.py` (entry point)
- `scripts/launchpad_models.py`, `launchpad_commands.py`, `launchpad_process.py`, `launchpad_output.py`
- `scripts/launchpad_shared.py`
- `scripts/agent_models.py` (shared model table; synced from `packages/shared/scripts`)

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

`model` takes an alias or a full model id from the shared table in
`scripts/agent_models.py` (also used by sc-launch-term and sc-codex). The
default is the newest flagship of each tool.

| Tool | Aliases | Default |
|------|---------|---------|
| claude | `fable` (`claude-fable-5-1`), `opus`, `sonnet`, `haiku` | `fable` |
| codex | `sol` (`gpt-6.1-sol`), `astra` (`gpt-6-astra`), `terra` (`gpt-5.6-terra`), `luna` (`gpt-6-luna`), `codex` (the Codex default, `gpt-6.1-sol`) | `sol` |

Append `[1m]` to any claude alias or id (`fable[1m]`, `claude-opus-5-5[1m]`) for
the 1M-context variant.

`effort` sets reasoning effort: claude `low`..`max` (`--effort`), codex
`low`..`ultra` (`-c model_reasoning_effort=<level>`; `luna` models stop at
`max`). Omit it to use the CLI's default. An unknown model or an effort the
model does not support returns `VALIDATION.INVALID_MODEL` /
`VALIDATION.INVALID_EFFORT` listing the valid choices. Gemini takes any
`model` string and rejects `effort`.

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
  "model": "sol",
  "cwd": "/abs/path/to/repo",
  "atm_identity": "reviewer-1",
  "extra_args": ["--skip-git-repo-check"]
}
```

## Sessions, Resume, and Isolation (claude and codex)

The fields below are additive: payloads that use none of them still run in
text mode with the same envelope keys. Since 0.14.0 claude and codex receive
the prompt on stdin in every mode (see "Prompt delivery").

### Input fields (all optional)

| Field | Type | Meaning |
|-------|------|---------|
| `output_format` | `"text"` \| `"json"` | `json` runs the harness in its structured mode (`claude --print --output-format stream-json --verbose`, `codex exec --json`) and fills `data.session_id` / `data.result_text`. Default: `json` when `resume_session_id` or `isolation` is present, otherwise `text`. |
| `resume_session_id` | string | Continue that session with `prompt` (`claude --print --resume <id>`, `codex exec resume <id> -`). Requires `isolation` (explicit keep/relax) and JSON output. Letters, digits, `.`, `_`, `:`, `-` only. |
| `isolation.tools` | `"default"` \| `"none"` | `none` removes the harness tool surface (see guarantees below). |
| `isolation.cwd` | `"given"` \| `"temp"` | `temp` creates a fresh empty directory for a **new** session and returns it as `data.cwd`; omit `cwd` in that case. |
| `timeout_seconds` | number > 0 | Kill the child process tree after this many seconds and return `CLI.TIMEOUT`. |
| `ephemeral` | bool | Do not persist the session (`claude --no-session-persistence`, `codex exec --ephemeral`); it cannot be resumed. |

`cwd` is required unless `isolation.cwd` is `"temp"`, and must be omitted then.
`isolation.tools: "none"` rejects `extra_args` and `atm_identity`.

**Prompt delivery.** claude and codex always get the prompt on stdin
(`claude --print` with no positional prompt; `codex exec ... -`), never on the
command line, so prompts of any size work on Windows (whose command line is
limited to about 32K characters) and nothing passes through a `.cmd` shim's
argument parsing. Gemini has no stdin mode and keeps `--prompt <text>`.

**Windows `.cmd` shims.** cmd.exe re-parses the arguments of a `.cmd`/`.bat`
file and Python cannot escape them safely. When the resolved CLI is such a shim,
any argument containing `" % ! ^ & | < >` or a newline (from `model`,
`extra_args`, or a gemini prompt) fails as `CLI.UNSAFE_ARGUMENT` before launch.
sc-launchpad's own flags never contain these characters.

### Output fields added to `data`

`output_format`, `session_id`, `result_text`, `resumed_session_id`,
`isolation` (`{tools, cwd, flags}` or `null`), `timeout_seconds`, `timed_out`,
`duration_seconds`, `warnings` (non-fatal harness notices), `ephemeral`, and
`cleanup_paths` (see below). Existing keys (`tool`, `model`, `cwd`,
`teammate_mode`, `atm_team`, `atm_identity`, `exit_code`, `stdout`, `stderr`)
keep their meaning in text mode. In JSON mode `stdout` is `null` (the answer is
`result_text`) and `stderr` is its last 4000 characters; a failure carries
`error.details.stdout_tail` / `stderr_tail`.

On failure `error` gains an optional `details` object (for example
`stderr_tail`, `exit_code`, `searched_path`, `reported_error`,
`resume_session_id`, `stdout_tail`, `session_id`). On a timeout `data.session_id`
holds the session id if the harness had already emitted it.

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

**Cleanup ownership.** The caller owns cleanup. `data.cleanup_paths` lists
everything the session leaves behind: the temp `data.cwd`, the private
`CODEX_HOME` of an isolated codex session, and claude's transcript directory
for a temp cwd (`~/.claude/projects/<encoded cwd>`, honoring
`CLAUDE_CONFIG_DIR`). sc-launchpad keeps them because every resumed turn needs
them; after the last turn delete each one (for example
`shutil.rmtree(path, ignore_errors=True)`). When a launch fails after the child
started, the paths are in `error.details.cleanup_paths`. A temp cwd is removed
automatically only when the launch fails before any child process started.

Claude stores sessions per project directory, so always resume with the
`data.cwd` the first turn reported. Codex resolves a thread id globally, but
the same rule keeps both harnesses uniform.

### Isolation guarantees

Flags verified on macOS with `claude` 2.1.302 and `codex-cli` 0.162.1. Flags are
listed in `data.isolation.flags`. If a future CLI rejects a flag, the launch
fails with `CLI.UNSUPPORTED_FLAG` naming the rejected flag or feature
(`error.details.rejected`, `error.details.rejected_is_isolation_flag`); nothing is
silently dropped and there is no runtime probing that could weaken isolation.

**Verified per turn.** With `tools: "none"` sc-launchpad does not trust the
flags alone. It inspects the harness output and fails closed with
`ISOLATION.VIOLATED` (no `result_text`, `recoverable: false`, evidence in
`error.details.tool_activity`) when claude's `init` event lists any tool or MCP
server, when claude did not report a tool-less `init` at all, when any
`tool_use` block appears, or when codex emits any item other than
`agent_message`, `reasoning`, `error`, or `todo_list`.

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
--ignore-rules -c sandbox_mode=read-only -c web_search=disabled` and
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
- `--ignore-user-config` skips `config.toml` (MCP servers, profiles, custom
  providers). It does not cover the global `AGENTS.md`, so sc-launchpad also
  points `CODEX_HOME` at a private directory
  (`$TMPDIR/sc-launchpad-codex-home-<hash of cwd>`, mode 0700) that contains
  only a link to your `auth.json`. Global instructions, config, and session
  history never reach the child (verified: a global `AGENTS.md` instruction is
  followed without it and ignored with it). The directory is keyed by cwd so
  resumed turns find the thread; it is listed in `data.cleanup_paths`.

**Both, `cwd: "temp"`** — the child runs in a new empty directory from
`tempfile.mkdtemp(prefix="sc-launchpad-")`, outside any git repository (codex
gets `--skip-git-repo-check` whenever `isolation` is present).

**`extra_args`** are rejected with `tools: "none"`: any flag that touches tools,
permissions, sandbox, MCP, or config could override isolation. With
`tools: "default"` they are appended unfiltered after the isolation flags.

**`tools: "default"`** — the harness's normal tools and the existing automation
flags (`--dangerously-skip-permissions`, `--yolo`).

**Gemini** — `output_format: "json"`, `resume_session_id`, `isolation`, and `ephemeral` return
`CAPABILITY.UNSUPPORTED`. Gemini text-mode launches (and `timeout_seconds`)
work as before.

### Error codes

| Code | When |
|------|------|
| `VALIDATION.MISSING_INPUT` / `VALIDATION.INVALID_JSON` / `VALIDATION.INVALID_PAYLOAD` / `VALIDATION.INVALID_CWD` / `VALIDATION.INVALID_MODEL` / `VALIDATION.INVALID_EFFORT` | Payload problems (unknown fields are rejected). |
| `CLI.NOT_FOUND` | The CLI (or `atm` in teammate mode) is not on PATH; `details.searched_path` lists the PATH directories. |
| `CLI.LAUNCH_FAILED` | The executable could not be started. |
| `CLI.NON_ZERO_EXIT` | The child exited non-zero for an unclassified reason. |
| `CLI.TIMEOUT` | `timeout_seconds` elapsed; the child tree was killed. `data.session_id` is set when the session id had already been emitted. |
| `CLI.OUTPUT_UNPARSEABLE` | Structured output was not valid JSON / JSONL. |
| `CLI.SESSION_ID_MISSING` | Structured output had no session id. |
| `CLI.RESULT_MISSING` | Structured output had no final assistant message. |
| `CLI.RESUME_SESSION_NOT_FOUND` | The harness does not know `resume_session_id`. |
| `CLI.AUTH_FAILED` | Authentication failure detected (claude `api_error_status` 401/403 or auth text in stderr / error events). |
| `CLI.REPORTED_ERROR` | Exit 0 but the harness reported an error (claude `is_error`, codex `turn.failed`). |
| `CLI.UNSUPPORTED_FLAG` | The CLI rejected a flag or feature name (version drift or bad `extra_args`); `details.rejected` names it. |
| `CLI.UNSAFE_ARGUMENT` | The CLI resolves to a Windows `.cmd`/`.bat` shim and an argument contains cmd.exe metacharacters. |
| `ISOLATION.VIOLATED` | `tools: "none"` but the harness output shows tools were available or used; the answer is withheld. |
| `CAPABILITY.UNSUPPORTED` | The tool does not support a requested field (gemini). |
| `ATM.ADD_MEMBER_FAILED` | Teammate registration failed. |
| `RUNTIME.INTERRUPTED` | The runtime received SIGINT/SIGTERM/SIGHUP (or Ctrl-Break) while the child ran; the child tree was killed. |
| `RUNTIME.TEMP_CWD_FAILED` / `RUNTIME.CODEX_HOME_FAILED` / `RUNTIME.UNEXPECTED` | Runtime problems. |

Every failure sets `success: false`, `error.code`, `error.message`,
`error.suggested_action`, and, when a child ran, `error.details.stderr_tail`
plus the usual `data` block.

## Direct Script Invocation

The agent path (skill -> `launchpad` agent -> one Bash call) remains the way an
LLM session should launch background agents.

A **program** (not the main LLM session) may also invoke the runtime directly
as a subprocess, for example to fan out the same prompt to several harnesses
in parallel:

```bash
python3 .claude/scripts/sc_launchpad_task.py --json '<payload JSON>'
python3 .claude/scripts/sc_launchpad_task.py --json - < payload.json   # large payloads
```

With a plugin install the script is `$CLAUDE_PLUGIN_ROOT/scripts/sc_launchpad_task.py`.

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
  caller's stdin: claude and codex receive the prompt through a pipe, gemini
  an empty stdin.
- The child runs in its own process group. `timeout_seconds` kills the whole
  tree; terminating the runtime with SIGTERM/SIGINT (POSIX) or Ctrl-Break
  (Windows) also kills the tree and still prints an envelope
  (`RUNTIME.INTERRUPTED`). A hard kill (SIGKILL / `TerminateProcess`) of the
  runtime cannot be intercepted, so bound run time with `timeout_seconds`.

## Storage

Each launch appends one line to
`<CLAUDE_PROJECT_DIR or cwd>/.claude/state/logs/sc-launchpad/launch.jsonl`:
`timestamp`, `event` (`launch`), `package`, `level`, `tool`, `model`, `effort`,
`output_format`, `isolation`, `ephemeral`, `session_id`, `resumed_session_id`,
`exit_code`, `error_code`, `duration_seconds`. The prompt, the answer, and the
environment are never logged. A log write failure never fails the launch.
