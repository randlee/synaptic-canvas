"""Tests for token usage extraction from Claude transcripts.

Tests the extraction of token usage metrics from Claude transcript entries,
including:
- Direct Claude API responses (type: "assistant" with message.usage)
- Subagent results (toolUseResult with totalTokens)
- Aggregation across multiple entries
- Edge cases (empty, missing fields, partial data)

Note: The extract_token_usage() function may not exist yet (Agent 7A is creating it).
These tests are designed to verify the expected behavior once implemented.
"""

import pytest
from typing import List, Dict, Any

from harness.schemas import TokenUsage


# =============================================================================
# Test Fixtures - Sample Transcript Entries
# =============================================================================


SAMPLE_ASSISTANT_MESSAGE = {
    "uuid": "msg-1",
    "type": "assistant",
    "message": {
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_creation_input_tokens": 1000,
            "cache_read_input_tokens": 5000
        }
    }
}

SAMPLE_ASSISTANT_MESSAGE_2 = {
    "uuid": "msg-2",
    "type": "assistant",
    "message": {
        "usage": {
            "input_tokens": 200,
            "output_tokens": 75,
            "cache_creation_input_tokens": 500,
            "cache_read_input_tokens": 3000
        }
    }
}

SAMPLE_TOOL_RESULT = {
    "uuid": "tool-1",
    "type": "tool_result",
    "toolUseResult": {
        "totalTokens": 2500,
        "totalToolUseCount": 10
    }
}

SAMPLE_TOOL_RESULT_2 = {
    "uuid": "tool-2",
    "type": "tool_result",
    "toolUseResult": {
        "totalTokens": 1500,
        "totalToolUseCount": 5
    }
}

SAMPLE_USER_MESSAGE = {
    "uuid": "user-1",
    "type": "user",
    "message": {
        "role": "user",
        "content": "Hello!"
    }
}

SAMPLE_SYSTEM_MESSAGE = {
    "uuid": "sys-1",
    "type": "system",
    "message": {
        "type": "init"
    }
}


# =============================================================================
# TokenUsage Model Tests
# =============================================================================


class TestTokenUsageModel:
    """Tests for the TokenUsage Pydantic model."""

    def test_token_usage_model_defaults(self):
        """Verify default values are 0 for all fields."""
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_creation_tokens == 0
        assert usage.cache_read_tokens == 0
        assert usage.subagent_tokens == 0

    def test_token_usage_total_billable(self):
        """Verify billable excludes cache reads and subagent tokens."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=1000,
            cache_read_tokens=5000,
            subagent_tokens=2500,
        )
        # Billable = input + output + cache_creation (excludes cache_read and subagent)
        expected_billable = 100 + 50 + 1000
        assert usage.total_billable == expected_billable

    def test_token_usage_total_all(self):
        """Verify total includes everything."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=1000,
            cache_read_tokens=5000,
            subagent_tokens=2500,
        )
        # Total = billable + cache_read + subagent
        expected_total = (100 + 50 + 1000) + 5000 + 2500
        assert usage.total_all == expected_total

    def test_token_usage_from_dict(self):
        """Test model creation from dictionary."""
        data = {
            "input_tokens": 46,
            "output_tokens": 9,
            "cache_creation_tokens": 15466,
            "cache_read_tokens": 99728,
            "subagent_tokens": 11414,
        }
        usage = TokenUsage(**data)
        assert usage.input_tokens == 46
        assert usage.output_tokens == 9
        assert usage.cache_creation_tokens == 15466
        assert usage.cache_read_tokens == 99728
        assert usage.subagent_tokens == 11414

    def test_token_usage_partial_fields(self):
        """Test model with only some fields specified."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cache_creation_tokens == 0
        assert usage.cache_read_tokens == 0
        assert usage.subagent_tokens == 0
        # Total billable should still work
        assert usage.total_billable == 150

    def test_token_usage_serialization(self):
        """Test model serialization to dict."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=1000,
        )
        data = usage.model_dump()
        assert data["input_tokens"] == 100
        assert data["output_tokens"] == 50
        assert data["cache_creation_tokens"] == 1000
        assert data["cache_read_tokens"] == 0
        assert data["subagent_tokens"] == 0


# =============================================================================
# Token Extraction Function Tests
# =============================================================================


# Attempt to import the extraction function
# It may be in either enrichment (preferred) or collector module
try:
    from harness.enrichment import extract_token_usage
    EXTRACTION_AVAILABLE = True
except ImportError:
    try:
        from harness.collector import extract_token_usage
        EXTRACTION_AVAILABLE = True
    except ImportError:
        EXTRACTION_AVAILABLE = False
        # Define a placeholder for the tests
        def extract_token_usage(entries: List[Dict[str, Any]]) -> TokenUsage:
            raise NotImplementedError("extract_token_usage not yet implemented")


