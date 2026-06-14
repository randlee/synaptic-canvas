from __future__ import annotations

import json
import zipfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import beads_export as tool


def test_export_writes_hierarchical_tree_and_includes_scoped_ancestor(tmp_path: Path, capsys) -> None:
    board = [
        {
            "id": "p3-aaa",
            "title": "Epic Root",
            "issue_type": "epic",
            "status": "open",
            "priority": 1,
            "labels": ["bucket:test"],
        },
        {
            "id": "p3-aaa.1",
            "title": "Feature Child",
            "issue_type": "feature",
            "status": "open",
            "priority": 2,
            "labels": ["bucket:test"],
            "parent": "p3-aaa",
            "description": "Depends on `p3-aaa.1.1`.",
        },
        {
            "id": "p3-aaa.1.1",
            "title": "Leaf Task",
            "issue_type": "task",
            "status": "open",
            "priority": 2,
            "labels": ["bucket:test"],
            "parent": "p3-aaa.1",
        },
    ]
    board_path = tmp_path / "board.json"
    board_path.write_text(json.dumps(board), encoding="utf-8")

    cwd = Path.cwd()
    try:
        # run under the temp root so the exporter writes to tmp/export
        import os

        os.chdir(tmp_path)
        rc = tool.main(
            [
                "sample-export",
                "--root",
                "p3-aaa.1",
                "--board-json",
                str(board_path),
                "--json",
            ]
        )
    finally:
        os.chdir(cwd)

    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    export_root = tmp_path / "export" / "sample-export"
    assert output["scoped_ancestors"] == ["p3-aaa"]
    assert (export_root / "INDEX.md").exists()
    assert (
        export_root
        / "tree"
        / "p3-aaa--epic-root"
        / "p3-aaa.md"
    ).exists()
    assert (
        export_root
        / "tree"
        / "p3-aaa--epic-root"
        / "p3-aaa.1--feature-child"
        / "p3-aaa.1.md"
    ).exists()
    assert (
        export_root
        / "tree"
        / "p3-aaa--epic-root"
        / "p3-aaa.1--feature-child"
        / "p3-aaa.1.1--leaf-task"
        / "p3-aaa.1.1.md"
    ).exists()


def test_export_can_run_linkify_html_and_package_in_one_command(tmp_path: Path, capsys) -> None:
    board = [
        {
            "id": "p3-aaa",
            "title": "Epic Root",
            "issue_type": "epic",
            "status": "open",
            "priority": 1,
            "labels": ["bucket:test"],
        },
        {
            "id": "p3-aaa.1",
            "title": "Feature Child",
            "issue_type": "feature",
            "status": "open",
            "priority": 2,
            "labels": ["bucket:test"],
            "parent": "p3-aaa",
            "description": "Depends on p3-aaa.1.1.",
        },
        {
            "id": "p3-aaa.1.1",
            "title": "Leaf Task",
            "issue_type": "task",
            "status": "open",
            "priority": 2,
            "labels": ["bucket:test"],
            "parent": "p3-aaa.1",
        },
    ]
    board_path = tmp_path / "board.json"
    board_path.write_text(json.dumps(board), encoding="utf-8")

    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        rc = tool.main(
            [
                "sample-export",
                "--root",
                "p3-aaa.1",
                "--board-json",
                str(board_path),
                "--linkify",
                "--html",
                "--package",
                "--json",
            ]
        )
    finally:
        os.chdir(cwd)

    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    export_root = tmp_path / "export" / "sample-export"
    assert output["linkify_validate"]["files_changed"] == 0
    assert output["linkify_validate"]["missing_beads"] == []
    assert output["linkify_validate"]["broken_relative_links"] == []
    assert (tmp_path / "export" / "sample-export-html" / "index.html").exists()
    assert Path(output["package"]).exists()
    with zipfile.ZipFile(output["package"]) as archive:
        members = set(archive.namelist())
    assert "sample-export/INDEX.md" in members
    assert "sample-export-html/index.html" in members
    feature_md = (
        export_root
        / "tree"
        / "p3-aaa--epic-root"
        / "p3-aaa.1--feature-child"
        / "p3-aaa.1.md"
    ).read_text(encoding="utf-8")
    assert "[`p3-aaa.1.1`]" in feature_md
