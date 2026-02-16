# Agent Teams Best Practices

> Practical patterns and anti-patterns for building reliable multi-agent systems in Claude Code

## Table of Contents

- [Architecture Patterns](#architecture-patterns)
- [Common Pitfalls](#common-pitfalls)
- [Spawn Gating](#spawn-gating)
- [Lifecycle Management](#lifecycle-management)
- [Resource Management](#resource-management)
- [Operational Notes](#operational-notes)

---

## Architecture Patterns

### Long-Running PM with Sprint-Based Orchestrators

**Goal**: PM manages multiple project phases, delegating each sprint to a fresh orchestrator agent.

```
┌─────────────────────────────────────────────────────────┐
│ PM (Team Lead)                                          │
│ - Long-running, manages entire project lifecycle       │
│ - Creates one scrum-master per sprint                  │
│ - Provides fresh context for each sprint               │
└─────────────────────────────────────────────────────────┘
                        │
                        │ spawn named teammate
                        ▼
        ┌───────────────────────────────┐
        │ Scrum-Master (Named Teammate) │
        │ - Orchestrates single sprint  │
        │ - Spawns dev + QA workers     │
        │ - Completes before context    │
        └───────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            │                       │
            ▼                       ▼
    ┌──────────────┐        ┌──────────────┐
    │ Dev Worker   │        │ QA Worker    │
    │ (Background) │        │ (Background) │
    └──────────────┘        └──────────────┘
```

**Key Principles**:
- **PM = Team Lead**: Only the PM can create named teammates
- **Orchestrators = Named Teammates**: Need full lifecycle (compaction, messaging)
- **Workers = Background Agents**: Short-lived, task-specific, no sub-agents

---

## Common Pitfalls

### Pitfall 1: Background Orchestrators Can't Spawn Subagents

**Symptom**: PM creates scrum-master as background agent (`run_in_background=true`). Scrum-master silently does all work itself instead of spawning dev/QA workers.

**Why It Fails**:
- Background agents cannot spawn subagents
- Agent doesn't complain, just adapts by doing the work
- PM accepts this as "agent-teams just doesn't work"

**The Problem**:
```python
# ❌ WRONG: Background orchestrator
Task(
    subagent_type="scrum-master",
    run_in_background=true,  # Can't spawn subagents!
    prompt="Orchestrate dev/QA loop..."
)
```

**The Fix**:
```python
# ✅ CORRECT: Named teammate orchestrator
Task(
    subagent_type="scrum-master",
    team_name="sprint-1",
    name="scrum-master",  # Named teammate!
    prompt="Orchestrate dev/QA loop..."
)
```

### Pitfall 2: Named Teammates Creating More Named Teammates

**Symptom**: Scrum-master (named teammate) tries to spawn dev/QA as named teammates. Exhausts tmux sessions (3 scrum-masters × 2 teammates each = 9 panes). PM concludes "named teammates are just background agents with messaging."

**Why It Fails**:
- Only team lead should create named teammates
- Named teammates should spawn background workers
- Resource exhaustion: Too many tmux sessions

**The Problem**:
```python
# ❌ WRONG: Named teammate trying to create more named teammates
# (Running inside scrum-master agent)
Task(
    subagent_type="rust-developer",
    team_name="sprint-1",  # Teammate can't use team_name!
    name="dev-1",
    prompt="Implement feature..."
)
```

**The Fix**:
```python
# ✅ CORRECT: Named teammate spawns background workers
# (Running inside scrum-master agent)
Task(
    subagent_type="rust-developer",
    run_in_background=true,  # Background, no team_name!
    prompt="Implement feature..."
)
```

### Pitfall 3: Assuming Teammates Can See Your Output

**Symptom**: Lead writes instructions in the main session, but teammates never respond or act on them.

**Why It Fails**:
- Teammates cannot "see" your normal text output
- Only messages sent via the `SendMessage` tool are delivered
- Messages auto-deliver; no inbox polling is required

**The Fix**:
```python
SendMessage(
    team_name="project-team",
    name="scrum-master",
    type="message",
    content="Please orchestrate sprint 1 with dev/QA workers."
)
```

---

## Spawn Gating

### Understanding Agent Spawning Patterns

Before discussing gating, understand the three ways to spawn agents:

#### Named Teammate (Full Lifecycle)
```python
Task(
    subagent_type="scrum-master",
    name="sm-sprint-1",           # ← Makes it a named teammate
    team_name="project-team",     # ← Adds to team
    prompt="Coordinate sprint 1"
)
```
- Creates tmux pane (or in-process teammate)
- Full lifecycle (compaction, messaging, proper shutdown)
- Part of team, visible in team config
- **Use for**: Orchestrators that need to survive long tasks

#### Background Agent (Lightweight Sidechain)
```python
Task(
    subagent_type="rust-developer",
    run_in_background=true,        # ← Runs in background
    # NO name parameter              ← Not a teammate
    # NO team_name parameter         ← Not part of team
    prompt="Implement feature X"
)
```
- No tmux pane, runs as sidechain process
- Dies at context limit (no compaction)
- Not part of team, not visible in team config
- **Use for**: Short-lived workers that complete quickly

#### Key Differences

| Feature | Named Teammate | Background Agent |
|---------|----------------|------------------|
| `name` parameter | ✓ Required | ✗ Not allowed |
| `team_name` parameter | ✓ Required | ✗ Not allowed |
| `run_in_background` | ✗ Not used | ✓ Required |
| Tmux pane | ✓ Yes | ✗ No |
| Context compaction | ✓ Yes | ✗ No |
| Can receive messages | ✓ Yes | ✗ No |
| Resource cost | High | Low |

### Why Gating Is Needed

Without constraints:
- **Resource exhaustion**: Multiple orchestrators create multiple named teammates
- **Lifecycle issues**: Background agents without names can't compact, die at context limit
- **Architecture violations**: Teammates spawning teammates breaks hierarchy

### The Solution: PreToolUse Hook on Task Tool

**Hook enforces two rules**:
1. **Orchestrators must be named teammates** (need full lifecycle/compaction)
2. **Only team lead can use `team_name` parameter** (prevents teammates from creating teammates)

### Implementation

#### 1. Hook Configuration

**File**: `.claude/settings.json` (or `.claude/settings.local.json` for testing)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/scripts/gate-agent-spawns.py"
          }
        ]
      }
    ]
  }
}
```

**Important**: Must be in `settings.json`, NOT agent frontmatter. Agent frontmatter hooks don't work in Claude Code **tmux mode** (they work in-process, but not when teammates spawn in separate tmux panes). Settings.json PreToolUse hooks work universally across all teammate modes.

#### 2. Gate Script (Production Implementation)

**File**: `.claude/scripts/gate-agent-spawns.py`

**Source**: Copied from `agent-team-mail` (production-tested, enforces both rules)

```python
#!/usr/bin/env python3
"""PreToolUse hook that enforces safe agent spawning patterns for orchestrators.

## Why This Exists

The scrum-master agent acts as an ORCHESTRATOR — it coordinates sprints by
spawning dev and QA sub-agents to do the actual work. Without this gate,
orchestrators can accidentally spawn agents incorrectly, leading to:

1. Resource exhaustion: Each named teammate = tmux pane. 3 scrum-masters each
   spawning 2 named teammates = 9 panes. With background agents = 3 panes.

2. Lifecycle issues: Background agents without names can't compact and die at
   context limit. Orchestrators need full teammate status to survive long sprints.

This gate enforces two rules:
- Rule 1: Orchestrators (scrum-master, project-manager) MUST be named teammates
- Rule 2: Only the team LEAD can create named teammates (not orchestrators themselves)

## Mode Compatibility

Works with both in-process and tmux teammates because it uses PreToolUse hooks
in settings.json (fires for ALL Task calls) and session_id differentiation
(present in both modes). See Reddit post for mode differences:
https://www.reddit.com/r/ClaudeCode/comments/1qzypcs/playing_around_with_the_new_agent_teams_experiment/

NOTE: Agent-teams is pre-release as of 2/11/2026. Verified on Claude Code v2.1.39+.

Exit codes: 0 = Allow, 2 = Block
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Orchestrator agents that require full teammate lifecycle
ORCHESTRATORS = {"scrum-master", "project-manager"}


def log_event(event_type: str, data: dict, extra: dict = None) -> None:
    """Log hook event to SC standard location.

    Logs exactly one structured message per hook invocation.
    """
    log_dir = Path.cwd() / ".claude" / "state" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "gate-agent-spawns.jsonl"

    tool_input = data.get("tool_input", {})
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "session_id": data.get("session_id", ""),
        "subagent_type": tool_input.get("subagent_type", ""),
        "name": tool_input.get("name", ""),
        "team_name": tool_input.get("team_name", ""),
        "run_in_background": tool_input.get("run_in_background", False),
    }

    # Add agentId if available (from spawned agent)
    if extra and "agent_id" in extra:
        log_entry["agent_id"] = extra["agent_id"]

    # Add block reason if this is a block event
    if extra and "reason" in extra:
        log_entry["reason"] = extra["reason"]
        log_entry["rule"] = extra.get("rule", "")

    try:
        with log_file.open("a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass  # Don't fail hook on logging errors


def get_lead_session_id(team_name: str) -> str | None:
    """Get team lead's session ID to differentiate lead from teammates.

    Returns None if team doesn't exist (allows by default).
    """
    if not team_name or not team_name.strip():
        return None

    config_path = Path.home() / ".claude" / "teams" / team_name / "config.json"
    if not config_path.exists():
        return None

    try:
        config = json.loads(config_path.read_text())
        return config.get("leadSessionId")
    except Exception:
        return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        # Can't parse input - allow by default (fail open)
        return 0

    tool_input = data.get("tool_input", {})
    subagent_type = tool_input.get("subagent_type", "")
    teammate_name = tool_input.get("name", "")  # If present, spawns named teammate
    team_name = tool_input.get("team_name", "")  # If present, spawns into team
    session_id = data.get("session_id", "")

    # Rule 1: Orchestrators must be spawned with teammate_name
    # WHY: They need full lifecycle (compaction, proper shutdown) to coordinate
    # long-running sprints. Background agents die at context limit.
    if subagent_type in ORCHESTRATORS and not teammate_name:
        log_event("agent_spawn_blocked", data, {
            "reason": f"Orchestrator '{subagent_type}' requires name parameter",
            "rule": "Rule 1: Orchestrators must be named teammates"
        })
        sys.stderr.write(
            f"BLOCKED: '{subagent_type}' is an orchestrator and must be a named teammate.\n"
            f"\n"
            f"Correct:\n"
            f'  Task(subagent_type="{subagent_type}", name="sm-sprint-X", team_name="<team>", ...)\n'
            f"\n"
            f"Wrong:\n"
            f'  Task(subagent_type="{subagent_type}", run_in_background=true)  # no name = dies at context limit\n'
        )
        return 2

    # Rule 2: Only team LEAD can spawn agents with team_name
    # WHY: Prevents orchestrators from creating teammates (pane exhaustion).
    # Orchestrators should spawn background agents (no team_name, no teammate_name).
    if team_name and str(team_name).strip():
        lead_session_id = get_lead_session_id(team_name)

        # Allow if we can't determine lead (no team config yet)
        # WHY: Fail open - team might be new, don't block legitimate spawns
        if not lead_session_id:
            return 0

        # Allow if caller IS the team lead
        # WHY: Lead creates the orchestrators, needs team_name to add them to team
        if session_id == lead_session_id:
            return 0

        # Block: caller is a teammate trying to use team_name
        # WHY: Teammates spawning teammates = pane explosion
        log_event("agent_spawn_blocked", data, {
            "reason": "Teammate attempted to spawn agent with team_name",
            "rule": "Rule 2: Only team lead can create named teammates"
        })
        sys.stderr.write(
            f"BLOCKED: Only the team lead can spawn agents with team_name.\n"
            f"\n"
            f"You are a teammate. Use background agents:\n"
            f'  Task(subagent_type="...", run_in_background=true, prompt="...")  # no team_name\n'
            f"\n"
            f"NOT allowed from teammates:\n"
            f'  Task(..., team_name="{team_name}", ...)  # creates named teammate = pane exhaustion\n'
        )
        return 2

    # Allow: All checks passed
    # WHY: Either spawning non-orchestrator, or spawning background agent (no team_name)
    log_event("agent_spawn_allowed", data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**What This Enforces**:
- ✅ **Rule 1**: Orchestrators MUST have a `name` parameter (full lifecycle)
- ✅ **Rule 2**: Only team lead can use `team_name` parameter (prevents pane explosion)
- ✅ Session ID differentiation (team lead vs teammates)
- ✅ Fails open on parse errors (doesn't break workflow)
- ✅ Structured logging to `.claude/state/logs/gate-agent-spawns.jsonl`
- ✅ Clear error messages with correct vs incorrect examples

### Logging

The gate logs exactly **one structured event per hook invocation** to `.claude/state/logs/gate-agent-spawns.jsonl`:

**Success Events** (`agent_spawn_allowed`):
```json
{
  "timestamp": "2026-02-11T10:30:45.123456",
  "event": "agent_spawn_allowed",
  "session_id": "abc123...",
  "subagent_type": "scrum-master",
  "name": "sm-sprint-1",
  "team_name": "project-alpha",
  "run_in_background": false
}
```

**Block Events** (`agent_spawn_blocked`):
```json
{
  "timestamp": "2026-02-11T10:31:12.789012",
  "event": "agent_spawn_blocked",
  "session_id": "def456...",
  "subagent_type": "scrum-master",
  "name": "",
  "team_name": "",
  "run_in_background": true,
  "reason": "Orchestrator 'scrum-master' requires name parameter",
  "rule": "Rule 1: Orchestrators must be named teammates"
}
```

**View Logs**:
```bash
# Watch in real-time
tail -f .claude/state/logs/gate-agent-spawns.jsonl | jq .

# Count blocks vs allows
grep agent_spawn_blocked .claude/state/logs/gate-agent-spawns.jsonl | wc -l
grep agent_spawn_allowed .claude/state/logs/gate-agent-spawns.jsonl | wc -l

# See all Rule 2 violations (teammates trying to spawn teammates)
jq 'select(.rule == "Rule 2: Only team lead can create named teammates")' \
  .claude/state/logs/gate-agent-spawns.jsonl
```

### Verification

**Test Cases**:

| Scenario | Caller | team_name | name | run_in_background | Rule | Result |
|----------|--------|-----------|------|-------------------|------|--------|
| Team lead → orchestrator | Lead | ✓ | ✓ | ✗ | Both pass | ✅ Allow |
| Team lead → background worker | Lead | ✗ | ✗ | ✓ | N/A | ✅ Allow |
| Teammate → background worker | Teammate | ✗ | ✗ | ✓ | N/A | ✅ Allow |
| Teammate → named teammate | Teammate | ✓ | ✓ | ✗ | Rule 2 | ❌ Block |
| Orchestrator as background | Either | ✗ | ✗ | ✓ | Rule 1 | ❌ Block |
| Team lead → multiple orchestrators | Lead | ✓ | ✓ | ✗ | Allowed | ✅ Allow |

**Tested On**:
- Claude Code v2.1.39+
- Settings.json PreToolUse hooks work with both in-process and tmux teammate modes
- **Note**: Agent frontmatter hooks only work for in-process teammates, NOT in tmux mode

### Key Insight: Session ID Differentiation

The gate script uses `session_id` to distinguish team lead from teammates:

```python
# Get team lead's session ID from team config
config_path = Path.home() / ".claude" / "teams" / team_name / "config.json"
config = json.loads(config_path.read_text())
lead_session_id = config.get("leadSessionId")

# Compare caller's session_id with team lead
if session_id == lead_session_id:
    # This is team lead - can create named teammates
    return 0  # Allow
else:
    # This is a teammate - can only create background agents
    return 2  # Block
```

**Why This Works**:
- Team lead has `session_id == leadSessionId` in team config
- Teammates have different session IDs
- Present in both in-process and tmux modes
- Prevents pane explosion from teammates spawning teammates

---

## Lifecycle Management

### Named Teammates vs Background Agents

| Feature | Named Teammate | Background Agent |
|---------|----------------|------------------|
| **Can spawn subagents** | ✓ Yes | ✗ No |
| **Context compaction** | ✓ Yes | ✗ No |
| **Can receive messages** | ✓ Yes | ✗ No |
| **Lifecycle management** | Full | Limited |
| **Resource cost** | High (tmux pane) | Low (async) |
| **Use case** | Orchestrators | Workers |

### Team Lifecycle Safety

**Rule**: `TeamDelete` requires all teammates to be shut down first.

**Recommended sequence**:
1. Send a shutdown request to each teammate
2. Wait for shutdown approval/ack
3. Call `TeamDelete`

**Example**:
```python
SendMessage(
    team_name="project-team",
    name="scrum-master",
    type="shutdown_request",
    content="Please finish and shut down."
)

# Wait for teammate to confirm shutdown, then:
TeamDelete(team_name="project-team")
```

### When to Use Each

**Named Teammates** (use `team_name` + `name`):
- ✓ Orchestrators (scrum-master, project-manager)
- ✓ Long-running coordinators
- ✓ Agents that spawn subagents
- ✓ Agents that need messaging
- ✓ Agents that may hit context limits

**Background Agents** (use `run_in_background=true`):
- ✓ Short-lived workers (dev, QA, researcher)
- ✓ Task-specific agents
- ✓ Agents that don't spawn subagents
- ✓ Parallel execution

---

## Resource Management

### Tmux Session Limits

**Problem**: Each named teammate requires a tmux pane. Too many teammates exhaust available sessions.

**Example Calculation**:
```
1 PM (team lead)
  → 3 scrum-masters (named teammates)
    → 2 dev/QA each (named teammates)
= 1 + 3 + (3 × 2) = 10 tmux panes
```

**Solution**: Only orchestrators should be named teammates. Workers should be background agents:
```
1 PM (team lead)
  → 3 scrum-masters (named teammates)
    → 2 dev/QA each (background agents)
= 1 + 3 = 4 tmux panes
```

### Context Management

**Named Teammates**:
- Can compact context when approaching limits
- Continue across context boundaries
- Higher resource cost, but more resilient

**Background Agents**:
- Die at context limit (no compaction)
- Must complete within initial context window
- Lower resource cost, but less resilient

**Best Practice**: Size your agents appropriately:
- **Orchestrators**: Expected to run long → named teammate
- **Workers**: Expected to complete quickly → background agent

---

## Operational Notes

### Background Agent Result Retrieval

**Rule**: `Task` returns a `task_id` when `run_in_background=true`. Use `TaskOutput` to retrieve results.

**Example**:
```python
result = Task(
    subagent_type="rust-developer",
    run_in_background=true,
    prompt="Implement feature X and report status."
)

output = TaskOutput(task_id=result.task_id, block=true)
```

### Teammate Mode Detection

**Default behavior**:
- If `$TMUX` is set, teammates run in tmux mode
- If `$TMUX` is unset, teammates run in-process

**Force tmux**:
```bash
claude --teammate-mode tmux
```

**Why tmux matters**:
- In-process teammates cannot compact
- In-process teammates die at context limit
- Use tmux for any non-trivial orchestration work

### Nested Teams Are Forbidden

**Rule**: Teammates should not create **named teammates** or new **teams**. They should spawn **background subagents** for the work they oversee.

**Pattern**:
- Lead spawns named orchestrators
- Orchestrators spawn background workers

**Anti-pattern**:
- Orchestrator uses `team_name` or `name` to create additional named teammates
- Orchestrator creates a new team instead of spawning background subagents

### Debug Logging Best Practices

**Default**: Do not log by default (privacy, disk usage).

**Enable when needed**:
```bash
GATE_DEBUG=1 claude ...
```

**Log location considerations**:
- Prefer `/tmp` for short-lived debugging
- Prefer project directory only when logs are part of deliverables

---

## Reference Implementation

**Full working example**: [`agent-team-mail`](https://github.com/yourusername/agent-team-mail)

**Reddit Discussion**: [Playing around with the new agent teams experiment](https://www.reddit.com/r/ClaudeCode/comments/1qzypcs/playing_around_with_the_new_agent_teams_experiment/)

**Related Documentation**:
- [Agent Tool Use Best Practices](./agent-tool-use-best-practices.md) - Hook patterns, environment variables
- [PLUGIN-STORAGE-CONVENTIONS.md](../PLUGIN-STORAGE-CONVENTIONS.md) - Metadata storage paths

---

## Quick Reference

### Spawning an Orchestrator (Named Teammate)

```python
Task(
    subagent_type="scrum-master",
    team_name="sprint-1",
    name="scrum-master",
    description="Orchestrate dev/QA loop",
    prompt="Run sprint cycle with dev and QA workers..."
)
```

### Spawning a Worker (Background Agent)

```python
Task(
    subagent_type="rust-developer",
    run_in_background=true,
    description="Implement feature",
    prompt="Implement the user authentication feature..."
)
```

### Gate Script Locations

- **Hook config**: `.claude/settings.json` (or `.claude/settings.local.json`)
- **Gate script**: `.claude/scripts/gate-agent-spawns.py`
- **Team config**: `~/.claude/teams/<team-name>/config.json` (read-only)

---

**Document Version**: 1.0
**Last Updated**: 2026-02-11
**Maintained By**: Synaptic Canvas Team
