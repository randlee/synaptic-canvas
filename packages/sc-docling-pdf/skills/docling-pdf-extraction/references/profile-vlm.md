# Profile: `vlm` — Complex Layout / Dense Mixed Content

## When to Use

Use `vlm` **only** when the standard pipeline produces poor results:
- Multi-column layout where columns merge incorrectly
- Reading order wrong in output
- Significant content missing or misplaced
- Academic papers, magazine-style, heavily designed documents

**Always try `rich` or `text` first.** VLM is 3–10× slower.

---

## Command

```bash
docling convert INPUT.pdf \
  --pipeline vlm \
  --vlm-model granite_docling \
  --to markdown \
  --to json \
  --output ./output \
  --image-export-mode referenced \
  --device mps
```

| Flag | Reason |
|------|--------|
| `--pipeline vlm` | Switches to Vision-Language Model pipeline |
| `--vlm-model granite_docling` | Best quality; IBM Granite optimized for documents |
| `--device mps` | **Critical** — VLM is very GPU-intensive; CPU is impractically slow |

---

## VLM Model Options

| Model | Flag | Quality | Speed | Size |
|-------|------|---------|-------|------|
| GraniteDocling | `--vlm-model granite_docling` | Best | Slowest | ~4 GB |
| SmolDocling | `--vlm-model smol_docling` | Good | Faster | ~1.5 GB |

Start with `smol_docling` for a quick quality check:

```bash
docling convert INPUT.pdf \
  --pipeline vlm --vlm-model smol_docling \
  --to markdown --output ./probe-vlm --device mps

cat ./probe-vlm/*.md | head -80
```

Only use `granite_docling` if smol output is insufficient.

---

## With Image Enrichment

Enrichment flags work with VLM pipeline:

```bash
docling convert INPUT.pdf \
  --pipeline vlm \
  --vlm-model granite_docling \
  --to markdown --to json \
  --output ./output \
  --image-export-mode referenced \
  --enrich-picture-classes \
  --enrich-picture-description \
  --enrich-chart-extraction \
  --device mps
```

---

## With OCR (Scanned + Complex Layout)

```bash
docling convert INPUT.pdf \
  --pipeline vlm --vlm-model granite_docling \
  --force-ocr --ocr-engine easyocr \
  --to markdown --output ./output --device mps
```

---

## Pre-downloading VLM Models

```bash
docling tools models download --vlm-model granite_docling
docling tools models download --vlm-model smol_docling

# Use offline:
docling convert INPUT.pdf --pipeline vlm --vlm-model granite_docling \
  --artifacts-path ~/.docling/models --device mps --output ./output
```

---

## Performance

| Model | Pages | Approx. Time (Apple M-series) |
|-------|-------|-------------------------------|
| smol_docling | 10 | 3–8 min |
| smol_docling | 50 | 15–40 min |
| granite_docling | 10 | 8–20 min |
| granite_docling | 50 | 45–120 min |

Split large documents first:
```bash
brew install qpdf
qpdf INPUT.pdf --pages . 1-30 -- part1.pdf
qpdf INPUT.pdf --pages . 31-60 -- part2.pdf
```

---

## Debug Layout

```bash
docling convert INPUT.pdf \
  --pipeline vlm --vlm-model smol_docling \
  --show-layout --output ./debug --device mps
```

Outputs page images with bounding boxes drawn on detected content regions.
