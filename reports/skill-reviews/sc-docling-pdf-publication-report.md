# sc-docling-pdf Publication Review Report

**Target**: `packages/sc-docling-pdf`
**Reviewer**: Codex
**Date**: 2026-04-22
**Status**: Ready for initial review

---

## Executive Summary

`sc-docling-pdf` is now in a workable state for initial skill publication.

The package has:
- current Docling CLI syntax throughout the skill and references
- package-local tests for documentation, manifest wiring, CLI surface, fixtures, baseline integration, and advanced integration
- installer coverage at the repo level
- a curated local PDF fixture corpus covering NIST reports, math-heavy content, a TI datasheet, and a scientific paper
- live validation of the Docling paths the skill actually recommends

The strongest result is the **baseline `rich` datasheet path** plus selective enrichment.
That path produced the most reviewable Markdown and the clearest improvement over the baseline when chart-related enrichment was enabled.

The main caveats are operational rather than structural:
- advanced runtime depends on `transformers<5.5`
- EasyOCR may need manual model prefetch on systems with TLS / certificate issues
- VLM and picture-description paths are materially slower and should be used selectively

Overall recommendation:
- publish as an initial `0.1.0`
- position baseline `rich` as the default
- position `smoldocling` as the first VLM escalation
- reserve `granite_docling` and picture-description for slower, higher-effort passes

---

## Package Surface

Primary package files:
- `packages/sc-docling-pdf/manifest.yaml`
- `packages/sc-docling-pdf/.claude-plugin/plugin.json`
- `packages/sc-docling-pdf/skills/docling-pdf-extraction/SKILL.md`
- `packages/sc-docling-pdf/skills/docling-pdf-extraction/references/*.md`
- `packages/sc-docling-pdf/tests/*.py`

Publication-facing cleanup completed:
- tightened top-level profile selection guidance
- added quick-versus-higher-quality runtime guidance
- clarified OCR language and image-export recommendations
- documented advanced runtime validation and troubleshooting
- added installer coverage for the package itself

---

## Validation Matrix

### Fast, CI-safe checks

1. Default package-local tests

Command:

```bash
pytest -q packages/sc-docling-pdf/tests
```

Result:

```text
28 passed, 12 skipped in 10.97s
```

Notes:
- integration-heavy modules are intentionally skipped unless opt-in env vars are set

2. Installer coverage

Command:

```bash
pytest -q tests/test_sc_install.py -k sc_docling_pdf
```

Result:

```text
1 passed, 4 deselected in 0.07s
```

Coverage:
- installs `sc-docling-pdf`
- verifies skill and reference files land in `.claude/skills/docling-pdf-extraction/`

3. Manifest / frontmatter / cross-reference validators

Commands:

```bash
python3 scripts/validate-frontmatter-schema.py --package sc-docling-pdf
python3 scripts/validate-manifest-artifacts.py --package sc-docling-pdf
python3 scripts/validate-cross-references.py --package sc-docling-pdf
```

Result:

```text
PASS
```

### Live Docling integration

4. Baseline integration matrix

Command:

```bash
SC_DOCLING_RUN_INTEGRATION=1 \
SC_DOCLING_TEST_OUTPUT_ROOT=/tmp/sc-docling-integration \
pytest -q -m integration packages/sc-docling-pdf/tests/test_docling_integration.py
```

Result:

```text
5 passed in 162.71s (0:02:42)
```

Cases:
- `nist-sp-1163[text]`
- `nist-sp-500-304[text]`
- `nist-jres-111-006-exact-decimals[text]`
- `ti-opa188-datasheet[rich]`
- `arxiv-2008.02873v2-qubits[rich]`

5. Advanced integration matrix

Command:

```bash
SC_DOCLING_RUN_ADVANCED=1 \
SC_DOCLING_ADVANCED_OUTPUT_ROOT=/tmp/sc-docling-advanced-integration \
pytest -q packages/sc-docling-pdf/tests/test_docling_advanced_integration.py
```

Latest successful result:

```text
7 passed in 702.54s (0:11:42)
```

Cases:
- scan OCR with EasyOCR on a text-heavy scanned page
- `--enrich-code --enrich-formula`
- `--enrich-picture-classes`
- `--enrich-picture-description`
- `--enrich-chart-extraction`
- `--pipeline vlm --vlm-model smoldocling`
- `--pipeline vlm --vlm-model granite_docling`

---

## Review Artifacts

### Best baseline artifact

The most convincing output for initial review is:

```text
/tmp/sc-docling-advanced-integration/chart-datasheet-advanced/datasheet-1-3.md
```

Why it matters:
- it reads like a useful engineering extraction, not a toy sample
- the improvement over the baseline is visible in Markdown
- it validates the package’s strongest agent-facing use case: datasheets

Compare with:

```text
/tmp/sc-docling-advanced-integration/chart-datasheet-baseline/datasheet-1-3.md
/tmp/sc-docling-advanced-integration/chart-datasheet-advanced/datasheet-1-3.md
/tmp/sc-docling-advanced-integration/chart-datasheet-advanced/datasheet-1-3.json
```

Observed delta:
- baseline markdown had `0` `line chart` mentions
- enriched markdown had `1` `line chart` mention

### OCR / scan review artifacts

The first scan sample used a cover page and was rejected as a review artifact because it was too sparse.
The scan test was corrected to use a text-heavy abstract page.

Current scan artifact:

```text
/tmp/sc-docling-advanced-integration/scan-nist-sp-1163-abstract-page4/nist-sp-1163-scan-abstract-page4.md
```

