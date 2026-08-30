"""Tests for scripts/generate-eval-fixtures.py (packages/evals -> test-packages fixtures)."""
from __future__ import annotations

import importlib.util
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "generate_eval_fixtures", REPO_ROOT / "scripts" / "generate-eval-fixtures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def _setup_dirs(tmp_path, monkeypatch):
    packages_dir = tmp_path / "packages"
    fixtures_dir = tmp_path / "test-packages" / "fixtures"
    monkeypatch.setattr(MOD, "PACKAGES_DIR", packages_dir)
    monkeypatch.setattr(MOD, "FIXTURES_DIR", fixtures_dir)
    # main() also prints paths relative to REPO_ROOT; keep it consistent with
    # the tmp_path tree so that path.relative_to(REPO_ROOT) doesn't blow up.
    monkeypatch.setattr(MOD, "REPO_ROOT", tmp_path)
    return packages_dir, fixtures_dir


def _grader(path: Path, meta_lines: str, body: str = "grader body\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{meta_lines}\n---\n{body}", encoding="utf-8")


class TestMapGrader:
    def test_regex_contains_last_message(self):
        g = {"type": "regex", "pattern": "abort", "flags": "i", "match": "contains"}
        exp = MOD._map_grader("g1", g)
        assert exp["type"] == "output_contains"
        assert exp["expected"] == {"pattern": "abort", "flags": "i"}
        assert exp["description"] == "grader: g1"

    def test_regex_not_contains_last_message(self):
        g = {"type": "regex", "pattern": "abort", "match": "not_contains"}
        exp = MOD._map_grader("g2", g)
        assert exp["type"] == "output_not_contains"
        assert exp["expected"]["pattern"] == "abort"

    def test_regex_file_contains(self):
        g = {"type": "regex", "pattern": "MERGE", "match": "contains",
             "target": {"source": "file", "path": "gh-calls.log"}}
        exp = MOD._map_grader("g3", g)
        assert exp["type"] == "file_contains"
        assert exp["expected"] == {"path": "gh-calls.log", "pattern": "MERGE", "flags": ""}

    def test_regex_file_not_contains(self):
        g = {"type": "regex", "pattern": "MERGE", "match": "not_contains",
             "target": {"source": "file", "path": "gh-calls.log"}}
        exp = MOD._map_grader("g4", g)
        assert exp["type"] == "file_not_contains"
        assert exp["expected"]["path"] == "gh-calls.log"

    def test_tool_used_min_maps_to_tool_call(self):
        g = {"type": "tool_used", "tool": "Bash", "input_match": "stack view", "min": 1}
        exp = MOD._map_grader("g5", g)
        assert exp["type"] == "tool_call"
        assert exp["expected"] == {"tool": "Bash", "pattern": "stack view", "flags": "i"}

    def test_tool_used_max_zero_maps_to_tool_not_called(self):
        # Regression: `max: 0` is falsy, so a naive `g.get("max")` truthiness
        # check would silently swallow this and misclassify as tool_call.
        g = {"type": "tool_used", "tool": "Bash", "input_match": "gh api", "min": 0, "max": 0}
        exp = MOD._map_grader("g6", g)
        assert exp["type"] == "tool_not_called"

    def test_tool_order(self):
        g = {"type": "tool_order", "before": "stack view", "after": "stack merge"}
        exp = MOD._map_grader("g7", g)
        assert exp["type"] == "tool_order"
        assert exp["expected"] == {"before": "stack view", "after": "stack merge"}

    def test_llm(self):
        g = {"type": "llm", "criteria": "response is polite"}
        exp = MOD._map_grader("g8", g)
        assert exp["type"] == "llm_judge"
        assert exp["expected"] == {"criteria": "response is polite"}

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="unmapped grader type"):
            MOD._map_grader("g9", {"type": "nope"})


