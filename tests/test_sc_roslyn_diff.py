import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "packages" / "sc-roslyn-diff" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import roslyn_diff_runner as runner  # noqa: E402
import sc_diff  # noqa: E402
import sc_git_diff  # noqa: E402


def test_load_json_stdin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{\"ok\": true}"))
    assert runner.load_json_stdin() == {"ok": True}


def test_write_json(capsys: pytest.CaptureFixture):
    runner.write_json({"ok": True})
    assert capsys.readouterr().out == "{\"ok\": true}"


def test_run_command_executes():
    code, out, err = runner.run_command([sys.executable, "-c", "print('hi')"])
    assert code == 0
    assert out.strip() == "hi"
    assert err == ""


def test_resolve_repo_root_prefers_arg(tmp_path: Path):
    resolved = runner.resolve_repo_root(str(tmp_path))
    assert resolved == tmp_path


def test_ensure_roslyn_diff_updates_then_installs(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_run_command(cmd, cwd=None, capture_output=True):
        calls.append(cmd)
        if cmd[:3] == ["dotnet", "tool", "update"]:
            return 1, "", ""
        return 0, "", ""

    monkeypatch.setattr(runner.shutil, "which", lambda name: "roslyn-diff")
    monkeypatch.setattr(runner, "run_command", fake_run_command)

    runner.ensure_roslyn_diff()

    assert calls[0][:3] == ["dotnet", "tool", "update"]
    assert calls[1][:3] == ["dotnet", "tool", "install"]


def test_create_empty_temp():
    path = runner.create_empty_temp(".txt")
    assert path.exists()
    assert path.read_text() == ""
    path.unlink(missing_ok=True)


def test_normalize_display_path(tmp_path: Path):
    nested = tmp_path / "src" / "File.cs"
    nested.parent.mkdir(parents=True)
    nested.write_text("class A {}")
    assert runner.normalize_display_path(nested, tmp_path) == "src/File.cs"


def test_open_html_dispatch(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_popen(cmd):
        captured["cmd"] = cmd
        return None

    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(sys, "platform", "darwin")

    runner.open_html(Path("/tmp/report.html"))

    assert captured["cmd"][0] == "open"


def test_parse_pair_list_valid():
    old_path, new_path = runner.parse_pair_list("old.cs,new.cs")
    assert old_path == "old.cs"
    assert new_path == "new.cs"


def test_parse_pair_list_invalid():
    with pytest.raises(ValueError):
        runner.parse_pair_list("one.cs")


def test_sanitize_filename():
    assert runner.sanitize_filename("a/b:c") == "a_b_c"
    assert runner.sanitize_filename("@@@") == "diff"


def test_chunked():
    chunks = list(runner.chunked([1, 2, 3, 4, 5], 2))
    assert chunks == [[1, 2], [3, 4], [5]]


def test_aggregate_counts():
    results = [
        {"is_identical": True},
        {"is_identical": False},
        {"error": {"code": "diff.failed"}},
    ]
    identical, diff, errors = runner.aggregate_counts(results)
    assert identical == 1
    assert diff == 1
    assert errors == 1


def test_list_folder_files_excludes_git_dir(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ignored.txt").write_text("nope")
    (tmp_path / "keep.txt").write_text("ok")
    files = runner.list_folder_files(tmp_path)
    assert (tmp_path / "keep.txt") in files
    assert (tmp_path / ".git" / "ignored.txt") not in files


def test_build_pairs_for_folders(tmp_path: Path):
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()
    (old_root / "a.cs").write_text("class A {}")
    (new_root / "b.cs").write_text("class B {}")
    pairs, temp_files = runner.build_pairs_for_folders(old_root, new_root)

    rel_paths = sorted(pair.rel_path for pair in pairs)
    assert rel_paths == ["a.cs", "b.cs"]

    warnings = {pair.rel_path: pair.warnings for pair in pairs}
    assert warnings["a.cs"] == ["new_missing"]
    assert warnings["b.cs"] == ["old_missing"]

    for path in temp_files:
        assert path.exists()
        path.unlink(missing_ok=True)


def test_run_roslyn_diff_builds_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_run_command(cmd, cwd=None, capture_output=True):
        captured["cmd"] = cmd
        json_path = Path(cmd[cmd.index("--json") + 1])
        json_path.write_text(json.dumps({"$schema": "roslyn-diff-output-v1"}))
        if "--html" in cmd:
            Path(cmd[cmd.index("--html") + 1]).write_text("<html></html>")
        if "--text" in cmd:
            Path(cmd[cmd.index("--text") + 1]).write_text("diff text")
        if "--git" in cmd:
            Path(cmd[cmd.index("--git") + 1]).write_text("diff patch")
        return 1, "", ""

    opened = {"called": False}

    monkeypatch.setattr(runner, "run_command", fake_run_command)
    monkeypatch.setattr(runner, "open_html", lambda path: opened.__setitem__("called", True))

    text_out = tmp_path / "out.txt"
    git_out = tmp_path / "out.patch"
    result = runner.run_roslyn_diff(
        tmp_path / "old.cs",
        tmp_path / "new.cs",
        "roslyn",
        True,
        tmp_path,
        "label",
        True,
        5,
        text_out,
        git_out,
    )

    assert result["mode"] == "roslyn"
    assert result["roslyn"]["$schema"] == "roslyn-diff-output-v1"
    assert "--mode" in captured["cmd"]
    assert "roslyn" in captured["cmd"]
    assert "--ignore-whitespace" in captured["cmd"]
    assert "--context" in captured["cmd"]
    assert "--text" in captured["cmd"]
    assert "--git" in captured["cmd"]
    assert result["text_path"] == str(text_out.resolve())
    assert result["git_path"] == str(git_out.resolve())
    assert result["output_paths"]["text"] == [str(text_out.resolve())]
    assert result["output_paths"]["git"] == [str(git_out.resolve())]
    assert Path(result["html_path"]).exists()
    assert Path(result["text_path"]).exists()
    assert Path(result["git_path"]).exists()
    assert opened["called"] is True


def test_process_pairs_adds_pair_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fake_run_roslyn_diff(
        old_path,
        new_path,
        mode,
        html,
        output_dir,
        label,
        ignore_whitespace,
        context_lines,
        text_output,
        git_output,
    ):
        return {"is_identical": True, "mode": mode, "html_path": None, "roslyn": None, "warnings": []}

    monkeypatch.setattr(runner, "run_roslyn_diff", fake_run_roslyn_diff)

    pair = runner.DiffPair(
        old_path=tmp_path / "old.cs",
        new_path=tmp_path / "new.cs",
        rel_path="old.cs",
        kind="file",
        warnings=["old_missing"],
    )
    results = runner.process_pairs([pair], "auto", False, tmp_path, "label", 10, False, None, None, None)

    assert results[0]["pair"]["rel_path"] == "old.cs"
    assert "old_missing" in results[0]["warnings"]


def test_sc_diff_main_errors_on_bad_context(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture):
    monkeypatch.setattr(sc_diff, "load_json_stdin", lambda: {"files": "a.cs,b.cs", "context_lines": "nope"})
    exit_code = sc_diff.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["error"]["code"] == "diff.invalid_input"


def test_sc_diff_main_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture):
    old_path = tmp_path / "Old.cs"
    new_path = tmp_path / "New.cs"
    old_path.write_text("class Old {}")
    new_path.write_text("class New {}")

    monkeypatch.setattr(
        sc_diff,
        "load_json_stdin",
        lambda: {
            "files": f"{old_path.name},{new_path.name}",
            "repo_root": str(tmp_path),
            "text_output": True,
        },
    )
    monkeypatch.setattr(sc_diff, "ensure_roslyn_diff", lambda: None)

    def fake_process_pairs(
        pairs,
        mode,
        html,
        output_dir,
        label_prefix,
        files_per_agent,
        ignore_whitespace,
        context_lines,
        text_output,
        git_output,
    ):
        assert text_output == runner.AUTO_OUTPUT
        return [
            {
                "pair": {
                    "kind": "file",
                    "old_path": str(old_path),
                    "new_path": str(new_path),
                    "rel_path": None,
                },
                "is_identical": False,
                "mode": mode,
                "html_path": None,
                "roslyn": {"$schema": "roslyn-diff-output-v1"},
                "warnings": [],
            }
        ]

    monkeypatch.setattr(sc_diff, "process_pairs", fake_process_pairs)

    exit_code = sc_diff.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["data"]["diff_count"] == 1


def test_sc_git_diff_main_missing_refs(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture):
    monkeypatch.setattr(sc_git_diff, "load_json_stdin", lambda: {})
    monkeypatch.setattr(sc_git_diff, "ensure_roslyn_diff", lambda: None)
    monkeypatch.setattr(sc_git_diff, "run_command", lambda *args, **kwargs: (0, "", ""))

    exit_code = sc_git_diff.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["error"]["code"] == "diff.missing_refs"


def test_sc_git_diff_main_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture):
    monkeypatch.setattr(
        sc_git_diff,
        "load_json_stdin",
        lambda: {
            "base_ref": "main",
            "head_ref": "feature",
            "repo_root": str(tmp_path),
        },
    )
    monkeypatch.setattr(sc_git_diff, "ensure_roslyn_diff", lambda: None)
    monkeypatch.setattr(sc_git_diff, "run_command", lambda *args, **kwargs: (0, "git@github.com:org/repo.git", ""))
    monkeypatch.setattr(sc_git_diff, "ensure_ref_available", lambda ref: None)
    monkeypatch.setattr(sc_git_diff, "list_changed_files", lambda base, head: ["src/Foo.cs"])

    temp_file = tmp_path / "Foo.cs"
    temp_file.write_text("class Foo {}")
    monkeypatch.setattr(sc_git_diff, "git_show_to_temp", lambda ref, path: temp_file)

    captured = {"pairs": None}

    def fake_process_pairs(
        pairs,
        mode,
        html,
        output_dir,
        label_prefix,
        files_per_agent,
        ignore_whitespace,
        context_lines,
        text_output,
        git_output,
    ):
        captured["pairs"] = pairs
        return [
            {
                "pair": {
                    "kind": "git",
                    "old_path": str(temp_file),
                    "new_path": str(temp_file),
                    "rel_path": "src/Foo.cs",
                },
                "is_identical": True,
                "mode": mode,
                "html_path": None,
                "roslyn": None,
                "warnings": [],
            }
        ]

    monkeypatch.setattr(sc_git_diff, "process_pairs", fake_process_pairs)

    exit_code = sc_git_diff.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["data"]["refs"]["base"] == "main"
    assert captured["pairs"][0].rel_path == "src/Foo.cs"


def test_validate_sc_diff_hook_accepts_valid_payload():
    script = SCRIPT_DIR / "validate_sc_diff_hook.py"
    payload = {
        "tool_input": {
            "command": (
                "python3 sc_diff.py "
                "{"
                "\"files\":\"a.cs,b.cs\","
                "\"text_output\":true,"
                "\"git_output\":\"/tmp/out.patch\""
                "}"
            )
        }
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0


def test_validate_sc_git_diff_hook_rejects_missing_refs():
    script = SCRIPT_DIR / "validate_sc_git_diff_hook.py"
    payload = {"tool_input": {"command": "python3 sc_git_diff.py {}"}}
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2


def test_validate_sc_git_diff_hook_accepts_output_paths():
    script = SCRIPT_DIR / "validate_sc_git_diff_hook.py"
    payload = {
        "tool_input": {
            "command": (
                "python3 sc_git_diff.py "
                "{"
                "\"base_ref\":\"main\","
                "\"head_ref\":\"feature\","
                "\"text_output\":true,"
                "\"git_output\":\"/tmp/out.patch\""
                "}"
            )
        }
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
