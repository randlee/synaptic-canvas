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
from typing import Any, Callable, Dict, Iterable, Optional, Set, Tuple

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


def get_repo_root(cwd: Optional[Path] = None) -> Path:
    """Get the repository root using git rev-parse.

    Args:
        cwd: Working directory to run git from (default: current directory)

    Returns:
        Path to the repository root

    Raises:
        RuntimeError: If not in a git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Not in a git repository: {e.stderr}") from e


def get_repo_name(cwd: Optional[Path] = None) -> str:
    """Get the repository name from the root directory.

    Args:
        cwd: Working directory to run git from (default: current directory)

    Returns:
        Repository directory name
    """
    return get_repo_root(cwd).name


def run_git(
    args: list,
    cwd: Optional[Path] = None,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """Run a git command with standard options.

    Args:
        args: Git command arguments (without 'git' prefix)
        cwd: Working directory (default: current directory)
        check: Raise exception on non-zero exit (default: True)
        capture_output: Capture stdout/stderr (default: True)

    Returns:
        CompletedProcess result

    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        text=True,
    )


def _dedupe_preserve(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}

    # Minimal fallback parser for git.protected_branches
    data: Dict[str, Any] = {}
    current_section = None
    current_key = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0 and stripped.endswith(":") and not stripped.startswith("-"):
            current_section = stripped[:-1]
            current_key = None
            data.setdefault(current_section, {})
            continue

        if indent == 2 and current_section == "git" and stripped.endswith(":"):
            current_key = stripped[:-1]
            continue

        if indent >= 4 and current_section == "git" and current_key == "protected_branches" and stripped.startswith("-"):
            value = stripped.lstrip("-").strip()
            if value:
                data.setdefault("git", {}).setdefault("protected_branches", []).append(value)
            continue

        if current_section == "git" and "protected_branches" in stripped and "[" in stripped:
            # Inline list: protected_branches: [a, b]
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                raw = parts[1].strip().lstrip("[").rstrip("]")
                branches = [b.strip() for b in raw.split(",") if b.strip()]
                data.setdefault("git", {})["protected_branches"] = branches
                continue

    return data


