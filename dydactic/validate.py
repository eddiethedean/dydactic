import typing as _typing

import pydantic as _pydantic

from . import result as _result
from . import options as _options
from . import record as _record
from . import cast as _cast
from . import hooks as _hooks
from . import transform as _transform
from . import rules as _rules

# Type alias for progress callbacks
ProgressCallback = _typing.Callable[
    [int, int | None, _result.RecordValidationResult | _result.JsonValidationResult],
    None,
]


def _filter_record_fields(
    record: dict[str, _typing.Any], fields: list[str]
) -> dict[str, _typing.Any]:
    """Filter record to include only specified fields.

    Args:
        record: Dictionary record
        fields: List of field names to include

    Returns:
        Filtered dictionary
    """
    return {k: v for k, v in record.items() if k in fields}


def _project_model_fields(
    model_instance: _pydantic.BaseModel, fields: list[str]
) -> dict[str, _typing.Any]:
    """Project model to include only specified fields.

    Args:
        model_instance: Validated Pydantic model instance
        fields: List of field names to include

    Returns:
        Dictionary with only specified fields
    """
    if hasattr(model_instance, "model_dump"):
        all_data = model_instance.model_dump()
    elif hasattr(model_instance, "__dict__"):
        all_data = model_instance.__dict__
    else:
        return {}

    return {k: v for k, v in all_data.items() if k in fields}


