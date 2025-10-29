"""Async validation functions for parallel processing."""

import asyncio
import os
import typing as _typing
from collections.abc import AsyncIterator, Iterator

import pydantic as _pydantic

from . import result as _result
from . import options as _options
from . import record as _record
from . import validate as _validate

# Type alias for progress callbacks (must match validate.py)
ProgressCallback = _typing.Callable[
    [int, int | None, _result.RecordValidationResult | _result.JsonValidationResult],
    None,
]


async def async_validate_record(
    record: _record.Record,
    model: _pydantic.BaseModel | _typing.Callable,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    raise_errors: bool = False,
) -> _result.RecordValidationResult:
    """Asynchronously validate a single record against a Pydantic model or annotated class.

    Args:
        record: Dictionary or Pydantic model to validate
        model: Pydantic BaseModel class or callable class with annotations
        from_attributes: Whether to validate from object attributes (Pydantic only)
        strict: Whether to use strict validation (Pydantic only)
        raise_errors: If True, raise exceptions instead of returning them in result

    Returns:
        RecordValidationResult containing error (if any), validated result, and original value
    """
    # Run validation in thread pool to avoid blocking
    return await asyncio.to_thread(
        _validate.validate_record,
        record,
        model,
        from_attributes=from_attributes,
        strict=strict,
        raise_errors=raise_errors,
    )


