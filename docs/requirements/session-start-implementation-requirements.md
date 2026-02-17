# Session Start Implementation Requirements

**Created**: 2026-02-13
**Status**: Requirements Analysis
**Related Design**: [Session Start Hook Design](../design/sc-session-start-design.md)
**Related Convention**: [Plugin Storage Conventions](../PLUGIN-STORAGE-CONVENTIONS.md)

---

## Executive Summary

This document provides implementation requirements for two tasks:

1. **Task #1**: Create `sc_session_start.py` orchestrator in sc-manage package
2. **Task #2**: Update sc-manage installer to register SessionStart hook

These tasks enable per-session initialization for globally-installed plugins when Claude Code starts in a new folder.

---

## Current State Analysis

### Existing Infrastructure

**sc-manage Package Status**:
- **Location**: `/packages/sc-manage/`
- **Version**: 0.8.0
- **Current capabilities**: Install/uninstall packages, manage package registry
- **Install script**: Uses `tools/sc-install.py` → `src/sc_cli/install.py`
- **Registry management**: Updates `.claude/agents/registry.yaml` with installed agents/skills

**Hook System Status**:
- **Format**: JSON-based hooks in `.claude/settings.local.json` or `~/.claude/hooks/hooks.json` (per design)
- **Example hook structure**:
  ```json
  {
    "hooks": {
      "PreToolUse": [
        {
          "matcher": "Task",
          "hooks": [
            {
              "type": "command",
              "command": "python3 .claude/scripts/log-task-input.py"
            }
          ]
        }
      ]
    }
  }
  ```
- **SessionStart hook**: Not yet implemented (design exists)

**Dependencies**:
- `pydantic`: Already in sc-manage requirements
- `pyyaml`: Need to add (for manifest parsing)
- `python3`: Already required

### Design Document Status

**Design**: `/docs/design/sc-session-start-design.md` (✅ Complete)

**Key specifications**:
- Orchestrator location: `~/.claude/scripts/sc_session_start.py`
- Hook registration: `~/.claude/hooks/hooks.json`
- Per-plugin scripts: `scripts/<plugin>_session_start.py`
- Global timeout: 30 seconds (enforced by detached watchdog)
- Session path: `os.getcwd()` (may not be a git repo)
- Non-blocking: Fire-and-forget with async process spawning

---

## Task #1: Create sc_session_start.py Orchestrator

### Requirements

#### 1.1 File Location and Structure

**Location**: `packages/sc-manage/scripts/sc_session_start.py`

**Installation target**: `~/.claude/scripts/sc_session_start.py` (when sc-manage installed globally)

**Entry point**: Called by Claude Code's SessionStart hook with no arguments

**Required behavior**:
1. Discover all `sc-*` plugins from global and local `.claude` directories
2. Deduplicate plugins (local takes precedence over global)
3. Parse `manifest.yaml` for each plugin to find `hooks.session_start` declaration
4. Fire each plugin's session start script asynchronously (fire-and-forget)
5. Spawn detached watchdog process to enforce 30-second timeout
6. Exit immediately without blocking session start

#### 1.2 Discovery Algorithm

**Search locations**:
- Global: `~/.claude/commands/`, `~/.claude/agents/`, `~/.claude/packages/`
- Local: `.claude/commands/`, `.claude/agents/`, `.claude/packages/` (in cwd)

**Discovery logic**:
```python
def discover_plugins(base_path: Path, scope: str) -> dict:
    """
    Discover sc-* plugins in a .claude directory.
    Returns dict of {plugin_name: {path, scope, session_start}}
    """
    plugins = {}
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

                # Security: prevent path traversal
                if script_path and item.resolve() not in script_path.parents:
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
```

#### 1.3 Plugin Script Invocation

**Arguments passed to each plugin script**:
- `--session-path <path>`: Folder Claude was launched from (may not be git repo)
- `--plugin-path <path>`: Absolute path to plugin installation directory
- `--scope <global|local>`: Installation scope

