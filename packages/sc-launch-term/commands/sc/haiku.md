---
description: Launch Claude Code (haiku) in a supported terminal at a specified directory
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [--effort <level>] [-- <claude args...>]"
allowed-tools: Bash, AskUserQuestion
---

Launch Claude Code with `claude --model claude-haiku-5-5 --dangerously-skip-permissions` in a supported terminal.

## Arguments

Parse from `$ARGUMENTS`:
- `dir` optional positional target directory. Default: `$PWD`.
- `--terminal <name>` optional explicit backend. Default: `auto`.
- `--tab` optional request for a new tab instead of a new window when supported.
- `--tmux` optional tmux session flow using the session name `"{folder} - haiku"`.
- `--identity <name>` optional; only meaningful when `ATM_TEAM` is set. With `ATM_TEAM` set, the launcher exports `ATM_TEAM` and `ATM_IDENTITY=<name>` into the launched session, generating a name from the haiku identity pool when omitted. Without `ATM_TEAM`, no `ATM_IDENTITY` is generated, registered or exported, an inherited `ATM_IDENTITY` is cleared in the launched session (`ATM_TEAM` is left alone), and a supplied `--identity` is ignored with a warning.
- `--effort <level>` optional reasoning effort: `low`, `medium`, `high`, `xhigh`, or `max` (passed as `--effort <level>`). Default: Claude's own.
- `-- <claude args...>` optional passthrough Claude CLI arguments. Everything after `--` is forwarded to `claude`.

Supported backends:
- macOS: `iterm2`, `ghostty`, `wezterm`, `warp`, `cmux`, `terminal`
- Windows: `wt`, `warp`

Backend notes:
- Warp opens a new window only; reject `--tab` if `warp` is selected.
- cmux creates and focuses a new workspace, which is cmux's tab primitive.
- `--tmux` requires `tmux` on `PATH`. On Windows, only use it if your shell already supports `tmux`.
- When `--tmux` is used, the launcher also adds `--teammate-mode tmux` to match the current local `haiku` wrapper behavior.
- If `ATM_TEAM` is set, the launcher registers the member (supplied or generated identity) first with `atm teams add-member <team> <identity> --model haiku --cwd <dir>`. Without `ATM_TEAM` there is no registration.

## Steps

**Step 0** — If `$ARGUMENTS` contains `--help`, print the following and stop:

```
Usage: /sc:haiku [dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [--effort <level>] [-- <claude args...>]

Launch Claude Code (haiku) in a supported terminal.

Examples:
  /sc:haiku
  /sc:haiku ~/projects/foo
  /sc:haiku ~/projects/foo --terminal wezterm
  /sc:haiku ~/projects/foo --tab
  /sc:haiku ~/projects/foo --tmux
  /sc:haiku ~/projects/foo --identity alice
  /sc:haiku ~/projects/foo -- --continue
  /sc:haiku ~/projects/foo --terminal ghostty -- --continue --resume <session-id>
```

**Step 1** — Parse `$ARGUMENTS`. Extract `dir`, `--terminal`, `--tab`, `--tmux`, `--identity`, and `--effort`. If `--` is present, collect everything after it into `CLAUDE_ARG_TAIL`; otherwise `CLAUDE_ARG_TAIL` is empty.

**Step 2** — Resolve `dir` to an absolute path.

**Step 3** — If `warp` is selected with `--tab`, stop and explain that scripted Warp launches open a new window only.

**Step 4** — Build `TERM_ARG`: `--terminal <name>` if supplied, otherwise omit. Build `EFFORT_ARG`: `--effort <level>` if supplied, otherwise omit.

**Step 5** — Build `IDENTITY_ARG`: `--identity <name>` if supplied, otherwise omit. Do not invent a name; the launcher generates one from the model's pool only when `ATM_TEAM` is set.

### Without `--tmux`

Run and stop:

```bash
.claude/scripts/sc-term-launch.sh launch-claude-model haiku "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <EFFORT_ARG> <CLAUDE_ARG_TAIL>
```

### With `--tmux`

**Step 6** — Build `SESSION_NAME = "{basename(dir)} - haiku"`.

**Step 7** — Check whether tmux session naming is available:

```bash
.claude/scripts/sc-term-launch.sh check-session "<SESSION_NAME>"
```

Parse JSON: `{"available": bool, "exists": bool, "next_name": str}`.

If `available` is false, stop and tell the user that local tmux support is unavailable.

If `exists` is false, run and stop:

```bash
.claude/scripts/sc-term-launch.sh launch-claude-model haiku "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <EFFORT_ARG> --tmux "<SESSION_NAME>" <CLAUDE_ARG_TAIL>
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
.claude/scripts/sc-term-launch.sh attach-pane-claude-model "<SESSION_NAME>" haiku --cwd "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <EFFORT_ARG> <CLAUDE_ARG_TAIL>
```

**New session (`next_name`)**:
```bash
.claude/scripts/sc-term-launch.sh launch-claude-model haiku "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <EFFORT_ARG> --tmux "<next_name>" <CLAUDE_ARG_TAIL>
```

**Enter custom name** — ask for the session name in a follow-up message, then:
```bash
.claude/scripts/sc-term-launch.sh launch-claude-model haiku "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <EFFORT_ARG> --tmux "<custom_name>" <CLAUDE_ARG_TAIL>
```
