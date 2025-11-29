import sys
from pathlib import Path

# Ensure src/ is importable for 'sc_cli'
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