@pytest.mark.skipif(not EXTRACTION_AVAILABLE, reason="extract_token_usage not yet implemented")
class TestExtractTokenUsage:
    """Tests for extract_token_usage function."""

    def test_extract_from_single_assistant_message(self):
        """Basic extraction from a single assistant message."""
        entries = [SAMPLE_ASSISTANT_MESSAGE]
        usage = extract_token_usage(entries)

        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cache_creation_tokens == 1000
        assert usage.cache_read_tokens == 5000
        assert usage.subagent_tokens == 0

    def test_extract_from_multiple_messages(self):
        """Aggregation across multiple assistant messages."""
        entries = [SAMPLE_ASSISTANT_MESSAGE, SAMPLE_ASSISTANT_MESSAGE_2]
        usage = extract_token_usage(entries)

        # Should sum across all messages
        assert usage.input_tokens == 100 + 200
        assert usage.output_tokens == 50 + 75
        assert usage.cache_creation_tokens == 1000 + 500
        assert usage.cache_read_tokens == 5000 + 3000
        assert usage.subagent_tokens == 0

    def test_extract_subagent_tokens(self):
        """Extract tokens from toolUseResult entries."""
        entries = [SAMPLE_TOOL_RESULT]
        usage = extract_token_usage(entries)

        assert usage.subagent_tokens == 2500
        # Direct tokens should be 0 when only tool results present
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_extract_mixed_transcript(self):
        """Both assistant messages and tool_result entries."""
        entries = [
            SAMPLE_ASSISTANT_MESSAGE,
            SAMPLE_TOOL_RESULT,
            SAMPLE_ASSISTANT_MESSAGE_2,
            SAMPLE_TOOL_RESULT_2,
        ]
        usage = extract_token_usage(entries)

        # Assistant messages
        assert usage.input_tokens == 100 + 200
        assert usage.output_tokens == 50 + 75
        assert usage.cache_creation_tokens == 1000 + 500
        assert usage.cache_read_tokens == 5000 + 3000

        # Tool results (subagent tokens)
        assert usage.subagent_tokens == 2500 + 1500

    def test_extract_empty_transcript(self):
        """Handle empty list gracefully."""
        entries = []
        usage = extract_token_usage(entries)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_creation_tokens == 0
        assert usage.cache_read_tokens == 0
        assert usage.subagent_tokens == 0

    def test_extract_missing_usage_fields(self):
        """Handle entries without usage fields gracefully."""
        # User and system messages don't have usage data
        entries = [SAMPLE_USER_MESSAGE, SAMPLE_SYSTEM_MESSAGE]
        usage = extract_token_usage(entries)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_creation_tokens == 0
        assert usage.cache_read_tokens == 0
        assert usage.subagent_tokens == 0

    def test_extract_partial_usage_fields(self):
        """Handle entries with some usage fields missing."""
        partial_entry = {
            "uuid": "msg-partial",
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    # Missing cache fields
                }
            }
        }
        entries = [partial_entry]
        usage = extract_token_usage(entries)

        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cache_creation_tokens == 0  # Should default to 0
        assert usage.cache_read_tokens == 0  # Should default to 0
        assert usage.subagent_tokens == 0

    def test_extract_with_none_message(self):
        """Handle assistant entries with None message."""
        entry_with_none = {
            "uuid": "msg-none",
            "type": "assistant",
            "message": None
        }
        entries = [entry_with_none]
        usage = extract_token_usage(entries)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_extract_with_empty_usage(self):
        """Handle assistant entries with empty usage dict."""
        entry_with_empty_usage = {
            "uuid": "msg-empty-usage",
            "type": "assistant",
            "message": {
                "usage": {}
            }
        }
        entries = [entry_with_empty_usage]
        usage = extract_token_usage(entries)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_creation_tokens == 0
        assert usage.cache_read_tokens == 0

    def test_extract_tool_result_without_total_tokens(self):
        """Handle toolUseResult without totalTokens field."""
        entry_no_total = {
            "uuid": "tool-no-total",
            "type": "tool_result",
            "toolUseResult": {
                "totalToolUseCount": 5
                # Missing totalTokens
            }
        }
        entries = [entry_no_total]
        usage = extract_token_usage(entries)

        assert usage.subagent_tokens == 0

    def test_extract_tool_result_without_toolUseResult(self):
        """Handle tool_result type without toolUseResult dict."""
        entry_no_result = {
            "uuid": "tool-no-result",
            "type": "tool_result",
            # Missing toolUseResult
        }
        entries = [entry_no_result]
        usage = extract_token_usage(entries)

        assert usage.subagent_tokens == 0


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.skipif(not EXTRACTION_AVAILABLE, reason="extract_token_usage not yet implemented")
class TestTokenExtractionIntegration:
    """Integration tests for token extraction with enrichment pipeline."""

    def test_realistic_transcript(self):
        """Test with a realistic multi-turn transcript."""
        # Simulates a typical Claude Code session
        transcript = [
            # Initial system/summary
            {
                "uuid": "uuid-1",
                "type": "summary",
                "message": {"type": "init"}
            },
            # User prompt
            {
                "uuid": "uuid-2",
                "type": "user",
                "message": {"role": "user", "content": "List files"}
            },
            # First assistant response
            {
                "uuid": "uuid-3",
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 200,
                        "cache_creation_input_tokens": 5000,
                        "cache_read_input_tokens": 0
                    },
                    "content": [{"type": "tool_use", "name": "Bash"}]
                }
            },
            # Tool result
            {
                "uuid": "uuid-4",
                "type": "tool_result",
                "toolUseResult": {
                    "totalTokens": 500,
                    "totalToolUseCount": 1
                }
            },
            # Second assistant response (using cache)
            {
                "uuid": "uuid-5",
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "usage": {
                        "input_tokens": 50,
                        "output_tokens": 100,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 5000
                    },
                    "content": [{"type": "text", "text": "Done!"}]
                }
            },
        ]

        usage = extract_token_usage(transcript)

        # Verify aggregation
        assert usage.input_tokens == 1000 + 50
        assert usage.output_tokens == 200 + 100
        assert usage.cache_creation_tokens == 5000 + 0
        assert usage.cache_read_tokens == 0 + 5000
        assert usage.subagent_tokens == 500

        # Verify computed properties
        assert usage.total_billable == 1050 + 300 + 5000  # 6350
        assert usage.total_all == 6350 + 5000 + 500  # 11850


