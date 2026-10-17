## Files changed

Command: `git diff --cached --stat` (includes newly staged implementation and tests).

```text
 .github/workflows/tests.yml                        |  13 +
 packages/sc-gh-stack/CHANGELOG.md                  |   5 +
 packages/sc-gh-stack/README.md                     |  27 +-
 packages/sc-gh-stack/commands/sc-gh-stack-view.md  |  24 +-
 packages/sc-gh-stack/commands/sc-gh-stack.md       |   5 +-
 packages/sc-gh-stack/manifest.yaml                 |   3 +
 .../sc-gh-stack/scripts/gh_stack_chain_check.py    | 234 +++++---
 packages/sc-gh-stack/scripts/gh_stack_local.py     | 280 +++++++++
 packages/sc-gh-stack/scripts/gh_stack_remote.py    | 627 +++++++++++++++++++++
 packages/sc-gh-stack/scripts/gh_stack_shared.py    |  23 +-
 packages/sc-gh-stack/scripts/gh_stack_view.py      | 475 ++++++++--------
 .../sc-gh-stack/skills/sc-gh-stack-view/SKILL.md   | 100 ++--
 .../references/installation-and-troubleshooting.md |   8 +-
 packages/sc-gh-stack/skills/sc-gh-stack/SKILL.md   |  42 +-
 .../skills/sc-gh-stack/references/commands.md      |  19 +-
 .../references/installation-and-troubleshooting.md |   8 +-
 .../sc-gh-stack/references/phase-model-example.md  |   3 +
 .../skills/sc-gh-stack/references/preconditions.md |  16 +-
 .../sc-gh-stack/references/recipe-cut-layer.md     |  10 +-
 .../sc-gh-stack/references/recipe-evidence.md      |  18 +
 .../skills/sc-gh-stack/references/recipe-land.md   |  25 +-
 .../skills/sc-gh-stack/references/recipe-link.md   |  10 +-
 .../sc-gh-stack/references/recipe-restack.md       |  23 +-
 .../references/recipe-stale-tracking.md            |  32 +-
 .../sc-gh-stack/references/troubleshooting.md      |  12 +-
 .../skills/sc-gh-stack/references/workflow.md      |   9 +-
 .../sc-gh-stack/tests/test_gh_stack_baseline.py    | 157 ++++++
 .../sc-gh-stack/tests/test_gh_stack_chain_check.py |  38 +-
 .../tests/test_gh_stack_chain_observations.py      |  78 +++
 .../sc-gh-stack/tests/test_gh_stack_efficiency.py  | 227 ++++++++
 .../sc-gh-stack/tests/test_gh_stack_git_refresh.py |  93 +++
 packages/sc-gh-stack/tests/test_gh_stack_local.py  | 209 +++++++
 packages/sc-gh-stack/tests/test_gh_stack_remote.py | 386 +++++++++++++
 packages/sc-gh-stack/tests/test_gh_stack_view.py   |  98 +++-
 plans/2026-10-14-sc-gh-stack-api-efficiency.md     | 487 ++++++++++++++++
 35 files changed, 3352 insertions(+), 472 deletions(-)
```
