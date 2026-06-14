# sc-beads-export

Scope: Project
Requires: `python3`, `bd`, Python `markdown` package

Export scoped beads subtrees to hierarchical markdown for review or handoff. The package can also rewrite bead references to relative markdown links, validate those links, build a static HTML viewer, and package the result as a zip.

Security: See [SECURITY.md](../../../SECURITY.md) for repository security policy and practices.

## Summary
- Exports one or more root beads plus all descendants from the live board
- Includes scoped ancestors when needed so parent links resolve cleanly
- Rewrites bead-id references to relative markdown links and validates them
- Optionally renders an HTML site and packages the export under `export/packages/`

## Installed Components
- Skill: `skills/beads-export/SKILL.md`
- Scripts: `scripts/beads_export.py`, `scripts/beads_export_linkify.py`, `scripts/beads_export_html.py`, `scripts/beads_export_common.py`

## Usage
```bash
python3 .claude/scripts/beads_export.py feature-export \
  --root p3-abc \
  --root p3-def \
  --linkify \
  --html \
  --package \
  --json
```

The top-level script reads the live board with `bd list --json --all --limit 0` unless `--board-json` is provided for offline or test runs.

## Notes
- This package is local-only because it depends on the current repository's beads board.
- The HTML generator imports the Python `markdown` package; it is a real runtime dependency and is declared in `manifest.yaml`.
- Repository tests for this package use `--board-json` fixtures and temporary directories so they remain CI-safe and do not require live beads access.