**Invocation method**:
```python
subprocess.Popen(
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
```

#### 1.4 Timeout Enforcement

**Global timeout**: 30 seconds

**Implementation**: Detached watchdog process

**Watchdog behavior**:
1. Sleep for timeout duration (30 seconds)
2. Terminate all tracked PIDs
3. On Windows: Use `taskkill /PID <pid> /T /F`
4. On Unix: Send `SIGTERM`, wait 5 seconds, then `SIGKILL`

**Known limitation**: PID reuse within timeout window could terminate unrelated process (low risk)

#### 1.5 Error Handling

**Error policy**: Orchestrator never blocks or fails session start

| Scenario | Behavior |
|----------|----------|
| Plugin manifest missing | Skip silently |
| Plugin manifest malformed | Skip silently |
| session_start script missing | Skip silently |
| Script fails to spawn | Skip silently |
| Script crashes | Plugin's responsibility |
| Script exceeds timeout | Watchdog terminates after 30s |
| Non-git folder | Pass to plugin (handles gracefully) |

#### 1.6 Logging Requirements

**Log location**: `~/.claude/state/logs/sc-manage/session-start-orchestrator.log`

**Log format**: Structured JSONL using sc-logging template

**Events to log**:
- Session start with session path
- Discovered plugins (count and names)
- Fired plugins (success/failure per plugin)
- Watchdog spawned (with timeout and PIDs)
- Any errors (with context)

**Log fields** (extend BaseLogEntry):
```python
class SessionStartLogEntry(BaseLogEntry):
    session_path: Optional[str] = None
    plugins_discovered: Optional[List[str]] = None
    plugins_fired: Optional[List[str]] = None
    watchdog_pids: Optional[List[int]] = None
    error_context: Optional[str] = None
```

#### 1.7 Dependencies

**Python dependencies** (add to manifest.yaml):
- `pyyaml`: For manifest parsing
- `pydantic`: For structured logging (already present)

**System dependencies** (already present):
- `python3`: Interpreter
- `git`: Not required by orchestrator itself

#### 1.8 Implementation Checklist

- [ ] Create `packages/sc-manage/scripts/sc_session_start.py`
- [ ] Copy `templates/sc-logging.jenga.py` → `packages/sc-manage/scripts/sc_logging.py`
- [ ] Expand Jenga variables: `PACKAGE_NAME = "sc-manage"`
- [ ] Extend LogEntry with session-start-specific fields
- [ ] Implement `discover_plugins()` function
- [ ] Implement `fire_session_start()` function
- [ ] Implement `spawn_watchdog()` function with cross-platform support
- [ ] Implement deduplication logic (local overrides global)
- [ ] Add path traversal prevention in manifest parsing
- [ ] Add structured logging for all operations
- [ ] Handle YAML parsing errors gracefully
- [ ] Test on both Windows and Unix platforms
- [ ] Add unit tests (see Testing Requirements)

---

## Task #2: Update sc-manage Installer to Register SessionStart Hook

### Requirements

#### 2.1 Hook Registration Format

**Hook file location**: `~/.claude/hooks/hooks.json` (per design) OR `.claude/settings.json` format

**Based on existing hook structure**, the SessionStart hook should be registered as:

**Option A: Using hooks.json (from design)**:
```json
{
  "SessionStart": [
    "python3 ~/.claude/scripts/sc_session_start.py"
  ]
}
```

