---
description: Launch Claude Code (opus) in a supported terminal at a specified directory
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [-- <claude args...>]"
allowed-tools: Bash, AskUserQuestion
---

Launch Claude Code with `claude --model opus --dangerously-skip-permissions` in a supported terminal.

## Arguments

Parse from `$ARGUMENTS`:
- `dir` optional positional target directory. Default: `$PWD`.
- `--terminal <name>` optional explicit backend. Default: `auto`.
- `--tab` optional request for a new tab instead of a new window when supported.
- `--tmux` optional tmux session flow using the session name `"{folder} - opus"`.
- `--identity <name>` required when `ATM_TEAM` is set in the current environment. Exports both `ATM_TEAM` and `ATM_IDENTITY=<name>` into the launched session.
- `-- <claude args...>` optional passthrough Claude CLI arguments. Everything after `--` is forwarded to `claude`.

Supported backends:
- macOS: `iterm2`, `ghostty`, `wezterm`, `warp`, `terminal`
- Windows: `wt`, `warp`

Backend notes:
- Warp opens a new window only; reject `--tab` if `warp` is selected.
- `--tmux` requires `tmux` on `PATH`. On Windows, only use it if your shell already supports `tmux`.
- When `--tmux` is used, the launcher also adds `--teammate-mode tmux` to match the current local `opus` wrapper behavior.
- If `ATM_TEAM` is set and `--identity` is supplied, the launcher registers the member first with `atm teams add-member <team> <identity> --model opus --cwd <dir>`.

## Steps

**Step 0** — If `$ARGUMENTS` contains `--help`, print the following and stop:

```
Usage: /sc:opus [dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [-- <claude args...>]

Launch Claude Code (opus) in a supported terminal.

Examples:
  /sc:opus
  /sc:opus ~/projects/foo
  /sc:opus ~/projects/foo --terminal iterm2
  /sc:opus ~/projects/foo --tab
  /sc:opus ~/projects/foo --tmux
  /sc:opus ~/projects/foo --identity alice
  /sc:opus ~/projects/foo -- --continue
  /sc:opus ~/projects/foo --terminal warp -- --continue --resume <session-id>
```

**Step 1** — Parse `$ARGUMENTS`. Extract `dir`, `--terminal`, `--tab`, `--tmux`, and `--identity`. If `--` is present, collect everything after it into `CLAUDE_ARG_TAIL`; otherwise `CLAUDE_ARG_TAIL` is empty.

**Step 2** — Resolve `dir` to an absolute path.

**Step 3** — If `warp` is selected with `--tab`, stop and explain that scripted Warp launches open a new window only.

**Step 4** — Build `TERM_ARG`: `--terminal <name>` if supplied, otherwise omit.

**Step 5** — Build `IDENTITY_ARG`: `--identity <name>` if supplied, otherwise omit. If `ATM_TEAM` is set in the current environment and no identity was provided, stop and tell the user that `--identity` is required.

### Without `--tmux`

Run and stop:

```bash
.claude/scripts/sc-term-launch.sh launch-claude-model opus "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <CLAUDE_ARG_TAIL>
```

### With `--tmux`

**Step 6** — Build `SESSION_NAME = "{basename(dir)} - opus"`.

**Step 7** — Check whether tmux session naming is available:

```bash
.claude/scripts/sc-term-launch.sh check-session "<SESSION_NAME>"
```

Parse JSON: `{"available": bool, "exists": bool, "next_name": str}`.

If `available` is false, stop and tell the user that local tmux support is unavailable.

If `exists` is false, run and stop:

```bash
.claude/scripts/sc-term-launch.sh launch-claude-model opus "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --tmux "<SESSION_NAME>" <CLAUDE_ARG_TAIL>
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
.claude/scripts/sc-term-launch.sh attach-pane-claude-model "<SESSION_NAME>" opus --cwd "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <CLAUDE_ARG_TAIL>
```

**New session (`next_name`)**:
```bash
.claude/scripts/sc-term-launch.sh launch-claude-model opus "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --tmux "<next_name>" <CLAUDE_ARG_TAIL>
```

**Enter custom name** — ask for the session name in a follow-up message, then:
```bash
.claude/scripts/sc-term-launch.sh launch-claude-model opus "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --tmux "<custom_name>" <CLAUDE_ARG_TAIL>
```
