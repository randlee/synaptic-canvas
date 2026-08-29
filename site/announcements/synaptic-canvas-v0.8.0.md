# synaptic-canvas v0.8.0 — Synchronized Platform Release with Simplified Versioning

**Released:** January 20, 2026 · **Install:** `/plugin marketplace add randlee/synaptic-canvas`, then `/plugin install <package>@synaptic-canvas`

[Release notes](https://github.com/randlee/synaptic-canvas/releases/tag/v0.8.0) · [Marketplace registry](https://github.com/randlee/synaptic-canvas/blob/main/docs/registries/nuget/registry.json)

---

## Agent Orchestrator

**As an agent orchestrator, I want a marketplace of reusable orchestration skills (Claude Code skills/agents/commands), so that I can compose my agent's capabilities instead of building each from scratch.**

v0.8.0 is a synchronized platform release: all ten marketplace packages — sc-ci-automation, sc-codex, sc-delay-tasks, sc-git-worktree, sc-github-issue, sc-kanban, sc-manage, sc-repomix-nuget, sc-roslyn-diff, and sc-startup — move to 0.8.0 alongside the marketplace platform itself, with every registry file regenerated. Install or upgrade through the same `/plugin` surface and every package advances together.

The versioning story is the headline for anyone publishing into the marketplace: `scripts/set-package-version.py` becomes the single source of truth, updating package manifests, `plugin.json`, artifact frontmatter, and the registry in one pass — with version-decrement protection and a dry-run mode. `RELEASING.md` documents the whole flow end-to-end, so a release is now a checklist instead of a research project.

Under the hood, the marketplace gains a validation framework: frontmatter schema validators, script-reference and cross-reference validators, and marketplace-sync/registry automation keep a package from shipping with dangling references or a broken manifest. sc-codex also lands in the registry — a packaged Codex runner (Task Tool-compatible, with hook emulation and background execution) that extends the marketplace's reach beyond Claude Code.

---

## What's Next

Version management is now single-sourced for the next bump; the marketplace's test-harness and HTML-reporting work continues to mature package QA.
