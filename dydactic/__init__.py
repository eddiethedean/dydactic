"""Validate iterables using Pydantic.

A Python package for easily validating iterables of dictionaries, Pydantic models,
or JSON strings against Pydantic models with flexible error handling options.
"""

__version__ = "0.2.0"

from dydactic.validate import validate
from dydactic.cast import ValidationError
from dydactic.options import ErrorOption
from dydactic.stats import ValidationStats, get_stats
from dydactic.export import export_results
from dydactic.hooks import ValidationHooks
from dydactic.transform import Transform
from dydactic.rules import ValidationRule, RuleValidator
from dydactic.schema import (
    SchemaDiff,
    FieldChange,
    schema_diff,
    detect_drift,
    DriftReport,
)

# Re-export async functions
try:
    from dydactic.async_validate import (
        async_validate,
        async_validate_record,
        async_validate_records,
        async_validate_json,
        async_validate_jsons,
    )

    __all__ = [
        "validate",
        "async_validate",
        "async_validate_record",
        "async_validate_records",
        "async_validate_json",
        "async_validate_jsons",
        "ValidationError",
        "ErrorOption",
        "ValidationStats",
        "get_stats",
        "export_results",
        "ValidationHooks",
        "Transform",
        "ValidationRule",
        "RuleValidator",
        "SchemaDiff",
        "FieldChange",
        "schema_diff",
        "detect_drift",
        "DriftReport",
    ]
except ImportError:
    __all__ = [
        "validate",
        "ValidationError",
        "ErrorOption",
        "ValidationStats",
        "get_stats",
        "export_results",
        "ValidationHooks",
        "Transform",
        "ValidationRule",
        "RuleValidator",
        "SchemaDiff",
        "FieldChange",
        "schema_diff",
        "detect_drift",
        "DriftReport",
    ]
