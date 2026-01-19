"""
Result[T, E] infrastructure for explicit error handling.

Implements a discriminated union pattern with Success and Failure types,
supporting error accumulation and functional composition.

Design Principles:
- Errors are typed and documented
- Fail late: complete as much work as possible
- Error accumulation: collect multiple errors
- Warnings can accompany success
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar, Union

# Type variables for generic Result types
T = TypeVar("T")  # Success value type
U = TypeVar("U")  # Transformed success value type
E = TypeVar("E")  # Error type


@dataclass
class Success(Generic[T]):
    """
    Represents a successful result with an optional list of warnings.

    Attributes:
        value: The successful result value
        warnings: Non-fatal issues encountered during processing
    """

    value: T
    warnings: list[str] = field(default_factory=list)

    def is_success(self) -> bool:
        """Returns True for Success instances."""
        return True

    def is_failure(self) -> bool:
        """Returns False for Success instances."""
        return False


@dataclass
class Failure(Generic[E]):
    """
    Represents a failed result with error details and optional partial result.

    Attributes:
        error: The error that caused the failure
        partial_result: Any partial work completed before failure
    """

    error: E
    partial_result: Any = None

    def is_success(self) -> bool:
        """Returns False for Failure instances."""
        return False

    def is_failure(self) -> bool:
        """Returns True for Failure instances."""
        return True


# Type alias for Result union
Result = Union[Success[T], Failure[E]]


# -----------------------------------------------------------------------------
# Error Types
# -----------------------------------------------------------------------------


@dataclass
class EnrichmentError:
    """
    Error during enrichment phases.

    Attributes:
        phase: The enrichment phase where error occurred
               (e.g., "index", "tree_build", "depth_compute")
        message: Human-readable error description
        context: Additional context for debugging
    """

    phase: str
    message: str
    context: dict = field(default_factory=dict)


@dataclass
class ArtifactError:
    """
    Error during artifact operations.

    Attributes:
        operation: The operation that failed (e.g., "read", "write", "validate")
        path: Path to the artifact
        message: Human-readable error description
    """

    operation: str
    path: str
    message: str


@dataclass
class AggregateError:
    """
    Container for multiple errors collected during processing.

    Attributes:
        errors: List of individual errors
        partial_results: Any partial work completed before/during failures
    """

    errors: list[Any] = field(default_factory=list)
    partial_results: list[Any] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def collect_results(results: list[Result[T, E]]) -> Result[list[T], AggregateError]:
    """
    Aggregate multiple Results into a single Result.

    If all results are Success, returns Success with list of all values
    and accumulated warnings. If any results are Failure, returns Failure
    with AggregateError containing all errors and partial results.

    Args:
        results: List of Result instances to aggregate

    Returns:
        Success[list[T]]: If all inputs were successful, with accumulated warnings
        Failure[AggregateError]: If any inputs failed, with all errors collected
    """
    values: list[T] = []
    warnings: list[str] = []
    errors: list[E] = []
    partial_results: list[Any] = []

    for result in results:
        if isinstance(result, Success):
            values.append(result.value)
            warnings.extend(result.warnings)
        else:
            errors.append(result.error)
            if result.partial_result is not None:
                partial_results.append(result.partial_result)

    if errors:
        return Failure(
            error=AggregateError(errors=errors, partial_results=partial_results),
            partial_result=values if values else None,
        )

    return Success(value=values, warnings=warnings)


def map_result(
    result: Result[T, E], fn: Callable[[T], U]
) -> Result[U, E]:
    """
    Transform the success value of a Result.

    If the result is Success, applies fn to the value and returns a new Success.
    If the result is Failure, returns the Failure unchanged.

    Args:
        result: The Result to transform
        fn: Function to apply to the success value

    Returns:
        Success[U]: If input was Success, with transformed value
        Failure[E]: If input was Failure, unchanged
    """
    if isinstance(result, Success):
        return Success(value=fn(result.value), warnings=result.warnings)
    return result


def flat_map_result(
    result: Result[T, E], fn: Callable[[T], Result[U, E]]
) -> Result[U, E]:
    """
    Chain Result-returning operations.

    If the result is Success, applies fn to the value and returns the resulting Result.
    If the result is Failure, returns the Failure unchanged.
    Warnings from the original Success are prepended to the new result's warnings.

    Args:
        result: The Result to transform
        fn: Function that takes the success value and returns a new Result

    Returns:
        Result[U, E]: The result of applying fn, or the original Failure
    """
    if isinstance(result, Success):
        new_result = fn(result.value)
        # Preserve warnings from the original result
        if isinstance(new_result, Success):
            return Success(
                value=new_result.value,
                warnings=result.warnings + new_result.warnings,
            )
        return new_result
    return result


def unwrap_or(result: Result[T, E], default: T) -> T:
    """
    Extract the success value or return a default.

    Args:
        result: The Result to unwrap
        default: Value to return if result is Failure

    Returns:
        The success value if Success, otherwise the default
    """
    if isinstance(result, Success):
        return result.value
    return default


def unwrap_or_else(result: Result[T, E], fn: Callable[[E], T]) -> T:
    """
    Extract the success value or compute from the error.

    Args:
        result: The Result to unwrap
        fn: Function to compute value from error if Failure

    Returns:
        The success value if Success, otherwise fn(error)
    """
    if isinstance(result, Success):
        return result.value
    return fn(result.error)
