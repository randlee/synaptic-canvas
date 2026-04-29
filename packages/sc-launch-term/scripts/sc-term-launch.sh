#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/sc-term-launch.py"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$PYTHON_SCRIPT" "$@"
fi

if command -v py >/dev/null 2>&1; then
  exec py -3 "$PYTHON_SCRIPT" "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$PYTHON_SCRIPT" "$@"
fi

echo "No supported Python 3 launcher found on PATH. Tried: python3, py -3, python" >&2
exit 127
