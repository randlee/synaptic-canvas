#!/usr/bin/env python3
"""
Generate comprehensive HTML validation report for Synaptic Canvas.

Creates an HTML report with Bootstrap 5 styling that includes:
- Executive Summary (PASS/FAIL badge, timestamp, package count)
- Version Matrix Table (sortable, with package/manifest/commands/skills/agents versions)
- Package Details (expandable per-package breakdown)
- Validation Test Results (results from each validator script)
- Unit Test Results (link to pytest report + summary)
- File Inventory (all config files with dates)
- Issues & Warnings (grouped by severity with color badges)

Features:
    - Uses Jinja2 for HTML templating with Bootstrap 5 styling
    - Generates report at reports/YYYY-MM-DD-HHmmss-validation-report.html
    - Supports --skip-tests to skip pytest run
    - Supports --keep-reports N to keep N most recent reports (default 5)
    - Supports --no-cleanup to keep all reports
    - Auto-cleans old reports (keeps only 5 most recent)
    - Uses Result[T, E] pattern and Pydantic V2

Exit codes:
    0: Report generated successfully, all validations passed
    1: Report generated but some validations failed

Usage:
    python3 scripts/generate-validation-report.py
    python3 scripts/generate-validation-report.py --skip-tests
    python3 scripts/generate-validation-report.py --keep-reports 10
    python3 scripts/generate-validation-report.py --no-cleanup
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
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
class ReportError:
    """Error during report generation."""

    message: str
    file_path: Optional[str] = None
    details: dict = field(default_factory=dict)


@dataclass
class FileError:
    """Error related to file operations."""

    operation: str
    path: str
    message: str


# ============================================================================
# Pydantic Models
# ============================================================================


class Severity:
    """Severity levels for issues."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Issue(BaseModel):
    """An issue found during validation."""

    message: str
    severity: str = Severity.MEDIUM
    file_path: Optional[str] = None
    validator: Optional[str] = None
    details: dict = Field(default_factory=dict)

    def severity_badge_class(self) -> str:
        """Get Bootstrap badge class for severity."""
        return {
            Severity.CRITICAL: "bg-danger",
            Severity.HIGH: "bg-warning text-dark",
            Severity.MEDIUM: "bg-info text-dark",
            Severity.LOW: "bg-secondary",
        }.get(self.severity, "bg-secondary")


class ValidatorResult(BaseModel):
    """Result from running a validator."""

    name: str
    command: str
    exit_code: int
    passed: bool
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


class PackageVersion(BaseModel):
    """Version information for a package."""

    package_name: str
    manifest_version: str
    commands: list[dict] = Field(default_factory=list)  # name, version
    skills: list[dict] = Field(default_factory=list)
    agents: list[dict] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list)
    is_consistent: bool = True


class FileInfo(BaseModel):
    """Information about a configuration file."""

    path: str
    modified_time: str
    size_bytes: int


