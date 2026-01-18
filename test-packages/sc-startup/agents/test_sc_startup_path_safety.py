import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_init_rejects_escape_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    module = _load_module("sc_startup_init", REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_startup_init.py")
    result = module.run({"repo_root": str(repo_root), "config_path": "../escape.yaml"})
    assert result["success"] is False
    assert result["error"]["code"] == "VALIDATION.INVALID_PATH"


def test_checklist_rejects_escape_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    module = _load_module("sc_checklist_status", REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_checklist_status.py")
    result = module.run({"repo_root": str(repo_root), "checklist_path": "../escape.md"})
    assert result["success"] is False
    assert result["error"]["code"] == "VALIDATION.INVALID_PATH"
