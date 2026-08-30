# Eval reports

Published HTML reports from `claude plugin eval` runs, one folder per plugin:

    site/reports/evals/<plugin-name>/<date-time>-<eval-name>.html

`<date-time>` is `YYYYMMDD-HHMMSS` from the run; `<eval-name>` is the case name for a
single-case run, else the suite name.

Populate with:

```bash
python3 scripts/collect-eval-reports.py
```

which sweeps `packages/*/evals/results/*/report.html` (raw run outputs are gitignored;
the copies here are the record). Existing files are never overwritten without `--force`.