def validate_record(
    record: _record.Record,
    model: _pydantic.BaseModel | _typing.Callable,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    raise_errors: bool = False,
    fields: list[str] | None = None,
    project_fields: list[str] | None = None,
    transforms: dict[str, _transform.Transform]
    | list[_transform.Transform]
    | None = None,
    rules: list[_rules.ValidationRule] | None = None,
) -> _result.RecordValidationResult:
    """Validate a single record against a Pydantic model or annotated class.

    Args:
        record: Dictionary or Pydantic model to validate
        model: Pydantic BaseModel class or callable class with annotations
        from_attributes: Whether to validate from object attributes (Pydantic only)
        strict: Whether to use strict validation (Pydantic only)
        raise_errors: If True, raise exceptions instead of returning them in result
        fields: List of field names to validate (None for all fields)
        project_fields: List of field names to return in result (None for all fields)
        transforms: Transformations to apply before validation
        rules: Additional validation rules to apply after type checking

    Returns:
        RecordValidationResult containing error (if any), validated result, and original value
    """
    original_record = record

    # Convert record to dict if needed
    if isinstance(record, dict):
        record_dict = record.copy()
    elif hasattr(record, "model_dump"):
        record_dict = record.model_dump()
    elif hasattr(record, "__dict__"):
        record_dict = record.__dict__
    else:
        record_dict = dict(record) if hasattr(record, "__iter__") else {}

    # Apply transforms
    if transforms is not None:
        record_dict = _transform.apply_transforms(record_dict, transforms)

    # Filter fields if specified
    if fields is not None:
        record_dict = _filter_record_fields(record_dict, fields)

    validated_record: _pydantic.BaseModel | object
    try:
        if isinstance(model, _pydantic.BaseModel):
            # This is a model instance, not a class - shouldn't happen normally
            validated_record = model.model_validate(
                record_dict, from_attributes=from_attributes, strict=strict
            )
        elif isinstance(model, type) and issubclass(model, _pydantic.BaseModel):
            # Pydantic model class
            validated_record = model.model_validate(
                record_dict, from_attributes=from_attributes, strict=strict
            )
        else:
            # Regular class with annotations
            validated_record = _cast.cast_to_annotated_class(
                record_dict, _typing.cast(type, model)
            )

        # Apply validation rules if provided
        if rules is not None:
            rule_validator = _rules.RuleValidator(rules)
            rule_errors = rule_validator.validate(validated_record)
            if rule_errors:
                # Create ValidationError from rule errors
                from .cast import ValidationError

                raise ValidationError(rule_errors)

        # Project fields if specified
        if project_fields is not None and isinstance(
            validated_record, _pydantic.BaseModel
        ):
            projected = _project_model_fields(validated_record, project_fields)
            # Create a simple dict-like result instead of model
            validated_record = type("ProjectedResult", (), projected)()

    except _pydantic.ValidationError as e:
        if raise_errors:
            raise
        return _result.RecordValidationResult(e, None, original_record)
    except _cast.ValidationError as e:
        # Convert our ValidationError to Pydantic ValidationError for consistency
        if raise_errors:
            # Create a Pydantic ValidationError from our error details
            pydantic_errors: list[dict[str, _typing.Any]] = []
            for field, error_info in e.errors.items():
                pydantic_errors.append(
                    {
                        "type": "type_error",
                        "loc": (field,),
                        "msg": f"expected {error_info.get('type', 'unknown').__name__}, "
                        f"got {error_info.get('input_type', type(None)).__name__}",
                        "input": error_info.get("input_value"),
                    }
                )
            pydantic_error = _pydantic.ValidationError.from_exception_data(
                model.__name__ if isinstance(model, type) else "Unknown",
                pydantic_errors,  # type: ignore[arg-type]
            )
            raise pydantic_error
        # Convert our ValidationError to Pydantic ValidationError for consistency
        pydantic_errors_conv: list[dict[str, _typing.Any]] = []
        for field, error_info in e.errors.items():
            pydantic_errors_conv.append(
                {
                    "type": "type_error",
                    "loc": (field,),
                    "msg": f"expected {error_info.get('type', 'unknown').__name__}, "
                    f"got {error_info.get('input_type', type(None)).__name__}",
                    "input": error_info.get("input_value"),
                }
            )
        pydantic_error_conv = _pydantic.ValidationError.from_exception_data(
            model.__name__ if isinstance(model, type) else "Unknown",
            pydantic_errors_conv,  # type: ignore[arg-type]
        )
        return _result.RecordValidationResult(
            pydantic_error_conv, None, original_record
        )
    except Exception as e:
        if raise_errors:
            raise
        # Convert generic Exception to Pydantic ValidationError if possible
        if isinstance(e, _pydantic.ValidationError):
            return _result.RecordValidationResult(e, None, original_record)
        # For other exceptions, wrap in ValidationError
        pydantic_error = _pydantic.ValidationError.from_exception_data(
            model.__name__ if isinstance(model, type) else "Unknown",
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": str(e),  # type: ignore[typeddict-unknown-key]
                    "input": original_record,
                }
            ],
        )
        return _result.RecordValidationResult(pydantic_error, None, original_record)
    # For non-Pydantic classes, we still need to return the instance, but result type expects BaseModel
    # Use cast to allow object instances (which can be regular class instances)
    if isinstance(validated_record, _pydantic.BaseModel):
        result_model: _pydantic.BaseModel | None = validated_record
    else:
        # For regular classes, cast to BaseModel for type compatibility (runtime it's just an object)
        result_model = _typing.cast(_pydantic.BaseModel, validated_record)
    return _result.RecordValidationResult(None, result_model, original_record)


def _can_use_bulk(
    records: _typing.Iterator[_record.Record],
    model: _pydantic.BaseModel | _typing.Callable,
    error_option: _options.ErrorOption,
) -> bool:
    """Check if bulk validation can be used.

    Args:
        records: Iterator of records
        model: Model class
        error_option: Error handling option

    Returns:
        True if bulk validation is safe to use
    """
    # Bulk only works with Pydantic models, not custom classes
    if not (isinstance(model, type) and issubclass(model, _pydantic.BaseModel)):
        return False

    # Bulk only works with RETURN option (RAISE/SKIP need per-item handling)
    if error_option != _options.ErrorOption.RETURN:
        return False

    # Would need to check if all records are dicts, but that requires materializing
    # So we'll check this when bulk is actually requested
    return True


