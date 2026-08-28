#!/usr/bin/env python3
"""
Shared utilities for Synaptic Canvas package scripts.

Provides:
- Allowed-path validation against runtime-configured directories.
- Agent Runner helpers (registry validation + task prompt build + audit).
- Shared runtime context helpers.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

from pydantic import BaseModel, Field, field_validator

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


# =============================================================================
# Paths and settings
# =============================================================================


def _normalize_path(value: Optional[str | Path]) -> Optional[Path]:
    if value is None:
        return None
    return Path(value).expanduser().resolve()


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class PathPolicy(BaseModel):
    """Resolved allowed-path policy."""

    cwd: Path
    project_dir: Optional[Path] = None
    codex_home: Optional[Path] = None
    additional_dirs: Set[Path] = Field(default_factory=set)

    @field_validator("cwd", "project_dir", "codex_home", mode="before")
    @classmethod
    def _validate_path(cls, v):
        return _normalize_path(v)


class RuntimeContext(BaseModel):
    """Shared runtime context derived from environment + filesystem."""

    cwd: Path
    project_dir: Optional[Path]
    codex_home: Optional[Path]
    allowed_dirs: Set[Path] = Field(default_factory=set)


def get_project_dir() -> Optional[Path]:
    """Return project root from environment variables if set."""
    project_dir = os.getenv("CLAUDE_PROJECT_DIR") or os.getenv("CODEX_PROJECT_DIR")
    return _normalize_path(project_dir)


def _collect_additional_dirs(project_dir: Optional[Path]) -> Set[Path]:
    """Collect additionalDirectories from settings files."""
    settings_paths = [
        Path("~/.claude/settings.json").expanduser(),
        Path("~/.codex/settings.json").expanduser(),
    ]
    if project_dir:
        settings_paths.extend(
            [
                project_dir / ".claude" / "settings.json",
                project_dir / ".codex" / "settings.json",
            ]
        )

    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        settings_paths.append(Path(codex_home) / "settings.json")

    allowed: Set[Path] = set()
    for path in settings_paths:
        if not path.exists():
            continue
        data = _read_json(path)
        if not data:
            continue
        extra = (data.get("permissions") or {}).get("additionalDirectories")
        if isinstance(extra, list):
            for entry in extra:
                if isinstance(entry, str) and entry.strip():
                    allowed.add(_normalize_path(entry))
    return {p for p in allowed if p is not None}


def build_path_policy(cwd: Optional[Path] = None) -> PathPolicy:
    cwd = _normalize_path(cwd or Path.cwd())
    project_dir = get_project_dir()
    codex_home = _normalize_path(os.getenv("CODEX_HOME"))
    additional = _collect_additional_dirs(project_dir)
    return PathPolicy(cwd=cwd, project_dir=project_dir, codex_home=codex_home, additional_dirs=additional)


def collect_allowed_dirs(policy: PathPolicy) -> Set[Path]:
    allowed = {policy.cwd}
    if policy.project_dir:
        allowed.add(policy.project_dir)
    if policy.codex_home:
        allowed.add(policy.codex_home)
    allowed.update(policy.additional_dirs)
    return allowed


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        return path.is_relative_to(base)
    except AttributeError:
        try:
            path.relative_to(base)
            return True
        except ValueError:
            return False


def is_path_allowed(target: Path, allowed_dirs: Iterable[Path]) -> bool:
    target = _normalize_path(target)
    if target is None:
        return False
    for base in allowed_dirs:
        if base and _is_relative_to(target, base):
            return True
    return False


def validate_allowed_path(target: Path, allowed_dirs: Iterable[Path], label: str = "path") -> Path:
    resolved = _normalize_path(target)
    if resolved is None:
        raise ValueError(f"Invalid {label}: {target}")
    if not is_path_allowed(resolved, allowed_dirs):
        raise ValueError(f"{label} is outside allowed directories: {resolved}")
    return resolved


def load_runtime_context(cwd: Optional[Path] = None) -> RuntimeContext:
    policy = build_path_policy(cwd=cwd)
    allowed = collect_allowed_dirs(policy)
    return RuntimeContext(
        cwd=policy.cwd,
        project_dir=policy.project_dir,
        codex_home=policy.codex_home,
        allowed_dirs=allowed,
    )


def find_repo_root(start: Optional[Path] = None) -> Optional[Path]:
    """Find git repo root by walking up to a .git directory."""
    current = _normalize_path(start or Path.cwd())
    if current is None:
        return None
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def is_git_repo(path: Path) -> bool:
    """Return True if the path is inside a valid git repository."""
    repo_path = _normalize_path(path)
    if repo_path is None:
        return False
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_path,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


# =============================================================================
# Hook JSON validation helpers
# =============================================================================


def get_tool_command(payload: Dict[str, Any]) -> str:
    """Extract tool command string from a hook payload."""
    if not isinstance(payload, dict):
        return ""
    tool_input = payload.get("tool_input") or {}
    if isinstance(tool_input, dict):
        for key in ("command", "input"):
            val = tool_input.get(key)
            if isinstance(val, str):
                return val
    for key in ("command", "input"):
        val = payload.get(key)
        if isinstance(val, str):
            return val
    return ""


def extract_json_from_command(command: str) -> Dict[str, Any]:
    """Extract a JSON object embedded in a command string."""
    if not isinstance(command, str):
        raise ValueError("Command must be a string")

    text = command.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    greedy = re.search(r"\{.*\}", text, re.DOTALL)
    if greedy:
        try:
            data = json.loads(greedy.group(0))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    for match in re.finditer(r"\{.*?\}", text, re.DOTALL):
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except Exception:
            continue

    raise ValueError("Expected JSON object in command")


def extract_hook_json(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract JSON object from hook payload tool command."""
    command = get_tool_command(payload)
    if not command:
        raise ValueError("Expected tool_input.command in payload")
    return extract_json_from_command(command)


