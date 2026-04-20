# Profile: `rich` — Datasheets, Specs, Tables + Images ⭐

## When to Use
- Component datasheets, product specifications, application notes
- Any PDF with embedded photographs, vector diagrams, or schematics
- Documents with tables (bordered or borderless)
- Bar/pie/line charts to convert to tabular data
- Technical documents where images carry meaningful content

**Recommended default for most engineering/product documents.**

---

## Command

```bash
docling convert INPUT.pdf \
  --to markdown \
  --to json \
  --output ./output \
  --image-export-mode referenced \
  --table-mode accurate \
  --enrich-picture-classes \
  --enrich-picture-description \
  --enrich-chart-extraction \
  --device mps
```

| Flag | Reason |
|------|--------|
| `--to markdown --to json` | Markdown for reading; JSON for structured image metadata and table objects |
| `--image-export-mode referenced` | Saves images as PNG files, inserts `![]()` links — viewable, not base64 bloat |
| `--table-mode accurate` | Thorough table structure extraction |
| `--enrich-picture-classes` | Classifies each image: `photograph`, `diagram`, `chart`, `logo`, `screenshot` |
| `--enrich-picture-description` | Generates a text caption per image (runs a small VLM per image) |
| `--enrich-chart-extraction` | Converts bar/pie/line charts to tabular data in JSON output |
| `--device mps` | GPU acceleration — enrichment models are compute-intensive |

---

## Output Structure

```
./output/
  INPUT.md                  ← Markdown with image references and tables
  INPUT.json                ← Full document model
  INPUT-pictures/
    picture-0001.png
    picture-0002.png
    ...
```

Image references in markdown:
```markdown
![](INPUT-pictures/picture-0001.png)
```

View extracted images:
```bash
open ./output/INPUT-pictures/    # Mac: opens Finder/Preview
ls -lh ./output/INPUT-pictures/
```

---

## Faster Variant (skip captions)

`--enrich-picture-description` is the slowest step (~5–15s per image).
Omit it when captions are not needed:

```bash
docling convert INPUT.pdf \
  --to markdown \
  --output ./output \
  --image-export-mode referenced \
  --table-mode accurate \
  --enrich-picture-classes \
  --enrich-chart-extraction \
  --device mps
```

---

## Performance

With `--enrich-picture-description`:
- 20-page datasheet with 5–10 images: 2–5 minutes

Without `--enrich-picture-description`:
- Same document: typically 30–90 seconds

---

## Upgrade Path

Text layout garbled despite good image extraction?
→ Escalate to `vlm` profile; carry enrichment flags forward.

Document is also scanned?
→ Add `--force-ocr --ocr-engine easyocr` to this command.
