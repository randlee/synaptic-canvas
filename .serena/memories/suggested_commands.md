# Suggested Commands

- Install package into target repo: `python3 tools/sc-install.py install sc-git-worktree --dest /path/to/repo/.claude`
- List available packages: `python3 tools/sc-install.py list`
- Package info: `python3 tools/sc-install.py info <package-name>`
- Run tests: `pytest`
- Validate agent registry vs frontmatter: `python3 scripts/validate-agents.py` (requires yq, expects .claude/agents/registry.yaml)
