# Profile: `code` — Technical Documents with Code or Math

## When to Use
- API documentation, SDK references, programming guides
- Academic papers or engineering documents with equations
- Documents where code blocks must be preserved with correct formatting
- LaTeX-heavy documents

---

## Command

```bash
docling convert INPUT.pdf \
  --to markdown \
  --output ./output \
  --enrich-code \
  --enrich-formula \
  --table-mode accurate \
  --device mps
```

| Flag | Reason |
|------|--------|
| `--enrich-code` | Detects and formats code blocks, preserving indentation and language hints |
| `--enrich-formula` | Detects math expressions, renders in LaTeX notation |
| `--table-mode accurate` | Technical docs often have parameter/spec tables |

---

## Combined with Image Extraction

For technical docs that also have architecture diagrams or screenshots:

```bash
docling convert INPUT.pdf \
  --to markdown --to json \
  --output ./output \
  --enrich-code \
  --enrich-formula \
  --enrich-picture-classes \
  --image-export-mode referenced \
  --table-mode accurate \
  --device mps
```

---

## What Enrichment Does

**Without** `--enrich-code`:
```
def calculate ( x , y ) : return x + y
```

**With** `--enrich-code`:
````markdown
```python
def calculate(x, y):
    return x + y
```
````

**Without** `--enrich-formula`:
```
E = mc 2
```

**With** `--enrich-formula`:
```markdown
$E = mc^2$
```

---

## Performance

Both enrichment models add modest overhead vs `text` profile:
- 20-page doc: ~15–45 seconds (vs ~10s for `text`)
- Per-formula and per-code-block passes are lightweight vs `--enrich-picture-description`

---

## Upgrade Path

Code/formula extraction good but layout wrong?
→ Add `--enrich-code --enrich-formula` to the `vlm` profile command.

Document also has complex images?
→ Add `--enrich-picture-classes --enrich-picture-description --image-export-mode referenced`.
