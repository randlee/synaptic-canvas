#!/usr/bin/env python3
"""
sc-checklist-status agent implementation.
- Scans repo for TODO/FIXME/NOTE and untracked files
- Optionally updates checklist
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from os import environ
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError


class ChecklistParams(BaseModel):
    checklist_path: str = Field(..., description="Repo-root-relative path to checklist")
    repo_root: str = Field(..., description="Absolute path to repo root")
    mode: str = "update"  # update | report
    readonly: bool | None = None

    model_config = {"extra": "ignore"}


TODO_RE = re.compile(r"\b(TODO|FIXME|NOTE)\b[:\s-]*(.*)", re.IGNORECASE)
MAX_FILE_BYTES = 512 * 1024
MAX_FINDINGS = 40
MAX_SCAN_FILES = 2000
MAX_SCAN_SECONDS = 5


def _error(code: str, message: str, recoverable: bool, suggested_action: str) -> Dict[str, Any]:
    return {
        "success": False,
        "canceled": False,
        "aborted_by": None,
        "data": None,
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
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _load_settings_paths(repo_root: Path) -> List[Path]:
    project_dir = environ.get("CLAUDE_PROJECT_DIR") or environ.get("CODEX_PROJECT_DIR") or str(repo_root)
    codex_home = environ.get("CODEX_HOME")
    paths = [
        Path("~/.claude/settings.json").expanduser(),
        Path(project_dir) / ".claude" / "settings.json",
        Path("~/.codex/settings.json").expanduser(),
        Path(project_dir) / ".codex" / "settings.json",
    ]
    if codex_home:
        paths.append(Path(codex_home) / "settings.json")
    return [p for p in paths if p.exists()]


def _load_allowed_dirs(repo_root: Path) -> List[Path]:
    allowed = {repo_root.resolve(), Path.cwd().resolve()}
    project_dir = environ.get("CLAUDE_PROJECT_DIR") or environ.get("CODEX_PROJECT_DIR")
    if project_dir:
        allowed.add(Path(project_dir).expanduser().resolve())

    for settings_path in _load_settings_paths(repo_root):
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        extra = data.get("permissions", {}).get("additionalDirectories", [])
        if not isinstance(extra, list):
            continue
        for entry in extra:
            if not isinstance(entry, str) or not entry.strip():
                continue
            allowed.add(Path(entry).expanduser().resolve())

    return list(allowed)


def _is_allowed_path(path: Path, allowed_dirs: List[Path]) -> bool:
    for base in allowed_dirs:
        if _is_relative_to(path, base):
            return True
    return False


def _run_git(repo_root: Path, args: List[str], timeout: int = 10) -> Tuple[int, bytes, bytes]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root)] + args,
        capture_output=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _git_tracked_files(repo_root: Path) -> List[Path]:
    code, out, _ = _run_git(repo_root, ["ls-files", "-z"])
    if code != 0:
        raise RuntimeError("git ls-files failed")
    files = [repo_root / p.decode("utf-8", "ignore") for p in out.split(b"\x00") if p]
    return files


def _git_untracked_files(repo_root: Path) -> List[Path]:
    code, out, _ = _run_git(repo_root, ["ls-files", "--others", "--exclude-standard", "-z"])
    if code != 0:
        raise RuntimeError("git ls-files --others failed")
    return [repo_root / p.decode("utf-8", "ignore") for p in out.split(b"\x00") if p]


def _git_modified_files(repo_root: Path) -> List[Path]:
    code, out, _ = _run_git(repo_root, ["status", "--porcelain", "-z"])
    if code != 0:
        raise RuntimeError("git status failed")
    files = []
    for entry in out.split(b"\x00"):
        if not entry:
            continue
        status = entry[:2].decode("utf-8", "ignore")
        path = entry[3:].decode("utf-8", "ignore")
        if status.strip() and path:
            files.append(repo_root / path)
    return files


def _parse_checklist(lines: Iterable[str]) -> List[str]:
    items: List[str] = []
    for line in lines:
        m = re.match(r"^\s*[-*]\s+\[[ xX]\]\s+(.*)$", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _scan_todos(repo_root: Path, files: List[Path]) -> List[str]:
    findings: List[str] = []
    start = time.time()
    for path in files[:MAX_SCAN_FILES]:
        if time.time() - start >= MAX_SCAN_SECONDS:
            break
        if len(findings) >= MAX_FINDINGS:
            break
        try:
            data = path.read_bytes()
        except Exception:
            continue
        if b"\x00" in data[:1024] or len(data) > MAX_FILE_BYTES:
            continue
        text = data.decode("utf-8", errors="ignore")
        for idx, line in enumerate(text.splitlines(), 1):
            if len(findings) >= MAX_FINDINGS:
                break
            match = TODO_RE.search(line)
            if not match:
                continue
            tag = match.group(1).upper()
            detail = match.group(2).strip()
            rel = path.relative_to(repo_root).as_posix()
            suffix = f" {detail}" if detail else ""
            findings.append(f"{tag} {rel}:{idx}{suffix}")
    return findings


def _matches_existing(item: str, existing: List[str]) -> bool:
    item_low = item.lower()
    for entry in existing:
        if item_low in entry.lower():
            return True
    return False


def _atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tmp:
        tmp.write(content)
        temp_name = tmp.name
    Path(temp_name).replace(path)


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        parsed = ChecklistParams.model_validate(params)
    except ValidationError as exc:
        return _error("INPUT.MISSING", str(exc), False, "Provide checklist_path and repo_root")

    repo_root = Path(parsed.repo_root).expanduser().resolve()
    if not repo_root.is_dir():
        return _error("VALIDATION.INVALID_PATH", f"repo_root not found: {repo_root}", False, "Provide a valid repo_root")

    checklist_abs = _resolve_repo_relative(repo_root, parsed.checklist_path)

    allowed_dirs = _load_allowed_dirs(repo_root)
    if not _is_allowed_path(checklist_abs, allowed_dirs):
        return _error(
            "VALIDATION.INVALID_PATH",
            "Security warning: checklist_path is outside allowed directories",
            False,
            "Add the directory to permissions.additionalDirectories or use a repo-root-relative path",
        )

    if not checklist_abs.is_file():
        return _error(
            "VALIDATION.MISSING_CHECKLIST",
            "Checklist file not found",
            True,
            "Create the checklist or update config",
        )

    mode = "report" if parsed.readonly else parsed.mode

    try:
        checklist_text = checklist_abs.read_text(encoding="utf-8")
    except Exception as exc:
        return _error("IO.READ_FAILURE", f"Could not read checklist: {exc}", True, "Check file permissions")

    existing = _parse_checklist(checklist_text.splitlines())

    try:
        tracked = _git_tracked_files(repo_root)
        untracked = _git_untracked_files(repo_root)
        modified = _git_modified_files(repo_root)
    except Exception as exc:
        return _error("SCAN.UNREADABLE", str(exc), True, "Ensure git is installed and repo is valid")

    findings = _scan_todos(repo_root, tracked)
    missing = [item for item in findings if not _matches_existing(item, existing)]

    notes: List[str] = []
    if untracked:
        notes.append(f"Untracked files: {len(untracked)}")
    if modified:
        notes.append(f"Modified files: {len(modified)}")
        for path in modified[:10]:
            rel = path.relative_to(repo_root).as_posix()
            item = f"Review recent changes in {rel}"
            if not _matches_existing(item, existing) and item not in missing:
                missing.append(item)

    added: List[str] = []
    if mode == "update" and missing:
        appended = checklist_text.rstrip() + "\n"
        for item in missing:
            appended += f"- [ ] {item}\n"
            added.append(item)
        try:
            _atomic_write(checklist_abs, appended)
        except Exception as exc:
            return _error("IO.WRITE_FAILURE", f"Checklist update failed: {exc}", True, "Check file permissions")

    synced = not missing or (mode == "update" and len(added) == len(missing))

    return {
        "success": True,
        "canceled": False,
        "aborted_by": None,
        "data": {
            "synced": synced,
            "added": added,
            "missing": missing,
            "notes": notes,
        },
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
