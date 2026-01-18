#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$ROOT_DIR/reports"
: > "$ROOT_DIR/reports/trace.jsonl"

echo "Bootstrap complete. Set CLAUDE_CLI_PATH and ANTHROPIC_API_KEY before running integration tests."
