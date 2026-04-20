from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PACKAGE_ROOT / "tests" / "fixtures"
OUTPUT_ROOT = Path(os.environ.get("SC_DOCLING_TEST_OUTPUT_ROOT", "/tmp/sc-docling-integration"))
DEVICE = os.environ.get("SC_DOCLING_TEST_DEVICE", "cpu")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _fixture_spec(fixture_id: str) -> tuple[dict, Path]:
    fixture_path = next(FIXTURE_ROOT.rglob(f"{fixture_id}.fixture.yaml"))
    return yaml.safe_load(fixture_path.read_text(encoding="utf-8")), fixture_path


CASES = [
    {
        "fixture_id": "nist-sp-1163",
        "profile": "text",
        "args": ["--to", "md", "--no-ocr", "--table-mode", "accurate"],
        "expect_json": False,
    },
    {
        "fixture_id": "nist-sp-500-304",
        "profile": "text",
        "args": ["--to", "md", "--no-ocr", "--table-mode", "accurate"],
        "expect_json": False,
    },
    {
        "fixture_id": "nist-jres-111-006-exact-decimals",
        "profile": "text",
        "args": ["--to", "md", "--no-ocr", "--table-mode", "accurate"],
        "expect_json": False,
    },
    {
        "fixture_id": "ti-opa188-datasheet",
        "profile": "rich",
        "args": ["--to", "md", "--to", "json", "--image-export-mode", "referenced", "--table-mode", "accurate"],
        "expect_json": True,
    },
    {
        "fixture_id": "arxiv-2008.02873v2-qubits",
        "profile": "rich",
        "args": ["--to", "md", "--to", "json", "--image-export-mode", "referenced", "--table-mode", "accurate"],
        "expect_json": True,
    },
]


@pytest.mark.integration
@pytest.mark.parametrize("case", CASES, ids=[f"{case['fixture_id']}[{case['profile']}]" for case in CASES])
def test_docling_fixture_matrix(case: dict) -> None:
    if os.environ.get("SC_DOCLING_RUN_INTEGRATION") != "1":
        pytest.skip("set SC_DOCLING_RUN_INTEGRATION=1 to run Docling integration coverage")

    if shutil.which("docling") is None:
        pytest.skip("docling CLI is not installed")

    spec, fixture_path = _fixture_spec(case["fixture_id"])
    pdf_path = fixture_path.with_name(spec["filename"])
    stem = pdf_path.stem

    out_dir = OUTPUT_ROOT / f"{case['fixture_id']}-{case['profile']}"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docling",
        *case["args"],
        "--output",
        str(out_dir),
        "--device",
        DEVICE,
        str(pdf_path),
    ]
    env = {**os.environ, "COLUMNS": "220", "PAGER": "cat"}
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env=env)

    (out_dir / "command.txt").write_text(" ".join(cmd), encoding="utf-8")
    (out_dir / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (out_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")

    assert result.returncode == 0, (
        f"docling failed for {case['fixture_id']}[{case['profile']}]\n"
        f"command: {' '.join(cmd)}\n"
        f"stdout:\n{result.stdout[-2000:]}\n"
        f"stderr:\n{result.stderr[-4000:]}"
    )

    md_path = out_dir / f"{stem}.md"
    assert md_path.exists(), md_path
    md_text = md_path.read_text(encoding="utf-8")
    md_norm = _normalize_text(md_text)

    for needle in spec["expected"]["must_contain"]:
        assert _normalize_text(needle) in md_norm, f"{md_path} missing expected text: {needle}"

    min_headings = spec["expected"].get("min_headings")
    if min_headings is not None:
        heading_count = sum(1 for line in md_text.splitlines() if line.lstrip().startswith("#"))
        assert heading_count >= min_headings, (md_path, heading_count, min_headings)

    if case["expect_json"]:
        json_path = out_dir / f"{stem}.json"
        assert json_path.exists(), json_path
        doc = json.loads(json_path.read_text(encoding="utf-8"))

        min_tables = spec["expected"].get("min_tables")
        if min_tables is not None:
            assert len(doc.get("tables", [])) >= min_tables, (json_path, len(doc.get("tables", [])), min_tables)

        min_figures = spec["expected"].get("min_figures")
        if min_figures is not None:
            assert len(doc.get("pictures", [])) >= min_figures, (
                json_path,
                len(doc.get("pictures", [])),
                min_figures,
            )

        artifacts_dir = out_dir / f"{stem}_artifacts"
        assert artifacts_dir.exists(), artifacts_dir
        assert any(artifacts_dir.glob("*.png")), artifacts_dir
