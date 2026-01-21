#!/usr/bin/env python3
"""
security-scan.py - Automated security scanning for Synaptic Canvas packages

Purpose: Run comprehensive security checks on all packages in the repository

Usage:
    python3 scripts/security-scan.py                          # Full scan
    python3 scripts/security-scan.py --quick                  # Quick checks only
    python3 scripts/security-scan.py --json                   # JSON output
    python3 scripts/security-scan.py --package sc-delay-tasks # Single package
    python3 scripts/security-scan.py --help                   # Show help
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

# Import Result pattern from harness
sys.path.insert(0, str(Path(__file__).parent.parent / "test-packages" / "harness"))
from result import Failure, Result, Success


# =============================================================================
# Enums
# =============================================================================


class CheckStatus(str, Enum):
    """Status of a security check."""

    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"


class Severity(str, Enum):
    """Severity level of an issue."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# =============================================================================
# Error Types
# =============================================================================


@dataclass
class SecurityError:
    """Error during security scanning."""

    message: str
    file_path: str = ""
    severity: str = "medium"
    details: dict = field(default_factory=dict)


# =============================================================================
# Pydantic Models
# =============================================================================


class SecurityIssue(BaseModel):
    """A single security issue found during scanning."""

    severity: Severity
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    line_content: Optional[str] = None

    model_config = {"use_enum_values": True}


class CheckResult(BaseModel):
    """Result of a single security check."""

    check_name: str
    status: CheckStatus
    issues: List[SecurityIssue] = Field(default_factory=list)
    message: str = ""

    model_config = {"use_enum_values": True}


class ScanConfiguration(BaseModel):
    """Configuration for the security scan."""

    quick_mode: bool = False
    single_package: Optional[str] = None
    repo_root: Path
    output_format: str = "text"

    @field_validator("repo_root", mode="before")
    @classmethod
    def convert_to_path(cls, v):
        """Convert string to Path."""
        return Path(v) if isinstance(v, str) else v

    model_config = {"arbitrary_types_allowed": True}


class ScanResults(BaseModel):
    """Complete results of a security scan."""

    scan_date: str
    overall_status: CheckStatus
    issues_found: int
    checks: Dict[str, CheckResult]
    configuration: ScanConfiguration

    model_config = {"use_enum_values": True}


# =============================================================================
# Scanner Class
# =============================================================================


