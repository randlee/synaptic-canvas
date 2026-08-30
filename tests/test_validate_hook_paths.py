"""Tests for scripts/validate-hook-paths.py (hook command CWD-fragility scan)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "validate_hook_paths", REPO_ROOT / "scripts" / "validate-hook-paths.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# has_relative_path
# ---------------------------------------------------------------------------

def test_good_pattern_project_dir_braced():
    mod = _load()
    assert mod.has_relative_path(
        'python3 ${CLAUDE_PROJECT_DIR}/scripts/foo.py') is False


def test_good_pattern_project_dir_unbraced():
    mod = _load()
    assert mod.has_relative_path(
        'python3 $CLAUDE_PROJECT_DIR/scripts/foo.py') is False


def test_good_pattern_plugin_root_braced():
    mod = _load()
    assert mod.has_relative_path(
        'python3 ${CLAUDE_PLUGIN_ROOT}/scripts/foo.py') is False


def test_good_pattern_plugin_root_unbraced():
    mod = _load()
    assert mod.has_relative_path(
        'python3 $CLAUDE_PLUGIN_ROOT/scripts/foo.py') is False


def test_good_pattern_inline_python():
    mod = _load()
    assert mod.has_relative_path('python3 -c "print(1)"') is False
    assert mod.has_relative_path('python -c "print(1)"') is False


def test_bad_pattern_dot_slash():
    mod = _load()
    assert mod.has_relative_path('python3 ./scripts/foo.py') is True


def test_bad_pattern_claude_dir():
    mod = _load()
    assert mod.has_relative_path('python3 .claude/scripts/foo.py') is True


def test_bad_pattern_bare_scripts_leading():
    mod = _load()
    assert mod.has_relative_path('scripts/foo.py') is True


def test_bad_pattern_bare_scripts_after_space():
    mod = _load()
    assert mod.has_relative_path('python3 scripts/foo.py') is True


def test_neutral_command_without_path_or_marker():
    # No good marker and no bad pattern match -> not flagged.
    mod = _load()
    assert mod.has_relative_path('echo hello') is False


# ---------------------------------------------------------------------------
# scan_json_file
# ---------------------------------------------------------------------------

def _write_settings_json(path: Path, command: str):
    path.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}
            ]
        }
    }))


def test_scan_json_file_flags_relative_command(tmp_path):
    mod = _load()
    f = tmp_path / "settings.json"
    _write_settings_json(f, "python3 scripts/foo.py")
    issues = mod.scan_json_file(f)
    assert len(issues) == 1
    assert issues[0]["hook_type"] == "PreToolUse"
    assert issues[0]["command"] == "python3 scripts/foo.py"
    assert issues[0]["context"] == "root.hooks"


def test_scan_json_file_passes_good_command(tmp_path):
    mod = _load()
    f = tmp_path / "settings.json"
    _write_settings_json(f, "python3 ${CLAUDE_PROJECT_DIR}/scripts/foo.py")
    assert mod.scan_json_file(f) == []


def test_scan_json_file_ignores_file_without_hooks_key(tmp_path):
    mod = _load()
    f = tmp_path / "other.json"
    f.write_text(json.dumps({"not_hooks": True}))
    assert mod.scan_json_file(f) == []


def test_scan_json_file_handles_invalid_json(tmp_path):
    mod = _load()
    f = tmp_path / "broken.json"
    f.write_text("{not valid json")
    assert mod.scan_json_file(f) == []


def test_scan_json_file_ignores_non_dict_top_level(tmp_path):
    mod = _load()
    f = tmp_path / "list.json"
    f.write_text(json.dumps([1, 2, 3]))
    assert mod.scan_json_file(f) == []


def test_scan_json_file_ignores_malformed_hook_shapes(tmp_path):
    mod = _load()
    f = tmp_path / "malformed.json"
    f.write_text(json.dumps({
        "hooks": {
            "PreToolUse": "not-a-list",
            "PostToolUse": [
                "not-a-dict",
                {"hooks": "not-a-list"},
                {"hooks": ["not-a-dict"]},
            ],
        }
    }))
    assert mod.scan_json_file(f) == []


# ---------------------------------------------------------------------------
# scan_markdown_file
# ---------------------------------------------------------------------------

def _agent_md(command: str) -> str:
    return f"""---
name: demo-agent
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "{command}"
---

# Demo Agent
"""


def test_scan_markdown_file_flags_relative_command(tmp_path):
    mod = _load()
    f = tmp_path / "agent.md"
    f.write_text(_agent_md("python3 ./scripts/validate.py"))
    issues = mod.scan_markdown_file(f)
    assert len(issues) == 1
    assert issues[0]["hook_type"] == "PreToolUse"
    assert issues[0]["context"] == "frontmatter.hooks"


def test_scan_markdown_file_passes_good_command(tmp_path):
    mod = _load()
    f = tmp_path / "agent.md"
    f.write_text(_agent_md("python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py"))
    assert mod.scan_markdown_file(f) == []


def test_scan_markdown_file_ignores_file_without_frontmatter(tmp_path):
    mod = _load()
    f = tmp_path / "plain.md"
    f.write_text("# Just a heading\n\nNo frontmatter here.\n")
    assert mod.scan_markdown_file(f) == []


def test_scan_markdown_file_ignores_frontmatter_without_hooks(tmp_path):
    mod = _load()
    f = tmp_path / "agent.md"
    f.write_text("---\nname: demo\n---\n\n# Demo\n")
    assert mod.scan_markdown_file(f) == []


def test_scan_markdown_file_ignores_incomplete_frontmatter_delimiters(tmp_path):
    mod = _load()
    f = tmp_path / "agent.md"
    f.write_text("---\nname: demo\nno closing delimiter\n")
    assert mod.scan_markdown_file(f) == []


def test_scan_markdown_file_ignores_unreadable_file(tmp_path):
    mod = _load()
    missing = tmp_path / "does-not-exist.md"
    assert mod.scan_markdown_file(missing) == []


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def test_main_exits_zero_when_clean(tmp_path, monkeypatch, capsys):
    mod = _load()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    (tmp_path / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "python3 ${CLAUDE_PROJECT_DIR}/scripts/foo.py"}
        ]}]}
    }))
    assert mod.main() == 0
    assert "No hook path issues found" in capsys.readouterr().out


def test_main_exits_two_when_issues_found(tmp_path, monkeypatch, capsys):
    mod = _load()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    (tmp_path / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "python3 scripts/foo.py"}
        ]}]}
    }))
    assert mod.main() == 2
    out = capsys.readouterr().out
    assert "Found 1 hook(s)" in out
    assert "scripts/foo.py" in out


def test_main_scans_both_json_and_markdown(tmp_path, monkeypatch, capsys):
    mod = _load()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    (tmp_path / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "python3 scripts/a.py"}
        ]}]}
    }))
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "demo.md").write_text(_agent_md("python3 .claude/scripts/b.py"))
    assert mod.main() == 2
    out = capsys.readouterr().out
    assert "Found 2 hook(s)" in out


def test_main_skips_git_and_venv_directories(tmp_path, monkeypatch, capsys):
    mod = _load()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "python3 scripts/a.py"}
        ]}]}
    }))
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "python3 scripts/b.py"}
        ]}]}
    }))
    assert mod.main() == 0
    assert "No hook path issues found" in capsys.readouterr().out
