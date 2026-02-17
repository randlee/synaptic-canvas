#!/usr/bin/env python3
"""SC Agent Runner Library - Jenga Template

USAGE:
1. Copy this template to your package: packages/<your-package>/scripts/sc_shared.py
2. Update PACKAGE_NAME constant
3. Customize AGENT_TYPES and validation hooks if needed
4. Import sc_logging.py for audit logging integration

JENGA EXPANSION:
- {{PACKAGE_NAME}} - Replace with your package name (e.g., "sc-git-worktree")
- {{AGENT_TYPES}} - Optional: Define custom agent type list
- {{CUSTOM_VALIDATION_HOOKS}} - Optional: Add package-specific validation
- {{REGISTRY_DEFAULT}} - Optional: Override default registry path
- {{LOGS_DIR}} - Optional: Override default logs directory

INTEGRATION:
- Requires sc_logging.py in same directory for audit logging
- Uses registry validation pattern from Architecture Guidelines v0.5
- Provides SHA-256 integrity checking and version validation

Standard registry location: .claude/agents/registry.yaml
Standard log location: .claude/state/logs/agent-runner-<agent>-<timestamp>.json
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from pydantic import BaseModel, Field
except ImportError:
    print("ERROR: pydantic not installed. Run: pip install pydantic")
    import sys
    sys.exit(1)

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # Fallback to regex-based parsing


# =============================================================================
# Configuration - CUSTOMIZE THIS SECTION
# =============================================================================

# {{PACKAGE_NAME}} - Replace with your package name
PACKAGE_NAME = "{{PACKAGE_NAME}}"

# {{AGENT_TYPES}} - Optional: Define agent types for this package
# Example: AGENT_TYPES = ["create", "scan", "cleanup", "abort", "update"]
AGENT_TYPES = []  # Empty list = no type validation

# {{REGISTRY_DEFAULT}} - Default registry path
REGISTRY_DEFAULT = os.path.join(".claude", "agents", "registry.yaml")

# {{LOGS_DIR}} - Default logs directory
LOGS_DIR = os.path.join(".claude", "state", "logs")


# =============================================================================
# Pydantic Models - Agent Runner Data Structures
# =============================================================================

class AgentSpec(BaseModel):
    """Agent specification from registry."""
    name: str
    path: str
    expected_version: Optional[str] = None


class AgentFileInfo(BaseModel):
    """Agent file metadata with integrity hash."""
    path: str
    version_frontmatter: Optional[str]
    sha256: str  # SHA-256 hex digest (64 characters)


class AgentInvokeRequest(BaseModel):
    """Request to invoke an agent via Agent Runner."""
    agent: str
    params: Dict[str, Any] = Field(default_factory=dict)
    registry_path: str = REGISTRY_DEFAULT
    timeout_s: int = 120


class AgentInvokeResult(BaseModel):
    """Result of agent runner invocation (ready for Task tool)."""
    ok: bool
    agent: Dict[str, Any]  # {name, path, version, sha256}
    task_prompt: str
    timeout_s: int
    audit_path: str
    note: str = "Agent Runner does not launch the Task tool; pass task_prompt to the Task tool."


# =============================================================================
# Project Root Discovery - Robust Fallback Pattern
# =============================================================================

def _normalize_path(value: Optional[str | Path]) -> Optional[Path]:
    """Normalize path by expanding user and resolving to absolute."""
    if value is None:
        return None
    return Path(value).expanduser().resolve()


def find_project_root(start: Optional[Path] = None) -> Optional[Path]:
    """Find project root by searching upward for marker files/directories.

    Args:
        start: Starting directory (default: Path.cwd())

    Returns:
        Project root Path or None if not found

    Searches upward for:
        - .git directory (git repository)
        - .claude directory (Claude Code project)
        - .sc directory (Synaptic Canvas project)
    """
    current = Path(start or Path.cwd()).resolve()

    # Search upward through parent directories
    for parent in [current, *current.parents]:
        # Check for project markers
        if any([
            (parent / ".git").exists(),
            (parent / ".claude").exists(),
            (parent / ".sc").exists(),
        ]):
            return parent

    return None


def get_project_dir() -> Path:
    """Get project directory with robust fallback chain.

    Returns:
        Project directory Path (never None)

    Fallback order:
        1. CLAUDE_PROJECT_DIR (Claude Code hook context)
        2. CODEX_PROJECT_DIR (Codex compatibility)
        3. Search upward for .git/.claude/.sc markers
        4. Path.cwd() (last resort)

    Note:
        Environment variables are only available in hook contexts.
        Background agents, Bash tool, and teammates use marker search fallback.
    """
    # Try environment variables first (available in hook contexts)
    project_dir = os.getenv("CLAUDE_PROJECT_DIR") or os.getenv("CODEX_PROJECT_DIR")
    if project_dir:
        return _normalize_path(project_dir)

    # Try to find project root by searching for markers
    found_root = find_project_root()
    if found_root:
        return found_root

    # Last resort: current working directory
    return Path.cwd()


# =============================================================================
# Utility Functions - File I/O and YAML Parsing
# =============================================================================

def _read_text(path: str) -> str:
    """Read file as UTF-8 text."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_bytes(path: str) -> bytes:
    """Read file as binary (for SHA-256 computation)."""
    with open(path, "rb") as f:
        return f.read()


