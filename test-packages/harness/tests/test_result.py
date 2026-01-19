"""
Unit tests for harness.result module.

Tests the Result[T, E] discriminated union pattern including:
- Success and Failure creation
- Error types (EnrichmentError, ArtifactError)
- Helper functions for result composition
"""

import pytest

from harness.result import (
    AggregateError,
    ArtifactError,
    EnrichmentError,
    Failure,
    Result,
    Success,
    collect_results,
    flat_map_result,
    map_result,
    unwrap_or,
    unwrap_or_else,
)


class TestSuccess:
    """Tests for Success dataclass."""

    def test_create_success_with_value(self):
        """Test creating a Success with a value."""
        result = Success(value=42)
        assert result.value == 42
        assert result.warnings == []

    def test_create_success_with_warnings(self):
        """Test creating a Success with warnings."""
        result = Success(value="data", warnings=["warning1", "warning2"])
        assert result.value == "data"
        assert result.warnings == ["warning1", "warning2"]

    def test_is_success_returns_true(self):
        """Test that is_success() returns True for Success."""
        result = Success(value=100)
        assert result.is_success() is True

    def test_is_failure_returns_false(self):
        """Test that is_failure() returns False for Success."""
        result = Success(value="test")
        assert result.is_failure() is False

    def test_success_with_complex_value(self):
        """Test Success with a complex value type."""
        data = {"key": "value", "numbers": [1, 2, 3]}
        result = Success(value=data)
        assert result.value == {"key": "value", "numbers": [1, 2, 3]}

    def test_success_with_none_value(self):
        """Test Success with None as value (valid use case)."""
        result = Success(value=None)
        assert result.value is None
        assert result.is_success() is True


class TestFailure:
    """Tests for Failure dataclass."""

    def test_create_failure_with_error(self):
        """Test creating a Failure with an error."""
        error = "Something went wrong"
        result = Failure(error=error)
        assert result.error == "Something went wrong"
        assert result.partial_result is None

    def test_create_failure_with_partial_result(self):
        """Test creating a Failure with a partial result."""
        error = "Processing stopped"
        partial = {"processed": 5, "remaining": 10}
        result = Failure(error=error, partial_result=partial)
        assert result.error == "Processing stopped"
        assert result.partial_result == {"processed": 5, "remaining": 10}

    def test_is_success_returns_false(self):
        """Test that is_success() returns False for Failure."""
        result = Failure(error="error")
        assert result.is_success() is False

    def test_is_failure_returns_true(self):
        """Test that is_failure() returns True for Failure."""
        result = Failure(error="error")
        assert result.is_failure() is True

    def test_failure_with_typed_error(self):
        """Test Failure with a typed error object."""
        error = EnrichmentError(
            phase="tree_build",
            message="Failed to build tree",
            context={"node_count": 100},
        )
        result = Failure(error=error)
        assert result.error.phase == "tree_build"
        assert result.error.message == "Failed to build tree"


class TestEnrichmentError:
    """Tests for EnrichmentError dataclass."""

    def test_create_enrichment_error(self):
        """Test creating an EnrichmentError."""
        error = EnrichmentError(phase="index", message="Index failed")
        assert error.phase == "index"
        assert error.message == "Index failed"
        assert error.context == {}

    def test_enrichment_error_with_context(self):
        """Test EnrichmentError with context data."""
        error = EnrichmentError(
            phase="depth_compute",
            message="Depth computation failed",
            context={"max_depth": 10, "current_node": "node-42"},
        )
        assert error.phase == "depth_compute"
        assert error.context["max_depth"] == 10
        assert error.context["current_node"] == "node-42"

    def test_enrichment_error_phases(self):
        """Test common enrichment phases."""
        phases = ["index", "tree_build", "depth_compute", "validation"]
        for phase in phases:
            error = EnrichmentError(phase=phase, message=f"{phase} error")
            assert error.phase == phase


class TestArtifactError:
    """Tests for ArtifactError dataclass."""

    def test_create_artifact_error(self):
        """Test creating an ArtifactError."""
        error = ArtifactError(
            operation="read",
            path="/path/to/file.json",
            message="File not found",
        )
        assert error.operation == "read"
        assert error.path == "/path/to/file.json"
        assert error.message == "File not found"

    def test_artifact_error_operations(self):
        """Test common artifact operations."""
        operations = ["read", "write", "validate"]
        for op in operations:
            error = ArtifactError(
                operation=op,
                path="/test/path",
                message=f"{op} failed",
            )
            assert error.operation == op


