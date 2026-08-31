"""Tests for scripts/expand-jenga-templates.py.

The script expands Jenga template files (templates/sc-logging.jenga.py,
templates/sc-shared.jenga.py) into a package's scripts/ directory, renaming
{{PACKAGE_NAME}} placeholders and stripping unused {{EXTRA_IMPORTS}} /
{{EXTRA_FIELDS}} comment lines.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "expand-jenga-templates.py"


def _load():
    spec = importlib.util.spec_from_file_location("expand_jenga_templates", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- detect_package_name -----------------------------------------------


def test_detect_package_name_from_packages_dir():
    mod = _load()
    assert mod.detect_package_name(Path("/repo/packages/sc-git-worktree")) == "sc-git-worktree"


def test_detect_package_name_nested_under_packages():
    mod = _load()
    assert mod.detect_package_name(
        Path("/repo/packages/sc-git-worktree/scripts")
    ) == "sc-git-worktree"


def test_detect_package_name_falls_back_to_last_dir_name():
    mod = _load()
    assert mod.detect_package_name(Path("/repo/.claude/scripts")) == "scripts"


# --- expand_template ------------------------------------------------------


def test_expand_template_replaces_package_name_and_writes_file(tmp_path):
    mod = _load()
    template = tmp_path / "sc-logging.jenga.py"
    template.write_text("PKG = '{{PACKAGE_NAME}}'\n")
    target_dir = tmp_path / "out"

    output_path = mod.expand_template(template, target_dir, "sc-git-worktree", "logging")

    assert output_path == target_dir / "sc_git_worktree_logging.py"
    assert output_path.read_text() == "PKG = 'sc-git-worktree'\n"


def test_expand_template_strips_extra_imports_and_fields_comments(tmp_path):
    mod = _load()
    template = tmp_path / "sc-shared.jenga.py"
    template.write_text(
        "import os\n"
        "    # {{EXTRA_IMPORTS}} add more here\n"
        "class LogEntry:\n"
        "    # {{EXTRA_FIELDS}} add more here\n"
        "    pass\n"
    )
    target_dir = tmp_path / "out"

    output_path = mod.expand_template(template, target_dir, "demo", "shared")
    content = output_path.read_text()

    assert "{{EXTRA_IMPORTS}}" not in content
    assert "{{EXTRA_FIELDS}}" not in content
    assert "import os" in content
    assert "class LogEntry" in content


def test_expand_template_creates_target_dir_if_missing(tmp_path):
    mod = _load()
    template = tmp_path / "sc-logging.jenga.py"
    template.write_text("x = 1\n")
    target_dir = tmp_path / "does" / "not" / "exist"

    output_path = mod.expand_template(template, target_dir, "pkg", "logging")

    assert output_path.exists()
    assert target_dir.is_dir()


# --- main() ----------------------------------------------------------------


def _make_repo(tmp_path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "sc-logging.jenga.py").write_text(
        "PKG = '{{PACKAGE_NAME}}'\n"
    )
    (tmp_path / "templates" / "sc-shared.jenga.py").write_text(
        "PKG = '{{PACKAGE_NAME}}'\n"
    )


def test_main_happy_path_expands_single_template(tmp_path, monkeypatch, capsys):
    mod = _load()
    _make_repo(tmp_path)
    fake_script = tmp_path / "scripts" / "expand-jenga-templates.py"
    monkeypatch.setattr(mod, "__file__", str(fake_script))

    target = "packages/demo-pkg"
    (tmp_path / target).mkdir(parents=True)
    monkeypatch.setattr(sys, "argv", [
        "expand-jenga-templates.py", target,
        "--template", "logging",
    ])

    rc = mod.main()

    assert rc == 0
    out = tmp_path / "packages" / "demo-pkg" / "scripts" / "demo_pkg_logging.py"
    assert out.exists()
    assert "demo-pkg" in out.read_text()
    captured = capsys.readouterr()
    assert "Jenga template expansion complete" in captured.out


def test_main_returns_error_when_no_templates_found(tmp_path, monkeypatch, capsys):
    mod = _load()
    (tmp_path / "templates").mkdir()  # empty: no template files present
    fake_script = tmp_path / "scripts" / "expand-jenga-templates.py"
    monkeypatch.setattr(mod, "__file__", str(fake_script))

    target = "packages/demo-pkg"
    (tmp_path / target).mkdir(parents=True)
    monkeypatch.setattr(sys, "argv", ["expand-jenga-templates.py", target])

    rc = mod.main()

    assert rc == 1
    captured = capsys.readouterr()
    assert "No templates expanded" in captured.out


def test_main_uses_explicit_package_name_override(tmp_path, monkeypatch):
    mod = _load()
    _make_repo(tmp_path)
    fake_script = tmp_path / "scripts" / "expand-jenga-templates.py"
    monkeypatch.setattr(mod, "__file__", str(fake_script))

    target = ".claude/scripts"
    (tmp_path / target).mkdir(parents=True)
    monkeypatch.setattr(sys, "argv", [
        "expand-jenga-templates.py", target,
        "--package-name", "hooks",
        "--template", "shared",
    ])

    rc = mod.main()

    assert rc == 0
    out = tmp_path / ".claude" / "scripts" / "hooks_shared.py"
    assert out.exists()
    assert "hooks" in out.read_text()