**Option B: Using settings.json format (from existing implementation)**:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "python3 ~/.claude/scripts/sc_session_start.py"
      }
    ]
  }
}
```

**Note**: Need to verify which format Claude Code actually uses for SessionStart hooks. The design document shows Option A, but existing PreToolUse hooks use Option B format.

#### 2.2 Installer Modification Points

**Installation script location**: `src/sc_cli/install.py`

**Relevant function**: `_update_registry()` (line 1002) - updates `.claude/agents/registry.yaml`

**New function needed**: `_register_session_start_hook(dest_path: Path) -> int`

**Trigger condition**: When `sc-manage` is installed globally or to `~/.claude`

#### 2.3 Hook Registration Algorithm

```python
def _register_session_start_hook(dest_path: Path) -> int:
    """Register SessionStart hook in hooks configuration.

    Args:
        dest_path: Path to .claude directory (should be ~/.claude for global)

    Returns:
        0 on success, 1 on failure
    """
    # Only register when installing to global ~/.claude
    home_claude = Path.home() / ".claude"
    if dest_path.resolve() != home_claude.resolve():
        # Not a global install, skip hook registration
        return 0

    # Determine hook file format and location
    hooks_json_path = home_claude / "hooks" / "hooks.json"
    settings_json_path = home_claude / "settings.json"

    # Try hooks.json first (per design document)
    if hooks_json_path.exists() or not settings_json_path.exists():
        return _register_in_hooks_json(hooks_json_path)
    else:
        return _register_in_settings_json(settings_json_path)


def _register_in_hooks_json(hooks_path: Path) -> int:
    """Register in hooks.json format (per design)."""
    hooks_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing hooks
    hooks = {}
    if hooks_path.exists():
        try:
            if yaml is not None:
                hooks = yaml.safe_load(_read_file(hooks_path)) or {}
            else:
                hooks = json.loads(_read_file(hooks_path))
        except Exception as e:
            warn(f"Could not parse {hooks_path}: {e}")
            return 1

    # Add SessionStart hook
    if "SessionStart" not in hooks:
        hooks["SessionStart"] = []

    hook_command = "python3 ~/.claude/scripts/sc_session_start.py"
    if hook_command not in hooks["SessionStart"]:
        hooks["SessionStart"].append(hook_command)

    # Write back
    try:
        if yaml is not None:
            content = yaml.safe_dump(hooks, sort_keys=False)
        else:
            content = json.dumps(hooks, indent=2)
        hooks_path.write_text(content)
        info(f"Registered SessionStart hook in {hooks_path}")
        return 0
    except Exception as e:
        error(f"Failed to write {hooks_path}: {e}")
        return 1


def _register_in_settings_json(settings_path: Path) -> int:
    """Register in settings.json format (existing pattern)."""
    # Load existing settings
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(_read_file(settings_path))
        except Exception as e:
            warn(f"Could not parse {settings_path}: {e}")
            return 1

    # Initialize hooks section
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "SessionStart" not in settings["hooks"]:
        settings["hooks"]["SessionStart"] = []

    # Add hook entry
    hook_entry = {
        "type": "command",
        "command": "python3 ~/.claude/scripts/sc_session_start.py"
    }

    # Check if already registered
    for existing in settings["hooks"]["SessionStart"]:
        if existing.get("command") == hook_entry["command"]:
            info("SessionStart hook already registered")
            return 0

    settings["hooks"]["SessionStart"].append(hook_entry)

    # Write back
    try:
        content = json.dumps(settings, indent=2)
        settings_path.write_text(content)
        info(f"Registered SessionStart hook in {settings_path}")
        return 0
    except Exception as e:
        error(f"Failed to write {settings_path}: {e}")
        return 1
```

#### 2.4 Integration with Existing Installer

**Modification point**: In `src/sc_cli/install.py`, after line 1246 (registry update), add:

```python
# Update registry.yaml (agents and skills)
_update_registry(dest_path, installed_artifact_rels)

# Register SessionStart hook if installing sc-manage globally
if pkg_dir.name == "sc-manage":
    hook_result = _register_session_start_hook(dest_path)
    if hook_result != 0:
        warn("Failed to register SessionStart hook (sc-manage will still work)")
        # Don't fail installation if hook registration fails
