"""Tests for dydactic.validate module."""

import pytest
import pydantic

from dydactic import validate
from dydactic.validate import (
    validate_record,
    validate_records,
    validate_json,
    validate_jsons,
)
from dydactic.options import ErrorOption


class Person(pydantic.BaseModel):
    id: int
    name: str
    age: float


def test_validate_record_success():
    """Test successful record validation."""
    record = {"id": 1, "name": "Alice", "age": 30.0}
    result = validate_record(record, Person)

    assert result.error is None
    assert result.result is not None
    assert isinstance(result.result, Person)
    assert result.result.id == 1
    assert result.result.name == "Alice"
    assert result.value == record


def test_validate_record_error():
    """Test record validation with error."""
    record = {"id": "not_a_number", "name": "Alice", "age": 30.0}
    result = validate_record(record, Person)

    assert result.error is not None
    assert result.result is None
    assert result.value == record


def test_validate_record_raise_errors():
    """Test that raise_errors=True raises exceptions."""
    record = {"id": "not_a_number", "name": "Alice", "age": 30.0}

    with pytest.raises(pydantic.ValidationError):
        validate_record(record, Person, raise_errors=True)


def test_validate_record_with_callable():
    """Test validation with a callable class."""

    class PersonClass:
        id: int
        name: str
        age: float

    record = {"id": 1, "name": "Alice", "age": 30.0}
    result = validate_record(record, PersonClass)

    assert result.error is None
    assert result.result is not None
    assert isinstance(result.result, PersonClass)


def test_validate_records_success():
    """Test successful validation of record iterator."""
    records = [
        {"id": 1, "name": "Alice", "age": 30.0},
        {"id": 2, "name": "Bob", "age": 25.5},
    ]
    results = list(validate_records(iter(records), Person))

    assert len(results) == 2
    assert all(r.error is None for r in results)
    assert all(r.result is not None for r in results)


def test_validate_records_error_option_return():
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
    assert results[1].error is not None
    assert results[2].error is None


def test_validate_records_error_option_skip():
    """Test ErrorOption.SKIP skips invalid records."""
    records = [
        {"id": 1, "name": "Alice", "age": 30.0},  # Valid
        {"id": "invalid", "name": "Bob", "age": 25.5},  # Invalid - should be skipped
        {"id": 3, "name": "Charlie", "age": 35.0},  # Valid
    ]
    results = list(
        validate_records(iter(records), Person, error_option=ErrorOption.SKIP)
    )

    assert len(results) == 2
    assert all(r.error is None for r in results)
    assert results[0].result.id == 1
    assert results[1].result.id == 3


def test_validate_records_error_option_raise():
    """Test ErrorOption.RAISE raises on first error."""
    records = [
        {"id": 1, "name": "Alice", "age": 30.0},  # Valid
        {"id": "invalid", "name": "Bob", "age": 25.5},  # Invalid - should raise
    ]

    with pytest.raises(pydantic.ValidationError):
        list(validate_records(iter(records), Person, error_option=ErrorOption.RAISE))


def test_validate_json_success():
    """Test successful JSON validation."""
    json_str = '{"id": 1, "name": "Alice", "age": 30.0}'
    result = validate_json(json_str, Person)

    assert result.error is None
    assert result.result is not None
    assert isinstance(result.result, Person)
    assert result.result.id == 1


def test_validate_json_error():
    """Test JSON validation with error."""
    json_str = '{"id": "not_a_number", "name": "Alice", "age": 30.0}'
    result = validate_json(json_str, Person)

    assert result.error is not None
    assert result.result is None


def test_validate_json_raise_errors():
    """Test that raise_errors=True raises exceptions for JSON."""
    json_str = '{"id": "not_a_number", "name": "Alice", "age": 30.0}'

    with pytest.raises(pydantic.ValidationError):
        validate_json(json_str, Person, raise_errors=True)


def test_validate_json_bytes():
    """Test JSON validation with bytes."""
    json_bytes = b'{"id": 1, "name": "Alice", "age": 30.0}'
    result = validate_json(json_bytes, Person)

    assert result.error is None
    assert result.result is not None


def test_validate_jsons_success():
    """Test successful validation of JSON iterator."""
    json_strings = [
        '{"id": 1, "name": "Alice", "age": 30.0}',
        '{"id": 2, "name": "Bob", "age": 25.5}',
    ]
    results = list(validate_jsons(iter(json_strings), Person))

    assert len(results) == 2
    assert all(r.error is None for r in results)


def test_validate_jsons_error_option_skip():
    """Test ErrorOption.SKIP skips invalid JSON."""
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


def test_validate_mixed_records_and_json():
    """Test validate function with mixed record and JSON types."""
    items = [
        {"id": 1, "name": "Alice", "age": 30.0},  # Record
        '{"id": 2, "name": "Bob", "age": 25.5}',  # JSON
        {"id": 3, "name": "Charlie", "age": 35.0},  # Record
    ]
    results = list(validate(iter(items), Person))

    assert len(results) == 3
    assert all(r.error is None for r in results)
    assert results[0].result.id == 1
    assert results[1].result.id == 2
    assert results[2].result.id == 3


def test_validate_strict_mode():
    """Test validation with strict mode enabled."""
    record = {
        "id": 1.0,
        "name": "Alice",
        "age": 30.0,
    }  # id is float, should fail in strict

    # Without strict, this should pass (coercion)
    result = validate_record(record, Person, strict=False)
    assert result.error is None

    # With strict, this should fail (no coercion)
    result = validate_record(record, Person, strict=True)
    assert result.error is not None


def test_validate_from_attributes():
    """Test validation from object attributes."""

    class PersonObj:
        def __init__(self):
            self.id = 1
            self.name = "Alice"
            self.age = 30.0

    obj = PersonObj()
    result = validate_record(obj, Person, from_attributes=True)

    assert result.error is None
    assert result.result is not None
    assert result.result.id == 1
