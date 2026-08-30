# Eval reports

Published HTML reports from `claude plugin eval` runs, one folder per plugin:

    site/reports/evals/<plugin-name>/<date-time>-<eval-name>.html

`<date-time>` is `YYYYMMDD-HHMMSS` from the run; `<eval-name>` is the case name for a
single-case run, else the suite/fixture name. This directory is served via GitHub Pages
and is the long-term record with full history — reports are never overwritten, only
added.

How reports arrive:

- **test-packages harness runs** of `<pkg>-evals` fixtures write here directly
  (`<date-time>-<pkg>-evals.html` + JSON sidecar + artifacts folder).
- **Standalone-runner / official `claude plugin eval` runs** are swept from
  `packages/*/evals/results/` (gitignored) by:

```bash
python3 scripts/collect-eval-reports.py
```

which also rebuilds `index.html` (the Pages landing page — run it after any eval run).
Existing files are never overwritten without `--force`.
