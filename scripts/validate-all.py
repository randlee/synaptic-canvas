#!/usr/bin/env python3
"""
Master validation orchestrator for Synaptic Canvas.

Runs all validation scripts in order and aggregates results.

Features:
    - Runs all validators in sequence or parallel
    - Supports --continue-on-failure mode
    - Supports --json output mode
    - Supports --parallel for concurrent execution
    - Returns aggregated exit code (0 if all pass, 1 if any fail)
    - Uses Result[T, E] pattern from project conventions
    - Uses Pydantic V2 for validation results

Exit codes:
    0: All validations passed
    1: One or more validations failed

Usage:
    python3 scripts/validate-all.py [options]
    python3 scripts/validate-all.py --parallel
    python3 scripts/validate-all.py --json
    python3 scripts/validate-all.py --continue-on-failure
"""

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# Add test-packages/harness to path for Result imports
sys.path.insert(
    0, str(Path(__file__).parent.parent / "test-packages" / "harness")
)
from result import Failure, Result, Success


# ============================================================================
# Error Types
# ============================================================================


@dataclass
class ValidatorError:
    """Error during validator execution."""

    validator_name: str
    message: str
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0


@dataclass
class OrchestratorError:
    """Error during orchestration."""

    message: str
    details: dict = field(default_factory=dict)


# ============================================================================
# Pydantic Models
# ============================================================================


class ValidatorConfig(BaseModel):
    """Configuration for a single validator."""

    name: str = Field(description="Human-readable name of the validator")
    command: list[str] = Field(description="Command and arguments to execute")
    required: bool = Field(default=True, description="Whether this validator is required")
    timeout: int = Field(default=300, description="Timeout in seconds")


class ValidatorResult(BaseModel):
    """Result from running a single validator."""

    name: str
    command: str
    exit_code: int
    passed: bool
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


class ValidationSummary(BaseModel):
    """Summary of all validation results."""

    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_validators: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration_seconds: float = 0.0
    all_passed: bool = False
    results: list[ValidatorResult] = Field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(indent=2)


# ============================================================================
# Validators Configuration
# ============================================================================

DEFAULT_VALIDATORS: list[ValidatorConfig] = [
    ValidatorConfig(
        name="Version Consistency",
        command=["python3", "scripts/audit-versions.py", "--verbose"],
    ),
    ValidatorConfig(
        name="Manifest Artifacts",
        command=["python3", "scripts/validate-manifest-artifacts.py"],
    ),
    ValidatorConfig(
        name="Shared Scripts",
        command=["python3", "scripts/validate-shared-scripts.py"],
    ),
    ValidatorConfig(
        name="Marketplace Sync",
        command=["python3", "scripts/validate-marketplace-sync.py"],
    ),
    ValidatorConfig(
        name="Plugin JSON",
        command=["python3", "scripts/validate-plugin-json.py"],
        required=False,  # May not exist in all setups
    ),
    ValidatorConfig(
        name="Agent Registry",
        command=["python3", "scripts/validate-agents.py"],
    ),
    ValidatorConfig(
        name="Frontmatter Schema",
        command=["python3", "scripts/validate-frontmatter-schema.py"],
    ),
    ValidatorConfig(
        name="Script References",
        command=["python3", "scripts/validate-script-references.py"],
    ),
    ValidatorConfig(
        name="Cross References",
        command=["python3", "scripts/validate-cross-references.py"],
    ),
    ValidatorConfig(
        name="Security Scan",
        command=["python3", "scripts/security-scan.py"],
    ),
]


# ============================================================================
# Validation Functions
# ============================================================================


