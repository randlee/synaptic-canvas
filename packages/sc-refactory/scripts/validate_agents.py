#!/usr/bin/env python3
"""Validate agent and skill versions against agents/registry.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "agents" / "registry.yaml"
MANIFEST = ROOT / "manifest.yaml"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    _, rest = text.split("---\n", 1)
    header, _, _ = rest.partition("\n---\n")
    return yaml.safe_load(header) or {}


def main() -> int:
    registry = load_yaml(REGISTRY)
    manifest = load_yaml(MANIFEST)
    package_version = manifest.get("version")
    failures: list[str] = []

    for name, info in registry.get("agents", {}).items():
        rel_path = info["path"].removeprefix(".claude/")
        agent_path = ROOT / rel_path
        if not agent_path.exists():
            failures.append(f"missing agent file: {info['path']}")
            continue
        fm = frontmatter(agent_path)
        if fm.get("version") != info.get("version"):
            failures.append(
                f"agent version mismatch for {name}: file={fm.get('version')} registry={info.get('version')}"
            )
        if package_version and fm.get("version") != package_version:
            failures.append(
                f"agent package-version mismatch for {name}: file={fm.get('version')} package={package_version}"
            )

    for name, info in registry.get("skills", {}).items():
        path = info.get("path")
        if not path:
            failures.append(f"missing skill path in registry: {name}")
            continue
        rel_path = path.removeprefix(".claude/")
        skill_path = ROOT / rel_path
        if not skill_path.exists():
            failures.append(f"missing skill file: {path}")
            continue
        fm = frontmatter(skill_path)
        if fm.get("version") != info.get("version"):
            failures.append(
                f"skill version mismatch for {name}: file={fm.get('version')} registry={info.get('version')}"
            )
        if package_version and fm.get("version") != package_version:
            failures.append(
                f"skill package-version mismatch for {name}: file={fm.get('version')} package={package_version}"
            )

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    print("All agent and skill versions validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
