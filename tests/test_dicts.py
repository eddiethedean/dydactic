"""Integration tests for dydactic package."""

import typing
import pydantic
from dydactic import validate


class Person(pydantic.BaseModel):
    """Test model for integration tests."""

    id: int
    name: str
    age: float


def test_simple_integration():
    """Basic integration test for validate function."""
    records: list[dict[str, typing.Any]] = [
        dict(id=1, name="Odos", age=38),
        dict(id=2, name="Kayla", age=31),
        dict(id=3, name="Dexter", age=2),
    ]
    iterable = validate(records, Person)
    result = next(iterable)
    assert result.error is None
    assert result.result == Person(id=1, name="Odos", age=38)
    assert result.value == dict(id=1, name="Odos", age=38)

    # Test all records
    results = list(validate(records, Person))
    assert len(results) == 3
    assert all(r.error is None for r in results)
