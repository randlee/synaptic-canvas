# sc-launch-term

Launch Claude, Codex, and Gemini sessions in supported terminals with a shared
autodetect launcher. Codex exposes Sol, Astra, Terra, and Luna model aliases through
one shared model-launch implementation. Models and reasoning-effort levels come
from the shared table `scripts/agent_models.py` (also used by sc-launchpad and sc-codex).
Generated ATM identities come from the shared name pools in `scripts/agent_identity.py`
(also used by sc-launchpad).

## Commands

- `/sc:sonnet`
- `/sc:haiku`
- `/sc:opus`
- `/sc:fable`
- `/sc:sol`
- `/sc:astra`
- `/sc:terra`
- `/sc:luna`
- `/sc:codex`
- `/sc:gemini`

Each command accepts:

- `dir` optional target directory, defaulting to the current working directory
- `--terminal <name>` to force a specific terminal backend
- `--tab` to request a new tab when the backend supports it
- `--tmux` to create or attach to a named tmux session
- `--identity <name>` optional; only used when `ATM_TEAM` is set. With a team, an omitted identity is generated from the model-specific pool and `ATM_TEAM`, `ATM_IDENTITY` and `BEADS_ACTOR` (equal to the identity) are exported. Without a team it is ignored with a warning
- `--effort <level>` optional reasoning effort (Claude and Codex commands): claude `low`..`max`, codex `low`..`ultra` (`luna` stops at `max`); omitted means the CLI's default
- `-- <args...>` to forward extra CLI args to the launched tool

## Terminal Backends

Autodetect order:

- macOS: `iterm2`, `ghostty`, `wezterm`, `warp`, `cmux`, `terminal`
- Windows: `wt`, `warp`

Supported explicit values:

- macOS: `auto`, `iterm2`, `ghostty`, `wezterm`, `warp`, `cmux`, `terminal`
- Windows: `auto`, `wt`, `windows-terminal`, `warp`

Notes:

- Warp automation uses Warp launch configurations and opens a new window.
- cmux automation creates and focuses a new cmux workspace, which is cmux's tab primitive.
- `/sc:sonnet`, `/sc:haiku`, `/sc:opus`, and `/sc:fable` launch `claude` directly with
  `--model <full id> --dangerously-skip-permissions` (for example
  `claude-fable-5-1`), so they no longer depend on shell aliases or functions.
- `/sc:sol`, `/sc:astra`, `/sc:terra`, and `/sc:luna` launch Codex with
  `--model gpt-6.1-sol`, `gpt-6-astra`, `gpt-5.6-terra`, and `gpt-6-luna`
  respectively, using the shared Codex launcher and model-specific identity pools.
- `/sc:codex` launches the Codex default model (currently `sol`).
- `--effort` becomes `--effort <level>` for claude and
  `-c model_reasoning_effort=<level>` for codex.
- When `--tmux` is used with Claude model commands, the launcher also
  adds `--teammate-mode tmux` to match the current local wrappers.
- If `ATM_TEAM` is set in the current environment, every launch exports
  `ATM_TEAM`, an explicit or generated `ATM_IDENTITY=<name>` and
  `BEADS_ACTOR=<name>` (the same name) into the launched session.
  `BEADS_ACTOR` is the actor `bd` (beads) records in audit-trail entries and
  slot holders, so it always tracks the child's `ATM_IDENTITY`.
- If `ATM_TEAM` is not set, the launcher does not generate, register or export
  an `ATM_IDENTITY` or `BEADS_ACTOR`. An inherited `ATM_IDENTITY` and
  `BEADS_ACTOR` (the parent session's) are cleared in the launched session
  (`unset ATM_IDENTITY BEADS_ACTOR` in POSIX shells,
  `Remove-Item Env:ATM_IDENTITY,Env:BEADS_ACTOR` in PowerShell) and in the
  launcher's own environment, so no backend (tmux, WezTerm, Windows Terminal,
  cmux, ...) can hand the parent's identity to the child, and `bd` in the child
  falls back to its own default actor instead of the parent's. `ATM_TEAM` is
  never cleared. `--identity` is ignored with a warning on stderr.
- When `ATM_TEAM` is set, the launcher also runs
  `atm teams add-member <team> <identity> --model <model> --cwd <dir>` before
  starting the AI tool. Pane-specific `--pane-id` wiring is intentionally left
  as a future follow-up.
- The installed entrypoint is `.claude/scripts/sc-term-launch.sh`, which resolves a
  Python 3 launcher in this order: `python3`, `py -3`, then `python`.
- `--tmux` requires `tmux` to be installed and available on `PATH`.

## Installation

```bash
/marketplace install sc-launch-term
```

This package is intended for global command installation under `~/.claude/`.

## Security and Runtime Notes

- The commands launch locally installed CLIs only. They do not download code or open network connections by themselves.
- `/sc:sonnet`, `/sc:haiku`, `/sc:opus`, and `/sc:fable` invoke the local `claude` CLI with `--dangerously-skip-permissions`, so use this package only in environments where that launch model is acceptable.
- `/sc:sol`, `/sc:astra`, `/sc:terra`, `/sc:luna`, and `/sc:codex` forward to the local `codex` executable on `PATH`.
- `/sc:gemini` forwards to the local `gemini` executable on `PATH`.
- cmux requires the local `cmux` CLI on `PATH`; cmux launches always target a new workspace/tab.
- When `ATM_TEAM` is present, the launcher exports `ATM_TEAM`, an explicit or generated `ATM_IDENTITY`, and `BEADS_ACTOR` set to that identity into the child session. Without `ATM_TEAM`, it exports no identity and clears an inherited `ATM_IDENTITY` and `BEADS_ACTOR` (never `ATM_TEAM`).
- In ATM teammate mode, the launcher also runs `atm teams add-member <team> <identity> --model <model> --cwd <dir>` before starting the tool.
- `--tmux` creates or reuses a local tmux session and therefore depends on a trusted local `tmux` installation.
- The installed wrapper is `.claude/scripts/sc-term-launch.sh`, which resolves Python through the local machine in this order: `python3`, `py -3`, then `python`.

## Examples

```bash
/sc:sonnet ~/projects/foo
/sc:haiku ~/projects/foo --terminal ghostty
/sc:opus ~/projects/foo --tab
/sc:fable ~/projects/foo --terminal cmux --tab
/sc:sol ~/projects/foo
/sc:astra ~/projects/foo --effort high
/sc:terra ~/projects/foo --terminal cmux --tab
/sc:luna ~/projects/foo
/sc:codex ~/projects/foo --identity alice
/sc:sonnet ~/projects/foo -- --continue
/sc:codex ~/projects/foo --tmux
/sc:gemini ~/projects/foo --terminal wt
```
