# Changelog

All notable changes to the **sc-rust** package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.10.0] - Unreleased

### Added
- New `rust-service-hardening` skill for production-readiness guidance and review of Rust services
- Prioritized service-hardening checklist in `skills/rust-service-hardening/references/production-checklist.md`
- Shared framework notes for Tokio, Axum/Hyper, Tonic, and Reqwest in `skills/rust-service-hardening/references/framework-notes.md`

### Changed
- Expanded `sc-rust` package metadata and marketplace/plugin descriptions to include service-hardening scope
- Updated `README.md` and `USE-CASES.md` to advertise when `rust-service-hardening` should be selected
- Bumped `sc-rust` package and bundled artifact versions from `0.9.0` to `0.10.0`

### Scope
- `rust-service-hardening` is intended for Rust services with runtime, network, or deployment concerns
- Explicitly excludes non-service crates, embedded Rust, pure sync CLI tools, and low-level libraries without runtime/network/server concerns

## [0.9.0] - 2026-03-30

### Added
- `rust-development` skill with Pragmatic Rust Guidelines and cross-platform portability rules
- `rust-best-practices` skill with design pattern enforcement (Error Context, Typestate, Sealed Traits, Newtype, Cow, Interior Mutability, Infallible, Trait Object Safety)
- Five agents: `rust-architect`, `rust-code-reviewer`, `rust-code-explorer`, `rust-developer`, `rust-qa-agent`
- `cross-platform-guidelines.md` bundled in `rust-development` skill for self-contained installation

### Changed
- `rust-qa-agent`: removed `WebSearch` and `WebFetch` tools because QA workflows do not need network research
