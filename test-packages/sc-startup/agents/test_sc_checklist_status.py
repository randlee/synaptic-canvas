import importlib.util
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _init_git(repo_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)


def test_missing_checklist(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git(repo_root)
    module = _load_module(
        "sc_checklist_status",
        REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_checklist_status.py",
    )
    result = module.run({"repo_root": str(repo_root), "checklist_path": "pm/checklist.md"})
    assert result["success"] is False
    assert result["error"]["code"] == "VALIDATION.MISSING_CHECKLIST"


def test_update_adds_missing_items(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git(repo_root)
    (repo_root / "pm").mkdir()
    checklist = repo_root / "pm" / "checklist.md"
    checklist.write_text("- [ ] existing item\n", encoding="utf-8")
    src_dir = repo_root / "src"
    src_dir.mkdir()
    target = src_dir / "main.txt"
    target.write_text("TODO: add coverage\n", encoding="utf-8")
    subprocess.run(["git", "add", str(target)], cwd=repo_root, check=True, capture_output=True)
    module = _load_module(
        "sc_checklist_status",
        REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_checklist_status.py",
    )
    result = module.run({"repo_root": str(repo_root), "checklist_path": "pm/checklist.md", "mode": "update"})
    assert result["success"] is True
    assert result["data"]["added"]
    updated = checklist.read_text(encoding="utf-8")
    assert "TODO src/main.txt" in updated


def test_report_only_does_not_modify(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git(repo_root)
    (repo_root / "pm").mkdir()
    checklist = repo_root / "pm" / "checklist.md"
    checklist.write_text("- [ ] existing item\n", encoding="utf-8")
    src_dir = repo_root / "src"
    src_dir.mkdir()
    target = src_dir / "main.txt"
    target.write_text("FIXME: update docs\n", encoding="utf-8")
    subprocess.run(["git", "add", str(target)], cwd=repo_root, check=True, capture_output=True)
    module = _load_module(
        "sc_checklist_status",
        REPO_ROOT / "packages" / "sc-startup" / "agents" / "sc_checklist_status.py",
    )
    result = module.run({"repo_root": str(repo_root), "checklist_path": "pm/checklist.md", "mode": "report"})
    assert result["success"] is True
    assert result["data"]["added"] == []
    after = checklist.read_text(encoding="utf-8")
    assert after.strip() == "- [ ] existing item"
