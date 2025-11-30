#!/usr/bin/env python3
# Backward-compatible shim: keep import path sc_cli.sc_install
from .install import main

if __name__ == "__main__":
    raise SystemExit(main())
