# Session Start Hook Design

**Status:** Draft
**Author:** ARCH-SKILL
**Created:** January 23, 2026
**Package:** sc-manage
**Related:** [Plugin Storage Conventions](../PLUGIN-STORAGE-CONVENTIONS.md), [GitHub Issue #9394](https://github.com/anthropics/claude-code/issues/9394)

---

## Problem Statement

When a plugin is installed globally (`~/.claude/`), it may require per-repo initialization:
- Detect and cache protected branches
- Verify credentials for the repo's provider (GitHub vs Azure)
- Create repo-local settings files
- Display first-time instructions

**Current gap:** Claude Code has no `PostInstall` hook, and even if it did, a global install would only fire once—not per-repo.

**Solution:** Hook into Claude Code's `SessionStart` event to orchestrate per-plugin initialization on each session, with fast "already initialized" checks to minimize overhead.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Claude Code SessionStart Hook (global)                                  │
│   ~/.claude/hooks/hooks.json                                            │
│   { "SessionStart": ["python3 ~/.claude/scripts/sc_session_start.py"] }│
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ sc_session_start.py (Central Orchestrator)                              │
│                                                                         │
│  1. Get session path (cwd - folder Claude was launched from)            │
│  2. Discover installed sc-* plugins:                                    │
│     a. Local: .claude/commands/, .claude/agents/                        │
│     b. Global: ~/.claude/commands/, ~/.claude/agents/                   │
│  3. Deduplicate: local takes precedence over global                     │
│  4. For each plugin with hooks.session_start in manifest:               │
│     → Fire subprocess.Popen() (async, fire-and-forget)                  │
│  5. Spawn watchdog process to enforce global timeout                    │
│  6. Exit immediately (no session-start blocking)                        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│ sc-git-worktree    │ │ sc-github-issue    │ │ sc-nuget-publish   │
│ _session_start.py  │ │ _session_start.py  │ │ _session_start.py  │
│                    │ │                    │ │                    │
│ - Quick init check │ │ - Verify gh auth   │ │ - Check NuGet      │
│ - Detect if git    │ │ - Cache repo info  │ │   credentials      │
│ - Detect branches  │ │ - Setup labels     │ │ - Verify feed      │
│ - Save settings    │ │                    │ │                    │
│   (git: "none" if  │ │                    │ │                    │
│    not a git repo) │ │                    │ │                    │
└────────────────────┘ └────────────────────┘ └────────────────────┘
```

**Note:** Session path is the folder Claude was launched from. It may or may not be a git repository. Plugins must handle both cases.

---

## Prerequisites

### sc-manage Must Be Installed Globally

The orchestrator (`sc_session_start.py`) lives in `sc-manage` and must be installed globally to register the `SessionStart` hook in `~/.claude/hooks/hooks.json`.

Packages that require session-start initialization **depend on sc-manage**.

Because the orchestrator parses `manifest.yaml`, sc-manage must declare a YAML parser dependency (e.g., `requires.python: [pyyaml]`) or switch to a stdlib format.

### Manifest Declaration

Plugins declare their session-start script in `manifest.yaml`:

```yaml
# packages/sc-git-worktree/manifest.yaml
name: sc-git-worktree
version: 1.2.0

hooks:
  # Script MUST be named <plugin>_session_start.py to avoid conflicts
  session_start: scripts/sc_git_worktree_session_start.py

requires:
  packages:
    - sc-manage   # Dependency for session-start orchestration
  python:
    - pyyaml      # Or equivalent if using YAML parsing
```

**Important:** Script must be named `<plugin>_session_start.py` (with underscores replacing hyphens) to prevent filename collisions when multiple plugins are installed.

---

## Orchestrator Specification

### File Location

```
~/.claude/scripts/sc_session_start.py      # Installed by sc-manage
```

### Input

Called by Claude Code's SessionStart hook with no arguments. Orchestrator determines context from environment:

| Source | Value |
|--------|-------|
| `os.getcwd()` | Session path (folder Claude was launched from - may or may not be a git repo) |
| `~/.claude/` | Global plugin install location |
| `.claude/` (in cwd) | Local plugin install location |

### Global Timeout

The orchestrator enforces a **30-second timeout** via a detached watchdog process. This prevents hung plugins from consuming resources indefinitely **without blocking session start**.

**Known limitation:** The watchdog targets PIDs after a delay. In the unlikely event of PID reuse within the timeout window, an unrelated process could be terminated. This is low risk given short-lived session-start scripts; consider process-group targeting or a process table check if this becomes a concern.

### Behavior

```python
#!/usr/bin/env python3
"""
Session Start Orchestrator

Discovers installed sc-* plugins and fires their session_start.py scripts
asynchronously. Each plugin handles its own initialization and idempotency.

Installed by: sc-manage
Location: ~/.claude/scripts/sc_session_start.py
"""

import subprocess
import sys
from pathlib import Path
import yaml

GLOBAL_TIMEOUT_SECONDS = 30


def main():
    session_path = Path.cwd()  # Folder Claude was launched from (may not be git repo)
    home = Path.home()

    # 1. Discover plugins from both locations
    global_plugins = discover_plugins(home / ".claude", scope="global")
    local_plugins = discover_plugins(session_path / ".claude", scope="local")

    # 2. Deduplicate: local takes precedence
    plugins = {**global_plugins, **local_plugins}  # local overwrites global

    # 3. Fire each plugin's session_start.py (async) and track processes
    processes = []
    for name, info in plugins.items():
        if script := info.get("session_start"):
            proc = fire_session_start(
                script_path=script,
                session_path=session_path,
                plugin_path=info["path"],
                scope=info["scope"],
            )
            if proc:
                processes.append((name, proc))

    # 4. Spawn watchdog (detached) to enforce timeout; do not block session start
    if processes:
        spawn_watchdog(processes, GLOBAL_TIMEOUT_SECONDS)

    sys.exit(0)


def discover_plugins(base_path: Path, scope: str) -> dict:
    """
    Discover sc-* plugins in a .claude directory.
    Returns dict of {plugin_name: {path, scope, session_start}}
    """
    plugins = {}
    # Check for manifest files in expected locations
    # Plugins can be in commands/, agents/, or packages/
    for search_dir in ["commands", "agents", "packages"]:
        search_path = base_path / search_dir
        if not search_path.exists():
            continue

        for item in search_path.iterdir():
            if not item.is_dir() or not item.name.startswith("sc-"):
                continue

            manifest_path = item / "manifest.yaml"
            if not manifest_path.exists():
                continue

            try:
                manifest = yaml.safe_load(manifest_path.read_text())
                session_start = manifest.get("hooks", {}).get("session_start")
                script_path = (item / session_start).resolve() if session_start else None
                if script_path and item.resolve() not in script_path.parents:
                    # Defensive: ignore paths that escape the plugin directory
                    continue

                plugins[item.name] = {
                    "path": item,
                    "scope": scope,
                    "session_start": script_path,
                }
            except Exception:
                # Skip malformed manifests
                continue

    return plugins


def fire_session_start(
    script_path: Path, session_path: Path, plugin_path: Path, scope: str
) -> subprocess.Popen | None:
    """
    Fire a plugin's session_start.py asynchronously.
    Returns the Popen object for timeout tracking.
    """
    if not script_path.exists():
        return None

    try:
        return subprocess.Popen(
            [
                sys.executable,  # Use same Python interpreter
                str(script_path),
                "--session-path", str(session_path),
                "--plugin-path", str(plugin_path),
                "--scope", scope,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent session
        )
    except Exception:
        # Don't fail orchestrator if one plugin fails to start
        return None


def spawn_watchdog(processes: list[tuple[str, subprocess.Popen]], timeout_seconds: int) -> None:
    """
    Spawn a detached watchdog that terminates any plugin processes still
    running after the timeout. This keeps SessionStart non-blocking.
    """
    pids = [proc.pid for _, proc in processes if proc and proc.pid]
    if not pids:
        return

    # Detached watchdog process; uses the same interpreter for portability
    watchdog_code = (
        "import os,signal,time\n"
        "import subprocess\n"
        f"time.sleep({timeout_seconds})\n"
        "if os.name == 'nt':\n"
        "    for pid in " + repr(pids) + ":\n"
        "        try:\n"
        "            subprocess.run(['taskkill','/PID',str(pid),'/T','/F'],\n"
        "                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        "        except Exception:\n"
        "            pass\n"
        "else:\n"
        "    for pid in " + repr(pids) + ":\n"
        "        try:\n"
        "            os.kill(pid, signal.SIGTERM)\n"
        "        except Exception:\n"
        "            pass\n"
        "    time.sleep(5)\n"
        "    for pid in " + repr(pids) + ":\n"
        "        try:\n"
        "            os.kill(pid, signal.SIGKILL)\n"
        "        except Exception:\n"
        "            pass\n"
    )

    try:
        subprocess.Popen(
            [sys.executable, "-c", watchdog_code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        # Watchdog failure should not block session start
        pass


if __name__ == "__main__":
    main()
```

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Plugin manifest missing | Skip silently |
| Plugin manifest malformed | Skip silently |
| session_start script missing | Skip silently |
| Script fails to spawn | Skip silently (logged by plugin) |
| Script crashes | Plugin's responsibility to log |
| Script exceeds timeout | Watchdog terminates after 30s |
| Non-git folder | Plugin handles gracefully (records `git: "none"`) |

The orchestrator **never blocks or fails** the session start. All errors are isolated to individual plugins.

---

## Per-Plugin Session Start Contract

### File Location

```
packages/<plugin>/scripts/<plugin>_session_start.py
```

**Example:** `packages/sc-git-worktree/scripts/sc_git_worktree_session_start.py`

The naming convention `<plugin>_session_start.py` (hyphens replaced with underscores) prevents filename collisions when multiple plugins install scripts to the same directory.

### Arguments

| Argument | Description |
|----------|-------------|
| `--session-path` | Absolute path to folder Claude was launched from (may or may not be a git repo) |
| `--plugin-path` | Absolute path to plugin installation |
| `--scope` | `global` or `local` |

**Note:** The session path is NOT necessarily a git repository. Plugins must detect git status themselves and handle non-git folders appropriately (e.g., record `git: "none"` in settings).

### Required Behavior

1. **Fast initialization check**: If already initialized for this session path, exit immediately
2. **Idempotent**: Safe to run multiple times
3. **Self-contained**: Handle own errors, don't depend on orchestrator
4. **Self-logging**: Write to `.claude/state/logs/<package>/session-start.log` (in session path)
5. **Timeout**: Should complete within 10 seconds or background heavy work
6. **Handle non-git folders**: Check for `.git` directory; if absent, record `git: "none"` in settings or skip git-specific initialization

### Example Implementation

```python
#!/usr/bin/env python3
"""
Session Start for sc-git-worktree

File: scripts/sc_git_worktree_session_start.py

Detects git status and protected branches, initializes session-local settings.
Handles both git and non-git folders appropriately.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import yaml
import subprocess

PACKAGE_NAME = "sc-git-worktree"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-path", required=True, type=Path)
    parser.add_argument("--plugin-path", required=True, type=Path)
    parser.add_argument("--scope", required=True, choices=["global", "local"])
    args = parser.parse_args()

    session_path = args.session_path

    # 1. Quick check: already initialized for this session path?
    settings_path = session_path / ".sc" / PACKAGE_NAME / "settings.yaml"
    if settings_path.exists():
        # Already initialized
        sys.exit(0)

    # 2. Check if this is a git repo
    is_git_repo = (session_path / ".git").exists()

    # 3. Initialize settings
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if is_git_repo:
        # Git repo: detect protected branches
        protected_branches = detect_protected_branches(session_path)
        settings = {
            "initialized_at": datetime.now().isoformat(),
            "git": {
                "detected": True,
                "protected_branches": protected_branches,
            },
        }
    else:
        # Not a git repo: record that fact
        settings = {
            "initialized_at": datetime.now().isoformat(),
            "git": "none",  # Explicitly record non-git status
        }

    # 4. Write settings
    settings_path.write_text(yaml.dump(settings, default_flow_style=False))

    # 5. Log initialization
    log_initialization(session_path, settings)

    sys.exit(0)


def detect_protected_branches(session_path: Path) -> list[str]:
    """Detect protected branches from git-flow config."""
    branches = []

    for config_key in ["gitflow.branch.master", "gitflow.branch.develop"]:
        try:
            result = subprocess.run(
                ["git", "config", "--get", config_key],
                cwd=session_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                branches.append(result.stdout.strip())
        except Exception:
            pass

    return branches or ["main"]  # Default fallback


def log_initialization(session_path: Path, settings: dict):
    """Log initialization event."""
    log_dir = session_path / ".claude" / "state" / "logs" / PACKAGE_NAME
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "session-start.log"
    with open(log_file, "a") as f:
        f.write(f"{datetime.now().isoformat()} - Initialized: {settings}\n")


if __name__ == "__main__":
    main()
```

---

## Duplicate Plugin Handling

When a plugin is installed both globally and locally:

| Scenario | Behavior | Rationale |
|----------|----------|-----------|
| Same plugin, both locations | **Local takes precedence** | Local may have repo-specific customizations |
| Different versions | Local version runs | Assume local is intentionally pinned |
| Only global | Global runs | Normal case for shared plugins |
| Only local | Local runs | Normal case for repo-specific plugins |

### Detection Logic

```python
# In orchestrator
global_plugins = discover_plugins(home / ".claude", scope="global")
local_plugins = discover_plugins(session_path / ".claude", scope="local")

# Dict merge: local overwrites global keys
plugins = {**global_plugins, **local_plugins}
```

### Recommendation to Users

When duplicate detected, plugins MAY log a warning:

```
WARNING: sc-git-worktree installed both globally and locally.
Using local version. Consider uninstalling one:
  - Global: ~/.claude/commands/sc-git-worktree/
  - Local: .claude/commands/sc-git-worktree/
```

---

## Installation

### sc-manage Installation

When `sc-manage` is installed globally, it:

1. Creates `~/.claude/scripts/sc_session_start.py`
2. Updates `~/.claude/hooks/hooks.json`:

```json
{
  "SessionStart": [
    "python3 ~/.claude/scripts/sc_session_start.py"
  ]
}
```

### Plugin Installation

Plugins with session-start hooks:

1. Declare in `manifest.yaml`:
   ```yaml
   hooks:
     session_start: scripts/sc_git_worktree_session_start.py  # <plugin>_session_start.py
   requires:
     packages:
       - sc-manage
   ```

2. Implement `scripts/<plugin>_session_start.py` following the contract above

---

## Logging

### Orchestrator Logs

```
~/.claude/state/logs/sc-manage/session-start-orchestrator.log
```

Format:
```
2026-01-23T10:30:00 - Session start: /path/to/repo
2026-01-23T10:30:00 - Discovered plugins: sc-git-worktree (local), sc-github-issue (global)
2026-01-23T10:30:00 - Fired: sc-git-worktree, sc-github-issue
```

**TTL and redaction:** Logs must follow Plugin Storage Conventions (14-day TTL, no secrets). If a shared log-pruner handles TTLs, document it in the package README.

### Per-Plugin Logs

```
.claude/state/logs/<package>/session-start.log   # In the repo
```

Format per plugin's discretion, but should include:
- Timestamp
- Initialization status (skipped/performed)
- Any detected values
- Errors if applicable

---

## Security Considerations

| Risk | Mitigation |
|------|------------|
| Malicious plugin script | Plugins come from trusted sources (marketplace) |
| Script escapes sandbox | Runs in same context as Claude Code |
| Windows watchdog behavior | Uses `taskkill /T /F` for process termination on Windows |
| Credential exposure | Plugins must not log credentials (per storage conventions) |
| Path traversal in manifest | Resolve and ensure `hooks.session_start` stays within plugin directory |
| Resource exhaustion | Each plugin should self-timeout |

---

## Implementation Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| PID reuse during watchdog delay | Unrelated process could be terminated | Low likelihood; prefer process-group targeting or process table validation if it becomes an issue |
| YAML parser dependency missing | Orchestrator fails to parse manifests | Declare `requires.python: [pyyaml]` or switch to a stdlib manifest format |
| Windows process termination differences | Plugin processes may outlive timeout | Use `taskkill /T /F` and document limitations for backgrounded child processes |
| Session path is not a repo | Git-specific initialization fails | Require plugins to detect `.git` and record `git: "none"` |

---

## Testing Strategy

### Unit Tests

1. `discover_plugins()` finds plugins correctly
2. Deduplication prefers local over global
3. Missing manifest handled gracefully
4. Missing session_start script handled gracefully

### Integration Tests

1. Orchestrator runs without blocking
2. Plugin scripts receive correct arguments
3. Fire-and-forget actually detaches
4. Multiple plugins run concurrently
5. Watchdog terminates long-running plugins after timeout

### Manual Testing

```bash
# Simulate session start (run from a session folder)
python3 ~/.claude/scripts/sc_session_start.py

# Check orchestrator logs
cat ~/.claude/state/logs/sc-manage/session-start-orchestrator.log

# Check plugin logs (in session folder)
cat .claude/state/logs/sc-git-worktree/session-start.log

# Check generated settings
cat .sc/sc-git-worktree/settings.yaml

# Test in non-git folder
cd /tmp && python3 ~/.claude/scripts/sc_session_start.py
cat .sc/sc-git-worktree/settings.yaml  # Should show git: "none"
```

---

## Implementation Plan

### Phase 1: Orchestrator (sc-manage)

1. [ ] Create `scripts/sc_session_start.py` in sc-manage package
2. [ ] Update sc-manage installer to register SessionStart hook in `~/.claude/hooks/hooks.json`
3. [ ] Add orchestrator logging to `~/.claude/state/logs/sc-manage/`
4. [ ] Implement 30-second global timeout via detached watchdog process
5. [ ] Test with mock plugins

### Phase 2: First Plugin (sc-git-worktree)

1. [ ] Add `hooks.session_start: scripts/sc_git_worktree_session_start.py` to manifest
2. [ ] Create `scripts/sc_git_worktree_session_start.py`
3. [ ] Implement git detection (handle non-git folders with `git: "none"`)
4. [ ] Implement protected branch detection for git repos
5. [ ] Test end-to-end (both git and non-git folders)

### Phase 3: Documentation

1. [ ] Update PLUGIN-STORAGE-CONVENTIONS.md with session-start section
2. [ ] Add session-start to manifest schema docs
3. [ ] Create example template for plugin authors

### Phase 4: Rollout

1. [ ] Add session-start to sc-github-issue (`scripts/sc_github_issue_session_start.py`)
2. [ ] Add session-start to other plugins as needed
3. [ ] Update marketplace docs

---

## Design Decisions (Resolved)

1. **Global timeout:** ✅ Yes, 30 seconds. Orchestrator tracks spawned processes and terminates any still running after timeout.

2. **State tracking:** ✅ Each plugin manages its own state in `.sc/<package>/settings.yaml`. No central registry.

3. **Notifications:** ✅ Silent operation. No user notifications except for warnings/errors logged to plugin log files.

4. **Script naming:** ✅ Scripts must be named `<plugin>_session_start.py` to avoid filename collisions.

5. **Session vs repo path:** ✅ Pass `--session-path` (folder Claude launched from), not `--repo-path`. Plugins detect git status themselves and handle non-git folders (record `git: "none"`).

---

## Related Work

- [GitHub Issue #9394](https://github.com/anthropics/claude-code/issues/9394) - PostInstall hook request
- [Plugin Storage Conventions](../PLUGIN-STORAGE-CONVENTIONS.md) - Settings and logging standards
- [Architecture Guidelines v0.4](../claude-code-skills-agents-guidelines-0.4.md) - Agent patterns

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
| 2026-01-23 | Added 30s global timeout; changed `--repo-path` to `--session-path`; added non-git folder handling; renamed scripts to `<plugin>_session_start.py` |
