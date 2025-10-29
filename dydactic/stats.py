"""Validation statistics and aggregation utilities."""

import json
import typing
from dataclasses import dataclass, asdict
from collections import Counter

from . import result as _result


@dataclass
class ValidationStats:
    """Statistics about validation results.

    Attributes:
        total: Total number of records validated
        valid_count: Number of successfully validated records
        invalid_count: Number of records with validation errors
        valid_percentage: Percentage of valid records
        invalid_percentage: Percentage of invalid records
        error_counts: Frequency count of error types (error class names)
        field_error_counts: Frequency count of errors by field name
        total_errors: Total number of errors (some records may have multiple fields with errors)
    """

    total: int
    valid_count: int
    invalid_count: int
    valid_percentage: float
    invalid_percentage: float
    error_counts: dict[str, int]
    field_error_counts: dict[str, int]
    total_errors: int

    @classmethod
    def from_results(
        cls,
        results: typing.Iterable[
            _result.RecordValidationResult | _result.JsonValidationResult
        ],
    ) -> "ValidationStats":
        """Create ValidationStats from a collection of validation results.

        Args:
            results: Iterable of RecordValidationResult or JsonValidationResult

        Returns:
            ValidationStats instance with computed statistics
        """
        results_list = list(results)
        total = len(results_list)

        valid_count = sum(1 for r in results_list if r.error is None)
        invalid_count = total - valid_count

        valid_percentage = (valid_count / total * 100) if total > 0 else 0.0
        invalid_percentage = (invalid_count / total * 100) if total > 0 else 0.0

        # Count error types
        error_type_counter: Counter[str] = Counter()
        field_error_counter: Counter[str] = Counter()
        total_errors = 0

        for result in results_list:
            if result.error is not None:
                error_type = type(result.error).__name__
                error_type_counter[error_type] += 1
                total_errors += 1

                # Extract field-level errors from Pydantic ValidationError
                if hasattr(result.error, "errors"):
                    for error_detail in result.error.errors():
                        if "loc" in error_detail and len(error_detail["loc"]) > 0:
                            field_name = ".".join(
                                str(loc) for loc in error_detail["loc"]
                            )
                            field_error_counter[field_name] += 1
                            total_errors += 1

        return cls(
            total=total,
            valid_count=valid_count,
            invalid_count=invalid_count,
            valid_percentage=valid_percentage,
            invalid_percentage=invalid_percentage,
            error_counts=dict(error_type_counter),
            field_error_counts=dict(field_error_counter),
            total_errors=total_errors,
        )

    def top_errors(self, n: int = 10) -> list[tuple[str, int]]:
        """Get top N most frequent error types.

        Args:
            n: Number of top errors to return

        Returns:
            List of (error_type, count) tuples, sorted by count descending
        """
        sorted_errors = sorted(
            self.error_counts.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_errors[:n]

    def top_field_errors(self, n: int = 10) -> list[tuple[str, int]]:
        """Get top N most frequent field-level errors.

        Args:
            n: Number of top field errors to return

        Returns:
            List of (field_name, count) tuples, sorted by count descending
        """
        sorted_field_errors = sorted(
            self.field_error_counts.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_field_errors[:n]

    def to_dict(self) -> dict[str, typing.Any]:
        """Convert stats to dictionary.

        Returns:
            Dictionary representation of statistics
        """
        return asdict(self)

    def to_json(self, indent: int | None = None) -> str:
        """Convert stats to JSON string.

        Args:
            indent: JSON indentation level (None for compact)

        Returns:
            JSON string representation of statistics
        """
        return json.dumps(self.to_dict(), indent=indent)

    def __repr__(self) -> str:
        """String representation of stats."""
        return (
            f"ValidationStats(total={self.total}, "
            f"valid={self.valid_count} ({self.valid_percentage:.1f}%), "
            f"invalid={self.invalid_count} ({self.invalid_percentage:.1f}%))"
        )


def get_stats(
    results: typing.Iterable[
        _result.RecordValidationResult | _result.JsonValidationResult
    ],
) -> ValidationStats:
    """Convenience function to get validation statistics.

    Args:
        results: Iterable of validation results

    Returns:
        ValidationStats instance

    Example:
        >>> results = list(validate(records, Person))
        >>> stats = get_stats(results)
        >>> print(f"Valid: {stats.valid_percentage:.1f}%")
    """
    return ValidationStats.from_results(results)
