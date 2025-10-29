"""Result types for validation operations."""

import typing as _t

import pydantic as _pydantic

from . import record as _record


class RecordValidationResult(_t.NamedTuple):
    """Result of validating a single record (dictionary or Pydantic model).

    Attributes:
        error: ValidationError if validation failed, None otherwise
        result: Validated Pydantic BaseModel instance if successful, None otherwise
        value: Original record that was validated
    """

    error: _pydantic.ValidationError | None
    result: _pydantic.BaseModel | None
    value: _record.Record


class JsonValidationResult(_t.NamedTuple):
    """Result of validating a single JSON string.

    Attributes:
        error: ValidationError if validation failed, None otherwise
        result: Validated Pydantic BaseModel instance if successful, None otherwise
        value: Original JSON string that was validated
    """

    error: _pydantic.ValidationError | None
    result: _pydantic.BaseModel | None
    value: _record.Json
