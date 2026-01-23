#!/usr/bin/env python3
"""Preflight hook for the commit-push agent.

This hook runs before the commit-push agent starts and validates:
1. Protected branches are configured (or auto-detects from git-flow)
2. Git authentication is working

Exit codes:
- 0: Allow agent to proceed
- 2: Block agent execution
"""

import sys

# Ensure the scripts directory is in the path for imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from preflight_utils import run_preflight_check


def main() -> int:
    """Run preflight checks for commit-push agent."""
    return run_preflight_check("commit_push_agent_start")


if __name__ == "__main__":
    sys.exit(main())
