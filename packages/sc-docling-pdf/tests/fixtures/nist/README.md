# NIST PDF Fixtures

This directory vendors two public NIST PDFs for `sc-docling-pdf` integration tests.

Why these fixtures:
- `nist-sp-500-304.pdf` is a dense, layout-rich technical standard with a long title, table of contents, list of tables/figures, structured sections, and requirements/assertions tables.
- `nist-sp-1163.pdf` is a shorter technical/economic report with abstract text, figure and table lists, and regular body prose that is easier to validate with stable text checks.

Source and rights:
- These publications were downloaded from `nvlpubs.nist.gov`.
- NIST states in `nist-sp-500-304.pdf` that the publication "is not subject to copyright."
- As NIST publications, these are U.S. government works and are suitable for local test fixtures.

Companion files:
- `*.fixture.yaml` records the source URL, checksum, and a small set of stable assertions.
- `*.reference.txt` contains short canonical text snippets that later conversion tests can match semantically.

These fixtures are intended for structural conversion tests, not for exact whole-document snapshot comparisons.
