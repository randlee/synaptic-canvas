# Native Codex marketplace

Synaptic Canvas publishes a Codex catalog at `.agents/plugins/marketplace.json`.
It is independent of `.claude-plugin/marketplace.json`; the existing Claude
catalog, including forwarded plugins, is unchanged.

## Install and use

Requires a Codex CLI with `codex plugin` support (tested with 0.162.1), plus Git
for Git-backed marketplace sources. No Claude CLI, Python bootstrap, API key,
or model request is needed to register and install these skill-only plugins.

```bash
codex plugin marketplace add randlee/synaptic-canvas --ref develop
codex plugin list --available --marketplace synaptic-canvas --json
codex plugin add sc-manage@synaptic-canvas --json
codex plugin add sc-gh-stack@synaptic-canvas --json
codex plugin list --marketplace synaptic-canvas --json
```

During this PR's review, use `--ref feature/sc-codex-marketplace` instead of
`--ref develop`; develop will contain the catalog only after this stack lands.
For a local checkout, use `codex plugin marketplace add /absolute/path/to/synaptic-canvas`.
Do not restrict a Git checkout to `.agents/plugins` with `--sparse`: the catalog
references `packages/sc-manage` and `packages/sc-gh-stack` as well.

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

The initial curated catalog includes `sc-manage` and `sc-gh-stack`. It does not
claim all Claude agents/commands are executable on Codex. In particular,
`sc-git-worktree` is not yet advertised as a native Codex plugin.

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
from the selected package manifests. Add packages to its curated list only after
verifying their execution workflow on Codex. Run it after metadata changes;
`--check` is included in `scripts/validate-all.py` to catch drift. Package version
bumps update both Claude and Codex manifests with `set-package-version.py`.

```bash
python3 scripts/sync-codex-marketplace.py --check
pytest -q tests/test_codex_marketplace.py
SC_TEST_CODEX_CLI=1 pytest -q tests/test_codex_marketplace.py
```

The opt-in tests use the installed CLI, temporary `CODEX_HOME` profiles and local
and Git-backed catalogs. They install/list/load/remove real plugins, exercise
bundled helpers, and make no GitHub or model requests.

Format reference: [OpenAI plugin packaging documentation](https://developers.openai.com/plugins/build/plugins).
