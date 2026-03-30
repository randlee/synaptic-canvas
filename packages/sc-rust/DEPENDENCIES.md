# Dependencies

## Required CLI Tools

| Tool | Min Version | Purpose |
|------|-------------|---------|
| `cargo` | 1.87 | Build, test, and lint Rust projects |
| `cargo-llvm-cov` | any | Coverage analysis in `rust-qa-agent` |

### Installing cargo-llvm-cov

```bash
cargo install cargo-llvm-cov
```

## Optional

| Tool | Purpose |
|------|---------|
| `rustup` | Manage Rust toolchain versions |

## No Python Dependencies

This package has no Python script dependencies. All agents are prompt-only.

## No sc-* Package Dependencies

This package has no runtime dependencies on other Synaptic Canvas packages.
