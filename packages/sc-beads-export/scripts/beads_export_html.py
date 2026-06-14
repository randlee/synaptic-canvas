from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

import markdown
from beads_export_common import (
    html_output_root_for_export,
    iter_markdown_files,
    relative_href,
    reset_output_dir,
)


LINK_RE = re.compile(r"(\[[^\]]+\])\(([^)]+)\)")
H2_RE = re.compile(r"^##\s+(.*)$")
H1_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)
TREE_ITEM_RE = re.compile(r"^(?P<indent>\s*)-\s+\[`(?P<bead_id>[^`]+)`\]\((?P<href>[^)]+)\)\s+—\s+(?P<label>.+)$")


@dataclass(frozen=True)
class NavItem:
    depth: int
    bead_id: str
    href: str
    label: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a static HTML site from a hierarchical beads markdown export."
    )
    parser.add_argument(
        "export_root",
        help="Path to the markdown export root, e.g. export/opencv-sdk.",
    )
    parser.add_argument(
        "--output",
        help="Optional output directory. Defaults to <export_root>-html.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary.",
    )
    return parser.parse_args(argv)

def rewrite_markdown_links(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        if target.endswith(".md"):
            return f"{label}({target[:-3]}.html)"
        return match.group(0)

    return LINK_RE.sub(replace, text)


def render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["extra", "fenced_code", "sane_lists", "tables", "toc"],
        output_format="html5",
    )


def page_title(markdown_text: str, fallback: str) -> str:
    match = H1_RE.search(markdown_text)
    if match:
        return match.group(1).strip()
    return fallback


def extract_index_section(markdown_text: str, section_name: str) -> str:
    lines = markdown_text.splitlines()
    in_section = False
    section: list[str] = []
    for line in lines:
        heading = H2_RE.match(line)
        if heading:
            if in_section:
                break
            in_section = heading.group(1).strip().lower() == section_name.lower()
            continue
        if in_section:
            section.append(line)
    extracted = "\n".join(section).strip()
    return extracted


def extract_index_tree(markdown_text: str) -> str:
    extracted = extract_index_section(markdown_text, "tree")
    return extracted or "_No tree available._"


def extract_site_title(markdown_text: str, fallback: str) -> str:
    scoped = extract_index_section(markdown_text, "scoped ancestors")
    if scoped:
        for line in scoped.splitlines():
            match = TREE_ITEM_RE.match(line)
            if match:
                return match.group("label").strip()
    return fallback


def parse_nav_items(markdown_text: str) -> list[NavItem]:
    items: list[NavItem] = []
    for line in extract_index_tree(markdown_text).splitlines():
        match = TREE_ITEM_RE.match(line)
        if not match:
            continue
        indent = match.group("indent")
        items.append(
            NavItem(
                depth=len(indent) // 2,
                bead_id=match.group("bead_id"),
                href=match.group("href"),
                label=match.group("label").strip(),
            )
        )
    return items


def render_nav_html(
    nav_items: list[NavItem],
    *,
    current_source: Path,
    source_root: Path,
) -> str:
    if not nav_items:
        return "<p>No tree available.</p>"

    current_output = output_path_for(current_source, source_root, Path("/__site__"))
    parts: list[str] = []
    current_depth = -1
    previous_depth = -1

    for index, item in enumerate(nav_items):
        next_depth = nav_items[index + 1].depth if index + 1 < len(nav_items) else -1
        while current_depth < item.depth:
            parts.append("<ul>")
            current_depth += 1
        while current_depth > item.depth:
            parts.append("</li></ul>")
            current_depth -= 1
        if previous_depth == item.depth:
            parts.append("</li>")

        target_source = source_root / item.href
        target_output = output_path_for(target_source, source_root, Path("/__site__"))
        href = relative_href(current_output, target_output)
        current_class = ' class="current"' if target_output == current_output else ""
        parts.append(
            f'<li><a{current_class} href="{html.escape(href)}" title="{html.escape(item.bead_id)}">{html.escape(item.label)}</a>'
        )
        previous_depth = item.depth

        if next_depth < item.depth:
            while current_depth > next_depth:
                parts.append("</li></ul>")
                current_depth -= 1
            previous_depth = next_depth

    while current_depth >= 0:
        parts.append("</li></ul>")
        current_depth -= 1

    return "".join(parts)


