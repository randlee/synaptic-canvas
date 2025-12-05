#!/usr/bin/env bash
set -euo pipefail

SRC="${1:-}" # file path or URL
if [[ -z "$SRC" ]]; then
  echo "Usage: validate-registry.sh <file-or-url>" >&2
  exit 2
fi

TMP=""
cleanup(){ [[ -n "$TMP" && -f "$TMP" ]] && rm -f "$TMP"; }
trap cleanup EXIT

if [[ "$SRC" =~ ^https?:// ]]; then
  TMP=$(mktemp)
  if ! curl -fsSL "$SRC" -o "$TMP"; then
    echo "ERROR: failed to fetch $SRC" >&2
    exit 1
  fi
  SRC="$TMP"
fi

if command -v jq >/dev/null 2>&1; then
  if ! jq -e '.packages and (.|type=="object")' "$SRC" >/dev/null; then
    echo "ERROR: invalid registry structure (missing .packages)" >&2
    exit 1
  fi
  echo "OK: registry validated"
else
  echo "WARN: jq not installed; skipping structural validation" >&2
  echo "OK: registry loaded"
fi