def run_validator(
    config: ValidatorConfig,
    cwd: Optional[Path] = None,
) -> Result[ValidatorResult, ValidatorError]:
    """
    Run a single validator script.

    Args:
        config: Validator configuration
        cwd: Working directory for execution

    Returns:
        Success with ValidatorResult if execution completed (pass or fail)
        Failure with ValidatorError if execution failed to start
    """
    start_time = time.time()
    command_str = " ".join(config.command)

    try:
        result = subprocess.run(
            config.command,
            capture_output=True,
            text=True,
            timeout=config.timeout,
            cwd=cwd,
        )

        duration = time.time() - start_time

        return Success(
            value=ValidatorResult(
                name=config.name,
                command=command_str,
                exit_code=result.returncode,
                passed=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=round(duration, 2),
            )
        )

    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        return Failure(
            error=ValidatorError(
                validator_name=config.name,
                message=f"Timeout after {config.timeout} seconds",
                stdout=e.stdout or "" if hasattr(e, "stdout") else "",
                stderr=e.stderr or "" if hasattr(e, "stderr") else "",
                duration_seconds=round(duration, 2),
            )
        )

    except FileNotFoundError:
        duration = time.time() - start_time
        return Failure(
            error=ValidatorError(
                validator_name=config.name,
                message=f"Script not found: {config.command[0] if config.command else 'unknown'}",
                duration_seconds=round(duration, 2),
            )
        )

    except Exception as e:
        duration = time.time() - start_time
        return Failure(
            error=ValidatorError(
                validator_name=config.name,
                message=str(e),
                duration_seconds=round(duration, 2),
            )
        )


def run_validators_sequential(
    validators: list[ValidatorConfig],
    continue_on_failure: bool = False,
    verbose: bool = False,
    cwd: Optional[Path] = None,
) -> Result[ValidationSummary, OrchestratorError]:
    """
    Run validators sequentially.

    Args:
        validators: List of validator configurations
        continue_on_failure: Continue running validators after failure
        verbose: Enable verbose output
        cwd: Working directory for execution

    Returns:
        Success with ValidationSummary
        Failure with OrchestratorError if orchestration fails
    """
    summary = ValidationSummary(total_validators=len(validators))
    warnings = []
    start_time = time.time()

    for i, config in enumerate(validators, 1):
        if verbose:
            print(f"\n[{i}/{len(validators)}] Running: {config.name}")
            print(f"    Command: {' '.join(config.command)}")

        result = run_validator(config, cwd)

        if isinstance(result, Failure):
            error = result.error
            validator_result = ValidatorResult(
                name=config.name,
                command=" ".join(config.command),
                exit_code=-1,
                passed=False,
                error_message=error.message,
                stdout=error.stdout,
                stderr=error.stderr,
                duration_seconds=error.duration_seconds,
            )
            summary.results.append(validator_result)

            if config.required:
                summary.failed += 1
                if verbose:
                    print(f"    FAILED: {error.message}")

                if not continue_on_failure:
                    # Still mark remaining as skipped
                    for remaining in validators[i:]:
                        summary.results.append(
                            ValidatorResult(
                                name=remaining.name,
                                command=" ".join(remaining.command),
                                exit_code=-1,
                                passed=False,
                                error_message="Skipped due to previous failure",
                            )
                        )
                        summary.skipped += 1
                    break
            else:
                summary.skipped += 1
                warnings.append(f"Optional validator '{config.name}' failed: {error.message}")
                if verbose:
                    print(f"    SKIPPED (optional): {error.message}")

        else:
            validator_result = result.value
            summary.results.append(validator_result)

            if validator_result.passed:
                summary.passed += 1
                if verbose:
                    print(f"    PASSED ({validator_result.duration_seconds:.2f}s)")
            else:
                if config.required:
                    summary.failed += 1
                    if verbose:
                        print(f"    FAILED (exit code: {validator_result.exit_code})")
                        if validator_result.stderr:
                            print(f"    Stderr: {validator_result.stderr[:200]}...")

                    if not continue_on_failure:
                        # Skip remaining validators
                        for remaining in validators[i:]:
                            summary.results.append(
                                ValidatorResult(
                                    name=remaining.name,
                                    command=" ".join(remaining.command),
                                    exit_code=-1,
                                    passed=False,
                                    error_message="Skipped due to previous failure",
                                )
                            )
                            summary.skipped += 1
                        break
                else:
                    summary.skipped += 1
                    warnings.append(f"Optional validator '{config.name}' failed")
                    if verbose:
                        print(f"    SKIPPED (optional, exit code: {validator_result.exit_code})")

    summary.total_duration_seconds = round(time.time() - start_time, 2)
    summary.all_passed = summary.failed == 0

    return Success(value=summary, warnings=warnings)


