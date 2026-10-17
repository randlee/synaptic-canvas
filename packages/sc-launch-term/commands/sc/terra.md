---
description: Launch Codex with the Terra model (gpt-5.6-terra) in a supported terminal
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [--effort <level>] [-- <codex args...>]"
allowed-tools: Bash, AskUserQuestion
---

Launch Codex with model alias `terra` using the shared Codex model-launch flow.

Use the same argument contract and tmux collision handling as `/sc:fable` (session name `"{folder} - terra"`), with
`CODEX_ARG_TAIL` (everything after `--`, forwarded to `codex`) in place of
`CLAUDE_ARG_TAIL`, `--effort <level>` accepting `low`, `medium`, `high`, `xhigh`, `max`, or `ultra`
(passed as `-c model_reasoning_effort=<level>`; default: the model's own, `medium`),
and invoke:

```bash
.claude/scripts/sc-term-launch.sh launch-codex-model terra "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <EFFORT_ARG> <CODEX_ARG_TAIL>
```

For `--tmux`, use `launch-codex-model terra ... --tmux "<session>"` and
`attach-pane-codex-model "<session>" terra --cwd "<resolved_dir>" ...` in place of the
Claude subcommands.

A missing identity is drawn from the Terra sci-fi/cyberpunk name pool. The launched command is:

```text
codex --model gpt-5.6-terra --yolo --enable hooks
```
