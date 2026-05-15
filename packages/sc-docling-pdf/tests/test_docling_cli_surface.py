from __future__ import annotations

import shutil
import subprocess
import os

import pytest


REQUIRED_DOCLING_FLAGS = [
    "--to",
    "--image-export-mode",
    "--pipeline",
    "--vlm-model",
    "--ocr",
    "--force-ocr",
    "--ocr-engine",
    "--table-mode",
    "--enrich-code",
    "--enrich-formula",
    "--enrich-picture-classes",
    "--enrich-picture-description",
    "--enrich-chart-extraction",
    "--artifacts-path",
    "--num-threads",
    "--page-batch-size",
    "--device",
]

REQUIRED_DOCLING_TERMS = [
    "Usage: docling [OPTIONS] source",
    "md",
    "json",
    "granite_docling",
    "smoldocling",
]

REQUIRED_DOCLING_TOOLS_TERMS = [
    "Usage: docling-tools models download",
    "granitedocling",
    "smoldocling",
    "easyocr",
]


def _run_help(command: list[str], binary_name: str) -> str:
    if shutil.which(binary_name) is None:
        pytest.skip(f"{binary_name} is not installed")

    env = os.environ.copy()
    env.setdefault("COLUMNS", "220")
    env.setdefault("PAGER", "cat")

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(command)}\n"
            f"STDOUT:\n{completed.stdout}\n"
            f"STDERR:\n{completed.stderr}"
        )
    return f"{completed.stdout}\n{completed.stderr}"


def test_docling_version_runs() -> None:
    if shutil.which("docling") is None:
        pytest.skip("docling is not installed")
    completed = subprocess.run(
        ["docling", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    combined = f"{completed.stdout}\n{completed.stderr}"
    assert "Docling version:" in combined


def test_docling_help_contains_recommended_skill_options() -> None:
    help_text = _run_help(["docling", "--help"], "docling")
    for term in REQUIRED_DOCLING_TERMS:
        assert term in help_text
    for flag in REQUIRED_DOCLING_FLAGS:
        assert flag in help_text


def test_docling_tools_download_help_contains_documented_models() -> None:
    help_text = _run_help(
        ["docling-tools", "models", "download", "--help"], "docling-tools"
    )
    for term in REQUIRED_DOCLING_TOOLS_TERMS:
        assert term in help_text
