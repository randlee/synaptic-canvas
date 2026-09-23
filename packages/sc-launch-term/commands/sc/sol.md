---
description: Launch Codex with the GPT-5.6 Sol model in a supported terminal
argument-hint: "[dir] [--terminal <name>] [--tab] [--tmux] [--identity <name>] [-- <codex args...>]"
allowed-tools: Bash, AskUserQuestion
---

Launch Codex with model alias `sol` using the shared Codex model-launch flow.

Use the same argument contract and tmux collision handling as `/sc:codex`, but invoke:

```bash
.claude/scripts/sc-term-launch.sh launch-codex-model sol "<resolved_dir>" <TERM_ARG> <TAB_ARG> <IDENTITY_ARG> <CODEX_ARG_TAIL>
```

The shared launcher resolves a missing identity from the Sol sci-fi/cyberpunk name pool and runs the model as `gpt-5.6-sol`.
