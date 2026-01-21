# sc-delay-tasks Troubleshooting Guide

This guide helps diagnose and resolve common issues with the sc-delay-tasks package for Synaptic Canvas.

## Quick Diagnostics

Run these commands to verify your setup:

```bash
# Verify Python 3 is available
python3 --version

# Check if sc-delay-tasks is installed (global)
ls -la ~/Documents/.claude/commands/delay.md
ls -la ~/Documents/.claude/scripts/sc-delay-run.py

# Check if sc-delay-tasks is installed (local)
ls -la .claude/commands/delay.md
ls -la .claude/scripts/sc-delay-run.py

# Test the delay script directly
python3 .claude/scripts/sc-delay-run.py --seconds 10 --action "test"

# Check agent registry (if applicable)
cat .claude/agents/registry.yaml | grep delay
```

## Common Issues

### 1. Command Not Found: `/delay` Not Recognized

**Problem:** When you run `/delay`, Claude doesn't recognize the command.

**Symptoms:**
```
Unknown command: /delay
```

**Root Causes:**
- Package not installed in the correct scope
- Installation path incorrect
- Claude not detecting `.claude/commands/` directory

**Resolution:**

1. Verify installation location:
```bash
# For global use
ls ~/Documents/.claude/commands/delay.md

# For local use (inside repo)
ls .claude/commands/delay.md
```

2. If missing, reinstall:
```bash
# Global install
python3 tools/sc-install.py install sc-delay-tasks --dest ~/Documents/.claude

# Local install
python3 tools/sc-install.py install sc-delay-tasks --dest ./.claude
```

3. Restart Claude or refresh the command index.

**Prevention:**
- Always verify installation scope matches your usage pattern
- Use global install for commands you want available everywhere

---

### 2. Python3 Not Found or Wrong Version

**Problem:** The delay script fails because Python 3 is not available.

**Symptoms:**
```
python3: command not found
```
or
```
SyntaxError: invalid syntax (modern Python features)
```

**Root Causes:**
- Python 3 not installed
- Python 3 not in PATH
- Python version too old (requires >= 3.8)

**Resolution:**

1. Check Python version:
```bash
python3 --version
```

2. If not found or version < 3.8, install/upgrade Python:

**macOS:**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.12
```

**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- Ensure "Add to PATH" is checked during installation

3. Verify PATH:
```bash
which python3
echo $PATH
```

4. If installed but not in PATH, add to your shell profile:
```bash
# For bash (~/.bashrc or ~/.bash_profile)
export PATH="/usr/local/bin:$PATH"

# For zsh (~/.zshrc)
export PATH="/usr/local/bin:$PATH"
```

**Prevention:**
- Keep Python 3.8+ in your PATH
- Use `python3` explicitly (not `python`)

---

### 3. Polling Not Triggering: Interval Too Short

**Problem:** Polling delays fail with validation errors.

**Symptoms:**
```json
{
  "success": false,
  "error": {
    "code": "validation.interval",
    "message": "Interval too short"
  }
}
```

**Root Causes:**
- Interval set below minimum 60 seconds
- Misunderstanding of interval units (seconds vs minutes)

**Resolution:**

1. Check your command parameters:
```bash
# WRONG - interval too short
/delay --poll --every 30 --for 5m

# CORRECT - minimum 60 seconds
/delay --poll --every 60 --for 5m
```

2. For delays under 60 seconds, use `--once`:
```bash
/delay --once --seconds 30 --action "quick check"
```

3. Verify interval calculation:
```bash
# Test with minimal valid parameters
python3 .claude/scripts/sc-delay-run.py --every 60 --attempts 1
```

**Prevention:**
- Always use intervals >= 60 seconds for polling
- For sub-minute delays, use one-shot mode (`--once`)
- Remember: `--every` is in seconds, not minutes

---

### 4. Agent Timeout or Delegation Issues

**Problem:** Delay agent times out or fails to delegate properly.

**Symptoms:**
```
Agent execution timeout after 120s
Task delegation failed: no response from delay-poll agent
```

**Root Causes:**
- Total duration exceeds agent timeout limits
- Background shell not properly maintained
- Claude task system timeout (default 2-minute limit)

**Resolution:**

1. Ensure total duration doesn't exceed 12 hours:
```bash
# Check maximum duration
python3 -c "print(12 * 60 * 60)"  # 43200 seconds max
```

2. Use bounded attempts for long polls:
```bash
# WRONG - might exceed timeout
/delay --poll --every 60 --for 180m

