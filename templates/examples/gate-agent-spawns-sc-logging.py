#!/usr/bin/env python3
"""SC Structured Logging Library - Expanded for gate-agent-spawns

This is an EXAMPLE of sc-logging.jenga.py expanded for the gate-agent-spawns hook.
Shows how to customize the template with package-specific fields.

Copy from templates/sc-logging.jenga.py and expand Jenga variables:
- {{PACKAGE_NAME}} → "hooks" (or could be package-specific)
- {{EXTRA_IMPORTS}} → typing.Literal, Optional
- {{EXTRA_FIELDS}} → Gate-specific fields (session_id, subagent_type, decision)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

try:
    from pydantic import BaseModel, Field, ConfigDict
except ImportError:
    print("ERROR: pydantic not installed. Run: pip install pydantic", file=sys.stderr)
    sys.exit(1)

# Expanded: {{PACKAGE_NAME}} → "hooks" (centralized hook logging)
# Alternative: Could be package-specific like "sc-agent-teams"
PACKAGE_NAME = "hooks"

# Standard log location following SC conventions
LOGS_DIR = Path.cwd() / ".claude" / "state" / "logs" / PACKAGE_NAME


# =============================================================================
# Base Schema - DO NOT MODIFY
# =============================================================================

class BaseLogEntry(BaseModel):
    """Base log entry schema - extendable via inheritance."""
    model_config = ConfigDict(extra="allow")

    timestamp: str = Field(
        description="ISO 8601 timestamp with timezone (UTC)",
        examples=["2026-02-11T10:30:45.123456Z"]
    )
    event: str = Field(
        description="Event type identifier",
        examples=["agent_spawn_allowed", "agent_spawn_blocked"]
    )
    package: str = Field(
        description="Package name",
        examples=["hooks", "sc-git-worktree"]
    )
    level: str = Field(
        default="info",
        description="Log level",
        pattern="^(debug|info|warning|error|critical)$"
    )


# =============================================================================
# Package-Specific Extensions - CUSTOMIZED FOR GATE-AGENT-SPAWNS
# =============================================================================

# Expanded: {{EXTRA_IMPORTS}}
# from typing import Literal, Optional (already imported above)


class GateDecision(BaseModel):
    """Structured gate decision with reason and rule."""
    allowed: bool
    reason: Optional[str] = Field(default=None, description="Block reason if not allowed")
    rule: Optional[str] = Field(default=None, description="Rule that was violated")


class LogEntry(BaseLogEntry):
    """Extended log entry for agent spawn gate logging.

    Expanded: {{EXTRA_FIELDS}}
    Gate-specific fields track spawn requests and gate decisions.
    """
    session_id: Optional[str] = Field(default=None, description="Caller session ID")
    subagent_type: Optional[str] = Field(default=None, description="Agent type being spawned")
    teammate_name: Optional[str] = Field(default=None, description="Name parameter (if named teammate)")
    team_name: Optional[str] = Field(default=None, description="Team name (if joining team)")
    run_in_background: Optional[bool] = Field(default=None, description="Whether spawning as background agent")

    # Structured decision
    decision: Optional[GateDecision] = Field(default=None, description="Gate decision with reason")


# =============================================================================
# Logging Functions
# =============================================================================

def get_log_file(event_type: str, *, log_dir: Optional[Path] = None) -> Path:
    """Get log file path for event type."""
    log_dir = log_dir or LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_event = event_type.lower().replace(" ", "-").replace("_", "-")
    return log_dir / f"{safe_event}.jsonl"


def log_event(
    event: str,
    level: str = "info",
    log_dir: Optional[Path] = None,
    **extra_fields
) -> None:
    """Log a structured event."""
    timestamp = datetime.now(timezone.utc).isoformat()

    entry = LogEntry(
        timestamp=timestamp,
        event=event,
        package=PACKAGE_NAME,
        level=level,
        **extra_fields
    )

    log_file = get_log_file(event, log_dir=log_dir)

    try:
        with log_file.open("a") as f:
            f.write(entry.model_dump_json() + "\n")
    except Exception as e:
        print(f"WARNING: Failed to write log: {e}", file=sys.stderr)


def log_gate_decision(
    hook_data: dict,
    allowed: bool,
    reason: Optional[str] = None,
    rule: Optional[str] = None
) -> None:
    """Log a gate decision with full context.

    Args:
        hook_data: Full hook payload from stdin
        allowed: Whether spawn was allowed
        reason: Block reason if not allowed
        rule: Rule that was violated
    """
    tool_input = hook_data.get("tool_input", {})

    log_event(
        event="agent_spawn_blocked" if not allowed else "agent_spawn_allowed",
        level="warning" if not allowed else "info",
        session_id=hook_data.get("session_id", ""),
        subagent_type=tool_input.get("subagent_type", ""),
        teammate_name=tool_input.get("name", ""),
        team_name=tool_input.get("team_name", ""),
        run_in_background=tool_input.get("run_in_background", False),
        decision=GateDecision(
            allowed=allowed,
            reason=reason,
            rule=rule
        ).model_dump() if reason or rule else {"allowed": allowed}
    )


# =============================================================================
# Querying Helpers
# =============================================================================

def read_logs(
    event_type: str,
    limit: Optional[int] = None,
    log_dir: Optional[Path] = None
) -> list[LogEntry]:
    """Read log entries from file."""
    log_file = get_log_file(event_type, log_dir=log_dir)
    if not log_file.exists():
        return []

    entries = []
    with log_file.open("r") as f:
        for line in f:
            try:
                entry = LogEntry.model_validate_json(line.strip())
                entries.append(entry)
            except Exception:
                continue

    if limit:
        entries = entries[-limit:][::-1]

    return entries


# =============================================================================
# CLI Interface (for testing)
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gate Agent Spawns Logging")
    subparsers = parser.add_subparsers(dest="command")

    # Read command
    read_parser = subparsers.add_parser("read", help="Read gate logs")
    read_parser.add_argument("event_type", help="Event type (agent-spawn-allowed or agent-spawn-blocked)")
    read_parser.add_argument("--limit", type=int, default=10, help="Limit entries")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show gate statistics")

    args = parser.parse_args()

    if args.command == "read":
        entries = read_logs(args.event_type, limit=args.limit)
        for entry in entries:
            print(entry.model_dump_json(indent=2))

    elif args.command == "stats":
        allowed = read_logs("agent-spawn-allowed")
        blocked = read_logs("agent-spawn-blocked")

        print(f"Total allowed: {len(allowed)}")
        print(f"Total blocked: {len(blocked)}")
        print(f"\nBlocked breakdown:")

        reasons = {}
        for entry in blocked:
            if entry.decision and entry.decision.get("reason"):
                reason = entry.decision["reason"]
                reasons[reason] = reasons.get(reason, 0) + 1

        for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"  {count:3d} - {reason}")

    else:
        parser.print_help()