class TestCollectResults:
    """Tests for collect_results function."""

    def test_collect_all_success(self):
        """Test collecting all successful results."""
        results: list[Result[int, str]] = [
            Success(value=1),
            Success(value=2),
            Success(value=3),
        ]
        collected = collect_results(results)

        assert isinstance(collected, Success)
        assert collected.value == [1, 2, 3]
        assert collected.warnings == []

    def test_collect_success_with_warnings(self):
        """Test collecting successful results accumulates warnings."""
        results: list[Result[str, str]] = [
            Success(value="a", warnings=["warn1"]),
            Success(value="b", warnings=["warn2", "warn3"]),
            Success(value="c"),
        ]
        collected = collect_results(results)

        assert isinstance(collected, Success)
        assert collected.value == ["a", "b", "c"]
        assert collected.warnings == ["warn1", "warn2", "warn3"]

    def test_collect_with_single_failure(self):
        """Test collecting results with one failure."""
        results: list[Result[int, str]] = [
            Success(value=1),
            Failure(error="error occurred"),
            Success(value=3),
        ]
        collected = collect_results(results)

        assert isinstance(collected, Failure)
        assert isinstance(collected.error, AggregateError)
        assert len(collected.error.errors) == 1
        assert collected.error.errors[0] == "error occurred"
        # Partial results should contain successful values
        assert collected.partial_result == [1, 3]

    def test_collect_with_multiple_failures(self):
        """Test collecting results with multiple failures."""
        results: list[Result[int, str]] = [
            Failure(error="error1"),
            Failure(error="error2", partial_result="partial"),
            Success(value=1),
        ]
        collected = collect_results(results)

        assert isinstance(collected, Failure)
        assert len(collected.error.errors) == 2
        assert "error1" in collected.error.errors
        assert "error2" in collected.error.errors
        assert collected.error.partial_results == ["partial"]

    def test_collect_empty_list(self):
        """Test collecting empty list returns empty success."""
        results: list[Result[int, str]] = []
        collected = collect_results(results)

        assert isinstance(collected, Success)
        assert collected.value == []
        assert collected.warnings == []

    def test_collect_all_failures(self):
        """Test collecting all failures."""
        results: list[Result[int, str]] = [
            Failure(error="error1"),
            Failure(error="error2"),
        ]
        collected = collect_results(results)

        assert isinstance(collected, Failure)
        assert len(collected.error.errors) == 2
        assert collected.partial_result is None


class TestMapResult:
    """Tests for map_result function."""

    def test_map_success(self):
        """Test mapping over a Success value."""
        result: Result[int, str] = Success(value=5)
        mapped = map_result(result, lambda x: x * 2)

        assert isinstance(mapped, Success)
        assert mapped.value == 10

    def test_map_success_preserves_warnings(self):
        """Test that map_result preserves warnings."""
        result: Result[int, str] = Success(value=5, warnings=["warning"])
        mapped = map_result(result, lambda x: x * 2)

        assert isinstance(mapped, Success)
        assert mapped.value == 10
        assert mapped.warnings == ["warning"]

    def test_map_failure(self):
        """Test mapping over a Failure returns the same Failure."""
        result: Result[int, str] = Failure(error="error")
        mapped = map_result(result, lambda x: x * 2)

        assert isinstance(mapped, Failure)
        assert mapped.error == "error"

    def test_map_type_transformation(self):
        """Test map_result can change the value type."""
        result: Result[int, str] = Success(value=42)
        mapped = map_result(result, lambda x: f"value is {x}")

        assert isinstance(mapped, Success)
        assert mapped.value == "value is 42"


class TestFlatMapResult:
    """Tests for flat_map_result function."""

    def test_flat_map_success_to_success(self):
        """Test flat_map with Success returning Success."""

        def operation(x: int) -> Result[str, str]:
            return Success(value=f"result: {x}")

        result: Result[int, str] = Success(value=10)
        flat_mapped = flat_map_result(result, operation)

        assert isinstance(flat_mapped, Success)
        assert flat_mapped.value == "result: 10"

    def test_flat_map_success_to_failure(self):
        """Test flat_map with Success returning Failure."""

        def operation(x: int) -> Result[str, str]:
            if x < 0:
                return Failure(error="negative value")
            return Success(value=f"result: {x}")

        result: Result[int, str] = Success(value=-5)
        flat_mapped = flat_map_result(result, operation)

        assert isinstance(flat_mapped, Failure)
        assert flat_mapped.error == "negative value"

    def test_flat_map_failure(self):
        """Test flat_map with Failure returns the same Failure."""

        def operation(x: int) -> Result[str, str]:
            return Success(value=f"result: {x}")

        result: Result[int, str] = Failure(error="original error")
        flat_mapped = flat_map_result(result, operation)

        assert isinstance(flat_mapped, Failure)
        assert flat_mapped.error == "original error"

    def test_flat_map_accumulates_warnings(self):
        """Test flat_map accumulates warnings from both results."""

        def operation(x: int) -> Result[int, str]:
            return Success(value=x * 2, warnings=["inner warning"])

        result: Result[int, str] = Success(value=5, warnings=["outer warning"])
        flat_mapped = flat_map_result(result, operation)

        assert isinstance(flat_mapped, Success)
        assert flat_mapped.value == 10
        assert flat_mapped.warnings == ["outer warning", "inner warning"]

    def test_flat_map_chaining(self):
        """Test chaining multiple flat_map operations."""

        def add_one(x: int) -> Result[int, str]:
            return Success(value=x + 1)

        def multiply_two(x: int) -> Result[int, str]:
            return Success(value=x * 2)

        result: Result[int, str] = Success(value=5)
        chained = flat_map_result(
            flat_map_result(result, add_one),
            multiply_two,
        )

        assert isinstance(chained, Success)
        assert chained.value == 12  # (5 + 1) * 2

    def test_flat_map_chain_short_circuits_on_failure(self):
        """Test that flat_map chain stops at first failure."""

        def fail_on_ten(x: int) -> Result[int, str]:
            if x == 10:
                return Failure(error="hit ten")
            return Success(value=x + 5)

        result: Result[int, str] = Success(value=5)
        # First flat_map: 5 + 5 = 10
        # Second flat_map: fails because x == 10
        chained = flat_map_result(
            flat_map_result(result, fail_on_ten),
            fail_on_ten,
        )

        assert isinstance(chained, Failure)
        assert chained.error == "hit ten"


