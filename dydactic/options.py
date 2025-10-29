"""Error handling options for validation operations."""

from enum import Enum


class ErrorOption(str, Enum):
    """Options for how to handle validation errors.

    Attributes:
        RETURN: Return errors in the result object without raising
        RAISE: Immediately raise exceptions when validation fails
        SKIP: Skip invalid records silently (only for iterator functions)
    """

    RETURN = "return"
    RAISE = "raise"
    SKIP = "skip"
