from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
import yaml


pytestmark = pytest.mark.integration

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PACKAGE_ROOT / "tests" / "fixtures"
OUTPUT_ROOT = Path(os.environ.get("SC_DOCLING_ADVANCED_OUTPUT_ROOT", "/tmp/sc-docling-advanced-integration"))
DEFAULT_DEVICE = os.environ.get("SC_DOCLING_TEST_DEVICE", "cpu")
VLM_DEVICE = os.environ.get("SC_DOCLING_VLM_DEVICE", "mps")

EASYOCR_MODELS = {
    "craft_mlt_25k.pth": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip",
    "english_g2.pth": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip",
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _require_enabled() -> None:
    if os.environ.get("SC_DOCLING_RUN_ADVANCED") != "1":
        pytest.skip("set SC_DOCLING_RUN_ADVANCED=1 to run advanced Docling integration coverage")

    if shutil.which("docling") is None:
        pytest.skip("docling CLI is not installed")


def _fixture_spec(fixture_id: str) -> tuple[dict, Path]:
    fixture_path = next(FIXTURE_ROOT.rglob(f"{fixture_id}.fixture.yaml"))
    return yaml.safe_load(fixture_path.read_text(encoding="utf-8")), fixture_path


def _subset_pdf(source: Path, page_indexes: list[int], out_path: Path) -> Path:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for idx in page_indexes:
        writer.add_page(reader.pages[idx])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as handle:
        writer.write(handle)
    return out_path


def _image_only_pdf(source: Path, page_index: int, out_path: Path) -> Path:
    fitz = pytest.importorskip("fitz")
    image_mod = pytest.importorskip("PIL.Image")

    png_path = out_path.with_suffix(".png")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(source)
    page = doc.load_page(page_index)
    pix = page.get_pixmap(dpi=220, alpha=False)
    pix.save(str(png_path))

    img = image_mod.open(png_path).convert("RGB")
    img.save(out_path, "PDF", resolution=220.0)
    return out_path


def _ensure_easyocr_models() -> None:
    curl = shutil.which("curl")
    if curl is None:
        pytest.skip("curl is required to prefetch EasyOCR models in this environment")

    model_dir = Path.home() / ".EasyOCR" / "model"
    model_dir.mkdir(parents=True, exist_ok=True)

    for filename, url in EASYOCR_MODELS.items():
        target = model_dir / filename
        if target.exists():
            continue

        zip_path = model_dir / f"{target.stem}.zip"
        subprocess.run([curl, "-L", "-o", str(zip_path), url], check=True, timeout=1800)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extract(filename, model_dir)
        zip_path.unlink()
        assert target.exists(), target


def _run_docling(
    *,
    source: Path,
    out_dir: Path,
    args: list[str],
    device: str,
    timeout: int = 7200,
) -> subprocess.CompletedProcess[str]:
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docling",
        *args,
        "--output",
        str(out_dir),
        "--device",
        device,
        str(source),
    ]
    env = {**os.environ, "COLUMNS": "220", "PAGER": "cat"}
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)

    (out_dir / "command.txt").write_text(" ".join(cmd), encoding="utf-8")
    (out_dir / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (out_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")

    assert result.returncode == 0, (
        f"docling failed\ncommand: {' '.join(cmd)}\n"
        f"stdout:\n{result.stdout[-2000:]}\n"
        f"stderr:\n{result.stderr[-4000:]}"
    )
    return result


def test_scan_profile_easyocr_english_placeholder() -> None:
    _require_enabled()
    _ensure_easyocr_models()

    spec, fixture_path = _fixture_spec("nist-sp-1163")
    pdf_path = fixture_path.with_name(spec["filename"])
    # Use the abstract page rather than the cover page so OCR quality is actually reviewable.
    scan_pdf = _image_only_pdf(pdf_path, 3, OUTPUT_ROOT / "generated" / "nist-sp-1163-scan-abstract-page4.pdf")
    out_dir = OUTPUT_ROOT / "scan-nist-sp-1163-abstract-page4"

    _run_docling(
        source=scan_pdf,
        out_dir=out_dir,
        args=[
            "--to",
            "md",
            "--force-ocr",
            "--ocr-engine",
            "easyocr",
            "--ocr-lang",
            "en",
            "--image-export-mode",
            "placeholder",
            "--table-mode",
            "accurate",
        ],
        device="cpu",
        timeout=3600,
    )

    md_path = out_dir / "nist-sp-1163-scan-abstract-page4.md"
    text = md_path.read_text(encoding="utf-8")
    norm = _normalize_text(text)
    assert "abstract" in norm
    assert "there is a general concern that the u.s. manufacturing industry has lost competitiveness" in norm
    assert "additive manufacturing is a relatively new process" in norm
    assert "data:image/png;base64" not in text


def test_enrich_code_and_formula_on_math_subset() -> None:
    _require_enabled()

    spec, fixture_path = _fixture_spec("nist-jres-111-006-exact-decimals")
    pdf_path = fixture_path.with_name(spec["filename"])
    subset = _subset_pdf(pdf_path, [0, 1, 2, 3], OUTPUT_ROOT / "generated" / "math-1-4.pdf")
    out_dir = OUTPUT_ROOT / "code-formula-math-1-4"

    _run_docling(
        source=subset,
        out_dir=out_dir,
        args=[
            "--to",
            "md",
            "--enrich-code",
            "--enrich-formula",
            "--table-mode",
            "accurate",
        ],
        device=DEFAULT_DEVICE,
        timeout=3600,
    )

    md_path = out_dir / "math-1-4.md"
    text = md_path.read_text(encoding="utf-8")
    norm = _normalize_text(text)
    assert "integer representation of decimal numbers for exact computations" in norm
    assert "## 1 introduction" in text.lower()
    assert "```" in text


def test_enrich_picture_classes_on_paper_subset() -> None:
    _require_enabled()

    spec, fixture_path = _fixture_spec("arxiv-2008.02873v2-qubits")
    pdf_path = fixture_path.with_name(spec["filename"])
    subset = _subset_pdf(pdf_path, [0, 1, 2, 3], OUTPUT_ROOT / "generated" / "paper-1-4.pdf")
    out_dir = OUTPUT_ROOT / "picture-classes-paper-1-4"

    _run_docling(
        source=subset,
        out_dir=out_dir,
        args=[
            "--to",
            "md",
            "--to",
            "json",
            "--image-export-mode",
            "referenced",
            "--table-mode",
            "accurate",
            "--enrich-picture-classes",
        ],
        device=DEFAULT_DEVICE,
    )

    md_path = out_dir / "paper-1-4.md"
    json_path = out_dir / "paper-1-4.json"
    assert "high-fidelity control of superconducting qubits" in _normalize_text(
        md_path.read_text(encoding="utf-8")
    )

    doc = json.loads(json_path.read_text(encoding="utf-8"))
    assert doc["pictures"], json_path
    assert any(
        ann.get("kind") == "classification"
        for pic in doc["pictures"]
        for ann in pic.get("annotations", [])
    )


def test_enrich_picture_description_on_paper_subset() -> None:
    _require_enabled()

    spec, fixture_path = _fixture_spec("arxiv-2008.02873v2-qubits")
    pdf_path = fixture_path.with_name(spec["filename"])
    subset = _subset_pdf(pdf_path, [0, 1, 2, 3], OUTPUT_ROOT / "generated" / "paper-1-4.pdf")
    out_dir = OUTPUT_ROOT / "picture-description-paper-1-4"

    _run_docling(
        source=subset,
        out_dir=out_dir,
        args=[
            "--to",
            "md",
            "--to",
            "json",
            "--image-export-mode",
            "referenced",
            "--table-mode",
            "accurate",
            "--enrich-picture-classes",
            "--enrich-picture-description",
        ],
        device=VLM_DEVICE,
    )

    md_path = out_dir / "paper-1-4.md"
    json_path = out_dir / "paper-1-4.json"
    assert "abstract" in _normalize_text(md_path.read_text(encoding="utf-8"))

    doc = json.loads(json_path.read_text(encoding="utf-8"))
    assert any(
        ann.get("kind") == "description"
        for pic in doc["pictures"]
        for ann in pic.get("annotations", [])
    )


def test_chart_extraction_changes_datasheet_markdown() -> None:
    _require_enabled()

    spec, fixture_path = _fixture_spec("ti-opa188-datasheet")
    pdf_path = fixture_path.with_name(spec["filename"])
    subset = _subset_pdf(pdf_path, [0, 1, 2], OUTPUT_ROOT / "generated" / "datasheet-1-3.pdf")

    base_out = OUTPUT_ROOT / "chart-datasheet-baseline"
    adv_out = OUTPUT_ROOT / "chart-datasheet-advanced"

    _run_docling(
        source=subset,
        out_dir=base_out,
        args=[
            "--to",
            "md",
            "--to",
            "json",
            "--image-export-mode",
            "referenced",
            "--table-mode",
            "accurate",
        ],
        device=DEFAULT_DEVICE,
    )
    _run_docling(
        source=subset,
        out_dir=adv_out,
        args=[
            "--to",
            "md",
            "--to",
            "json",
            "--image-export-mode",
            "referenced",
            "--table-mode",
            "accurate",
            "--enrich-picture-classes",
            "--enrich-chart-extraction",
        ],
        device=DEFAULT_DEVICE,
    )

    base_md = (base_out / "datasheet-1-3.md").read_text(encoding="utf-8")
    adv_md = (adv_out / "datasheet-1-3.md").read_text(encoding="utf-8")
    assert "line chart" not in base_md.lower()
    assert "line chart" in adv_md.lower()

    doc = json.loads((adv_out / "datasheet-1-3.json").read_text(encoding="utf-8"))
    assert doc["pictures"], adv_out
    assert any(
        ann.get("kind") == "classification"
        and any(
            pred.get("class_name") == "line_chart"
            for pred in ann.get("predicted_classes", [])
        )
        for pic in doc["pictures"]
        for ann in pic.get("annotations", [])
    )


def test_vlm_smoldocling_on_paper_subset() -> None:
    _require_enabled()

    spec, fixture_path = _fixture_spec("arxiv-2008.02873v2-qubits")
    pdf_path = fixture_path.with_name(spec["filename"])
    subset = _subset_pdf(pdf_path, [0, 1], OUTPUT_ROOT / "generated" / "paper-1-2.pdf")
    out_dir = OUTPUT_ROOT / "vlm-smoldocling-paper-1-2"

    _run_docling(
        source=subset,
        out_dir=out_dir,
        args=[
            "--pipeline",
            "vlm",
            "--vlm-model",
            "smoldocling",
            "--to",
            "md",
            "--to",
            "json",
            "--image-export-mode",
            "referenced",
        ],
        device=VLM_DEVICE,
    )

    text = (out_dir / "paper-1-2.md").read_text(encoding="utf-8")
    norm = _normalize_text(text)
    assert "high-fidelity control of superconducting qubits" in norm
    assert "abstract" in norm


def test_vlm_granite_docling_on_paper_subset() -> None:
    _require_enabled()

    spec, fixture_path = _fixture_spec("arxiv-2008.02873v2-qubits")
    pdf_path = fixture_path.with_name(spec["filename"])
    subset = _subset_pdf(pdf_path, [0, 1], OUTPUT_ROOT / "generated" / "paper-1-2.pdf")
    out_dir = OUTPUT_ROOT / "vlm-granite-paper-1-2"

    _run_docling(
        source=subset,
        out_dir=out_dir,
        args=[
            "--pipeline",
            "vlm",
            "--vlm-model",
            "granite_docling",
            "--to",
            "md",
            "--to",
            "json",
            "--image-export-mode",
            "referenced",
        ],
        device=VLM_DEVICE,
    )

    text = (out_dir / "paper-1-2.md").read_text(encoding="utf-8")
    norm = _normalize_text(text)
    assert "high-fidelity control of superconducting qubits" in norm
    assert "abstract" in norm
