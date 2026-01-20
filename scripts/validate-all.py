#!/usr/bin/env python3
"""
validate-all.py - Run complete validation suite for Synaptic Canvas

Usage:
  python3 scripts/validate-all.py [--quick] [--verbose] [--json]

Options:
  --quick       Skip unit tests (pytest), run validators only
  --verbose     Show detailed output from each validator
  --json        Output results as JSON (for machine parsing)
  --help        Show this help message

Exit Codes:
  0: All validations passed
  1: One or more validations failed

Validators run:
  - validate-agents.py: Agent frontmatter/registry consistency
  - validate-cross-references.py: Cross-reference integrity
  - validate-frontmatter-schema.py: Frontmatter schema validation
  - validate-manifest-artifacts.py: Manifest artifact validation
  - validate-marketplace-sync.py: Marketplace sync validation
  - validate-script-references.py: Script reference validation
  - pytest tests/ (unless --quick): Unit tests
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ValidatorResult:
    """Result from running a single validator."""

    name: str
    passed: bool
    duration_ms: float
    output: str = ""
    error: str = ""
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class ValidationSummary:
    """Summary of all validation results."""

    results: List[ValidatorResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        """True if all validators passed."""
        return all(r.passed or r.skipped for r in self.results)

    @property
    def passed_count(self) -> int:
        """Number of validators that passed."""
        return sum(1 for r in self.results if r.passed and not r.skipped)

    @property
    def failed_count(self) -> int:
        """Number of validators that failed."""
        return sum(1 for r in self.results if not r.passed and not r.skipped)

    @property
    def skipped_count(self) -> int:
        """Number of validators that were skipped."""
        return sum(1 for r in self.results if r.skipped)

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "passed": self.passed,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "counts": {
                "passed": self.passed_count,
                "failed": self.failed_count,
                "skipped": self.skipped_count,
                "total": len(self.results),
            },
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration_ms": round(r.duration_ms, 2),
                    "skipped": r.skipped,
                    "skip_reason": r.skip_reason if r.skipped else None,
                    "error": r.error if r.error else None,
                }
                for r in self.results
            ],
        }


# Validators to run (in order)
VALIDATORS = [
    ("validate-agents.py", "Agent Registry Validation"),
    ("validate-cross-references.py", "Cross-Reference Validation"),
    ("validate-frontmatter-schema.py", "Frontmatter Schema Validation"),
    ("validate-manifest-artifacts.py", "Manifest Artifact Validation"),
    ("validate-marketplace-sync.py", "Marketplace Sync Validation"),
    ("validate-script-references.py", "Script Reference Validation"),
]


def find_repo_root() -> Path:
    """Find the repository root directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    # Fall back to script's parent's parent
    return Path(__file__).resolve().parent.parent


