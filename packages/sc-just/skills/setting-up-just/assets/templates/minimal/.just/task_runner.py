#!/usr/bin/env python3
# sc-just-template-version: 0.1.0
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tomllib

PYTHON_CMD_TOKEN = "{{python_cmd}}"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return repo_root() / ".just" / "config.toml"


def load_config() -> dict:
    path = config_path()
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
        f"{repo_name(config)} task runner",
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


def _normalize_part(part: str) -> str:
    if part == PYTHON_CMD_TOKEN:
        return sys.executable
    return part


def normalize_steps(steps: list[str] | list[list[str]]) -> list[list[str]]:
    if steps and isinstance(steps[0], str):
        steps = [steps]
    return [[_normalize_part(part) for part in step] for step in steps]


def run_steps(label: str, steps: list[list[str]]) -> int:
    if not steps:
        print(f"{label} is not configured. Edit .just/config.toml and add command steps.")
        return 2

    root = repo_root()
    for step in normalize_steps(steps):
        print("+", " ".join(step))
        completed = subprocess.run(step, cwd=root)
        if completed.returncode != 0:
            return completed.returncode
    return 0
