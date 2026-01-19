# Synaptic Canvas – Project Overview

- Purpose: Marketplace of Claude Code skills/commands/agents packaged for easy reuse and installation.
- Tech stack: Python (CLI under src/sc_cli, agent runner in src/agent_runner), Bash helper scripts, YAML/Markdown artifacts. Tests via pytest.
- Structure: README/CONTRIBUTING docs; packages/ holds package manifests and artifacts (commands/skills/agents/scripts); tools/sc-install.py provides install CLI; scripts/validate-agents.py validates agent versions vs registry; tests/ covers CLI helpers (delay_run, sc_install); docs/ contains additional guidelines.
- Packages: each package has manifest.yaml plus subdirs commands/, skills/, agents/, scripts/; sc-git-worktree is the included package.
- Licensing: MIT.
