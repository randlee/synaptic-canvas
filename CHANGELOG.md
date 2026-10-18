# Changelog
All notable marketplace-wide changes are documented in this file. Package changes
are in each package's own `packages/<package>/CHANGELOG.md`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
The marketplace platform version lives in `version.yaml` and is independent of
package versions (see `docs/versioning-strategy.md`).

## [Unreleased]

### Added
- Full Codex catalog parity (24 plugins, including forwarded sources), generated
  plugin inventory, three-agent Luna inclusion review, and native discovery
  checks for every local skill package.
- Native Codex marketplace for sc-manage and sc-gh-stack, generated manifests,
  drift validation, isolated CLI install/load/remove tests and install guidance.
- Explicit Claude, Codex, Cursor and Hermes target flags for `sc-manage` and
  the installer; non-Claude targets receive portable skills/scripts/assets.
  Cursor sc-manage also writes a native `/sc-manage` command. `--dest` accepts
  one explicit target, while legacy defaults are preserved.

### Fixed
- Windows installer status encoding and native catalog path normalization.
  Version tests now check registry/manifest consistency instead of stale pins.

## [0.14.0] - 2026-10-17
### Added
- sc-launchpad sessions, `env_file` support, and model/effort selection from the
  shared model table; ATM teammate launches generate and register a new identity
  (sc-launchpad 0.14.2, sc-launch-term 0.14.2, sc-codex 0.14.1).
- Forwarded `process-porn` plugin in `marketplace.json` (#117).

### Changed
- sc-gh-stack 0.2.0 (#134, #136).
- Child agents never inherit the parent's `ATM_IDENTITY`; `BEADS_ACTOR` follows
  the child's `ATM_IDENTITY` (#133).
- sc-git-worktree installs globally via `.local.j2` templating (#114).

### Fixed
- `set-package-version.py` keeps forwarded marketplace entries on version bumps
  (#135).
- `set-package-version.py` writes the marketplace version into
  `marketplace.json`, `registry.json` and the nuget registry from `version.yaml`;
  it used to copy the version of the alphabetically first package.
  `--marketplace X.Y.Z` with no package bumps only the platform version.