```

#### 2.5 Artifact Installation

**Ensure orchestrator script is installed**:

In `packages/sc-manage/manifest.yaml`, add to artifacts.scripts:
```yaml
artifacts:
  scripts:
    - scripts/sc_session_start.py  # ADD THIS LINE
    - scripts/sc_shared.py
    - scripts/sc_manage_common.py
    # ... existing scripts
```

**Script installation**: The existing installer already handles copying scripts from artifacts to `dest_path/scripts/`

#### 2.6 Uninstallation Handling

**Hook removal**: When sc-manage is uninstalled globally, should remove SessionStart hook

**Implementation**: Add function to uninstall logic in `src/sc_cli/install.py`:

```python
def _unregister_session_start_hook(dest_path: Path) -> int:
    """Remove SessionStart hook when uninstalling sc-manage globally."""
    home_claude = Path.home() / ".claude"
    if dest_path.resolve() != home_claude.resolve():
        return 0  # Not global install, nothing to remove

    # Try both possible locations
    hooks_json_path = home_claude / "hooks" / "hooks.json"
    settings_json_path = home_claude / "settings.json"

    result = 0
    for path in [hooks_json_path, settings_json_path]:
        if path.exists():
            result |= _remove_hook_from_file(path)

    return result
```

#### 2.7 Dependency Updates

**Update manifest.yaml**:

```yaml
# packages/sc-manage/manifest.yaml
requires:
  - python3
  - git
  - pydantic
  - pyyaml  # ADD THIS LINE (needed for manifest parsing)
```

#### 2.8 Implementation Checklist

- [ ] Add `sc_session_start.py` to `artifacts.scripts` in manifest.yaml
- [ ] Add `pyyaml` to `requires` in manifest.yaml
- [ ] Create `_register_session_start_hook()` function in `src/sc_cli/install.py`
- [ ] Create `_register_in_hooks_json()` helper function
- [ ] Create `_register_in_settings_json()` helper function
- [ ] Add hook registration call after registry update in install flow
- [ ] Create `_unregister_session_start_hook()` function
- [ ] Add hook removal call in uninstall flow
- [ ] Test global installation registers hook correctly
- [ ] Test local installation skips hook registration
- [ ] Test uninstallation removes hook
- [ ] Test idempotency (re-installing doesn't duplicate hooks)
- [ ] Document in sc-manage README.md
- [ ] Update CHANGELOG.md with new capability

---

## Testing Requirements

### Unit Tests

**Test file**: `packages/sc-manage/tests/test_session_start.py`

**Required tests**:

1. **Discovery tests**:
   - Test `discover_plugins()` finds plugins in commands/agents/packages
   - Test deduplication (local overrides global)
   - Test malformed manifest handling
   - Test missing session_start script handling
   - Test path traversal prevention

2. **Invocation tests**:
   - Test `fire_session_start()` spawns process correctly
   - Test arguments passed correctly
   - Test process detachment (start_new_session)
   - Test failure handling (script doesn't exist)

3. **Watchdog tests**:
   - Test `spawn_watchdog()` spawns detached process
   - Test timeout enforcement (mock sleep)
   - Test cross-platform termination (Windows vs Unix)

4. **Logging tests**:
   - Test structured logging to correct location
   - Test all event types logged
   - Test no secrets in logs

**Test file**: `tests/test_session_start_registration.py`

**Required tests**:

1. **Hook registration tests**:
   - Test hook registered in hooks.json format
   - Test hook registered in settings.json format
   - Test idempotency (no duplicates)
   - Test global install only
   - Test local install skips registration

2. **Hook unregistration tests**:
   - Test hook removed on uninstall
   - Test graceful handling if hook file doesn't exist

### Integration Tests

**Test file**: `tests/integration/test_session_start_e2e.py`

**Required tests**:

1. Install sc-manage globally
2. Verify `~/.claude/scripts/sc_session_start.py` exists
3. Verify hook registered in hooks file
4. Create mock plugin with session_start script
5. Simulate SessionStart hook execution
6. Verify plugin script called with correct arguments
7. Verify logs created in expected locations
8. Uninstall sc-manage
9. Verify hook removed

### Manual Testing

**Test script location**: Create `scripts/test-session-start-manual.sh`

**Test steps**:
```bash
#!/bin/bash
# Manual testing script for session-start functionality