def validate_records(
    records: _typing.Iterator[_record.Record],
    model: _pydantic.BaseModel,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    error_option: _options.ErrorOption = _options.ErrorOption.RETURN,
    on_progress: ProgressCallback | None = None,
    hooks: _hooks.ValidationHooks | None = None,
    fields: list[str] | None = None,
    project_fields: list[str] | None = None,
    transforms: dict[str, _transform.Transform]
    | list[_transform.Transform]
    | None = None,
    rules: list[_rules.ValidationRule] | None = None,
    bulk: bool = False,
) -> _typing.Generator[_result.RecordValidationResult, None, None]:
    """Validate an iterator of records against a Pydantic model.

    Args:
        records: Iterator of dictionaries or Pydantic models to validate
        model: Pydantic BaseModel class to validate against
        from_attributes: Whether to validate from object attributes
        strict: Whether to use strict validation
        error_option: How to handle errors (RETURN, RAISE, or SKIP)
        on_progress: Optional callback function(index, total, result) called after each validation
        hooks: Optional ValidationHooks instance for event callbacks
        fields: List of field names to validate (None for all)
        project_fields: List of field names to return in result (None for all)
        transforms: Transformations to apply before validation
        rules: Additional validation rules to apply
        bulk: If True, attempt to use bulk validation when possible (requires materializing records)

    Yields:
        RecordValidationResult for each record (skipped if error_option=SKIP and error occurs)

    Raises:
        ValidationError: If error_option=RAISE and validation fails
    """
    # Try bulk validation if requested and conditions are met
    if bulk and _can_use_bulk(records, model, error_option):
        try:
            from pydantic import TypeAdapter

            # Materialize records for bulk validation
            records_list = list(records)
            if not records_list:
                return

            # Check all records are dicts
            if not all(isinstance(r, dict) for r in records_list):
                # Fall through to individual validation
                records = iter(records_list)
            else:
                # Apply transforms if needed
                if transforms is not None:
                    records_list = [
                        _transform.apply_transforms(
                            _typing.cast(dict[str, _typing.Any], r), transforms
                        )
                        if not isinstance(r, dict)
                        else _transform.apply_transforms(r, transforms)
                        for r in records_list
                    ]

                # Filter fields if needed
                if fields is not None:
                    records_list = [
                        _filter_record_fields(
                            _typing.cast(dict[str, _typing.Any], r), fields
                        )
                        if not isinstance(r, dict)
                        else _filter_record_fields(r, fields)
                        for r in records_list
                    ]

                # Use TypeAdapter for bulk validation
                # model is already a type[BaseModel] at this point due to _can_use_bulk check
                ta = TypeAdapter(list[model])  # type: ignore[valid-type]
                try:
                    validated_models = ta.validate_python(records_list, strict=strict)

                    total_count = len(records_list)
                    for idx, validated_model in enumerate(validated_models):
                        # Apply rules if provided
                        if rules is not None:
                            rule_validator = _rules.RuleValidator(rules)
                            rule_errors = rule_validator.validate(validated_model)
                            if rule_errors:
                                from .cast import ValidationError

                                cast_error = ValidationError(rule_errors)
                                # Convert to Pydantic ValidationError
                                pydantic_errors_list: list[dict[str, _typing.Any]] = []
                                for field, error_info in cast_error.errors.items():
                                    pydantic_errors_list.append(
                                        {
                                            "type": "type_error",
                                            "loc": (field,),
                                            "msg": f"expected {error_info.get('type', 'unknown').__name__}, "
                                            f"got {error_info.get('input_type', type(None)).__name__}",
                                            "input": error_info.get("input_value"),
                                        }
                                    )
                                model_name = (
                                    model.__name__
                                    if hasattr(model, "__name__")
                                    else "Unknown"
                                )
                                pydantic_err = (
                                    _pydantic.ValidationError.from_exception_data(
                                        model_name,
                                        pydantic_errors_list,  # type: ignore[arg-type]
                                    )
                                )
                                result = _result.RecordValidationResult(
                                    pydantic_err, None, records_list[idx]
                                )
                            else:
                                # Project fields if needed
                                if project_fields is not None:
                                    projected = _project_model_fields(
                                        validated_model, project_fields
                                    )
                                    validated_model = type(
                                        "ProjectedResult", (), projected
                                    )()

                                result = _result.RecordValidationResult(
                                    None, validated_model, records_list[idx]
                                )
                        else:
                            # Project fields if needed
                            if project_fields is not None:
                                projected = _project_model_fields(
                                    validated_model, project_fields
                                )
                                validated_model = type(
                                    "ProjectedResult", (), projected
                                )()

                            result = _result.RecordValidationResult(
                                None, validated_model, records_list[idx]
                            )

                        # Call hooks
                        if hooks is not None:
                            hooks.call_after_validate(result)
                            hooks.call_on_success(result)
                            hooks.call_on_error(result)
                            if not hooks.check_should_continue(result):
                                return

                        # Call progress
                        if on_progress is not None:
                            try:
                                on_progress(idx, total_count, result)
                            except Exception:
                                pass

                        yield result
                    return
                except _pydantic.ValidationError:
                    # Bulk validation failed - fall through to individual validation
                    # This will provide better error reporting per item
                    records = iter(records_list)
        except Exception:
            # Fall through to individual validation on any error
            pass

    # Individual validation (default or fallback from bulk)
    # Try to get total if possible
    total: int | None = None
    records_list = list(records) if not isinstance(records, list) else records
    if isinstance(records_list, list):
        total = len(records_list)
        records = iter(records_list)
    elif hasattr(records, "__len__"):
        total = len(records)

    index = 0
    for record in records:
        # Call before_validate hook
        if hooks is not None:
            hooks.call_before_validate(record)

        record_result: _result.RecordValidationResult = validate_record(
            record,
            model,
            from_attributes=from_attributes,
            strict=strict,
            raise_errors=error_option == _options.ErrorOption.RAISE,
            fields=fields,
            project_fields=project_fields,
            transforms=transforms,
            rules=rules,
        )

        # Call hooks
        if hooks is not None:
            hooks.call_after_validate(record_result)
            hooks.call_on_success(record_result)
            hooks.call_on_error(record_result)

            # Check if should continue
            if not hooks.check_should_continue(record_result):
                break

        # Call progress callback if provided
        if on_progress is not None:
            try:
                on_progress(index, total, record_result)
            except Exception:
                # Silently ignore callback errors to not interrupt validation
                pass

        if record_result.error and error_option == _options.ErrorOption.SKIP:
            index += 1
            continue

        index += 1
        yield record_result


