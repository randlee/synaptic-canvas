# Synaptic Canvas

[![tests](https://github.com/randlee/synaptic-canvas/actions/workflows/tests.yml/badge.svg)](https://github.com/randlee/synaptic-canvas/actions/workflows/tests.yml)

A marketplace for Claude Code skills, commands, and agents.

## Installation

### Quick Install (single package)

Python CLI (recommended):
```bash
python3 tools/sc-install.py install git-worktree --dest /path/to/your-repo/.claude
```

Bash wrapper (also available):
```bash
./tools/sc-install.sh install git-worktree --dest /path/to/your-repo/.claude
```

From GitHub (once published):
```bash
curl -fsSL https://raw.githubusercontent.com/randlee/synaptic-canvas/main/tools/sc-install.sh | \
  bash -s -- install git-worktree --dest /path/to/your-repo/.claude
```

### Manual Install

1. Clone or download the package folder
2. Copy contents to your repo's `.claude/` directory
3. Replace `{{REPO_NAME}}` tokens with your repository name

## Packages

| Package | Description | Tier |
|---------|-------------|------|
| [git-worktree](packages/git-worktree/) | Manage git worktrees with optional tracking | 1 (token substitution) |

## Package Tiers

- **Tier 0**: Direct copy — no substitution needed
- **Tier 1**: Token substitution — `{{REPO_NAME}}` and similar auto-detected values
- **Tier 2**: Runtime dependencies — requires external tools (Python, Node, etc.)

## Creating a Package

See [CONTRIBUTING.md](CONTRIBUTING.md) for package authoring guidelines.

### Manifest Format

Each package requires a `manifest.yaml`:

```yaml
name: my-package
version: 1.0.0
description: What it does
author: your-handle
tags: [relevant, tags]

artifacts:
  commands:
    - commands/my-command.md
  skills:
    - skills/my-skill/SKILL.md
  agents:
    - agents/my-agent.md

# Optional: token substitution (makes it Tier 1)
variables:
  REPO_NAME:
    auto: git-repo-basename

# Optional: runtime requirements (makes it Tier 2)
requires:
  - git >= 2.0
```

## License

MIT
