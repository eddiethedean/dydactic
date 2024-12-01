import typing
import pydantic
from dydactic import validate


class Person(pydantic.BaseModel):
    id: int
    name: str
    age: float


def test_simple():
    records: list[dict[str, typing.Any]] = [
        dict(id=1, name='Odos', age=38),
        dict(id=2, name='Kayla', age=31),
        dict(id=3, name='Dexter', age=2)
    ]
    iterable = validate(records, Person)
    result = next(iterable)
    assert result.error is None
    assert result.result == Person(id=1, name='Odos', age=38)
    assert result.value == dict(id=1, name='Odos', age=38)