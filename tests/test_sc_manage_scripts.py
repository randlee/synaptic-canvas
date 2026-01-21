import io
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "packages" / "sc-manage" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sc_manage_docs
import sc_manage_install
import sc_manage_list
import sc_manage_uninstall


def _write_manifest(path: Path, name: str, description: str, scope: str = "both") -> None:
    path.write_text(
        "\n".join(
            [
                f"name: {name}",
                f"description: {description}",
                "install:",
                f"  scope: {scope}",
                "artifacts:",
                "  commands:",
                "    - commands/example.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_list_packages_detects_scopes_and_installs(tmp_path, monkeypatch, capsys):
    repo_root = tmp_path / "repo"
    packages_dir = repo_root / "packages"
    pkg_a = packages_dir / "sc-alpha"
    pkg_b = packages_dir / "sc-beta"
    pkg_a.mkdir(parents=True)
    pkg_b.mkdir(parents=True)
    _write_manifest(pkg_a / "manifest.yaml", "sc-alpha", "Alpha package")
    _write_manifest(pkg_b / "manifest.yaml", "sc-beta", "Beta package")

    local_claude = repo_root / ".claude" / "commands"
    local_claude.mkdir(parents=True)
    (local_claude / "example.md").write_text("local", encoding="utf-8")

    global_claude = tmp_path / "global" / "commands"
    global_claude.mkdir(parents=True)
    (global_claude / "example.md").write_text("global", encoding="utf-8")

    monkeypatch.setattr(sc_manage_list, "resolve_repo_root", lambda: repo_root)

    payload = {
        "sc_repo_path": str(repo_root),
        "global_claude_dir": str(global_claude.parent),
    }

    stdin_backup = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        assert sc_manage_list.main() == 0
    finally:
        sys.stdin = stdin_backup

    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["success"] is True
    packages = {p["name"]: p for p in data["data"]["packages"]}
    assert packages["sc-alpha"]["installed"] in {"local", "both"}
    assert packages["sc-beta"]["installed"] in {"local", "both"}


def test_install_blocks_global_for_local_only(tmp_path, monkeypatch, capsys):
    repo_root = tmp_path / "repo"
    pkg_dir = repo_root / "packages" / "sc-local"
    pkg_dir.mkdir(parents=True)
    _write_manifest(pkg_dir / "manifest.yaml", "sc-local", "Local only", scope="local-only")

    payload = {
        "package": "sc-local",
        "scope": "global",
        "sc_repo_path": str(repo_root),
        "global_claude_dir": str(tmp_path / "global"),
    }

    stdin_backup = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        assert sc_manage_install.main() == 1
    finally:
        sys.stdin = stdin_backup

    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["success"] is False
    assert data["error"]["code"] == "SCOPE_NOT_ALLOWED"


def test_install_success_runs_installer(tmp_path, monkeypatch, capsys):
    repo_root = tmp_path / "repo"
    pkg_dir = repo_root / "packages" / "sc-install"
    pkg_dir.mkdir(parents=True)
    _write_manifest(pkg_dir / "manifest.yaml", "sc-install", "Install package")

    monkeypatch.setattr(sc_manage_install, "run_install", lambda *_: (0, "ok", ""))
    monkeypatch.setattr(sc_manage_install, "resolve_dest", lambda *_: (tmp_path / "dest", None))

    payload = {
        "package": "sc-install",
        "scope": "local",
        "sc_repo_path": str(repo_root),
        "global_claude_dir": str(tmp_path / "global"),
    }

    stdin_backup = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        assert sc_manage_install.main() == 0
    finally:
        sys.stdin = stdin_backup

    data = json.loads(capsys.readouterr().out)
    assert data["success"] is True
    assert data["data"]["package"] == "sc-install"


def test_uninstall_success_runs_uninstaller(tmp_path, monkeypatch, capsys):
    repo_root = tmp_path / "repo"
    pkg_dir = repo_root / "packages" / "sc-remove"
    pkg_dir.mkdir(parents=True)
    _write_manifest(pkg_dir / "manifest.yaml", "sc-remove", "Remove package")

    monkeypatch.setattr(sc_manage_uninstall, "run_uninstall", lambda *_: (0, "ok", ""))
    monkeypatch.setattr(sc_manage_uninstall, "resolve_dest", lambda *_: (tmp_path / "dest", None))

    payload = {
        "package": "sc-remove",
        "scope": "local",
        "sc_repo_path": str(repo_root),
        "global_claude_dir": str(tmp_path / "global"),
    }

    stdin_backup = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        assert sc_manage_uninstall.main() == 0
    finally:
        sys.stdin = stdin_backup

    data = json.loads(capsys.readouterr().out)
    assert data["success"] is True
    assert data["data"]["package"] == "sc-remove"


def test_docs_returns_readme_path(tmp_path, capsys):
    repo_root = tmp_path / "repo"
    pkg_dir = repo_root / "packages" / "sc-docs"
    pkg_dir.mkdir(parents=True)
    _write_manifest(pkg_dir / "manifest.yaml", "sc-docs", "Docs package")
    readme = pkg_dir / "README.md"
    readme.write_text("# Docs", encoding="utf-8")

    payload = {"package": "sc-docs", "sc_repo_path": str(repo_root)}

    stdin_backup = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        assert sc_manage_docs.main() == 0
    finally:
        sys.stdin = stdin_backup

    data = json.loads(capsys.readouterr().out)
    assert data["success"] is True
    assert data["data"]["readme_path"] == str(readme)


def _extract_json_blocks(text: str) -> list[dict]:
    blocks = []
    marker = "```json"
    idx = 0
    while True:
        start = text.find(marker, idx)
        if start == -1:
            break
        end = text.find("```", start + len(marker))
        if end == -1:
            break
        content = text[start + len(marker) : end].strip()
        blocks.append(json.loads(content))
        idx = end + 3
    return blocks


def test_agent_markdown_json_examples_are_valid():
    agent_files = [
        REPO_ROOT / "packages" / "sc-manage" / "agents" / "sc-packages-list.md",
        REPO_ROOT / "packages" / "sc-manage" / "agents" / "sc-package-install.md",
        REPO_ROOT / "packages" / "sc-manage" / "agents" / "sc-package-uninstall.md",
        REPO_ROOT / "packages" / "sc-manage" / "agents" / "sc-package-docs.md",
    ]

    for path in agent_files:
        blocks = _extract_json_blocks(path.read_text(encoding="utf-8"))
        assert blocks, f"No JSON blocks found in {path}"
        for block in blocks:
            assert "success" in block
            assert "data" in block
            assert "error" in block

    docs_blocks = _extract_json_blocks(agent_files[-1].read_text(encoding="utf-8"))
    error_blocks = [b for b in docs_blocks if b.get("success") is False]
    assert error_blocks
    assert error_blocks[0]["error"]["code"] == "README_NOT_FOUND"