class TestEnvMergeCommand:
    def test_returns_heredoc_embedding_env(self):
        cmd = MOD._env_merge_command({"PATH": "./bin:/usr/bin"})
        assert cmd.startswith("python3 - <<'MERGE_ENV_EOF'")
        assert "MERGE_ENV_EOF" in cmd
        assert "'PATH': './bin:/usr/bin'" in cmd or '"PATH"' in cmd or "PATH" in cmd

    def test_executed_command_absolutizes_relative_path_entries(self, tmp_path):
        cmd = MOD._env_merge_command({"PATH": "./bin:../bin:/usr/bin"})
        cwd = tmp_path / "project"
        cwd.mkdir()
        result = subprocess.run(["bash", "-c", cmd], cwd=cwd, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

        settings = yaml.safe_load((cwd / ".claude" / "settings.json").read_text())
        path_val = settings["env"]["PATH"]
        parts = path_val.split(":")
        assert parts[0] == str((cwd / "bin").resolve())
        assert parts[1] == str((cwd.parent / "bin").resolve())
        assert parts[2] == "/usr/bin"

    def test_merges_into_existing_settings_without_dropping_other_keys(self, tmp_path):
        cwd = tmp_path / "project"
        (cwd / ".claude").mkdir(parents=True)
        (cwd / ".claude" / "settings.json").write_text('{"hooks": {"x": 1}}', encoding="utf-8")

        cmd = MOD._env_merge_command({"PATH": "/usr/bin"})
        result = subprocess.run(["bash", "-c", cmd], cwd=cwd, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

        settings = yaml.safe_load((cwd / ".claude" / "settings.json").read_text())
        assert settings["hooks"] == {"x": 1}
        assert settings["env"]["PATH"] == "/usr/bin"

    def test_non_path_keys_kept_verbatim(self, tmp_path):
        cwd = tmp_path / "project"
        cwd.mkdir()
        cmd = MOD._env_merge_command({"FOO": "bar", "PATH": "./bin"})
        result = subprocess.run(["bash", "-c", cmd], cwd=cwd, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        settings = yaml.safe_load((cwd / ".claude" / "settings.json").read_text())
        assert settings["env"]["FOO"] == "bar"
        assert settings["env"]["PATH"] == str((cwd / "bin").resolve())


PROMPT_MD = textwrap.dedent("""\
    ---
    name: Case One
    model: claude-haiku-4-5-20251001
    tags: [foo, bar]
    allowed_tools: [Bash, Read]
    timeout_seconds: 120
    env:
      PATH: "./bin:/usr/bin"
    ---
    Do the thing carefully.
    """)

PROMPT_MD_NO_EXTRAS = textwrap.dedent("""\
    ---
    name: Case Two
    model: claude-haiku-4-5-20251001
    allowed_tools: [Read]
    timeout_seconds: 60
    ---
    A simpler case.
    """)


def _build_full_case(packages_dir: Path, pkg: str = "demo-pkg", case: str = "case-one") -> Path:
    case_dir = packages_dir / pkg / "evals" / case
    case_dir.mkdir(parents=True)
    (case_dir / "prompt.md").write_text(PROMPT_MD, encoding="utf-8")
    (case_dir / "scaffold.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")

    graders_dir = case_dir / "graders"
    _grader(graders_dir / "a-output-contains.md",
            'type: regex\npattern: "diverg|abort"\nflags: "i"\nmatch: contains')
    _grader(graders_dir / "b-file-not-contains.md",
            'type: regex\npattern: "MERGE-SUBSET"\nmatch: not_contains\n'
            'target: { source: file, path: "gh-calls.log" }')
    _grader(graders_dir / "c-tool-call.md",
            'type: tool_used\ntool: Bash\ninput_match: "stack view --json"\nmin: 1')
    _grader(graders_dir / "d-tool-not-called.md",
            'type: tool_used\ntool: Bash\ninput_match: "gh api"\nmin: 0\nmax: 0')
    _grader(graders_dir / "e-tool-order.md",
            'type: tool_order\nbefore: "stack view --json"\nafter: "stack merge"')
    _grader(graders_dir / "f-llm.md",
            'type: llm\ncriteria: "response explains the outcome"')
    return case_dir


class TestGeneratePackage:
    def test_end_to_end_fixture_and_test_yaml(self, tmp_path, monkeypatch):
        packages_dir, fixtures_dir = _setup_dirs(tmp_path, monkeypatch)
        _build_full_case(packages_dir)

        written = MOD.generate_package("demo-pkg")
        assert written

        fixture_dir = fixtures_dir / "demo-pkg-evals"
        fixture_yaml = yaml.safe_load((fixture_dir / "fixture.yaml").read_text())
        assert fixture_yaml["name"] == "demo-pkg-evals"
        assert fixture_yaml["setup"]["plugins"] == ["demo-pkg@synaptic-canvas"]
        assert fixture_yaml["package"] == "demo-pkg@synaptic-canvas"
        assert fixture_yaml["tests_dir"] == "tests"

        scaffold_copy = fixture_dir / "resources" / "case-one" / "scaffold.sh"
        assert scaffold_copy.exists()
        assert scaffold_copy.read_text() == "#!/bin/sh\necho hi\n"

        test_yaml_path = fixture_dir / "tests" / "test_case_one.yaml"
        raw = test_yaml_path.read_text()
        assert raw.startswith("# GENERATED by scripts/generate-eval-fixtures.py")
        assert "do not edit" in raw.lower()

        doc = yaml.safe_load(raw)
        assert doc["test_id"] == "demo-pkg-eval-case-one"
        assert doc["test_name"] == "Case One"
        assert "generated-eval" in doc["tags"]
        assert doc["execution"]["model"] == "claude-haiku-4-5-20251001"
        assert doc["execution"]["tools"] == ["Bash", "Read"]
        assert doc["execution"]["timeout_ms"] == 120 * 1000
        assert doc["execution"]["prompt"] == "Do the thing carefully."

        setup = doc["setup"]
        assert {"src": "resources/case-one/scaffold.sh", "dest": "scaffold.sh"} in setup["files"]
        assert "bash scaffold.sh" in setup["commands"]
        assert any(c.startswith("python3 - <<'MERGE_ENV_EOF'") for c in setup["commands"])

        exps = doc["expectations"]
        assert [e["id"] for e in exps] == [f"exp-{i:03d}" for i in range(1, 7)]
        types = [e["type"] for e in exps]
        assert types == [
            "output_contains", "file_not_contains", "tool_call",
            "tool_not_called", "tool_order", "llm_judge",
        ]

    def test_case_without_scaffold_or_env_has_no_setup_key(self, tmp_path, monkeypatch):
        packages_dir, fixtures_dir = _setup_dirs(tmp_path, monkeypatch)
        case_dir = packages_dir / "demo-pkg" / "evals" / "case-two"
        case_dir.mkdir(parents=True)
        (case_dir / "prompt.md").write_text(PROMPT_MD_NO_EXTRAS, encoding="utf-8")
        _grader(case_dir / "graders" / "a-output.md",
                'type: regex\npattern: "ok"\nmatch: contains')

        MOD.generate_package("demo-pkg")

        doc = yaml.safe_load(
            (fixtures_dir / "demo-pkg-evals" / "tests" / "test_case_two.yaml").read_text())
        assert "setup" not in doc
        assert doc["execution"]["timeout_ms"] == 60 * 1000

    def test_results_dir_and_non_case_dirs_are_skipped(self, tmp_path, monkeypatch):
        packages_dir, fixtures_dir = _setup_dirs(tmp_path, monkeypatch)
        _build_full_case(packages_dir)
        evals_dir = packages_dir / "demo-pkg" / "evals"

        results_dir = evals_dir / "results" / "some-run"
        results_dir.mkdir(parents=True)
        (results_dir / "prompt.md").write_text(PROMPT_MD, encoding="utf-8")

        not_a_case = evals_dir / "INCIDENTS.md"
        not_a_case.write_text("notes", encoding="utf-8")

        empty_dir = evals_dir / "scratch"
        empty_dir.mkdir()

        MOD.generate_package("demo-pkg")

        tests_dir = fixtures_dir / "demo-pkg-evals" / "tests"
        produced = {p.name for p in tests_dir.iterdir()}
        assert produced == {"test_case_one.yaml"}


class TestMain:
    def test_missing_evals_dir_returns_error(self, tmp_path, monkeypatch, capsys):
        packages_dir, fixtures_dir = _setup_dirs(tmp_path, monkeypatch)
        (packages_dir / "no-evals-pkg").mkdir(parents=True)

        rc = MOD.main(["--package", "no-evals-pkg"])
        assert rc == 1
        assert "no evals/" in capsys.readouterr().err

    def test_valid_package_returns_zero(self, tmp_path, monkeypatch):
        packages_dir, fixtures_dir = _setup_dirs(tmp_path, monkeypatch)
        _build_full_case(packages_dir)

        rc = MOD.main(["--package", "demo-pkg"])
        assert rc == 0
        assert (fixtures_dir / "demo-pkg-evals" / "fixture.yaml").exists()
