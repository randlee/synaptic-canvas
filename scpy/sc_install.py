#!/usr/bin/env python3
"""
Python rewrite of tools/sc-install.sh

Commands:
  list
  info <package>
  install <package> --dest <path/to/.claude> [--force] [--no-expand]
  uninstall <package> --dest <path/to/.claude>

Notes:
- Uses YAML if PyYAML is installed; otherwise falls back to a simple line parser
  compatible with the existing manifest patterns.
- Token expansion: replaces {{REPO_NAME}} when variables.REPO_NAME.auto == git-repo-basename
- Scripts are made executable on install (artifacts under scripts/*)
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Optional YAML support
try:  # pragma: no cover - exercised in environment when available
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def info(msg: str) -> None:
    print(f"{GREEN}✓{NC} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}⚠{NC} {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"{RED}✗{NC} {msg}", file=sys.stderr)


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DIR = REPO_ROOT / "packages"


@dataclass
class Manifest:
    name: str
    path: Path
    description: str
    artifacts: Dict[str, List[str]]
    variables: Dict[str, Dict[str, str]]


def _read_file(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _parse_manifest(pkg_dir: Path) -> Manifest:
    manifest_path = pkg_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise SystemExit(f"No manifest.yaml in {pkg_dir.name}")

    if yaml is not None:
        data = yaml.safe_load(_read_file(manifest_path)) or {}
        artifacts = (data.get("artifacts") or {})
        variables = (data.get("variables") or {})
        desc = (data.get("description") or "").strip()
        return Manifest(
            name=data.get("name") or pkg_dir.name,
            path=pkg_dir,
            description=desc,
            artifacts={k: list(v or []) for k, v in artifacts.items()},
            variables=variables,
        )

    # Fallback: minimal line parser for artifacts sections
    artifacts: Dict[str, List[str]] = {"commands": [], "skills": [], "agents": [], "scripts": []}
    current: Optional[str] = None
    for line in _read_file(manifest_path).splitlines():
        line = line.rstrip()
        if line.strip().endswith(":"):
            key = line.strip()[:-1]
            if key in artifacts:
                current = key
            else:
                current = None
            continue
        if current and line.strip().startswith("- "):
            item = line.split("- ", 1)[1].strip()
            artifacts[current].append(item)
    # Best-effort description: not critical
    return Manifest(name=pkg_dir.name, path=pkg_dir, description="", artifacts=artifacts, variables={})


def _available_packages() -> Iterable[Path]:
    if not PACKAGES_DIR.exists():
        return []
    return sorted(p for p in PACKAGES_DIR.iterdir() if p.is_dir())


def cmd_list() -> int:
    print("Available packages:\n")
    for pkg_dir in _available_packages():
        m = _parse_manifest(pkg_dir)
        desc_first = m.description.splitlines()[0] if m.description else "(no manifest)"
        print(f"  {pkg_dir.name:<20} {desc_first[:60]}")
    return 0


def cmd_info(pkg: str) -> int:
    pkg_dir = PACKAGES_DIR / pkg
    if not pkg_dir.is_dir():
        error(f"Package not found: {pkg}")
        return 1
    manifest_path = pkg_dir / "manifest.yaml"
    if not manifest_path.exists():
        error(f"No manifest.yaml in {pkg}")
        return 1
    print(f"Package: {pkg}")
    print(f"Path: {pkg_dir}")
    print()
    sys.stdout.write(_read_file(manifest_path))
    if not _read_file(manifest_path).endswith("\n"):
        print()
    return 0


def _git_repo_basename(dest_dir: Path) -> str:
    try:
        # Determine toplevel from parent of dest (.claude lives under repo)
        toplevel = (
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=dest_dir.parent,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            ).stdout.strip()
            or ""
        )
        return Path(toplevel).name if toplevel else ""
    except Exception:
        return ""


def _iter_artifacts(m: Manifest) -> Iterable[str]:
    order = ["commands", "skills", "agents", "scripts"]
    for key in order:
        for item in m.artifacts.get(key, []):
            yield item


def _ensure_executable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def cmd_install(pkg: str, dest: str, *, force: bool, expand: bool) -> int:
    pkg_dir = PACKAGES_DIR / pkg
    if not pkg_dir.is_dir():
        error(f"Package not found: {pkg}")
        return 1
    if not dest:
        error("--dest is required")
        return 1
    if ".claude" not in dest:
        error("--dest must point to a .claude directory")
        return 1

    dest_path = Path(dest).expanduser().resolve()
    dest_path.mkdir(parents=True, exist_ok=True)

    manifest = _parse_manifest(pkg_dir)

    repo_name = ""
    if expand and manifest.variables.get("REPO_NAME", {}).get("auto") == "git-repo-basename":
        repo_name = _git_repo_basename(dest_path)

    info(f"Installing {pkg} to {dest_path}")
    if repo_name:
        info(f"REPO_NAME={repo_name}")

    def install_one(rel_file: str) -> None:
        src = (pkg_dir / rel_file).resolve()
        dst = (dest_path / rel_file).resolve()
        if not src.exists():
            warn(f"Source not found: {src}")
            return
        if dst.exists() and not force:
            warn(f"Skip (exists): {dst}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        # executable for scripts/*
        if rel_file.startswith("scripts/"):
            _ensure_executable(dst)
        # token expansion
        if expand and repo_name:
            try:
                text = dst.read_text(encoding="utf-8", errors="ignore")
                text = text.replace("{{REPO_NAME}}", repo_name)
                dst.write_text(text, encoding="utf-8")
            except Exception:
                # Ignore binary/non-text failures
                pass
        info(f"Installed: {rel_file}")

    for rel in _iter_artifacts(manifest):
        install_one(rel)

    info(f"Done installing {pkg}")
    return 0


def cmd_uninstall(pkg: str, dest: str) -> int:
    pkg_dir = PACKAGES_DIR / pkg
    if not pkg_dir.is_dir():
        error(f"Package not found: {pkg}")
        return 1
    if not dest:
        error("--dest is required")
        return 1
    dest_path = Path(dest).expanduser().resolve()
    manifest = _parse_manifest(pkg_dir)
    info(f"Uninstalling {pkg} from {dest_path}")

    for rel in _iter_artifacts(manifest):
        dst = dest_path / rel
        if dst.exists():
            try:
                dst.unlink()
                info(f"Removed: {rel}")
            except Exception:
                warn(f"Could not remove: {rel}")
    info(f"Done uninstalling {pkg}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sc-install", add_help=True)
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list")

    p_info = sub.add_parser("info")
    p_info.add_argument("package")

    p_install = sub.add_parser("install")
    p_install.add_argument("package")
    p_install.add_argument("--dest", required=True)
    p_install.add_argument("--force", action="store_true")
    p_install.add_argument("--no-expand", action="store_true")

    p_uninstall = sub.add_parser("uninstall")
    p_uninstall.add_argument("package")
    p_uninstall.add_argument("--dest", required=True)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "info":
        return cmd_info(args.package)
    if args.cmd == "install":
        return cmd_install(args.package, args.dest, force=args.force, expand=not args.no_expand)
    if args.cmd == "uninstall":
        return cmd_uninstall(args.package, args.dest)
    # Default: if user passed legacy style without subcommand, show help
    build_parser().print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
