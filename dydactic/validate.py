import typing as _typing

import pydantic as _pydantic

import result as _result
import options as _options
import record as _record
import cast as _cast


def validate_record(
    record: _record.Record,
    model: _pydantic.BaseModel | _typing.Callable,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    raise_errors: bool = False
) -> _result.RecordValidationResult:
    try:
        if isinstance(model, _pydantic.BaseModel):
            validated_record = model.model_validate(
                record, from_attributes=from_attributes, strict=strict
            )
        else:
            validated_record = _cast.cast_to_annotated_class(record, model)
    except Exception as e:
        if raise_errors:
            raise e
        return _result.RecordValidationResult(e, None, record)
    return _result.RecordValidationResult(None, validated_record, record)


def validate_records(
    records: _typing.Iterator[_record.Record],
    model: _pydantic.BaseModel,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    error_option: _options.ErrorOption = _options.ErrorOption.RETURN
) -> _typing.Generator[_result.RecordValidationResult, None, None]:
    for record in records:
        result: _result.RecordValidationResult = validate_record(
            record, model,
            from_attributes=from_attributes,
            strict=strict,
            raise_errors=error_option == _options.ErrorOption.RAISE
        )
        if result.error and error_option == _options.ErrorOption.SKIP:
            continue
        yield result


def validate_json(
    json: _record.Json,
    model: _pydantic.BaseModel,
    *,
    strict: bool | None = None,
    raise_errors: bool = False
) -> _result.JsonValidationResult:
    try:
        validated_record: _pydantic.BaseModel = model.model_validate_json(
            json, strict=strict
        )
    except _pydantic.ValidationError as e:
        if raise_errors:
            raise e
        return _result.JsonValidationResult(e, None, json)
    return _result.JsonValidationResult(None, validated_record, json)


def validate_jsons(
    records: _typing.Iterator[_record.Json],
    model: _pydantic.BaseModel,
    *,
    strict: bool | None = None,
    error_option: _options.ErrorOption = _options.ErrorOption.RETURN
) -> _typing.Generator[_result.JsonValidationResult, None, None]:
    for record in records:
        result: _result.JsonValidationResult = validate_json(
            record, model,
            strict=strict,
            raise_errors=error_option == _options.ErrorOption.RAISE
        )
        if result.error and error_option == _options.ErrorOption.SKIP:
            continue
        yield result


def validate(
    records: _typing.Iterator[_record.Record | _record.Json],
    model: _pydantic.BaseModel,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    error_option: _options.ErrorOption = _options.ErrorOption.RETURN
) -> _typing.Generator[_result.RecordValidationResult | _result.JsonValidationResult, None, None]:
    result: _result.RecordValidationResult | _result.JsonValidationResult
    for record in records:
        if isinstance(record, _record.Json):
            result = validate_json(
                record, model,
                strict=strict,
                raise_errors=error_option == _options.ErrorOption.RAISE
            )
        else:
            result = validate_record(
                record, model, # type: ignore 
                from_attributes=from_attributes,
                strict=strict,
                raise_errors=error_option == _options.ErrorOption.RAISE
            )
        if result.error and error_option == _options.ErrorOption.SKIP:
            continue
        yield result