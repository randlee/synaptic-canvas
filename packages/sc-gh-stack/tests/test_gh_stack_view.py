"""Regression tests for gh_stack_view.build_rows against gh-stack JSON shapes,
plus select_stacks (the generalized trunk-selection logic for sc-gh-stack-view).

gh-stack v0.1.0 omits ``head``/``base`` for a layer whose branch is not present
locally (viewed from a sibling worktree before fetch).  The report must degrade
to ❓/notes for that layer, never raise.  Runs under pytest and standalone with
``python3 -m unittest``.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gh_stack_view.py"
spec = importlib.util.spec_from_file_location("gh_stack_view_under_test", SCRIPT)
assert spec is not None and spec.loader is not None
gsv = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gsv
spec.loader.exec_module(gsv)

TRUNK = "integrate/phase-ax"
T0 = "0" * 40
A1 = "a" * 40
B2 = "b" * 40
C3 = "c" * 40
OLD = "d" * 40


def layer(name: str, pr: int, *, head: str | None, base: str | None, needs_rebase: bool = False) -> dict:
    entry = {"name": name, "isCurrent": False, "isMerged": False, "isQueued": False,
             "needsRebase": needs_rebase, "pr": {"number": pr, "state": "OPEN"}}
    if head is not None:
        entry["head"] = head
    if base is not None:
        entry["base"] = base
    return entry


def pr(head: str, base: str, *, mergeable: str = "MERGEABLE", state: str = "CLEAN") -> dict:
    return {"headRefOid": head, "baseRefName": base, "mergeable": mergeable,
            "mergeStateStatus": state, "isDraft": False, "ci": "SUCCESS"}


class BuildRowsShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.origins = {TRUNK: T0, "fix/bottom": A1, "fix/middle": B2, "docs/top": C3}
        patches = [
            mock.patch.object(gsv, "origin_sha", side_effect=lambda ref: self.origins.get(ref)),
            mock.patch.object(gsv, "is_ancestor", return_value=False),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def coherent_stack(self) -> tuple[dict, dict]:
        stack = {"trunk": TRUNK, "currentBranch": "fix/bottom", "branches": [
            layer("fix/bottom", 1, head=A1, base=T0),
            layer("fix/middle", 2, head=B2, base=A1),
            layer("docs/top", 3, head=C3, base=B2),
        ]}
        prs = {1: pr(A1, TRUNK), 2: pr(B2, "fix/bottom"), 3: pr(C3, "fix/middle")}
        return stack, prs

    def test_full_shape_is_coherent(self) -> None:
        stack, prs = self.coherent_stack()
        rows, problems, notes = gsv.build_rows(stack, prs, fetched=True)
        self.assertEqual(problems, [])
        self.assertEqual(notes, [])
        self.assertEqual([gsv.sync_icon(r) for r in rows], [gsv.ICON_SYNC["ok"]] * 3)

    def test_missing_head_and_base_keys_do_not_crash(self) -> None:
        # Regression: gh stack view --json returned layers without head/base;
        # build_rows raised KeyError('head') while formatting the origin problem.
        stack, prs = self.coherent_stack()
        stack["branches"][1] = layer("fix/middle", 2, head=None, base=None)
        stack["branches"][2] = layer("docs/top", 3, head=None, base=None)
        rows, problems, notes = gsv.build_rows(stack, prs, fetched=True)
        self.assertEqual(problems, [], "remote side (origin == PR head) is coherent, so no problems")
        self.assertTrue(any("no local head" in n and "fix/middle" in n for n in notes))
        self.assertTrue(any("no base SHA" in n and "docs/top" in n for n in notes))
        self.assertIsNone(rows[1]["head"])
        self.assertIsNone(rows[1]["base"])
        self.assertIsNone(rows[1]["base_ok"])
        self.assertEqual(gsv.sync_icon(rows[1]), gsv.ICON_SYNC["unknown"])

    def test_missing_head_with_stale_pr_is_reported_not_raised(self) -> None:
        stack, prs = self.coherent_stack()
        stack["branches"][2] = layer("docs/top", 3, head=None, base=B2)
        prs[3] = pr(OLD, "fix/middle")  # PR head differs from origin -> stale push
        rows, problems, _ = gsv.build_rows(stack, prs, fetched=True)
        self.assertEqual(len(problems), 1)
        self.assertIn("docs/top", problems[0])
        self.assertIn("local - / origin ccccccccc / PR ddddddddd differ", problems[0])
        self.assertEqual(gsv.sync_icon(rows[2]), gsv.ICON_SYNC["stale"])

    def test_missing_head_falls_back_to_pr_head_for_next_layer_base(self) -> None:
        stack, prs = self.coherent_stack()
        stack["branches"][0] = layer("fix/bottom", 1, head=None, base=T0)
        self.origins["fix/bottom"] = None  # not fetched either
        rows, problems, _ = gsv.build_rows(stack, prs, fetched=True)
        self.assertEqual(problems, [])
        self.assertEqual(rows[1]["expected_base"], A1)

    def test_no_fetch_marks_unknown_without_raising(self) -> None:
        stack, prs = self.coherent_stack()
        stack["branches"][2] = layer("docs/top", 3, head=None, base=None)
        rows, problems, _ = gsv.build_rows(stack, prs, fetched=False)
        self.assertEqual(problems, [])
        self.assertEqual(gsv.sync_icon(rows[2]), gsv.ICON_SYNC["unknown"])

    def test_render_table_handles_missing_head(self) -> None:
        stack, prs = self.coherent_stack()
        stack["branches"][2] = layer("docs/top", 3, head=None, base=None)
        rows, problems, notes = gsv.build_rows(stack, prs, fetched=True)
        landing = {"landable": None, "reason": "no open layer or trunk not fetched"}
        text = gsv.render_table(stack, rows, problems, notes, landing, trunk_origin=T0)
        self.assertIn("VERDICT: ✅ COHERENT", text)
        self.assertIn("note: L3 docs/top: gh stack reported no local head", text)

    def test_needs_rebase_and_base_mismatch_still_flagged(self) -> None:
        stack, prs = self.coherent_stack()
        stack["branches"][1] = layer("fix/middle", 2, head=B2, base=OLD, needs_rebase=True)
        _, problems, _ = gsv.build_rows(stack, prs, fetched=True)
        self.assertTrue(any("base ddddddddd != parent head aaaaaaaaa" in p for p in problems))
        self.assertTrue(any("gh stack reports needsRebase" in p for p in problems))


T1 = "1" * 40  # trunk head after the bottom layer merged


class MergedBottomLayerTests(unittest.TestCase):
    """Regression: after ``gh stack merge``/merge-async lands the bottom layer,
    GitHub retargets the next layer onto the trunk.  The report used to demand
    that layer be based on the MERGED branch (PR base and base SHA), producing
    two false problems on a stack gh-stack itself reported as needsRebase=false."""

    def setUp(self) -> None:
        # Trunk moved from T0 to T1 (the merge commit of the bottom layer).
        self.origins = {TRUNK: T1, "fix/bottom": A1, "fix/middle": B2, "docs/top": C3}
        self.ancestors = {(T0, T1), (A1, T1)}
        patches = [
            mock.patch.object(gsv, "origin_sha", side_effect=lambda ref: self.origins.get(ref)),
            mock.patch.object(gsv, "is_ancestor", side_effect=lambda a, b: (a, b) in self.ancestors),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def merged_bottom_stack(self, *, middle_base: str, middle_pr_base: str = TRUNK) -> tuple[dict, dict]:
        bottom = layer("fix/bottom", 1, head=A1, base=T0)
        bottom["isMerged"] = True
        bottom["pr"]["state"] = "MERGED"
        stack = {"trunk": TRUNK, "currentBranch": "docs/top", "branches": [
            bottom,
            layer("fix/middle", 2, head=B2, base=middle_base),
            layer("docs/top", 3, head=C3, base=B2),
        ]}
        prs = {1: pr(A1, TRUNK, state="MERGED"), 2: pr(B2, middle_pr_base), 3: pr(C3, "fix/middle")}
        return stack, prs

    def test_layer_above_merged_bottom_is_judged_against_trunk(self) -> None:
        # gh stack reports the retargeted layer's base as the pre-merge trunk
        # commit (T0), an ancestor of the new trunk head: behind trunk, not a rebase.
        stack, prs = self.merged_bottom_stack(middle_base=T0)
        rows, problems, notes = gsv.build_rows(stack, prs, fetched=True)
        self.assertEqual(problems, [], problems)
        self.assertEqual(len(notes), 1)
        self.assertIn("L2 fix/middle: behind trunk", notes[0])
        self.assertEqual(gsv.sync_icon(rows[0]), gsv.ICON_MERGE["MERGED"])
        self.assertEqual(gsv.sync_icon(rows[1]), gsv.ICON_SYNC["rebase"], "behind trunk still shows the rebase icon")
        self.assertEqual(gsv.sync_icon(rows[2]), gsv.ICON_SYNC["ok"])
        self.assertEqual(rows[1]["expected_base"], T1, "expected base is the trunk head, not the merged layer's head")

    def test_layer_above_merged_bottom_on_trunk_head_is_clean(self) -> None:
        stack, prs = self.merged_bottom_stack(middle_base=T1)
        rows, problems, notes = gsv.build_rows(stack, prs, fetched=True)
        self.assertEqual(problems, [])
        self.assertEqual(notes, [])
        self.assertEqual([gsv.sync_icon(r) for r in rows[1:]], [gsv.ICON_SYNC["ok"]] * 2)

    def test_layer_above_merged_bottom_still_targeting_merged_branch_is_flagged(self) -> None:
        # GitHub has not retargeted the PR yet: that IS a problem the owner must fix.
        stack, prs = self.merged_bottom_stack(middle_base=T1, middle_pr_base="fix/bottom")
        _rows, problems, _notes = gsv.build_rows(stack, prs, fetched=True)
        self.assertEqual(len(problems), 1)
        self.assertIn("PR #2 base is fix/bottom, expected integrate/phase-ax", problems[0])

    def test_open_parent_mismatch_is_still_a_problem(self) -> None:
        # Above an OPEN layer the ancestor leniency must not apply.
        stack, prs = self.merged_bottom_stack(middle_base=T1)
        stack["branches"][2]["base"] = OLD
        self.ancestors.add((OLD, B2))
        _rows, problems, _notes = gsv.build_rows(stack, prs, fetched=True)
        self.assertEqual(len(problems), 1)
        self.assertIn("L3 docs/top: base ddddddddd != parent head bbbbbbbbb -> needs rebase", problems[0])


def found_stack(trunk: str, branch: str, pr_num: int, *, merged: bool = False, closed: bool = False) -> dict:
    """Minimal deduped ``found`` entry: one layer is enough for select_stacks,
    which only inspects trunk and branch-open state."""
    state = "MERGED" if merged else ("CLOSED" if closed else "OPEN")
    return {
        "trunk": trunk,
        "worktree": f"/tmp/{branch}",
        "branches": [{"name": branch, "isMerged": merged, "isQueued": False,
                      "needsRebase": False, "pr": {"number": pr_num, "state": state}}],
    }


class SelectStacksTests(unittest.TestCase):
    def test_default_keeps_open_stacks_on_any_trunk(self) -> None:
        found = [
            found_stack("develop", "fix/a", 1),
            found_stack("integrate/phase-bc", "fix/b", 2),
            found_stack("main", "fix/c", 3),
        ]
        stacks, hidden = gsv.select_stacks(found, None, include_all=False)
        self.assertEqual({s["trunk"] for s in stacks}, {"develop", "integrate/phase-bc", "main"})
        self.assertEqual(hidden, 0)

    def test_default_hides_fully_merged_stack_and_counts_it_hidden(self) -> None:
        found = [
            found_stack("develop", "fix/a", 1),
            found_stack("develop", "fix/merged", 2, merged=True),
        ]
        stacks, hidden = gsv.select_stacks(found, None, include_all=False)
        self.assertEqual([s["branches"][0]["name"] for s in stacks], ["fix/a"])
        self.assertEqual(hidden, 1)

    def test_trunk_filter_keeps_only_matching_trunk(self) -> None:
        found = [
            found_stack("develop", "fix/a", 1),
            found_stack("integrate/phase-bc", "fix/b", 2),
            found_stack("integrate/phase-bc", "fix/c", 3),
        ]
        stacks, hidden = gsv.select_stacks(found, "integrate/phase-bc", include_all=False)
        self.assertEqual({s["trunk"] for s in stacks}, {"integrate/phase-bc"})
        self.assertEqual(len(stacks), 2)
        self.assertEqual(hidden, 1)

    def test_include_all_keeps_merged_stacks(self) -> None:
        found = [
            found_stack("develop", "fix/a", 1),
            found_stack("develop", "fix/merged", 2, merged=True),
            found_stack("main", "fix/closed", 3, closed=True),
        ]
        stacks, hidden = gsv.select_stacks(found, None, include_all=True)
        self.assertEqual(len(stacks), 3)
        self.assertEqual(hidden, 0)

    def test_include_all_with_trunk_filter_still_filters_trunk(self) -> None:
        found = [
            found_stack("develop", "fix/a", 1, merged=True),
            found_stack("main", "fix/b", 2, merged=True),
        ]
        stacks, hidden = gsv.select_stacks(found, "develop", include_all=True)
        self.assertEqual([s["trunk"] for s in stacks], ["develop"])
        self.assertEqual(hidden, 1)


if __name__ == "__main__":
    unittest.main()


class ErrorConditionTests(unittest.TestCase):
    def _cp(self, rc: int, out: str = "", err: str = ""):
        import subprocess
        return subprocess.CompletedProcess(["x"], rc, stdout=out, stderr=err)

    def test_merge_tree_usage_error_is_not_judged_as_conflict(self) -> None:
        rows = [{"branch": "top", "origin": C3, "merged": False}]
        with mock.patch.object(gsv, "is_ancestor", return_value=True), \
             mock.patch.object(gsv, "run", return_value=self._cp(129, err="usage: git merge-tree")):
            landing = gsv.landing_verdict({"trunk": TRUNK}, rows, T0)
        self.assertIsNone(landing["landable"])
        self.assertIn("git < 2.38", landing["reason"])

    def test_merge_tree_conflict_is_reported(self) -> None:
        rows = [{"branch": "top", "origin": C3, "merged": False}]
        with mock.patch.object(gsv, "is_ancestor", return_value=True), \
             mock.patch.object(gsv, "run", return_value=self._cp(1, out="CONFLICT (content): x.rs")):
            landing = gsv.landing_verdict({"trunk": TRUNK}, rows, T0)
        self.assertFalse(landing["landable"])
        self.assertIn("CONFLICT (content): x.rs", landing["reason"])

    def test_stack_json_at_records_unreadable_worktrees(self) -> None:
        gsv.SKIPPED.clear()
        with mock.patch.object(gsv, "run", return_value=self._cp(6, err="branch belongs to multiple stacks")):
            self.assertIsNone(gsv.stack_json_at("/wt/a"))
        with mock.patch.object(gsv, "run", return_value=self._cp(2, err="not in a stack")):
            self.assertIsNone(gsv.stack_json_at("/wt/b"))
        with mock.patch.object(gsv, "run", return_value=self._cp(0, out="not json")):
            self.assertIsNone(gsv.stack_json_at("/wt/c"))
        joined = "\n".join(gsv.SKIPPED)
        self.assertIn("/wt/a: gh stack view exit 6", joined)
        self.assertIn("gh stack checkout <specific-branch>", joined)
        self.assertNotIn("/wt/b", joined, "exit 2 (not in a stack) is normal and not reported")
        self.assertIn("/wt/c: gh stack view --json returned non-JSON", joined)
        gsv.SKIPPED.clear()

    def test_pr_details_partial_graphql_errors_warn_and_continue(self) -> None:
        import io
        repo = self._cp(0, out='{"owner": {"login": "o"}, "name": "r"}')
        payload = {"data": {"repository": {"pr1": {"number": 1, "headRefOid": A1}, "pr2": None}},
                   "errors": [{"message": "Could not resolve to a PullRequest with the number of 2."}]}
        gql = self._cp(0, out=__import__("json").dumps(payload))
        with mock.patch.object(gsv, "run", side_effect=[repo, gql]), \
             mock.patch.object(gsv.sys, "stderr", new=io.StringIO()) as err:
            prs = gsv.pr_details([1, 2])
        self.assertEqual(prs[1]["headRefOid"], A1)
        self.assertEqual(prs[2]["ci"], "NONE")
        self.assertIn("warning: GraphQL reported", err.getvalue())

    def test_pr_details_rejects_non_int_numbers(self) -> None:
        repo = self._cp(0, out='{"owner": {"login": "o"}, "name": "r"}')
        with mock.patch.object(gsv, "run", return_value=repo):
            with self.assertRaises(gsv.ToolError):
                gsv.pr_details([1, "2; mutation"])  # type: ignore[list-item]

    def test_guarded_never_tracebacks(self) -> None:
        import io
        with mock.patch.object(gsv.sys, "stderr", new=io.StringIO()) as err:
            self.assertEqual(gsv.guarded("gh-stack-view", lambda: (_ for _ in ()).throw(KeyError("pr"))), 2)
        self.assertTrue(err.getvalue().startswith("gh-stack-view: unexpected KeyError"))
