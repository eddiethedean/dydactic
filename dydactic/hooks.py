"""Validation hooks and callbacks for extensibility."""

import typing

from . import result as _result


class ValidationHooks:
    """Hooks for validation events.

    All callbacks are optional. Hooks are called at different points in the
    validation pipeline to allow custom behavior.

    Attributes:
        before_validate: Called before validation starts, receives the raw record
        after_validate: Called after validation completes, receives the result
        on_success: Called only if validation succeeded, receives the result
        on_error: Called only if validation failed, receives the result
        should_continue: Called after validation to determine if processing should continue.
                        Returns True to continue, False to stop. If None, always continues.
    """

    def __init__(
        self,
        *,
        before_validate: typing.Callable[[typing.Any], None] | None = None,
        after_validate: typing.Callable[
            [_result.RecordValidationResult | _result.JsonValidationResult], None
        ]
        | None = None,
        on_success: typing.Callable[
            [_result.RecordValidationResult | _result.JsonValidationResult], None
        ]
        | None = None,
        on_error: typing.Callable[
            [_result.RecordValidationResult | _result.JsonValidationResult], None
        ]
        | None = None,
        should_continue: typing.Callable[
            [_result.RecordValidationResult | _result.JsonValidationResult], bool
        ]
        | None = None,
    ) -> None:
        """Initialize ValidationHooks.

        Args:
            before_validate: Callback(index, record) called before validation
            after_validate: Callback(result) called after validation
            on_success: Callback(result) called on successful validation
            on_error: Callback(result) called on validation error
            should_continue: Callback(result) returns whether to continue processing
        """
        self.before_validate = before_validate
        self.after_validate = after_validate
        self.on_success = on_success
        self.on_error = on_error
        self.should_continue = should_continue

    def call_before_validate(self, record: typing.Any) -> None:
        """Call before_validate hook if set.

        Args:
            record: The record about to be validated
        """
        if self.before_validate is not None:
            try:
                self.before_validate(record)
            except Exception:
                # Silently ignore hook errors to not interrupt validation
                pass

    def call_after_validate(
        self, result: _result.RecordValidationResult | _result.JsonValidationResult
    ) -> None:
        """Call after_validate hook if set.

        Args:
            result: The validation result
        """
        if self.after_validate is not None:
            try:
                self.after_validate(result)
            except Exception:
                pass

    def call_on_success(
        self, result: _result.RecordValidationResult | _result.JsonValidationResult
    ) -> None:
        """Call on_success hook if set.

        Args:
            result: The validation result (should have error=None)
        """
        if self.on_success is not None and result.error is None:
            try:
                self.on_success(result)
            except Exception:
                pass

    def call_on_error(
        self, result: _result.RecordValidationResult | _result.JsonValidationResult
    ) -> None:
        """Call on_error hook if set.

        Args:
            result: The validation result (should have error set)
        """
        if self.on_error is not None and result.error is not None:
            try:
                self.on_error(result)
            except Exception:
                pass

    def check_should_continue(
        self, result: _result.RecordValidationResult | _result.JsonValidationResult
    ) -> bool:
        """Check if processing should continue.

        Args:
            result: The validation result

        Returns:
            True if should continue, False if should stop
        """
        if self.should_continue is not None:
            try:
                return self.should_continue(result)
            except Exception:
                # On error, default to continue
                return True
        return True
