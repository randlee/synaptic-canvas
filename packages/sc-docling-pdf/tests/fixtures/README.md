# Fixture Corpus

This package now vendors five PDF fixtures for Docling smoke and integration testing:

- `nist/nist-sp-500-304.pdf`: table-heavy NIST technical standard
- `nist/nist-sp-1163.pdf`: NIST technical/economic report with figures and tables
- `math/nist-jres-111-006-exact-decimals.pdf`: math-heavy NIST journal article
- `datasheets/ti-opa188-datasheet.pdf`: electronics datasheet with tables, diagrams, and product boilerplate
- `papers/arxiv-2008.02873v2-qubits.pdf`: scientific paper with abstract, affiliations, figures, and references

Each fixture should have:
- a `*.fixture.yaml` sidecar with source URL, checksum, and expected assertions
- a `*.reference.txt` sidecar with short semantic snippets for later output comparisons

Licensing notes:
- NIST fixtures are U.S. government works and are suitable for repo-local test fixtures.
- The TI datasheet is public and reproducible, but not open-content. Keep it unmodified and retain notices.
- The arXiv paper was selected because the PDF states `CC BY 4.0`.