class TestSummary(BaseModel):
    """Summary of pytest results."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    report_path: Optional[str] = None


class ReportData(BaseModel):
    """All data for the validation report."""

    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    report_file: str = ""
    overall_passed: bool = True
    total_packages: int = 0
    marketplace_version: str = ""

    # Validation results
    validator_results: list[ValidatorResult] = Field(default_factory=list)
    validation_passed: int = 0
    validation_failed: int = 0

    # Version matrix
    package_versions: list[PackageVersion] = Field(default_factory=list)

    # Issues
    issues: list[Issue] = Field(default_factory=list)

    # File inventory
    config_files: list[FileInfo] = Field(default_factory=list)

    # Test results
    test_summary: TestSummary = Field(default_factory=TestSummary)

    def get_issues_by_severity(self, severity: str) -> list[Issue]:
        """Get issues filtered by severity."""
        return [i for i in self.issues if i.severity == severity]


# ============================================================================
# HTML Template
# ============================================================================

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Synaptic Canvas Validation Report - {{ data.timestamp[:10] }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .badge-pass { background-color: #198754; }
        .badge-fail { background-color: #dc3545; }
        .card { margin-bottom: 20px; }
        .validator-output {
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.85em;
            white-space: pre-wrap;
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
        }
        .table-version th { white-space: nowrap; }
        .severity-critical { color: #dc3545; }
        .severity-high { color: #fd7e14; }
        .severity-medium { color: #0dcaf0; }
        .severity-low { color: #6c757d; }
        .accordion-button:not(.collapsed) { background-color: #e7f1ff; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- Header -->
        <div class="row mb-4">
            <div class="col">
                <h1>Synaptic Canvas Validation Report</h1>
                <p class="text-muted">Generated: {{ data.timestamp }}</p>
            </div>
        </div>

        <!-- Executive Summary -->
        <div class="card">
            <div class="card-header">
                <h2 class="h5 mb-0">Executive Summary</h2>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <h6>Overall Status</h6>
                        {% if data.overall_passed %}
                        <span class="badge badge-pass fs-5">PASS</span>
                        {% else %}
                        <span class="badge badge-fail fs-5">FAIL</span>
                        {% endif %}
                    </div>
                    <div class="col-md-3">
                        <h6>Marketplace Version</h6>
                        <span class="fs-5">{{ data.marketplace_version or 'N/A' }}</span>
                    </div>
                    <div class="col-md-3">
                        <h6>Packages Validated</h6>
                        <span class="fs-5">{{ data.total_packages }}</span>
                    </div>
                    <div class="col-md-3">
                        <h6>Issues Found</h6>
                        <span class="fs-5 {% if data.issues %}text-danger{% else %}text-success{% endif %}">
                            {{ data.issues | length }}
                        </span>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-md-6">
                        <h6>Validation Results</h6>
                        <span class="text-success">{{ data.validation_passed }} passed</span> /
                        <span class="text-danger">{{ data.validation_failed }} failed</span>
                    </div>
                    {% if data.test_summary.report_path %}
                    <div class="col-md-6">
                        <h6>Unit Tests</h6>
                        <a href="{{ data.test_summary.report_path }}" target="_blank">View Test Report</a>
                        ({{ data.test_summary.passed }} passed, {{ data.test_summary.failed }} failed)
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>

        <!-- Version Matrix -->
        <div class="card">
            <div class="card-header">
                <h2 class="h5 mb-0">Version Matrix</h2>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped table-hover table-version">
                        <thead>
                            <tr>
                                <th>Package</th>
                                <th>Manifest</th>
                                <th>Commands</th>
                                <th>Skills</th>
                                <th>Agents</th>
                                <th>Scripts</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for pkg in data.package_versions %}
                            <tr>
                                <td><strong>{{ pkg.package_name }}</strong></td>
                                <td>{{ pkg.manifest_version }}</td>
                                <td>{{ pkg.commands | length }} items</td>
                                <td>{{ pkg.skills | length }} items</td>
                                <td>{{ pkg.agents | length }} items</td>
                                <td>{{ pkg.scripts | length }} items</td>
                                <td>
                                    {% if pkg.is_consistent %}
                                    <span class="badge bg-success">Consistent</span>
                                    {% else %}
                                    <span class="badge bg-danger">Mismatch</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Package Details (Accordion) -->
        <div class="card">
            <div class="card-header">
                <h2 class="h5 mb-0">Package Details</h2>
            </div>
            <div class="card-body">
                <div class="accordion" id="packageAccordion">
                    {% for pkg in data.package_versions %}
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button"
                                    data-bs-toggle="collapse" data-bs-target="#pkg-{{ loop.index }}">
                                {{ pkg.package_name }} (v{{ pkg.manifest_version }})
                                {% if not pkg.is_consistent %}
                                <span class="badge bg-danger ms-2">Version Mismatch</span>
                                {% endif %}
                            </button>
                        </h2>
                        <div id="pkg-{{ loop.index }}" class="accordion-collapse collapse">
                            <div class="accordion-body">
                                <div class="row">
                                    <div class="col-md-3">
                                        <h6>Commands ({{ pkg.commands | length }})</h6>
                                        <ul class="list-unstyled">
                                            {% for cmd in pkg.commands %}
                                            <li>{{ cmd.name }} <small class="text-muted">v{{ cmd.version }}</small></li>
                                            {% else %}
                                            <li class="text-muted">None</li>
                                            {% endfor %}
                                        </ul>
                                    </div>
                                    <div class="col-md-3">
                                        <h6>Skills ({{ pkg.skills | length }})</h6>
                                        <ul class="list-unstyled">
                                            {% for skill in pkg.skills %}
                                            <li>{{ skill.name }} <small class="text-muted">v{{ skill.version }}</small></li>
                                            {% else %}
                                            <li class="text-muted">None</li>
                                            {% endfor %}
                                        </ul>
                                    </div>
                                    <div class="col-md-3">
                                        <h6>Agents ({{ pkg.agents | length }})</h6>
                                        <ul class="list-unstyled">
                                            {% for agent in pkg.agents %}
                                            <li>{{ agent.name }} <small class="text-muted">v{{ agent.version }}</small></li>
                                            {% else %}
                                            <li class="text-muted">None</li>
                                            {% endfor %}
                                        </ul>
                                    </div>
                                    <div class="col-md-3">
                                        <h6>Scripts ({{ pkg.scripts | length }})</h6>
                                        <ul class="list-unstyled">
                                            {% for script in pkg.scripts %}
                                            <li>{{ script }}</li>
                                            {% else %}
                                            <li class="text-muted">None</li>
                                            {% endfor %}
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Validation Results -->
        <div class="card">
            <div class="card-header">
                <h2 class="h5 mb-0">Validation Test Results</h2>
            </div>
            <div class="card-body">
                <div class="accordion" id="validatorAccordion">
                    {% for result in data.validator_results %}
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button"
                                    data-bs-toggle="collapse" data-bs-target="#validator-{{ loop.index }}">
                                {% if result.passed %}
                                <span class="badge bg-success me-2">PASS</span>
                                {% else %}
                                <span class="badge bg-danger me-2">FAIL</span>
                                {% endif %}
                                {{ result.name }}
                                <small class="text-muted ms-2">({{ result.duration_seconds }}s)</small>
                            </button>
                        </h2>
                        <div id="validator-{{ loop.index }}" class="accordion-collapse collapse">
                            <div class="accordion-body">
                                <p><strong>Command:</strong> <code>{{ result.command }}</code></p>
                                <p><strong>Exit Code:</strong> {{ result.exit_code }}</p>
                                {% if result.stdout %}
                                <h6>Output:</h6>
                                <div class="validator-output">{{ result.stdout }}</div>
                                {% endif %}
                                {% if result.stderr %}
                                <h6 class="mt-3">Errors:</h6>
                                <div class="validator-output text-danger">{{ result.stderr }}</div>
                                {% endif %}
                                {% if result.error_message %}
                                <div class="alert alert-danger mt-3">{{ result.error_message }}</div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Unit Test Results -->
        {% if data.test_summary.total > 0 %}
        <div class="card">
            <div class="card-header">
                <h2 class="h5 mb-0">Unit Test Results</h2>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-2">
                        <h6>Total</h6>
                        <span class="fs-4">{{ data.test_summary.total }}</span>
                    </div>
                    <div class="col-md-2">
                        <h6>Passed</h6>
                        <span class="fs-4 text-success">{{ data.test_summary.passed }}</span>
                    </div>
                    <div class="col-md-2">
                        <h6>Failed</h6>
                        <span class="fs-4 text-danger">{{ data.test_summary.failed }}</span>
                    </div>
                    <div class="col-md-2">
                        <h6>Skipped</h6>
                        <span class="fs-4 text-warning">{{ data.test_summary.skipped }}</span>
                    </div>
                    <div class="col-md-2">
                        <h6>Errors</h6>
                        <span class="fs-4 text-danger">{{ data.test_summary.errors }}</span>
                    </div>
                    <div class="col-md-2">
                        <h6>Duration</h6>
                        <span class="fs-4">{{ data.test_summary.duration_seconds }}s</span>
                    </div>
                </div>
                {% if data.test_summary.report_path %}
                <div class="mt-3">
                    <a href="{{ data.test_summary.report_path }}" class="btn btn-primary" target="_blank">
                        View Detailed Test Report
                    </a>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        <!-- File Inventory -->
        <div class="card">
            <div class="card-header">
                <h2 class="h5 mb-0">File Inventory</h2>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm table-striped">
                        <thead>
                            <tr>
                                <th>File</th>
                                <th>Last Modified</th>
                                <th>Size</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for file in data.config_files %}
                            <tr>
                                <td><code>{{ file.path }}</code></td>
                                <td>{{ file.modified_time }}</td>
                                <td>{{ file.size_bytes }} bytes</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Issues & Warnings -->
        {% if data.issues %}
        <div class="card">
            <div class="card-header">
                <h2 class="h5 mb-0">Issues & Warnings</h2>
            </div>
            <div class="card-body">
                {% for severity in ['critical', 'high', 'medium', 'low'] %}
                {% set issues = data.get_issues_by_severity(severity) %}
                {% if issues %}
                <h6 class="severity-{{ severity }} text-uppercase">{{ severity }} ({{ issues | length }})</h6>
                <ul class="mb-3">
                    {% for issue in issues %}
                    <li>
                        <span class="badge {{ issue.severity_badge_class() }}">{{ issue.severity }}</span>
                        {{ issue.message }}
                        {% if issue.file_path %}
                        <small class="text-muted">({{ issue.file_path }})</small>
                        {% endif %}
                        {% if issue.validator %}
                        <small class="text-muted">[{{ issue.validator }}]</small>
                        {% endif %}
                    </li>
                    {% endfor %}
                </ul>
                {% endif %}
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Footer -->
        <div class="text-center text-muted mt-4 mb-4">
            <p>Generated by Synaptic Canvas Validation Report Generator</p>
            <p><small>Report file: {{ data.report_file }}</small></p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''


# ============================================================================
# Data Collection Functions
# ============================================================================


def get_marketplace_version(project_root: Path) -> Result[str, FileError]:
    """
    Get marketplace version from version.yaml.

    Args:
        project_root: Project root directory

    Returns:
        Success with version string, or Failure with error
    """
    version_file = project_root / "version.yaml"

    if not version_file.exists():
        return Failure(
            error=FileError(
                operation="read",
                path=str(version_file),
                message="version.yaml not found",
            )
        )

    try:
        with open(version_file) as f:
            data = yaml.safe_load(f)
            return Success(value=data.get("version", "unknown"))
    except Exception as e:
        return Failure(
            error=FileError(
                operation="read",
                path=str(version_file),
                message=str(e),
            )
        )


def extract_frontmatter_version(file_path: Path) -> Optional[str]:
    """Extract version from YAML frontmatter in markdown file."""
    try:
        with open(file_path) as f:
            content = f.read()

        # Match YAML frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if match:
            frontmatter = yaml.safe_load(match.group(1))
            if isinstance(frontmatter, dict):
                return frontmatter.get("version")
    except Exception:
        pass
    return None


def collect_package_versions(
    project_root: Path,
) -> Result[list[PackageVersion], ReportError]:
    """
    Collect version information for all packages.

    Args:
        project_root: Project root directory

    Returns:
        Success with list of PackageVersion, or Failure with error
    """
    packages_dir = project_root / "packages"
    if not packages_dir.exists():
        return Failure(
            error=ReportError(
                message="packages directory not found",
                file_path=str(packages_dir),
            )
        )

    package_versions = []
    warnings = []

    for package_dir in sorted(packages_dir.iterdir()):
        if not package_dir.is_dir() or package_dir.name.startswith("."):
            continue

        manifest_path = package_dir / "manifest.yaml"
        if not manifest_path.exists():
            warnings.append(f"No manifest.yaml in {package_dir.name}")
            continue

        try:
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
        except Exception as e:
            warnings.append(f"Error reading manifest in {package_dir.name}: {e}")
            continue

        pkg_version = PackageVersion(
            package_name=manifest.get("name", package_dir.name),
            manifest_version=manifest.get("version", "unknown"),
        )

        artifacts = manifest.get("artifacts", {})

        # Collect commands
        for cmd_path in artifacts.get("commands", []):
            full_path = package_dir / cmd_path
            version = extract_frontmatter_version(full_path)
            pkg_version.commands.append({
                "name": Path(cmd_path).stem,
                "version": version or "unknown",
            })
            if version != pkg_version.manifest_version:
                pkg_version.is_consistent = False

        # Collect skills
        for skill_path in artifacts.get("skills", []):
            full_path = package_dir / skill_path
            version = extract_frontmatter_version(full_path)
            pkg_version.skills.append({
                "name": Path(skill_path).parent.name,
                "version": version or "unknown",
            })
            if version != pkg_version.manifest_version:
                pkg_version.is_consistent = False

        # Collect agents
        for agent_path in artifacts.get("agents", []):
            full_path = package_dir / agent_path
            version = extract_frontmatter_version(full_path)
            pkg_version.agents.append({
                "name": Path(agent_path).stem,
                "version": version or "unknown",
            })
            if version != pkg_version.manifest_version:
                pkg_version.is_consistent = False

        # Collect scripts
        pkg_version.scripts = artifacts.get("scripts", [])

        package_versions.append(pkg_version)

    return Success(value=package_versions, warnings=warnings)


def collect_config_files(project_root: Path) -> list[FileInfo]:
    """
    Collect information about configuration files.

    Args:
        project_root: Project root directory

    Returns:
        List of FileInfo objects
    """
    config_patterns = [
        "version.yaml",
        ".claude-plugin/marketplace.json",
        ".claude-plugin/registry.json",
        ".claude/agents/registry.yaml",
        "packages/*/manifest.yaml",
        "packages/*/.claude-plugin/plugin.json",
    ]

    config_files = []

    for pattern in config_patterns:
        for path in project_root.glob(pattern):
            if path.is_file():
                try:
                    stat = path.stat()
                    config_files.append(
                        FileInfo(
                            path=path.relative_to(project_root).as_posix(),
                            modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            size_bytes=stat.st_size,
                        )
                    )
                except Exception:
                    pass

    return sorted(config_files, key=lambda f: f.path)


def run_validators(
    project_root: Path,
    verbose: bool = False,
) -> Result[list[ValidatorResult], ReportError]:
    """
    Run all validators and collect results.

    Args:
        project_root: Project root directory
        verbose: Enable verbose output

    Returns:
        Success with list of ValidatorResult, or Failure with error
    """
    # Import validators configuration from validate-all.py logic
    validators = [
        ("Version Consistency", ["python3", "scripts/audit-versions.py", "--verbose"]),
        ("Manifest Artifacts", ["python3", "scripts/validate-manifest-artifacts.py"]),
        ("Marketplace Sync", ["python3", "scripts/validate-marketplace-sync.py"]),
        ("Plugin JSON", ["python3", "scripts/validate-plugin-json.py"]),
        ("Agent Registry", ["python3", "scripts/validate-agents.py"]),
        ("Frontmatter Schema", ["python3", "scripts/validate-frontmatter-schema.py"]),
        ("Script References", ["python3", "scripts/validate-script-references.py"]),
        ("Cross References", ["python3", "scripts/validate-cross-references.py"]),
        ("Security Scan", ["python3", "scripts/security-scan.py"]),
    ]

    results = []
    import time

    for name, command in validators:
        if verbose:
            print(f"  Running: {name}...")

        start = time.time()
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=project_root,
            )
            duration = round(time.time() - start, 2)

            results.append(
                ValidatorResult(
                    name=name,
                    command=" ".join(command),
                    exit_code=proc.returncode,
                    passed=proc.returncode == 0,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    duration_seconds=duration,
                )
            )

        except FileNotFoundError:
            duration = round(time.time() - start, 2)
            results.append(
                ValidatorResult(
                    name=name,
                    command=" ".join(command),
                    exit_code=-1,
                    passed=False,
                    error_message=f"Script not found: {command[1] if len(command) > 1 else 'unknown'}",
                    duration_seconds=duration,
                )
            )

        except subprocess.TimeoutExpired:
            duration = round(time.time() - start, 2)
            results.append(
                ValidatorResult(
                    name=name,
                    command=" ".join(command),
                    exit_code=-1,
                    passed=False,
                    error_message="Timeout after 300 seconds",
                    duration_seconds=duration,
                )
            )

        except Exception as e:
            duration = round(time.time() - start, 2)
            results.append(
                ValidatorResult(
                    name=name,
                    command=" ".join(command),
                    exit_code=-1,
                    passed=False,
                    error_message=str(e),
                    duration_seconds=duration,
                )
            )

    return Success(value=results)


def run_pytest(
    project_root: Path,
    report_path: Path,
    verbose: bool = False,
) -> Result[TestSummary, ReportError]:
    """
    Run pytest and collect results.

    Args:
        project_root: Project root directory
        report_path: Path for HTML report
        verbose: Enable verbose output

    Returns:
        Success with TestSummary, or Failure with error
    """
    if verbose:
        print("  Running pytest...")

    json_report = project_root / "reports" / ".pytest-results.json"

    try:
        # Run pytest with JSON report
        command = [
            "python3", "-m", "pytest",
            "tests/",
            f"--json-report-file={json_report}",
            "--json-report",
            "-v",
            "--ignore=test-packages/",
        ]

        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=project_root,
        )

        summary = TestSummary()

        # Try to parse JSON report
        if json_report.exists():
            try:
                with open(json_report) as f:
                    data = json.load(f)

                summary_data = data.get("summary", {})
                summary.total = summary_data.get("total", 0)
                summary.passed = summary_data.get("passed", 0)
                summary.failed = summary_data.get("failed", 0)
                summary.skipped = summary_data.get("skipped", 0)
                summary.errors = summary_data.get("error", 0)
                summary.duration_seconds = round(data.get("duration", 0), 2)

            except Exception:
                # Parse from pytest output if JSON fails
                pass

        # If no JSON data, try to parse from output
        if summary.total == 0:
            # Parse something like: "10 passed, 2 failed, 1 skipped in 5.43s"
            match = re.search(
                r"(\d+) passed.*?(\d+) failed.*?in ([\d.]+)s",
                proc.stdout,
            )
            if match:
                summary.passed = int(match.group(1))
                summary.failed = int(match.group(2))
                summary.duration_seconds = float(match.group(3))
                summary.total = summary.passed + summary.failed

        summary.report_path = report_path.name if report_path.exists() else None

        # Clean up temp file
        if json_report.exists():
            json_report.unlink()

        return Success(value=summary)

    except subprocess.TimeoutExpired:
        return Failure(
            error=ReportError(
                message="pytest timed out after 600 seconds",
            )
        )

    except Exception as e:
        return Failure(
            error=ReportError(
                message=f"pytest failed: {e}",
            )
        )


def extract_issues(validator_results: list[ValidatorResult]) -> list[Issue]:
    """
    Extract issues from validator results.

    Args:
        validator_results: List of validator results

    Returns:
        List of Issue objects
    """
    issues = []

    for result in validator_results:
        if result.passed:
            continue

        # Determine severity based on validator
        if "security" in result.name.lower():
            severity = Severity.HIGH
        elif "cross" in result.name.lower() or "reference" in result.name.lower():
            severity = Severity.MEDIUM
        else:
            severity = Severity.HIGH

        # Create issue from failure
        issues.append(
            Issue(
                message=f"{result.name} validation failed (exit code: {result.exit_code})",
                severity=severity,
                validator=result.name,
                details={"stderr": result.stderr[:500] if result.stderr else ""},
            )
        )

        # Try to extract specific issues from stderr/stdout
        output = result.stderr or result.stdout
        if output:
            for line in output.split("\n"):
                line = line.strip()
                if any(marker in line.lower() for marker in ["error:", "fail:", "missing:", "invalid:"]):
                    issues.append(
                        Issue(
                            message=line[:200],
                            severity=Severity.MEDIUM,
                            validator=result.name,
                        )
                    )

    return issues


# ============================================================================
# Report Generation
# ============================================================================


def render_html_report(data: ReportData) -> str:
    """
    Render HTML report using template.

    Args:
        data: Report data

    Returns:
        HTML string
    """
    try:
        from jinja2 import Template
        template = Template(HTML_TEMPLATE)
        return template.render(data=data)
    except ImportError:
        # Fallback: simple string replacement
        html = HTML_TEMPLATE
        html = html.replace("{{ data.timestamp }}", data.timestamp)
        html = html.replace("{{ data.marketplace_version or 'N/A' }}", data.marketplace_version or "N/A")
        html = html.replace("{{ data.total_packages }}", str(data.total_packages))
        html = html.replace("{{ data.report_file }}", data.report_file)
        return html


def generate_report_filename(prefix: str = "validation") -> str:
    """Generate timestamped report filename."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    return f"{timestamp}-{prefix}-report.html"


