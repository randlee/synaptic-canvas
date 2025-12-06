# sc-delay-tasks

[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](https://github.com/randlee/synaptic-canvas/blob/main/docs/PUBLISHER-VERIFICATION.md)
[![Security Scanned](https://img.shields.io/badge/security-scanned-blue)](https://github.com/randlee/synaptic-canvas/blob/main/SECURITY.md)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version 0.5.0](https://img.shields.io/badge/version-0.5.0-blue)](CHANGELOG.md)

Scope: Global or Local
Requires: python3

Schedule delayed one-shot waits or bounded polling with minimal heartbeats. Provides a `/delay` command and agents reusable by other skills (e.g., CI check delays).

Security: See [SECURITY.md](../../../SECURITY.md) for security policy and practices.

## Summary
- delay-once: single wait, emit a final action
- delay-poll: bounded polling, optional stop-on-success hook
- git-pr-check-delay: poll PR required checks using the delay helper

## Quick Start (Global install)
```bash
python3 tools/sc-install.py install sc-delay-tasks --dest /Users/<you>/Documents/.claude
```
Then use `/delay` anywhere.

Repo-local install (optional)
```bash
python3 tools/sc-install.py install sc-delay-tasks --dest /path/to/your-repo/.claude
```

## Usage
- `/delay --once --minutes 2 --action "go"`
- `/delay --poll --every 60 --for 5m --action "done"`

## Agents
- `delay-once` (v0.5.0)
- `delay-poll` (v0.5.0)
- `git-pr-check-delay` (v0.5.0)

All agents call the helper script:
```bash
python3 .claude/scripts/delay-run.py ...
```

## Install / Uninstall
- Install (global):
  ```bash
  python3 tools/sc-install.py install sc-delay-tasks --dest /Users/<you>/Documents/.claude
  ```
- Uninstall:
  ```bash
  python3 tools/sc-install.py uninstall sc-delay-tasks --dest /Users/<you>/Documents/.claude
  ```

## Troubleshooting
- Ensure `python3` is available in PATH
- For polling, minimum interval is 60 seconds

## Components
- Command: `commands/delay.md`
- Agents: `delay-once`, `delay-poll`, `git-pr-check-delay`
- Script: `scripts/delay-run.py`

## Version & Changelog
- 0.5.0 — Initial v0.x publication (three agents)

## Support
- Repository: https://github.com/…/synaptic-canvas
- Issues: https://github.com/…/synaptic-canvas/issues