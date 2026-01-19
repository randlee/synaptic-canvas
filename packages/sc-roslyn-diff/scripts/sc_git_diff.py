#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from roslyn_diff_runner import (
    AUTO_OUTPUT,
    DiffPair,
    aggregate_counts,
    ensure_roslyn_diff,
    load_json_stdin,
    process_pairs,
    resolve_repo_root,
    run_command,
    write_json,
)


SETTINGS_RELATIVE = Path(".sc/roslyn-diff/settings.json")


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


def load_settings(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / SETTINGS_RELATIVE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save_settings(repo_root: Path, settings: Dict[str, Any]) -> None:
    path = repo_root / SETTINGS_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2))


def detect_provider(remote_url: str, pr_url: Optional[str]) -> str:
    combined = (pr_url or "") + " " + remote_url
    if "dev.azure.com" in combined or "visualstudio.com" in combined:
        return "azure"
    if "github.com" in combined:
        return "github"
    return "unknown"


def parse_github_pr_url(url: str) -> Optional[Tuple[str, str, str]]:
    match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if not match:
        return None
    owner, repo, pr = match.group(1), match.group(2), match.group(3)
    return owner, repo, pr


def parse_azure_pr_url(url: str) -> Optional[Tuple[str, str, str, str]]:
    match = re.search(r"dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)/pullrequest/(\d+)", url)
    if match:
        return match.group(1), match.group(2), match.group(3), match.group(4)
    match = re.search(r"([^/.]+)\.visualstudio\.com/([^/]+)/_git/([^/]+)/pullrequest/(\d+)", url)
    if match:
        return match.group(1), match.group(2), match.group(3), match.group(4)
    return None


def parse_azure_remote(remote_url: str) -> Optional[Tuple[str, str, str]]:
    match = re.search(r"dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)", remote_url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    match = re.search(r"([^/.]+)\.visualstudio\.com/([^/]+)/_git/([^/]+)", remote_url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None


def parse_github_remote(remote_url: str) -> Optional[Tuple[str, str]]:
    match = re.search(r"github\.com[:/]{1}([^/]+)/([^/]+?)(?:\.git)?$", remote_url)
    if match:
        return match.group(1), match.group(2)
    return None


def resolve_refs_github(pr_number: str) -> Optional[Tuple[str, str]]:
    if not shutil.which("gh"):
        return None
    code, out, _ = run_command(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "baseRefName,headRefName",
            "--jq",
            ".baseRefName + \"|\" + .headRefName",
        ]
    )
    if code != 0 or "|" not in out:
        return None
    base, head = out.strip().split("|", 1)
    return base, head


def resolve_refs_azure(pr_number: str, org: Optional[str], project: Optional[str]) -> Optional[Tuple[str, str]]:
    if not shutil.which("az"):
        return None
    cmd = ["az", "repos", "pr", "show", "--id", str(pr_number), "--query", "{base:targetRefName,head:sourceRefName}", "-o", "json"]
    if org:
        cmd += ["--organization", org]
    if project:
        cmd += ["--project", project]
    code, out, _ = run_command(cmd)
    if code != 0:
        return None
    try:
        payload = json.loads(out)
    except Exception:
        return None
    base = payload.get("base")
    head = payload.get("head")
    if base and head:
        return base, head
    return None


def ensure_ref_available(ref: str) -> None:
    run_command(["git", "fetch", "origin", ref])


def list_changed_files(base_ref: str, head_ref: str) -> List[str]:
    code, out, _ = run_command(["git", "diff", "--name-only", f"{base_ref}..{head_ref}"])
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def git_show_to_temp(ref: str, path: str) -> Optional[Path]:
    code, out, _ = run_command(["git", "show", f"{ref}:{path}"])
    if code != 0:
        return None
    fd, name = tempfile.mkstemp(suffix=Path(path).suffix)
    os.close(fd)
    Path(name).write_text(out)
    return Path(name)


def main() -> int:
    params = load_json_stdin()
    pr_url = params.get("pr_url")
    pr_number = params.get("pr_number")
    base_ref = params.get("base_ref")
    head_ref = params.get("head_ref")
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
    text_output = params.get("text_output")
    git_output = params.get("git_output")

    repo_root = resolve_repo_root(params.get("repo_root"))

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

    code, remote_url, _ = run_command(["git", "config", "--get", "remote.origin.url"])
    remote_url = remote_url.strip() if code == 0 else ""

    provider = detect_provider(remote_url, pr_url)
    settings = load_settings(repo_root)

    if not base_ref or not head_ref:
        if pr_url:
            if provider == "github":
                parsed = parse_github_pr_url(pr_url)
                if parsed:
                    pr_number = parsed[2]
            elif provider == "azure":
                parsed = parse_azure_pr_url(pr_url)
                if parsed:
                    org, project, repo, pr_number = parsed
                    settings.setdefault("azure", {})
                    settings["azure"].update({"organization": org, "project": project, "repo": repo})
                    save_settings(repo_root, settings)
        if pr_number:
            if provider == "github":
                refs = resolve_refs_github(str(pr_number))
                if refs:
                    base_ref, head_ref = refs
            elif provider == "azure":
                azure_cfg = settings.get("azure", {})
                refs = resolve_refs_azure(str(pr_number), azure_cfg.get("organization"), azure_cfg.get("project"))
                if refs:
                    base_ref, head_ref = refs

    if not base_ref or not head_ref:
        write_json(
            _error(
                "diff.missing_refs",
                "Could not resolve base/head refs",
                False,
                "Provide base_ref/head_ref or a valid PR URL/number",
            )
        )
        return 1

    ensure_ref_available(base_ref)
    ensure_ref_available(head_ref)

    changed_files = list_changed_files(base_ref, head_ref)
    if len(changed_files) > max_pairs and not allow_large:
        write_json(
            _error(
                "diff.too_large",
                "Pair count exceeds max_pairs without allow_large",
                True,
                "Use --allow-large or reduce scope",
            )
        )
        return 1

    temp_files: List[Path] = []
    pairs: List[DiffPair] = []
    for path in changed_files:
        warnings: List[str] = []
        old_temp = git_show_to_temp(base_ref, path)
        new_temp = git_show_to_temp(head_ref, path)
        if old_temp is None:
            old_temp = Path(tempfile.mkstemp(suffix=Path(path).suffix)[1])
            warnings.append("old_missing")
        if new_temp is None:
            new_temp = Path(tempfile.mkstemp(suffix=Path(path).suffix)[1])
            warnings.append("new_missing")
        temp_files.extend([old_temp, new_temp])
        pairs.append(DiffPair(old_path=old_temp, new_path=new_temp, rel_path=path, kind="git", warnings=warnings))

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
    label_prefix = f"{base_ref.replace('/', '_')}__{head_ref.replace('/', '_')}"
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

    identical_count, diff_count, errors_count = aggregate_counts(results)

    write_json(
        {
            "success": True,
            "data": {
                "refs": {"base": base_ref, "head": head_ref},
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
