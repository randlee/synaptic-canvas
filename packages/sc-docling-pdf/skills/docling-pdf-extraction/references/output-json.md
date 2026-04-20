# Output: JSON

## Overview

The JSON output contains the full Docling document model — every element
(paragraphs, tables, images, headers, lists) with text content, structural
label, bounding boxes, and enrichment data.

---

## Enabling JSON Output

```bash
docling INPUT.pdf --to json --output ./output --device mps

# Typically paired with markdown:
docling INPUT.pdf --to md --to json --output ./output --device mps
```

---

## Top-Level Structure

```json
{
  "schema_name": "DoclingDocument",
  "version": "1.3.0",
  "name": "INPUT",
  "origin": { "filename": "INPUT.pdf", "page_count": 12 },
  "furniture": [ ... ],   // headers, footers, page numbers
  "body": [ ... ],        // main content elements (ordered)
  "pages": { ... }        // page dimensions
}
```

---

## Element Labels

Every `body` item has a `label`:

| Label | Content |
|-------|---------|
| `title` | Document title |
| `section_header` | Chapter or section heading |
| `text` | Body paragraph |
| `table` | Structured table |
| `picture` | Image or diagram |
| `list_item` | Bullet or numbered list item |
| `code` | Code block |
| `formula` | Mathematical expression |
| `caption` | Figure or table caption |
| `footnote` | Footnote text |

---

## Navigation Scripts

```python
import json

with open("./output/INPUT.json") as f:
    doc = json.load(f)

# Document outline (headers only)
for item in doc["body"]:
    if item.get("label") in ("title", "section_header"):
        level = item.get("level", 1)
        print("  " * (level - 1) + item.get("text", ""))

# Count elements by label
from collections import Counter
counts = Counter(i.get("label","?") for i in doc["body"])
for label, n in counts.most_common():
    print(f"{n:4d}  {label}")

# Page count
print(doc["origin"]["page_count"], "pages")
```

---

## Bounding Boxes

Every element includes `prov` with page number and bounding box:

```json
"prov": [{
  "page_no": 3,
  "bbox": { "l": 72.0, "t": 145.2, "r": 540.0, "b": 200.5, "coord_origin": "BOTTOMLEFT" }
}]
```

Coordinates are in PDF points (1 pt = 1/72 inch), origin bottom-left.

---

## Enrichment Data in JSON

### Picture with classification + caption
```json
{
  "label": "picture",
  "classification": { "predicted_class": "diagram", "confidence": 0.94 },
  "description": "A block diagram showing the system architecture...",
  "image": { "uri": "INPUT-pictures/picture-0003.png" }
}
```

### Formula
```json
{ "label": "formula", "text": "$P = IV\\cos\\theta$" }
```

---

## When to Use JSON vs Markdown

| Use Case | Format |
|----------|--------|
| Reading content / LLM input | Markdown |
| Image metadata, classifications, captions | JSON |
| Table data with merged cells | JSON |
| Chart extracted data | JSON |
| Bounding boxes / page location | JSON |
| Building a downstream pipeline | JSON |
