#!/usr/bin/env python3
import sys
from pathlib import Path

# Add repo src to sys.path so 'sc_cli' can be imported without installation when running in-repo
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from sc_cli.delay_run import main

if __name__ == "__main__":
    raise SystemExit(main())