# =============================================================================
# Tests for Enrichment Integration (if enrichment uses token extraction)
# =============================================================================


try:
    from harness.enrichment import build_timeline_tree
    from harness.schemas import TestContext, TestContextPaths, ArtifactPaths
    ENRICHMENT_AVAILABLE = True
except ImportError:
    ENRICHMENT_AVAILABLE = False


@pytest.mark.skipif(not ENRICHMENT_AVAILABLE, reason="enrichment module not available")
class TestEnrichmentTokenUsage:
    """Tests that enrichment integrates token usage into stats."""

    @pytest.fixture
    def test_context(self):
        """Create a minimal test context."""
        return TestContext(
            fixture_id="test-fixture",
            test_id="test-001",
            test_name="Test Name",
            package="test-package",
            paths=TestContextPaths(
                fixture_yaml="fixtures/test.yaml",
                test_yaml="tests/test.yaml",
            )
        )

    @pytest.fixture
    def artifact_paths(self):
        """Create minimal artifact paths."""
        return ArtifactPaths(
            transcript="reports/test-transcript.jsonl",
            trace="reports/test-trace.jsonl",
            enriched="reports/test-enriched.json",
        )

    @pytest.mark.skipif(not EXTRACTION_AVAILABLE, reason="extract_token_usage not yet implemented")
    def test_enrichment_includes_token_usage(self, test_context, artifact_paths):
        """Verify enrichment populates token_usage in stats.

        This test verifies the integration between token extraction
        and the enrichment pipeline. The build_timeline_tree function
        should extract tokens and include them in TreeStats.
        """
        # Transcript with usage data
        transcript = [
            {
                "uuid": "uuid-1",
                "type": "assistant",
                "message": {
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cache_creation_input_tokens": 500,
                        "cache_read_input_tokens": 1000,
                    }
                }
            }
        ]
        trace = []

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=trace,
            test_context=test_context,
            artifact_paths=artifact_paths,
        )

        # build_timeline_tree now returns Result - unwrap it
        from harness.result import Success
        assert isinstance(result, Success), f"Expected Success, got {type(result)}"
        enriched_data = result.value

        # Check that stats includes token_usage
        assert enriched_data.stats.token_usage is not None
        assert enriched_data.stats.token_usage.input_tokens == 100
        assert enriched_data.stats.token_usage.output_tokens == 50
        assert enriched_data.stats.token_usage.cache_creation_tokens == 500
        assert enriched_data.stats.token_usage.cache_read_tokens == 1000

    @pytest.mark.skipif(not EXTRACTION_AVAILABLE, reason="extract_token_usage not yet implemented")
    def test_enrichment_with_no_usage_data(self, test_context, artifact_paths):
        """Verify enrichment handles transcripts without usage data."""
        # Transcript without usage fields
        transcript = [
            {
                "uuid": "uuid-1",
                "type": "user",
                "message": {"content": "Hello"}
            }
        ]
        trace = []

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=trace,
            test_context=test_context,
            artifact_paths=artifact_paths,
        )

        # build_timeline_tree now returns Result - unwrap it
        from harness.result import Success
        assert isinstance(result, Success), f"Expected Success, got {type(result)}"
        enriched_data = result.value

        # token_usage should exist but be zeros (or None - depends on implementation)
        if enriched_data.stats.token_usage is not None:
            assert enriched_data.stats.token_usage.input_tokens == 0
            assert enriched_data.stats.token_usage.output_tokens == 0
