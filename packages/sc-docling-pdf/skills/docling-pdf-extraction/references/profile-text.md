# Profile: `text` — Clean Digital PDF

## When to Use
- PDF has selectable text (confirmed via pdftotext or Preview)
- No images needed in output
- Single-column or simple layout
- Goal is fast, clean prose extraction

If you need tables, images, or diagrams → use `rich` profile instead.

---

## Command

```bash
docling convert INPUT.pdf \
  --to markdown \
  --output ./output \
  --no-ocr \
  --table-mode accurate \
  --device mps
```

| Flag | Reason |
|------|--------|
| `--no-ocr` | Skip OCR — text is embedded. Significant speed gain. |
| `--table-mode accurate` | Thorough table model. Minimal cost for digital PDFs. |
| `--device mps` | Apple Silicon GPU acceleration. Use `--device cpu` on non-Mac. |

---

## Batch

```bash
docling convert ./pdfs/ \
  --from pdf \
  --to markdown \
  --output ./output \
  --no-ocr \
  --table-mode accurate \
  --num-threads 8 \
  --device mps
```

---

## Performance

Fastest profile. Typical Apple Silicon speeds:
- 1–20 pages: 2–10 seconds
- 100+ pages: 30–90 seconds

---

## Upgrade Path

Poor output quality (garbled paragraphs, missing sections)?
1. Try `rich` profile — adds picture detection, better table handling
2. Try `vlm` profile — full vision-language model re-read
