#!/usr/bin/env python3
"""
Agent Runner core utilities (library module).
- Validates agent name/path/version against .claude/agents/registry.yaml
- Extracts YAML frontmatter from agent file and verifies version
- Computes SHA-256 of the agent file for runtime attestation
- Builds a Task tool prompt string for the skill to use
- Writes a redacted audit record to .claude/state/logs/

Note: This scaffold does NOT launch the Task tool itself. It prepares
"task_prompt" for the skill to pass to the Task tool and records an audit entry.
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import os
import re
from typing import Any, Dict, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # Fallback basic parsing will be used

REGISTRY_DEFAULT = os.path.join(".claude", "agents", "registry.yaml")
LOGS_DIR = os.path.join(".claude", "state", "logs")


@dataclasses.dataclass
class AgentSpec:
    name: str
    path: str  # path to agent .md file (relative or absolute)
    expected_version: Optional[str]


@dataclasses.dataclass
class AgentFileInfo:
    path: str
    version_frontmatter: Optional[str]
    sha256: str


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _extract_frontmatter(text: str) -> str:
    """Return YAML frontmatter text between the first two '---' lines.
    Returns empty string if not found.
    """
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
    if not s:
        return {}
    if yaml is not None:
        return yaml.safe_load(s) or {}
    # Minimal fallback parser for simple key: value pairs
    out: Dict[str, Any] = {}
    for line in s.splitlines():
        m = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line.strip())
        if m:
            key, val = m.group(1), m.group(2)
            out[key] = val if val else None
    return out


def _load_yaml_file(path: str) -> Dict[str, Any]:
    text = _read_text(path)
    if yaml is not None:
        return yaml.safe_load(text) or {}
    # very simple fallback (agents top-level only)
    data: Dict[str, Any] = {}
    current = None
    for line in text.splitlines():
        if line.strip().startswith("agents:"):
            data["agents"] = {}
            current = "agents"
            continue
        if current == "agents":
            m = re.match(r"^\s{2}([A-Za-z0-9_\-]+):\s*$", line)
            if m:
                data["agents"][m.group(1)] = {}
            m2 = re.match(r"^\s{4}version:\s*(.+)$", line)
            if m2:
                last = list(data["agents"].keys())[-1]
                data["agents"][last]["version"] = m2.group(1)
            m3 = re.match(r"^\s{4}path:\s*(.+)$", line)
            if m3:
                last = list(data["agents"].keys())[-1]
                data["agents"][last]["path"] = m3.group(1)
    return data


def load_registry(path: str = REGISTRY_DEFAULT) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Registry not found: {path}")
    return _load_yaml_file(path)


def get_agent_spec(registry: Dict[str, Any], name: str) -> AgentSpec:
    agents = (registry or {}).get("agents", {})
    if name not in agents:
        raise KeyError(f"Agent '{name}' not found in registry")
    ent = agents[name]
    return AgentSpec(name=name, path=ent.get("path", ""), expected_version=ent.get("version"))


def read_agent_file_info(path: str) -> AgentFileInfo:
    text = _read_text(path)
    fm_text = _extract_frontmatter(text)
    fm = _parse_yaml(fm_text)
    version = fm.get("version") if isinstance(fm, dict) else None
    digest = hashlib.sha256(_read_bytes(path)).hexdigest()
    return AgentFileInfo(path=path, version_frontmatter=version, sha256=digest)


def validate_agent(registry_path: str, agent_name: str) -> Tuple[AgentSpec, AgentFileInfo]:
    reg = load_registry(registry_path)
    spec = get_agent_spec(reg, agent_name)
    if not spec.path:
        raise ValueError(f"Agent '{agent_name}' has no path in registry")
    agent_path = spec.path
    if not os.path.isabs(agent_path):
        agent_path = os.path.abspath(agent_path)
    if not os.path.isfile(agent_path):
        raise FileNotFoundError(f"Agent file not found: {agent_path}")
    info = read_agent_file_info(agent_path)
    if spec.expected_version and info.version_frontmatter and str(spec.expected_version) != str(info.version_frontmatter):
        raise ValueError(
            f"Version mismatch for '{agent_name}': file={info.version_frontmatter} registry={spec.expected_version}"
        )
    return spec, info


def build_task_prompt(agent_file_path: str, params: Dict[str, Any]) -> str:
    lines = [
        f"Load {agent_file_path} and execute with parameters:",
    ]
    for k, v in params.items():
        lines.append(f"- {k}: {v}")
    lines.append("Return ONLY fenced JSON as per the agent's Output Format section.")
    return "\n".join(lines)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_audit(agent: AgentSpec, info: AgentFileInfo, outcome: str, duration_ms: Optional[int] = None) -> str:
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
    fname = f"agent-runner-{agent.name}-{ts.replace(':','').replace('-','').replace('T','_')}.json"
    fpath = os.path.join(LOGS_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    return fpath


def invoke(agent_name: str, params: Dict[str, Any], registry_path: str = REGISTRY_DEFAULT, timeout_s: int = 120) -> Dict[str, Any]:
    """Prepare a Task tool prompt after validating registry + frontmatter; write audit.
    Returns JSON object with task_prompt and attestation info. Does not launch Task tool.
    """
    spec, info = validate_agent(registry_path, agent_name)
    prompt = build_task_prompt(info.path, params)
    audit_path = write_audit(spec, info, outcome="prepared")
    return {
        "ok": True,
        "agent": {
            "name": spec.name,
            "path": info.path,
            "version": info.version_frontmatter,
            "sha256": info.sha256,
        },
        "task_prompt": prompt,
        "timeout_s": timeout_s,
        "audit_path": audit_path,
        "note": "Agent Runner does not launch the Task tool; pass task_prompt to the Task tool.",
    }


def validate_only(agent_name: str, registry_path: str = REGISTRY_DEFAULT) -> Dict[str, Any]:
    spec, info = validate_agent(registry_path, agent_name)
    return {
        "ok": True,
        "agent": {
            "name": spec.name,
            "path": info.path,
            "version": info.version_frontmatter,
            "sha256": info.sha256,
        },
        "message": "Agent file matches registry (version + path).",
    }
