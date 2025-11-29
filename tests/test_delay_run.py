from __future__ import annotations

import builtins
from typing import List

from sc_cli import delay_run


def test_one_shot_minutes_heartbeats_and_action():
    lines: List[str] = []

    def _out(msg: str):
        lines.append(msg)

    def _sleep(_sec: float):
        pass

    rc = delay_run.main(["--minutes", "2", "--action", "go"], _sleep=_sleep, _out=_out)
    assert rc == 0
    assert "Waiting 2 minutes..." in lines
    assert "Waiting 1 minutes..." in lines
    assert lines[-1] == "Action: go"


def test_until_invalid_exits_nonzero(capsys):
    rc = delay_run.main(["--until", "not-a-time"], _sleep=lambda s: None)
    assert rc == 1
    err = capsys.readouterr().err
    assert "invalid --until format" in err or "Invalid --until format" in err


def test_polling_for_duration_loops_correct_times():
    sleeps: List[float] = []
    lines: List[str] = []

    def _sleep(sec: float):
        sleeps.append(sec)

    def _out(msg: str):
        lines.append(msg)

    rc = delay_run.main(["--every", "60", "--for", "5m", "--action", "done"], _sleep=_sleep, _out=_out)
    assert rc == 0
    assert sleeps == [60, 60, 60, 60, 60]
    assert lines.count("Waiting 1 minutes...") == 5
    assert lines[-1] == "Action: done"


def test_errors_for_short_durations_and_intervals(capsys):
    assert delay_run.main(["--seconds", "5"], _sleep=lambda s: None) == 1
    assert "Duration too short" in capsys.readouterr().err
    assert delay_run.main(["--every", "30", "--attempts", "2"], _sleep=lambda s: None) == 1
    assert "Interval too short" in capsys.readouterr().err
