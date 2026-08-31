# Changelog

All notable changes to sc-commit-push-pr will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.0] - 2026-08-30

- **Hard dependency on the gh-stack toolchain (breaking for uninstalled toolchains):** sc-commit-push-pr is the critical junction where a stack-unaware commit/pull/merge/push or PR creation can corrupt a `gh stack`'s linearity, so the `gh` CLI, the `gh-stack` extension, and the managing-gh-stacks skill (package `sc-gh-stack`) are now required unconditionally -- every run, every branch, every provider (GitHub and Azure DevOps alike). Missing any of them refuses immediately with the new `PREFLIGHT.STACK_PREREQS_MISSING` error, both from the SubAgentStart preflight hooks and from the scripts themselves.
- Added stack-layer detection (state-based: a `gh-stack` marker under the worktree's git-dir, the same signal `gh stack` uses). Plain branches are unaffected -- byte-identical commit/push/PR flow. On a gh-stack layer: commit proceeds normally, pull/merge-from-destination is skipped, and push/PR creation is refused with the new `STACK.USE_GH_STACK` error, deferring to `gh stack submit --auto` via the managing-gh-stacks skill.
- `create_pr.py` (and the `create-pr` agent) standalone flow gets the same two gates: unconditional toolchain prerequisite, then stack-layer refusal -- a stack layer's PR base and linkage may only be set by `gh stack submit --auto`.
- Added `packages/sc-commit-push-pr/scripts/stack_guard.py` with the detection/prerequisite primitives (deliberately duplicated from `sc-git-worktree`'s equivalents rather than imported, per package-isolation convention).
- Declared `dependencies: sc-gh-stack >= 0.2.0` in the manifest.

## [0.10.0] - 2026-04-18

- Version alignment with Synaptic Canvas 0.10.0 release

## [0.9.0] - 2026-01-20

- Initial release: commit, push, and PR creation skill for GitHub and Azure DevOps
- `commit-push` agent for staging, committing, and pushing changes
- `create-pr` agent for opening pull requests with structured descriptions