def build_template(*, title: str, site_title: str, nav_html: str, body_html: str, breadcrumbs_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{{{{ASSET_PREFIX}}}}assets/site.css">
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <a href="{{{{HOME_HREF}}}}" class="home-link">{html.escape(site_title)}</a>
      </div>
      <nav class="tree-nav">
        {nav_html}
      </nav>
    </aside>
    <main class="content">
      <div class="breadcrumbs">{breadcrumbs_html}</div>
      <article class="page">
        {body_html}
      </article>
    </main>
  </div>
</body>
</html>
"""


def breadcrumbs_for(source_path: Path, root: Path) -> str:
    if source_path.name == "INDEX.md":
        return '<a href="index.html">Home</a>'

    parts = list(source_path.relative_to(root).parts)
    crumbs = ['<a href="index.html">Home</a>']
    if parts and parts[0] == "tree":
        crumbs.append("tree")
        for part in parts[1:]:
            if part.endswith(".md"):
                crumbs.append(html.escape(part[:-3]))
            else:
                crumbs.append(html.escape(part))
    return " / ".join(crumbs)


def css_text() -> str:
    return """
:root {
  --bg: #f5f1e8;
  --paper: #fffdf8;
  --ink: #1d1a16;
  --muted: #6e6255;
  --line: #d7cfc2;
  --accent: #0f5c4d;
  --accent-soft: #e2efe9;
  --code-bg: #f3efe7;
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--ink); }
body {
  font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
  line-height: 1.6;
}

.layout {
  display: grid;
  grid-template-columns: minmax(280px, 340px) 1fr;
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  overflow: auto;
  border-right: 1px solid var(--line);
  background: linear-gradient(180deg, #f7f4ec 0%, #efe7d9 100%);
  padding: 1.25rem 1rem 2rem;
}

.sidebar-header {
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--line);
}

.home-link {
  color: var(--ink);
  text-decoration: none;
  font-size: 1.15rem;
  font-weight: 700;
}

.tree-nav ul {
  list-style: none;
  padding-left: 1rem;
  margin: 0.35rem 0;
  border-left: 1px solid var(--line);
}

.tree-nav > ul {
  padding-left: 0;
  border-left: none;
}

.tree-nav li {
  margin: 0.18rem 0;
  padding-left: 0.55rem;
}

.tree-nav a {
  color: var(--accent);
  text-decoration: none;
  display: inline-block;
  padding: 0.08rem 0;
}

.tree-nav a.current {
  font-weight: 700;
  color: var(--ink);
}

.tree-nav a:hover,
.content a:hover {
  text-decoration: underline;
}

.content {
  padding: 2rem clamp(1rem, 3vw, 2.5rem) 3rem;
}

.breadcrumbs {
  color: var(--muted);
  font-size: 0.95rem;
  margin-bottom: 1rem;
}

.breadcrumbs a {
  color: var(--muted);
  text-decoration: none;
}

.page {
  max-width: 980px;
  background: var(--paper);
  border: 1px solid var(--line);
  padding: clamp(1.2rem, 2vw, 2rem);
  box-shadow: 0 10px 30px rgba(49, 37, 22, 0.06);
}

h1, h2, h3, h4 {
  line-height: 1.2;
  margin-top: 1.4em;
}

h1 {
  margin-top: 0;
  font-size: clamp(1.9rem, 3vw, 2.6rem);
}

h2 {
  border-top: 1px solid var(--line);
  padding-top: 0.9rem;
}

a {
  color: var(--accent);
}

