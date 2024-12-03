import typing as _t

import pydantic as _pydantic

from . import record as _record


class RecordValidationResult(_t.NamedTuple):
    error: _pydantic.ValidationError | None
    result: _pydantic.BaseModel | None
    value: _record.Record


class JsonValidationResult(_t.NamedTuple):
    error: _pydantic.ValidationError | None
    result: _pydantic.BaseModel | None
    value: _record.Json