"""Tests for ErrorOption behavior."""

import pytest
import pydantic

from dydactic.validate import validate_records, validate_jsons, validate
from dydactic.options import ErrorOption


class Person(pydantic.BaseModel):
    id: int
    name: str
    age: float


def test_error_option_return():
    """Test ErrorOption.RETURN returns errors in results."""
    records = [
        {"id": 1, "name": "Alice", "age": 30.0},  # Valid
        {"id": "invalid", "name": "Bob", "age": 25.5},  # Invalid
        {"id": 3, "name": "Charlie", "age": 35.0},  # Valid
    ]

    results = list(
        validate_records(iter(records), Person, error_option=ErrorOption.RETURN)
    )

    assert len(results) == 3
    assert results[0].error is None
    assert results[0].result is not None
    assert results[1].error is not None
    assert results[1].result is None
    assert results[2].error is None
    assert results[2].result is not None


def test_error_option_raise_immediately():
    """Test ErrorOption.RAISE raises exception on first error."""
    records = [
        {"id": 1, "name": "Alice", "age": 30.0},  # Valid
        {"id": "invalid", "name": "Bob", "age": 25.5},  # Invalid - should raise here
        {"id": 3, "name": "Charlie", "age": 35.0},  # Never reached
    ]

    with pytest.raises(pydantic.ValidationError):
        list(validate_records(iter(records), Person, error_option=ErrorOption.RAISE))


def test_error_option_raise_on_first_record():
    """Test ErrorOption.RAISE raises even if first record is invalid."""
    records = [
        {"id": "invalid", "name": "Alice", "age": 30.0},  # Invalid - should raise here
    ]

    with pytest.raises(pydantic.ValidationError):
        list(validate_records(iter(records), Person, error_option=ErrorOption.RAISE))


def test_error_option_skip():
    """Test ErrorOption.SKIP silently skips invalid records."""
    records = [
        {"id": 1, "name": "Alice", "age": 30.0},  # Valid
        {"id": "invalid", "name": "Bob", "age": 25.5},  # Invalid - should be skipped
        {"id": 3, "name": "Charlie", "age": 35.0},  # Valid
        {
            "id": "also_invalid",
            "name": "David",
            "age": 40.0,
        },  # Invalid - should be skipped
    ]

    results = list(
        validate_records(iter(records), Person, error_option=ErrorOption.SKIP)
    )

    assert len(results) == 2
    assert all(r.error is None for r in results)
    assert all(r.result is not None for r in results)
    assert results[0].result.id == 1
    assert results[1].result.id == 3


def test_error_option_skip_all_invalid():
    """Test ErrorOption.SKIP with all invalid records returns empty list."""
    records = [
        {"id": "invalid1", "name": "Alice", "age": 30.0},
        {"id": "invalid2", "name": "Bob", "age": 25.5},
    ]

    results = list(
        validate_records(iter(records), Person, error_option=ErrorOption.SKIP)
    )

    assert len(results) == 0


def test_error_option_json_return():
    """Test ErrorOption.RETURN with JSON validation."""
    json_strings = [
        '{"id": 1, "name": "Alice", "age": 30.0}',
        '{"id": "invalid", "name": "Bob", "age": 25.5}',
        '{"id": 3, "name": "Charlie", "age": 35.0}',
    ]

    results = list(
        validate_jsons(iter(json_strings), Person, error_option=ErrorOption.RETURN)
    )

    assert len(results) == 3
    assert results[0].error is None
    assert results[1].error is not None
    assert results[2].error is None


def test_error_option_json_skip():
    """Test ErrorOption.SKIP with JSON validation."""
    json_strings = [
        '{"id": 1, "name": "Alice", "age": 30.0}',
        '{"id": "invalid", "name": "Bob", "age": 25.5}',
        '{"id": 3, "name": "Charlie", "age": 35.0}',
    ]

    results = list(
        validate_jsons(iter(json_strings), Person, error_option=ErrorOption.SKIP)
    )

    assert len(results) == 2
    assert all(r.error is None for r in results)


def test_error_option_json_raise():
    """Test ErrorOption.RAISE with JSON validation."""
    json_strings = [
        '{"id": 1, "name": "Alice", "age": 30.0}',
        '{"id": "invalid", "name": "Bob", "age": 25.5}',
    ]

    with pytest.raises(pydantic.ValidationError):
        list(validate_jsons(iter(json_strings), Person, error_option=ErrorOption.RAISE))


def test_error_option_validate_mixed():
    """Test ErrorOption behavior with validate() function (mixed types)."""
    items = [
        {"id": 1, "name": "Alice", "age": 30.0},  # Valid record
        '{"id": "invalid", "name": "Bob", "age": 25.5}',  # Invalid JSON
        {"id": 3, "name": "Charlie", "age": 35.0},  # Valid record
    ]

    results = list(validate(iter(items), Person, error_option=ErrorOption.SKIP))

    assert len(results) == 2
    assert all(r.error is None for r in results)
