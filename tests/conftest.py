"""Shared pytest fixtures for dydactic tests."""

import typing
import pytest
import pydantic


class Person(pydantic.BaseModel):
    """Test model representing a person."""

    id: int
    name: str
    age: float


class Employee(pydantic.BaseModel):
    """Test model representing an employee."""

    employee_id: int
    name: str
    email: str
    salary: float | None = None


@pytest.fixture
def person_model() -> type[pydantic.BaseModel]:
    """Fixture providing the Person Pydantic model."""
    return Person


@pytest.fixture
def employee_model() -> type[pydantic.BaseModel]:
    """Fixture providing the Employee Pydantic model."""
    return Employee


@pytest.fixture
def valid_person_records() -> list[dict[str, typing.Any]]:
    """Fixture providing valid person records."""
    return [
        {"id": 1, "name": "Alice", "age": 30.0},
        {"id": 2, "name": "Bob", "age": 25.5},
        {"id": 3, "name": "Charlie", "age": 35.0},
    ]


@pytest.fixture
def invalid_person_records() -> list[dict[str, typing.Any]]:
    """Fixture providing invalid person records."""
    return [
        {"id": "not_a_number", "name": "Alice", "age": 30.0},  # Invalid id type
        {"id": 2, "name": "Bob"},  # Missing age
        {"id": 3, "name": "Charlie", "age": "not_a_number"},  # Invalid age type
    ]


@pytest.fixture
def mixed_person_records() -> list[dict[str, typing.Any]]:
    """Fixture providing mix of valid and invalid person records."""
    return [
        {"id": 1, "name": "Alice", "age": 30.0},  # Valid
        {"id": "invalid", "name": "Bob", "age": 25.5},  # Invalid
        {"id": 3, "name": "Charlie", "age": 35.0},  # Valid
        {"id": 4},  # Missing required fields
    ]


@pytest.fixture
def valid_json_records() -> list[str]:
    """Fixture providing valid JSON strings."""
    return [
        '{"id": 1, "name": "Alice", "age": 30.0}',
        '{"id": 2, "name": "Bob", "age": 25.5}',
        '{"id": 3, "name": "Charlie", "age": 35.0}',
    ]


@pytest.fixture
def invalid_json_records() -> list[str]:
    """Fixture providing invalid JSON strings."""
    return [
        '{"id": "not_a_number", "name": "Alice", "age": 30.0}',
        '{"id": 2, "name": "Bob"}',  # Missing age
        "not json at all",
    ]
