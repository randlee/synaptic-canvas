---
description: Launch Codex CLI in a supported terminal at a specified directory
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>]"
allowed-tools: Bash, AskUserQuestion
---

Launch Codex CLI in a supported terminal.

## Arguments

Parse from `$ARGUMENTS`:
- `dir` optional positional target directory. Default: `$PWD`.
- `--terminal <name>` optional explicit backend. Default: `auto`.
- `--tab` optional request for a new tab instead of a new window when supported.
- `--tmux` optional tmux session flow using the session name `"{folder} - codex"`.
- `--identity <name>` required when `ATM_TEAM` is set in the current environment. Exports both `ATM_TEAM` and `ATM_IDENTITY=<name>` into the launched session.

Supported backends:
- macOS: `iterm2`, `ghostty`, `wezterm`, `warp`, `terminal`
- Windows: `wt`, `warp`

Backend notes:
- Warp opens a new window only; reject `--tab` if `warp` is selected.
- `--tmux` requires `tmux` on `PATH`. On Windows, only use it if your shell already supports `tmux`.
- If `ATM_TEAM` is set and `--identity` is supplied, the launcher registers the member first with `atm teams add-member <team> <identity> --model codex --cwd <dir>`.

The launched command is:

```text
codex --yolo -c features.codex_hooks=true
```

## Steps

**Step 0** — If `$ARGUMENTS` contains `--help`, print the following and stop:

```
Usage: /sc:codex [dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>]

Launch Codex CLI in a supported terminal.

Examples:
  /sc:codex
  /sc:codex ~/projects/foo
  /sc:codex ~/projects/foo --terminal wt
  /sc:codex ~/projects/foo --tab
  /sc:codex ~/projects/foo --tmux
  /sc:codex ~/projects/foo --identity alice
```

**Step 1** — Parse `$ARGUMENTS`. Extract `dir`, `--terminal`, `--tab`, `--tmux`, and `--identity`.

**Step 2** — Resolve `dir` to an absolute path.

**Step 3** — If `warp` is selected with `--tab`, stop and explain that scripted Warp launches open a new window only.

**Step 4** — Build `TERM_ARG`: `--terminal <name>` if supplied, otherwise omit.

**Step 5** — Build `IDENTITY_ARG`: `--identity <name>` if supplied, otherwise omit. If `ATM_TEAM` is set in the current environment and no identity was provided, stop and tell the user that `--identity` is required.

### Without `--tmux`

Run and stop:

```bash
python3 .claude/scripts/sc-term-launch.py launch "codex --yolo -c features.codex_hooks=true" "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model codex
```

### With `--tmux`

**Step 6** — Build `SESSION_NAME = "{basename(dir)} - codex"`.

**Step 7** — Check whether tmux session naming is available:

```bash
python3 .claude/scripts/sc-term-launch.py check-session "<SESSION_NAME>"
```

Parse JSON: `{"available": bool, "exists": bool, "next_name": str}`.

If `available` is false, stop and tell the user that local tmux support is unavailable.

If `exists` is false, run and stop:

```bash
python3 .claude/scripts/sc-term-launch.py launch "codex --yolo -c features.codex_hooks=true" "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model codex --tmux "<SESSION_NAME>"
```

If `exists` is true, use `AskUserQuestion` exactly once with:
- `Connect to existing session (no Codex)`
- `Connect to existing session + Codex in new pane`
- `New session: <next_name>`
- `Enter custom session name`

Handle responses:

**Connect (no Codex)**:
```bash
python3 .claude/scripts/sc-term-launch.py attach "<SESSION_NAME>" <TERM_ARG> <TAB_ARG>
```

**Connect + Codex pane**:
```bash
python3 .claude/scripts/sc-term-launch.py attach-pane "<SESSION_NAME>" "codex --yolo -c features.codex_hooks=true" --cwd "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model codex
```

**New session (`next_name`)**:
```bash
python3 .claude/scripts/sc-term-launch.py launch "codex --yolo -c features.codex_hooks=true" "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model codex --tmux "<next_name>"
```

**Enter custom name** — ask for the session name in a follow-up message, then:
```bash
python3 .claude/scripts/sc-term-launch.py launch "codex --yolo -c features.codex_hooks=true" "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model codex --tmux "<custom_name>"
```
