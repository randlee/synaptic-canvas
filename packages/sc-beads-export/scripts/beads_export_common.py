from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


def slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "untitled"


def relative_href(from_path: Path, to_path: Path) -> str:
    return os.path.relpath(to_path, from_path.parent)


def iter_markdown_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def export_root_for_name(export_name: str) -> Path:
    return Path("export") / export_name


def html_output_root_for_export(export_root: Path) -> Path:
    return export_root.parent / f"{export_root.name}-html"


def reset_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
