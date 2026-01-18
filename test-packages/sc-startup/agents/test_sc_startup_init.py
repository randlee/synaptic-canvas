import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_invalid_repo(tmp_path: Path) -> None:
    module = _load_module("sc_startup_init", REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_startup_init.py")
    result = module.run({"repo_root": str(tmp_path / "missing")})
    assert result["success"] is False
    assert result["error"]["code"] == "VALIDATION.INVALID_REPO"


def test_missing_config_returns_data(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pm").mkdir()
    (repo_root / "pm" / "ARCH-SC.md").write_text("# Prompt\n", encoding="utf-8")
    module = _load_module("sc_startup_init", REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_startup_init.py")
    result = module.run({"repo_root": str(repo_root), "detect_plugins": False})
    assert result["success"] is False
    assert result["error"]["code"] == "VALIDATION.MISSING_CONFIG"
    assert result["data"]["candidates"]["startup_prompt"]


def test_config_and_candidates(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pm").mkdir()
    (repo_root / "pm" / "ARCH-SC.md").write_text("# Prompt\n", encoding="utf-8")
    (repo_root / "pm" / "checklist.md").write_text("- [ ] item\n", encoding="utf-8")
    (repo_root / ".claude").mkdir()
    (repo_root / ".claude" / "sc-startup.yaml").write_text(
        "startup-prompt: pm/ARCH-SC.md\ncheck-list: pm/checklist.md\npr-enabled: true\n",
        encoding="utf-8",
    )
    module = _load_module("sc_startup_init", REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_startup_init.py")
    result = module.run({"repo_root": str(repo_root), "detect_plugins": False})
    assert result["success"] is True
    data = result["data"]
    assert data["config_found"] is True
    assert data["config"]["startup-prompt"] == "pm/ARCH-SC.md"
    assert "worktree-scan" in data["missing_keys"]
    assert "startup_prompt" in data["candidates"]


def test_plugin_detection(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".claude").mkdir()
    (repo_root / ".claude" / "sc-startup.yaml").write_text("startup-prompt: pm/a.md\ncheck-list: pm/b.md\n", encoding="utf-8")
    (repo_root / ".claude-plugin").mkdir()
    marketplace = {
        "plugins": [
            {"name": "sc-startup", "version": "0.7.0"},
            {"name": "sc-git-worktree", "version": "0.7.0"},
        ]
    }
    (repo_root / ".claude-plugin" / "marketplace.json").write_text(json.dumps(marketplace), encoding="utf-8")
    module = _load_module("sc_startup_init", REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_startup_init.py")
    result = module.run({"repo_root": str(repo_root), "detect_plugins": True})
    assert result["success"] is True
    assert result["data"]["plugins"]["sc-startup"]["installed"] is True