def validate_json(
    json: _record.Json,
    model: _pydantic.BaseModel,
    *,
    strict: bool | None = None,
    raise_errors: bool = False,
) -> _result.JsonValidationResult:
    """Validate a JSON string against a Pydantic model.

    Args:
        json: JSON string, bytes, or bytearray to validate
        model: Pydantic BaseModel class to validate against
        strict: Whether to use strict validation
        raise_errors: If True, raise exceptions instead of returning them in result

    Returns:
        JsonValidationResult containing error (if any), validated result, and original value

    Raises:
        ValidationError: If raise_errors=True and validation fails
    """
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
    error_option: _options.ErrorOption = _options.ErrorOption.RETURN,
    on_progress: ProgressCallback | None = None,
    hooks: _hooks.ValidationHooks | None = None,
) -> _typing.Generator[_result.JsonValidationResult, None, None]:
    """Validate an iterator of JSON strings against a Pydantic model.

    Args:
        records: Iterator of JSON strings, bytes, or bytearrays to validate
        model: Pydantic BaseModel class to validate against
        strict: Whether to use strict validation
        error_option: How to handle errors (RETURN, RAISE, or SKIP)
        on_progress: Optional callback function(index, total, result) called after each validation
        hooks: Optional ValidationHooks instance for event callbacks

    Yields:
        JsonValidationResult for each JSON (skipped if error_option=SKIP and error occurs)

    Raises:
        ValidationError: If error_option=RAISE and validation fails
    """
    # Try to get total if possible
    total = None
    if hasattr(records, "__len__"):
        total = len(records)  # type: ignore
    elif isinstance(records, list):
        total = len(records)

    index = 0
    for record in records:
        # Call before_validate hook
        if hooks is not None:
            hooks.call_before_validate(record)

        result: _result.JsonValidationResult = validate_json(
            record,
            model,
            strict=strict,
            raise_errors=error_option == _options.ErrorOption.RAISE,
        )

        # Call hooks
        if hooks is not None:
            hooks.call_after_validate(result)
            hooks.call_on_success(result)
            hooks.call_on_error(result)

            if not hooks.check_should_continue(result):
                break

        # Call progress callback if provided
        if on_progress is not None:
            try:
                on_progress(index, total, result)
            except Exception:
                # Silently ignore callback errors
                pass

        if result.error and error_option == _options.ErrorOption.SKIP:
            index += 1
            continue

        index += 1
        yield result


