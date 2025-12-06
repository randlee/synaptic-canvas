#!/usr/bin/env bash
set -euo pipefail

# Simple delay/poll script with minimal heartbeats.
# Supports one-shot (--seconds/--minutes) or polling (--every with --for or --attempts).

usage() {
  cat <<'USAGE'
Usage:
  scripts/delay-run.sh --seconds N [--action "text"]
  scripts/delay-run.sh --minutes N [--action "text"]
  scripts/delay-run.sh --every N --for M [--action "text"] [--suppress-action]
  scripts/delay-run.sh --every N --attempts K [--action "text"] [--suppress-action]

Notes:
  - Minimum wait: 10 seconds (one-shot); minimum interval: 60 seconds (polling)
  - Maximum duration: 12 hours
  - Heartbeat prints "Waiting Xm..." each minute/interval (or seconds for short waits)
  - Final line always: "Action: <text>" (or (none specified)) unless --suppress-action is used
USAGE
}

seconds=""
interval=""
max_duration=""
max_attempts=""
action=""
suppress_action="false"

until_val=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --seconds)
      seconds="$2"; shift 2;;
    --minutes)
      seconds=$(( $2 * 60 )); shift 2;;
    --every)
      interval="$2"; shift 2;;
    --for)
      max_duration="$2"; shift 2;;
    --attempts)
      max_attempts="$2"; shift 2;;
    --action)
      action="$2"; shift 2;;
    --suppress-action)
      suppress_action="true"; shift 1;;
    --until)
      until_val="$2"; shift 2;;
    --help|-h)
      usage; exit 0;;
    *)
      echo "Unknown arg: $1" >&2; usage; exit 1;;
  esac
done

# Validate one-shot vs polling
if [[ -n "$seconds" && -n "$interval" ]]; then
  echo "Cannot combine one-shot and polling." >&2; exit 1;
fi
if [[ -z "$seconds" && -z "$interval" && -z "$until_val" ]]; then
  echo "Must specify --seconds/--minutes, --until, or --every." >&2; exit 1;
fi

# One-shot
if [[ -n "$seconds" ]]; then
  if [[ "$seconds" -lt 10 ]]; then echo "Duration too short" >&2; exit 1; fi
  if [[ "$seconds" -gt 43200 ]]; then echo "Duration too long" >&2; exit 1; fi
  if [[ "$seconds" -lt 60 ]]; then
    echo "Waiting ${seconds} seconds..."
    sleep "$seconds"
  else
    rem="$seconds"
    while [[ "$rem" -ge 60 ]]; do
      mins=$(( rem / 60 ))
      echo "Waiting ${mins} minutes..."
      sleep 60
      rem=$(( rem - 60 ))
    done
    if [[ "$rem" -gt 0 ]]; then
      echo "Waiting ${rem} seconds..."
      sleep "$rem"
    fi
  fi
  if [[ "$suppress_action" != "true" ]]; then
    echo "Action: ${action:-"(none specified)"}"
  fi
  exit 0
fi

# One-shot via until
if [[ -n "$until_val" ]]; then
  seconds=$(python3 - <<PY
import sys, datetime
val = sys.argv[1]
now = datetime.datetime.now()
try:
    # HH:MM or HH:MM:SS local
    parts = [int(p) for p in val.split(":")]
    if len(parts) == 2:
        target = now.replace(hour=parts[0], minute=parts[1], second=0, microsecond=0)
    elif len(parts) == 3:
        target = now.replace(hour=parts[0], minute=parts[1], second=parts[2], microsecond=0)
    else:
        raise ValueError
    if target <= now:
        target = target + datetime.timedelta(days=1)
except Exception:
    try:
        target = datetime.datetime.fromisoformat(val)
        if target.tzinfo is None:
            target = target.replace(tzinfo=None)
    except Exception:
        print("INVALID", file=sys.stderr)
        sys.exit(1)
delta = target - now
seconds = int(delta.total_seconds())
print(seconds)
PY
)
  if [[ "$seconds" == "INVALID" ]]; then echo "Invalid --until format" >&2; exit 1; fi
  if [[ "$seconds" -lt 10 ]]; then echo "Duration too short" >&2; exit 1; fi
  if [[ "$seconds" -gt 43200 ]]; then echo "Duration too long" >&2; exit 1; fi
  rem="$seconds"
  if [[ "$rem" -lt 60 ]]; then
    echo "Waiting ${rem} seconds..."
    sleep "$rem"
  else
    while [[ "$rem" -ge 60 ]]; do
      mins=$(( rem / 60 ))
      echo "Waiting ${mins} minutes..."
      sleep 60
      rem=$(( rem - 60 ))
    done
    if [[ "$rem" -gt 0 ]]; then
      echo "Waiting ${rem} seconds..."
      sleep "$rem"
    fi
  fi
  if [[ "$suppress_action" != "true" ]]; then
    echo "Action: ${action:-"(none specified)"}"
  fi
  exit 0
fi

# Polling
if [[ -n "$interval" ]]; then
  if [[ "$interval" -lt 60 ]]; then echo "Interval too short" >&2; exit 1; fi
  if [[ -z "$max_duration" && -z "$max_attempts" ]]; then
    echo "Polling requires --for <duration> or --attempts <count>." >&2; exit 1;
  fi
  # Convert duration to attempts if provided
  attempts="$max_attempts"
  if [[ -n "$max_duration" ]]; then
    total=$max_duration
    if [[ "$total" =~ m$ ]]; then
      total=${total%m}
      total=$(( total * 60 ))
    fi
    if [[ "$total" =~ s$ ]]; then
      total=${total%s}
    fi
    if [[ "$total" -gt 43200 ]]; then echo "Duration too long" >&2; exit 1; fi
    attempts=$(( total / interval ))
  fi
  if [[ -z "$attempts" || "$attempts" -lt 1 ]]; then
    echo "Invalid attempts" >&2; exit 1;
  fi
  for ((i=0; i<attempts; i++)); do
    mins=$(( interval / 60 ))
    echo "Waiting ${mins} minutes..."
    sleep "$interval"
  done
  if [[ "$suppress_action" != "true" ]]; then
    echo "Action: ${action:-"(none specified)"}"
  fi
fi
