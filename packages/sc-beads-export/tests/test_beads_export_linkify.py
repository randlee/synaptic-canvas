from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import beads_export_linkify as tool


def test_dry_run_reports_missing_and_does_not_write(tmp_path: Path, capsys) -> None:
    root = tmp_path / "export"
    beads = root / "beads"
    beads.mkdir(parents=True)

    source = beads / "p3-abc.1.md"
    target = beads / "p3-abc.2.md"
    source.write_text(
        "\n".join(
                [
                    "# Source",
                    "",
                    "- `id`: `p3-abc.1`",
                    "- `parent`: `p3-abc.2 — Parent task`",
                    "- Depends on `p3-zzz.9`",
                    "",
                ]
            ),
        encoding="utf-8",
    )
    target.write_text("# Target\n", encoding="utf-8")

    rc = tool.main([str(root), "--dry-run", "--json"])
    output = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert output["files_changed"] == 1
    assert output["missing_beads"] == [
        {
            "file": str(source.resolve()),
            "line": 5,
            "bead_id": "p3-zzz.9",
        }
    ]
    assert source.read_text(encoding="utf-8").splitlines()[2] == "- `id`: `p3-abc.1`"
    assert "p3-abc.2" in source.read_text(encoding="utf-8")


def test_write_mode_links_ids_and_validates_relative_paths(tmp_path: Path, capsys) -> None:
    root = tmp_path / "export"
    beads = root / "beads"
    beads.mkdir(parents=True)

    source = beads / "p3-abc.1.md"
    target = beads / "p3-abc.2.md"
    source.write_text(
        "\n".join(
            [
                "# Source",
                "",
                "- `id`: `p3-abc.1`",
                "- `parent`: `p3-abc.2 — Parent task`",
                "- Related bead: p3-abc.2",
                "- Existing link: [`p3-abc.2`](p3-abc.2.md)",
                "```md",
                "`p3-abc.2` inside code fence should remain untouched",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    target.write_text("# Target\n", encoding="utf-8")

    rc = tool.main([str(root), "--json"])
    output = json.loads(capsys.readouterr().out)
    updated = source.read_text(encoding="utf-8")

    assert rc == 0
    assert output["broken_relative_links"] == []
    assert "- `id`: `p3-abc.1`" in updated
    assert "- `parent`: [`p3-abc.2`](p3-abc.2.md) — Parent task" in updated
    assert "- Related bead: [`p3-abc.2`](p3-abc.2.md)" in updated
    assert "- Existing link: [`p3-abc.2`](p3-abc.2.md)" in updated
    assert "`p3-abc.2` inside code fence should remain untouched" in updated


def test_write_mode_links_nested_hierarchy_and_is_idempotent(tmp_path: Path, capsys) -> None:
    root = tmp_path / "export"
    leaf_dir = root / "tree" / "p3-abc--root" / "p3-abc.1--child"
    target_dir = root / "tree" / "p3-abc--root"
    leaf_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    source = leaf_dir / "p3-abc.1.md"
    target = target_dir / "p3-abc.md"
    source.write_text(
        "\n".join(
            [
                "# Child",
                "",
                "- `id`: `p3-abc.1`",
                "- `parent`: `p3-abc — Root`",
                "- Root bead: p3-abc",
                "",
            ]
        ),
        encoding="utf-8",
    )
    target.write_text("# Root\n", encoding="utf-8")

    rc = tool.main([str(root), "--json"])
    first = json.loads(capsys.readouterr().out)
    updated = source.read_text(encoding="utf-8")

    assert rc == 0
    assert first["files_changed"] == 1
    assert "- `parent`: [`p3-abc`](../p3-abc.md) — Root" in updated
    assert "- Root bead: [`p3-abc`](../p3-abc.md)" in updated

    rc = tool.main([str(root), "--dry-run", "--json"])
    second = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert second["files_changed"] == 0
    assert second["missing_beads"] == []
    assert second["broken_relative_links"] == []
