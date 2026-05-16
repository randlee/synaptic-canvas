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


def render_help(config: dict) -> str:
    sections = config.get("help", {}).get("sections", [])
    usage = config.get("help", {}).get("usage", "just <recipe>")
    recipes = [
        recipe
        for section in sections
        for recipe in section.get("recipes", [])
    ]
    width = max((len(recipe.get("name", "")) for recipe in recipes), default=4)
    lines = [
        f"{repo_name(config)} .NET task runner",
        "",
        "Usage:",
        f"  {usage}",
        "",
    ]
    for section in sections:
        lines.append(f"{section.get('title', 'Recipes')}:")
        for recipe in section.get("recipes", []):
            lines.append(
                f"  {recipe.get('name', '').ljust(width)}  {recipe.get('description', '')}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    try:
        config = load_config()
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(str(exc))
        return 2

    print(render_help(config), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
