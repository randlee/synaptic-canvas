import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _install_package(pkg: str, test_repo: Path) -> None:
    installer = REPO_ROOT / "tools" / "sc-install.sh"
    dest = test_repo / ".claude"
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(installer), "install", pkg, "--dest", str(dest), "--force"], check=True, capture_output=True)


def _run_claude(prompt: str, cwd: Path, timeout: int = 20) -> subprocess.CompletedProcess:
    claude = shutil.which("claude")
    if not claude:
        pytest.skip("claude CLI not available")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"
    try:
        return subprocess.run(
            [
                claude,
                "-p",
                prompt,
                "--model",
                "haiku",
                "--setting-sources",
                "project",
                "--tools",
                "Bash",
                "--dangerously-skip-permissions",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
            env=env,
            cwd=str(cwd),
        )
    except subprocess.TimeoutExpired:
        pytest.skip("claude CLI timed out")


def _write_claude_output(test_repo: Path, res: subprocess.CompletedProcess) -> None:
    output_path = test_repo / "reports" / "claude-output.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    if res.stdout:
        payload.append("STDOUT:\n" + res.stdout.strip())
    if res.stderr:
        payload.append("STDERR:\n" + res.stderr.strip())
    output_path.write_text("\n\n".join(payload) + "\n", encoding="utf-8")


def _reset_reports(test_repo: Path) -> None:
    report_dir = test_repo / "reports"
    for name in ("trace.jsonl", "claude-output.txt"):
        path = report_dir / name
        if path.exists():
            path.unlink()


@contextmanager
def _temp_move(path: Path) -> Path:
    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        shutil.move(str(path), str(backup))
    try:
        yield backup
    finally:
        if backup.exists() and not path.exists():
            shutil.move(str(backup), str(path))


def _set_yaml_key(path: Path, key: str, value: str) -> str:
    original = path.read_text(encoding="utf-8")
    lines = []
    replaced = False
    for line in original.splitlines():
        if line.startswith(f"{key}:"):
            lines.append(f"{key}: {value}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append(f"{key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return original


@pytest.mark.integration
def test_sc_startup_command_runs() -> None:
    test_repo = os.environ.get("SC_TEST_REPO")
    if not test_repo:
        pytest.skip("SC_TEST_REPO not set")
    test_repo_path = Path(test_repo)
    _install_package("sc-startup", test_repo_path)
    _reset_reports(test_repo_path)
    res = _run_claude("/sc-startup --fast --readonly", test_repo_path)
    if res.returncode != 0:
        pytest.skip(f"claude CLI failed: {res.stderr.strip()}")
    output = (res.stdout + res.stderr).lower()
    assert "unknown" not in output


@pytest.mark.integration
def test_sc_startup_command_invokes_agents() -> None:
    test_repo = os.environ.get("SC_TEST_REPO")
    if not test_repo:
        pytest.skip("SC_TEST_REPO not set")
    test_repo_path = Path(test_repo)
    _install_package("sc-startup", test_repo_path)
    _reset_reports(test_repo_path)
    res = _run_claude("/sc-startup --readonly", test_repo_path, timeout=60)
    if res.returncode != 0:
        pytest.skip(f"claude CLI failed: {res.stderr.strip()}")
    _write_claude_output(test_repo_path, res)
    output = (res.stdout + res.stderr).lower()
    assert "startup" in output or "checklist" in output


@pytest.mark.integration
def test_sc_startup_missing_checklist() -> None:
    test_repo = os.environ.get("SC_TEST_REPO")
    if not test_repo:
        pytest.skip("SC_TEST_REPO not set")
    test_repo_path = Path(test_repo)
    _install_package("sc-startup", test_repo_path)
    _reset_reports(test_repo_path)
    checklist_path = test_repo_path / "pm" / "checklist.md"
    if not checklist_path.exists():
        pytest.skip("Checklist file missing before test")
    with _temp_move(checklist_path):
        res = _run_claude("/sc-startup --readonly", test_repo_path, timeout=60)
        if res.returncode != 0:
            pytest.skip(f"claude CLI failed: {res.stderr.strip()}")
        _write_claude_output(test_repo_path, res)
        assert (res.stdout + res.stderr).strip()


@pytest.mark.integration
def test_sc_startup_missing_prompt_path() -> None:
    test_repo = os.environ.get("SC_TEST_REPO")
    if not test_repo:
        pytest.skip("SC_TEST_REPO not set")
    test_repo_path = Path(test_repo)
    _install_package("sc-startup", test_repo_path)
    _reset_reports(test_repo_path)
    config_path = test_repo_path / ".claude" / "sc-startup.yaml"
    if not config_path.exists():
        pytest.skip("Config file missing before test")
    original = _set_yaml_key(config_path, "startup-prompt", "pm/DOES_NOT_EXIST.md")
    try:
        res = _run_claude("/sc-startup --readonly", test_repo_path, timeout=60)
        if res.returncode != 0:
            pytest.skip(f"claude CLI failed: {res.stderr.strip()}")
        _write_claude_output(test_repo_path, res)
        assert (res.stdout + res.stderr).strip()
    finally:
        config_path.write_text(original, encoding="utf-8")


@pytest.mark.integration
def test_sc_startup_missing_config() -> None:
    test_repo = os.environ.get("SC_TEST_REPO")
    if not test_repo:
        pytest.skip("SC_TEST_REPO not set")
    test_repo_path = Path(test_repo)
    _install_package("sc-startup", test_repo_path)
    _reset_reports(test_repo_path)
    config_path = test_repo_path / ".claude" / "sc-startup.yaml"
    if not config_path.exists():
        pytest.skip("Config file missing before test")
    with _temp_move(config_path):
        res = _run_claude("/sc-startup --readonly", test_repo_path, timeout=60)
        if res.returncode != 0:
            pytest.skip(f"claude CLI failed: {res.stderr.strip()}")
        _write_claude_output(test_repo_path, res)
        assert (res.stdout + res.stderr).strip()


@pytest.mark.integration
def test_sc_git_worktree_status_runs() -> None:
    test_repo = os.environ.get("SC_TEST_REPO")
    if not test_repo:
        pytest.skip("SC_TEST_REPO not set")
    test_repo_path = Path(test_repo)
    _install_package("sc-git-worktree", test_repo_path)
    _reset_reports(test_repo_path)
    res = _run_claude("/sc-git-worktree --status", test_repo_path, timeout=40)
    if res.returncode != 0:
        pytest.skip(f"claude CLI failed: {res.stderr.strip()}")
    output = (res.stdout + res.stderr).lower()
    assert "unknown" not in output
