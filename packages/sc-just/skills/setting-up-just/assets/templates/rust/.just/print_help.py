#!/usr/bin/env python3
# sc-just-template-version: 0.1.0
from __future__ import annotations

from pathlib import Path
import tomllib

def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config() -> dict:
    path = repo_root() / ".just" / "config.toml"
    if not path.exists():
        raise FileNotFoundError(f"missing config file: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def render_help(config: dict) -> str:
    sections = config.get("help", {}).get("sections", [])
    usage = config.get("help", {}).get("usage", "just <recipe>")
    recipes = [
        recipe
        for section in sections
        for recipe in section.get("recipes", [])
    ]
    width = max((len(recipe.get("name", "")) for recipe in recipes), default=4)
    configured_name = config.get("repo", {}).get("name", "").strip()
    display_name = configured_name or repo_root().name
    lines = [
        f"{display_name} task runner",
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
        print(render_help(load_config()), end="")
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
