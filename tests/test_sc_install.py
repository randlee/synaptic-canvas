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
    assert "sc-delay-tasks" in out
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
    rc = sc_install.main(["install", "sc-delay-tasks", "--dest", str(dest)])
    assert rc == 0
    # Files exist
    assert (dest / "agents/sc-delay-once.md").exists()
    py = dest / "scripts/sc-delay-run.py"
    assert py.exists()
    # Executable bit set (at least for user)
    assert os.access(py, os.X_OK)

    # Uninstall
    rc = sc_install.main(["uninstall", "sc-delay-tasks", "--dest", str(dest)])
    assert rc == 0
    assert not (dest / "agents/sc-delay-once.md").exists()


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


def test_install_sc_ai_cli_copies_template_assets(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    dest = repo / ".claude"

    rc = sc_install.main(["install", "sc-ai-cli", "--dest", str(dest)])
    assert rc == 0

    assert (dest / "skills/creating-ai-clis/SKILL.md").exists()
    assert (dest / "skills/creating-ai-clis/assets/templates/rust/Cargo.toml.j2").exists()
    assert (dest / "skills/designing-cli-simulators/assets/templates/go/simulator.go.j2").exists()


def test_install_sc_docling_pdf_copies_skill_and_references(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    dest = repo / ".claude"

    rc = sc_install.main(["install", "sc-docling-pdf", "--dest", str(dest)])
    assert rc == 0

    skill_dir = dest / "skills/docling-pdf-extraction"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "references/installation.md").exists()
    assert (skill_dir / "references/profile-rich.md").exists()
    assert (skill_dir / "references/profile-scan.md").exists()
    assert (skill_dir / "references/profile-vlm.md").exists()