class SecurityScanner:
    """Main security scanner implementation."""

    # Patterns for secrets detection
    SECRET_PATTERNS = [
        r'password\s*=\s*["\047][^"\047]+["\047]',
        r'api_key\s*=\s*["\047][^"\047]+["\047]',
        r'secret\s*=\s*["\047][^"\047]+["\047]',
        r'token\s*=\s*["\047][^"\047]+["\047]',
        r'AWS_KEY\s*=\s*["\047][^"\047]+["\047]',
        r'AWS_SECRET\s*=\s*["\047][^"\047]+["\047]',
        r'GITHUB_TOKEN\s*=\s*["\047][^"\047]+["\047]',
        r'private_key\s*=\s*["\047][^"\047]+["\047]',
        r"BEGIN PRIVATE KEY",
        r"BEGIN RSA PRIVATE KEY",
    ]

    # Directories to exclude from scanning
    EXCLUDE_DIRS = [".git", ".venv", ".venv.bak", "__pycache__", "node_modules", "docs", "tests", "test-packages"]

    # Files to exclude from secrets/python safety scanning (patterns in the filename)
    EXCLUDE_FILES = ["security-scan", "security_scan", "SECURITY-SCANNING"]

    # Allowlisted shell=True usage for vetted cases (repo-relative paths)
    ALLOW_SHELL_TRUE = {
        "packages/sc-codex/scripts/ai_cli/task_runner.py",
    }

    def __init__(self, config: ScanConfiguration):
        """Initialize scanner with configuration."""
        self.config = config
        self.checks: Dict[str, CheckResult] = {}

    def run(self) -> Result[ScanResults, SecurityError]:
        """Run all security checks and return results."""
        try:
            # Run all checks
            self.scan_secrets()
            self.check_script_quality()
            self.check_python_safety()
            self.verify_package_documentation()
            self.verify_license_files()
            self.audit_dependencies()

            # Calculate overall status
            overall_status = self._calculate_overall_status()
            issues_found = sum(len(check.issues) for check in self.checks.values())

            results = ScanResults(
                scan_date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                overall_status=overall_status,
                issues_found=issues_found,
                checks=self.checks,
                configuration=self.config,
            )

            return Success(value=results, warnings=[])

        except Exception as e:
            return Failure(
                error=SecurityError(
                    message=f"Security scan failed: {str(e)}",
                    severity="high",
                    details={"exception": type(e).__name__},
                )
            )

    def scan_secrets(self) -> None:
        """Scan for hardcoded secrets and credentials."""
        issues: List[SecurityIssue] = []
        search_path = self._get_search_path()

        for pattern in self.SECRET_PATTERNS:
            matches = self._grep_pattern(pattern, search_path, case_insensitive=True)
            for file_path, line_num, line_content in matches:
                # Skip this script itself
                if "security-scan" in file_path:
                    continue

                issues.append(
                    SecurityIssue(
                        severity=Severity.HIGH,
                        message=f"Potential secret in: {file_path}",
                        file_path=file_path,
                        line_number=line_num,
                        line_content=line_content[:100] if line_content else None,
                    )
                )

        # Check for credentials in markdown
        md_pattern = r"(password|secret|token|key)"
        md_matches = self._grep_pattern(
            md_pattern, search_path, include_glob="*.md", case_insensitive=True
        )
        for file_path, line_num, line_content in md_matches:
            if re.search(
                r'(password|secret|token|key).*["\'].*[a-zA-Z0-9]{16,}',
                line_content,
                re.IGNORECASE,
            ):
                issues.append(
                    SecurityIssue(
                        severity=Severity.MEDIUM,
                        message=f"Possible credential in markdown: {file_path}",
                        file_path=file_path,
                        line_number=line_num,
                    )
                )

        status = CheckStatus.PASSED if not issues else CheckStatus.FAILED
        message = f"({len(issues)} potential secrets found)" if issues else "(0 potential secrets found)"

        self.checks["secrets_detection"] = CheckResult(
            check_name="Secrets Detection", status=status, issues=issues, message=message
        )

    def check_script_quality(self) -> None:
        """Check shell script quality."""
        issues: List[SecurityIssue] = []
        search_path = self._get_search_path()

        # Find all shell scripts
        scripts = list(search_path.rglob("*.sh"))
        total_scripts = len(scripts)

        for script in scripts:
            # Check if executable (skip on Windows where this doesn't work properly)
            if sys.platform != "win32" and not os.access(script, os.X_OK):
                issues.append(
                    SecurityIssue(
                        severity=Severity.MEDIUM,
                        message=f"Script not executable: {script.as_posix()}",
                        file_path=script.as_posix(),
                    )
                )

            # Check for shebang
            try:
                with open(script, "r", encoding="utf-8") as f:
                    first_line = f.readline()
                    if not first_line.startswith("#!"):
                        issues.append(
                            SecurityIssue(
                                severity=Severity.MEDIUM,
                                message=f"Missing shebang in: {script.as_posix()}",
                                file_path=script.as_posix(),
                            )
                        )

                    # Check for set -e
                    f.seek(0)
                    first_20_lines = "".join(f.readlines()[:20])
                    if "set -e" not in first_20_lines:
                        issues.append(
                            SecurityIssue(
                                severity=Severity.LOW,
                                message=f"Missing 'set -e' in: {script.as_posix()}",
                                file_path=script.as_posix(),
                            )
                        )
            except Exception as e:
                issues.append(
                    SecurityIssue(
                        severity=Severity.MEDIUM,
                        message=f"Could not read script: {script.as_posix()} ({e})",
                        file_path=script.as_posix(),
                    )
                )

            # Run shellcheck if available
            if self._command_exists("shellcheck"):
                result = subprocess.run(
                    ["shellcheck", "-x", str(script)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0 and "No issues detected" not in result.stdout:
                    shellcheck_issues = result.stdout.count("\nIn ")
                    if shellcheck_issues > 0:
                        issues.append(
                            SecurityIssue(
                                severity=Severity.LOW,
                                message=f"Shellcheck found {shellcheck_issues} issue(s) in: {script.as_posix()}",
                                file_path=script.as_posix(),
                            )
                        )

        if not issues:
            status = CheckStatus.PASSED
            message = f"(all {total_scripts} scripts valid)"
        elif len(issues) < 5:
            status = CheckStatus.WARNING
            message = f"({len(issues)} minor issues found)"
        else:
            status = CheckStatus.FAILED
            message = f"({len(issues)} issues found)"

        self.checks["script_quality"] = CheckResult(
            check_name="Script Quality", status=status, issues=issues, message=message
        )

    def check_python_safety(self) -> None:
        """Check for unsafe Python patterns."""
        issues: List[SecurityIssue] = []
        search_path = self._get_search_path()

        # Check for eval()
        eval_matches = self._grep_pattern(r"eval\(", search_path, include_glob="*.py")
        for file_path, line_num, _ in eval_matches:
            issues.append(
                SecurityIssue(
                    severity=Severity.HIGH,
                    message=f"Unsafe eval() call in: {file_path}",
                    file_path=file_path,
                    line_number=line_num,
                )
            )

        # Check for exec()
        exec_matches = self._grep_pattern(r"exec\(", search_path, include_glob="*.py")
        for file_path, line_num, _ in exec_matches:
            issues.append(
                SecurityIssue(
                    severity=Severity.HIGH,
                    message=f"Unsafe exec() call in: {file_path}",
                    file_path=file_path,
                    line_number=line_num,
                )
            )

        # Check for shell=True
        shell_matches = self._grep_pattern(r"shell=True", search_path, include_glob="*.py")
        for file_path, line_num, _ in shell_matches:
            try:
                rel_path = Path(file_path).resolve().relative_to(self.config.repo_root).as_posix()
            except Exception:
                rel_path = file_path
            if rel_path in self.ALLOW_SHELL_TRUE:
                continue
            issues.append(
                SecurityIssue(
                    severity=Severity.MEDIUM,
                    message=f"Potentially unsafe shell=True in: {file_path}",
                    file_path=file_path,
                    line_number=line_num,
                )
            )

        # Check for pickle.loads
        pickle_matches = self._grep_pattern(r"pickle\.loads", search_path, include_glob="*.py")
        for file_path, line_num, _ in pickle_matches:
            issues.append(
                SecurityIssue(
                    severity=Severity.MEDIUM,
                    message=f"Pickle deserialization in: {file_path}",
                    file_path=file_path,
                    line_number=line_num,
                )
            )

        status = CheckStatus.PASSED if not issues else CheckStatus.FAILED
        message = (
            "(no unsafe patterns found)" if not issues else f"({len(issues)} unsafe patterns found)"
        )

        self.checks["python_safety"] = CheckResult(
            check_name="Python Safety", status=status, issues=issues, message=message
        )

    def verify_package_documentation(self) -> None:
        """Verify package documentation is complete."""
        issues: List[SecurityIssue] = []
        packages = self._get_packages()

        for package_name in packages:
            pkg_path = self.config.repo_root / "packages" / package_name

            # Check for README.md
            readme_path = pkg_path / "README.md"
            if not readme_path.exists():
                issues.append(
                    SecurityIssue(
                        severity=Severity.HIGH,
                        message=f"Missing README.md in: {package_name}",
                        file_path=pkg_path.as_posix(),
                    )
                )
            else:
                # Check README mentions security
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                        if "security" not in content:
                            issues.append(
                                SecurityIssue(
                                    severity=Severity.MEDIUM,
                                    message=f"README missing security information: {package_name}",
                                    file_path=readme_path.as_posix(),
                                )
                            )
                except Exception:
                    pass

            # Check for LICENSE
            license_path = pkg_path / "LICENSE"
            if not license_path.exists():
                issues.append(
                    SecurityIssue(
                        severity=Severity.HIGH,
                        message=f"Missing LICENSE in: {package_name}",
                        file_path=pkg_path.as_posix(),
                    )
                )

            # Check for manifest.yaml
            manifest_path = pkg_path / "manifest.yaml"
            if not manifest_path.exists():
                issues.append(
                    SecurityIssue(
                        severity=Severity.HIGH,
                        message=f"Missing manifest.yaml in: {package_name}",
                        file_path=pkg_path.as_posix(),
                    )
                )
            else:
                # Validate YAML syntax
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        yaml.safe_load(f)
                except yaml.YAMLError:
                    issues.append(
                        SecurityIssue(
                            severity=Severity.HIGH,
                            message=f"Invalid YAML in manifest.yaml: {package_name}",
                            file_path=manifest_path.as_posix(),
                        )
                    )

            # Check for CHANGELOG.md (recommended, not required)
            changelog_path = pkg_path / "CHANGELOG.md"
            if not changelog_path.exists():
                issues.append(
                    SecurityIssue(
                        severity=Severity.LOW,
                        message=f"Missing CHANGELOG.md in: {package_name} (recommended)",
                        file_path=pkg_path.as_posix(),
                    )
                )

        # Missing docs are warnings; invalid YAML or corrupt files are failures
        has_critical = any(
            "Invalid YAML" in issue.message or "Empty" in issue.message
            for issue in issues
        )
        high_issues = sum(1 for issue in issues if issue.severity == Severity.HIGH)

        if not issues:
            status = CheckStatus.PASSED
            message = f"(all {len(packages)} packages have required docs)"
        elif has_critical:
            status = CheckStatus.FAILED
            message = f"({high_issues} critical issues)"
        else:
            status = CheckStatus.WARNING
            message = f"({len(issues)} issues in {len(packages)} packages)"

        self.checks["package_documentation"] = CheckResult(
            check_name="Package Documentation", status=status, issues=issues, message=message
        )

    def verify_license_files(self) -> None:
        """Verify all packages have license files."""
        issues: List[SecurityIssue] = []
        packages = self._get_packages()

        for package_name in packages:
            pkg_path = self.config.repo_root / "packages" / package_name
            license_path = pkg_path / "LICENSE"

            if not license_path.exists():
                issues.append(
                    SecurityIssue(
                        severity=Severity.HIGH,
                        message=f"Missing LICENSE in: {package_name}",
                        file_path=pkg_path.as_posix(),
                    )
                )
            elif license_path.stat().st_size == 0:
                issues.append(
                    SecurityIssue(
                        severity=Severity.HIGH,
                        message=f"Empty LICENSE file in: {package_name}",
                        file_path=license_path.as_posix(),
                    )
                )

        # Check root LICENSE
        root_license = self.config.repo_root / "LICENSE"
        if not root_license.exists():
            issues.append(
                SecurityIssue(
                    severity=Severity.HIGH,
                    message="Missing LICENSE in repository root",
                    file_path=self.config.repo_root.as_posix(),
                )
            )

        # Missing LICENSE is a warning, but invalid/empty LICENSE is a failure
        has_critical = any(
            "Empty LICENSE" in issue.message or "Invalid" in issue.message
            for issue in issues
        )
        if not issues:
            status = CheckStatus.PASSED
            message = "(all packages have LICENSE)"
        elif has_critical:
            status = CheckStatus.FAILED
            message = f"({len(issues)} license issues)"
        else:
            status = CheckStatus.WARNING
            message = f"({len(issues)} missing licenses)"

        self.checks["license_files"] = CheckResult(
            check_name="License Files", status=status, issues=issues, message=message
        )

    def audit_dependencies(self) -> None:
        """Audit dependencies for vulnerabilities."""
        if self.config.quick_mode:
            self.checks["dependency_audit"] = CheckResult(
                check_name="Dependency Audit",
                status=CheckStatus.SKIPPED,
                issues=[],
                message="(quick mode)",
            )
            return

        issues: List[SecurityIssue] = []

        # Check Node.js dependencies
        package_json = self.config.repo_root / "package.json"
        if package_json.exists() and self._command_exists("npm"):
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=self.config.repo_root,
                capture_output=True,
                text=True,
            )
            try:
                audit_data = json.loads(result.stdout)
                if "vulnerabilities" in audit_data:
                    metadata = audit_data.get("metadata", {}).get("vulnerabilities", {})
                    high = metadata.get("high", 0)
                    moderate = metadata.get("moderate", 0)

                    if high > 0:
                        issues.append(
                            SecurityIssue(
                                severity=Severity.HIGH,
                                message=f"{high} high severity npm vulnerabilities",
                            )
                        )

                    if moderate > 0:
                        issues.append(
                            SecurityIssue(
                                severity=Severity.MEDIUM,
                                message=f"{moderate} moderate severity npm vulnerabilities",
                            )
                        )
            except json.JSONDecodeError:
                pass

        # Check Python dependencies
        requirements_txt = self.config.repo_root / "requirements.txt"
        if requirements_txt.exists():
            vulnerable_packages = ["pyyaml<5.4", "requests<2.20.0", "urllib3<1.26.5"]

            try:
                with open(requirements_txt, "r", encoding="utf-8") as f:
                    content = f.read()
                    for vuln_pkg in vulnerable_packages:
                        pkg_name = vuln_pkg.split("<")[0]
                        if re.search(f"^{pkg_name}", content, re.MULTILINE):
                            issues.append(
                                SecurityIssue(
                                    severity=Severity.MEDIUM,
                                    message=f"Check version of {pkg_name} (known vulnerabilities in old versions)",
                                    file_path=requirements_txt.as_posix(),
                                )
                            )
            except Exception:
                pass

        # Check for insecure git URLs
        manifests = list((self.config.repo_root / "packages").rglob("manifest.yaml"))
        for manifest in manifests:
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "git+http://" in content or "git://" in content:
                        issues.append(
                            SecurityIssue(
                                severity=Severity.LOW,
                                message=f"Insecure git:// protocol in: {manifest.as_posix()}",
                                file_path=manifest.as_posix(),
                            )
                        )
            except Exception:
                pass

        # Determine status
        high_issues = sum(1 for issue in issues if issue.severity == Severity.HIGH)
        if not issues:
            status = CheckStatus.PASSED
            message = "(no vulnerabilities found)"
        elif high_issues == 0:
            status = CheckStatus.WARNING
            message = f"({len(issues)} warnings found)"
        else:
            status = CheckStatus.FAILED
            message = f"({high_issues} high severity issues)"

        self.checks["dependency_audit"] = CheckResult(
            check_name="Dependency Audit", status=status, issues=issues, message=message
        )

    def _calculate_overall_status(self) -> CheckStatus:
        """Calculate overall status based on individual checks."""
        has_failed = any(check.status == CheckStatus.FAILED for check in self.checks.values())
        has_warning = any(check.status == CheckStatus.WARNING for check in self.checks.values())

        if has_failed:
            return CheckStatus.FAILED
        elif has_warning:
            return CheckStatus.WARNING
        else:
            return CheckStatus.PASSED

    def _get_search_path(self) -> Path:
        """Get the path to search based on configuration."""
        if self.config.single_package:
            return self.config.repo_root / "packages" / self.config.single_package
        return self.config.repo_root

    def _get_packages(self) -> List[str]:
        """Get list of packages to check."""
        if self.config.single_package:
            return [self.config.single_package]

        packages_dir = self.config.repo_root / "packages"
        if not packages_dir.exists():
            return []

        return [
            p.name for p in packages_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
        ]

    def _grep_pattern(
        self,
        pattern: str,
        search_path: Path,
        include_glob: Optional[str] = None,
        case_insensitive: bool = False,
    ) -> List[tuple[str, int, str]]:
        """Search for pattern in files, return (file_path, line_num, line_content)."""
        matches = []

        if include_glob:
            # Get files matching glob but filter out excluded directories
            files = [
                f for f in search_path.rglob(include_glob)
                if not any(excl in f.parts for excl in self.EXCLUDE_DIRS)
            ]
        else:
            # Get all files, excluding certain directories
            files = []
            for root, dirs, filenames in os.walk(search_path):
                # Remove excluded dirs from dirs list (modifies in-place)
                dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
                for filename in filenames:
                    files.append(Path(root) / filename)

        regex_flags = re.IGNORECASE if case_insensitive else 0
        compiled_pattern = re.compile(pattern, regex_flags)

        for file_path in files:
            # Skip excluded files
            file_path_str = file_path.as_posix()
            if any(excl in file_path_str for excl in self.EXCLUDE_FILES):
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if compiled_pattern.search(line):
                            matches.append((file_path_str, line_num, line.strip()))
            except Exception:
                # Skip files that can't be read
                pass

        return matches

    @staticmethod
    def _command_exists(command: str) -> bool:
        """Check if a command exists in PATH (cross-platform)."""
        return shutil.which(command) is not None


# =============================================================================
# Output Functions
# =============================================================================


def format_text_output(results: ScanResults) -> str:
    """Format results as human-readable text."""
    lines = []

    # Header
    lines.append("")
    lines.append("═" * 63)
    lines.append(f"Security Scan Report - {results.scan_date}")
    lines.append("═" * 63)
    lines.append("")

    # Individual check results
    for check in results.checks.values():
        status_symbol = {
            CheckStatus.PASSED: "✅",
            CheckStatus.WARNING: "⚠️",
            CheckStatus.FAILED: "❌",
            CheckStatus.SKIPPED: "⊘",
        }.get(check.status, "?")

        lines.append(f"{status_symbol} {check.check_name}: {check.status} {check.message}")

        # Show issues if any
        for issue in check.issues:
            severity_color = {"HIGH": "[HIGH]", "MEDIUM": "[MEDIUM]", "LOW": "[LOW]"}.get(
                issue.severity, "[?]"
            )
            lines.append(f"   {severity_color} {issue.message}")

    lines.append("")
    lines.append("─" * 63)
    lines.append("")

    # Overall status
    overall_symbol = {
        CheckStatus.PASSED: "✅ PASSED",
        CheckStatus.WARNING: "⚠️  PASSED (with warnings)",
        CheckStatus.FAILED: "❌ FAILED",
    }.get(results.overall_status, "? UNKNOWN")

    lines.append(f"OVERALL STATUS: {overall_symbol}")
    lines.append(f"Total Issues Found: {results.issues_found}")
    lines.append(f"Scan Date: {results.scan_date}")
    lines.append("")
    lines.append("═" * 63)

    return "\n".join(lines)


def format_json_output(results: ScanResults) -> str:
    """Format results as JSON."""
    return results.model_dump_json(indent=2)


# =============================================================================
# Main Function
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Security Scan Tool for Synaptic Canvas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/security-scan.py
  python3 scripts/security-scan.py --quick
  python3 scripts/security-scan.py --json > scan-results.json
  python3 scripts/security-scan.py --package sc-delay-tasks

Checks Performed:
  1. Secrets Detection      - Scan for hardcoded credentials
  2. Script Quality         - Validate shell scripts with shellcheck
  3. Python Safety          - Check for unsafe Python patterns
  4. Package Documentation  - Verify security docs present
  5. License Files          - Ensure all packages have LICENSE
  6. Dependency Audit       - Check for vulnerable dependencies

Exit Codes:
  0 - All checks passed (or only warnings found)
  1 - Failures found (critical issues)
        """,
    )

    parser.add_argument("--quick", action="store_true", help="Run quick checks only (skip slow scans)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--package", type=str, help="Scan only the specified package")

    args = parser.parse_args()

    # Determine repo root
    repo_root = Path(__file__).parent.parent.resolve()

    # Validate single package exists if specified
    if args.package:
        package_path = repo_root / "packages" / args.package
        if not package_path.exists():
            print(f"Error: Package not found: {args.package}", file=sys.stderr)
            return 2

    # Create configuration
    config = ScanConfiguration(
        quick_mode=args.quick,
        single_package=args.package,
        repo_root=repo_root,
        output_format="json" if args.json else "text",
    )

    # Run scanner
    scanner = SecurityScanner(config)
    result = scanner.run()

    if isinstance(result, Failure):
        print(f"Error: {result.error.message}", file=sys.stderr)
        return 2

    # Format and print results
    if config.output_format == "json":
        print(format_json_output(result.value))
    else:
        print(format_text_output(result.value))

    # Return appropriate exit code
    # Exit code 0: PASSED or WARNING (warnings are informational)
    # Exit code 1: FAILED (critical issues that should block)
    if result.value.overall_status == CheckStatus.FAILED:
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
