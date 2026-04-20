# Output: Tables

## Overview

Docling detects and extracts tables using a dedicated table structure model.
Tables appear as GFM tables in markdown and as structured objects in JSON.

---

## Enabling Best Table Extraction

```bash
docling convert INPUT.pdf \
  --to markdown --to json \
  --output ./output \
  --table-mode accurate \
  --device mps
```

| Flag | Effect |
|------|--------|
| `--table-mode accurate` (default) | Thorough structure recognition. Better for complex tables. |
| `--table-mode fast` | Faster, lower accuracy. Only for simple bordered tables. |
| `--no-tables` | Disable table extraction entirely. |

---

## Chart-to-Table Extraction

```bash
docling convert INPUT.pdf \
  --to markdown --to json \
  --output ./output \
  --table-mode accurate \
  --enrich-chart-extraction \
  --device mps
```

`--enrich-chart-extraction` reads chart images and outputs their underlying data
as structured tables in the JSON output under the chart element.

---

## Markdown Table Output

```markdown
| Parameter | Symbol | Min | Typ | Max | Unit |
|-----------|--------|-----|-----|-----|------|
| Supply Voltage | VCC | 4.5 | 5.0 | 5.5 | V |
| Quiescent Current | IQ | — | 8 | 15 | mA |
```

Limitations of markdown tables: no merged cells, no multi-line cells,
rotated headers may be lost. For complex tables → use JSON.

---

## Export Tables to CSV

```python
import json, csv, os

with open("./output/INPUT.json") as f:
    doc = json.load(f)

os.makedirs("./output/tables", exist_ok=True)
table_num = 0

for item in doc.get("body", []):
    if item.get("label") == "table":
        table_num += 1
        grid = item.get("data", {}).get("grid", [])
        path = f"./output/tables/table-{table_num:03d}.csv"
        with open(path, "w", newline="") as f:
            csv.writer(f).writerows(
                [cell.get("text", "") for cell in row] for row in grid
            )
        print(f"Saved {path} ({len(grid)} rows)")
```

---

## Verify Table Count

```bash
python3 -c "
import json, sys
with open(sys.argv[1]) as f: doc = json.load(f)
tables = [i for i in doc.get('body',[]) if i.get('label')=='table']
print(f'{len(tables)} table(s)')
for n,t in enumerate(tables,1):
    grid = t.get('data',{}).get('grid',[])
    page = t.get('prov',[{}])[0].get('page_no','?')
    print(f'  Table {n}: page {page}, {len(grid)}r x {len(grid[0]) if grid else 0}c')
" ./output/INPUT.json
```

---

## Borderless / Text-formatted Tables

Docling handles bordered tables well. Borderless columnar text is harder.
If borderless tables are being missed:

1. Confirm `--table-mode accurate` is set (default)
2. Escalate to `vlm` pipeline — reads the page visually:

```bash
docling convert INPUT.pdf \
  --pipeline vlm --vlm-model granite_docling \
  --to markdown --to json \
  --output ./output \
  --table-mode accurate \
  --device mps
```
