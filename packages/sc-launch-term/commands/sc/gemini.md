---
description: Launch Gemini CLI in a supported terminal at a specified directory
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>]"
allowed-tools: Bash, AskUserQuestion
---

Launch Gemini CLI in a supported terminal.

## Arguments

Parse from `$ARGUMENTS`:
- `dir` optional positional target directory. Default: `$PWD`.
- `--terminal <name>` optional explicit backend. Default: `auto`.
- `--tab` optional request for a new tab instead of a new window when supported.
- `--tmux` optional tmux session flow using the session name `"{folder} - gemini"`.
- `--identity <name>` required when `ATM_TEAM` is set in the current environment. Exports both `ATM_TEAM` and `ATM_IDENTITY=<name>` into the launched session.

Supported backends:
- macOS: `iterm2`, `ghostty`, `wezterm`, `warp`, `terminal`
- Windows: `wt`, `warp`

Backend notes:
- Warp opens a new window only; reject `--tab` if `warp` is selected.
- `--tmux` requires `tmux` on `PATH`. On Windows, only use it if your shell already supports `tmux`.
- If `ATM_TEAM` is set and `--identity` is supplied, the launcher registers the member first with `atm teams add-member <team> <identity> --model gemini --cwd <dir>`.

The launched command is:

```text
gemini --yolo
```

## Steps

**Step 0** — If `$ARGUMENTS` contains `--help`, print the following and stop:

```
Usage: /sc:gemini [dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>]

Launch Gemini CLI in a supported terminal.

Examples:
  /sc:gemini
  /sc:gemini ~/projects/foo
  /sc:gemini ~/projects/foo --terminal warp
  /sc:gemini ~/projects/foo --tab
  /sc:gemini ~/projects/foo --tmux
  /sc:gemini ~/projects/foo --identity alice
```

**Step 1** — Parse `$ARGUMENTS`. Extract `dir`, `--terminal`, `--tab`, `--tmux`, and `--identity`.

**Step 2** — Resolve `dir` to an absolute path.

**Step 3** — If `warp` is selected with `--tab`, stop and explain that scripted Warp launches open a new window only.

**Step 4** — Build `TERM_ARG`: `--terminal <name>` if supplied, otherwise omit.

**Step 5** — Build `IDENTITY_ARG`: `--identity <name>` if supplied, otherwise omit. If `ATM_TEAM` is set in the current environment and no identity was provided, stop and tell the user that `--identity` is required.

### Without `--tmux`

Run and stop:

```bash
.claude/scripts/sc-term-launch.sh launch "gemini --yolo" "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model gemini
```

### With `--tmux`

**Step 6** — Build `SESSION_NAME = "{basename(dir)} - gemini"`.

**Step 7** — Check whether tmux session naming is available:

```bash
.claude/scripts/sc-term-launch.sh check-session "<SESSION_NAME>"
```

Parse JSON: `{"available": bool, "exists": bool, "next_name": str}`.

If `available` is false, stop and tell the user that local tmux support is unavailable.

If `exists` is false, run and stop:

```bash
.claude/scripts/sc-term-launch.sh launch "gemini --yolo" "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model gemini --tmux "<SESSION_NAME>"
```

If `exists` is true, use `AskUserQuestion` exactly once with:
- `Connect to existing session (no Gemini)`
- `Connect to existing session + Gemini in new pane`
- `New session: <next_name>`
- `Enter custom session name`

Handle responses:

**Connect (no Gemini)**:
```bash
.claude/scripts/sc-term-launch.sh attach "<SESSION_NAME>" <TERM_ARG> <TAB_ARG>
```

**Connect + Gemini pane**:
```bash
.claude/scripts/sc-term-launch.sh attach-pane "<SESSION_NAME>" "gemini --yolo" --cwd "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model gemini
```

**New session (`next_name`)**:
```bash
.claude/scripts/sc-term-launch.sh launch "gemini --yolo" "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model gemini --tmux "<next_name>"
```

**Enter custom name** — ask for the session name in a follow-up message, then:
```bash
.claude/scripts/sc-term-launch.sh launch "gemini --yolo" "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> --member-model gemini --tmux "<custom_name>"
```
