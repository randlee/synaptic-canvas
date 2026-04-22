# Profile: `scan` — Scanned or Photographed Documents

## When to Use
- PDF has no selectable text (pdftotext returns empty/garbled)
- Document was physically scanned or photographed
- Mixed PDF: some pages scanned, some digital

---

## Command

```bash
docling INPUT.pdf \
  --to md \
  --output ./output \
  --force-ocr \
  --ocr-engine easyocr \
  --ocr-lang en \
  --image-export-mode placeholder \
  --table-mode accurate \
  --device mps
```

| Flag | Reason |
|------|--------|
| `--force-ocr` | Discards any embedded text; re-reads everything via OCR. Use when embedded text is garbage. |
| `--ocr-engine easyocr` | Best general-purpose OCR. Handles mixed fonts and printed text better than Tesseract. |
| `--ocr-lang en` | For English-only scans, keeps EasyOCR on the smaller `english_g2` recognition model. |
| `--image-export-mode placeholder` | Prevents Markdown from ballooning with embedded base64 page images on image-only scans. |
| `--table-mode accurate` | Tables in scans are harder to detect; accurate mode uses more model capacity. |
| `--device mps` | OCR models are GPU-intensive; MPS gives significant speedup on Mac. |

If you want extracted PNGs from the scan as well as OCR text, replace `placeholder` with `referenced`.

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
--ocr-lang "en,fr"     # EasyOCR codes: en, fr, de, zh, ja ...
--ocr-lang "eng,fra"   # Tesseract codes: eng, fra, deu, chi_sim ...
```

If you omit `--ocr-lang`, Docling's EasyOCR integration defaults to `fr,de,es,en`.
That usually triggers the broader `latin_g2.pth` recognition model on first use.
For English-only technical PDFs, `--ocr-lang en` is the faster and more deterministic path.

---

## Difficult Situations

**Low-resolution scan (< 150 DPI):** Rescan at 300 DPI if possible. Otherwise try:
```bash
docling INPUT.pdf --force-ocr --ocr-engine tesseract --psm 6 --device mps
```

**Two-column scanned layout:** Escalate to VLM pipeline:
```bash
docling INPUT.pdf --pipeline vlm --vlm-model granite_docling \
  --force-ocr --device mps --output ./output
```

---

## Performance

OCR is significantly slower than text extraction:
- 10 pages: 30–120 seconds
- 100 pages: 5–20 minutes

Optimize: `--num-threads 8 --page-batch-size 2`

First use of EasyOCR may also spend time downloading model weights into `~/.EasyOCR/model/`.
If the first run fails with `CERTIFICATE_VERIFY_FAILED`, use the manual prefetch steps in `installation.md`.

---

## Upgrade Path

OCR text acceptable but layout garbled (columns merged, wrong order)?
→ Escalate to `vlm` profile with `--force-ocr` retained.
