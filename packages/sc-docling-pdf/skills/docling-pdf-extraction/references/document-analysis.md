# Document Analysis — Pre-Conversion Inspection

Inspect the document before converting to avoid picking the wrong profile.
Answer these four questions, then return to SKILL.md Step 3.

---

## Q1: Is text selectable or bitmapped?

**Selectable** = embedded font glyphs → extraction is fast and accurate.
**Bitmapped** = scanned or photographed → OCR required (`scan` profile).

### Test in Preview (Mac)
Open in Preview. Try to click-drag-select a word.
- Text highlights → **digital**
- Cursor becomes crosshair → **scanned**

### Test with pdftotext
```bash
brew install poppler   # if needed

pdftotext INPUT.pdf - | head -40
# Empty or garbled output → scanned
```

### Quick Python check
```bash
python3 -c "
import subprocess, sys
r = subprocess.run(['pdftotext', sys.argv[1], '-'], capture_output=True, text=True)
chars = len(r.stdout.strip())
print(f'{chars} chars extracted')
print('DIGITAL' if chars > 100 else 'LIKELY SCANNED')
" INPUT.pdf
```

---

## Q2: Does it contain tables?

### Visual check
- Grid lines / bordered cells → structured table (docling handles well)
- Columnar data, no borders → text-formatted table (may need `vlm`)
- Bar / pie / line charts → use `--enrich-chart-extraction`

### Quick docling probe
```bash
docling INPUT.pdf --to json --output ./probe --device mps
python3 -c "
import json, sys
with open(sys.argv[1]) as f: doc = json.load(f)
tables = [i for i in doc.get('body',[]) if i.get('label')=='table']
print(f'{len(tables)} table(s) found')
" ./probe/*.json
```

---

## Q3: Does it contain images or diagrams?

### Image types in PDFs

| Type | Notes |
|------|-------|
| Photograph | Raster (JPEG/PNG) embedded — extracted as PNG |
| Vector diagram | PDF drawing commands — rasterized to PNG by docling |
| Screenshot | Raster — extracted as PNG |
| Chart/graph | Use `--enrich-chart-extraction` |
| Equation | Use `--enrich-formula` |

### Check with pdfimages
```bash
pdfimages -list INPUT.pdf   # lists all embedded raster images
```

Rules of thumb:
- Many images → `rich` profile with `--image-export-mode referenced`
- No images listed but visuals appear → likely vector diagrams (docling still extracts them)
- > 2 images/page → image-heavy document

---

## Q4: How complex is the layout?

**Simple** (standard pipeline sufficient):
- Single column, clear table borders, images clearly separated

**Complex** (consider `vlm`):
- 2–3 column body text, text wrapped around images, heavy callouts/text boxes

Always try `standard` pipeline first — only escalate to `vlm` if output is garbled:
```bash
docling INPUT.pdf --to md --output ./probe-standard --device mps
cat ./probe-standard/*.md | head -60
```

Signs VLM is needed: wrong paragraph order, merged columns, missing content.

---

## Analysis Checklist

```
Text type:  [ ] Digital   [ ] Scanned
Tables:     [ ] None   [ ] Bordered   [ ] Chart/graph
Images:     [ ] None   [ ] Few (<2/page)   [ ] Many (>2/page)
Img types:  [ ] Photo   [ ] Vector diagram   [ ] Screenshot   [ ] Chart
Layout:     [ ] Simple   [ ] Complex/multi-column
Code/Math:  [ ] None   [ ] Code blocks   [ ] Equations
```

| Pattern | Profile |
|---------|---------|
| Scanned (any) | `scan` |
| Digital + no images + simple | `text` |
| Digital + tables or images + simple | `rich` |
| Digital + code or math | `code` |
| Digital + complex layout OR standard output garbled | `vlm` |
