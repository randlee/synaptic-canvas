---
description: Deprecated compatibility alias for launching Codex Terra in a supported terminal
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [-- <codex args...>]"
allowed-tools: Bash, AskUserQuestion
---

`/sc:codex` is retained as a deprecated compatibility alias. It routes to the `terra` model and Terra identity pool, launching Codex as `gpt-5.6-terra`.

Use `/sc:terra` for new invocations. The shared launcher handles argument parsing, terminal selection, cmux workspace/tab creation, tmux session collision handling, identity generation, and Codex passthrough arguments.

For this compatibility alias, resolve the optional directory and arguments using the same contract as the model commands, then invoke:

```bash
.claude/scripts/sc-term-launch.sh launch-codex-model codex "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <CODEX_ARG_TAIL>
```

The deprecated `codex` model alias is normalized by the launcher to:

```text
codex --model gpt-5.6-terra --yolo --enable hooks
```
