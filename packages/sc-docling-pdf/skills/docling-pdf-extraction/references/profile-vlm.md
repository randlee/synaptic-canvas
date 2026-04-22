# Profile: `vlm` — Complex Layout / Dense Mixed Content

## When to Use

Use `vlm` **only** when the standard pipeline produces poor results:
- Multi-column layout where columns merge incorrectly
- Reading order wrong in output
- Significant content missing or misplaced
- Academic papers, magazine-style, heavily designed documents

**Always try `rich` or `text` first.** VLM is 3–10× slower.
Run the validation block from `installation.md` before using `vlm`.

---

## Command

```bash
docling INPUT.pdf \
  --pipeline vlm \
  --vlm-model granite_docling \
  --to md \
  --to json \
  --output ./output \
  --image-export-mode referenced \
  --device mps
```

| Flag | Reason |
|------|--------|
| `--pipeline vlm` | Switches to Vision-Language Model pipeline |
| `--vlm-model granite_docling` | Best quality; IBM Granite optimized for documents |
| `--device mps` | Recommended on Apple Silicon; use `cpu` if Docling refuses MPS in your environment |

---

## VLM Model Options

| Model | Flag | Quality | Speed | Size |
|-------|------|---------|-------|------|
| GraniteDocling | `--vlm-model granite_docling` | Best | Slowest | ~4 GB |
| SmolDocling | `--vlm-model smoldocling` | Good | Faster | ~1.5 GB |

Start with `smoldocling` for a quick quality check:

```bash
docling INPUT.pdf \
  --pipeline vlm --vlm-model smoldocling \
  --to md --output ./probe-vlm --device mps

cat ./probe-vlm/*.md | head -80
```

Only use `granite_docling` if smol output is insufficient.

Practical notes from local validation:
- On Apple Silicon, Granite may warn `MLX not available on Apple Silicon, falling back to Transformers`; the run can still complete successfully.
- Hugging Face may warn about unauthenticated requests. `HF_TOKEN` improves rate limits, but is not required for the public models used here.

---

## With Image Enrichment

Enrichment flags work with VLM pipeline only when the advanced runtime is healthy:

```bash
docling INPUT.pdf \
  --pipeline vlm \
  --vlm-model granite_docling \
  --to md --to json \
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
docling INPUT.pdf \
  --pipeline vlm --vlm-model granite_docling \
  --force-ocr --ocr-engine easyocr --ocr-lang en \
  --to md --output ./output --device mps
```

---

## Pre-downloading VLM Models

```bash
docling-tools models download granitedocling
docling-tools models download smoldocling

# Use offline:
docling INPUT.pdf --pipeline vlm --vlm-model granite_docling \
  --artifacts-path ~/.docling/models --device mps --output ./output
```

## Compatibility Note

If you see:

```text
ImportError: cannot import name 'HybridMambaAttentionDynamicCache'
```

your Granite runtime is incompatible with the installed `transformers`.
For this skill, pin:

```bash
python3 -m pip install -U "transformers<5.5" "peft>=0.18.1"
```

---

## Performance

| Model | Pages | Approx. Time (Apple M-series) |
|-------|-------|-------------------------------|
| smoldocling | 10 | 3–8 min |
| smoldocling | 50 | 15–40 min |
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
docling INPUT.pdf \
  --pipeline vlm --vlm-model smoldocling \
  --show-layout --output ./debug --device mps
```

Outputs page images with bounding boxes drawn on detected content regions.
