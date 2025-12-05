#!/usr/bin/env bash
set -euo pipefail

PACKAGE_PATH="."
OUTPUT_PATH="./repomix-output.xml"
COMPRESS="true"
INCLUDE_PATTERNS=("**/*.cs")
IGNORE_PATTERNS=("**/obj/**" "**/bin/**" "**/*.Tests.cs")

usage(){
  cat <<'USAGE'
Usage: generate.sh [--package-path PATH] [--output FILE] [--no-compress] \
                   [--include GLOB ...] [--ignore GLOB ...]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --package-path) PACKAGE_PATH="$2"; shift 2;;
    --output) OUTPUT_PATH="$2"; shift 2;;
    --no-compress) COMPRESS="false"; shift;;
    --include) INCLUDE_PATTERNS+=("$2"); shift 2;;
    --ignore) IGNORE_PATTERNS+=("$2"); shift 2;;
    --help|-h) usage; exit 0;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1;;
  esac
done

if [[ ! -d "$PACKAGE_PATH" ]]; then
  echo "Package path not found: $PACKAGE_PATH" >&2
  exit 1
fi

CMD=(npx -y repomix --style xml --output "$OUTPUT_PATH" --remove-empty-lines)
if [[ "$COMPRESS" == "true" ]]; then
  CMD+=(--compress)
fi
for pat in "${INCLUDE_PATTERNS[@]}"; do CMD+=(--include "$pat"); done
for pat in "${IGNORE_PATTERNS[@]}"; do CMD+=(--ignore "$pat"); done

( cd "$PACKAGE_PATH" && "${CMD[@]}" )

# Basic size cap ~500KB
SIZE=$(stat -f%z "$OUTPUT_PATH" 2>/dev/null || stat -c%s "$OUTPUT_PATH")
if [[ "$SIZE" -gt 512000 ]]; then
  echo "Output too large ($SIZE bytes)" >&2
  exit 1
fi

echo "OK: $OUTPUT_PATH ($SIZE bytes)"
