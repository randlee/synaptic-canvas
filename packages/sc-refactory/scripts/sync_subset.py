#!/usr/bin/env python3
"""Sync a filtered local subset of rule/doc source files into `.refactor/`."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from runtime import append_json_log, find_repo_root

DOC_REF_RE = re.compile(r"\.refactor/docs/[A-Za-z0-9._/\-]+\.md")
RULE_ID_RE = re.compile(r'ref:ruleId\s+"([^"]+)"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync a local subset of refactor rules into a repo")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-root", default=None, help="Bundle root containing rules/ and docs/")
    parser.add_argument("--profile", default=None, help="Profile name to resolve under profiles/")
    parser.add_argument("--profile-file", default=None, help="Explicit YAML or JSON profile path")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true", help="Remove files synced by the previous run before copying")
    parser.add_argument("--rebuild-db", action="store_true", help="Rebuild .refactor/db after syncing")
    return parser.parse_args()


def load_structured_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if yaml is None:
        raise RuntimeError("PyYAML is required to read YAML sync profiles")
    return yaml.safe_load(text) or {}


def resolve_profile_path(args: argparse.Namespace, repo_root: Path) -> Path | None:
    if args.profile_file:
        return Path(args.profile_file).resolve()
    if not args.profile:
        return None

    candidates = [
        repo_root / ".refactor" / "profiles" / f"{args.profile}.yaml",
        repo_root / ".refactor" / "profiles" / f"{args.profile}.yml",
        repo_root / ".refactor" / "profiles" / f"{args.profile}.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"profile not found: {args.profile}")


def resolve_source_root(args: argparse.Namespace, profile: dict, profile_path: Path | None) -> Path:
    if args.source_root:
        return Path(args.source_root).resolve()
    source_value = profile.get("source_root")
    if source_value:
        source_path = Path(source_value)
        if not source_path.is_absolute() and profile_path is not None:
            source_path = (profile_path.parent / source_path).resolve()
        return source_path.resolve()
    raise RuntimeError("source root is required; pass --source-root or define source_root in the profile")


def load_profile(args: argparse.Namespace, repo_root: Path) -> tuple[dict, Path | None]:
    profile_path = resolve_profile_path(args, repo_root)
    if profile_path is None:
        return {}, None
    if not profile_path.is_file():
        raise RuntimeError(f"profile file not found: {profile_path}")
    return load_structured_file(profile_path), profile_path


def parse_rule_id(ttl_path: Path) -> str | None:
    match = RULE_ID_RE.search(ttl_path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def match_any(path: Path, patterns: list[str], base: Path) -> bool:
    rel = path.relative_to(base).as_posix()
    name = path.name
    for pattern in patterns:
        if Path(rel).match(pattern) or Path(name).match(pattern):
            return True
    return False


def select_rule_files(rules_dir: Path, profile: dict) -> list[Path]:
    ttl_files = sorted(rules_dir.glob("*.ttl"))
    if not profile:
        return ttl_files

    selected: list[Path] = []
    rule_ids = set(profile.get("rule_ids") or [])
    rule_files = list(profile.get("rule_files") or [])
    include_globs = list(profile.get("include_globs") or [])

    for ttl in ttl_files:
        if rule_ids:
            parsed_id = parse_rule_id(ttl)
            if parsed_id and parsed_id in rule_ids:
                selected.append(ttl)
                continue
        if rule_files and match_any(ttl, rule_files, rules_dir):
            selected.append(ttl)
            continue
        if include_globs and match_any(ttl, include_globs, rules_dir):
            selected.append(ttl)
            continue

    deduped: dict[str, Path] = {}
    for ttl in selected:
        deduped[ttl.name] = ttl
    return sorted(deduped.values())


def collect_doc_paths(source_root: Path, selected_ttls: list[Path], profile: dict) -> list[Path]:
    docs_dir = source_root / "docs"
    selected: dict[str, Path] = {}

    for ttl in selected_ttls:
        text = ttl.read_text(encoding="utf-8")
        for rel in DOC_REF_RE.findall(text):
            doc_path = source_root / rel.removeprefix(".refactor/")
            if doc_path.is_file():
                selected[doc_path.relative_to(docs_dir).as_posix()] = doc_path

    doc_files = list(profile.get("doc_files") or [])
    if docs_dir.is_dir() and doc_files:
        for doc in docs_dir.rglob("*.md"):
            if match_any(doc, doc_files, docs_dir):
                selected[doc.relative_to(docs_dir).as_posix()] = doc

    return sorted(selected.values())


def manifest_path(repo_root: Path) -> Path:
    return repo_root / ".refactor" / "temp" / "sync_subset_manifest.json"


def load_previous_manifest(repo_root: Path) -> dict:
    path = manifest_path(repo_root)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_manifest(repo_root: Path, payload: dict, dry_run: bool) -> None:
    if dry_run:
        return
    path = manifest_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def remove_previous(repo_root: Path, dry_run: bool) -> list[str]:
    previous = load_previous_manifest(repo_root)
    removed: list[str] = []
    for rel in previous.get("synced_files", []):
        path = repo_root / rel
        if path.exists():
            removed.append(rel)
            if not dry_run:
                path.unlink()
    return removed


def copy_files(files: list[Path], source_base: Path, dest_base: Path, dry_run: bool) -> list[str]:
    copied: list[str] = []
    for src in files:
        rel = src.relative_to(source_base)
        dst = dest_base / rel
        copied.append(dst.as_posix())
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return copied


def rebuild_db(repo_root: Path) -> tuple[int, str]:
    script = repo_root / ".refactor" / "scripts" / "rebuild_db.py"
    result = subprocess.run(
        ["python3", str(script), "--repo-root", str(repo_root)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def main() -> int:
    args = parse_args()
    repo_root = find_repo_root(Path(args.repo_root))
    profile, profile_path = load_profile(args, repo_root)
    source_root = resolve_source_root(args, profile, profile_path)

    rules_dir = source_root / "rules"
    docs_dir = source_root / "docs"
    if not rules_dir.is_dir():
        raise SystemExit("source root must contain a rules/ directory")

    selected_ttls = select_rule_files(rules_dir, profile)
    selected_docs = collect_doc_paths(source_root, selected_ttls, profile)

    removed: list[str] = []
    if args.clean or profile.get("clean") is True:
        removed = remove_previous(repo_root, args.dry_run)

    copied_rules = copy_files(
        selected_ttls,
        rules_dir,
        repo_root / ".refactor" / "rules",
        args.dry_run,
    )
    copied_docs = copy_files(
        selected_docs,
        docs_dir,
        repo_root / ".refactor" / "docs",
        args.dry_run,
    )

    rebuild_requested = args.rebuild_db or profile.get("rebuild_db") is True
    rebuild_result: dict | None = None
    if rebuild_requested and not args.dry_run:
        code, output = rebuild_db(repo_root)
        rebuild_result = {"returncode": code, "output": output}

    synced_files = copied_rules + copied_docs
    write_manifest(
        repo_root,
        {
            "profile": args.profile or profile.get("name"),
            "profile_file": str(profile_path) if profile_path else None,
            "source_root": str(source_root),
            "synced_files": synced_files,
        },
        args.dry_run,
    )

    result = {
        "success": rebuild_result is None or rebuild_result["returncode"] == 0,
        "data": {
            "profile": args.profile or profile.get("name"),
            "profile_file": str(profile_path) if profile_path else None,
            "source_root": str(source_root),
            "rule_count": len(copied_rules),
            "doc_count": len(copied_docs),
            "rules": copied_rules,
            "docs": copied_docs,
            "removed": removed,
            "dry_run": args.dry_run,
            "rebuild_db": rebuild_requested,
            "rebuild_result": rebuild_result,
        },
        "error": None,
    }

    append_json_log(repo_root, "sync_subset.log", result["data"])
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
