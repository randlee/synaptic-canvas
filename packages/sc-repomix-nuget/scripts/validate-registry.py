#!/usr/bin/env python3
"""
Validate registry file structure.

Usage:
    python3 validate-registry.py <file-or-url>
"""

import json
import sys
import tempfile
import urllib.request
from pathlib import Path


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate-registry.py <file-or-url>", file=sys.stderr)
        return 2

    src = sys.argv[1]
    temp_file = None

    try:
        # Handle URL
        if src.startswith("http://") or src.startswith("https://"):
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as f:
                    temp_file = f.name
                    with urllib.request.urlopen(src) as response:
                        content = response.read().decode("utf-8")
                        f.write(content)
                src = temp_file
            except Exception as e:
                print(f"ERROR: failed to fetch {src}: {e}", file=sys.stderr)
                return 1

        # Validate JSON structure
        src_path = Path(src)
        if not src_path.exists():
            print(f"ERROR: file not found: {src}", file=sys.stderr)
            return 1

        try:
            with open(src_path) as f:
                data = json.load(f)

            if not isinstance(data, dict):
                print(
                    "ERROR: invalid registry structure (not an object)",
                    file=sys.stderr,
                )
                return 1

            if "packages" not in data:
                print(
                    "ERROR: invalid registry structure (missing .packages)",
                    file=sys.stderr,
                )
                return 1

            print("OK: registry validated")
            return 0

        except json.JSONDecodeError as e:
            print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
            return 1

    finally:
        # Cleanup temp file
        if temp_file:
            try:
                Path(temp_file).unlink()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
