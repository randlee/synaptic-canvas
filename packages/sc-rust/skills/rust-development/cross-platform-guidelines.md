# Cross-Platform Guidelines for Rust Projects

Rules and patterns for ensuring Rust code works correctly on Ubuntu, macOS, and Windows.

## Temporary Files and Directories

**Problem**: `/tmp/` is Unix-only. Windows has no `/tmp/` directory.

**Solution**: Use `std::env::temp_dir()` for temporary paths in production code. Use `tempfile::TempDir` for test isolation.

```rust
// BAD: Unix-only, fails on Windows
let path = PathBuf::from("/tmp/session-id");

// GOOD: cross-platform
let path = std::env::temp_dir().join("session-id");
```

In tests, always use a scoped `TempDir`:

```rust
// BAD: hardcoded /tmp path in test
let path = PathBuf::from("/tmp/test-artifact");

// GOOD: temp-isolated TempDir
let dir = tempfile::tempdir().expect("temp dir");
let path = dir.path().join("test-artifact");
```

### Verification

```bash
grep -rn '"/tmp/' crates/ && echo "FAIL: Found /tmp hardcoding" || echo "OK"
```

## File Paths

- Use `std::path::Path` and `PathBuf` for all file operations — never string concatenation.
- Use `path.join()` for path construction (handles separators cross-platform).
- Never hardcode `/` or `\` as path separators.

## Environment Variables

- Check env vars with `std::env::var()`, not by reading `/proc` or shell config files.
- For test isolation, set env vars per-command with `cmd.env("KEY", "value")` rather than `std::env::set_var()` — the latter is global and causes race conditions in parallel tests.

## Home Directory Resolution

**Problem**: `dirs::home_dir()` on Windows uses the Windows API and ignores `HOME`/`USERPROFILE` environment variables, breaking tests that set `HOME` to a temp directory.

**Solution**: Check a project-specific override env var first before falling back to `dirs::home_dir()`.

**NEVER** use `.env("HOME", ...)` or `.env("USERPROFILE", ...)` in tests — these do not work on Windows.

## Clippy Compliance

CI runs clippy with `-D warnings`. Local toolchains may be older and miss lints.

### Known Strict Lints

- **`collapsible_if`**: Nested `if`/`if let` chains must be collapsed using let chain syntax (stable since Rust 1.87):

```rust
// BAD
if path.is_file() {
    if let Ok(content) = fs::read_to_string(&path) { /* ... */ }
}

// GOOD
if path.is_file()
    && let Ok(content) = fs::read_to_string(&path)
{ /* ... */ }
```

### Pre-Commit Check

```bash
cargo clippy --all-targets --all-features -- -D warnings
```

## Line Endings

- `fs::read_to_string()` returns platform-native line endings.
- When comparing file content in tests, avoid hardcoding `\n`. Use `.contains()` or `.lines()` for line-by-line comparison.
- Use `.gitattributes` to enforce consistent line endings for source files.
