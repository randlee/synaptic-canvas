#!/usr/bin/env python3
"""
Python rewrite of packages/sc-delay-tasks/scripts/sc-delay-run.py

Features:
- one-shot delay: --seconds N | --minutes N | --until <HH:MM[:SS]|ISO>
- polling: --every N --for <Xs|Xm> | --every N --attempts K
- optional: --action TEXT and --suppress-action

Output format mirrors the Bash script:
- Heartbeats: "Waiting X minutes..." (for minute intervals) or "Waiting X seconds..."
- Final line (unless suppressed): "Action: <text>" or "Action: (none specified)"
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Callable, Optional


MAX_SECONDS = 12 * 60 * 60  # 12 hours


def _heartbeat_wait(total_seconds: int, *, sleep: Callable[[float], None] = time.sleep, out=print) -> None:
    if total_seconds < 60:
        out(f"Waiting {total_seconds} seconds...")
        sleep(total_seconds)
        return
    rem = total_seconds
    while rem >= 60:
        mins = rem // 60
        out(f"Waiting {mins} minutes...")
        sleep(60)
        rem -= 60
    if rem > 0:
        out(f"Waiting {rem} seconds...")
        sleep(rem)


def _parse_until(value: str) -> int:
    now = datetime.now()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", value)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2))
        s = int(m.group(3) or 0)
        target = now.replace(hour=h, minute=mi, second=s, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)
        return int((target - now).total_seconds())
    # Try ISO 8601 via fromisoformat (naive treated as local)
    try:
        target = datetime.fromisoformat(value)
    except Exception as e:  # noqa: BLE001
        raise ValueError("invalid --until format") from e
    if target <= now:
        raise ValueError("--until must be in the future")
    return int((target - now).total_seconds())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=True)
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--seconds", type=int)
    g.add_argument("--minutes", type=int)
    g.add_argument("--until", type=str)

    # Polling requires --every and one of --for / --attempts
    p.add_argument("--every", type=int, help="Polling interval in seconds")
    p.add_argument("--for", dest="for_duration", type=str, help="Total duration (e.g., 5m or 120s)")
    p.add_argument("--attempts", type=int)

    p.add_argument("--action", type=str, default="")
    p.add_argument("--suppress-action", action="store_true")
    return p


def _print_action(action: str, suppress: bool, out=print) -> None:
    if not suppress:
        out(f"Action: {action if action else '(none specified)'}")


def _validate_bounds(seconds: int) -> None:
    if seconds < 10:
        raise ValueError("Duration too short")
    if seconds > MAX_SECONDS:
        raise ValueError("Duration too long")


def _parse_duration_token(s: str) -> int:
    """Parse tokens like '5m' or '120s' into seconds."""
    m = re.fullmatch(r"(\d+)([ms])", s)
    if not m:
        raise ValueError("Invalid duration format (use <Ns> or <Nm>)")
    val = int(m.group(1))
    unit = m.group(2)
    return val * 60 if unit == "m" else val


def main(argv: Optional[list[str]] = None, *, _sleep=time.sleep, _out=print, _err=lambda *a, **k: print(*a, file=sys.stderr, **k)) -> int:
    args = build_parser().parse_args(argv)

    # Resolve seconds for one-shot or until
    seconds: Optional[int] = None
    if args.seconds is not None or args.minutes is not None:
        if args.seconds is not None and args.minutes is not None:
            _err("Cannot combine one-shot and polling.")
            return 1
        seconds = args.seconds if args.seconds is not None else args.minutes * 60
    elif args.until is not None:
        try:
            seconds = _parse_until(args.until)
        except ValueError as e:
            _err(str(e) if str(e) else "Invalid --until format")
            return 1

    interval = args.every

    if seconds is None and interval is None:
        _err("Must specify --seconds/--minutes, --until, or --every.")
        return 1

    # One-shot
    if seconds is not None and interval is not None:
        _err("Cannot combine one-shot and polling.")
        return 1

    if seconds is not None:
        try:
            _validate_bounds(seconds)
        except ValueError as e:
            _err(str(e))
            return 1
        _heartbeat_wait(seconds, sleep=_sleep, out=_out)
        _print_action(args.action, args.suppress_action, out=_out)
        return 0

    # Polling
    if interval is not None:
        if interval < 60:
            _err("Interval too short")
            return 1
        attempts: Optional[int] = args.attempts
        if args.for_duration:
            try:
                total = _parse_duration_token(args.for_duration)
            except ValueError as e:
                _err(str(e))
                return 1
            if total > MAX_SECONDS:
                _err("Duration too long")
                return 1
            attempts = total // interval
        if not attempts or attempts < 1:
            _err("Invalid attempts")
            return 1
        mins = interval // 60
        for _ in range(attempts):
            _out(f"Waiting {mins} minutes...")
            _sleep(interval)
        _print_action(args.action, args.suppress_action, out=_out)
        return 0

    _err("Invalid arguments")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
