# Marketplace Forwarding and Second-Repo Setup

How to set up a second GitHub repository as a Claude Code marketplace and link it to the Synaptic Canvas primary marketplace.

---

## How the Marketplace System Works

Claude Code's marketplace is **not a single centralized registry**. It is a collection of independently registered sources. Each user adds marketplaces by GitHub repo:

```
/plugin marketplace add randlee/synaptic-canvas
/plugin marketplace add yourorg/your-marketplace
```

Each marketplace is **siloed** — there is no built-in forwarding, symlink, or inheritance between them. A "second repo" marketplace is a fully independent registry that users add alongside (not instead of) the primary.

---

## What a Second Repo Actually Needs

A working marketplace requires **three files** per package, not two. The two-file minimum described in some sources omits the `registry.json`, which is the file Claude Code fetches over HTTP for install resolution.

### File 1: `.claude-plugin/marketplace.json` (repo root)

Registers the repo as a marketplace. Each plugin entry requires all fields below — `name`+`source` alone is insufficient.

```json
{
  "name": "my-marketplace",
  "owner": {
    "name": "yourorg",
    "email": "you@example.com"
  },
  "metadata": {
    "description": "A marketplace for my Claude Code packages",
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
      "keywords": ["keyword1", "keyword2"],
      "category": "tools"
    }
  ]
}
```

**Important:** `source` must be a **relative path** to the package directory within the same repo. GitHub URLs are not supported in `marketplace.json`.

### File 2: `packages/my-package/.claude-plugin/plugin.json`

Defines the individual package and declares its artifacts. `name`+`version` alone is not enough — Claude Code needs the artifact lists to install correctly.

```json
{
  "name": "my-package",
  "description": "What this package does.",
  "version": "1.0.0",
  "author": { "name": "yourorg" },
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "commands": [
    "./commands/my-command.md"
  ],
  "skills": [
    "./skills/my-skill/SKILL.md"
  ],
  "agents": [
    "./agents/my-agent.md"
  ]
}
```

Omit `commands`, `skills`, or `agents` arrays if the package has none of that type.

### File 3: `docs/registries/nuget/registry.json`

This is the **distribution registry** — what Claude Code fetches over HTTP when resolving installs. Without it, `/plugin install package@marketplace` cannot resolve.

Claude Code looks for this file at:
```
https://raw.githubusercontent.com/yourorg/your-marketplace/main/docs/registries/nuget/registry.json
```
with fallback to `master` branch and GitHub Pages.

Minimum structure:

```json
{
  "version": "2.0.0",
  "generated": "2026-01-01T00:00:00Z",
  "repo": "yourorg/your-marketplace",
  "marketplace": {
    "name": "My Marketplace",
    "version": "1.0.0",
    "status": "beta",
    "url": "https://github.com/yourorg/your-marketplace"
  },
  "metadata": {
    "registryVersion": "2.0.0",
    "schemaVersion": "1.0.0",
    "totalPackages": 1,
    "totalCommands": 1,
    "totalSkills": 1,
    "totalAgents": 0,
    "totalScripts": 0,
    "categories": {
      "tools": ["my-package"]
    }
  },
  "packages": {
    "my-package": {
      "name": "my-package",
      "version": "1.0.0",
      "status": "beta",
      "tier": 0,
      "description": "What this package does.",
      "github": "yourorg/your-marketplace",
      "repo": "https://github.com/yourorg/your-marketplace",
      "path": "packages/my-package",
      "readme": "https://raw.githubusercontent.com/yourorg/your-marketplace/main/packages/my-package/README.md",
      "license": "MIT",
      "author": { "name": "yourorg" },
      "tags": ["keyword1", "keyword2"],
      "artifacts": {
        "commands": 1,
        "skills": 1,
        "agents": 0,
        "scripts": 0,
        "schemas": 0
      },
      "dependencies": [],
      "changelog": "https://raw.githubusercontent.com/yourorg/your-marketplace/main/packages/my-package/CHANGELOG.md",
      "lastUpdated": "2026-01-01",
      "dependents": []
    }
  },
  "versionCompatibility": {},
  "publishers": {}
}
```

---

## Package Tiers

| Tier | Meaning | Example |
|------|---------|---------|
| `0` | No dependencies — works immediately after copy | `sc-delay-tasks` |
| `1` | Token substitution required (e.g., `{{REPO_NAME}}`) | `sc-git-worktree` |
| `2` | External CLI tools or runtime required | `sc-ci-automation` |

Set `tier` in `registry.json` based on what the package needs at install time.

---

## How to Link to Synaptic Canvas (the Primary Marketplace)

Claude Code treats every registered marketplace as an independent source. There is no technical "link" — but there are two documentation-level approaches:

### Option 1: Recommend Both (preferred)

In your repo's `README.md`, instruct users to add both marketplaces:

```bash
# Add the primary marketplace (skills, agents, worktree tools, etc.)
/plugin marketplace add randlee/synaptic-canvas

# Add your marketplace
/plugin marketplace add yourorg/your-marketplace
```

Packages from both marketplaces become available side by side. Name collisions are avoided by using distinct package name prefixes (Synaptic Canvas uses `sc-`; pick a different prefix for your packages).

### Option 2: Repackage a Dependency

If your package depends on a Synaptic Canvas package at install time, declare it in `registry.json`:

```json
"dependencies": ["sc-git-worktree >= 0.12.0"]
```

This is declarative only — it documents the requirement but does not auto-install. Users must add the Synaptic Canvas marketplace separately to satisfy it.

---

## What Does NOT Work

| Misconception | Reality |
|---|---|
| `"source": "https://github.com/..."` in `marketplace.json` | **Not supported.** `source` must be a relative path. GitHub URLs only appear in `registry.json`. |
| A marketplace that "forwards" installs to another marketplace | **Not supported.** Each marketplace is siloed; users add each one independently. |
| Minimum `plugin.json` with only `name` + `version` | **Insufficient.** Artifact arrays (`commands`, `skills`, `agents`) are required for install to copy the right files. |
| Two-file setup (marketplace.json + plugin.json) | **Incomplete.** `registry.json` is required for HTTP-based install resolution. |

---

## Automation

Synaptic Canvas keeps `marketplace.json` and `registry.json` in sync via:

```bash
python3 scripts/sync-marketplace-json.py   # update marketplace.json from registry.json
python3 scripts/validate-marketplace-sync.py  # validate both are consistent
```

For a new marketplace, adapt these scripts or maintain the files manually. `registry.json` is the source of truth; `marketplace.json` is derived from it.

---

## Minimal Directory Structure

```
your-marketplace/
├── .claude-plugin/
│   └── marketplace.json          # registers the repo as a marketplace
├── packages/
│   └── my-package/
│       ├── .claude-plugin/
│       │   └── plugin.json       # defines the package + artifact lists
│       ├── commands/
│       │   └── my-command.md
│       ├── skills/
│       │   └── my-skill/
│       │       └── SKILL.md
│       ├── README.md
│       └── CHANGELOG.md
└── docs/
    └── registries/
        └── nuget/
            └── registry.json     # HTTP distribution registry (required for install)
```
