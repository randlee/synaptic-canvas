---
name: beads-export
version: 0.1.0
description: Export a scoped beads subtree to shareable markdown, rewrite all bead-id references to relative links, validate that links resolve, and optionally package the export as a zip. Use when the user wants an offline/shareable beads export for a feature, epic, or related subtree.
---

# Beads Export

Export a scoped beads subtree to markdown for review or sharing.

This skill does not perform any beads write. It only reads the live board and writes export artifacts under `export/`.

Implementation references for this skill are:

- `../../scripts/beads_export.py`
- `../../scripts/beads_export_common.py`
- `../../scripts/beads_export_linkify.py`
- `../../scripts/beads_export_html.py`

This skill is local-script-first. It does not invoke background agents or use an agent registry.
If this workflow is later split into delegated agent execution, that delegated layer should use the local agent-runner pattern. Until then, do not add agent-runner steps to this skill.

## Inputs

This skill takes:

- one or more parent bead IDs
- an export name or output folder name
- optional request to package the result as a zip

The parent bead IDs are the roots of the export. For each parent, export the entire descendant tree.

## Step 1 — Verify required tools

Run:

```bash
which bd && bd --version
which python3 && python3 --version
which zip || true
```

If `which` fails but you believe one of these tools is installed, check common non-PATH locations before concluding it is missing:

```bash
for candidate in \
  "$HOME/.local/bin/bd" \
  "$HOME/.venvs/beads/bin/bd" \
  "$(python3 -m site --user-base 2>/dev/null)/bin/bd" \
  "/opt/homebrew/bin/bd" \
  "/usr/local/bin/bd"; do
  [ -x "$candidate" ] && echo "Found bd at: $candidate" && break
done

for candidate in \
  "$(command -v python3 2>/dev/null)" \
  "/opt/homebrew/bin/python3" \
  "/usr/local/bin/python3"; do
  [ -x "$candidate" ] && echo "Found python3 at: $candidate" && break
done
```

If `bd` or `python3` is still missing, stop and read `references/installation-and-troubleshooting.md` before proceeding.

`zip` is only required if the user asked for a packaged archive.

## Step 2 — Define the export scope

Use only the scope the user explicitly requested.

Typical shapes:

- one root bead and all descendants
- several related root beads and all descendants
- one feature subtree plus sibling/supporting subtrees the user explicitly named

Do not invent extra roots.

If a parent bead is needed only so internal links resolve cleanly, include it as a scoped parent export and say so.

If the user supplies multiple parent bead IDs, preserve them as separate top-level roots inside the export.

## Step 3 — Run the top-level export command

The default entrypoint for this skill is one command:

```bash
python3 .claude/scripts/beads_export.py <export-name> \
  --root <bead-id> [--root <bead-id> ...] \
  --linkify \
  [--html] \
  [--package] \
  --json
```

This command:

- reads the live board with `bd list --json --all --limit 0`
- writes the hierarchical markdown export
- runs the markdown linkifier in write mode
- reruns link validation in dry-run mode
- optionally generates the HTML site
- optionally creates the shareable zip

Build the export from the live board data, not from `.beads/issues.jsonl`.

Examples:

```bash
python3 .claude/scripts/beads_export.py feature-export \
  --root <bead-id-a> \
  --root <bead-id-b> \
  --root <bead-id-c> \
  --linkify \
  --html \
  --package \
  --json
```

## Step 4 — Write the markdown export

Default target structure:

```text
export/<export-name>/
├── INDEX.md
└── tree/
    ├── <bead-id>--<slug>/
    │   ├── <bead-id>.md
    │   ├── <child-id>--<child-slug>/
    │   │   └── <child-id>.md
    │   └── ...
    └── ...
```

Required output rules:

- one markdown file per exported bead
- file name is exactly `<bead-id>.md`
- each exported bead lives inside a directory named `<bead-id>--<slug>`
- child bead directories are nested under their parent bead directory
- the filesystem layout must mirror the beads parent/child hierarchy
- `INDEX.md` contains:
  - export purpose
  - exported roots
  - included scope
  - tree view
  - links to every exported bead file
- each bead file should include:
  - title
  - summary metadata
  - description
  - dependencies
  - child beads
  - export notes

Slug rules:

- use a filesystem-safe slug derived from the bead title
- keep the bead ID at the front of the directory name
- prefer lowercase kebab-case for the slug
- if slugging logic changes, do not change the actual markdown filename; only the containing directory name may vary

Example shape:

```text
export/<export-name>/
├── INDEX.md
└── tree/
    └── <parent-id>--<parent-slug>/
        ├── <parent-id>.md
        ├── <child-id-a>--<child-slug-a>/
        │   └── <child-id-a>.md
        └── <child-id-b>--<child-slug-b>/
            └── <child-id-b>.md
```

## Step 5 — Validate linkification results

The top-level export command already runs the linkifier and then validates the result.

If you need to debug linkification directly, use:

```bash
python3 .claude/scripts/beads_export_linkify.py export/<export-name> --dry-run --json
```

The script must:

- convert bead-id references to relative markdown links
- skip already-linked references
- report missing bead targets
- report broken relative links
- work correctly with the hierarchical directory layout, not just a flat folder

Done condition for linkification:

- `files_changed: 0`
- `missing_beads: []`
- `broken_relative_links: []`

## Optional Step 6 — Generate a browser-viewable HTML site

If the user wants a static browser viewer in addition to the markdown export, run the top-level command with `--html`.

For direct debugging, generate it from the markdown export without modifying the markdown files:

```bash
python3 .claude/scripts/beads_export_html.py export/<export-name> --json
```

Expected output:

- `export/<export-name>-html/index.html`
- one `.html` page per exported markdown file
- shared sidebar navigation derived from the markdown export tree
- internal markdown links rewritten to relative `.html` links in the generated site only

This step is low risk because the markdown export remains the canonical source and is not edited by the HTML generator.

## Step 7 — Package if requested

If the user wants a shareable archive, the top-level command should be run with `--package`.

The resulting archive is:

```bash
export/packages/<export-name>-export.zip
```

Packaging rules:

- if only markdown export is requested, package the markdown export tree only
- if `--html` is also requested, include both:
  - `export/<export-name>/`
  - `export/<export-name>-html/`

Then verify the archive exists and report its path.

## Reporting rules

When reporting completion, include:

- export folder path
- whether links were validated cleanly
- whether a zip was created
- archive path if present
- any intentionally excluded beads or notes
- the parent bead IDs used as export roots

If there are missing bead targets, do not claim the export is clean. Report the exact missing IDs and where they were referenced.