# BETTER - bounded attempts
/delay --poll --every 60 --attempts 10
```

3. For long-running delays, delegate properly:
```bash
# Use background execution via Bash tool with run_in_background
# The delay-poll agent should handle this automatically
```

4. Check if delay script completes successfully:
```bash
# Test manually
python3 .claude/scripts/sc-delay-run.py --every 60 --attempts 2
# Should emit heartbeats and complete
```

**Prevention:**
- Keep polling durations reasonable (< 30 minutes for interactive use)
- Use explicit `--attempts` for predictable behavior
- For very long delays, consider breaking into smaller chunks

---

### 5. Duration Validation Errors

**Problem:** Duration is rejected as "too short" or "too long".

**Symptoms:**
```
Duration too short
Duration too long
```

**Root Causes:**
- Duration < 10 seconds (minimum threshold)
- Duration > 12 hours (maximum threshold)
- Invalid duration format

**Resolution:**

1. Respect minimum duration (10 seconds):
```bash
# WRONG - too short
/delay --once --seconds 5

# CORRECT
/delay --once --seconds 10
```

2. Respect maximum duration (12 hours):
```bash
# WRONG - exceeds 43200 seconds
/delay --once --minutes 800

# CORRECT - within limits
/delay --once --minutes 720  # 12 hours
```

3. Check duration format for polling:
```bash
# Valid formats: Xs (seconds) or Xm (minutes)
/delay --poll --every 60 --for 5m   # CORRECT
/delay --poll --every 60 --for 300s # CORRECT
/delay --poll --every 60 --for 5h   # WRONG - 'h' not supported
```

**Prevention:**
- Always use 10s minimum, 12h maximum
- Use format `Xs` or `Xm` for `--for` parameter
- Test with `delay-run.py` directly for validation

---

### 6. Environment Variable Issues

**Problem:** Script fails due to missing or incorrect environment variables.

**Symptoms:**
```
NameError: name 'sys' is not defined
ImportError: cannot import name 'main' from 'sc_cli.delay_run'
```

**Root Causes:**
- Python path not set correctly
- Script installed without proper structure
- Using script from wrong location

**Resolution:**

1. Verify script location and structure:
```bash
# Script should exist at this path
ls -la .claude/scripts/sc-delay-run.py

# Check if src directory exists (for in-repo usage)
ls -la src/sc_cli/delay_run.py
```

2. If using from repo root, ensure `src/` directory is accessible:
```bash
# The script adds src/ to sys.path automatically
# Verify repo structure:
tree -L 2 -d .
```

3. For standalone installations, the script must be executable:
```bash
chmod +x .claude/scripts/sc-delay-run.py
```

4. Test import manually:
```bash
cd /path/to/repo
python3 -c "import sys; sys.path.insert(0, 'src'); from sc_cli.delay_run import main; print('OK')"
```

**Prevention:**
- Install via `sc-install.py` (handles permissions automatically)
- Don't manually move script files
- Keep repo structure intact if running in-repo

---

### 7. Background Shell Problems

**Problem:** Polling delays don't emit heartbeats or appear "stuck".

**Symptoms:**
- No "Waiting X minutes..." output during polling
- Agent appears frozen
- Terminal shows no activity

**Root Causes:**
- Output buffering in background shells
- Shell output not being captured properly
- Process not actually running

**Resolution:**

1. Test script output directly (not via agent):
```bash
# Should emit heartbeats every 60 seconds
python3 .claude/scripts/sc-delay-run.py --every 60 --attempts 2
```

2. If output missing, check for output buffering:
```bash
# Force unbuffered output
python3 -u .claude/scripts/sc-delay-run.py --every 60 --attempts 2
```

3. For background execution via Claude, verify Bash tool usage:
```bash
# Check if shell is running
ps aux | grep delay-run
```

4. Review agent output for errors:
```bash
# Check if agent reported execution errors
cat .claude/agents/delay-poll.md | grep -A5 "Constraints"
```

**Prevention:**
- Use explicit `--attempts` to ensure bounded execution
- Monitor first heartbeat to confirm execution started
- For long polls, check process status periodically

---

### 8. Invalid Time Format for `--until`

**Problem:** The `--until` parameter rejects your time format.

**Symptoms:**
```
invalid --until format
--until must be in the future
```

**Root Causes:**
- Incorrect time format
- Time already in the past
- Timezone confusion

**Resolution:**

1. Use valid time formats:

**HH:MM format (24-hour):**
```bash
/delay --once --until 14:30 --action "afternoon task"
/delay --once --until 09:00:00 --action "morning task"
```

**ISO 8601 format:**
```bash
/delay --once --until "2025-12-02T15:30:00" --action "specific datetime"
```

2. Ensure time is in the future:
```bash
# Check current time first
date

