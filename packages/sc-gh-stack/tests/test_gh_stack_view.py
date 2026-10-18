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
from contextlib import contextmanager
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
        self.assertTrue(any("no recorded base SHA" in n and "docs/top" in n for n in notes))
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
        self.assertIn("coherence unknown", text)
        self.assertIn("note: L3 docs/top: no local head", text)

    def test_needs_rebase_and_base_mismatch_still_flagged(self) -> None:
        stack, prs = self.coherent_stack()
        stack["branches"][1] = layer("fix/middle", 2, head=B2, base=OLD, needs_rebase=True)
        _, problems, _ = gsv.build_rows(stack, prs, fetched=True)
        self.assertTrue(any("base ddddddddd != parent head aaaaaaaaa" in p for p in problems))
        self.assertTrue(any("parent edge indicates needsRebase" in p for p in problems))

    def test_summary_counts_and_prioritizes_hidden_stable_ci_failure(self):
        stack, prs = self.coherent_stack()
        rows, _, _ = gsv.build_rows(stack, prs, fetched=True)
        rows = [dict(rows[0], layer=n, pr=n, branch=f'branch/{n}', local_merge_clean=True, changed=True)
                for n in range(1, 121)]
        rows[-1]['ci'] = 'ERROR'
        text = gsv.render_table(stack, rows, [], [], {'landable': None, 'reason': 'fixture'}, trunk_origin=T0, coherent=True)
        self.assertIn('1 hosted/check blockers', text)
        self.assertIn('| 120/120 | #120 |', text)
        self.assertEqual(sum(line.startswith('| ') and '/120 |' in line for line in text.splitlines()), 10)


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
        self.assertEqual(gsv.sync_icon(rows[1]), gsv.ICON_SYNC["behind"], "behind a moved trunk is its own icon, not a rebase order")
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

    def test_merged_middle_resets_next_open_parent_to_trunk(self) -> None:
        stack, prs = self.merged_bottom_stack(middle_base=T1)
        stack['branches'][0]['isMerged'] = False
        stack['branches'][1]['isMerged'] = True
        stack['branches'][2]['base'] = T1
        prs[3]['baseRefName'] = TRUNK
        rows, problems, _ = gsv.build_rows(stack, prs, fetched=True)
        self.assertEqual(problems, [])
        self.assertEqual(rows[2]['expected_base'], T1)


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
        with mock.patch.object(gsv, "read_local_snapshot", side_effect=gsv.ToolError("worktree missing")), mock.patch.object(gsv, "run", side_effect=AssertionError("unexpected subprocess")):
            self.assertIsNone(gsv.stack_json_at("/wt/a"))
        with mock.patch.object(gsv, "read_local_snapshot", return_value={"stacks": [], "warnings": []}), mock.patch.object(gsv, "run", return_value=self._cp(1)):
            self.assertIsNone(gsv.stack_json_at("/wt/b"))
        joined = "\n".join(gsv.SKIPPED)
        self.assertIn("/wt/a: worktree missing", joined)
        self.assertNotIn("/wt/b", joined)
        gsv.SKIPPED.clear()

    def test_pr_details_partial_graphql_errors_warn_and_continue(self) -> None:
        client = mock.Mock()
        client.pr_details.return_value = {1: {"headRefOid": A1}, 2: {}}
        with mock.patch.object(gsv, "run", side_effect=AssertionError("render/acquisition wrapper must use shared client")):
            prs = gsv.pr_details([1, 2], client=client)
        self.assertEqual(prs[1]["headRefOid"], A1)
        self.assertEqual(prs[2], {}, "unresolved PR is falsy so rows render as unknown")
        client.pr_details.assert_called_once_with([1, 2], force=False, offline=False, head_map=None)

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


class ReviewRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        gsv.SKIPPED.clear()
        self.addCleanup(gsv.SKIPPED.clear)

    def test_unknown_recorded_bottom_base_does_not_order_rebase_for_moved_trunk(self):
        stack = {'trunk': TRUNK, 'branches': [layer('l1', 1, head=A1, base=None)]}
        refs = {f'refs/remotes/origin/{TRUNK}': T0, 'refs/remotes/origin/l1': A1}
        with mock.patch.object(gsv, 'is_ancestor', return_value=False):
            rows, problems, notes = gsv.build_rows(stack, {}, fetched=True, refs=refs)
        self.assertIsNone(rows[0]['needs_rebase'])
        self.assertIsNone(rows[0]['base_ok'])
        self.assertFalse(any('needsRebase' in problem or 'needs rebase' in problem for problem in problems))
        self.assertTrue(any('no recorded base SHA' in note for note in notes))

    def test_unknown_upper_recorded_base_still_checks_parent_containment(self):
        stack = {'trunk': TRUNK, 'branches': [layer('l1', 1, head=A1, base=None),
                                            layer('l2', 2, head=B2, base=None)]}
        refs = {f'refs/remotes/origin/{TRUNK}': T0, 'refs/remotes/origin/l1': A1,
                'refs/remotes/origin/l2': B2}
        with mock.patch.object(gsv, 'is_ancestor', return_value=False):
            rows, problems, _ = gsv.build_rows(stack, {}, fetched=True, refs=refs)
        self.assertIsNone(rows[0]['needs_rebase'])
        self.assertTrue(rows[1]['needs_rebase'])
        self.assertTrue(any('L2' in problem and 'needsRebase' in problem for problem in problems))

    @contextmanager
    def report_dependencies(self, warnings=(), fetch_error=None):
        stack = {"trunk": TRUNK, "worktree": None, "branches": [layer("l1", 1, head=A1, base=T0)]}
        snapshot = {"repository": {}, "refs": {'refs/heads/l1': A1}, "stacks": [stack], "warnings": list(warnings), "fingerprint": "epoch"}
        client = mock.Mock()
        client.cache_dir = Path('/unused-fixture-cache')
        client.path = client.cache_dir / 'remote.json'
        client.refresh_git.return_value = {"fresh": False, "source": "unknown", "observed_at": None, "error": fetch_error}
        client.pr_details.return_value = {}
        client.branch_observations = {}
        client.observations, client.metrics, client.warnings, client.snapshot_id = {}, {}, [fetch_error] if fetch_error else [], 'fixture'
        conflicts = {"layers": [{"branch": "l1", "base": T0, "head": A1, "clean": True, "reason": "clean"}], "combined": {"base": T0, "head": A1, "clean": True, "reason": "clean"}, "clean": True}
        with mock.patch.object(gsv, 'preflight'), mock.patch.object(gsv, 'read_local_snapshot', return_value=snapshot), mock.patch.object(gsv, 'StackDataClient', return_value=client), mock.patch.object(gsv, 'evaluate_stack_conflicts', return_value=conflicts), mock.patch.object(gsv, 'read_snapshot', return_value={}), mock.patch.object(gsv, 'write_snapshot'), mock.patch.object(gsv, 'run', side_effect=AssertionError('unexpected subprocess')):
            yield client

    def test_unresolved_pr_row_is_unknown_not_stale(self) -> None:
        stack = {"trunk": TRUNK, "currentBranch": "l1", "branches": [layer("l1", 1, head=A1, base=T0)]}
        with mock.patch.object(gsv, "origin_sha", side_effect=lambda ref: {TRUNK: T0, "l1": A1}.get(ref)), \
             mock.patch.object(gsv, "is_ancestor", return_value=False):
            rows, problems, notes = gsv.build_rows(stack, {1: {}}, fetched=True)
        self.assertEqual(problems, [])
        self.assertTrue(any("PR #1 could not be resolved" in n for n in notes))
        self.assertEqual(gsv.sync_icon(rows[0]), gsv.ICON_SYNC["unknown"])
        self.assertEqual(gsv.merge_icon(rows[0]), gsv.ICON_SYNC["unknown"])
        self.assertEqual(gsv.ci_icon(rows[0]), gsv.ICON_SYNC["unknown"])

    def test_needs_rebase_on_behind_trunk_bottom_is_a_note(self) -> None:
        stack = {"trunk": TRUNK, "currentBranch": "l1", "branches": [layer("l1", 1, head=A1, base=OLD, needs_rebase=True)]}
        with mock.patch.object(gsv, "origin_sha", side_effect=lambda ref: {TRUNK: T0, "l1": A1}.get(ref)), \
             mock.patch.object(gsv, "is_ancestor", side_effect=lambda a, b: (a, b) == (OLD, T0)):
            rows, problems, notes = gsv.build_rows(stack, {1: pr(A1, TRUNK)}, fetched=True)
        self.assertEqual(problems, [])
        self.assertTrue(any("needsRebase, but only against a trunk that moved" in n for n in notes))
        self.assertEqual(gsv.sync_icon(rows[0]), gsv.ICON_SYNC["behind"])

    def test_skipped_worktree_makes_report_exit_1_and_landing_unjudged(self) -> None:
        import io, subprocess
        stack = {"trunk": TRUNK, "currentBranch": "l1", "worktree": "/wt/l1",
                 "branches": [layer("l1", 1, head=A1, base=T0)]}
        args = gsv.argparse.Namespace(trunk=None, phase=None, all=False, no_fetch=True, no_pr=True, json=True)
        with self.report_dependencies(warnings=['/wt/top: catalog unreadable']), \
             mock.patch("builtins.print") as out, \
             mock.patch.object(gsv.sys, "stderr", new=io.StringIO()) as err:
            rc = gsv.run_report(args, None)
        self.assertEqual(rc, 1)
        payload = __import__("json").loads(out.call_args[0][0])
        self.assertFalse(payload["coherent"])
        self.assertIn("discovery incomplete", payload["stacks"][0]["problems"][0])
        self.assertIsNone(payload["stacks"][0]["landing"]["landable"])
        self.assertIn('/wt/top: catalog unreadable', payload['warnings'])

    def test_fetch_timeout_degrades_to_unknown(self) -> None:
        import io
        stack = {"trunk": TRUNK, "currentBranch": "l1", "worktree": "/wt/l1",
                 "branches": [layer("l1", 1, head=A1, base=T0)]}
        args = gsv.argparse.Namespace(trunk=None, phase=None, all=False, no_fetch=False, no_pr=True, json=False)
        with self.report_dependencies(fetch_error='git fetch timed out after 60s'), \
             mock.patch("builtins.print") as output, \
             mock.patch.object(gsv.sys, "stderr", new=io.StringIO()) as err:
            rc = gsv.run_report(args, None)
        self.assertEqual(rc, 1)
        self.assertIn('git fetch timed out', '\n'.join(str(call) for call in output.call_args_list))

    def test_default_text_unknown_coherence_is_not_green(self):
        args = gsv.argparse.Namespace(all=False, no_fetch=True, no_pr=True, json=False)
        with self.report_dependencies(), mock.patch('builtins.print') as output:
            gsv.run_report(args, None)
        text = '\n'.join(str(call.args[0]) for call in output.call_args_list)
        self.assertNotIn('VERDICT: ✅ COHERENT', text)
        self.assertIn('unknown', text.lower())

    def test_unknown_ci_icon_is_not_success(self):
        self.assertNotEqual(gsv.ci_icon({'ci': None, 'pr_unresolved': True}), gsv.ICON_CI['SUCCESS'])
        self.assertEqual(gsv.ci_icon({'ci': None, 'pr_unresolved': True}), gsv.ICON_SYNC['unknown'])

    def test_stale_successful_ci_and_unknown_merge_are_not_green(self):
        self.assertEqual(gsv.ci_icon({'ci': 'SUCCESS', 'hosted_stale': True}), gsv.ICON_SYNC['unknown'])
        self.assertEqual(gsv.merge_icon({'merged': False, 'mergeable': 'UNKNOWN', 'merge_state': 'UNKNOWN'}), gsv.ICON_SYNC['unknown'])
