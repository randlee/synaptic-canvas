import sys
from pathlib import Path

# Ensure src/ is importable for 'sc_cli'
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CODEX_SCRIPTS = ROOT / "packages" / "sc-codex" / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(CODEX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CODEX_SCRIPTS))
