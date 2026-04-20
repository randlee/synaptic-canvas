# Profile: `scan` — Scanned or Photographed Documents

## When to Use
- PDF has no selectable text (pdftotext returns empty/garbled)
- Document was physically scanned or photographed
- Mixed PDF: some pages scanned, some digital

---

## Command

```bash
docling convert INPUT.pdf \
  --to markdown \
  --output ./output \
  --force-ocr \
  --ocr-engine easyocr \
  --table-mode accurate \
  --device mps
```

| Flag | Reason |
|------|--------|
| `--force-ocr` | Discards any embedded text; re-reads everything via OCR. Use when embedded text is garbage. |
| `--ocr-engine easyocr` | Best general-purpose OCR. Handles mixed fonts and printed text better than Tesseract. |
| `--table-mode accurate` | Tables in scans are harder to detect; accurate mode uses more model capacity. |
| `--device mps` | OCR models are GPU-intensive; MPS gives significant speedup on Mac. |

### `--ocr` vs `--force-ocr`

| Flag | Behavior |
|------|----------|
| `--ocr` (default) | OCR runs only on bitmapped regions. Preserves existing embedded text. |
| `--force-ocr` | Replaces ALL text with OCR, including embedded text. |

Use `--ocr` for mixed PDFs (some digital pages, some scanned).
Use `--force-ocr` when embedded text is entirely corrupted or missing.

---

## OCR Engine Selection

| Engine | Flag | Best For |
|--------|------|----------|
| EasyOCR | `--ocr-engine easyocr` | General use; multi-language; mixed fonts |
| Tesseract | `--ocr-engine tesseract` | Fast; clean single-language scans |
| RapidOCR | `--ocr-engine rapidocr` | Lightweight; simple documents |
| Auto | `--ocr-engine auto` | System picks best available |

Install EasyOCR: `pip install docling[easyocr]`

### Language hints
```bash
--ocr-lang "eng,fra"   # EasyOCR codes: en, fr, de, zh, ja ...
--ocr-lang "eng,fra"   # Tesseract codes: eng, fra, deu, chi_sim ...
```

---

## Difficult Situations

**Low-resolution scan (< 150 DPI):** Rescan at 300 DPI if possible. Otherwise try:
```bash
docling convert INPUT.pdf --force-ocr --ocr-engine tesseract --psm 6 --device mps
```

**Two-column scanned layout:** Escalate to VLM pipeline:
```bash
docling convert INPUT.pdf --pipeline vlm --vlm-model granite_docling \
  --force-ocr --device mps --output ./output
```

---

## Performance

OCR is significantly slower than text extraction:
- 10 pages: 30–120 seconds
- 100 pages: 5–20 minutes

Optimize: `--num-threads 8 --page-batch-size 2`

---

## Upgrade Path

OCR text acceptable but layout garbled (columns merged, wrong order)?
→ Escalate to `vlm` profile with `--force-ocr` retained.
