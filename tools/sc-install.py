#!/usr/bin/env python3
import sys
from pathlib import Path

# Add repo src to sys.path so 'sc_cli' can be imported without installation
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from sc_cli.install import main

if __name__ == "__main__":
    raise SystemExit(main())
