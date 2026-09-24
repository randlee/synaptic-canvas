from pathlib import Path

from sc_cli import install as sc_install
from sc_cli import skill_integration


def test_resolve_install_scope_supports_user_and_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sc_install.Path, "home", lambda: tmp_path / "home")

    assert sc_install._resolve_install_scope(local_flag=True) == tmp_path
    assert sc_install._resolve_install_scope(project_flag=True) == tmp_path
    assert sc_install._resolve_install_scope(global_flag=True) == tmp_path / "home"
    assert sc_install._resolve_install_scope(user_flag=True) == tmp_path / "home"


def test_install_marketplace_scope_aliases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(skill_integration.Path, "home", lambda: tmp_path / "home")

    calls = []

    def fake_cmd_install(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(skill_integration, "cmd_install", fake_cmd_install)

    result = skill_integration.install_marketplace_package("sc-delay-tasks", scope="project")
    assert result["status"] == "success"
    assert calls[-1]["local_flag"] is True
    assert calls[-1]["project_flag"] is True
    assert str(tmp_path / ".claude") in result["message"]

    result = skill_integration.install_marketplace_package("sc-delay-tasks", scope="user")
    assert result["status"] == "success"
    assert calls[-1]["global_flag"] is True
    assert calls[-1]["user_flag"] is True
    assert str(tmp_path / "home" / ".claude") in result["message"]
