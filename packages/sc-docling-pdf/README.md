# sc-docling-pdf

[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](https://github.com/randlee/synaptic-canvas/blob/main/docs/PUBLISHER-VERIFICATION.md)
[![Security Scanned](https://img.shields.io/badge/security-scanned-blue)](https://github.com/randlee/synaptic-canvas/blob/main/SECURITY.md)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](../../../LICENSE)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)

Scope: Local-only
Requires: docling ≥ 2.90.0, python ≥ 3.10

Convert PDF documents to markdown and structured output using the docling CLI. Selects the optimal conversion profile based on document content: clean text, scanned/OCR, rich datasheets with images and tables, complex layouts via VLM, or technical documents with code and formulas.

Security: See [SECURITY.md](../../../SECURITY.md) for security policy and practices.

## Summary

Single skill package for PDF-to-structured-output conversion using the docling CLI. No MCP required — pure CLI workflow. Automatically selects from five conversion profiles based on document analysis, and supports multiple output formats in a single run.

## Quick Start (Local-only)

1) Install docling:
   ```bash
   pip install "docling>=2.90.0"
   ```

2) Install the package into a repo:
   ```bash
   python3 tools/sc-install.py install sc-docling-pdf --dest /path/to/your-repo/.claude
   ```

3) Convert a PDF in Claude Code:
   ```
   /docling-pdf path/to/document.pdf
   ```
   Or trigger by phrasing: "convert pdf", "pdf to markdown", "extract images from pdf", "datasheet", "get tables from pdf", or "extract diagrams".

## Conversion Profiles

| Profile | Document Type | When to Use |
|---------|--------------|-------------|
| `text`  | Digital PDF, prose only, no images needed | Fastest path — seconds |
| `scan`  | Scanned or photographed, bitmapped text | OCR-first, selectable OCR engine and language |
| `rich`  | Datasheets, spec sheets, tables + photos + diagrams ⭐ | Best default: quick and thorough |
| `vlm`   | Complex layout, dense mixed content | Layout rescue after standard paths fail |
| `code`  | Technical docs with code blocks or math formulas | Structure-focused with formula/code fidelity |

Profiles can be combined (e.g., `scan` + `rich` flags are additive). Output formats (markdown, images, tables, JSON) are independent of the conversion profile.

## Output Formats

| Need | Format |
|------|--------|
| LLM consumption, editor reading | Markdown |
| Viewing extracted photographs and diagrams | PNG images (referenced) |
| Working with tables or chart data | CSV/Tables |
| Structured access, metadata, bounding boxes | JSON |

## Requirements

- `docling >= 2.90.0` (cli)
- `python >= 3.10`
- Optional: `poppler` (for document analysis), `docling[easyocr,vlm]` (for advanced workflows)

## Skill

### docling-pdf-extraction
Analyzes the PDF, selects the optimal conversion profile, and runs the docling CLI with the right flags for the document type. Reads supporting references for each profile and output format.

## Install / Uninstall

Install (local-only):
```bash
python3 tools/sc-install.py install sc-docling-pdf --dest /path/to/your-repo/.claude
```

Uninstall:
```bash
python3 tools/sc-install.py uninstall sc-docling-pdf --dest /path/to/your-repo/.claude
```

## Documentation

- [README.md](README.md) — This file
- [CHANGELOG.md](CHANGELOG.md) — Version history and changes

## License

MIT License. See [LICENSE](../../../LICENSE) for details.

## Contributing

See the main [synaptic-canvas repository](https://github.com/randlee/synaptic-canvas) for contribution guidelines.