code {
  background: var(--code-bg);
  padding: 0.1rem 0.3rem;
  border-radius: 0.25rem;
  font-family: "SFMono-Regular", Menlo, Monaco, monospace;
  font-size: 0.92em;
}

pre {
  background: var(--code-bg);
  padding: 1rem;
  overflow: auto;
  border: 1px solid var(--line);
}

pre code {
  background: transparent;
  padding: 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

th, td {
  border: 1px solid var(--line);
  padding: 0.6rem 0.7rem;
  vertical-align: top;
}

th {
  background: var(--accent-soft);
  text-align: left;
}

blockquote {
  margin: 1rem 0;
  padding: 0.2rem 1rem;
  border-left: 4px solid var(--line);
  color: var(--muted);
}

@media (max-width: 960px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--line);
  }

  .page {
    max-width: none;
  }
}
""".strip()


def output_path_for(source_path: Path, source_root: Path, output_root: Path) -> Path:
    relative = source_path.relative_to(source_root)
    if relative == Path("INDEX.md"):
        return output_root / "index.html"
    return output_root / relative.with_suffix(".html")


def asset_prefix_for(output_path: Path, output_root: Path) -> str:
    depth = len(output_path.relative_to(output_root).parents) - 1
    return "../" * depth


def build_site(source_root: Path, output_root: Path | None = None) -> dict[str, object]:
    source_root = source_root.resolve()
    if not source_root.exists():
        raise FileNotFoundError(f"Export root does not exist: {source_root}")

    output_root = output_root.resolve() if output_root else html_output_root_for_export(source_root)

    markdown_files = iter_markdown_files(source_root)
    if not markdown_files:
        raise ValueError(f"No markdown files found under {source_root}")

    reset_output_dir(output_root)
    (output_root / "assets").mkdir(parents=True, exist_ok=True)
    (output_root / "assets" / "site.css").write_text(css_text(), encoding="utf-8")

    index_source = (source_root / "INDEX.md").read_text(encoding="utf-8")
    nav_items = parse_nav_items(index_source)
    site_title = extract_site_title(index_source, source_root.name)

    html_files_written = 0
    for source_path in markdown_files:
        output_path = output_path_for(source_path, source_root, output_root)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        markdown_text = source_path.read_text(encoding="utf-8")
        if source_path.name == "INDEX.md":
            markdown_text = H1_RE.sub(f"# {site_title}", markdown_text, count=1)
        rewritten_markdown = rewrite_markdown_links(markdown_text)
        body_html = render_markdown(rewritten_markdown)
        breadcrumbs_html = breadcrumbs_for(source_path, source_root)
        nav_html = render_nav_html(nav_items, current_source=source_path, source_root=source_root)
        template = build_template(
            title=page_title(markdown_text, source_path.stem if source_path.name != "INDEX.md" else source_root.name),
            site_title=site_title,
            nav_html=nav_html,
            body_html=body_html,
            breadcrumbs_html=breadcrumbs_html,
        )
        home_href = f"{asset_prefix_for(output_path, output_root)}index.html"
        asset_prefix = asset_prefix_for(output_path, output_root)
        html_text = template.replace("{{HOME_HREF}}", home_href).replace("{{ASSET_PREFIX}}", asset_prefix)
        output_path.write_text(html_text, encoding="utf-8")
        html_files_written += 1

    summary = {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "markdown_files_read": len(markdown_files),
        "html_files_written": html_files_written,
        "index_html": str((output_root / "index.html").resolve()),
        "css_file": str((output_root / "assets" / "site.css").resolve()),
    }
    return summary


def generate_site(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    output_root = Path(args.output).resolve() if args.output else None
    summary = build_site(Path(args.export_root), output_root)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Source root: {summary['source_root']}")
        print(f"Output root: {summary['output_root']}")
        print(f"Markdown files read: {summary['markdown_files_read']}")
        print(f"HTML files written: {summary['html_files_written']}")
        print(f"Index HTML: {summary['index_html']}")
    return summary


def main(argv: list[str] | None = None) -> int:
    generate_site(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
