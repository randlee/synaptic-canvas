# Native Codex marketplace

Synaptic Canvas publishes a Codex catalog at `.agents/plugins/marketplace.json`.
It mirrors every entry in `.claude-plugin/marketplace.json`, preserving local
and forwarded sources. The existing Claude catalog is not filtered or replaced.

## Install and use

Requires a Codex CLI with `codex plugin` support (tested with 0.162.1), plus Git
for Git-backed marketplace sources. No Claude CLI, Python bootstrap, API key,
or model request is needed for catalog registration and packaging checks.
Individual plugins may need credentials, other tools or services when used.

```bash
codex plugin marketplace add randlee/synaptic-canvas --ref develop
codex plugin list --available --marketplace synaptic-canvas --json
codex plugin add sc-manage@synaptic-canvas --json
codex plugin add sc-gh-stack@synaptic-canvas --json
codex plugin list --marketplace synaptic-canvas --json
```

During this PR's review, use `--ref fix/sc-manage-stack-ci` instead of
`--ref develop`; develop will contain the catalog only after this stack lands.
For a local checkout, use `codex plugin marketplace add /absolute/path/to/synaptic-canvas`.
Do not restrict a Git checkout to `.agents/plugins` with `--sparse`: the catalog
references the complete local `packages/` tree as well.

The catalog resolves `./packages/<name>` from the repository root, not from
`.agents/plugins/`. Codex installs the whole package (skills, scripts and
references) into its plugin cache and records installed/enabled state in the
current Codex profile. `CODEX_HOME` selects an isolated/custom profile.

Start a new Codex session, then select the skills in `/skills`. Native plugins
namespace them as `sc-manage:managing-sc-packages`, `sc-gh-stack:sc-gh-stack`,
and `sc-gh-stack:sc-gh-stack-view`; use the names shown by skill autocomplete.
`/sc-manage` is a Claude/Cursor command, not a Codex slash command. Stack helper
scripts resolve relative to the loaded skills, including inside the native cache.
Using stack operations still requires Git, Python, GitHub CLI/auth and the
gh-stack extension as documented in that package; installation doesn't grant
GitHub authorization or spend GraphQL quota.

All 24 existing marketplace plugins are included, including `sc-git-worktree`
and the four forwarded entries. Inclusion is not gated on proving every workflow
in this session. See the generated [inventory](CODEX-PLUGIN-INVENTORY.md) and
[three-agent Luna inclusion review](CODEX-PLUGIN-REVIEW.md) for per-plugin caveats.
Local packages with skills use portable root manifests so their actual skills
are discoverable, not just compatibility-converted commands. Command-only and
forwarded plugins retain their existing compatibility loading.

## Update and remove

```bash
codex plugin marketplace upgrade synaptic-canvas --json
codex plugin add sc-gh-stack@synaptic-canvas --json
codex plugin remove sc-gh-stack@synaptic-canvas --json
codex plugin marketplace remove synaptic-canvas --json
```

Refresh the marketplace, then install again to select its current package
version. Removing the marketplace is separate from removing installed plugins;
remove unwanted plugins explicitly first. Preserve a configured source/ref
unless the user asks to change it. Do not add this repository's plugin settings
to a user's real profile just to test packaging.

## Artifact installer versus native plugins

The Python installer and `sc_manage_dispatch.py --codex` still copy loose
skills/scripts into `.codex/` at project or user scope. They neither register
native plugins nor report/remove native installs. Avoid installing both forms
of the same skill, which can expose duplicate entries.

A native cached `sc-manage` uses `codex plugin` for Codex plugin management; no
source checkout is needed. To use its artifact dispatcher for project or other
host installs, set `SC_REPO_PATH` to a full checkout of Synaptic Canvas. Codex
does not run this repository's Python `install.py` hook during native installs.

## Maintenance and tests

`scripts/sync-codex-marketplace.py` generates the catalog and native manifests
from the existing marketplace and local package manifests. It has no inclusion
allowlist: new and forwarded marketplace entries propagate automatically;
unrecognized source types fail validation rather than silently disappearing.
Run it after marketplace or metadata changes;
`--check` is included in `scripts/validate-all.py` to catch drift. Package version
bumps update both Claude and Codex manifests with `set-package-version.py`.

```bash
python3 scripts/sync-codex-marketplace.py --check
pytest -q tests/test_codex_marketplace.py
SC_TEST_CODEX_CLI=1 pytest -q tests/test_codex_marketplace.py
SC_TEST_CODEX_CLI=1 SC_TEST_CODEX_FORWARDED=1 pytest -q tests/test_codex_marketplace.py
```

The opt-in tests use the installed CLI, temporary `CODEX_HOME` profiles and local
and Git-backed catalogs. They install/list/load/remove real plugins, exercise
bundled helpers, and make no GitHub API or model requests. The full-catalog test
installs every local package and requires every declared skill to load enabled
from the native cache. `SC_TEST_CODEX_FORWARDED=1` also installs remote plugins
using Git transport; it does not exercise their service integrations.

Format reference: [OpenAI plugin packaging documentation](https://developers.openai.com/plugins/build/plugins).
