# Minimal Marketplace Setup

Source of truth: [anthropics/claude-plugins-public](https://github.com/anthropics/claude-plugins-public/blob/main/.claude-plugin/marketplace.json)

## Required Files

### `.claude-plugin/marketplace.json` (repo root)

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "my-marketplace",
  "description": "My Claude Code marketplace",
  "owner": { "name": "yourorg", "email": "you@example.com" },
  "plugins": [
    {
      "name": "my-package",
      "description": "What this package does.",
      "author": { "name": "yourorg" },
      "category": "tools",
      "source": "./packages/my-package",
      "homepage": "https://github.com/yourorg/your-marketplace"
    }
  ]
}
```

### `packages/my-package/.claude-plugin/plugin.json`

```json
{
  "name": "my-package",
  "description": "What this package does.",
  "version": "1.0.0",
  "author": { "name": "yourorg" }
}
```

## Referencing a Plugin from an External Repo

Use a `git-subdir` source object instead of a local path. Pin to a commit with `sha`, optionally a branch/tag with `ref`:

```json
{
  "name": "my-package",
  "description": "What this package does.",
  "author": { "name": "yourorg" },
  "category": "tools",
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/yourorg/other-repo.git",
    "path": "plugins/my-package",
    "ref": "main",
    "sha": "abc123..."
  }
}
```

## Linking to Synaptic Canvas

To reference a Synaptic Canvas package from your marketplace, add an entry pointing to its repo:

```json
{
  "name": "sc-git-worktree",
  "description": "Manage git worktrees for parallel development.",
  "author": { "name": "randlee" },
  "category": "tools",
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/randlee/synaptic-canvas.git",
    "path": "packages/sc-git-worktree",
    "ref": "main"
  }
}
```
