---
name: docling-pdf-extraction
version: 0.1.0
description: >
  Convert PDF documents to markdown, extract images and tables using the docling CLI.
  Use when asked to convert a PDF, extract a datasheet, get images from a PDF, or
  process any document into structured output. Triggers: 'convert pdf', 'pdf to
  markdown', 'extract images from pdf', 'datasheet', 'get tables from pdf',
  'extract diagrams'. No MCP required — uses docling CLI only.
entry_point: /docling-pdf
triggers:
  - convert pdf
  - pdf to markdown
  - extract images
  - extract tables
  - datasheet
  - docling
  - ocr pdf
---

# Docling PDF Extraction

Convert PDFs to markdown and structured output using the docling CLI.
Selects the optimal conversion profile based on document content.

## Step 1 — Verify Installation

```bash
which docling && docling --version
```

If not found on PATH, also check common install locations — Claude Code's bash
PATH may differ from the interactive shell:

```bash
for p in "$HOME/.local/bin/docling" "$HOME/.venvs/docling/bin/docling" \
  "$(python3 -m site --user-base 2>/dev/null)/bin/docling" \
  "/opt/homebrew/bin/docling"; do
  [ -x "$p" ] && echo "Found at: $p" && break
done
```

If found at a non-PATH location, use the full path for all `docling` commands,
or export that directory to PATH for the session.

If not installed: **read `references/installation.md` before proceeding.**

---

## Step 2 — Analyze the Document

Before choosing a profile, inspect the document to understand its content type.

**Read `references/document-analysis.md`** to determine:
- Is text selectable (digital) or bitmapped (scanned)?
- Are there tables? Images? Diagrams? Charts? Code? Math?
- Is the layout simple or complex (multi-column, dense mixed content)?

---

## Step 3 — Select a Conversion Profile

| Profile | Document Type | Reference |
|---------|--------------|-----------|
| `text`  | Digital PDF, prose only, no images needed | `references/profile-text.md` |
| `scan`  | Scanned or photographed, bitmapped text | `references/profile-scan.md` |
| `rich`  | Datasheet, spec sheet, tables + photographs + diagrams ⭐ | `references/profile-rich.md` |
| `vlm`   | Complex layout, dense mixed content, poor standard results | `references/profile-vlm.md` |
| `code`  | Technical docs with code blocks or math formulas | `references/profile-code.md` |

**Tie-breaking rules:**
- Prefer `rich` over `text` — it's a superset with minimal overhead
- Prefer `rich` over `vlm` — VLM is 3–10× slower; only escalate when standard output is poor
- Profiles can be combined: `scan` + `rich` flags are additive

---

## Step 4 — Select Output Format(s)

Output format is independent of conversion profile. Multiple formats can be generated in one run.

| Need | Reference |
|------|-----------|
| LLM consumption, reading in editor | `references/output-markdown.md` |
| Viewing extracted photographs and diagrams | `references/output-images.md` |
| Working with tables or chart data | `references/output-tables.md` |
| Structured access, metadata, bounding boxes | `references/output-json.md` |

---

## Quick Reference

```bash
# Fastest — clean digital PDF
docling convert INPUT.pdf --to markdown --output ./out --device mps

# Datasheet with tables + images (most common)
docling convert INPUT.pdf --to markdown --to json --output ./out \
  --image-export-mode referenced \
  --enrich-picture-classes --enrich-picture-description \
  --enrich-chart-extraction --device mps

# Scanned document
docling convert INPUT.pdf --to markdown --output ./out \
  --force-ocr --ocr-engine easyocr --device mps
```

For all other cases, follow Steps 1–4 above.
