# Output: Images (PNG Extraction)

## Overview

Docling extracts all embedded raster images and rasterizes vector diagrams to PNG.
Use `--image-export-mode referenced` to save them as files.

---

## Enabling Image File Export

```bash
docling INPUT.pdf \
  --to md \
  --output ./output \
  --image-export-mode referenced \
  --device mps
```

Output structure:
```
./output/
  INPUT.md
  INPUT-pictures/
    picture-0001.png
    picture-0002.png
    ...
```

---

## Enrichment Flags

### `--enrich-picture-classes`
Classifies each image:

| Class | Description |
|-------|-------------|
| `photograph` | Real-world photo |
| `diagram` | Technical diagram, schematic, flowchart |
| `chart` | Bar, pie, line, scatter chart |
| `screenshot` | UI or screen capture |
| `logo` | Brand mark, icon |
| `table` | Image that is actually a table (not parsed as table) |

### `--enrich-picture-description`
Runs a small VLM per image to generate a natural language caption:
- `"A block diagram showing the system architecture with labeled components."`
- `"A photograph of a PCB assembly showing the main processor and memory modules."`

Captions appear in JSON output under each picture element.
Budget ~5–15 seconds per image.

---

## Viewing Extracted Images

```bash
open ./output/INPUT-pictures/              # opens folder in Finder/Preview
open ./output/INPUT-pictures/picture-0001.png
ls -lh ./output/INPUT-pictures/
qlmanage -p ./output/INPUT-pictures/picture-0001.png 2>/dev/null   # Quick Look
```

---

## Filtering by Type (JSON)

After `--enrich-picture-classes --to json`:

```python
import json

with open("./output/INPUT.json") as f:
    doc = json.load(f)

for item in doc.get("body", []):
    if item.get("label") == "picture":
        page = item.get("prov", [{}])[0].get("page_no", "?")
        cls  = item.get("classification", {}).get("predicted_class", "unknown")
        ref  = item.get("image", {}).get("uri", "")
        desc = item.get("description", "")
        print(f"Page {page} | {cls:12s} | {ref}")
        if desc:
            print(f"  → {desc}")
```

---

## Photographs vs. Vector Diagrams

| Property | Photograph | Vector Diagram |
|----------|-----------|----------------|
| PDF storage | Embedded JPEG/PNG | PDF drawing commands |
| `pdfimages` sees it | Yes | No |
| Docling extracts it | Yes | Yes (rasterized to PNG) |
| `--enrich-picture-classes` result | `photograph` | `diagram` |

Both end up as PNG files in `INPUT-pictures/`.
Vector diagrams may appear at lower DPI than their original scalable form —
use `vlm` pipeline for higher-resolution rasterization.

---

## Raw Extraction (no AI, fastest)

`pdfimages` from poppler extracts only embedded raster images (no vectors, no AI):

```bash
brew install poppler
mkdir ./raw-images
pdfimages -png INPUT.pdf ./raw-images/img
ls ./raw-images/
```

Use docling for vector diagrams, classifications, and captions.
