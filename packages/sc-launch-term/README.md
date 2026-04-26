# sc-launch-term

Launch Claude, Codex, and Gemini sessions in supported terminals with a shared
autodetect launcher.

## Commands

- `/sc:sonnet`
- `/sc:haiku`
- `/sc:opus`
- `/sc:codex`
- `/sc:gemini`

Each command accepts:

- `dir` optional target directory, defaulting to the current working directory
- `--terminal <name>` to force a specific terminal backend
- `--tab` to request a new tab when the backend supports it
- `--tmux` to create or attach to a named tmux session
- `--identity <name>` required when `ATM_TEAM` is set; exports both `ATM_TEAM` and `ATM_IDENTITY`
- `-- <args...>` to forward extra CLI args to the launched tool

## Terminal Backends

Autodetect order:

- macOS: `iterm2`, `ghostty`, `wezterm`, `warp`, `terminal`
- Windows: `wt`, `warp`

Supported explicit values:

- macOS: `auto`, `iterm2`, `ghostty`, `wezterm`, `warp`, `terminal`
- Windows: `auto`, `wt`, `windows-terminal`, `warp`

Notes:

- Warp automation uses Warp launch configurations and opens a new window.
- `/sc:sonnet`, `/sc:haiku`, and `/sc:opus` launch `claude` directly with
  `--model <name> --dangerously-skip-permissions`, so they no longer depend on
  shell aliases or functions.
- When `--tmux` is used with those Claude model commands, the launcher also
  adds `--teammate-mode tmux` to match the current local wrappers.
- If `ATM_TEAM` is set in the current environment, every launch requires
  `--identity <name>` and exports both `ATM_TEAM` and `ATM_IDENTITY=<name>`
  into the launched session.
- When `ATM_TEAM` is set, the launcher also runs
  `atm teams add-member <team> <identity> --model <model> --cwd <dir>` before
  starting the AI tool. Pane-specific `--pane-id` wiring is intentionally left
  as a future follow-up.
- `--tmux` requires `tmux` to be installed and available on `PATH`.

## Installation

```bash
/marketplace install sc-launch-term
```

This package is intended for global command installation under `~/.claude/`.

## Examples

```bash
/sc:sonnet ~/projects/foo
/sc:haiku ~/projects/foo --terminal ghostty
/sc:opus ~/projects/foo --tab
/sc:codex ~/projects/foo --identity alice
/sc:sonnet ~/projects/foo -- --continue
/sc:codex ~/projects/foo --tmux
/sc:gemini ~/projects/foo --terminal wt
```
