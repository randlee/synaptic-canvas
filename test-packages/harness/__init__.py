"""
Claude Code Test Harness

A testing framework for validating Claude Code skills, commands, and agents.
Provides environment isolation, data collection, and report generation.

Modules:
    - models: Pydantic models for the v3.0 report schema
    - environment: Environment isolation (HOME override, cleanup)
    - collector: Data collection from hooks and transcripts
    - expectations: Assertions and expectations framework
    - reporter: JSON and HTML report generation
    - runner: Test orchestration and execution
    - fixture_loader: YAML fixture loading and parsing
    - pytest_plugin: Pytest integration for dynamic test generation

Example usage:
    from harness.environment import isolated_claude_session
    from harness.collector import DataCollector
    from harness.expectations import (
        ToolCallExpectation,
        OutputContainsExpectation,
        evaluate_expectations,
    )
    from harness.reporter import ReportBuilder

    with isolated_claude_session() as session:
        # Run Claude with isolated environment
        result = session.run_prompt("/sc-startup --readonly")

        # Collect data from hooks and transcript
        collector = DataCollector(session.trace_path, session.transcript_path)
        data = collector.collect()

        # Define and evaluate expectations
        expectations = [
            ToolCallExpectation(
                id="exp-001",
                description="Read config",
                tool="Bash",
                pattern=r"cat.*config\\.yaml",
            ),
            OutputContainsExpectation(
                id="exp-002",
                description="Report generated",
                pattern=r"Report",
            ),
        ]
        results = evaluate_expectations(expectations, data)

        # Build report
        report = ReportBuilder(data, results).build()

YAML Fixture Testing:
    from harness.fixture_loader import FixtureLoader

    # Discover and load fixtures
    loader = FixtureLoader("/path/to/fixtures")
    fixtures = loader.discover_fixtures()
    config = loader.load_fixture("sc-startup")

    # Or run tests with pytest
    # pytest test-packages/fixtures/ -v
"""

__version__ = "0.1.0"
__all__ = [
    "models",
    "environment",
    "collector",
    "expectations",
    "reporter",
    "runner",
    "fixture_loader",
    "pytest_plugin",
]