# If it's 14:00 now, this will fail:
/delay --once --until 13:00

# This will work (next occurrence of 13:00 is tomorrow):
/delay --once --until 13:00  # Rolls to next day automatically
```

3. For same-day future time:
```bash
# If it's 10:00 AM, schedule for 3:00 PM today
/delay --once --until 15:00 --action "end of day task"
```

**Prevention:**
- Use 24-hour format to avoid AM/PM confusion
- Verify current time before scheduling
- Use ISO format for precise datetime control

---

## Installation & Setup Issues

### Package Not Found During Installation

**Problem:**
```bash
python3 tools/sc-install.py install sc-delay-tasks --dest ~/.claude
# Package not found: sc-delay-tasks
```

**Resolution:**

1. Verify you're in the repository root:
```bash
# Should show packages/sc-delay-tasks/
ls packages/
```

2. Check package directory exists:
```bash
ls -la packages/sc-delay-tasks/manifest.yaml
```

3. If missing, clone/update repository:
```bash
git pull origin main
```

---

### Destination Path Issues

**Problem:**
```bash
python3 tools/sc-install.py install sc-delay-tasks --dest ~/Documents
# --dest must point to a .claude directory
```

**Resolution:**

Always include `.claude` in destination:
```bash
# WRONG
--dest ~/Documents

# CORRECT
--dest ~/Documents/.claude
```

---

### Permission Denied Errors

**Problem:**
```bash
Permission denied: '/Users/username/Documents/.claude/scripts/sc-delay-run.py'
```

**Resolution:**

1. Fix script permissions:
```bash
chmod +x ~/.claude/scripts/sc-delay-run.py
```

2. Fix directory permissions:
```bash
chmod -R u+rwX ~/.claude/
```

3. If system-level issues:
```bash
# Check directory ownership
ls -la ~/Documents/.claude

# Fix if needed (replace username)
sudo chown -R username:staff ~/Documents/.claude
```

---

## Configuration Issues

### Missing Action Text

**Problem:** Delay completes but action text is unclear or missing.

**Resolution:**

Always specify meaningful action text:
```bash
# WRONG - no context
/delay --once --minutes 5

# BETTER
/delay --once --minutes 5 --action "check build status"

# If you don't want action output
/delay --once --minutes 5 --suppress-action
```

---

### Incorrect Interval Units

**Problem:** Confusion between seconds and minutes.

**Resolution:**

Understand unit specifications:
```bash
# --seconds: always in seconds
/delay --once --seconds 120  # 2 minutes

# --minutes: always in minutes
/delay --once --minutes 2    # 2 minutes

# --every: always in seconds
/delay --poll --every 120 --attempts 3  # Poll every 2 minutes

