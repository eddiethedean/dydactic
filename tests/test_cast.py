"""Tests for dydactic.cast module."""

import pytest
from datetime import datetime
import typing

from dydactic.cast import (
    cast_as,
    cast_as_union,
    cast_as_annotation,
    cast_to_annotated_class,
    ValidationError,
    cls_annotations,
)


def test_cast_as_basic_types():
    """Test basic type casting."""
    assert cast_as(5, int) == 5
    assert cast_as("5", int) == 5
    assert cast_as(5.5, float) == 5.5
    assert cast_as("5.5", float) == 5.5
    assert cast_as("hello", str) == "hello"


def test_cast_as_datetime():
    """Test datetime casting."""
    result = cast_as("2023-01-01T12:00:00", datetime)
    assert isinstance(result, datetime)
    assert result.year == 2023
    assert result.month == 1
    assert result.day == 1


def test_cast_as_datetime_already_datetime():
    """Test that already datetime objects pass through."""
    dt = datetime(2023, 1, 1, 12, 0, 0)
    result = cast_as(dt, datetime)
    assert result is dt


def test_cast_as_invalid_type():
    """Test that invalid type casting raises ValueError."""
    with pytest.raises((ValueError, TypeError)):
        cast_as("not_a_number", int)


def test_cast_as_union():
    """Test union type casting."""
    # Test int | str
    assert cast_as_union(5, typing.Union[int, str]) == 5
    assert cast_as_union("hello", typing.Union[int, str]) == "hello"

    # Test with optional
    assert cast_as_union(5, typing.Optional[int]) == 5
    assert cast_as_union(None, typing.Optional[int]) is None


def test_cast_as_union_python310_syntax():
    """Test Python 3.10+ union syntax (X | Y)."""
    # This should work with get_origin/get_args
    union_type = int | str
    assert cast_as_union(5, union_type) == 5
    assert cast_as_union("hello", union_type) == "hello"


def test_cast_as_union_failure():
    """Test that union casting fails when no type matches."""
    with pytest.raises(TypeError, match="Failed to cast value"):
        cast_as_union([1, 2, 3], typing.Union[int, str])


def test_cast_as_annotation_simple():
    """Test annotation-based casting for simple types."""
    assert cast_as_annotation("5", int) == 5
    assert cast_as_annotation(5, int) == 5


def test_cast_as_annotation_union():
    """Test annotation-based casting for union types."""
    assert cast_as_annotation("5", typing.Union[int, str]) == 5
    assert cast_as_annotation("hello", typing.Union[int, str]) == "hello"


def test_cls_annotations():
    """Test extracting annotations from a class."""

    class TestClass:
        x: int
        y: str
        z: float

    annotations = cls_annotations(TestClass)
    assert annotations["x"] is int
    assert annotations["y"] is str
    assert annotations["z"] is float


def test_cls_annotations_no_annotations():
    """Test class with no annotations."""

    class NoAnnotations:
        pass

    annotations = cls_annotations(NoAnnotations)
    assert annotations == {}


def test_cast_to_annotated_class_success():
    """Test successful casting to annotated class."""

    class Person:
        id: int
        name: str
        age: float

    data = {"id": 1, "name": "Alice", "age": 30.0}
    person = cast_to_annotated_class(data, Person)

    assert isinstance(person, Person)
    assert person.id == 1
    assert person.name == "Alice"
    assert person.age == 30.0


def test_cast_to_annotated_class_type_coercion():
    """Test type coercion when casting."""

    class Person:
        id: int
        name: str
        age: float

    data = {"id": "1", "name": "Alice", "age": "30.0"}
    person = cast_to_annotated_class(data, Person)

    assert isinstance(person, Person)
    assert person.id == 1
    assert person.age == 30.0


def test_cast_to_annotated_class_missing_key():
    """Test that missing required keys raise ValidationError."""

    class Person:
        id: int
        name: str
        age: float

    data = {"id": 1, "name": "Alice"}  # Missing age

    with pytest.raises(ValidationError) as exc_info:
        cast_to_annotated_class(data, Person)

    assert "age" in exc_info.value.errors
    assert exc_info.value.errors["age"]["error"] == "Missing required field"


def test_cast_to_annotated_class_invalid_type():
    """Test that invalid types raise ValidationError."""

    class Person:
        id: int
        name: str
        age: float

    data = {"id": "not_a_number", "name": "Alice", "age": 30.0}

    with pytest.raises(ValidationError) as exc_info:
        cast_to_annotated_class(data, Person)

    assert "id" in exc_info.value.errors
    assert exc_info.value.errors["id"]["type"] is int


def test_cast_to_annotated_class_multiple_errors():
    """Test that multiple validation errors are collected."""

    class Person:
        id: int
        name: str
        age: float

    data = {"id": "not_a_number", "name": "Alice", "age": "also_not_a_number"}

    with pytest.raises(ValidationError) as exc_info:
        cast_to_annotated_class(data, Person)

    errors = exc_info.value.errors
    assert "id" in errors
    assert "age" in errors


def test_cast_to_annotated_class_extra_keys():
    """Test that extra keys are ignored."""

    class Person:
        id: int
        name: str

    data = {"id": 1, "name": "Alice", "extra_field": "should be ignored"}
    person = cast_to_annotated_class(data, Person)

    assert person.id == 1
    assert person.name == "Alice"
    # Extra field should be ignored (not cause error)


def test_cast_to_annotated_class_with_datetime():
    """Test casting with datetime fields."""

    class Event:
        name: str
        timestamp: datetime

    data = {"name": "Meeting", "timestamp": "2023-01-01T12:00:00"}
    event = cast_to_annotated_class(data, Event)

    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.year == 2023


def test_cast_to_annotated_class_with_union():
    """Test casting with union types."""

    class Config:
        value: int | str

    data = {"value": 5}
    config = cast_to_annotated_class(data, Config)
    assert config.value == 5

    data2 = {"value": "hello"}
    config2 = cast_to_annotated_class(data2, Config)
    assert config2.value == "hello"


def test_validation_error_message():
    """Test that ValidationError has informative message."""

    class Person:
        id: int
        name: str

    data = {"id": "not_a_number", "name": 123}

    with pytest.raises(ValidationError) as exc_info:
        cast_to_annotated_class(data, Person)

    error_msg = str(exc_info.value)
    assert "Validation failed" in error_msg
    assert "id" in error_msg or "name" in error_msg