Additional scan-review artifacts produced outside the test harness for better evaluation:

```text
/tmp/sc-docling-review/ti-scan-rich/ti-opa188-scan-pages1-2.md
/tmp/sc-docling-review/qubits-scan/qubits-scan-pages1-2.md
/tmp/sc-docling-review/qubits-scan-vlm-smol/qubits-scan-pages1-2.md
```

Why these matter:
- scanned TI datasheet exercises OCR plus engineering tables / bullets
- scanned qubits paper exercises OCR on denser academic layout
- scanned qubits paper with SmolDocling shows the OCR-only versus OCR+VLM quality tradeoff on the same source

Timed scan-review runs:

```text
ti_scan_rich:        29.1s
qubits_scan:         30.4s
qubits_scan_vlm_smol: 117.0s
```

Timed artifact paths:

```text
/tmp/sc-docling-review/ti-scan-rich-timed/ti-opa188-scan-pages1-2.md
/tmp/sc-docling-review/qubits-scan-timed/qubits-scan-pages1-2.md
/tmp/sc-docling-review/qubits-scan-vlm-smol-timed/qubits-scan-pages1-2.md
```

### VLM comparison artifacts

Use these side by side:

```text
/tmp/sc-docling-advanced-integration/vlm-smoldocling-paper-1-2/paper-1-2.md
/tmp/sc-docling-advanced-integration/vlm-granite-paper-1-2/paper-1-2.md
```

Observed:
- both preserved the title and abstract on the same subset
- Granite is slower
- Smol is the better first escalation path for “is VLM enough?” checks

Observed on the scanned qubits review set:
- OCR-only output was already usable in about 30 seconds
- SmolDocling VLM took about 117 seconds on the same scanned 2-page subset
- Smol reduced some raw OCR roughness, but did not justify replacing OCR-only as the first pass for every scanned paper

### Picture metadata artifacts

Picture classes:

```text
/tmp/sc-docling-advanced-integration/picture-classes-paper-1-4/paper-1-4.json
```

Picture descriptions:

```text
/tmp/sc-docling-advanced-integration/picture-description-paper-1-4/paper-1-4.json
```

Observed:
- class annotations are present in the picture-classes run
- description annotations are present in the picture-description run

---

## Key Findings

### 1. Default recommendation is correct now

`rich` should be the default recommendation for engineering PDFs.

Reason:
- `text` is fastest but too narrow for the common use case
- `rich` gives usable markdown, images, and JSON without the VLM tax
- it performed well on the datasheet and paper fixtures

### 2. OCR guidance needed to be more specific than “just use EasyOCR”

Two practical fixes were required:
- specify `--ocr-lang en` for English-only documents
- use `--image-export-mode placeholder` for scanned Markdown unless extracted images are explicitly needed

Reason:
- language selection changes which EasyOCR recognition model is pulled
- image-only scans can bloat Markdown badly if base64 images are embedded

The review-specific timed scan runs also support the new guidance:
- OCR-only scanned datasheet or paper subsets landed in roughly 30 seconds
- OCR+Smol VLM on the same scanned paper subset took roughly 2 minutes
- that is a meaningful enough runtime gap to justify a “quick usable” versus “slower higher-quality” split in the docs

### 3. VLM should be framed as an escalation path, not the default

Best order:
1. `text` for clean prose
2. baseline `rich`
3. `scan` for bitmapped documents
4. `smoldocling`
5. `granite_docling`

### 4. Chart extraction should be documented conservatively

The flag is worth keeping, but the docs should not promise that every chart will become clean numeric series output.

What is safe to claim:
- the flag runs successfully in the validated environment
- it can change the output meaningfully
- users should inspect the JSON and Markdown after the run

### 5. Installer readiness is now covered

Repo-level install coverage now ensures:
- the package installs
- the skill and its references are copied into the expected installed skill directory

---

## Known Caveats

1. EasyOCR first-use downloads may fail on some systems with:

```text
CERTIFICATE_VERIFY_FAILED
```

Mitigation:
- documented manual prefetch into `~/.EasyOCR/model/`

2. Granite advanced runtime is currently safest with:

```text
transformers < 5.5
```

3. VLM runs may warn:

```text
MLX not available on Apple Silicon, falling back to Transformers
```

This did not prevent successful local runs.

4. Hugging Face may warn about unauthenticated requests.

This is not a blocker for public model downloads, but `HF_TOKEN` can improve rate limits.

5. Picture-description is one of the slowest enrichment paths.

Recommendation:
- do not enable it by default
- use it when image semantics are actually needed

---

## Publication Recommendation

Recommendation: **publish for initial review as `0.1.0`**

Reasoning:
- the package is installable
- docs and commands match the actual CLI
- the recommended paths have live test coverage
- stronger artifacts exist for human review
- remaining caveats are documented and operational, not structural

Suggested reviewer focus:
1. baseline `rich` datasheet output
2. scan-only versus scan+VLM comparison on the qubits paper
3. Smol versus Granite VLM comparison
4. whether the current guidance strikes the right balance between “quick usable” and “slower higher quality”

---

## Final Checklist

- [x] manifest artifacts correct
- [x] skill references install correctly
- [x] stale Docling CLI syntax removed
- [x] package-local docs/tests added
- [x] installer test added
- [x] baseline integration matrix passing
- [x] advanced integration matrix passing
- [x] OCR caveats documented
- [x] VLM caveats documented
- [x] stronger review artifacts generated
- [x] publication review report written