async def async_validate_records(
    records: AsyncIterator[_record.Record] | Iterator[_record.Record],
    model: _pydantic.BaseModel,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    error_option: _options.ErrorOption = _options.ErrorOption.RETURN,
    max_workers: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> AsyncIterator[_result.RecordValidationResult]:
    """Asynchronously validate an iterator of records against a Pydantic model.

    Args:
        records: Async or sync iterator of dictionaries or Pydantic models to validate
        model: Pydantic BaseModel class to validate against
        from_attributes: Whether to validate from object attributes
        strict: Whether to use strict validation
        error_option: How to handle errors (RETURN, RAISE, or SKIP)
        max_workers: Maximum number of concurrent validations (default: CPU count)
        on_progress: Optional callback function(index, total, result) called after each validation

    Yields:
        RecordValidationResult for each record (skipped if error_option=SKIP and error occurs)

    Raises:
        ValidationError: If error_option=RAISE and validation fails
    """
    if max_workers is None:
        max_workers = min(32, os.cpu_count() or 1)

    semaphore = asyncio.Semaphore(max_workers)

    async def validate_with_semaphore(
        record: _record.Record, idx: int
    ) -> tuple[int, _result.RecordValidationResult]:
        async with semaphore:
            result = await async_validate_record(
                record,
                model,
                from_attributes=from_attributes,
                strict=strict,
                raise_errors=error_option == _options.ErrorOption.RAISE,
            )
            return idx, result

    # Convert sync iterator to async if needed
    if isinstance(records, Iterator) and not isinstance(records, AsyncIterator):
        # Materialize sync iterator for async processing
        records_list = list(records)
        total = len(records_list) if records_list else None

        # Create tasks for parallel validation
        tasks = [
            validate_with_semaphore(record, idx)
            for idx, record in enumerate(records_list)
        ]

        # Process results as they complete
        for coro in asyncio.as_completed(tasks):
            idx, result = await coro

            if on_progress is not None:
                try:
                    on_progress(idx, total, result)
                except Exception:
                    pass

            if result.error and error_option == _options.ErrorOption.SKIP:
                continue

            if result.error and error_option == _options.ErrorOption.RAISE:
                raise result.error

            yield result
    else:
        # Async iterator
        total = None
        index = 0
        async for record in records:
            idx, result = await validate_with_semaphore(record, index)

            if on_progress is not None:
                try:
                    on_progress(idx, total, result)
                except Exception:
                    pass

            if result.error and error_option == _options.ErrorOption.SKIP:
                index += 1
                continue

            if result.error and error_option == _options.ErrorOption.RAISE:
                raise result.error

            index += 1
            yield result


async def async_validate_json(
    json: _record.Json,
    model: _pydantic.BaseModel,
    *,
    strict: bool | None = None,
    raise_errors: bool = False,
) -> _result.JsonValidationResult:
    """Asynchronously validate a JSON string against a Pydantic model.

    Args:
        json: JSON string, bytes, or bytearray to validate
        model: Pydantic BaseModel class to validate against
        strict: Whether to use strict validation
        raise_errors: If True, raise exceptions instead of returning them in result

    Returns:
        JsonValidationResult containing error (if any), validated result, and original value
    """
    return await asyncio.to_thread(
        _validate.validate_json, json, model, strict=strict, raise_errors=raise_errors
    )


async def async_validate_jsons(
    records: AsyncIterator[_record.Json] | Iterator[_record.Json],
    model: _pydantic.BaseModel,
    *,
    strict: bool | None = None,
    error_option: _options.ErrorOption = _options.ErrorOption.RETURN,
    max_workers: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> AsyncIterator[_result.JsonValidationResult]:
    """Asynchronously validate an iterator of JSON strings against a Pydantic model.

    Args:
        records: Async or sync iterator of JSON strings, bytes, or bytearrays to validate
        model: Pydantic BaseModel class to validate against
        strict: Whether to use strict validation
        error_option: How to handle errors (RETURN, RAISE, or SKIP)
        max_workers: Maximum number of concurrent validations (default: CPU count)
        on_progress: Optional callback function(index, total, result) called after each validation

    Yields:
        JsonValidationResult for each JSON (skipped if error_option=SKIP and error occurs)

    Raises:
        ValidationError: If error_option=RAISE and validation fails
    """
    if max_workers is None:
        env_workers = os.getenv("PYTHON_MAX_WORKERS")
        if env_workers is not None:
            try:
                env_workers_int = int(env_workers)
            except (ValueError, TypeError):
                env_workers_int = 1
        else:
            env_workers_int = 1
        max_workers = min(32, env_workers_int, os.cpu_count() or 1)

    semaphore = asyncio.Semaphore(max_workers)

    async def validate_with_semaphore(
        json_record: _record.Json, idx: int
    ) -> tuple[int, _result.JsonValidationResult]:
        async with semaphore:
            result = await async_validate_json(
                json_record,
                model,
                strict=strict,
                raise_errors=error_option == _options.ErrorOption.RAISE,
            )
            return idx, result

    if isinstance(records, Iterator) and not isinstance(records, AsyncIterator):
        records_list = list(records)
        total = len(records_list) if records_list else None

        tasks = [
            validate_with_semaphore(record, idx)
            for idx, record in enumerate(records_list)
        ]

        for coro in asyncio.as_completed(tasks):
            idx, result = await coro

            if on_progress is not None:
                try:
                    on_progress(idx, total, result)
                except Exception:
                    pass

            if result.error and error_option == _options.ErrorOption.SKIP:
                continue

            if result.error and error_option == _options.ErrorOption.RAISE:
                raise result.error

            yield result
    else:
        total = None
        index = 0
        async for record in records:
            idx, result = await validate_with_semaphore(record, index)

            if on_progress is not None:
                try:
                    on_progress(idx, total, result)
                except Exception:
                    pass

            if result.error and error_option == _options.ErrorOption.SKIP:
                index += 1
                continue

            if result.error and error_option == _options.ErrorOption.RAISE:
                raise result.error

            index += 1
            yield result


async def async_validate(
    records: AsyncIterator[_record.Record | _record.Json]
    | Iterator[_record.Record | _record.Json],
    model: _pydantic.BaseModel,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    error_option: _options.ErrorOption = _options.ErrorOption.RETURN,
    max_workers: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> AsyncIterator[_result.RecordValidationResult | _result.JsonValidationResult]:
    """Asynchronously validate an iterator of records (dicts/models) or JSON strings.

    Automatically detects whether each record is a dict/model or JSON string and validates accordingly.

    Args:
        records: Async or sync iterator of dictionaries, Pydantic models, or JSON strings
        model: Pydantic BaseModel class to validate against
        from_attributes: Whether to validate from object attributes (for dict/model records only)
        strict: Whether to use strict validation
        error_option: How to handle errors (RETURN, RAISE, or SKIP)
        max_workers: Maximum number of concurrent validations (default: CPU count)
        on_progress: Optional callback function(index, total, result) called after each validation

    Yields:
        RecordValidationResult or JsonValidationResult for each record
        (skipped if error_option=SKIP and error occurs)

    Raises:
        ValidationError: If error_option=RAISE and validation fails
    """
    if max_workers is None:
        max_workers = min(32, os.cpu_count() or 1)

    semaphore = asyncio.Semaphore(max_workers)

    async def validate_one(
        record: _record.Record | _record.Json, idx: int
    ) -> tuple[int, _result.RecordValidationResult | _result.JsonValidationResult]:
        async with semaphore:
            if isinstance(record, (str, bytes, bytearray)):
                json_result = await async_validate_json(
                    record,
                    model,
                    strict=strict,
                    raise_errors=error_option == _options.ErrorOption.RAISE,
                )
                return idx, _typing.cast(
                    _result.RecordValidationResult | _result.JsonValidationResult,
                    json_result,
                )
            else:
                record_result = await async_validate_record(
                    record,
                    model,
                    from_attributes=from_attributes,
                    strict=strict,
                    raise_errors=error_option == _options.ErrorOption.RAISE,
                )
                return idx, _typing.cast(
                    _result.RecordValidationResult | _result.JsonValidationResult,
                    record_result,
                )

    if isinstance(records, Iterator) and not isinstance(records, AsyncIterator):
        records_list = list(records)
        total = len(records_list) if records_list else None

        tasks = [validate_one(record, idx) for idx, record in enumerate(records_list)]

        for coro in asyncio.as_completed(tasks):
            idx, result = await coro

            if on_progress is not None:
                try:
                    on_progress(idx, total, result)
                except Exception:
                    pass

            if result.error and error_option == _options.ErrorOption.SKIP:
                continue

            if result.error and error_option == _options.ErrorOption.RAISE:
                raise result.error

            yield result
    else:
        total = None
        index = 0
        async for record in records:
            idx, result = await validate_one(record, index)

            if on_progress is not None:
                try:
                    on_progress(idx, total, result)
                except Exception:
                    pass

            if result.error and error_option == _options.ErrorOption.SKIP:
                index += 1
                continue

            if result.error and error_option == _options.ErrorOption.RAISE:
                raise result.error

            index += 1
            yield result
