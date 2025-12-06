# Changelog

All notable changes to the **sc-delay-tasks** package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Support for dynamic interval adjustment during polling
- Enhanced logging and debug modes
- Webhook-based notifications on task completion
- Integration with external scheduling services

## [0.4.0] - 2025-12-02

### Status
Beta release - initial v0.x publication.

### Added
- **delay-once** agent: Schedule a single delayed action with minimal overhead
  - Supports minute, hour, and day-based delays
  - Configurable exit action or hook
  - Lightweight wait mechanism
- **delay-poll** agent: Bounded polling with stop-on-success capability
  - Configurable polling interval (minimum 60 seconds)
  - Time-bounded execution window
  - Optional success detection hook
  - Graceful timeout handling
- **git-pr-check-delay** agent: Poll Git/GitHub PR required checks before proceeding
  - Integrates with delay-poll for check status monitoring
  - Useful for CI/CD workflows requiring status verification
- `/delay` command: User-facing command for scheduling delayed tasks
  - `--once` mode: `python3 /delay --once --minutes N --action <command>`
  - `--poll` mode: `python3 /delay --poll --every N --for <duration> --action <command>`
- **delay-run.py** helper script: Common runtime for all agents
  - Efficient polling implementation
  - Minimal heartbeat overhead
  - Cross-platform support

### Components
- Command: `commands/delay.md`
- Skill: `skills/delaying-tasks/SKILL.md`
- Agents:
  - `agents/delay-once.md` (v0.4.0)
  - `agents/delay-poll.md` (v0.4.0)
  - `agents/git-pr-check-delay.md` (v0.4.0)
- Script: `scripts/delay-run.py`

### Dependencies
- **bash**: For command execution and scripting
- **python3**: For scheduling logic and polling implementation

### Scope
- **Global**: Can be installed globally for system-wide access
- **Local**: Can also be installed in individual repositories

### Known Limitations
- Minimum polling interval is 60 seconds (prevents excessive heartbeats)
- Single-machine scheduling only (no distributed scheduler)
- Delays are interrupted if the CLI process terminates
- No persistence across shell sessions

### Requirements
- `python3` must be available in PATH
- `bash` for wrapper scripts and command composition

### Installation
```bash
# Global install
python3 tools/sc-install.py install sc-delay-tasks --dest /Users/<you>/Documents/.claude

# Local (repo-specific) install
python3 tools/sc-install.py install sc-delay-tasks --dest /path/to/your-repo/.claude
```

### Uninstallation
```bash
python3 tools/sc-install.py uninstall sc-delay-tasks --dest /path/to/your-repo/.claude
```

### Troubleshooting
- **"python3 not found"**: Ensure Python 3.8+ is installed and in PATH
- **"Polling timeout exceeded"**: Increase the `--for` duration or adjust the `--every` interval
- **Minimum interval warning**: Polling intervals under 60 seconds are not supported to prevent CLI overhead

### Future Roadmap
- v0.5.0: Add cron-like scheduling with persistent task storage
- v0.6.0: Support for conditional actions and branching logic
- v1.0.0: Stable API with full backward compatibility
- Add webhooks for async notifications
- Native OS-level scheduler integration (launchd on macOS, Task Scheduler on Windows)

### Contributing
When updating this changelog:
1. Add entries under **[Unreleased]** for new features, bug fixes, or breaking changes
2. Use standard changelog categories: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**
3. Link issue/PR numbers when available
4. Create a new section with version and date when releasing
5. Maintain chronological order with newest versions at the top

---

## Repository
- **Repository**: [synaptic-canvas](https://github.com/randlee/synaptic-canvas)
- **Issues**: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- **Package Registry**: [docs/registries/nuget/registry.json](https://github.com/randlee/synaptic-canvas/blob/main/docs/registries/nuget/registry.json)