def run_validators_parallel(
    validators: list[ValidatorConfig],
    max_workers: int = 4,
    verbose: bool = False,
    cwd: Optional[Path] = None,
) -> Result[ValidationSummary, OrchestratorError]:
    """
    Run validators in parallel.

    Args:
        validators: List of validator configurations
        max_workers: Maximum number of concurrent validators
        verbose: Enable verbose output
        cwd: Working directory for execution

    Returns:
        Success with ValidationSummary
        Failure with OrchestratorError if orchestration fails
    """
    summary = ValidationSummary(total_validators=len(validators))
    warnings = []
    start_time = time.time()

    if verbose:
        print(f"\nRunning {len(validators)} validators in parallel (max {max_workers} workers)")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_config = {
            executor.submit(run_validator, config, cwd): config
            for config in validators
        }

        for future in as_completed(future_to_config):
            config = future_to_config[future]

            try:
                result = future.result()

                if isinstance(result, Failure):
                    error = result.error
                    validator_result = ValidatorResult(
                        name=config.name,
                        command=" ".join(config.command),
                        exit_code=-1,
                        passed=False,
                        error_message=error.message,
                        stdout=error.stdout,
                        stderr=error.stderr,
                        duration_seconds=error.duration_seconds,
                    )
                    summary.results.append(validator_result)

                    if config.required:
                        summary.failed += 1
                        if verbose:
                            print(f"  FAILED: {config.name} - {error.message}")
                    else:
                        summary.skipped += 1
                        warnings.append(f"Optional validator '{config.name}' failed: {error.message}")
                        if verbose:
                            print(f"  SKIPPED: {config.name} (optional)")

                else:
                    validator_result = result.value
                    summary.results.append(validator_result)

                    if validator_result.passed:
                        summary.passed += 1
                        if verbose:
                            print(f"  PASSED: {config.name} ({validator_result.duration_seconds:.2f}s)")
                    else:
                        if config.required:
                            summary.failed += 1
                            if verbose:
                                print(f"  FAILED: {config.name} (exit code: {validator_result.exit_code})")
                        else:
                            summary.skipped += 1
                            warnings.append(f"Optional validator '{config.name}' failed")
                            if verbose:
                                print(f"  SKIPPED: {config.name} (optional)")

            except Exception as e:
                validator_result = ValidatorResult(
                    name=config.name,
                    command=" ".join(config.command),
                    exit_code=-1,
                    passed=False,
                    error_message=str(e),
                )
                summary.results.append(validator_result)

                if config.required:
                    summary.failed += 1
                else:
                    summary.skipped += 1

    summary.total_duration_seconds = round(time.time() - start_time, 2)
    summary.all_passed = summary.failed == 0

    # Sort results by validator name for consistent output
    summary.results.sort(key=lambda r: r.name)

    return Success(value=summary, warnings=warnings)


def print_summary(summary: ValidationSummary, verbose: bool = False) -> None:
    """Print human-readable validation summary."""
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    # Overall status
    if summary.all_passed:
        print("\n  STATUS: ALL PASSED")
    else:
        print("\n  STATUS: FAILED")

    # Statistics
    print(f"\n  Total validators:  {summary.total_validators}")
    print(f"  Passed:            {summary.passed}")
    print(f"  Failed:            {summary.failed}")
    print(f"  Skipped:           {summary.skipped}")
    print(f"  Total duration:    {summary.total_duration_seconds:.2f}s")

    # Results table
    print("\n" + "-" * 70)
    print(f"{'Validator':<30} {'Status':<10} {'Duration':<12} {'Exit Code':<10}")
    print("-" * 70)

    for result in summary.results:
        status = "PASS" if result.passed else ("SKIP" if result.error_message and "kipped" in result.error_message else "FAIL")
        duration_str = f"{result.duration_seconds:.2f}s" if result.duration_seconds > 0 else "-"
        exit_code_str = str(result.exit_code) if result.exit_code >= 0 else "-"
        print(f"{result.name:<30} {status:<10} {duration_str:<12} {exit_code_str:<10}")

    print("-" * 70)

    # Show failures in detail
    failed_results = [r for r in summary.results if not r.passed and r.error_message != "Skipped due to previous failure"]
    if failed_results and verbose:
        print("\nFAILURE DETAILS:")
        for result in failed_results:
            print(f"\n  {result.name}:")
            if result.error_message:
                print(f"    Error: {result.error_message}")
            if result.stderr:
                print(f"    Stderr (truncated):")
                for line in result.stderr.split("\n")[:5]:
                    if line.strip():
                        print(f"      {line}")

    print("=" * 70)


