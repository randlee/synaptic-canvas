# Profile: `rich` — Datasheets, Specs, Tables + Images ⭐

## When to Use
- Component datasheets, product specifications, application notes
- Any PDF with embedded photographs, vector diagrams, or schematics
- Documents with tables (bordered or borderless)
- Bar/pie/line charts to convert to tabular data
- Technical documents where images carry meaningful content

**Recommended default for most engineering/product documents.**
Start with the baseline command below. Add enrichment flags only after the runtime validation in `installation.md` passes.

---

## Command

```bash
docling INPUT.pdf \
  --to md \
  --to json \
  --output ./output \
  --image-export-mode referenced \
  --table-mode accurate \
  --device mps
```

| Flag | Reason |
|------|--------|
| `--to md --to json` | Markdown for reading; JSON for structured image metadata and table objects |
| `--image-export-mode referenced` | Saves images as PNG files, inserts `![]()` links — viewable, not base64 bloat |
| `--table-mode accurate` | Thorough table structure extraction |
| `--device mps` | GPU acceleration if available; use `--device cpu` elsewhere |

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

## Optional Enrichment Variant

Only use this after the Step 1 validation passes:

```bash
docling INPUT.pdf \
  --to md \
  --to json \
  --output ./output \
  --image-export-mode referenced \
  --table-mode accurate \
  --enrich-picture-classes \
  --enrich-picture-description \
  --enrich-chart-extraction \
  --device mps
```

Notes:
- `--enrich-picture-classes` adds class labels such as `diagram`, `chart`, or `photograph`
- `--enrich-picture-description` adds image captions and is usually the slowest flag
- `--enrich-chart-extraction` converts supported charts into tabular JSON, but is the most dependency-sensitive enrichment step
- If you hit a Granite / `transformers` import error, remove the enrichment flags and use the baseline command

---

## Performance

Baseline `rich` without enrichment:
- 20-page datasheet: typically tens of seconds on Apple Silicon, longer on CPU

With `--enrich-picture-description`:
- 20-page datasheet with 5–10 images: 2–5 minutes

Without `--enrich-picture-description`:
- Same document: typically 30–90 seconds

---

## Upgrade Path

Text layout garbled despite good image extraction?
→ Escalate to `vlm` profile; carry enrichment flags forward only if runtime validation passes.

Document is also scanned?
→ Add `--force-ocr --ocr-engine easyocr` to this command.
