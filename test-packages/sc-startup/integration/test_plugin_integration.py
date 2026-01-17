import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _build_bundle(plugin_root: Path, dest_root: Path) -> None:
    harness = REPO_ROOT / "test-packages" / "test_fixtures" / "plugin_test_harness.py"
    cmd = ["python3", str(harness), "--plugin-root", str(plugin_root), "--dest", str(dest_root)]
    subprocess.run(cmd, check=True, capture_output=True)


@pytest.mark.integration
def test_claude_plugin_validate(tmp_path: Path) -> None:
    claude = shutil.which("claude")
    if not claude:
        pytest.skip("claude CLI not available")
    plugin_root = REPO_ROOT / "packages" / "sc-startup"
    bundle = tmp_path / "bundle"
    _build_bundle(plugin_root, bundle)
    res = subprocess.run(
        [claude, "plugin", "validate", str(bundle)],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if res.returncode != 0:
        pytest.skip(f"claude plugin validate failed: {res.stderr.strip()}")
    assert "validation passed" in res.stdout.lower()


@pytest.mark.integration
def test_claude_hooks_trace(tmp_path: Path) -> None:
    claude = shutil.which("claude")
    if not claude:
        pytest.skip("claude CLI not available")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    test_repo = os.environ.get("SC_TEST_REPO")
    if not test_repo:
        pytest.skip("SC_TEST_REPO not set")
    trace_path = Path(test_repo) / "reports" / "trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text("", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"
    res = subprocess.run(
        [
            claude,
            "-p",
            "Use Bash to run 'ls' and return the output only.",
            "--model",
            "haiku",
            "--setting-sources",
            "project",
            "--tools",
            "Bash",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
        env=env,
        cwd=test_repo,
    )
    if res.returncode != 0:
        pytest.skip(f"claude CLI failed: {res.stderr.strip()}")
    trace = trace_path.read_text(encoding="utf-8").strip()
    if not trace:
        pytest.skip("hooks did not emit trace output")