def get_validators(
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> list[ValidatorConfig]:
    """
    Get filtered list of validators.

    Args:
        include: Only include validators with these names (substring match)
        exclude: Exclude validators with these names (substring match)

    Returns:
        Filtered list of validators
    """
    validators = DEFAULT_VALIDATORS.copy()

    if include:
        validators = [
            v for v in validators
            if any(inc.lower() in v.name.lower() for inc in include)
        ]

    if exclude:
        validators = [
            v for v in validators
            if not any(exc.lower() in v.name.lower() for exc in exclude)
        ]

    return validators


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Master validation orchestrator - runs all validation scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run all validators sequentially:
    python3 scripts/validate-all.py

  Run validators in parallel:
    python3 scripts/validate-all.py --parallel

  Continue on failure:
    python3 scripts/validate-all.py --continue-on-failure

  Output as JSON:
    python3 scripts/validate-all.py --json

  Verbose output:
    python3 scripts/validate-all.py --verbose

  Include/exclude specific validators:
    python3 scripts/validate-all.py --include version --include manifest
    python3 scripts/validate-all.py --exclude security

Available validators:
  - Version Consistency (audit-versions.py)
  - Manifest Artifacts (validate-manifest-artifacts.py)
  - Marketplace Sync (validate-marketplace-sync.py)
  - Plugin JSON (validate-plugin-json.py) [optional]
  - Agent Registry (validate-agents.py)
  - Frontmatter Schema (validate-frontmatter-schema.py)
  - Script References (validate-script-references.py)
  - Cross References (validate-cross-references.py)
  - Security Scan (security-scan.py)
""",
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run validators in parallel",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum parallel workers (default: 4)",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue running validators after a failure",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--include",
        type=str,
        action="append",
        help="Only include validators matching this name (can be repeated)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        action="append",
        help="Exclude validators matching this name (can be repeated)",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Working directory for script execution",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available validators and exit",
    )

    args = parser.parse_args()

    # List validators and exit
    if args.list:
        print("Available validators:")
        for v in DEFAULT_VALIDATORS:
            required = "" if v.required else " (optional)"
            print(f"  - {v.name}{required}")
            print(f"    Command: {' '.join(v.command)}")
        return 0

    # Get filtered validators
    validators = get_validators(include=args.include, exclude=args.exclude)

    if not validators:
        if args.json:
            print(json.dumps({"error": "No validators matched filter criteria"}))
        else:
            print("Error: No validators matched filter criteria")
        return 1

    # Run validators
    if args.parallel:
        result = run_validators_parallel(
            validators,
            max_workers=args.max_workers,
            verbose=args.verbose and not args.json,
            cwd=args.cwd,
        )
    else:
        result = run_validators_sequential(
            validators,
            continue_on_failure=args.continue_on_failure,
            verbose=args.verbose and not args.json,
            cwd=args.cwd,
        )

    if isinstance(result, Failure):
        if args.json:
            print(json.dumps({"error": result.error.message, "details": result.error.details}))
        else:
            print(f"Error: {result.error.message}")
        return 1

    summary = result.value

    # Output results
    if args.json:
        print(summary.to_json())
    else:
        print_summary(summary, verbose=args.verbose)

    return 0 if summary.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
