#!/usr/bin/env python3
"""
sc-startup-init agent implementation.
- Detects config and candidate prompt/checklist paths
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from pydantic import BaseModel, Field, ValidationError

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - runtime dependency handling
    yaml = None


class InitParams(BaseModel):
    repo_root: str = Field(..., description="Absolute path to repo root")
    config_path: str = Field(default=".claude/sc-startup.yaml")
    readonly: bool | None = None
    detect_plugins: bool = True

    model_config = {"extra": "ignore"}


def _error(code: str, message: str, recoverable: bool, suggested_action: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "success": False,
        "canceled": False,
        "aborted_by": None,
        "data": data,
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
            "suggested_action": suggested_action,
        },
        "metadata": {"tool_calls": [], "duration_ms": 0},
    }


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _resolve_repo_relative(repo_root: Path, rel_path: str) -> Path:
    candidate = Path(rel_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (repo_root / candidate).resolve()
    if not _is_relative_to(resolved, repo_root):
        raise ValueError("path escapes repo root")
    return resolved


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _find_plugin(plugins: Iterable[Dict[str, Any]], name: str) -> Dict[str, Any]:
    for plugin in plugins:
        if plugin.get("name") == name:
            return plugin
    return {}


def _detect_plugins(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.is_file():
        raise FileNotFoundError("marketplace.json missing")
    data = json.loads(marketplace_path.read_text(encoding="utf-8"))
    entries = data.get("plugins", []) or []
    result: Dict[str, Dict[str, Any]] = {}
    for name in ("sc-ci-automation", "sc-git-worktree", "sc-startup"):
        match = _find_plugin(entries, name)
        installed = bool(match)
        result[name] = {
            "installed": installed,
            "version": match.get("version") if installed else None,
        }
    return result


def _collect_candidates(repo_root: Path, patterns: List[str], limit: int = 10, max_collect: int = 120) -> List[str]:
    found: List[Path] = []
    seen: Set[Path] = set()
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(resolved)
            if len(found) >= max_collect:
                break
        if len(found) >= max_collect:
            break
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    trimmed = found[:limit]
    return [str(p.relative_to(repo_root).as_posix()) for p in trimmed]


def _yaml_payload(
    startup_prompt: Optional[str],
    checklist: Optional[str],
    worktree_scan: Optional[str],
    pr_enabled: Optional[bool],
    worktree_enabled: Optional[bool],
) -> str:
    lines = [
        f"startup-prompt: {startup_prompt or ''}".rstrip(),
        f"check-list: {checklist or ''}".rstrip(),
        f"worktree-scan: {worktree_scan or 'scan'}",
        f"pr-enabled: {'true' if pr_enabled is not False else 'false'}",
        f"worktree-enabled: {'true' if worktree_enabled is not False else 'false'}",
    ]
    return "\n".join(lines) + "\n"


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        parsed = InitParams.model_validate(params)
    except ValidationError as exc:
        return _error("INPUT.MISSING", str(exc), False, "Provide required inputs")

    repo_root = Path(parsed.repo_root).expanduser().resolve()
    if not repo_root.is_dir():
        return _error("VALIDATION.INVALID_REPO", f"repo_root not found: {repo_root}", False, "Pass a valid repo_root")

    try:
        config_abs = _resolve_repo_relative(repo_root, parsed.config_path)
    except ValueError:
        return _error(
            "VALIDATION.INVALID_PATH",
            f"config_path escapes repo_root: {parsed.config_path}",
            False,
            "Use a repo-root-relative path",
        )

    config: Dict[str, Any] = {}
    config_found = config_abs.is_file()
    if config_found:
        try:
            config = _load_yaml(config_abs)
        except Exception as exc:
            return _error("FORMAT.INVALID_YAML", f"Invalid YAML: {exc}", False, "Fix YAML in config file")

    candidates = {
        "startup_prompt": _collect_candidates(
            repo_root,
            [
                "pm/**/*prompt*.md",
                "pm/**/*startup*.md",
                "pm/**/ARCH-*.md",
                "project*/**/*prompt*.md",
                "project*/**/*startup*.md",
                "README*.md",
            ],
        ),
        "checklist": _collect_candidates(
            repo_root,
            [
                "pm/**/*checklist*.md",
                "project*/**/*checklist*.md",
                "**/*checklist*.md",
            ],
        ),
    }

    plugins: Dict[str, Dict[str, Any]] = {}
    if parsed.detect_plugins:
        try:
            plugins = _detect_plugins(repo_root)
        except FileNotFoundError:
            return _error(
                "DEPENDENCY.MISSING",
                "marketplace.json not found",
                True,
                "Ensure .claude-plugin/marketplace.json exists",
            )
        except Exception as exc:
            return _error("SCAN.IO", f"plugin detection failed: {exc}", True, "Retry or disable detect_plugins")

    required = ["startup-prompt", "check-list"]
    optional = ["worktree-scan", "pr-enabled", "worktree-enabled"]
    missing_keys = [k for k in required + optional if k not in config]

    startup_prompt = config.get("startup-prompt") or (candidates["startup_prompt"][0] if candidates["startup_prompt"] else None)
    checklist = config.get("check-list") or (candidates["checklist"][0] if candidates["checklist"] else None)

    data = {
        "config_found": config_found,
        "config_path": str(Path(parsed.config_path).as_posix()),
        "config": config,
        "missing_keys": missing_keys,
        "plugins": plugins,
        "candidates": candidates,
        "yaml": _yaml_payload(
            startup_prompt=startup_prompt,
            checklist=checklist,
            worktree_scan=config.get("worktree-scan"),
            pr_enabled=config.get("pr-enabled"),
            worktree_enabled=config.get("worktree-enabled"),
        ),
    }

    if not config_found:
        return _error(
            "VALIDATION.MISSING_CONFIG",
            "Config not found",
            True,
            "Create .claude/sc-startup.yaml or run init",
            data=data,
        )

    return {
        "success": True,
        "canceled": False,
        "aborted_by": None,
        "data": data,
        "error": None,
        "metadata": {"tool_calls": [], "duration_ms": 0},
    }


def main() -> int:
    try:
        params = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print(json.dumps(_error("INPUT.INVALID_JSON", "Could not parse input JSON", False, "Fix input and retry")))
        return 1

    result = run(params)
    print(json.dumps(result))
    return 0 if result.get("success") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