# --for: specify unit explicitly
/delay --poll --every 60 --for 10m  # 10 minutes total
/delay --poll --every 60 --for 600s # 600 seconds total
```

---

## Integration Issues

### Using with CI/CD Systems

**Problem:** Delays in CI pipelines behave unexpectedly.

**Resolution:**

1. Use explicit timeouts in CI:
```yaml
# GitHub Actions example
- name: Wait for deployment
  timeout-minutes: 15
  run: |
    python3 .claude/scripts/sc-delay-run.py --every 60 --attempts 10
```

2. Avoid interactive features in CI:
```bash
# WRONG - relies on Claude agent
/delay --poll --every 60 --for 10m

# CORRECT - direct script usage
python3 .claude/scripts/sc-delay-run.py --every 60 --for 10m
```

---

### Using with Other Synaptic Canvas Packages

**Problem:** Conflicts with sc-git-worktree or other packages.

**Resolution:**

1. Ensure compatible scopes:
```bash
# sc-delay-tasks can be global or local
# Install globally for use in all repos
python3 tools/sc-install.py install sc-delay-tasks --dest ~/Documents/.claude
```

2. For PR check delays with sc-git-worktree:
```bash
# Both packages should be installed locally in the repo
python3 tools/sc-install.py install sc-delay-tasks --dest ./.claude
python3 tools/sc-install.py install sc-git-worktree --dest ./.claude
```

---

## Performance & Timeout Issues

### Large Number of Polling Attempts

**Problem:** Polling with many attempts causes memory issues or hangs.

**Resolution:**

1. Limit attempts to reasonable values:
```bash
# AVOID - 1000 attempts might take hours
/delay --poll --every 60 --attempts 1000

# BETTER - bounded to 30 minutes
/delay --poll --every 60 --attempts 30
```

2. Break long delays into chunks:
```bash
# Instead of one 3-hour delay
# Use multiple shorter delays with checks in between
```

---

### Heartbeat Frequency

**Problem:** Too many or too few heartbeat messages.

**Explanation:**
- Heartbeats emit every 60 seconds for minute-based waits
- For sub-minute waits, one heartbeat at the start
- This is by design to avoid spam

**Workaround:**

If you need finer-grained progress:
```python
# Modify the script locally (not recommended)
# Or check process status externally
ps aux | grep delay-run
```

---

## Platform-Specific Issues

### macOS Issues

**Problem:** `stat` command format differs.

**Resolution:**

The delay script doesn't use `stat`, but if you see errors in related tools:
```bash
# macOS uses different stat syntax
stat -f%z file.txt  # macOS
stat -c%s file.txt  # Linux
```

---

### Windows Issues

**Problem:** Windows paths and Python invocation differ.

**Resolution:**

1. Use forward slashes or escape backslashes:
```bash
# WRONG
python3 .claude\scripts\delay-run.py

# CORRECT
python3 .claude/scripts/sc-delay-run.py
```

2. Ensure Python is in PATH:
```cmd
# Test in Command Prompt
python3 --version

# Or use py launcher
py -3 --version
```

3. Use WSL for better compatibility:
```bash
# Install WSL2 and use Linux-style paths
wsl python3 .claude/scripts/sc-delay-run.py --seconds 10
```

---

### Linux Issues

**Problem:** Different Python installations.

**Resolution:**

1. Use correct Python binary:
```bash
# Try different aliases
which python3
which python3.8
which python3.12

# Create alias if needed
alias python3='/usr/bin/python3.12'
```

2. For Ubuntu/Debian:
```bash
# Install python3 if missing
sudo apt update
sudo apt install python3 python3-pip
```

---

## Getting Help

### When to Escalate

Escalate to GitHub issues if you encounter:

- Validation errors that seem incorrect
- Script crashes with Python tracebacks
- Unexpected behavior in polling loops
- Integration issues with Claude Code agents

### How to Report Bugs

Include the following information:

1. **Environment details:**
```bash
python3 --version
uname -a  # or systeminfo on Windows
echo $SHELL
```

2. **Installation details:**
```bash
ls -la .claude/commands/delay.md
ls -la .claude/scripts/sc-delay-run.py
cat .claude/agents/registry.yaml | grep delay
```

3. **Command that failed:**
```bash
# Exact command and parameters
/delay --poll --every 60 --for 5m --action "test"
```

4. **Error output:**
```
# Full error message including JSON output
```

5. **Reproduction steps:**
```
1. Install sc-delay-tasks to local repo
2. Run /delay --poll --every 60 --attempts 5
3. Observe error: ...
```

### Debug Information to Collect

**Basic diagnostics:**
```bash
# Python version
python3 --version

# Script exists and is executable
ls -la .claude/scripts/sc-delay-run.py

# Test script directly
python3 .claude/scripts/sc-delay-run.py --seconds 10 --action "debug test"

# Check agent registry
cat .claude/agents/registry.yaml
```

**For polling issues:**
```bash
# Test minimal polling
python3 .claude/scripts/sc-delay-run.py --every 60 --attempts 1

# Verify heartbeat output
python3 -u .claude/scripts/sc-delay-run.py --every 60 --attempts 2 | cat -v
```

**For agent delegation issues:**
```bash
# Check agent file exists
ls -la .claude/agents/delay-poll.md

# Verify agent version
grep "version:" .claude/agents/delay-poll.md
```

---

## FAQ

### Q: What's the difference between `--once` and `--poll`?

**A:**
- `--once`: Single delay, then emit action (one-shot timer)
- `--poll`: Repeated delays with heartbeats (bounded loop)

Use `--once` for simple delays. Use `--poll` for waiting with periodic checks.

---

### Q: Can I use delays shorter than 60 seconds?

**A:**
- Yes, for `--once` mode (minimum 10 seconds)
- No, for `--poll` mode (minimum 60 seconds to avoid busy-waiting)

---

### Q: Why is there a 12-hour maximum?

**A:** To prevent runaway delays and resource consumption. For longer waits, consider:
- Breaking into multiple delays
- Using system-level scheduling (cron, systemd timers)
- Revisiting your workflow design

---

### Q: Can I cancel a running delay?

**A:**
- If running in terminal: Ctrl+C
- If delegated to agent: Use Claude's task cancellation
- Background shells: Find and kill the process:
```bash
ps aux | grep delay-run
kill <PID>
```

---

### Q: How do I use delays in PR workflows?

**A:** Use the `git-pr-check-delay` agent:
```bash
# This agent uses delay-poll internally
# Configure in your workflow to poll PR status
```

See `packages/sc-delay-tasks/agents/git-pr-check-delay.md` for details.

---

### Q: Can I customize heartbeat messages?

**A:** No, heartbeat format is standardized. But you can:
- Parse output programmatically
- Suppress action with `--suppress-action`
- Check process status externally

---

### Q: What happens if my system sleeps during a delay?

**A:**
- Python's `time.sleep()` continues after wake
- Total elapsed time includes sleep duration
- For critical timing, use `--until` with absolute times

---

### Q: Can I run multiple delays in parallel?

**A:** Yes:
```bash
# In separate terminals or background shells
python3 .claude/scripts/sc-delay-run.py --every 60 --attempts 5 &
python3 .claude/scripts/sc-delay-run.py --every 120 --attempts 3 &
```

Each runs independently.

---

### Q: How do I update sc-delay-tasks?

**A:**
```bash
# Uninstall old version
python3 tools/sc-install.py uninstall sc-delay-tasks --dest ~/.claude

# Pull latest changes
git pull origin main

# Reinstall
python3 tools/sc-install.py install sc-delay-tasks --dest ~/.claude
```

---

## Additional Resources

- **Package README:** `packages/sc-delay-tasks/README.md`
- **Use Cases:** `packages/sc-delay-tasks/USE-CASES.md`
- **Changelog:** `packages/sc-delay-tasks/CHANGELOG.md`
- **Agent Specifications:**
  - `packages/sc-delay-tasks/agents/delay-once.md`
  - `packages/sc-delay-tasks/agents/delay-poll.md`
  - `packages/sc-delay-tasks/agents/git-pr-check-delay.md`
- **Repository:** https://github.com/randlee/synaptic-canvas
- **Issues:** https://github.com/randlee/synaptic-canvas/issues
