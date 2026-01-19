#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

AUTO_OUTPUT = "__auto__"


@dataclass
class DiffPair:
    old_path: Path
    new_path: Path
    rel_path: Optional[str]
    kind: str
    warnings: List[str]


def load_json_stdin() -> Dict[str, Any]:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def write_json(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload))


def run_command(
    cmd: Sequence[str],
    cwd: Optional[Path] = None,
    capture_output: bool = True,
) -> Tuple[int, str, str]:
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
        stderr=subprocess.PIPE if capture_output else subprocess.DEVNULL,
        text=True,
    )
    if not capture_output:
        return proc.returncode, "", ""
    return proc.returncode, proc.stdout, proc.stderr


def resolve_repo_root(repo_root: Optional[str] = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    code, out, _ = run_command(["git", "rev-parse", "--show-toplevel"])
    if code == 0:
        return Path(out.strip()).resolve()
    return Path.cwd().resolve()


def ensure_roslyn_diff() -> None:
    if shutil.which("roslyn-diff"):
        code, _, _ = run_command(["dotnet", "tool", "update", "-g", "roslyn-diff"], capture_output=False)
        if code == 0:
            return
    code, _, _ = run_command(["dotnet", "tool", "install", "-g", "roslyn-diff"], capture_output=False)
    if code != 0 and not shutil.which("roslyn-diff"):
        raise RuntimeError("roslyn-diff tool install failed")


def parse_pair_list(value: str) -> Tuple[str, str]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if len(parts) != 2:
        raise ValueError("Expected exactly two comma-delimited paths")
    return parts[0], parts[1]


def normalize_display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root))
    except Exception:
        return str(path.resolve())


def create_empty_temp(suffix: str = "") -> Path:
    fd, name = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return Path(name)


def list_folder_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for filename in filenames:
            files.append(Path(dirpath) / filename)
    return files


def build_pairs_for_folders(old_root: Path, new_root: Path) -> Tuple[List[DiffPair], List[Path]]:
    old_files = list_folder_files(old_root)
    new_files = list_folder_files(new_root)

    old_map = {str(f.relative_to(old_root)): f for f in old_files}
    new_map = {str(f.relative_to(new_root)): f for f in new_files}

    all_rel = sorted(set(old_map.keys()) | set(new_map.keys()))
    pairs: List[DiffPair] = []
    temp_files: List[Path] = []

    for rel in all_rel:
        old_path = old_map.get(rel)
        new_path = new_map.get(rel)
        warnings: List[str] = []
        suffix = Path(rel).suffix

        if old_path is None:
            old_path = create_empty_temp(suffix)
            temp_files.append(old_path)
            warnings.append("old_missing")
        if new_path is None:
            new_path = create_empty_temp(suffix)
            temp_files.append(new_path)
            warnings.append("new_missing")

        pairs.append(DiffPair(old_path=old_path, new_path=new_path, rel_path=rel, kind="file", warnings=warnings))

    return pairs, temp_files


def sanitize_filename(value: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return base.strip("_") or "diff"


def open_html(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif sys.platform.startswith("win"):
        subprocess.Popen(["cmd", "/c", "start", "", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def run_roslyn_diff(
    old_path: Path,
    new_path: Path,
    mode: str,
    html: bool,
    output_dir: Path,
    label: str,
    ignore_whitespace: bool,
    context_lines: Optional[int],
    text_output: Optional[Path],
    git_output: Optional[Path],
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    fd, json_name = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    json_file = Path(json_name)
    html_path: Optional[Path] = None

    cmd = ["roslyn-diff", "diff", str(old_path), str(new_path), "--json", str(json_file), "--quiet", "--no-color"]
    if mode in {"line", "roslyn"}:
        cmd += ["--mode", mode]
    if ignore_whitespace:
        cmd += ["--ignore-whitespace"]
    if context_lines is not None:
        cmd += ["--context", str(context_lines)]
    if html:
        html_path = output_dir / f"{sanitize_filename(label)}.html"
        cmd += ["--html", str(html_path)]
    if text_output:
        cmd += ["--text", str(text_output)]
    if git_output:
        cmd += ["--git", str(git_output)]

    code, _, stderr = run_command(cmd)

    roslyn_payload: Optional[Dict[str, Any]] = None
    if json_file.exists():
        try:
            roslyn_payload = json.loads(json_file.read_text())
        except Exception:
            roslyn_payload = None
    try:
        json_file.unlink(missing_ok=True)
    except Exception:
        pass

    result: Dict[str, Any] = {
        "is_identical": code == 0,
        "mode": mode,
        "html_path": str(html_path.resolve()) if html_path else None,
        "text_path": str(text_output.resolve()) if text_output else None,
        "git_path": str(git_output.resolve()) if git_output else None,
        "output_paths": {
            "html": [str(html_path.resolve())] if html_path else [],
            "text": [str(text_output.resolve())] if text_output else [],
            "git": [str(git_output.resolve())] if git_output else [],
        },
        "roslyn": roslyn_payload,
        "warnings": [],
    }

    if code == 2:
        result["error"] = {
            "code": "diff.failed",
            "message": stderr.strip() or "roslyn-diff failed",
        }

    if html_path and code == 1:
        try:
            open_html(html_path)
        except Exception:
            result.setdefault("warnings", []).append("html_open_failed")

    return result


def chunked(items: List[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def process_pairs(
    pairs: List[DiffPair],
    mode: str,
    html: bool,
    output_dir: Path,
    label_prefix: str,
    files_per_agent: int,
    ignore_whitespace: bool,
    context_lines: Optional[int],
    text_output: Union[Path, str, None],
    git_output: Union[Path, str, None],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    temp_dir: Optional[Path] = None

    counter = 0
    for batch in chunked(pairs, max(1, files_per_agent)):
        max_workers = min(4, len(batch)) or 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for pair in batch:
                counter += 1
                label = label_prefix
                if pair.rel_path:
                    label = f"{label_prefix}__{pair.rel_path}"
                text_path = text_output
                git_path = git_output
                if text_output == AUTO_OUTPUT:
                    if temp_dir is None:
                        temp_dir = output_dir / "temp"
                        temp_dir.mkdir(parents=True, exist_ok=True)
                    text_path = temp_dir / f"diff-{counter}.txt"
                if git_output == AUTO_OUTPUT:
                    if temp_dir is None:
                        temp_dir = output_dir / "temp"
                        temp_dir.mkdir(parents=True, exist_ok=True)
                    git_path = temp_dir / f"diff-{counter}.patch"
                futures.append(
                    executor.submit(
                        run_roslyn_diff,
                        pair.old_path,
                        pair.new_path,
                        mode,
                        html,
                        output_dir,
                        label,
                        ignore_whitespace,
                        context_lines,
                        text_path if isinstance(text_path, Path) else None,
                        git_path if isinstance(git_path, Path) else None,
                    )
                )
            for pair, future in zip(batch, futures):
                entry = future.result()
                entry["pair"] = {
                    "kind": pair.kind,
                    "old_path": str(pair.old_path),
                    "new_path": str(pair.new_path),
                    "rel_path": pair.rel_path,
                }
                if pair.warnings:
                    entry.setdefault("warnings", []).extend(pair.warnings)
                results.append(entry)

    return results


def aggregate_counts(results: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    identical = sum(1 for r in results if r.get("is_identical") is True)
    errors = sum(1 for r in results if r.get("error"))
    diff = len(results) - identical - errors
    return identical, diff, errors
