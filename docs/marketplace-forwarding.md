# Minimal Marketplace Setup

## Required Files

### `.claude-plugin/marketplace.json` (repo root)

```json
{
  "name": "my-marketplace",
  "owner": { "name": "yourorg", "email": "you@example.com" },
  "metadata": {
    "description": "My Claude Code marketplace",
    "version": "1.0.0"
  },
  "plugins": [
    {
      "name": "my-package",
      "source": "./packages/my-package",
      "description": "What this package does.",
      "version": "1.0.0",
      "author": { "name": "yourorg" },
      "license": "MIT",
      "keywords": ["keyword1"],
      "category": "tools"
    }
  ]
}
```

To reference a plugin from an external repo, use a `source` object:

```json
{
  "name": "my-package",
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/yourorg/other-repo.git",
    "path": "plugins/my-package"
  }
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

## Linking to Synaptic Canvas

Users add each marketplace independently:

```
/plugin marketplace add randlee/synaptic-canvas
/plugin marketplace add yourorg/your-marketplace
```
