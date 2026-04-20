# Output: Markdown

## Overview

Markdown is the default output and the best format for LLM consumption
and editor reading. One `.md` file is produced per input document.

---

## Basic Usage

```bash
--to markdown   # default when no --to specified
```

---

## Image Handling in Markdown

`--image-export-mode` controls how images appear:

| Mode | Flag | Markdown Output | PNG File? |
|------|------|-----------------|-----------|
| Embedded (default) | `--image-export-mode embedded` | `![](data:image/png;base64,...)` | No |
| Referenced ⭐ | `--image-export-mode referenced` | `![](INPUT-pictures/picture-001.png)` | Yes |
| Placeholder | `--image-export-mode placeholder` | `<!-- picture -->` | No |

**Use `referenced`** for datasheets — images are real PNG files you can open.
**Use `embedded`** for a single self-contained portable file (large).
**Use `placeholder`** for text-only extraction where image positions should be marked.

---

## Table Rendering

Tables render as GFM (GitHub Flavored Markdown):

```markdown
| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| VCC       | 4.5 | 5.0 | 5.5 | V    |
| IDD       |  —  | 120 | 200 | mA   |
```

Poor table rendering? Add `--table-mode accurate`.
Very complex tables (merged cells)? Use `--to json` — see `output-json.md`.

---

## Reading the Output

```bash
cat ./output/INPUT.md | head -100     # quick view
grep "^#" ./output/INPUT.md           # document outline
grep -n "voltage\|current" ./output/INPUT.md   # search
open ./output/INPUT.md                # Mac default app
code ./output/INPUT.md                # VS Code
```

---

## Batch

```bash
docling convert ./pdfs/ --from pdf --to markdown --output ./output --device mps
```

One `.md` per PDF, named to match the source file.

---

## Combining Formats

Markdown and JSON in one run:
```bash
docling convert INPUT.pdf --to markdown --to json --output ./output
```

Use markdown for reading; JSON for structured access to metadata.
See `output-json.md`.
