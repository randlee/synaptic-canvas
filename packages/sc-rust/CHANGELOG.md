# Changelog

All notable changes to the **sc-rust** package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.14.0] - 2026-10-26

### Fixed
- The three quality-mgr assignment templates render again. They quoted each variable (`"{{ worktree_path }}"`) inside a `format: json` template, where sc-compose already emits every variable as a JSON value, so sc-compose 1.7.0 refused all three with `ERR_RENDER_JSON_MALFORMED`. Variables are now emitted unquoted.

### Added
- Fix-round scope lock for the subjective reviewers. `rust-best-practices-agent` and `rust-service-hardening-agent` accept `carry_forward_findings` and `findings_scope_locked`; a locked dispatch reports fixed, open or regressed for the carried ids only and puts any new observation in `notes`, so QA converges instead of trading each fixed finding for a new one.
- Their assignment templates take a required `qa_round` and an optional `carry_forward_findings_json`. Above round 1 the render fails unless that reviewer's own carried ids are supplied.

### Changed
- `quality-mgr.rust.md` separates Sprint QA from Fix QA: a fix round dispatches only the reviewer that filed the finding, and the subjective reviewers run on a fix round only with an assigned finding of their own category (`RBP-*`, `RSH-*`). The examples pass `qa_round`.

## [Unreleased]

### Added
- canonical `rust-best-practices` practice inventory with stable practice ids
- dedicated per-pattern references for newtype/zero-cost, deref coercion, interior mutability, infallible usage, trait object safety, `Cow`, and `PhantomData`
- dedicated `rust-best-practices-agent` for structural pattern review
- dedicated `rust-service-hardening-agent` for runtime/service-hardening review
- `quality-mgr.rust.md` supplement plus `sc-compose` assignment templates for Rust reviewer orchestration

### Changed
- `rust-qa-agent` narrowed back to tests, clippy, coverage, portability, artifact checks, and first-principles QA
- `rust-architect`, `rust-code-reviewer`, and `rust-developer` updated to use the canonical service-hardening checklist references when applicable

## [0.10.0] - 2026-04-18

### Added
- New `rust-service-hardening` skill for production-readiness guidance and review of Rust services
- Prioritized service-hardening checklist in `skills/rust-service-hardening/references/production-checklist.md`
- Shared framework notes for Tokio, Axum/Hyper, Tonic, and Reqwest in `skills/rust-service-hardening/references/framework-notes.md`

### Changed
- Expanded `sc-rust` package metadata and marketplace/plugin descriptions to include service-hardening scope
- Updated `README.md` and `USE-CASES.md` to advertise when `rust-service-hardening` should be selected
- Bumped `sc-rust` package and bundled artifact versions to `0.10.0`

### Scope
- `rust-service-hardening` is intended for Rust services with runtime, network, or deployment concerns
- Explicitly excludes non-service crates, embedded Rust, pure sync CLI tools, and low-level libraries without runtime/network/server concerns

## [0.9.0] - 2026-03-30

### Added
- `rust-development` skill with Pragmatic Rust Guidelines and cross-platform portability rules
- `rust-best-practices` skill expanded into a canonical structural-pattern inventory with stable practice ids and stage-based enforcement guidance
- `rust-service-hardening` skill for Tokio and other Rust service/runtime production defaults
- Five agents: `rust-architect`, `rust-code-reviewer`, `rust-code-explorer`, `rust-developer`, `rust-qa-agent`
- `cross-platform-guidelines.md` bundled in `rust-development` skill for self-contained installation

### Changed
- `rust-qa-agent`: removed `WebSearch` and `WebFetch` tools because QA workflows do not need network research
