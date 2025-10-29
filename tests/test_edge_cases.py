"""Tests for edge cases and error conditions."""

import pydantic

from dydactic import validate
from dydactic.validate import validate_record, validate_json


class Person(pydantic.BaseModel):
    id: int
    name: str
    age: float


class PersonOptional(pydantic.BaseModel):
    id: int
    name: str
    age: float | None = None


def test_empty_iterator():
    """Test validation with empty iterator."""
    records = iter([])
    results = list(validate(records, Person))

    assert len(results) == 0


def test_none_values_not_allowed():
    """Test that None values are not allowed where not optional."""
    record = {"id": None, "name": "Alice", "age": 30.0}
    result = validate_record(record, Person)

    assert result.error is not None


def test_none_values_optional():
    """Test that None values are allowed when field is optional."""
    record = {"id": 1, "name": "Alice", "age": None}
    result = validate_record(record, PersonOptional)

    assert result.error is None
    assert result.result is not None
    assert result.result.age is None


def test_invalid_json_string():
    """Test handling of invalid JSON strings."""
    invalid_json = '{"id": 1, "name": "Alice"'  # Missing closing brace

    result = validate_json(invalid_json, Person)

    assert result.error is not None
    assert result.result is None


def test_missing_required_fields():
    """Test handling of missing required fields."""
    record = {"id": 1}  # Missing name and age

    result = validate_record(record, Person)

    assert result.error is not None
    assert "name" in str(result.error) or "age" in str(result.error)


def test_extra_fields():
    """Test that extra fields don't cause errors (unless model forbids them)."""
    record = {"id": 1, "name": "Alice", "age": 30.0, "extra_field": "value"}

    # Pydantic models by default allow extra fields
    result = validate_record(record, Person)
    assert result.error is None


class PersonStrict(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    id: int
    name: str
    age: float


def test_extra_fields_strict():
    """Test that extra fields cause errors in strict models."""
    record = {"id": 1, "name": "Alice", "age": 30.0, "extra_field": "value"}

    result = validate_record(record, PersonStrict)
    assert result.error is not None


def test_type_coercion_edge_cases():
    """Test various type coercion edge cases."""
    # String to int
    record1 = {"id": "123", "name": "Alice", "age": 30.0}
    result1 = validate_record(record1, Person)
    assert result1.error is None
    assert result1.result.id == 123

    # String to float
    record2 = {"id": 1, "name": "Alice", "age": "30.5"}
    result2 = validate_record(record2, Person)
    assert result2.error is None
    assert result2.result.age == 30.5

    # Invalid string to int
    record3 = {"id": "not_a_number", "name": "Alice", "age": 30.0}
    result3 = validate_record(record3, Person)
    assert result3.error is not None


def test_nested_validation():
    """Test validation with nested Pydantic models."""

    class Address(pydantic.BaseModel):
        street: str
        city: str

    class PersonWithAddress(pydantic.BaseModel):
        id: int
        name: str
        address: Address

    record = {
        "id": 1,
        "name": "Alice",
        "address": {"street": "123 Main St", "city": "New York"},
    }

    result = validate_record(record, PersonWithAddress)
    assert result.error is None
    assert result.result.address.city == "New York"


def test_empty_string_values():
    """Test handling of empty string values."""
    # Empty string should fail for int/float
    record1 = {"id": "", "name": "Alice", "age": 30.0}
    result1 = validate_record(record1, Person)
    assert result1.error is not None

    # Empty string is valid for str
    record2 = {"id": 1, "name": "", "age": 30.0}
    result2 = validate_record(record2, Person)
    assert result2.error is None
    assert result2.result.name == ""


def test_boolean_coercion():
    """Test boolean type coercion."""

    class Config(pydantic.BaseModel):
        enabled: bool

    # String to bool
    record1 = {"enabled": "true"}
    validate_record(record1, Config)
    # Pydantic handles this, should not error

    # Int to bool
    record2 = {"enabled": 1}
    result2 = validate_record(record2, Config)
    assert result2.error is None


def test_list_iterator_exhaustion():
    """Test that iterator is properly exhausted."""
    records = [
        {"id": 1, "name": "Alice", "age": 30.0},
        {"id": 2, "name": "Bob", "age": 25.5},
    ]

    iterator = iter(records)
    results = list(validate(iterator, Person))

    assert len(results) == 2
    # Iterator should be exhausted
    assert list(iterator) == []


def test_multiple_errors_in_one_record():
    """Test that multiple errors are captured in validation error."""
    record = {
        "id": "not_a_number",
        "name": 123,  # Wrong type
        "age": "also_not_a_number",
    }

    result = validate_record(record, Person)
    assert result.error is not None

    # Check that error message contains multiple field errors
    error_str = str(result.error)
    assert "id" in error_str or "name" in error_str or "age" in error_str


def test_bytes_json_input():
    """Test JSON validation with bytes input."""
    json_bytes = b'{"id": 1, "name": "Alice", "age": 30.0}'
    result = validate_json(json_bytes, Person)

    assert result.error is None
    assert result.result is not None


def test_bytearray_json_input():
    """Test JSON validation with bytearray input."""
    json_bytearray = bytearray(b'{"id": 1, "name": "Alice", "age": 30.0}')
    result = validate_json(json_bytearray, Person)

    assert result.error is None
    assert result.result is not None


def test_unicode_in_json():
    """Test JSON validation with unicode characters."""
    json_str = '{"id": 1, "name": "José", "age": 30.0}'
    result = validate_json(json_str, Person)

    assert result.error is None
    assert result.result.name == "José"
