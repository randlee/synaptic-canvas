from __future__ import annotations

import subprocess

import pytest


def require_yaml(clean_env: dict) -> None:
    check = subprocess.run(
        ["python3", "-c", "import yaml"],
        capture_output=True,
        text=True,
        env=clean_env,
    )
    if check.returncode != 0:
        pytest.skip("PyYAML not available without user site-packages")
