from __future__ import annotations

import argparse
import json
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import beads_export_html
import beads_export_linkify
from beads_export_common import export_root_for_name, relative_href, reset_output_dir, slugify


PRIORITY_MAP = {1: "P1", 2: "P2", 3: "P3", 4: "P4"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export one or more beads subtrees to hierarchical markdown under export/."
    )
    parser.add_argument("export_name", help="Folder name to create under export/.")
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        required=True,
        help="Parent bead ID to export. Repeat for multiple roots.",
    )
    parser.add_argument(
        "--board-json",
        help="Optional path to a bd list JSON export. If omitted, read live board data with bd list --json --all --limit 0.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary.",
    )
    parser.add_argument(
        "--linkify",
        action="store_true",
        help="Run the markdown linkifier after export and validate the result.",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate a static HTML site from the markdown export after link validation.",
    )
    parser.add_argument(
        "--package",
        action="store_true",
        help="Create a zip archive of the markdown export under export/packages/.",
    )
    return parser.parse_args(argv)


def load_issues(board_json: str | None) -> list[dict[str, Any]]:
    if board_json:
        return json.loads(Path(board_json).read_text(encoding="utf-8"))

    result = subprocess.run(
        ["bd", "list", "--json", "--all", "--limit", "0"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def build_children_map(issues: list[dict[str, Any]]) -> dict[str, list[str]]:
    children: dict[str, list[str]] = defaultdict(list)
    for issue in issues:
        parent = issue.get("parent")
        if parent:
            children[parent].append(issue["id"])
    for issue_id in children:
        children[issue_id].sort()
    return dict(children)


def collect_descendants(root_id: str, children: dict[str, list[str]]) -> set[str]:
    result: set[str] = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        if current in result:
            continue
        result.add(current)
        stack.extend(reversed(children.get(current, [])))
    return result


def collect_ancestors(root_ids: list[str], by_id: dict[str, dict[str, Any]]) -> set[str]:
    ancestors: set[str] = set()
    for root_id in root_ids:
        current = by_id.get(root_id, {}).get("parent")
        while current:
            if current in ancestors:
                break
            ancestors.add(current)
            current = by_id.get(current, {}).get("parent")
    return ancestors


def bead_dir_name(issue: dict[str, Any]) -> str:
    return f"{issue['id']}--{slugify(issue.get('title', issue['id']))}"


def selected_roots(included: set[str], by_id: dict[str, dict[str, Any]]) -> list[str]:
    roots = [iid for iid in included if by_id[iid].get("parent") not in included]
    return sorted(roots)


def file_paths_for(
    issue_id: str,
    *,
    root_dir: Path,
    included: set[str],
    by_id: dict[str, dict[str, Any]],
    cache: dict[str, Path],
) -> Path:
    if issue_id in cache:
        return cache[issue_id]

    issue = by_id[issue_id]
    parent = issue.get("parent")
    if parent and parent in included:
        parent_dir = file_paths_for(parent, root_dir=root_dir, included=included, by_id=by_id, cache=cache).parent
        issue_dir = parent_dir / bead_dir_name(issue)
    else:
        issue_dir = root_dir / bead_dir_name(issue)
    issue_dir.mkdir(parents=True, exist_ok=True)
    path = issue_dir / f"{issue_id}.md"
    cache[issue_id] = path
    return path


def format_dependencies(
    issue: dict[str, Any],
    *,
    included: set[str],
) -> list[str]:
    deps = issue.get("dependencies", []) or []
    if not deps:
        return ["- none"]
    lines: list[str] = []
    for dep in deps:
        dep_id = dep.get("depends_on_id", "")
        dep_type = dep.get("type", "")
        if dep_id in included:
            lines.append(f"- `{dep_type}` -> `{dep_id}`")
        else:
            lines.append(f"- `{dep_type}` -> `{dep_id}` (outside export scope)")
    return lines


def write_issue_markdown(
    issue: dict[str, Any],
    *,
    path: Path,
    by_id: dict[str, dict[str, Any]],
    included: set[str],
    children: dict[str, list[str]],
    requested_roots: set[str],
    ancestor_only: set[str],
) -> None:
    lines: list[str] = []
    lines.append(f"# {issue.get('title', issue['id'])}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- `id`: `{issue['id']}`")
    lines.append(f"- `issue_type`: `{issue.get('issue_type', '')}`")
    lines.append(f"- `status`: `{issue.get('status', '')}`")
    lines.append(f"- `priority`: `{PRIORITY_MAP.get(issue.get('priority'), issue.get('priority', ''))}`")
    parent = issue.get("parent")
    if parent:
        parent_title = by_id.get(parent, {}).get("title", "")
        parent_label = f"{parent} — {parent_title}" if parent_title else parent
        if parent in included:
            lines.append(f"- `parent`: `{parent_label}`")
        else:
            lines.append(f"- `parent`: `{parent_label}` (outside export scope)")
    else:
        lines.append("- `parent`: none")
    labels = issue.get("labels", []) or []
    lines.append(
        "- `labels`: " + (", ".join(f"`{label}`" for label in labels) if labels else "none")
    )
    lines.append(f"- `created_at`: `{issue.get('created_at', '')}`")
    lines.append(f"- `updated_at`: `{issue.get('updated_at', '')}`")
    if issue.get("closed_at"):
        lines.append(f"- `closed_at`: `{issue.get('closed_at')}`")
    lines.append("")

    lines.append("## Description")
    lines.append("")
    description = issue.get("description", "").rstrip()
    lines.append(description if description else "_No description._")
    lines.append("")

    lines.append("## Dependencies")
    lines.append("")
    lines.extend(format_dependencies(issue, included=included))
    lines.append("")

    lines.append("## Child Beads")
    lines.append("")
    child_ids = [child_id for child_id in children.get(issue["id"], []) if child_id in included]
    if child_ids:
        for child_id in child_ids:
            lines.append(f"- `{child_id}` — {by_id[child_id].get('title', '')}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Export Notes")
    lines.append("")
    lines.append("- Source: live beads board export")
    lines.append("- This markdown file was generated for offline review/export")
    if issue["id"] in requested_roots:
        lines.append("- This bead was a requested export root")
    if issue["id"] in ancestor_only:
        lines.append("- This bead was included as a scoped ancestor so internal parent links resolve cleanly")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def add_tree_lines(
    issue_id: str,
    *,
    index_lines: list[str],
    depth: int,
    children: dict[str, list[str]],
    included: set[str],
    path_map: dict[str, Path],
    index_path: Path,
    by_id: dict[str, dict[str, Any]],
) -> None:
    indent = "  " * depth
    href = relative_href(index_path, path_map[issue_id])
    index_lines.append(f"{indent}- [`{issue_id}`]({href}) — {by_id[issue_id].get('title', '')}")
    for child_id in children.get(issue_id, []):
        if child_id in included:
            add_tree_lines(
                child_id,
                index_lines=index_lines,
                depth=depth + 1,
                children=children,
                included=included,
                path_map=path_map,
                index_path=index_path,
                by_id=by_id,
            )


def export_beads(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    issues = load_issues(args.board_json)
    by_id = {issue["id"]: issue for issue in issues}

    missing_roots = [root for root in args.roots if root not in by_id]
    if missing_roots:
        raise ValueError(f"Unknown root bead ids: {', '.join(missing_roots)}")

    children = build_children_map(issues)
    requested_roots = set(args.roots)
    descendants = set().union(*(collect_descendants(root, children) for root in args.roots))
    ancestors = collect_ancestors(args.roots, by_id)
    included = descendants | ancestors
    ancestor_only = ancestors - descendants

    export_root = export_root_for_name(args.export_name)
    reset_output_dir(export_root)
    tree_root = export_root / "tree"
    tree_root.mkdir(parents=True, exist_ok=True)

    path_cache: dict[str, Path] = {}
    for issue_id in sorted(included):
        file_paths_for(issue_id, root_dir=tree_root, included=included, by_id=by_id, cache=path_cache)

    for issue_id in sorted(included):
        write_issue_markdown(
            by_id[issue_id],
            path=path_cache[issue_id],
            by_id=by_id,
            included=included,
            children=children,
            requested_roots=requested_roots,
            ancestor_only=ancestor_only,
        )

    index_path = export_root / "INDEX.md"
    index_lines: list[str] = []
    index_lines.append("# Beads Export")
    index_lines.append("")
    index_lines.append("This folder contains a hierarchical markdown export of selected beads roots and their descendants.")
    index_lines.append("")
    index_lines.append("## Requested Roots")
    index_lines.append("")
    for root_id in args.roots:
        href = relative_href(index_path, path_cache[root_id])
        index_lines.append(f"- [`{root_id}`]({href}) — {by_id[root_id].get('title', '')}")
    index_lines.append("")

    if ancestor_only:
        index_lines.append("## Scoped Ancestors")
        index_lines.append("")
        for issue_id in sorted(ancestor_only):
            href = relative_href(index_path, path_cache[issue_id])
            index_lines.append(f"- [`{issue_id}`]({href}) — {by_id[issue_id].get('title', '')}")
        index_lines.append("")

    index_lines.append("## Tree")
    index_lines.append("")
    for root_id in selected_roots(included, by_id):
        add_tree_lines(
            root_id,
            index_lines=index_lines,
            depth=0,
            children=children,
            included=included,
            path_map=path_cache,
            index_path=index_path,
            by_id=by_id,
        )
        index_lines.append("")

    index_lines.append("## Files")
    index_lines.append("")
    for issue_id in sorted(included):
        href = relative_href(index_path, path_cache[issue_id])
        index_lines.append(f"- [{href}]({href})")
    index_lines.append("")
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    summary: dict[str, Any] = {
        "export_root": str(export_root.resolve()),
        "requested_roots": args.roots,
        "scoped_ancestors": sorted(ancestor_only),
        "files_written": len(included) + 1,
        "tree_root": str(tree_root.resolve()),
    }

    if args.linkify or args.html:
        write_summary = beads_export_linkify.linkify_export(export_root, dry_run=False)
        dry_summary = beads_export_linkify.linkify_export(export_root, dry_run=True)
        summary["linkify_write"] = write_summary
        summary["linkify_validate"] = dry_summary
        if dry_summary["missing_beads"] or dry_summary["broken_relative_links"]:
            raise RuntimeError("Linkified export still has missing bead targets or broken relative links.")

    if args.html:
        html_summary = beads_export_html.build_site(export_root)
        summary["html"] = html_summary

    if args.package:
        packages_dir = Path("export") / "packages"
        packages_dir.mkdir(parents=True, exist_ok=True)
        package_path = packages_dir / f"{args.export_name}-export.zip"
        if package_path.exists():
            package_path.unlink()
        package_roots = [export_root]
        if args.html:
            html_output_root = Path(summary["html"]["output_root"])
            package_roots.append(html_output_root)
        with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for package_root in package_roots:
                for path in sorted(package_root.rglob("*")):
                    if path.is_file():
                        archive.write(path, arcname=str(path.relative_to(package_root.parent)))
        summary["package"] = str(package_path.resolve())

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Export root: {summary['export_root']}")
        print(f"Requested roots: {', '.join(args.roots)}")
        if ancestor_only:
            print(f"Scoped ancestors: {', '.join(sorted(ancestor_only))}")
        print(f"Files written: {summary['files_written']}")
    return summary


def main(argv: list[str] | None = None) -> int:
    export_beads(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
