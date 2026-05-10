# Minimal Marketplace Setup

Source of truth: [anthropics/claude-plugins-public](https://github.com/anthropics/claude-plugins-public/blob/main/.claude-plugin/marketplace.json)

---

## Part 1: Source Repo (the minimal marketplace)

The repo hosting the plugin needs two files.

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

---

## Part 2: Consuming Marketplace (synaptic-canvas side)

To pull a plugin from the source repo into synaptic-canvas, add a `git-subdir` entry to `.claude-plugin/marketplace.json`. Pin to a branch with `ref` and optionally a commit with `sha`:

```json
{
  "name": "my-package",
  "description": "What this package does.",
  "author": { "name": "yourorg" },
  "category": "tools",
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/yourorg/your-marketplace.git",
    "path": "packages/my-package",
    "ref": "main",
    "sha": "abc123..."
  }
}
```

No code is copied. Synaptic Canvas points directly at the source repo. Updates to the source repo are picked up automatically when `ref` is a branch name.
