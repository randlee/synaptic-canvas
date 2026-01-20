#!/usr/bin/env python3
"""
generate-validation-report.py - Generate HTML validation reports

Usage:
  python3 scripts/generate-validation-report.py [--output <path>] [--open] [--keep-reports <n>]

Options:
  --output PATH       Output path for HTML report (default: .claude/reports/validation/)
  --open              Open the report in browser after generation
  --keep-reports N    Keep only the last N reports (default: 5)
  --skip-cleanup      Skip cleanup of old reports
  --json FILE         Use existing JSON output from validate-all.py
  --help              Show this help message

Exit Codes:
  0: Report generated successfully
  1: Failed to generate report

This script runs validate-all.py --json and converts the output to an HTML report
with pass/fail status, timing information, and detailed error messages.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def find_repo_root() -> Path:
    """Find the repository root directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent


def run_validation(repo_root: Path) -> Dict[str, Any]:
    """Run validate-all.py and return JSON results."""
    script_path = repo_root / "scripts" / "validate-all.py"

    if not script_path.exists():
        raise FileNotFoundError(f"validate-all.py not found at {script_path}")

    result = subprocess.run(
        [sys.executable, str(script_path), "--json"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        timeout=600,  # 10 minute timeout
    )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse validation output: {e}\n{result.stdout}")


def generate_html_report(data: Dict[str, Any], repo_root: Path) -> str:
    """Generate HTML report from validation data."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overall_status = "PASSED" if data["passed"] else "FAILED"
    status_class = "pass" if data["passed"] else "fail"

    results_html = []
    for r in data["results"]:
        if r["skipped"]:
            row_class = "skip"
            status = "SKIPPED"
            details = r.get("skip_reason", "")
        elif r["passed"]:
            row_class = "pass"
            status = "PASSED"
            details = ""
        else:
            row_class = "fail"
            status = "FAILED"
            details = r.get("error", "")

        details_html = ""
        if details:
            escaped_details = (
                details.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            details_html = f'<div class="details"><pre>{escaped_details}</pre></div>'

        results_html.append(f"""
        <tr class="{row_class}">
            <td class="name">{r['name']}</td>
            <td class="status">{status}</td>
            <td class="duration">{r['duration_ms']:.0f}ms</td>
        </tr>
        {f'<tr class="{row_class}"><td colspan="3">{details_html}</td></tr>' if details_html else ''}
        """)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Report - {timestamp}</title>
    <style>
        :root {{
            --pass-color: #22c55e;
            --fail-color: #ef4444;
            --skip-color: #f59e0b;
            --bg-color: #1a1a2e;
            --card-bg: #16213e;
            --text-color: #e2e8f0;
            --border-color: #334155;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            padding: 2rem;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 2rem;
            padding: 2rem;
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }}

        h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .timestamp {{
            color: #94a3b8;
            font-size: 0.9rem;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .summary-card {{
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
            border: 1px solid var(--border-color);
        }}

        .summary-card.overall {{
            grid-column: 1 / -1;
        }}

        .summary-card h2 {{
            font-size: 0.9rem;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 0.5rem;
        }}

        .summary-card .value {{
            font-size: 2rem;
            font-weight: bold;
        }}

        .summary-card.pass .value {{ color: var(--pass-color); }}
        .summary-card.fail .value {{ color: var(--fail-color); }}
        .summary-card.skip .value {{ color: var(--skip-color); }}

        .results {{
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            overflow: hidden;
        }}

        .results h2 {{
            padding: 1rem 1.5rem;
            background: rgba(0,0,0,0.2);
            font-size: 1.1rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th, td {{
            padding: 1rem 1.5rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            background: rgba(0,0,0,0.2);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            color: #94a3b8;
        }}

        tr.pass {{ background: rgba(34, 197, 94, 0.1); }}
        tr.fail {{ background: rgba(239, 68, 68, 0.1); }}
        tr.skip {{ background: rgba(245, 158, 11, 0.1); }}

        td.status {{
            font-weight: 600;
        }}

        tr.pass td.status {{ color: var(--pass-color); }}
        tr.fail td.status {{ color: var(--fail-color); }}
        tr.skip td.status {{ color: var(--skip-color); }}

        td.duration {{
            color: #94a3b8;
            font-family: monospace;
        }}

        .details {{
            padding: 0;
        }}

        .details pre {{
            background: rgba(0,0,0,0.3);
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 0.85rem;
            color: #f87171;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        footer {{
            text-align: center;
            margin-top: 2rem;
            color: #64748b;
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Synaptic Canvas Validation Report</h1>
            <p class="timestamp">Generated: {timestamp}</p>
            <p class="timestamp">Repository: {repo_root}</p>
        </header>

        <div class="summary">
            <div class="summary-card overall {status_class}">
                <h2>Overall Status</h2>
                <div class="value">{overall_status}</div>
            </div>
            <div class="summary-card pass">
                <h2>Passed</h2>
                <div class="value">{data['counts']['passed']}</div>
            </div>
            <div class="summary-card fail">
                <h2>Failed</h2>
                <div class="value">{data['counts']['failed']}</div>
            </div>
            <div class="summary-card skip">
                <h2>Skipped</h2>
                <div class="value">{data['counts']['skipped']}</div>
            </div>
            <div class="summary-card">
                <h2>Duration</h2>
                <div class="value">{data['total_duration_ms']:.0f}ms</div>
            </div>
        </div>

        <div class="results">
            <h2>Validation Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Validator</th>
                        <th>Status</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(results_html)}
                </tbody>
            </table>
        </div>

        <footer>
            <p>Synaptic Canvas Validation Suite</p>
        </footer>
    </div>
</body>
</html>
"""
    return html


def cleanup_old_reports(reports_dir: Path, keep_count: int) -> List[Path]:
    """Remove old reports, keeping only the most recent ones."""
    if keep_count < 0:
        return []

    report_files = sorted(
        reports_dir.glob("validation-*.html"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    removed = []
    for report in report_files[keep_count:]:
        report.unlink()
        removed.append(report)

    return removed


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate HTML validation reports"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for HTML report (default: .claude/reports/validation/)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the report in browser after generation",
    )
    parser.add_argument(
        "--keep-reports",
        type=int,
        default=5,
        help="Keep only the last N reports (default: 5)",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip cleanup of old reports",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Use existing JSON output file instead of running validation",
    )

    args = parser.parse_args()

    repo_root = find_repo_root()

    # Determine output directory
    if args.output:
        output_path = Path(args.output)
        if output_path.is_dir():
            reports_dir = output_path
            output_file = None
        else:
            reports_dir = output_path.parent
            output_file = output_path
    else:
        reports_dir = repo_root / ".claude" / "reports" / "validation"
        output_file = None

    # Ensure output directory exists
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Get validation data
    print("Running validation suite...")
    try:
        if args.json:
            with open(args.json) as f:
                data = json.load(f)
        else:
            data = run_validation(repo_root)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Generate report
    print("Generating HTML report...")
    html = generate_html_report(data, repo_root)

    # Determine output filename
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = reports_dir / f"validation-{timestamp}.html"

    # Write report
    output_file.write_text(html, encoding="utf-8")
    print(f"Report saved: {output_file}")

    # Cleanup old reports
    if not args.skip_cleanup:
        removed = cleanup_old_reports(reports_dir, args.keep_reports)
        if removed:
            print(f"Cleaned up {len(removed)} old report(s)")

    # Open in browser if requested
    if args.open:
        print("Opening report in browser...")
        webbrowser.open(f"file://{output_file.resolve()}")

    # Print summary
    status = "PASSED" if data["passed"] else "FAILED"
    print(f"\nValidation {status}")
    print(f"  Passed: {data['counts']['passed']}")
    print(f"  Failed: {data['counts']['failed']}")
    print(f"  Skipped: {data['counts']['skipped']}")

    return 0 if data["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