echo "=== Session Start Manual Test ==="

# 1. Install sc-manage globally
echo "Installing sc-manage globally..."
python3 tools/sc-install.py install sc-manage --dest ~/.claude

# 2. Verify orchestrator installed
echo "Checking orchestrator exists..."
test -f ~/.claude/scripts/sc_session_start.py && echo "✓ Orchestrator found" || echo "✗ Orchestrator missing"

# 3. Verify hook registered
echo "Checking hook registration..."
if [ -f ~/.claude/hooks/hooks.json ]; then
    grep -q "sc_session_start.py" ~/.claude/hooks/hooks.json && echo "✓ Hook in hooks.json" || echo "✗ Hook missing"
elif [ -f ~/.claude/settings.json ]; then
    grep -q "sc_session_start.py" ~/.claude/settings.json && echo "✓ Hook in settings.json" || echo "✗ Hook missing"
else
    echo "✗ No hooks file found"
fi

# 4. Test orchestrator directly
echo "Testing orchestrator execution..."
cd /tmp
python3 ~/.claude/scripts/sc_session_start.py
echo "Exit code: $?"

# 5. Check logs
echo "Checking logs..."
test -f ~/.claude/state/logs/sc-manage/session-start-orchestrator.log && echo "✓ Logs created" || echo "✗ No logs"

# 6. View logs
echo "Recent log entries:"
tail -n 5 ~/.claude/state/logs/sc-manage/session-start-orchestrator.log || echo "(no logs yet)"

