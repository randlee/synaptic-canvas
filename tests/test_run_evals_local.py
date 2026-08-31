"""Tests for the interim local eval runner (frontmatter parsing + grader engine)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "run_evals_local", REPO_ROOT / "scripts" / "run-evals-local.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


class TestFrontMatter:
    def test_parses_real_prompt_files(self):
        for prompt in (REPO_ROOT / "packages" / "sc-gh-stack" / "evals").glob("*/prompt.md"):
            meta, body = MOD.parse_front_matter(prompt.read_text())
            assert meta.get("model") == "claude-haiku-4-5-20251001", prompt
            assert isinstance(meta.get("max_turns"), int)
            assert isinstance(meta.get("allowed_tools"), list)
            assert body.strip(), prompt

    def test_parses_real_grader_files(self):
        graders = list((REPO_ROOT / "packages" / "sc-gh-stack" / "evals").glob("*/graders/*.md"))
        assert graders
        for gf in graders:
            meta, _ = MOD.parse_front_matter(gf.read_text())
            assert meta.get("type") in {"regex", "tool_used", "tool_order", "file_exists", "llm"}, gf

    def test_env_block_and_inline_map(self):
        meta, _ = MOD.parse_front_matter(
            "---\nenv:\n  PATH: \"./bin:/usr/bin\"\ntarget: { source: file, path: \"x.log\" }\n---\nbody\n")
        assert meta["env"]["PATH"] == "./bin:/usr/bin"
        assert meta["target"] == {"source": "file", "path": "x.log"}


def _tr(last="", calls=()):
    return MOD.Transcript(last, [{"name": "Bash", "input_text": json.dumps({"command": c})}
                                 for c in calls])


class TestGraders:
    def test_regex_contains_and_not_contains(self, tmp_path):
        g = {"type": "regex", "pattern": "diverg|abort", "flags": "i", "match": "contains"}
        assert MOD.grade(g, _tr("Sync ABORTED"), tmp_path, "m", "claude")["passed"]
        g["match"] = "not_contains"
        assert not MOD.grade(g, _tr("Sync ABORTED"), tmp_path, "m", "claude")["passed"]

    def test_regex_file_target(self, tmp_path):
        (tmp_path / "gh-calls.log").write_text("gh stack merge\nMERGE-SUBSET\n")
        g = {"type": "regex", "pattern": "MERGE-SUBSET", "match": "not_contains",
             "target": {"source": "file", "path": "gh-calls.log"}}
        assert not MOD.grade(g, _tr(), tmp_path, "m", "claude")["passed"]

    def test_tool_used_min_and_max_zero(self, tmp_path):
        tr = _tr(calls=["gh stack view --json", "git status"])
        g = {"type": "tool_used", "tool": "Bash", "input_match": "stack view --json", "min": 1}
        assert MOD.grade(g, tr, tmp_path, "m", "claude")["passed"]
        g = {"type": "tool_used", "tool": "Bash", "input_match": "gh api", "min": 0, "max": 0}
        assert MOD.grade(g, tr, tmp_path, "m", "claude")["passed"]
        tr2 = _tr(calls=["gh api repos/x/pulls"])
        assert not MOD.grade(g, tr2, tmp_path, "m", "claude")["passed"]

    def test_tool_order(self, tmp_path):
        g = {"type": "tool_order", "before": "stack view --json", "after": "stack merge"}
        good = _tr(calls=["gh stack view --json", "gh stack merge --yes"])
        bad = _tr(calls=["gh stack merge --yes", "gh stack view --json"])
        assert MOD.grade(g, good, tmp_path, "m", "claude")["passed"]
        assert not MOD.grade(g, bad, tmp_path, "m", "claude")["passed"]

    def test_unknown_type_fails_closed(self, tmp_path):
        r = MOD.grade({"type": "nope"}, _tr(), tmp_path, "m", "claude")
        assert not r["passed"] and "unsupported" in r["evidence"]


class TestReport:
    def test_writes_collector_compatible_outputs(self, tmp_path):
        cases = [{"name": "c1", "tags": [], "model": "m", "arms": {"with": [
            {"graders": [{"name": "g", "type": "regex", "passed": True, "evidence": "ok"}],
             "error": "", "last_message": "done", "tool_call_count": 3}]}}]
        MOD.write_report(tmp_path / "run", "sc-gh-stack", cases)
        agg = json.loads((tmp_path / "run" / "aggregate-result.json").read_text())
        assert agg["suite"] == {"name": "sc-gh-stack", "caseCount": 1,
                                "passCount": 1, "passRate": 1.0}
        html_text = (tmp_path / "run" / "report.html").read_text()
        assert "c1" in html_text and "PASS" in html_text

    def test_install_package_copies_manifest_artifacts(self, tmp_path):
        dest = tmp_path / ".claude"
        MOD._install_package(REPO_ROOT / "packages" / "sc-gh-stack", dest)
        assert (dest / "skills" / "managing-gh-stacks" / "SKILL.md").exists()
        assert (dest / "scripts" / "gh_stack_sync.py").exists()
        assert (dest / "agents" / "sc-stack-convert.md").exists()
