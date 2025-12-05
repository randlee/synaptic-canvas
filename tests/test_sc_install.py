from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sc_cli import sc_install

def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "a@b"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "a"], check=True)


def test_list_and_info(capsys):
    assert sc_install.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "delay-tasks" in out
    assert "sc-git-worktree" in out

    assert sc_install.main(["info", "sc-git-worktree"]) == 0
    out = capsys.readouterr().out
    assert "Package: sc-git-worktree" in out
    assert "name: sc-git-worktree" in out  # manifest content printed


def test_install_and_uninstall_delay_tasks(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    dest = repo / ".claude"

    # Install
    rc = sc_install.main(["install", "delay-tasks", "--dest", str(dest)])
    assert rc == 0
    # Files exist
    assert (dest / "agents/delay-once.md").exists()
    py = dest / "scripts/delay-run.py"
    assert py.exists()
    # Executable bit set (at least for user)
    assert os.access(py, os.X_OK)

    # Uninstall
    rc = sc_install.main(["uninstall", "delay-tasks", "--dest", str(dest)])
    assert rc == 0
    assert not (dest / "agents/delay-once.md").exists()


def test_token_expansion_repo_name(tmp_path: Path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    _init_git_repo(repo)
    dest = repo / ".claude"
    rc = sc_install.main(["install", "sc-git-worktree", "--dest", str(dest)])
    assert rc == 0
    f = dest / "commands/sc-git-worktree.md"
    assert f.exists()
    content = f.read_text(encoding="utf-8")
    assert f"../{repo.name}-worktrees" in content
