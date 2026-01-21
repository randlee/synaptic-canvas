#!/usr/bin/env python3
"""
Build a temporary plugin bundle from .claude-plugin/plugin.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path


def _load_plugin_json(plugin_root: Path) -> dict:
    plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
    if not plugin_json.is_file():
        raise FileNotFoundError(f"plugin.json not found: {plugin_json}")
    return json.loads(plugin_json.read_text(encoding="utf-8"))


def _copy_entry(plugin_root: Path, dest_root: Path, rel_path: str) -> None:
    src = (plugin_root / rel_path).resolve()
    dst = (dest_root / rel_path).resolve()
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def build_bundle(plugin_root: Path, dest_root: Path) -> None:
    manifest = _load_plugin_json(plugin_root)
    # Always copy plugin.json
    _copy_entry(plugin_root, dest_root, ".claude-plugin/plugin.json")
    for section in ("commands", "agents", "skills", "hooks", "mcp"):
        for rel_path in manifest.get(section, []) or []:
            _copy_entry(plugin_root, dest_root, rel_path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build plugin bundle from plugin.json")
    ap.add_argument("--plugin-root", required=True, help="Path to plugin root (contains .claude-plugin/)")
    ap.add_argument("--dest", default="", help="Destination directory (defaults to temp dir)")
    args = ap.parse_args()

    plugin_root = Path(args.plugin_root).resolve()
    if not plugin_root.is_dir():
        raise SystemExit(f"Plugin root not found: {plugin_root}")

    if args.dest:
        dest_root = Path(args.dest).resolve()
        dest_root.mkdir(parents=True, exist_ok=True)
    else:
        dest_root = Path(tempfile.mkdtemp(prefix="sc-plugin-"))

    build_bundle(plugin_root, dest_root)
    print(dest_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