def cleanup_old_reports(
    reports_dir: Path,
    keep_count: int = 5,
    pattern: str = "*-validation-report.html",
) -> list[Path]:
    """
    Remove old reports, keeping only the most recent ones.

    Args:
        reports_dir: Reports directory
        keep_count: Number of reports to keep
        pattern: Glob pattern for report files

    Returns:
        List of deleted file paths
    """
    if not reports_dir.exists():
        return []

    # Get all matching reports sorted by modification time (newest first)
    reports = sorted(
        reports_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Delete old reports
    deleted = []
    for old_report in reports[keep_count:]:
        try:
            old_report.unlink()
            deleted.append(old_report)
        except Exception:
            pass

    return deleted


def generate_validation_report(
    project_root: Path,
    output_path: Optional[Path] = None,
    skip_tests: bool = False,
    keep_reports: int = 5,
    no_cleanup: bool = False,
    verbose: bool = False,
) -> Result[ReportData, ReportError]:
    """
    Generate comprehensive validation report.

    Args:
        project_root: Project root directory
        output_path: Custom output path (optional)
        skip_tests: Skip running pytest
        keep_reports: Number of reports to keep (default 5)
        no_cleanup: Skip cleanup of old reports
        verbose: Enable verbose output

    Returns:
        Success with ReportData, or Failure with error
    """
    warnings = []

    # Ensure reports directory exists
    reports_dir = project_root / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Generate report filename
    if output_path:
        report_file = output_path
    else:
        report_file = reports_dir / generate_report_filename()

    if verbose:
        print(f"Generating validation report: {report_file}")

    # Initialize report data
    data = ReportData(report_file=report_file.name)

    # Get marketplace version
    if verbose:
        print("  Collecting marketplace version...")
    version_result = get_marketplace_version(project_root)
    if isinstance(version_result, Success):
        data.marketplace_version = version_result.value
    else:
        warnings.append(f"Could not get marketplace version: {version_result.error.message}")

    # Collect package versions
    if verbose:
        print("  Collecting package versions...")
    packages_result = collect_package_versions(project_root)
    if isinstance(packages_result, Success):
        data.package_versions = packages_result.value
        data.total_packages = len(packages_result.value)
        warnings.extend(packages_result.warnings)
    else:
        warnings.append(f"Could not collect packages: {packages_result.error.message}")

    # Collect config files
    if verbose:
        print("  Collecting configuration files...")
    data.config_files = collect_config_files(project_root)

    # Run validators
    if verbose:
        print("  Running validators...")
    validators_result = run_validators(project_root, verbose)
    if isinstance(validators_result, Success):
        data.validator_results = validators_result.value
        data.validation_passed = sum(1 for r in validators_result.value if r.passed)
        data.validation_failed = sum(1 for r in validators_result.value if not r.passed)

        # Extract issues
        data.issues = extract_issues(validators_result.value)
    else:
        warnings.append(f"Validator error: {validators_result.error.message}")

    # Run pytest (unless skipped)
    test_report_file = None
    if not skip_tests:
        if verbose:
            print("  Running unit tests...")
        test_report_file = reports_dir / generate_report_filename("unit-test")
        test_result = run_pytest(project_root, test_report_file, verbose)
        if isinstance(test_result, Success):
            data.test_summary = test_result.value
        else:
            warnings.append(f"Test error: {test_result.error.message}")

    # Determine overall status
    data.overall_passed = (
        data.validation_failed == 0
        and data.test_summary.failed == 0
        and data.test_summary.errors == 0
    )

    # Render HTML
    if verbose:
        print("  Rendering HTML report...")
    html_content = render_html_report(data)

    # Write report
    try:
        with open(report_file, "w") as f:
            f.write(html_content)
    except Exception as e:
        return Failure(
            error=ReportError(
                message=f"Failed to write report: {e}",
                file_path=str(report_file),
            )
        )

    # Cleanup old reports
    if not no_cleanup:
        if verbose:
            print(f"  Cleaning up old reports (keeping {keep_reports})...")

        deleted = cleanup_old_reports(reports_dir, keep_reports, "*-validation-report.html")
        deleted.extend(cleanup_old_reports(reports_dir, keep_reports, "*-unit-test-report.html"))

        if deleted and verbose:
            for f in deleted:
                print(f"    Deleted: {f.name}")

    if verbose:
        print(f"\nReport generated: {report_file}")

    return Success(value=data, warnings=warnings)


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive HTML validation report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate full validation report:
    python3 scripts/generate-validation-report.py

  Skip running pytest (faster):
    python3 scripts/generate-validation-report.py --skip-tests

  Keep more reports:
    python3 scripts/generate-validation-report.py --keep-reports 10

  Keep all reports (no cleanup):
    python3 scripts/generate-validation-report.py --no-cleanup

  Custom output path:
    python3 scripts/generate-validation-report.py --output reports/custom.html

  Verbose output:
    python3 scripts/generate-validation-report.py --verbose
""",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Custom output path for the report",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest unit tests",
    )
    parser.add_argument(
        "--keep-reports",
        type=int,
        default=5,
        help="Number of reports to keep (default: 5)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't delete old reports",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args()

    # Generate report
    result = generate_validation_report(
        project_root=args.project_root,
        output_path=args.output,
        skip_tests=args.skip_tests,
        keep_reports=args.keep_reports,
        no_cleanup=args.no_cleanup,
        verbose=args.verbose,
    )

    if isinstance(result, Failure):
        print(f"Error: {result.error.message}")
        return 1

    data = result.value

    # Print summary
    if not args.verbose:
        print(f"\nValidation Report Generated: {data.report_file}")
        print(f"  Overall Status: {'PASS' if data.overall_passed else 'FAIL'}")
        print(f"  Packages: {data.total_packages}")
        print(f"  Validators: {data.validation_passed} passed, {data.validation_failed} failed")
        if data.test_summary.total > 0:
            print(f"  Tests: {data.test_summary.passed} passed, {data.test_summary.failed} failed")
        print(f"  Issues: {len(data.issues)}")

    # Print warnings
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    return 0 if data.overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
