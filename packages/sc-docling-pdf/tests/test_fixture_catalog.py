from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PACKAGE_ROOT / "tests" / "fixtures"


def _fixture_specs() -> list[dict]:
    specs = []
    for path in sorted(FIXTURE_ROOT.rglob("*.fixture.yaml")):
        specs.append(yaml.safe_load(path.read_text()))
    return specs


def test_fixture_catalog_has_expected_files():
    fixture_ids = {spec["id"] for spec in _fixture_specs()}
    assert fixture_ids == {
        "arxiv-2008.02873v2-qubits",
        "nist-jres-111-006-exact-decimals",
        "nist-sp-1163",
        "nist-sp-500-304",
        "ti-opa188-datasheet",
    }


def test_fixture_files_and_reference_text_exist():
    for spec in _fixture_specs():
        fixture_path = next(FIXTURE_ROOT.rglob(f"{spec['id']}.fixture.yaml"))
        pdf_path = fixture_path.with_name(spec["filename"])
        ref_path = fixture_path.with_name(spec["reference_text_file"])
        assert pdf_path.exists(), pdf_path
        assert ref_path.exists(), ref_path
        assert ref_path.read_text().strip()


def test_fixture_checksums_match_catalog():
    for spec in _fixture_specs():
        fixture_path = next(FIXTURE_ROOT.rglob(f"{spec['id']}.fixture.yaml"))
        pdf_path = fixture_path.with_name(spec["filename"])
        digest = sha256(pdf_path.read_bytes()).hexdigest()
        assert digest == spec["sha256"]


def test_fixture_catalog_has_expected_assertion_shape():
    for spec in _fixture_specs():
        expected = spec["expected"]
        assert expected["must_contain"]
        assert all(isinstance(item, str) and item for item in expected["must_contain"])
        assert spec["profiles"]
