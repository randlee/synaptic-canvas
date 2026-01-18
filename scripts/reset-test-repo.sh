#!/usr/bin/env bash
set -euo pipefail

echo "Resetting test repo..."

git reset --hard
git clean -fdx

mkdir -p reports
: > reports/trace.jsonl

echo "Reset complete."
