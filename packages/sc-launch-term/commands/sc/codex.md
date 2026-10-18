---
description: Launch Codex with the default Codex model (gpt-6.1-sol) in a supported terminal
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [--effort <level>] [-- <codex args...>]"
allowed-tools: Bash, AskUserQuestion
---

`/sc:codex` launches the Codex CLI's default model, currently `sol` (`gpt-6.1-sol`), and uses the Sol identity pool.

Use the same argument contract and tmux collision handling as `/sc:fable` (session name `"{folder} - codex"`), with
`CODEX_ARG_TAIL` (everything after `--`, forwarded to `codex`) in place of
`CLAUDE_ARG_TAIL`, `--effort <level>` accepting `low`, `medium`, `high`, `xhigh`, `max`, or `ultra`
(passed as `-c model_reasoning_effort=<level>`; default: the model's own, `low`),
and invoke:

```bash
.claude/scripts/sc-term-launch.sh launch-codex-model codex "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <EFFORT_ARG> <CODEX_ARG_TAIL>
```

For `--tmux`, use `launch-codex-model codex ... --tmux "<session>"` and
`attach-pane-codex-model "<session>" codex --cwd "<resolved_dir>" ...` in place of the
Claude subcommands.

With `ATM_TEAM` set, a missing identity is drawn from the Sol sci-fi/cyberpunk name pool; without `ATM_TEAM`, no identity is generated or exported and `--identity` is ignored with a warning. The launched command is:

```text
codex --model gpt-6.1-sol --yolo --enable hooks
```