def _extract_frontmatter(text: str) -> str:
    """Extract YAML frontmatter from markdown file (text between --- markers)."""
    lines = text.splitlines()
    fm_start = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            fm_start = i
            break
    if fm_start is None:
        return ""
    for j in range(fm_start + 1, len(lines)):
        if lines[j].strip() == "---":
            return "\n".join(lines[fm_start + 1 : j])
    return ""


def _parse_yaml(s: str) -> Dict[str, Any]:
    """Parse YAML string with fallback to regex-based parsing.

    Allows basic agent frontmatter parsing without pyyaml dependency.
    """
    if not s:
        return {}
    if yaml is not None:
        return yaml.safe_load(s) or {}

    # Fallback: regex-based parsing for simple key: value pairs
    out: Dict[str, Any] = {}
    for line in s.splitlines():
        match = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line.strip())
        if match:
            key, val = match.group(1), match.group(2)
            out[key] = val if val else None
    return out


def _load_yaml_file(path: str) -> Dict[str, Any]:
    """Load YAML file with fallback parsing for registry format.

    Expected registry format:
    agents:
      agent-name:
        version: "1.0.0"
        path: ".claude/agents/agent-file.md"
    """
    text = _read_text(path)
    if yaml is not None:
        return yaml.safe_load(text) or {}

    # Fallback: regex-based parsing for registry structure
    data: Dict[str, Any] = {}
    current = None
    for line in text.splitlines():
        if line.strip().startswith("agents:"):
            data["agents"] = {}
            current = "agents"
            continue
        if current == "agents":
            match = re.match(r"^\s{2}([A-Za-z0-9_\-]+):\s*$", line)
            if match:
                data["agents"][match.group(1)] = {}
            match_ver = re.match(r"^\s{4}version:\s*(.+)$", line)
            if match_ver:
                last = list(data["agents"].keys())[-1]
                data["agents"][last]["version"] = match_ver.group(1).strip('"\'')
            match_path = re.match(r"^\s{4}path:\s*(.+)$", line)
            if match_path:
                last = list(data["agents"].keys())[-1]
                data["agents"][last]["path"] = match_path.group(1).strip('"\'')
    return data


def _ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


# =============================================================================
# Registry Functions - Agent Lookup and Validation
# =============================================================================

