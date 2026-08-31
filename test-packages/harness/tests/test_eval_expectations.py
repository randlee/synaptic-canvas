"""Unit tests for the eval-bridge expectation types.

Covers the five types added so plugin eval graders (packages/*/evals/) can run
under this harness: output_not_contains, file_contains, file_not_contains,
tool_order, llm_judge.
"""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from harness.collector import ClaudeResponseText, CollectedData, CorrelatedToolCall
from harness.models import ExpectationType, TestStatus
from harness.reporter import ExpectationEvaluator


def _data(commands: list[str] = (), last_message: str = "", cwd: str | None = None) -> CollectedData:
    now = datetime.now()
    return CollectedData(
        cwd=cwd,
        tool_calls=[
            CorrelatedToolCall(
                tool_use_id=f"tool-{i}",
                tool_name="Bash",
                tool_input={"command": c},
                pre_timestamp=now,
                post_timestamp=now,
            )
            for i, c in enumerate(commands)
        ],
        claude_responses=[ClaudeResponseText(text=last_message)] if last_message else [],
    )


def _eval(data, exp_type, expected, exp_id="exp-001", description="d"):
    return ExpectationEvaluator(data).evaluate(
        expectation_id=exp_id,
        expectation_type=exp_type,
        description=description,
        expected=expected,
    )


class TestOutputNotContains:
    def test_passes_when_pattern_absent(self):
        r = _eval(_data(last_message="the stack is diverged"),
                  ExpectationType.OUTPUT_NOT_CONTAINS,
                  {"pattern": "successfully synced", "flags": "i"})
        assert r.status == TestStatus.PASS

    def test_fails_when_pattern_present(self):
        r = _eval(_data(last_message="Successfully synced all branches"),
                  ExpectationType.OUTPUT_NOT_CONTAINS,
                  {"pattern": "successfully synced", "flags": "i"})
        assert r.status == TestStatus.FAIL
        assert "forbidden" in r.failure_reason


class TestFileContains:
    def test_contains_and_not_contains(self, tmp_path):
        (tmp_path / "gh-calls.log").write_text("gh stack view --json\nMERGE-SUBSET\n")
        d = _data(cwd=str(tmp_path))
        assert _eval(d, ExpectationType.FILE_CONTAINS,
                     {"path": "gh-calls.log", "pattern": "stack view"}).status == TestStatus.PASS
        r = _eval(d, ExpectationType.FILE_NOT_CONTAINS,
                  {"path": "gh-calls.log", "pattern": "MERGE-SUBSET"})
        assert r.status == TestStatus.FAIL and "MERGE-SUBSET" in r.failure_reason

    def test_missing_file_fails_contains_passes_not_contains(self, tmp_path):
        d = _data(cwd=str(tmp_path))
        assert _eval(d, ExpectationType.FILE_CONTAINS,
                     {"path": "nope.log", "pattern": "x"}).status == TestStatus.FAIL
        assert _eval(d, ExpectationType.FILE_NOT_CONTAINS,
                     {"path": "nope.log", "pattern": "x"}).status == TestStatus.PASS


class TestToolOrder:
    def test_correct_order_passes(self):
        d = _data(commands=["gh stack view --json", "gh stack merge --yes"])
        r = _eval(d, ExpectationType.TOOL_ORDER,
                  {"before": "stack view --json", "after": "stack merge"})
        assert r.status == TestStatus.PASS
        assert r.actual == {"before_index": 0, "after_index": 1}

    def test_wrong_order_fails(self):
        d = _data(commands=["gh stack merge --yes", "gh stack view --json"])
        r = _eval(d, ExpectationType.TOOL_ORDER,
                  {"before": "stack view --json", "after": "stack merge"})
        assert r.status == TestStatus.FAIL and "index" in r.failure_reason

    def test_missing_side_fails_with_named_side(self):
        d = _data(commands=["gh stack merge --yes"])
        r = _eval(d, ExpectationType.TOOL_ORDER,
                  {"before": "stack view --json", "after": "stack merge"})
        assert r.status == TestStatus.FAIL and "'before'" in r.failure_reason


class TestLlmJudge:
    def _judge_result(self, verdict: str) -> MagicMock:
        proc = MagicMock()
        proc.stdout = json.dumps({"result": verdict})
        return proc

    def test_pass_verdict(self):
        d = _data(last_message="I refused to merge; #148 is not in the stack.")
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", return_value=self._judge_result("PASS: refused subset")):
            r = _eval(d, ExpectationType.LLM_JUDGE, {"criteria": "must refuse subset merge"})
        assert r.status == TestStatus.PASS
        assert r.actual["verdict"].startswith("PASS")

    def test_fail_verdict_carries_reason(self):
        d = _data(last_message="Merged #149.")
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", return_value=self._judge_result("FAIL: merged the subset")):
            r = _eval(d, ExpectationType.LLM_JUDGE, {"criteria": "must refuse subset merge"})
        assert r.status == TestStatus.FAIL and "judge: FAIL" in r.failure_reason

    def test_missing_cli_fails_closed(self):
        with patch("shutil.which", return_value=None):
            r = _eval(_data(last_message="x"), ExpectationType.LLM_JUDGE, {"criteria": "c"})
        assert r.status == TestStatus.FAIL and "not on PATH" in r.failure_reason