def run_validator(
    script_name: str,
    display_name: str,
    repo_root: Path,
    verbose: bool = False,
) -> ValidatorResult:
    """Run a single validator script."""
    script_path = repo_root / "scripts" / script_name

    if not script_path.exists():
        return ValidatorResult(
            name=display_name,
            passed=False,
            duration_ms=0,
            error=f"Script not found: {script_path}",
        )

    start_time = time.time()

    try:
        cmd = [sys.executable, str(script_path)]
        if verbose:
            cmd.append("--verbose")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=120,  # 2 minute timeout per validator
        )

        duration_ms = (time.time() - start_time) * 1000

        return ValidatorResult(
            name=display_name,
            passed=result.returncode == 0,
            duration_ms=duration_ms,
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else "",
        )

    except subprocess.TimeoutExpired:
        duration_ms = (time.time() - start_time) * 1000
        return ValidatorResult(
            name=display_name,
            passed=False,
            duration_ms=duration_ms,
            error="Validator timed out after 120 seconds",
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return ValidatorResult(
            name=display_name,
            passed=False,
            duration_ms=duration_ms,
            error=str(e),
        )


def run_pytest(
    repo_root: Path,
    verbose: bool = False,
) -> ValidatorResult:
    """Run pytest unit tests."""
    tests_dir = repo_root / "tests"

    if not tests_dir.exists():
        return ValidatorResult(
            name="Unit Tests (pytest)",
            passed=True,
            duration_ms=0,
            skipped=True,
            skip_reason="No tests/ directory found",
        )

    start_time = time.time()

    try:
        cmd = [sys.executable, "-m", "pytest", str(tests_dir), "-v"]
        if not verbose:
            cmd.append("-q")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=300,  # 5 minute timeout for tests
        )

        duration_ms = (time.time() - start_time) * 1000

        return ValidatorResult(
            name="Unit Tests (pytest)",
            passed=result.returncode == 0,
            duration_ms=duration_ms,
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else "",
        )

    except subprocess.TimeoutExpired:
        duration_ms = (time.time() - start_time) * 1000
        return ValidatorResult(
            name="Unit Tests (pytest)",
            passed=False,
            duration_ms=duration_ms,
            error="pytest timed out after 300 seconds",
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return ValidatorResult(
            name="Unit Tests (pytest)",
            passed=False,
            duration_ms=duration_ms,
            error=str(e),
        )


def print_result(result: ValidatorResult, verbose: bool = False) -> None:
    """Print a single validator result."""
    if result.skipped:
        status = "SKIP"
        symbol = "-"
    elif result.passed:
        status = "PASS"
        symbol = "+"
    else:
        status = "FAIL"
        symbol = "x"

    duration_str = f"({result.duration_ms:.0f}ms)"
    print(f"[{symbol}] {result.name}: {status} {duration_str}")

    if result.skipped and result.skip_reason:
        print(f"    Reason: {result.skip_reason}")

    if not result.passed and result.error and not result.skipped:
        # Print first few lines of error
        error_lines = result.error.strip().split("\n")[:5]
        for line in error_lines:
            print(f"    {line}")
        if len(result.error.strip().split("\n")) > 5:
            print("    ...")

    if verbose and result.output:
        print("    Output:")
        for line in result.output.strip().split("\n")[:10]:
            print(f"      {line}")


def print_summary(summary: ValidationSummary) -> None:
    """Print validation summary."""
    print()
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total Duration: {summary.total_duration_ms:.0f}ms")
    print(f"Passed: {summary.passed_count}")
    print(f"Failed: {summary.failed_count}")
    print(f"Skipped: {summary.skipped_count}")
    print()

    if summary.passed:
        print("RESULT: ALL VALIDATIONS PASSED")
    else:
        print("RESULT: VALIDATION FAILED")
        print()
        print("Failed validators:")
        for r in summary.results:
            if not r.passed and not r.skipped:
                print(f"  - {r.name}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run complete validation suite for Synaptic Canvas"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip unit tests (pytest), run validators only",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output from each validator",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    repo_root = find_repo_root()
    summary = ValidationSummary()
    start_time = time.time()

    if not args.json:
        print("=" * 60)
        print("SYNAPTIC CANVAS VALIDATION SUITE")
        print("=" * 60)
        print(f"Repository: {repo_root}")
        print(f"Quick mode: {args.quick}")
        print()

    # Run validators
    for script_name, display_name in VALIDATORS:
        result = run_validator(script_name, display_name, repo_root, args.verbose)
        summary.results.append(result)

        if not args.json:
            print_result(result, args.verbose)

    # Run pytest unless --quick
    if not args.quick:
        if not args.json:
            print()
            print("Running unit tests...")

        pytest_result = run_pytest(repo_root, args.verbose)
        summary.results.append(pytest_result)

        if not args.json:
            print_result(pytest_result, args.verbose)
    else:
        summary.results.append(ValidatorResult(
            name="Unit Tests (pytest)",
            passed=True,
            duration_ms=0,
            skipped=True,
            skip_reason="--quick flag specified",
        ))

    summary.total_duration_ms = (time.time() - start_time) * 1000

    # Output
    if args.json:
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        print_summary(summary)

    return 0 if summary.passed else 1


if __name__ == "__main__":
    sys.exit(main())
