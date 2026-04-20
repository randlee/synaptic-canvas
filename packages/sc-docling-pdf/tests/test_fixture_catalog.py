from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PACKAGE_ROOT / "tests" / "fixtures" / "nist"


def _fixture_specs() -> list[dict]:
    specs = []
    for path in sorted(FIXTURE_ROOT.glob("*.fixture.yaml")):
        specs.append(yaml.safe_load(path.read_text()))
    return specs


def test_fixture_catalog_has_expected_files():
    fixture_ids = {spec["id"] for spec in _fixture_specs()}
    assert fixture_ids == {"nist-sp-500-304", "nist-sp-1163"}


def test_fixture_files_and_reference_text_exist():
    for spec in _fixture_specs():
        pdf_path = FIXTURE_ROOT / spec["filename"]
        ref_path = FIXTURE_ROOT / spec["reference_text_file"]
        assert pdf_path.exists(), pdf_path
        assert ref_path.exists(), ref_path
        assert ref_path.read_text().strip()


def test_fixture_checksums_match_catalog():
    for spec in _fixture_specs():
        pdf_path = FIXTURE_ROOT / spec["filename"]
        digest = sha256(pdf_path.read_bytes()).hexdigest()
        assert digest == spec["sha256"]


def test_fixture_catalog_has_expected_assertion_shape():
    for spec in _fixture_specs():
        expected = spec["expected"]
        assert expected["must_contain"]
        assert all(isinstance(item, str) and item for item in expected["must_contain"])
        assert "text" in spec["profiles"]
