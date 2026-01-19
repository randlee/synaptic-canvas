#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

from roslyn_diff_runner import (
    AUTO_OUTPUT,
    DiffPair,
    aggregate_counts,
    build_pairs_for_folders,
    ensure_roslyn_diff,
    load_json_stdin,
    normalize_display_path,
    parse_pair_list,
    process_pairs,
    resolve_repo_root,
    write_json,
)


def _error(code: str, message: str, recoverable: bool, suggested_action: str) -> Dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
            "suggested_action": suggested_action,
        },
    }


def main() -> int:
    params = load_json_stdin()
    files = params.get("files")
    folders = params.get("folders")
    html = bool(params.get("html", False))
    mode = str(params.get("mode") or "auto").lower()
    if mode not in {"auto", "line", "roslyn"}:
        mode = "auto"
    ignore_whitespace = bool(params.get("ignore_whitespace", False))
    context_lines = params.get("context_lines")
    if context_lines is not None:
        try:
            context_lines = int(context_lines)
        except (TypeError, ValueError):
            write_json(_error("diff.invalid_input", "context_lines must be an integer", False, "Fix context_lines"))
            return 1
    allow_large = bool(params.get("allow_large", False))
    files_per_agent = int(params.get("files_per_agent", 10))
    max_pairs = int(params.get("max_pairs", 100))
    repo_root = resolve_repo_root(params.get("repo_root"))
    text_output = params.get("text_output")
    git_output = params.get("git_output")

    if bool(files) == bool(folders):
        write_json(
            _error(
                "diff.invalid_input",
                "Exactly one of 'files' or 'folders' is required",
                False,
                "Provide a comma-delimited list of two files or two folders",
            )
        )
        return 1

    try:
        ensure_roslyn_diff()
    except RuntimeError as exc:
        write_json(
            _error(
                "diff.tool_missing",
                str(exc),
                False,
                "Install roslyn-diff with 'dotnet tool install -g roslyn-diff'",
            )
        )
        return 1

    pairs: List[DiffPair] = []
    temp_files: List[Path] = []
    label_prefix = "diff"

    if files:
        try:
            old_raw, new_raw = parse_pair_list(files)
        except ValueError as exc:
            write_json(_error("diff.invalid_input", str(exc), False, "Fix --files value"))
            return 1

        old_path = (repo_root / old_raw).resolve() if not Path(old_raw).is_absolute() else Path(old_raw).resolve()
        new_path = (repo_root / new_raw).resolve() if not Path(new_raw).is_absolute() else Path(new_raw).resolve()
        if not old_path.exists() or not new_path.exists():
            write_json(
                _error(
                    "diff.path_missing",
                    "One or both file paths do not exist",
                    False,
                    "Verify the file paths",
                )
            )
            return 1
        pairs = [DiffPair(old_path=old_path, new_path=new_path, rel_path=None, kind="file", warnings=[])]
        label_prefix = f"{old_path.stem}__{new_path.stem}"
    else:
        try:
            old_raw, new_raw = parse_pair_list(folders)
        except ValueError as exc:
            write_json(_error("diff.invalid_input", str(exc), False, "Fix --folders value"))
            return 1

        old_root = (repo_root / old_raw).resolve() if not Path(old_raw).is_absolute() else Path(old_raw).resolve()
        new_root = (repo_root / new_raw).resolve() if not Path(new_raw).is_absolute() else Path(new_raw).resolve()
        if not old_root.exists() or not new_root.exists():
            write_json(
                _error(
                    "diff.path_missing",
                    "One or both folder paths do not exist",
                    False,
                    "Verify the folder paths",
                )
            )
            return 1
        pairs, temp_files = build_pairs_for_folders(old_root, new_root)
        label_prefix = f"{old_root.name}__{new_root.name}"

    if len(pairs) > max_pairs and not allow_large:
        write_json(
            _error(
                "diff.too_large",
                "Pair count exceeds max_pairs without allow_large",
                True,
                "Use --allow-large or reduce scope",
            )
        )
        return 1

    output_dir = repo_root / ".sc" / "roslyn-diff" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    if text_output is True:
        text_output = AUTO_OUTPUT
    elif isinstance(text_output, str) and text_output.strip():
        text_output = Path(text_output)
    else:
        text_output = None
    if git_output is True:
        git_output = AUTO_OUTPUT
    elif isinstance(git_output, str) and git_output.strip():
        git_output = Path(git_output)
    else:
        git_output = None

    results = process_pairs(
        pairs,
        mode,
        html,
        output_dir,
        label_prefix,
        files_per_agent,
        ignore_whitespace,
        context_lines,
        text_output,
        git_output,
    )

    for entry in results:
        entry["pair"]["old_path"] = normalize_display_path(Path(entry["pair"]["old_path"]), repo_root)
        entry["pair"]["new_path"] = normalize_display_path(Path(entry["pair"]["new_path"]), repo_root)

    identical_count, diff_count, errors_count = aggregate_counts(results)

    write_json(
        {
            "success": True,
            "data": {
                "results": results,
                "identical_count": identical_count,
                "diff_count": diff_count,
                "errors_count": errors_count,
            },
            "error": None,
        }
    )

    for temp_file in temp_files:
        try:
            temp_file.unlink(missing_ok=True)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
