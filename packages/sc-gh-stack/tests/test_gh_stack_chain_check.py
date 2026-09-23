"""Unit tests for gh_stack_chain_check.evaluate over injected git/gh lookups."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gh_stack_chain_check.py"
spec = importlib.util.spec_from_file_location("gh_stack_chain_check_under_test", SCRIPT)
assert spec is not None and spec.loader is not None
gcc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gcc
spec.loader.exec_module(gcc)

TRUNK = "develop"
T0, A1, B2, C3, OLD = ("0" * 40, "a" * 40, "b" * 40, "c" * 40, "d" * 40)


def pr(number: int, head: str, base: str, oid: str, *, draft: bool = False, state: str = "OPEN") -> dict:
    return {"number": number, "headRefName": head, "baseRefName": base, "headRefOid": oid,
            "isDraft": draft, "state": state}


class EvaluateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.origins = {TRUNK: T0, "l1": A1, "l2": B2, "l3": C3}
        # linear chain: T0 < A1 < B2 < C3
        self.ancestors = {(T0, A1), (T0, B2), (T0, C3), (A1, B2), (A1, C3), (B2, C3)}
        self.merge = True
        for p in (
            mock.patch.object(gcc, "origin_sha", side_effect=lambda ref: self.origins.get(ref)),
            mock.patch.object(gcc, "is_ancestor", side_effect=lambda a, b: a == b or (a, b) in self.ancestors),
            mock.patch.object(gcc, "merge_clean", side_effect=lambda base, head: self.merge),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.prs = {"l1": pr(1, "l1", TRUNK, A1), "l2": pr(2, "l2", "l1", B2), "l3": pr(3, "l3", "l2", C3)}

    def test_linear_pushed_chain_is_linkable(self) -> None:
        report = gcc.evaluate(TRUNK, ["l1", "l2", "l3"], self.prs, fetched=True, use_pr=True)
        self.assertTrue(report["linkable"], report["problems"])
        self.assertEqual(report["notes"], [])
        self.assertTrue(report["landing"]["clean"])
        text = gcc.render(report)
        self.assertIn("next: gh stack link --base develop 1 2 3", text)
        self.assertNotIn("#1", text.split("next:")[1], "a `#` would start a shell comment")
        self.assertEqual(report["link_command"], "gh stack link --base develop 1 2 3")

    def test_unpushed_layer_is_a_problem(self) -> None:
        self.origins.pop("l2")
        report = gcc.evaluate(TRUNK, ["l1", "l2", "l3"], self.prs, fetched=True, use_pr=True)
        self.assertFalse(report["linkable"])
        self.assertTrue(any("l2: not on origin" in p for p in report["problems"]))
        self.assertIsNone(report["landing"]["clean"], "landing not judged while a head is unpushed")

    def test_fork_layer_does_not_contain_parent(self) -> None:
        # l3 was cut from l1, not from l2: (B2, C3) missing
        self.ancestors.discard((B2, C3))
        report = gcc.evaluate(TRUNK, ["l1", "l2", "l3"], self.prs, fetched=True, use_pr=True)
        self.assertFalse(report["linkable"])
        self.assertTrue(any("l3: does not contain parent l2" in p for p in report["problems"]))

    def test_bottom_behind_trunk_is_a_note_not_a_problem(self) -> None:
        # trunk moved past the bottom's base; bottom still has its own commits
        self.ancestors.discard((T0, A1))
        report = gcc.evaluate(TRUNK, ["l1", "l2", "l3"], self.prs, fetched=True, use_pr=True)
        self.assertTrue(report["linkable"], report["problems"])
        self.assertTrue(any("l1: behind develop" in n for n in report["notes"]))

    def test_bottom_already_in_trunk_is_a_problem(self) -> None:
        self.ancestors.discard((T0, A1))
        self.ancestors.add((A1, T0))
        report = gcc.evaluate(TRUNK, ["l1", "l2"], self.prs, fetched=True, use_pr=True)
        self.assertTrue(any("no commits beyond develop" in p for p in report["problems"]))

    def test_wrong_pr_base_is_a_note_link_corrects_it(self) -> None:
        self.prs["l2"] = pr(2, "l2", TRUNK, B2)  # should be l1
        report = gcc.evaluate(TRUNK, ["l1", "l2", "l3"], self.prs, fetched=True, use_pr=True)
        self.assertTrue(report["linkable"])
        self.assertTrue(any("PR #2 base is develop, expected l1" in n for n in report["notes"]))
        self.assertFalse(report["rows"][1]["pr_base_ok"])

    def test_draft_closed_and_stale_pr_heads_are_problems(self) -> None:
        self.prs["l1"] = pr(1, "l1", TRUNK, A1, draft=True)
        self.prs["l2"] = pr(2, "l2", "l1", B2, state="MERGED")
        self.prs["l3"] = pr(3, "l3", "l2", OLD)
        report = gcc.evaluate(TRUNK, ["l1", "l2", "l3"], self.prs, fetched=True, use_pr=True)
        joined = "\n".join(report["problems"])
        self.assertIn("PR #1 is DRAFT", joined)
        self.assertIn("PR #2 is MERGED", joined)
        self.assertIn("PR #3 head ddddddddd != origin ccccccccc", joined)

    def test_missing_pr_is_a_note(self) -> None:
        self.prs.pop("l3")
        report = gcc.evaluate(TRUNK, ["l1", "l2", "l3"], self.prs, fetched=True, use_pr=True)
        self.assertTrue(report["linkable"])
        self.assertTrue(any("l3: no PR yet" in n and "base l2" in n for n in report["notes"]))
        text = gcc.render(report)
        self.assertIn("next: gh stack link --base develop 1 2 l3", text)
        self.assertIn("bare branch name pushes the LOCAL ref", text)

    def test_top_conflicts_with_trunk(self) -> None:
        self.merge = False
        report = gcc.evaluate(TRUNK, ["l1", "l2", "l3"], self.prs, fetched=True, use_pr=True)
        self.assertFalse(report["linkable"])
        self.assertFalse(report["landing"]["clean"])
        self.assertIn("MERGE INTO TRUNK: ⛔", gcc.render(report))

    def test_old_git_marks_merge_unknown(self) -> None:
        self.merge = None
        report = gcc.evaluate(TRUNK, ["l1"], self.prs, fetched=True, use_pr=True)
        self.assertTrue(report["linkable"])
        self.assertIsNone(report["landing"]["clean"])
        self.assertIn("git < 2.38", report["landing"]["reason"])

    def test_missing_trunk_on_origin_raises_tool_error(self) -> None:
        self.origins.pop(TRUNK)
        with self.assertRaises(gcc.ToolError):
            gcc.evaluate(TRUNK, ["l1"], self.prs, fetched=True, use_pr=True)

    def test_duplicate_branch_is_a_problem(self) -> None:
        report = gcc.evaluate(TRUNK, ["l1", "l1"], self.prs, fetched=True, use_pr=True)
        self.assertTrue(any("appears twice" in p for p in report["problems"]))


class IndexAndResolveTests(unittest.TestCase):
    def test_open_pr_wins_over_closed_for_same_branch(self) -> None:
        prs = [pr(5, "l1", TRUNK, OLD, state="CLOSED"), pr(9, "l1", TRUNK, A1)]
        by_number, by_branch = gcc.index_prs(prs)
        self.assertEqual(by_branch["l1"]["number"], 9)
        self.assertEqual(set(by_number), {5, 9})

    def test_newest_wins_among_same_state(self) -> None:
        prs = [pr(5, "l1", TRUNK, OLD, state="CLOSED"), pr(7, "l1", TRUNK, A1, state="CLOSED")]
        _, by_branch = gcc.index_prs(prs)
        self.assertEqual(by_branch["l1"]["number"], 7)

    def test_resolve_numbers_and_names(self) -> None:
        by_number, _ = gcc.index_prs([pr(12, "fix/x", TRUNK, A1)])
        self.assertEqual(gcc.resolve_layers(["12", "feat/y"], by_number), ["fix/x", "feat/y"])
        with mock.patch.object(gcc, "view_pr", side_effect=gcc.ToolError("PR #99 not found")):
            with self.assertRaises(gcc.ToolError):
                gcc.resolve_layers(["99"], by_number)


if __name__ == "__main__":
    unittest.main()


class MainContractTests(unittest.TestCase):
    """Exit codes 0/1/2 and the never-a-traceback guard, with every external call patched."""

    def _args(self, **kw) -> "gcc.argparse.Namespace":
        base = {"trunk": TRUNK, "layers": ["l1"], "no_fetch": True, "no_pr": True, "json": False}
        base.update(kw)
        return gcc.argparse.Namespace(**base)

    def test_exit_0_when_linkable(self) -> None:
        with mock.patch.object(gcc, "preflight"), \
             mock.patch.object(gcc, "evaluate", return_value={"trunk": TRUNK, "trunk_origin": T0, "rows": [], "problems": [], "notes": [], "landing": {"clean": None, "reason": "x"}, "linkable": True}), \
             mock.patch("builtins.print"):
            self.assertEqual(gcc.run_check(self._args()), 0)

    def test_exit_1_when_problems(self) -> None:
        with mock.patch.object(gcc, "preflight"), \
             mock.patch.object(gcc, "evaluate", return_value={"trunk": TRUNK, "trunk_origin": T0, "rows": [], "problems": ["p"], "notes": [], "landing": {"clean": None, "reason": "x"}, "linkable": False}), \
             mock.patch("builtins.print"):
            self.assertEqual(gcc.run_check(self._args()), 1)

    def test_exit_2_on_tool_error_and_on_unexpected_exception(self) -> None:
        import io
        for exc in (gcc.ToolError("git missing"), KeyError("owner")):
            with mock.patch.object(gcc, "preflight", side_effect=exc), \
                 mock.patch.object(gcc.sys, "stderr", new=io.StringIO()) as err:
                self.assertEqual(gcc.guarded("gh-stack-chain-check", lambda: gcc.run_check(self._args())), 2)
                self.assertTrue(err.getvalue().startswith("gh-stack-chain-check: "), err.getvalue())
                self.assertNotIn("Traceback", err.getvalue())

    def test_numeric_layer_outside_open_list_uses_pr_view(self) -> None:
        by_number, by_branch = gcc.index_prs([])
        with mock.patch.object(gcc, "view_pr", return_value=pr(1500, "fix/old", TRUNK, A1, state="MERGED")) as vp:
            self.assertEqual(gcc.resolve_layers(["1500"], by_number, by_branch), ["fix/old"])
            vp.assert_called_once_with(1500)
        self.assertEqual(by_branch["fix/old"]["state"], "MERGED")


class ErrorConditionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.origins = {TRUNK: T0, "l1": A1}
        for p in (
            mock.patch.object(gcc, "origin_sha", side_effect=lambda ref: self.origins.get(ref)),
            mock.patch.object(gcc, "is_ancestor", side_effect=lambda a, b: a == b or (a, b) == (T0, A1)),
            mock.patch.object(gcc, "merge_clean", return_value=True),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_trunk_listed_as_layer_is_a_problem(self) -> None:
        report = gcc.evaluate(TRUNK, ["l1", TRUNK], {}, fetched=True, use_pr=False)
        self.assertTrue(any("is the trunk" in p for p in report["problems"]))

    def test_index_prs_skips_malformed_entries(self) -> None:
        by_number, by_branch = gcc.index_prs([{"number": "x"}, {"headRefName": "a"}, pr(3, "l1", TRUNK, A1), "junk"])
        self.assertEqual(list(by_number), [3])
        self.assertEqual(list(by_branch), ["l1"])

    def test_view_pr_rejects_bad_shape(self) -> None:
        cp = __import__("subprocess").CompletedProcess(["gh"], 0, stdout='{"number": 5}', stderr="")
        with mock.patch.object(gcc, "run", return_value=cp):
            with self.assertRaises(gcc.ToolError):
                gcc.view_pr(5)

    def test_fetch_failure_is_a_warning_not_exit_2(self) -> None:
        import io
        failed = __import__("subprocess").CompletedProcess(["git"], 128, stdout="", stderr="fatal: could not read from remote")
        with mock.patch.object(gcc, "preflight"), \
             mock.patch.object(gcc, "run", return_value=failed), \
             mock.patch.object(gcc, "evaluate", return_value={"trunk": TRUNK, "trunk_origin": T0, "rows": [], "problems": [], "notes": [], "landing": {"clean": None, "reason": "x"}, "linkable": True}), \
             mock.patch("builtins.print"), \
             mock.patch.object(gcc.sys, "stderr", new=io.StringIO()) as err:
            args = gcc.argparse.Namespace(trunk=TRUNK, layers=["l1"], no_fetch=False, no_pr=True, json=False)
            self.assertEqual(gcc.run_check(args), 0)
            self.assertIn("warning: git fetch origin failed", err.getvalue())

    def test_run_hint_for_rate_limit_and_auth(self) -> None:
        shared = gcc.sys.modules[gcc.run.__module__]
        self.assertIn("rate limit", shared.hint_for("HTTP 403: API rate limit exceeded"))
        self.assertIn("gh auth", shared.hint_for("gh: Not logged in (HTTP 401)"))
        self.assertEqual(shared.hint_for("something else"), "")


class NextLineTests(unittest.TestCase):
    def test_no_next_line_when_not_linkable(self) -> None:
        report = {"trunk": TRUNK, "trunk_origin": T0, "rows": [{"layer": 1, "branch": "l1", "pr": 1, "pushed": False,
                  "contains_parent": None, "pr_base_ok": True, "pr_head_ok": True, "draft": False}],
                  "problems": ["L1 l1: not on origin"], "notes": [], "landing": {"clean": None, "reason": "x"}, "linkable": False}
        self.assertNotIn("next:", gcc.render(report))

    def test_link_command_survives_a_shell(self) -> None:
        import shlex, subprocess
        report = {"trunk": "develop", "rows": [{"branch": "l1", "pr": 1547}, {"branch": "l2", "pr": 1548}], "linkable": True}
        cmd = gcc.link_command(report)
        echoed = subprocess.run(["sh", "-c", "echo " + cmd], text=True, capture_output=True).stdout.strip()
        self.assertEqual(echoed, cmd)
        self.assertEqual(shlex.split(cmd)[-2:], ["1547", "1548"])


class RealGitTests(unittest.TestCase):
    """Prove the git semantics the chain logic assumes, against a real temporary repository."""

    @classmethod
    def setUpClass(cls) -> None:
        import shutil, subprocess, tempfile, os
        if shutil.which("git") is None:
            raise unittest.SkipTest("git not installed")
        cls.tmp = tempfile.mkdtemp()
        cls.cwd = os.getcwd()
        os.chdir(cls.tmp)
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x", "PATH": os.environ["PATH"], "HOME": cls.tmp}
        def git(*a): return subprocess.run(["git", *a], check=True, text=True, capture_output=True, env=env).stdout.strip()
        cls.git = staticmethod(git)
        git("init", "-q", "-b", "develop")
        Path("a.txt").write_text("a\n"); git("add", "."); git("commit", "-qm", "base")
        git("checkout", "-qb", "l1"); Path("a.txt").write_text("l1\n"); Path("b.txt").write_text("b\n"); git("add", "."); git("commit", "-qm", "l1")
        git("checkout", "-qb", "l2"); Path("c.txt").write_text("c\n"); git("add", "."); git("commit", "-qm", "l2")
        git("checkout", "-q", "develop"); git("checkout", "-qb", "fork"); Path("a.txt").write_text("conflict\n"); git("add", "."); git("commit", "-qm", "fork")
        git("checkout", "-q", "develop")
        # simulate origin/* by pointing remote-tracking refs at the local branches
        for b in ("develop", "l1", "l2", "fork"):
            git("update-ref", f"refs/remotes/origin/{b}", b)
        cls.sha = {b: git("rev-parse", b) for b in ("develop", "l1", "l2", "fork")}

    @classmethod
    def tearDownClass(cls) -> None:
        import os, shutil
        os.chdir(cls.cwd)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_origin_sha_and_is_ancestor(self) -> None:
        self.assertEqual(gcc.origin_sha("l1"), self.sha["l1"])
        self.assertIsNone(gcc.origin_sha("nope"))
        self.assertTrue(gcc.is_ancestor(self.sha["l1"], self.sha["l2"]))
        self.assertFalse(gcc.is_ancestor(self.sha["l2"], self.sha["l1"]))

    def test_merge_clean_detects_conflict_and_clean_merge(self) -> None:
        clean = gcc.merge_clean(self.sha["develop"], self.sha["l2"])
        conflict = gcc.merge_clean(self.sha["l1"], self.sha["fork"])
        if clean is None:
            self.skipTest("git < 2.38: merge-tree --write-tree unavailable (reported as unknown, as designed)")
        self.assertTrue(clean)
        self.assertFalse(conflict)

    def test_evaluate_end_to_end_on_real_refs(self) -> None:
        with mock.patch.object(gcc, "merge_clean", wraps=gcc.merge_clean):
            good = gcc.evaluate("develop", ["l1", "l2"], {}, fetched=True, use_pr=False)
            bad = gcc.evaluate("develop", ["l1", "fork"], {}, fetched=True, use_pr=False)
        self.assertTrue(good["linkable"], good["problems"])
        self.assertFalse(bad["linkable"])
        self.assertTrue(any("fork: does not contain parent l1" in p for p in bad["problems"]))
