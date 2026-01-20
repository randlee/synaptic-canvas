#!/usr/bin/env python3
"""
Generate repomix output for NuGet packages.

Usage:
    python3 generate.py [--package-path PATH] [--output FILE] [--no-compress]
                        [--include GLOB ...] [--ignore GLOB ...]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate repomix output for NuGet packages"
    )
    parser.add_argument(
        "--package-path",
        type=Path,
        default=Path("."),
        help="Path to the package directory (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./repomix-output.xml"),
        help="Output file path (default: ./repomix-output.xml)",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Disable compression",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Include patterns (can be specified multiple times)",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Ignore patterns (can be specified multiple times)",
    )

    args = parser.parse_args()

    # Default patterns
    include_patterns = args.include if args.include else ["**/*.cs"]
    ignore_patterns = args.ignore if args.ignore else [
        "**/obj/**",
        "**/bin/**",
        "**/*.Tests.cs",
    ]

    # Validate package path
    if not args.package_path.is_dir():
        print(f"Package path not found: {args.package_path}", file=sys.stderr)
        return 1

    # Build command
    cmd = [
        "npx",
        "-y",
        "repomix",
        "--style",
        "xml",
        "--output",
        str(args.output),
        "--remove-empty-lines",
    ]

    if not args.no_compress:
        cmd.append("--compress")

    for pat in include_patterns:
        cmd.extend(["--include", pat])

    for pat in ignore_patterns:
        cmd.extend(["--ignore", pat])

    # Run command from package directory
    try:
        result = subprocess.run(
            cmd,
            cwd=args.package_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"repomix failed: {result.stderr}", file=sys.stderr)
            return 1
    except FileNotFoundError:
        print("npx not found - ensure Node.js is installed", file=sys.stderr)
        return 1

    # Check output size (max ~500KB)
    output_path = args.package_path / args.output
    if output_path.exists():
        size = output_path.stat().st_size
        if size > 512000:
            print(f"Output too large ({size} bytes)", file=sys.stderr)
            return 1
        print(f"OK: {args.output} ({size} bytes)")
    else:
        print(f"Output file not created: {args.output}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
