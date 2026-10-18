---
description: Launch Codex with the Luna model (gpt-6-luna) in a supported terminal
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [--effort <level>] [-- <codex args...>]"
allowed-tools: Bash, AskUserQuestion
---

Launch Codex with model alias `luna` using the shared Codex model-launch flow.

Use the same argument contract and tmux collision handling as `/sc:fable` (session name `"{folder} - luna"`), with
`CODEX_ARG_TAIL` (everything after `--`, forwarded to `codex`) in place of
`CLAUDE_ARG_TAIL`, `--effort <level>` accepting `low`, `medium`, `high`, `xhigh`, or `max`
(passed as `-c model_reasoning_effort=<level>`; default: the model's own, `medium`),
and invoke:

```bash
.claude/scripts/sc-term-launch.sh launch-codex-model luna "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <EFFORT_ARG> <CODEX_ARG_TAIL>
```

For `--tmux`, use `launch-codex-model luna ... --tmux "<session>"` and
`attach-pane-codex-model "<session>" luna --cwd "<resolved_dir>" ...` in place of the
Claude subcommands.

With `ATM_TEAM` set, the identity is exported as both `ATM_IDENTITY` and `BEADS_ACTOR`, and a missing identity is drawn from the Luna sci-fi/cyberpunk name pool; without `ATM_TEAM`, no identity is generated or exported, an inherited `ATM_IDENTITY` and `BEADS_ACTOR` are cleared, and `--identity` is ignored with a warning. The launched command is:

```text
codex --model gpt-6-luna --yolo --enable hooks
```
