#!/usr/bin/env python3
import sys
from pathlib import Path

# Add repo root to sys.path so 'scpy' can be imported without installation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scpy.sc_install import main

if __name__ == "__main__":
    raise SystemExit(main())