echo "=== Test Complete ==="
```

---

## Implementation Order

### Phase 1: Orchestrator (Task #1)
1. Copy sc-logging template to sc-manage
2. Create sc_session_start.py with discovery logic
3. Implement plugin script invocation
4. Implement watchdog timeout
5. Add structured logging
6. Write unit tests
7. Test manually in isolation

### Phase 2: Installer Integration (Task #2)
1. Add orchestrator to manifest artifacts
2. Add pyyaml to manifest requires
3. Implement hook registration functions
4. Integrate with install flow
5. Implement hook unregistration
6. Write installer tests
7. Test end-to-end

### Phase 3: Documentation & Polish
1. Update sc-manage README.md
2. Update CHANGELOG.md
3. Add troubleshooting guide
4. Create manual test script
5. Document in PLUGIN-STORAGE-CONVENTIONS.md (already has section)

---

## Implementation Recommendations

### Critical Decisions

**Hook file format**: Need to verify which format Claude Code uses:
- Design document specifies `~/.claude/hooks/hooks.json` with simple array format
- Existing PreToolUse hooks use `.claude/settings.json` with structured format
- **Recommendation**: Support both, check for hooks.json first, fall back to settings.json

**Error handling philosophy**: Non-blocking at all costs
- Orchestrator never fails session start
- Hook registration failure doesn't block sc-manage installation
- Plugin script failures are plugin's problem

**Testing strategy**:
- Unit tests for all logic (discovery, invocation, watchdog)
- Integration tests for end-to-end flow
- Manual test script for validation
- Cross-platform testing (Windows + Unix)

### Security Considerations

**Path traversal prevention**:
- Validate `hooks.session_start` stays within plugin directory
- Use `Path.resolve()` and check parent relationships

**Process isolation**:
- Use `start_new_session=True` to detach from parent
- Redirect stdin/stdout/stderr to DEVNULL
- Watchdog terminates orphaned processes

**Credential safety**:
- Never log secrets (validate with assert_no_secrets_logged)
- Session path may contain sensitive info (sanitize in logs)

### Known Limitations

**PID reuse**: Watchdog targets PIDs after delay; PID reuse could terminate wrong process
- Risk: Low (short-lived session-start scripts)
- Mitigation: Document limitation; consider process-group targeting in future

**Windows process termination**: Backgrounded child processes may outlive timeout
- Risk: Medium (resource leaks if plugin spawns children)
- Mitigation: Use `taskkill /T /F` (terminates process tree)

**Non-git folders**: Session path may not be a git repository
- Risk: Medium (plugins may assume git context)
- Mitigation: Design requires plugins to handle `git: "none"` case

---

## Related Files

### Design & Documentation
- `/docs/design/sc-session-start-design.md` - Complete design specification
- `/docs/PLUGIN-STORAGE-CONVENTIONS.md` - Storage conventions (includes session-start section)
- `/plans/2026-02-11-sc-logging-consolidation-plan.md` - Logging consolidation context

### Implementation Files (Existing)
- `/packages/sc-manage/manifest.yaml` - Package manifest
- `/packages/sc-manage/scripts/sc_manage_install.py` - Current installer agent script
- `/src/sc_cli/install.py` - Core installation logic
- `/tools/sc-install.py` - Installation CLI entry point
- `/.claude/settings.local.json` - Hook configuration example

### Implementation Files (To Create)
- `/packages/sc-manage/scripts/sc_session_start.py` - Orchestrator (Task #1)
- `/packages/sc-manage/scripts/sc_logging.py` - Structured logging (copy from template)
- `/packages/sc-manage/tests/test_session_start.py` - Unit tests
- `/tests/test_session_start_registration.py` - Installer tests
- `/tests/integration/test_session_start_e2e.py` - Integration tests
- `/scripts/test-session-start-manual.sh` - Manual test script

### Templates & References
- `/templates/sc-logging.jenga.py` - Structured logging template (use this)
- `/.claude/scripts/log-task-input.py` - Example hook implementation

---

## Success Criteria

### Task #1: Orchestrator Created
- ✅ `sc_session_start.py` implements complete design specification
- ✅ Discovery finds plugins in all expected locations
- ✅ Deduplication works correctly (local overrides global)
- ✅ Plugin scripts invoked with correct arguments
- ✅ Watchdog enforces 30-second timeout
- ✅ Structured logging to `~/.claude/state/logs/sc-manage/`
- ✅ All unit tests pass
- ✅ Manual testing successful on Unix and Windows

### Task #2: Hook Registration Works
- ✅ Hook registered when sc-manage installed globally
- ✅ Hook registration idempotent (no duplicates)
- ✅ Hook not registered for local installs
- ✅ Hook removed on uninstall
- ✅ Installation doesn't fail if hook registration fails
- ✅ Works with both hooks.json and settings.json formats
- ✅ All installer tests pass
- ✅ End-to-end integration test passes

### Documentation Complete
- ✅ sc-manage README.md updated
- ✅ CHANGELOG.md includes new version
- ✅ Manual test script created and validated
- ✅ Troubleshooting guide includes session-start section

---

## Questions for Clarification

1. **Hook file format**: Which format does Claude Code actually use for SessionStart hooks?
   - `~/.claude/hooks/hooks.json` with array format (per design)
   - `.claude/settings.json` with structured format (per existing PreToolUse hooks)
   - Both supported?

2. **Hook registration failure**: Should sc-manage installation fail if hook registration fails?
   - Recommendation: No (warn but continue)

3. **Uninstallation behavior**: Should uninstalling sc-manage remove the hook even if other plugins need it?
   - Recommendation: Yes (only sc-manage should register the orchestrator hook)

4. **Cross-platform testing**: What Windows environments need to be tested?
   - Windows 10/11 with Python 3.8+?

5. **Python version support**: What's the minimum Python version?
   - Recommendation: Python 3.8+ (for subprocess.Popen features)

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-13 | 1.0 | Initial requirements document created |

