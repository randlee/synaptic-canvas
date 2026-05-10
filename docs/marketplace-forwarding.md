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

`source` must be a relative path to the package directory within the same repo.

### `packages/my-package/.claude-plugin/plugin.json`

```json
{
  "name": "my-package",
  "description": "What this package does.",
  "version": "1.0.0",
  "author": { "name": "yourorg" },
  "license": "MIT",
  "keywords": ["keyword1"],
  "commands": ["./commands/my-command.md"],
  "skills": ["./skills/my-skill/SKILL.md"],
  "agents": ["./agents/my-agent.md"]
}
```

Omit `commands`, `skills`, or `agents` arrays if the package has none.

## Linking to Synaptic Canvas

Users add each marketplace independently:

```
/plugin marketplace add randlee/synaptic-canvas
/plugin marketplace add yourorg/your-marketplace
```

There is no built-in forwarding between marketplaces. Each is a separate source.
