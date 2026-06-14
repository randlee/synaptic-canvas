from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import beads_export_html as tool


def test_generate_site_preserves_markdown_and_writes_html_tree(tmp_path: Path, capsys) -> None:
    export_root = tmp_path / "export" / "sample"
    child_dir = export_root / "tree" / "p3-abc--root" / "p3-abc.1--child"
    child_dir.mkdir(parents=True)

    index_md = export_root / "INDEX.md"
    root_md = export_root / "tree" / "p3-abc--root" / "p3-abc.md"
    child_md = child_dir / "p3-abc.1.md"

    index_text = "\n".join(
        [
            "# Beads Export",
            "",
            "## Scoped Ancestors",
            "",
            "- [`p3-abc`](tree/p3-abc--root/p3-abc.md) — Root",
            "",
            "## Tree",
            "",
            "- [`p3-abc`](tree/p3-abc--root/p3-abc.md) — Root",
            "  - [`p3-abc.1`](tree/p3-abc--root/p3-abc.1--child/p3-abc.1.md) — Child",
            "",
        ]
    )
    index_md.write_text(index_text, encoding="utf-8")
    root_md.write_text("# Root\n\nChild: [`p3-abc.1`](p3-abc.1--child/p3-abc.1.md)\n", encoding="utf-8")
    child_original = "# Child\n\nParent: [`p3-abc`](../p3-abc.md)\n"
    child_md.write_text(child_original, encoding="utf-8")

    output_root = tmp_path / "site"
    rc = tool.main([str(export_root), "--output", str(output_root), "--json"])
    summary = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert summary["markdown_files_read"] == 3
    assert (output_root / "index.html").exists()
    assert (output_root / "tree" / "p3-abc--root" / "p3-abc.html").exists()
    assert (
        output_root
        / "tree"
        / "p3-abc--root"
        / "p3-abc.1--child"
        / "p3-abc.1.html"
    ).exists()

    child_html = (
        output_root
        / "tree"
        / "p3-abc--root"
        / "p3-abc.1--child"
        / "p3-abc.1.html"
    ).read_text(encoding="utf-8")
    index_html = (output_root / "index.html").read_text(encoding="utf-8")
    nav_html = child_html.split('<nav class="tree-nav">', 1)[1].split("</nav>", 1)[0]

    assert "../p3-abc.html" in child_html
    assert 'title="p3-abc"' in child_html
    assert ">Root</a>" in nav_html
    assert "<code>p3-abc</code>" not in nav_html
    assert "assets/site.css" in child_html
    assert "tree-nav" in child_html
    assert '<a href="index.html" class="home-link">Root</a>' in index_html
    assert ">Root</h1>" in index_html
    assert child_md.read_text(encoding="utf-8") == child_original
