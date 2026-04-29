# Refactory Runtime Layout

Package source lives under `packages/sc-refactory/`.

When installed, the package artifacts are copied into:

- `~/.claude/agents/`, `~/.claude/skills/`, `~/.claude/scripts/`
- or `<repo>/.claude/agents/`, `<repo>/.claude/skills/`, `<repo>/.claude/scripts/`

After `refactory-install` runs in a repo, the repo-local runtime should include:

- `.startup/team-lead`
- `.refactor/docs/`
- `.refactor/rules/`
- `.refactor/profiles/`
- `.refactor/scripts/`
- `.refactor/reports/`
- `.refactor/db/`
- `.refactor/logs/`
- `.refactor/temp/`