def validate(
    records: _typing.Iterator[_record.Record | _record.Json],
    model: _pydantic.BaseModel,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    error_option: _options.ErrorOption = _options.ErrorOption.RETURN,
    on_progress: ProgressCallback | None = None,
    hooks: _hooks.ValidationHooks | None = None,
    fields: list[str] | None = None,
    project_fields: list[str] | None = None,
    transforms: dict[str, _transform.Transform]
    | list[_transform.Transform]
    | None = None,
    rules: list[_rules.ValidationRule] | None = None,
    bulk: bool = False,
) -> _typing.Generator[
    _result.RecordValidationResult | _result.JsonValidationResult, None, None
]:
    """Validate an iterator of records (dicts/models) or JSON strings against a Pydantic model.

    Automatically detects whether each record is a dict/model or JSON string and validates accordingly.

    Args:
        records: Iterator of dictionaries, Pydantic models, or JSON strings to validate
        model: Pydantic BaseModel class to validate against
        from_attributes: Whether to validate from object attributes (for dict/model records only)
        strict: Whether to use strict validation
        error_option: How to handle errors (RETURN, RAISE, or SKIP)
        on_progress: Optional callback function(index, total, result) called after each validation
        hooks: Optional ValidationHooks instance for event callbacks
        fields: List of field names to validate (None for all)
        project_fields: List of field names to return in result (None for all)
        transforms: Transformations to apply before validation
        rules: Additional validation rules to apply
        bulk: If True, attempt to use bulk validation when possible

    Yields:
        RecordValidationResult or JsonValidationResult for each record
        (skipped if error_option=SKIP and error occurs)

    Raises:
        ValidationError: If error_option=RAISE and validation fails
    """
    # Try to get total if possible
    total = None
    if hasattr(records, "__len__"):
        total = len(records)  # type: ignore
    elif isinstance(records, list):
        total = len(records)

    index = 0
    result: _result.RecordValidationResult | _result.JsonValidationResult
    for record in records:
        # Call before_validate hook
        if hooks is not None:
            hooks.call_before_validate(record)

        # Check if record is JSON type (str, bytes, or bytearray)
        if isinstance(record, (str, bytes, bytearray)):
            # JSON validation doesn't support fields/transforms yet
            result = validate_json(
                record,
                model,
                strict=strict,
                raise_errors=error_option == _options.ErrorOption.RAISE,
            )
        else:
            result = validate_record(
                record,
                model,
                from_attributes=from_attributes,
                strict=strict,
                raise_errors=error_option == _options.ErrorOption.RAISE,
                fields=fields,
                project_fields=project_fields,
                transforms=transforms,
                rules=rules,
            )

        # Call hooks
        if hooks is not None:
            hooks.call_after_validate(result)
            hooks.call_on_success(result)
            hooks.call_on_error(result)

            if not hooks.check_should_continue(result):
                break

        # Call progress callback if provided
        if on_progress is not None:
            try:
                on_progress(index, total, result)
            except Exception:
                # Silently ignore callback errors
                pass

        if result.error and error_option == _options.ErrorOption.SKIP:
            index += 1
            continue

        index += 1
        yield result
