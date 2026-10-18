import sys
from pathlib import Path

# Ensure src/ is importable for 'sc_cli'
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CODEX_SCRIPTS = ROOT / "packages" / "sc-codex" / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(CODEX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CODEX_SCRIPTS))


# Tests write to temp folders, never into the checkout. Package logs follow
# `.claude/state/logs/<package>/` under CLAUDE_PROJECT_DIR or cwd, so a test that
# forgets to isolate them leaves files here; the session fails if any appear.
REPO_LOGS = ROOT / ".claude" / "state" / "logs"


def _repo_log_files() -> set:
    return {p for p in REPO_LOGS.rglob("*") if p.is_file()} if REPO_LOGS.is_dir() else set()


def pytest_sessionstart(session):
    session.config._sc_repo_logs_before = _repo_log_files()


def pytest_sessionfinish(session, exitstatus):
    before = getattr(session.config, "_sc_repo_logs_before", None)
    if before is None:
        return
    created = sorted(str(p.relative_to(ROOT)) for p in _repo_log_files() - before)
    if created:
        session.config.get_terminal_writer().line(
            "Tests wrote into the checkout (isolate them under tmp_path):\n  " + "\n  ".join(created),
            red=True,
        )
        session.exitstatus = 1