class TestUnwrapOr:
    """Tests for unwrap_or function."""

    def test_unwrap_success(self):
        """Test unwrap_or with Success returns the value."""
        result: Result[int, str] = Success(value=42)
        assert unwrap_or(result, 0) == 42

    def test_unwrap_failure(self):
        """Test unwrap_or with Failure returns the default."""
        result: Result[int, str] = Failure(error="error")
        assert unwrap_or(result, 0) == 0


class TestUnwrapOrElse:
    """Tests for unwrap_or_else function."""

    def test_unwrap_or_else_success(self):
        """Test unwrap_or_else with Success returns the value."""
        result: Result[int, str] = Success(value=42)
        assert unwrap_or_else(result, lambda e: -1) == 42

    def test_unwrap_or_else_failure(self):
        """Test unwrap_or_else with Failure calls the function."""
        result: Result[int, str] = Failure(error="error message")
        value = unwrap_or_else(result, lambda e: len(e))
        assert value == 13  # len("error message")


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""

    def test_enrichment_pipeline(self):
        """Test a simulated enrichment pipeline with Result types."""

        def index_phase(data: dict) -> Result[dict, EnrichmentError]:
            if "items" not in data:
                return Failure(
                    error=EnrichmentError(
                        phase="index",
                        message="Missing items field",
                    )
                )
            return Success(
                value={"indexed": True, **data},
                warnings=["deprecated field 'legacy' ignored"] if "legacy" in data else [],
            )

        def tree_build_phase(data: dict) -> Result[dict, EnrichmentError]:
            if not data.get("indexed"):
                return Failure(
                    error=EnrichmentError(
                        phase="tree_build",
                        message="Data not indexed",
                    )
                )
            return Success(value={"tree_built": True, **data})

        # Test successful pipeline
        input_data = {"items": [1, 2, 3], "legacy": True}
        result = flat_map_result(index_phase(input_data), tree_build_phase)

        assert isinstance(result, Success)
        assert result.value["indexed"] is True
        assert result.value["tree_built"] is True
        assert "deprecated field 'legacy' ignored" in result.warnings

    def test_artifact_operations(self):
        """Test artifact operations with Result types."""

        def read_artifact(path: str) -> Result[str, ArtifactError]:
            if path.endswith(".json"):
                return Success(value='{"data": "content"}')
            return Failure(
                error=ArtifactError(
                    operation="read",
                    path=path,
                    message="Unsupported file format",
                )
            )

        def validate_artifact(content: str) -> Result[dict, ArtifactError]:
            if content.startswith("{"):
                return Success(value={"validated": True, "content": content})
            return Failure(
                error=ArtifactError(
                    operation="validate",
                    path="unknown",
                    message="Invalid JSON format",
                )
            )

        # Test successful read and validate
        result = flat_map_result(read_artifact("data.json"), validate_artifact)
        assert isinstance(result, Success)
        assert result.value["validated"] is True

        # Test failed read
        result = flat_map_result(read_artifact("data.txt"), validate_artifact)
        assert isinstance(result, Failure)
        assert result.error.operation == "read"

    def test_batch_processing_with_collect(self):
        """Test batch processing collecting results."""

        def process_item(item: int) -> Result[int, str]:
            if item % 2 == 0:
                return Success(value=item * 10)
            return Success(value=item * 10, warnings=[f"item {item} is odd"])

        items = [1, 2, 3, 4, 5]
        results = [process_item(item) for item in items]
        collected = collect_results(results)

        assert isinstance(collected, Success)
        assert collected.value == [10, 20, 30, 40, 50]
        assert len(collected.warnings) == 3  # items 1, 3, 5 are odd