def load_registry(path: str = REGISTRY_DEFAULT) -> Dict[str, Any]:
    """Load agent registry from YAML file.

    Args:
        path: Path to registry file (default: .claude/agents/registry.yaml)

    Returns:
        Registry data dictionary

    Raises:
        FileNotFoundError: If registry file not found
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Registry not found: {path}")
    return _load_yaml_file(path)


def get_agent_spec(registry: Dict[str, Any], name: str) -> AgentSpec:
    """Extract agent specification from registry by name.

    Args:
        registry: Registry data from load_registry()
        name: Agent name to lookup

    Returns:
        AgentSpec with name, path, and expected version

    Raises:
        KeyError: If agent not found in registry
    """
    agents = (registry or {}).get("agents", {})
    if name not in agents:
        raise KeyError(f"Agent '{name}' not found in registry")
    ent = agents[name]
    return AgentSpec(
        name=name,
        path=ent.get("path", ""),
        expected_version=ent.get("version")
    )


def read_agent_file_info(path: str) -> AgentFileInfo:
    """Read agent file metadata including version and SHA-256 hash.

    Args:
        path: Path to agent file (.md)

    Returns:
        AgentFileInfo with path, version, and SHA-256 digest

    Note:
        SHA-256 is computed on complete binary file content for integrity verification.
    """
    text = _read_text(path)
    fm_text = _extract_frontmatter(text)
    fm = _parse_yaml(fm_text)
    version = fm.get("version") if isinstance(fm, dict) else None

    # Compute SHA-256 hash of entire file (binary) for integrity checking
    digest = hashlib.sha256(_read_bytes(path)).hexdigest()

    return AgentFileInfo(
        path=path,
        version_frontmatter=version,
        sha256=digest
    )


def validate_agent(registry_path: str, agent_name: str) -> Tuple[AgentSpec, AgentFileInfo]:
    """Validate agent through 5-stage pipeline.

    Validation stages:
    1. Load registry from path
    2. Lookup agent specification by name
    3. Resolve agent file path (convert relative to absolute)
    4. Verify file exists at path
    5. Validate version match (registry vs file frontmatter)

    Args:
        registry_path: Path to registry file
        agent_name: Agent name to validate

    Returns:
        Tuple of (AgentSpec, AgentFileInfo)

    Raises:
        FileNotFoundError: Registry or agent file not found
        KeyError: Agent not found in registry
        ValueError: Agent has no path or version mismatch
    """
    # Stage 1: Load registry
    reg = load_registry(registry_path)

    # Stage 2: Lookup agent
    spec = get_agent_spec(reg, agent_name)

    # Stage 3: Validate path exists
    if not spec.path:
        raise ValueError(f"Agent '{agent_name}' has no path in registry")

    # Stage 4: Resolve to absolute path and verify file exists
    agent_path = spec.path
    if not os.path.isabs(agent_path):
        agent_path = os.path.abspath(agent_path)
    if not os.path.isfile(agent_path):
        raise FileNotFoundError(f"Agent file not found: {agent_path}")

    # Stage 5: Read file info and validate version
    info = read_agent_file_info(agent_path)
    if (spec.expected_version and info.version_frontmatter and
        str(spec.expected_version) != str(info.version_frontmatter)):
        raise ValueError(
            f"Version mismatch for '{agent_name}': "
            f"file={info.version_frontmatter} registry={spec.expected_version}"
        )

    return spec, info


# =============================================================================
# Task Prompt Building
# =============================================================================

def build_task_prompt(agent_file_path: str, params: Dict[str, Any]) -> str:
    """Build task prompt for Task tool invocation.

    Args:
        agent_file_path: Path to agent file
        params: Parameters to pass to agent

    Returns:
        Formatted prompt string for Task tool

    Note:
        Agent Runner does NOT invoke Task tool directly. Caller must pass
        this prompt to Task tool with agent file content.
    """
    lines = [
        f"Load {agent_file_path} and execute with parameters:",
    ]
    for k, v in params.items():
        lines.append(f"- {k}: {v}")
    lines.append("Return ONLY fenced JSON as per the agent's Output Format section.")
    return "\n".join(lines)


# =============================================================================
# Audit Logging Integration
# =============================================================================

def write_audit(
    agent: AgentSpec,
    info: AgentFileInfo,
    outcome: str,
    duration_ms: Optional[int] = None
) -> str:
    """Write audit record for agent invocation.

    Args:
        agent: Agent specification
        info: Agent file info with SHA-256
        outcome: Outcome string (e.g., "prepared", "success", "error")
        duration_ms: Optional execution duration in milliseconds

    Returns:
        Path to audit record file

    Audit record format (JSON):
        {
            "timestamp": "2026-02-11T10:30:45Z",
            "agent": "agent-name",
            "version_frontmatter": "1.0.0",
            "file_sha256": "abcd...",
            "invoker": "agent-runner",
            "outcome": "prepared",
            "duration_ms": 250
        }

    Note:
        For better integration, consider using sc_logging.log_event() instead.
        This direct JSON approach is provided for standalone usage.
    """
    _ensure_dir(LOGS_DIR)
    ts = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    record = {
        "timestamp": ts,
        "agent": agent.name,
        "version_frontmatter": info.version_frontmatter,
        "file_sha256": info.sha256,
        "invoker": "agent-runner",
        "outcome": outcome,
    }
    if duration_ms is not None:
        record["duration_ms"] = duration_ms

    # Filename: agent-runner-<agent>-<timestamp>.json
    # (timestamp sanitized for filesystem compatibility)
    fname = (f"agent-runner-{agent.name}-"
             f"{ts.replace(':','').replace('-','').replace('T','_')}.json")
    fpath = os.path.join(LOGS_DIR, fname)

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    return fpath


# =============================================================================
# Main Invocation Function
# =============================================================================

def invoke_agent_runner(request: AgentInvokeRequest) -> AgentInvokeResult:
    """Main entry point for Agent Runner invocation.

    Workflow:
    1. Validate agent (5-stage validation pipeline)
    2. Build task prompt with parameters
    3. Write audit record (outcome="prepared")
    4. Return result with task_prompt for caller to pass to Task tool

    Args:
        request: AgentInvokeRequest with agent name, params, registry path

    Returns:
        AgentInvokeResult with task_prompt and audit_path

    Raises:
        FileNotFoundError: Registry or agent file not found
        KeyError: Agent not found in registry
        ValueError: Validation errors

    Note:
        This function does NOT launch the Task tool. Caller must:
        1. Receive task_prompt from result
        2. Pass task_prompt to Task tool with agent file content
        3. Optionally update audit record after execution

    Example:
        request = AgentInvokeRequest(
            agent="worktree-create",
            params={"branch": "feature-x", "upstream": "origin"},
            registry_path=".claude/agents/registry.yaml"
        )
        result = invoke_agent_runner(request)

        # Caller passes result.task_prompt to Task tool
        # After execution, optionally:
        # write_audit(spec, info, outcome="success", duration_ms=1234)
    """
    spec, info = validate_agent(request.registry_path, request.agent)
    prompt = build_task_prompt(info.path, request.params)
    audit_path = write_audit(spec, info, outcome="prepared")

    result = AgentInvokeResult(
        ok=True,
        agent={
            "name": spec.name,
            "path": info.path,
            "version": info.version_frontmatter,
            "sha256": info.sha256,
        },
        task_prompt=prompt,
        timeout_s=request.timeout_s,
        audit_path=audit_path,
    )

    return result


# =============================================================================
# Custom Validation Hooks - CUSTOMIZE THIS SECTION
# =============================================================================

# {{CUSTOM_VALIDATION_HOOKS}}
# Add package-specific validation functions here.
#
# Examples:
# - Validate agent type is in AGENT_TYPES list
# - Validate parameters match expected schema
# - Validate allowed paths for file operations
# - Custom frontmatter field validation
#
# Example implementation:
#
# def validate_agent_type(agent_name: str) -> None:
#     """Validate agent type is in allowed list."""
#     if AGENT_TYPES and agent_name not in AGENT_TYPES:
#         raise ValueError(f"Agent '{agent_name}' not in allowed types: {AGENT_TYPES}")
#
# def validate_custom_params(params: Dict[str, Any]) -> None:
#     """Validate custom parameter requirements."""
#     required = ["branch_name", "upstream"]
#     for field in required:
#         if field not in params:
#             raise ValueError(f"Missing required parameter: {field}")


# =============================================================================
# CLI Interface (optional - for testing)
# =============================================================================

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="SC Agent Runner CLI")
    parser.add_argument("agent", help="Agent name from registry")
    parser.add_argument("--param", action="append", help="Agent parameter (key=value)")
    parser.add_argument("--registry", default=REGISTRY_DEFAULT, help="Registry path")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")

    args = parser.parse_args()

    # Parse parameters
    params = {}
    if args.param:
        for param in args.param:
            if "=" not in param:
                print(f"ERROR: Invalid parameter format: {param} (expected key=value)", file=sys.stderr)
                sys.exit(1)
            key, value = param.split("=", 1)
            params[key] = value

    # Invoke agent runner
    try:
        request = AgentInvokeRequest(
            agent=args.agent,
            params=params,
            registry_path=args.registry,
            timeout_s=args.timeout
        )
        result = invoke_agent_runner(request)

        print("✓ Agent Runner Success")
        print(f"Agent: {result.agent['name']} (version {result.agent['version']})")
        print(f"SHA-256: {result.agent['sha256']}")
        print(f"Audit: {result.audit_path}")
        print(f"\nTask Prompt:\n{result.task_prompt}")
        print(f"\nNote: {result.note}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