def _write_shared_protected_branches(shared_path: Path, branches: list[str]) -> None:
    shared_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"git": {"protected_branches": branches}}
    if yaml is not None:
        shared_path.write_text(yaml.safe_dump(payload, sort_keys=False))
    else:
        lines = ["git:", "  protected_branches:"]
        for branch in branches:
            lines.append(f"    - {branch}")
        shared_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_protected_branches(
    cwd: Optional[Path] = None,
    user_provided: Optional[list[str]] = None,
    cache_shared: bool = True,
    log_fn: Optional[Callable[[str], None]] = None,
) -> list:
    """Detect protected branches with shared settings and gitflow caching.

    Priority order:
    1) .sc/shared-settings.yaml (git.protected_branches)
    2) user-provided list (unioned with gitflow detection)
    3) gitflow config (gitflow.branch.master/develop), cached to shared settings

    Raises:
        ValueError if no protected branches can be determined.
    """
    repo_root = get_repo_root(cwd)
    shared_path = repo_root / ".sc" / "shared-settings.yaml"

    shared_settings = _load_yaml(shared_path)
    shared_branches = (shared_settings.get("git") or {}).get("protected_branches")
    if isinstance(shared_branches, list) and shared_branches:
        if user_provided:
            return _dedupe_preserve(user_provided + shared_branches)
        return shared_branches

    protected: list[str] = []
    if user_provided:
        protected.extend(user_provided)

    for config_key in ["gitflow.branch.master", "gitflow.branch.develop"]:
        try:
            result = run_git(
                ["config", "--get", config_key],
                cwd=repo_root,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                protected.append(result.stdout.strip())
        except Exception:
            pass

    protected = _dedupe_preserve(protected)

    if protected:
        if cache_shared:
            _write_shared_protected_branches(shared_path, protected)
            if log_fn:
                log_fn(f"cached protected branches to {shared_path}")
        return protected

    raise ValueError(
        "Protected branches not configured.\n\n"
        "Please create .sc/shared-settings.yaml with:\n"
        "git:\n"
        "  protected_branches: [main, develop]\n\n"
        "List all branches that require PR workflow (no direct push)."
    )


def resolve_merge_base(
    cwd: Optional[Path] = None,
    user_provided: Optional[list[str]] = None,
    cache_shared: bool = True,
    log_fn: Optional[Callable[[str], None]] = None,
) -> Optional[str]:
    """Resolve the best protected branch to use as merge base.

    Checks protected branches in order and returns the first one that
    exists locally or remotely. Used for merge detection to ensure we
    compare against a known stable branch, not HEAD.

    Args:
        cwd: Working directory to run git from (default: current directory)

    Returns:
        Branch name to use as merge base, or None if no protected branch found
    """
    protected = get_protected_branches(
        cwd=cwd,
        user_provided=user_provided,
        cache_shared=cache_shared,
        log_fn=log_fn,
    )

    for branch in protected:
        # Check local first
        local_result = run_git(["branch", "--list", branch], cwd=cwd, check=False)
        if local_result.returncode == 0 and local_result.stdout.strip():
            return branch

        # Check remote
        remote_result = run_git(
            ["branch", "-r", "--list", f"origin/{branch}"], cwd=cwd, check=False
        )
        if remote_result.returncode == 0 and remote_result.stdout.strip():
            return f"origin/{branch}"

    return None


def check_branch_exists_local(branch: str, cwd: Optional[Path] = None) -> bool:
    """Check if a branch exists locally."""
    result = run_git(["branch", "--list", branch], cwd=cwd, check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


def check_branch_exists_remote(branch: str, cwd: Optional[Path] = None) -> bool:
    """Check if a branch exists on remote (origin)."""
    result = run_git(["branch", "-r", "--list", f"origin/{branch}"], cwd=cwd, check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


def create_tracking_branch(branch: str, cwd: Optional[Path] = None) -> bool:
    """Create a local tracking branch for a remote branch.

    Args:
        branch: Branch name (without origin/ prefix)
        cwd: Working directory

    Returns:
        True if branch was created successfully
    """
    result = run_git(
        ["branch", "--track", branch, f"origin/{branch}"],
        cwd=cwd,
        check=False,
    )
    return result.returncode == 0


# =============================================================================
# Worktree Operations
# =============================================================================


def get_worktree_status(path: Path) -> tuple:
    """Check if worktree is clean.

    Returns:
        Tuple of (is_clean: bool, dirty_files: List[str])
    """
    result = run_git(["status", "--short"], cwd=path, check=False)
    if result.returncode != 0:
        return False, [f"git status failed: {result.stderr}"]
    dirty_files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    return len(dirty_files) == 0, dirty_files


def is_branch_merged(branch: str, base: str = "HEAD", cwd: Optional[Path] = None) -> bool:
    """Check if branch is merged into base."""
    result = run_git(["branch", "--merged", base], cwd=cwd, check=False)
    if result.returncode != 0:
        return False
    merged_branches = [b.strip().lstrip("* ") for b in result.stdout.strip().split("\n")]
    return branch in merged_branches


def count_unique_commits(branch: str, base: str = "HEAD", cwd: Optional[Path] = None) -> int:
    """Count commits in branch not in base."""
    result = run_git(["rev-list", "--count", f"{base}..{branch}"], cwd=cwd, check=False)
    if result.returncode != 0:
        return -1
    try:
        return int(result.stdout.strip())
    except ValueError:
        return -1


def remove_worktree(path: Path, force: bool = False, cwd: Optional[Path] = None) -> bool:
    """Remove a worktree."""
    args = ["worktree", "remove", str(path)]
    if force:
        args.append("--force")
    result = run_git(args, cwd=cwd, check=False)
    return result.returncode == 0


def delete_local_branch(branch: str, force: bool = False, cwd: Optional[Path] = None) -> bool:
    """Delete a local branch."""
    flag = "-D" if force else "-d"
    result = run_git(["branch", flag, branch], cwd=cwd, check=False)
    return result.returncode == 0


def delete_remote_branch(branch: str, cwd: Optional[Path] = None) -> tuple:
    """Delete a remote branch.

    Returns:
        Tuple of (success: bool, message: str)
    """
    result = run_git(["push", "origin", "--delete", branch], cwd=cwd, check=False)
    if result.returncode == 0:
        return True, "deleted"
    if "remote ref does not exist" in result.stderr:
        return True, "already absent"
    return False, result.stderr


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


# =============================================================================
# JSONL Tracking
# =============================================================================


class TrackingEntry(BaseModel):
    """A single worktree tracking entry stored in JSONL format."""

    branch: str = Field(..., description="Branch name")
    path: str = Field(..., description="Worktree path")
    base: str = Field(..., description="Base branch this was created from")
    owner: str = Field(..., description="Agent or user who created this worktree")
    purpose: str = Field("", description="Short description of worktree purpose")
    created: str = Field(..., description="ISO 8601 timestamp of creation")
    status: str = Field("active", description="Status: active, merged, abandoned")
    last_checked: str = Field(..., description="ISO 8601 timestamp of last check")
    notes: str = Field("", description="Optional notes")
    # Remote sync fields
    remote_exists: bool = Field(False, description="Whether branch exists on remote")
    local_worktree: bool = Field(True, description="Whether local worktree exists")
    remote_ahead: int = Field(0, description="Number of commits remote has that local doesn't")


def get_default_tracking_path(worktree_base: Path) -> Path:
    """Get the default JSONL tracking file path."""
    return worktree_base / "worktree-tracking.jsonl"


def load_tracking_jsonl(tracking_path: Path) -> list[TrackingEntry]:
    """Load tracking entries from JSONL file.

    Args:
        tracking_path: Path to the JSONL tracking file

    Returns:
        List of TrackingEntry objects (empty list if file doesn't exist)
    """
    if not tracking_path.exists():
        return []

    entries = []
    for line in tracking_path.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            entries.append(TrackingEntry.model_validate(data))
        except (json.JSONDecodeError, Exception):
            # Skip malformed lines
            continue
    return entries


def save_tracking_jsonl(tracking_path: Path, entries: list[TrackingEntry]) -> None:
    """Save tracking entries to JSONL file.

    Args:
        tracking_path: Path to the JSONL tracking file
        entries: List of TrackingEntry objects to save
    """
    # Ensure parent directory exists
    tracking_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for entry in entries:
        lines.append(json.dumps(entry.model_dump(), separators=(",", ":")))

    tracking_path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")


def add_tracking_entry(tracking_path: Path, entry: TrackingEntry) -> None:
    """Append a single tracking entry to the JSONL file.

    Args:
        tracking_path: Path to the JSONL tracking file
        entry: TrackingEntry to append
    """
    # Ensure parent directory exists
    tracking_path.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(entry.model_dump(), separators=(",", ":")) + "\n"

    # Append to file (create if doesn't exist)
    with open(tracking_path, "a", encoding="utf-8") as f:
        f.write(line)


def update_tracking_entry(tracking_path: Path, branch: str, updates: Dict[str, Any]) -> bool:
    """Update a tracking entry by branch name.

    Args:
        tracking_path: Path to the JSONL tracking file
        branch: Branch name to find and update
        updates: Dictionary of field updates

    Returns:
        True if entry was found and updated, False otherwise
    """
    entries = load_tracking_jsonl(tracking_path)
    found = False

    for entry in entries:
        if entry.branch == branch:
            for key, value in updates.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            found = True
            break

    if found:
        save_tracking_jsonl(tracking_path, entries)

    return found


def remove_tracking_entry(tracking_path: Path, branch: str) -> bool:
    """Remove a tracking entry by branch name.

    Args:
        tracking_path: Path to the JSONL tracking file
        branch: Branch name to remove

    Returns:
        True if entry was found and removed, False otherwise
    """
    entries = load_tracking_jsonl(tracking_path)
    original_count = len(entries)
    entries = [e for e in entries if e.branch != branch]

    if len(entries) < original_count:
        save_tracking_jsonl(tracking_path, entries)
        return True

    return False


def get_remote_ahead_count(branch: str, cwd: Optional[Path] = None) -> int:
    """Get the number of commits remote has that local branch doesn't.

    Uses: git rev-list --count <branch>..origin/<branch>

    Args:
        branch: Branch name to check
        cwd: Working directory (should be repo root or worktree)

    Returns:
        Number of commits remote is ahead, or -1 if error/not trackable
    """
    result = run_git(
        ["rev-list", "--count", f"{branch}..origin/{branch}"],
        cwd=cwd,
        check=False,
    )
    if result.returncode != 0:
        return -1
    try:
        return int(result.stdout.strip())
    except ValueError:
        return -1


def check_remote_branch_exists(branch: str, cwd: Optional[Path] = None) -> bool:
    """Check if a branch exists on the remote.

    Args:
        branch: Branch name to check
        cwd: Working directory

    Returns:
        True if branch exists on remote
    """
    result = run_git(
        ["branch", "-r", "--list", f"origin/{branch}"],
        cwd=cwd,
        check=False,
    )
    return bool(result.stdout.strip())


def sync_tracking_with_remote(tracking_path: Path, repo_root: Path) -> Dict[str, Any]:
    """Synchronize tracking entries with remote state.

    Updates remote_exists and remote_ahead for all tracked branches.
    Also checks if local worktree still exists.

    Args:
        tracking_path: Path to the JSONL tracking file
        repo_root: Path to the repository root

    Returns:
        Summary dict with counts of updated entries and any warnings
    """
    entries = load_tracking_jsonl(tracking_path)
    if not entries:
        return {"updated": 0, "warnings": []}

    # Fetch latest from remote first
    run_git(["fetch", "--all", "--prune"], cwd=repo_root, check=False)

    updated_count = 0
    warnings = []

    for entry in entries:
        changed = False

        # Check if local worktree still exists
        worktree_exists = Path(entry.path).exists()
        if entry.local_worktree != worktree_exists:
            entry.local_worktree = worktree_exists
            changed = True

        # Check remote state
        remote_exists = check_remote_branch_exists(entry.branch, cwd=repo_root)
        if entry.remote_exists != remote_exists:
            entry.remote_exists = remote_exists
            changed = True

        # Check remote ahead count (only if remote exists)
        if remote_exists:
            ahead_count = get_remote_ahead_count(entry.branch, cwd=repo_root)
            if ahead_count >= 0 and entry.remote_ahead != ahead_count:
                entry.remote_ahead = ahead_count
                changed = True

                # Warn if remote has unpulled commits
                if ahead_count > 0:
                    warnings.append({
                        "branch": entry.branch,
                        "message": f"Remote is {ahead_count} commit(s) ahead of local",
                        "remote_ahead": ahead_count,
                    })
        else:
            if entry.remote_ahead != 0:
                entry.remote_ahead = 0
                changed = True

        # Update last_checked timestamp
        entry.last_checked = _dt.datetime.now(_dt.timezone.utc).isoformat()
        changed = True

        if changed:
            updated_count += 1

    # Save updated entries
    save_tracking_jsonl(tracking_path, entries)

    return {
        "updated": updated_count,
        "total": len(entries),
        "warnings": warnings,
    }


def cleanup_empty_directories(worktree_base: Path, preserve_files: Optional[list] = None) -> list[str]:
    """Remove empty directories from the worktree structure.

    Walks the worktree base directory bottom-up and removes empty directories.
    Preserves the worktree base itself and any directories containing specified files.

    Args:
        worktree_base: Base directory for worktrees
        preserve_files: List of filenames to preserve (default: tracking file)

    Returns:
        List of removed directory paths
    """
    if not worktree_base.exists():
        return []

    preserve = preserve_files or ["worktree-tracking.jsonl", "worktree-tracking.md"]
    removed = []

    # Walk bottom-up to remove empty dirs
    for dirpath, dirnames, filenames in os.walk(str(worktree_base), topdown=False):
        path = Path(dirpath)

        # Don't remove the worktree base itself
        if path == worktree_base:
            continue

        # Don't remove if contains preserved files
        if any(f in filenames for f in preserve):
            continue

        # Don't remove if has any files
        if filenames:
            continue

        # Don't remove if has any subdirectories (they weren't removed)
        if dirnames:
            # Check if subdirs still exist (they might have been removed)
            remaining_dirs = [d for d in dirnames if (path / d).exists()]
            if remaining_dirs:
                continue

        # Directory is empty, remove it
        try:
            path.rmdir()
            removed.append(str(path))
        except OSError:
            # Directory not empty or permission error, skip
            pass

    return removed


def get_branch_creator_info(branch: str, base: str = "main", cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Get the author and date of the first unique commit on a branch.

    Finds the first commit on the branch that isn't on the base branch.

    Args:
        branch: Branch name to check
        base: Base branch to compare against (default: main)
        cwd: Working directory

    Returns:
        Dict with 'author', 'email', 'date' or empty dict if not found
    """
    # Get the first commit unique to this branch (oldest first)
    # --ancestry-path ensures we only get commits actually on this branch's path
    result = run_git(
        ["log", "--reverse", "--format=%an|%ae|%aI", f"{base}..origin/{branch}", "--ancestry-path", "-1"],
        cwd=cwd,
        check=False,
    )

    if result.returncode != 0 or not result.stdout.strip():
        # Try without ancestry-path as fallback
        result = run_git(
            ["log", "--reverse", "--format=%an|%ae|%aI", f"{base}..origin/{branch}", "-1"],
            cwd=cwd,
            check=False,
        )

    if result.returncode != 0 or not result.stdout.strip():
        return {}

    parts = result.stdout.strip().split("|")
    if len(parts) >= 3:
        return {
            "author": parts[0],
            "email": parts[1],
            "date": parts[2],
        }

    return {}


def get_all_remote_branches(cwd: Optional[Path] = None, patterns: Optional[list] = None) -> list[str]:
    """Get all remote branch names, optionally filtered by patterns.

    Args:
        cwd: Working directory
        patterns: Optional list of patterns to match (e.g., ['feature/*', 'hotfix/*'])

    Returns:
        List of branch names (without 'origin/' prefix)
    """
    result = run_git(["branch", "-r", "--list"], cwd=cwd, check=False)
    if result.returncode != 0:
        return []

    branches = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line or "->" in line:  # Skip HEAD -> origin/main
            continue
        if line.startswith("origin/"):
            branch = line[7:]  # Remove 'origin/' prefix
            if patterns:
                import fnmatch
                if any(fnmatch.fnmatch(branch, p) for p in patterns):
                    branches.append(branch)
            else:
                branches.append(branch)

    return branches


def reconcile_tracking(
    tracking_path: Path,
    repo_root: Path,
    discover_all: bool = False,
    branch_patterns: Optional[list] = None,
    protected_branches: Optional[list] = None,
) -> Dict[str, Any]:
    """Reconcile JSONL tracking with actual git state.

    This is the main sync function that:
    1. Updates local_worktree, remote_exists, remote_ahead for existing entries
    2. Removes entries where both local and remote are gone
    3. Optionally discovers untracked remote branches (--all mode)

    Args:
        tracking_path: Path to the JSONL tracking file
        repo_root: Path to the repository root
        discover_all: If True, also discover untracked remote branches
        branch_patterns: Patterns to match when discovering (e.g., ['feature/*'])
        protected_branches: List of protected branch names to skip

    Returns:
        Summary dict with reconciliation results
    """
    # Fetch latest from remote first
    run_git(["fetch", "--all", "--prune"], cwd=repo_root, check=False)

    entries = load_tracking_jsonl(tracking_path)
    protected = protected_branches or ["main", "master", "develop"]

    removed = []
    updated = []
    warnings = []
    discovered = []

    # Determine worktree base from tracking path
    worktree_base = tracking_path.parent

    # Update existing entries
    remaining_entries = []
    for entry in entries:
        # Check if local worktree still exists
        local_exists = Path(entry.path).exists() if entry.path else False
        entry.local_worktree = local_exists

        # Check if remote branch exists
        remote_exists = check_remote_branch_exists(entry.branch, cwd=repo_root)
        entry.remote_exists = remote_exists

        # Check remote ahead count
        if remote_exists and local_exists:
            ahead_count = get_remote_ahead_count(entry.branch, cwd=repo_root)
            if ahead_count >= 0:
                entry.remote_ahead = ahead_count
                if ahead_count > 0:
                    warnings.append({
                        "branch": entry.branch,
                        "message": f"Remote is {ahead_count} commit(s) ahead",
                        "remote_ahead": ahead_count,
                    })
        else:
            entry.remote_ahead = 0

        # Update timestamp
        entry.last_checked = _dt.datetime.now(_dt.timezone.utc).isoformat()

        # Decide whether to keep or remove
        if not local_exists and not remote_exists:
            # Both gone - remove entry
            removed.append(entry.branch)
        else:
            remaining_entries.append(entry)
            updated.append(entry.branch)

    # Discover untracked remote branches if requested
    if discover_all:
        tracked_branches = {e.branch for e in remaining_entries}
        default_patterns = branch_patterns or ["feature/*", "hotfix/*", "bugfix/*", "release/*"]

        remote_branches = get_all_remote_branches(cwd=repo_root, patterns=default_patterns)

        for branch in remote_branches:
            if branch in tracked_branches:
                continue
            if branch in protected:
                continue

            # Get creator info from first commit
            # Try multiple base branches
            creator_info = {}
            for base in ["main", "master", "develop"]:
                creator_info = get_branch_creator_info(branch, base=base, cwd=repo_root)
                if creator_info:
                    break

            # Create new entry
            new_entry = TrackingEntry(
                branch=branch,
                path=str(worktree_base / branch),
                base="unknown",
                owner=creator_info.get("author", "unknown"),
                purpose="",
                created=creator_info.get("date", _dt.datetime.now(_dt.timezone.utc).isoformat()),
                status="discovered",
                last_checked=_dt.datetime.now(_dt.timezone.utc).isoformat(),
                remote_exists=True,
                local_worktree=False,
                remote_ahead=0,
            )
            remaining_entries.append(new_entry)
            discovered.append({
                "branch": branch,
                "owner": new_entry.owner,
                "created": new_entry.created,
            })

    # Save updated entries
    save_tracking_jsonl(tracking_path, remaining_entries)

    return {
        "total": len(remaining_entries),
        "updated": len(updated),
        "removed": removed,
        "discovered": discovered,
        "warnings": warnings,
    }
