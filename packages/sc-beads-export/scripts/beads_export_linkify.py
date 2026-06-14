from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from beads_export_common import iter_markdown_files, relative_href


BEAD_ID_CORE = r"p3-[A-Za-z0-9]{3}(?:\.[A-Za-z0-9]+)*"
BEAD_ID_RE = re.compile(rf"{BEAD_ID_CORE}(?![A-Za-z0-9-])")
BACKTICKED_BEAD_ID_RE = re.compile(rf"`({BEAD_ID_CORE})(?![A-Za-z0-9-])([^`]*)`")
PLAIN_BEAD_ID_RE = re.compile(rf"(?<![`\\w/.-])({BEAD_ID_CORE})(?![A-Za-z0-9-]|[`\\w/.-])")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


@dataclass(frozen=True)
class MissingReference:
    file: str
    line: int
    bead_id: str


@dataclass(frozen=True)
class BrokenLink:
    file: str
    line: int
    target: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Link bead-id references across exported markdown files using relative links."
    )
    parser.add_argument("root", help="Root folder containing exported markdown files.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report planned changes without writing files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary.",
    )
    return parser.parse_args(argv)

def build_target_map(files: Iterable[Path]) -> dict[str, Path]:
    target_map: dict[str, Path] = {}
    for path in files:
        stem = path.stem
        if BEAD_ID_RE.fullmatch(stem) and stem not in target_map:
            target_map[stem] = path
    return target_map


def is_within_ranges(index: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in ranges)


def collect_link_ranges(line: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in LINK_RE.finditer(line)]


def should_skip_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("- `id`: ")


def link_label(bead_id: str) -> str:
    return f"[`{bead_id}`]"

def transform_line(
    line: str,
    *,
    current_file: Path,
    target_map: dict[str, Path],
    missing: set[MissingReference],
    line_number: int,
) -> tuple[str, int]:
    if should_skip_line(line):
        return line, 0

    link_ranges = collect_link_ranges(line)
    replacements: list[tuple[int, int, str]] = []

    for match in BACKTICKED_BEAD_ID_RE.finditer(line):
        if is_within_ranges(match.start(), link_ranges):
            continue
        bead_id = match.group(1)
        suffix = match.group(2)
        target = target_map.get(bead_id)
        if target is None:
            missing.add(MissingReference(str(current_file), line_number, bead_id))
            continue
        href = relative_href(current_file, target)
        replacement = f"{link_label(bead_id)}({href}){suffix}"
        replacements.append((match.start(), match.end(), replacement))

    occupied = [(start, end) for start, end, _ in replacements]

    for match in PLAIN_BEAD_ID_RE.finditer(line):
        if is_within_ranges(match.start(), link_ranges) or is_within_ranges(match.start(), occupied):
            continue
        bead_id = match.group(1)
        target = target_map.get(bead_id)
        if target is None:
            missing.add(MissingReference(str(current_file), line_number, bead_id))
            continue
        href = relative_href(current_file, target)
        replacement = f"{link_label(bead_id)}({href})"
        replacements.append((match.start(1), match.end(1), replacement))

    if not replacements:
        return line, 0

    pieces: list[str] = []
    cursor = 0
    for start, end, replacement in sorted(replacements, key=lambda item: item[0]):
        if start < cursor:
            continue
        pieces.append(line[cursor:start])
        pieces.append(replacement)
        cursor = end
    pieces.append(line[cursor:])
    transformed = "".join(pieces)
    return transformed, len(replacements)


def transform_markdown(
    path: Path,
    *,
    target_map: dict[str, Path],
    missing: set[MissingReference],
) -> tuple[str, int]:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    in_fence = False
    change_count = 0
    transformed_lines: list[str] = []

    for line_number, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            transformed_lines.append(line)
            continue
        if in_fence:
            transformed_lines.append(line)
            continue
        transformed, changed = transform_line(
            line,
            current_file=path,
            target_map=target_map,
            missing=missing,
            line_number=line_number,
        )
        transformed_lines.append(transformed)
        change_count += changed

    return "".join(transformed_lines), change_count


def validate_relative_links(files: Iterable[Path]) -> list[BrokenLink]:
    broken: list[BrokenLink] = []
    for path in files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in LINK_RE.finditer(line):
                target = match.group(1).strip()
                if not target or target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                target_path = (path.parent / target).resolve()
                if not target_path.exists():
                    broken.append(BrokenLink(str(path), line_number, target))
    return broken


def summarize(
    *,
    root: Path,
    files: list[Path],
    changed_files: list[str],
    changed_references: int,
    missing: set[MissingReference],
    broken: list[BrokenLink],
    dry_run: bool,
) -> dict[str, object]:
    return {
        "root": str(root),
        "mode": "dry-run" if dry_run else "write",
        "files_scanned": len(files),
        "files_changed": len(changed_files),
        "changed_files": changed_files,
        "references_linked": changed_references,
        "missing_beads": [
            {"file": item.file, "line": item.line, "bead_id": item.bead_id}
            for item in sorted(missing, key=lambda item: (item.file, item.line, item.bead_id))
        ],
        "broken_relative_links": [
            {"file": item.file, "line": item.line, "target": item.target}
            for item in broken
        ],
    }


def emit_text(summary: dict[str, object]) -> None:
    print(f"Root: {summary['root']}")
    print(f"Mode: {summary['mode']}")
    print(f"Files scanned: {summary['files_scanned']}")
    print(f"Files changed: {summary['files_changed']}")
    print(f"References linked: {summary['references_linked']}")

    changed_files = summary["changed_files"]
    if changed_files:
        print("Changed files:")
        for path in changed_files:
            print(f"- {path}")

    missing_beads = summary["missing_beads"]
    if missing_beads:
        print("Missing bead targets:")
        for item in missing_beads:
            print(f"- {item['file']}:{item['line']} -> {item['bead_id']}")

    broken_links = summary["broken_relative_links"]
    if broken_links:
        print("Broken relative links:")
        for item in broken_links:
            print(f"- {item['file']}:{item['line']} -> {item['target']}")


def linkify_export(root: Path | str, *, dry_run: bool) -> dict[str, object]:
    root_path = Path(root).resolve()
    files = iter_markdown_files(root_path)
    target_map = build_target_map(files)

    missing: set[MissingReference] = set()
    changed_files: list[str] = []
    changed_references = 0

    for path in files:
        transformed, change_count = transform_markdown(path, target_map=target_map, missing=missing)
        if change_count:
            changed_files.append(str(path))
            changed_references += change_count
            if not dry_run:
                path.write_text(transformed, encoding="utf-8")

    broken = validate_relative_links(files)
    return summarize(
        root=root_path,
        files=files,
        changed_files=changed_files,
        changed_references=changed_references,
        missing=missing,
        broken=broken,
        dry_run=dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = linkify_export(args.root, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        emit_text(summary)

    return 0 if not summary["missing_beads"] and not summary["broken_relative_links"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
