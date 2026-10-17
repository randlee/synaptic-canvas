# Tests

Command: `python3 -m pytest -q packages/sc-gh-stack/tests`

Result on 2026-10-17: **135 passed in 37.62s** (Python 3.11.9).

Git fixtures and fake API transports only; no live GitHub requests. Compilation, temporary installed-entrypoint smoke checks and `git diff --check` passed. Hosted Linux CI is configured but has not run. No 500-layer experiment.
