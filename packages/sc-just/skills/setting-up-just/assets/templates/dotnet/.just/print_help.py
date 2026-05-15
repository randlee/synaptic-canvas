#!/usr/bin/env python3
# sc-just-template-version: 0.1.0
from __future__ import annotations

import tomllib
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config() -> dict:
    path = repo_root() / ".just" / "config.toml"
    if not path.exists():
        raise FileNotFoundError(f"missing config file: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def repo_name(config: dict) -> str:
    configured_name = config.get("repo", {}).get("name", "").strip()
    return configured_name or repo_root().name


def main() -> int:
    try:
        config = load_config()
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(str(exc))
        return 2

    help_config = config.get("help", {})
    recipe_lines = []
    for section in help_config.get("sections", []):
        if section.get("title") != "General":
            continue
        recipe_lines.append(f"{section.get('title', 'Recipes')}:")
        for recipe in section.get("recipes", []):
            recipe_lines.append(f"  {recipe.get('name', ''):<12} {recipe.get('description', '')}")
        recipe_lines.append("")

    lines = [
        f"{repo_name(config)} .NET task runner",
        "",
        "Usage:",
        f"  {help_config.get('usage', 'just <recipe>')}",
        "  just build",
        "  just test",
        "",
        *recipe_lines,
    ]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
