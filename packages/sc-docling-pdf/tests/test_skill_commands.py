from __future__ import annotations

from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PACKAGE_ROOT / "skills" / "docling-pdf-extraction"


def _read(rel_path: str) -> str:
    return (PACKAGE_ROOT / rel_path).read_text(encoding="utf-8")


def test_no_stale_cli_forms_remain_in_skill_docs() -> None:
    stale_terms = [
        "docling convert",
        "--to markdown",
        "docling tools models download",
        "smol_docling",
    ]

    for md_file in SKILL_ROOT.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        for term in stale_terms:
            assert term not in content, f"{md_file} still contains stale term: {term}"


@pytest.mark.parametrize(
    ("rel_path", "required_terms"),
    [
        (
            "skills/docling-pdf-extraction/SKILL.md",
            [
                "docling INPUT.pdf --to md --output ./out --device mps",
                "run the advanced-runtime validation block from `references/installation.md`",
            ],
        ),
        (
            "skills/docling-pdf-extraction/references/profile-text.md",
            ["docling INPUT.pdf", "--to md", "--no-ocr", "--table-mode accurate", "--device mps"],
        ),
        (
            "skills/docling-pdf-extraction/references/profile-scan.md",
            ["docling INPUT.pdf", "--to md", "--force-ocr", "--ocr-engine easyocr", "--table-mode accurate", "--device mps"],
        ),
        (
            "skills/docling-pdf-extraction/references/profile-rich.md",
            [
                "docling INPUT.pdf",
                "--to md",
                "--to json",
                "--image-export-mode referenced",
                "--table-mode accurate",
                "--enrich-picture-classes",
                "--enrich-picture-description",
                "--enrich-chart-extraction",
                "baseline command",
                "--device mps",
            ],
        ),
        (
            "skills/docling-pdf-extraction/references/profile-code.md",
            ["docling INPUT.pdf", "--to md", "--enrich-code", "--enrich-formula", "--table-mode accurate", "--device mps"],
        ),
        (
            "skills/docling-pdf-extraction/references/profile-vlm.md",
            ["docling INPUT.pdf", "--pipeline vlm", "--vlm-model granite_docling", "--to md", "--device mps"],
        ),
        (
            "skills/docling-pdf-extraction/references/output-images.md",
            ["docling INPUT.pdf", "--to md", "--image-export-mode referenced"],
        ),
        (
            "skills/docling-pdf-extraction/references/output-json.md",
            ["docling INPUT.pdf --to json --output ./output --device mps"],
        ),
        (
            "skills/docling-pdf-extraction/references/output-markdown.md",
            ["--to md", "docling ./pdfs/ --from pdf --to md --output ./output --device mps"],
        ),
        (
            "skills/docling-pdf-extraction/references/output-tables.md",
            ["docling INPUT.pdf", "--to md --to json", "--table-mode accurate"],
        ),
        (
            "skills/docling-pdf-extraction/references/installation.md",
            [
                'python -m pip install -U "docling[easyocr,vlm]"',
                'python -m pip install -U "transformers<5.5" "peft>=0.18.1"',
                "docling-tools models download",
                "docling --artifacts-path ~/.docling/models INPUT.pdf",
                "docling-tools models download smoldocling",
                "docling https://arxiv.org/pdf/2408.09869 --output /tmp/docling-test",
                "HybridMambaAttentionDynamicCache",
            ],
        ),
    ],
)
def test_documented_commands_include_expected_recommended_options(
    rel_path: str, required_terms: list[str]
) -> None:
    content = _read(rel_path)
    for term in required_terms:
        assert term in content, f"{rel_path} missing expected term: {term}"


def test_installation_doc_explains_cli_vs_downloader_model_names() -> None:
    content = _read("skills/docling-pdf-extraction/references/installation.md")
    assert "Downloader model names differ from CLI preset names." in content
    assert "smoldocling" in content
    assert "granitedocling" in content


def test_installation_doc_includes_runtime_validation_and_transformers_ceiling() -> None:
    content = _read("skills/docling-pdf-extraction/references/installation.md")
    assert "Validate Advanced Runtime" in content
    assert 'transformers<5.5' in content
    assert "HybridMambaAttentionDynamicCache" in content


def test_profile_matrix_covers_all_named_profiles() -> None:
    skill_content = _read("skills/docling-pdf-extraction/SKILL.md")
    for profile in ["text", "scan", "rich", "vlm", "code"]:
        assert f"`{profile}`" in skill_content
