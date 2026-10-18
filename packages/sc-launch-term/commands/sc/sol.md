---
description: Launch Codex with the Sol model (gpt-6.1-sol) in a supported terminal
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [--effort <level>] [-- <codex args...>]"
allowed-tools: Bash, AskUserQuestion
---

Launch Codex with model alias `sol` using the shared Codex model-launch flow.

Use the same argument contract and tmux collision handling as `/sc:fable` (session name `"{folder} - sol"`), with
`CODEX_ARG_TAIL` (everything after `--`, forwarded to `codex`) in place of
`CLAUDE_ARG_TAIL`, `--effort <level>` accepting `low`, `medium`, `high`, `xhigh`, `max`, or `ultra`
(passed as `-c model_reasoning_effort=<level>`; default: the model's own, `low`),
and invoke:

```bash
.claude/scripts/sc-term-launch.sh launch-codex-model sol "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <EFFORT_ARG> <CODEX_ARG_TAIL>
```

For `--tmux`, use `launch-codex-model sol ... --tmux "<session>"` and
`attach-pane-codex-model "<session>" sol --cwd "<resolved_dir>" ...` in place of the
Claude subcommands.

With `ATM_TEAM` set, a missing identity is drawn from the Sol sci-fi/cyberpunk name pool; without `ATM_TEAM`, no identity is generated or exported and `--identity` is ignored with a warning. The launched command is:

```text
codex --model gpt-6.1-sol --yolo --enable hooks
```
