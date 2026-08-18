---
description: Launch Claude Code (fable) in a supported terminal at a specified directory
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [-- <claude args...>]"
allowed-tools: Bash, AskUserQuestion
---

Launch Claude Code with `claude --model fable --dangerously-skip-permissions` in a supported terminal.

## Arguments

Parse from `$ARGUMENTS`:
- `dir` optional positional target directory. Default: `$PWD`.
- `--terminal <name>` optional explicit backend. Default: `auto`.
- `--tab` optional request for a new tab when the backend supports it.
- `--tmux` optional tmux session flow using the session name `"{folder} - fable"`.
- `--identity <name>` optional. If omitted, a random name is generated. Exports both `ATM_TEAM` and `ATM_IDENTITY=<name>` into the launched session.
- `-- <claude args...>` optional passthrough Claude CLI arguments. Everything after `--` is forwarded to `claude`.

Supported backends:
- macOS: `iterm2`, `ghostty`, `wezterm`, `warp`, `cmux`, `terminal`
- Windows: `wt`, `warp`

Backend notes:
- Warp opens a new window only; reject `--tab` if `warp` is selected.
- cmux creates and focuses a new cmux workspace, which is cmux's tab primitive.
- `--tmux` requires `tmux` on `PATH`. On Windows, only use it if your shell already supports `tmux`.
- When `--tmux` is used, the launcher also adds `--teammate-mode tmux` to match the local Claude wrapper behavior.
- If `ATM_TEAM` is set and `--identity` is supplied, the launcher registers the member first with `atm teams add-member <team> <identity> --model fable --cwd <dir>`.

The launched command is:

```text
claude --model fable --dangerously-skip-permissions
```

## Steps

**Step 0** — If `$ARGUMENTS` contains `--help`, print the following and stop:

```
Usage: /sc:fable [dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [-- <claude args...>]

Launch Claude Code (fable) in a supported terminal.

Examples:
  /sc:fable
  /sc:fable ~/projects/foo
  /sc:fable ~/projects/foo --terminal cmux --tab
  /sc:fable ~/projects/foo --tab
  /sc:fable ~/projects/foo --tmux
  /sc:fable ~/projects/foo --identity alice
  /sc:fable ~/projects/foo -- --continue
```

**Step 1** — Parse `$ARGUMENTS`. Extract `dir`, `--terminal`, `--tab`, and `--tmux`. If `--` is present, collect everything after it into `CLAUDE_ARG_TAIL`; otherwise `CLAUDE_ARG_TAIL` is empty. Extract `--identity` when supplied.

**Step 2** — Resolve `dir` to an absolute path.

**Step 3** — If `warp` is selected with `--tab`, stop and explain that scripted Warp launches open a new window only.

**Step 4** — Build `TERM_ARG`: `--terminal <name>` if supplied, otherwise omit.

**Step 5** — Resolve identity: use `--identity <name>` if supplied, otherwise generate a random name. Build `IDENTITY_ARG` from the resolved value.

### Without `--tmux`

Run and stop:

```bash
.claude/scripts/sc-term-launch.sh launch-claude-model fable "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <CLAUDE_ARG_TAIL>
```

### With `--tmux`

**Step 6** — Build `SESSION_NAME = "{basename(dir)} - fable"`.

**Step 7** — Check whether tmux session naming is available:

```bash
.claude/scripts/sc-term-launch.sh check-session "<SESSION_NAME>"
```

Parse JSON: `{"available": bool, "exists": bool, "next_name": str}`.

If `available` is false, stop and tell the user that local tmux support is unavailable.

If `exists` is false, run and stop:

```bash
.claude/scripts/sc-term-launch.sh launch-claude-model fable "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --tmux "<SESSION_NAME>" <CLAUDE_ARG_TAIL>
```

If `exists` is true, use `AskUserQuestion` exactly once with:
- `Connect to existing session (no Claude)`
- `Connect to existing session + Claude in new pane`
- `New session: <next_name>`
- `Enter custom session name`

Handle responses:

**Connect (no Claude)**:
```bash
.claude/scripts/sc-term-launch.sh attach "<SESSION_NAME>" <TERM_ARG> <TAB_ARG>
```

**Connect + Claude pane**:
```bash
.claude/scripts/sc-term-launch.sh attach-pane-claude-model "<SESSION_NAME>" fable --cwd "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <CLAUDE_ARG_TAIL>
```

**New session (`next_name`)**:
```bash
.claude/scripts/sc-term-launch.sh launch-claude-model fable "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --tmux "<next_name>" <CLAUDE_ARG_TAIL>
```

**Enter custom name** — ask for the session name in a follow-up message, then:
```bash
.claude/scripts/sc-term-launch.sh launch-claude-model fable "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --tmux "<custom_name>" <CLAUDE_ARG_TAIL>
```