def validate_json_payload(payload: Dict[str, Any], schema: type[BaseModel]) -> BaseModel:
    """Validate payload dict with a pydantic schema and return the model."""
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object")
    return schema.model_validate(payload)


def validate_hook_json(payload: Dict[str, Any], schema: type[BaseModel]) -> BaseModel:
    """Extract and validate JSON from hook payload with schema."""
    data = extract_hook_json(payload)
    return validate_json_payload(data, schema)


# =============================================================================
# Agent Runner helpers (self-contained)
# =============================================================================

REGISTRY_DEFAULT = os.path.join(".claude", "agents", "registry.yaml")
LOGS_DIR = os.path.join(".claude", "state", "logs")


class AgentSpec(BaseModel):
    name: str
    path: str
    expected_version: Optional[str] = None


class AgentFileInfo(BaseModel):
    path: str
    version_frontmatter: Optional[str]
    sha256: str


class AgentInvokeRequest(BaseModel):
    agent: str
    params: Dict[str, Any] = Field(default_factory=dict)
    registry_path: str = REGISTRY_DEFAULT
    timeout_s: int = 120


class AgentInvokeResult(BaseModel):
    ok: bool
    agent: Dict[str, Any]
    task_prompt: str
    timeout_s: int
    audit_path: str
    note: str


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _extract_frontmatter(text: str) -> str:
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
    out: Dict[str, Any] = {}
    for line in s.splitlines():
        match = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line.strip())
        if match:
            key, val = match.group(1), match.group(2)
            out[key] = val if val else None
    return out


def _load_yaml_file(path: str) -> Dict[str, Any]:
    text = _read_text(path)
    if yaml is not None:
        return yaml.safe_load(text) or {}
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
                data["agents"][last]["version"] = match_ver.group(1)
            match_path = re.match(r"^\s{4}path:\s*(.+)$", line)
            if match_path:
                last = list(data["agents"].keys())[-1]
                data["agents"][last]["path"] = match_path.group(1)
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


def invoke_agent_runner(request: AgentInvokeRequest) -> AgentInvokeResult:
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
        note="Agent Runner does not launch the Task tool; pass task_prompt to the Task tool.",
    )
    return result
