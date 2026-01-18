#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    default_root = Path(__file__).resolve().parents[3]
    if "SC_REPO_PATH" in os.environ:
        return Path(os.environ["SC_REPO_PATH"]).expanduser()
    return default_root


def default_global_claude_dir() -> Path:
    if "GLOBAL_CLAUDE_DIR" in os.environ:
        return Path(os.environ["GLOBAL_CLAUDE_DIR"]).expanduser()
    return Path.home() / ".claude"


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


def artifacts_from_manifest(manifest: Dict[str, Any]) -> List[str]:
    artifacts = manifest.get("artifacts") or {}
    items: List[str] = []
    for key in ("commands", "skills", "agents", "scripts"):
        for rel in artifacts.get(key, []) or []:
            items.append(str(rel))
    return items


def any_artifact_installed(dest: Path, artifacts: List[str]) -> bool:
    for rel in artifacts:
        if (dest / rel).exists():
            return True
    return False


def resolve_dest(scope: str, global_claude_dir: Path) -> Tuple[Optional[Path], Optional[str]]:
    if scope == "global":
        return global_claude_dir, None
    repo_root = resolve_repo_root()
    if repo_root is None:
        return None, "Local scope requires a git repo"
    return repo_root / ".claude", None


def run_install(sc_repo_path: Path, package: str, dest: Path) -> Tuple[int, str, str]:
    cmd = ["python3", str(sc_repo_path / "tools" / "sc-install.py"), "install", package, "--dest", str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def run_uninstall(sc_repo_path: Path, package: str, dest: Path) -> Tuple[int, str, str]:
    cmd = ["python3", str(sc_repo_path / "tools" / "sc-install.py"), "uninstall", package, "--dest", str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr
