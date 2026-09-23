# Changelog

All notable changes to the **sc-gh-stack** package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-09-23

### Changed
- `recipe-cut-layer.md` now points to `sc-git-worktree --create-stacked <layer> <top> <trunk>` (0.14.0+), which performs the cut from `origin/<top>` with `--no-track`; the old advice to refresh the local ref and use plain `--create` is gone.

## [0.1.0] - 2026-09-23

### Added
- `sc-gh-stack` skill: the append-only stack model, lifecycle workflow,
  preconditions distilled from five production phases (2026-09-05 to
  2026-09-23, stacks of 2 to 21 PRs), and recipes for cutting a layer,
  linking, restacking (insert, remove a red layer, collapse the bottom),
  landing (atomic merge plus merge-async and non-linear fallbacks) and
  clearing stale per-worktree tracking; a phase-model worked example.
- Full `gh stack` v0.1.0 command guide, troubleshooting table and stack-design
  guidance carried over from the retired generic `gh-stack` skill, with
  field-verified overrides.
- `sc-gh-stack-view` skill and `gh_stack_view.py`: one-call coherence,
  mergeability, CI and LANDING table for every open stack (ported from
  atm-core; default view now shows every open stack on any trunk).
- `gh_stack_chain_check.py`: read-only pre-link check (pushed heads, linear
  ancestry, PR state and bases, clean merge into trunk) that prints the exact
  `gh stack link --base` command to run next.
- `/sc-gh-stack` and `/sc-gh-stack-view` commands.
- `gh_stack_shared.py`: the stdlib subprocess and git lookup helpers both scripts share.
- Unit tests for the scripts (real-git and mocked; every exit path).

### Notes
- Written against gh-stack extension v0.1.0. Re-verify `unstack --local`,
  `link <stack#> <pr>` and `merge` flags with `--help` if the extension moves.
- This package replaces the earlier `managing-gh-stacks` attempt (PR #101),
  whose rules contradicted the field lessons.
