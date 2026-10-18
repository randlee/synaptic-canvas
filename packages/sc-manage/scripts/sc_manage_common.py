#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TARGETS = ("claude", "codex", "cursor", "hermes")


def selected_targets(params: Dict[str, Any]) -> List[str]:
    if "targets" in params and "target" in params:
        raise ValueError("Provide targets or target, not both")
    targets = params.get("targets", [params.get("target", "claude")])
    if (not isinstance(targets, list) or not targets or
            any(not isinstance(target, str) or target not in TARGETS for target in targets)):
        raise ValueError("targets must be a nonempty list of claude, codex, cursor, hermes")
    return [target for target in TARGETS if target in targets]


def valid_package(package: Any) -> bool:
    return isinstance(package, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", package) is not None


def report_error(code: str, message: str, *, data: Any = None) -> int:
    print(json.dumps({"success": False, "data": data, "error": {
        "code": code, "message": message, "recoverable": True,
        "suggested_action": "Check the package, scope and explicit target flags"}}))
    return 1


def target_roots(params: Dict[str, Any], target: str) -> Tuple[Path, Path]:
    """Global/user roots; project roots never inherit profile overrides."""
    if target == "claude":
        return (Path(params.get("global_claude_dir", default_global_claude_dir())).expanduser(),
                Path(params.get("user_claude_dir", default_user_claude_dir())).expanduser())
    profile = os.environ.get(f"{target.upper()}_HOME") if target in ("codex", "hermes") else None
    default = Path(profile).expanduser() if profile else Path.home() / f".{target}"
    global_root = Path(params.get(f"global_{target}_dir", os.environ.get(f"GLOBAL_{target.upper()}_DIR", default))).expanduser()
    user_root = Path(params.get(f"user_{target}_dir", os.environ.get(f"USER_{target.upper()}_DIR", global_root))).expanduser()
    return global_root, user_root

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def read_json_stdin() -> Dict[str, Any]:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def resolve_repo_root() -> Optional[Path]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        root = result.stdout.strip()
        return Path(root) if root else None
    except Exception:
        return None


def default_sc_repo_path() -> Path:
    if "SC_REPO_PATH" in os.environ:
        return Path(os.environ["SC_REPO_PATH"]).expanduser()
    script = Path(__file__).resolve()
    candidates = list(script.parents)
    source_record = script.with_name("sc_manage_source.json")
    try:
        record = json.loads(source_record.read_text(encoding="utf-8"))
        if isinstance(record, dict) and isinstance(record.get("sc_repo_path"), str):
            candidates.insert(0, Path(record["sc_repo_path"]).expanduser())
    except (OSError, ValueError):
        pass
    # Claude's marketplace plugin cache contains a package, not necessarily the
    # complete source checkout. Its marketplace record can identify the latter.
    try:
        marketplaces = json.loads((Path.home() / ".claude/plugins/known_marketplaces.json").read_text(encoding="utf-8"))
        marketplace = marketplaces.get("synaptic-canvas", {}) if isinstance(marketplaces, dict) else {}
        location = marketplace.get("installLocation") if isinstance(marketplace, dict) else None
        if isinstance(location, str):
            candidates.append(Path(location).expanduser())
    except (OSError, ValueError):
        pass
    for candidate in candidates:
        if ((candidate / "tools/sc-install.py").is_file()
                and (candidate / "packages/sc-manage/manifest.yaml").is_file()):
            return candidate
    return script.parents[3]


def default_global_claude_dir() -> Path:
    if "GLOBAL_CLAUDE_DIR" in os.environ:
        return Path(os.environ["GLOBAL_CLAUDE_DIR"]).expanduser()
    return Path.home() / ".claude"

def default_user_claude_dir() -> Path:
    if "USER_CLAUDE_DIR" in os.environ:
        return Path(os.environ["USER_CLAUDE_DIR"]).expanduser()
    return Path.home() / ".claude"


def normalize_scope(scope: str) -> str:
    return {"project": "local"}.get(scope, scope)


def parse_manifest(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(raw) or {}

    data: Dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key in {"name", "version", "description"}:
            data[key] = value
    return data


def list_manifests(sc_repo_path: Path) -> List[Path]:
    manifests: List[Path] = []
    packages_dir = sc_repo_path / "packages"
    if not packages_dir.is_dir():
        return manifests
    for pkg_dir in packages_dir.iterdir():
        manifest = pkg_dir / "manifest.yaml"
        if manifest.exists():
            manifests.append(manifest)
    return sorted(manifests)


def manifest_scope(manifest: Dict[str, Any]) -> str:
    install = manifest.get("install") or {}
    scope = install.get("scope")
    if scope in {"local-only", "global-only", "both"}:
        return scope
    return "both"


def artifacts_from_manifest(manifest: Dict[str, Any], target: str = "claude") -> List[str]:
    artifacts = manifest.get("artifacts") or {}
    items: List[str] = []
    categories = ("commands", "skills", "agents", "scripts", "assets") if target == "claude" else ("skills", "scripts", "assets")
    for key in categories:
        for rel in artifacts.get(key, []) or []:
            items.append(str(rel))
    return items


def any_artifact_installed(dest: Path, artifacts: List[str]) -> bool:
    for rel in artifacts:
        if (dest / rel).exists():
            return True
    return False


def resolve_dest(
    scope: str,
    global_claude_dir: Path,
    user_claude_dir: Optional[Path] = None,
    target: str = "claude",
) -> Tuple[Optional[Path], Optional[str]]:
    scope = normalize_scope(scope)
    if scope == "user":
        return (user_claude_dir or global_claude_dir), None
    if scope == "global":
        return global_claude_dir, None
    repo_root = resolve_repo_root()
    if repo_root is None:
        return None, "Local scope requires a git repo"
    return repo_root / f".{target}", None


def run_install(sc_repo_path: Path, package: str, dest: Path, target: str = "claude") -> Tuple[int, str, str]:
    cmd = ["python3", str(sc_repo_path / "tools" / "sc-install.py"), "install", package, "--dest", str(dest)]
    if target != "claude":
        cmd.append(f"--{target}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def run_uninstall(sc_repo_path: Path, package: str, dest: Path, target: str = "claude") -> Tuple[int, str, str]:
    cmd = ["python3", str(sc_repo_path / "tools" / "sc-install.py"), "uninstall", package, "--dest", str(dest)]
    if target != "claude":
        cmd.append(f"--{target}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr
