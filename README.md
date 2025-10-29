# dydactic

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**dydactic** is a Python package for easily validating iterables of dictionaries, Pydantic models, or JSON strings against Pydantic models with flexible error handling options.

## Features

- 🔄 **Validate iterables** - Process multiple records efficiently
- 🎯 **Multiple input types** - Supports dictionaries, Pydantic models, and JSON strings
- ⚡ **Flexible error handling** - Choose how to handle validation errors (return, raise, or skip)
- 🏗️ **Type casting** - Automatic type coercion with support for union types and datetime parsing
- 🛡️ **Pydantic integration** - Full support for Pydantic v2 models
- 🔧 **Custom classes** - Validate against annotated Python classes (not just Pydantic models)
- ✨ **Python 3.10+** - Supports modern Python type hints including `X | Y` union syntax

- 🚀 **Async validation** - Concurrent validators for I/O-heavy pipelines
- 📊 **Validation stats** - Aggregate counts and error metrics
- 🪝 **Hooks** - Lifecycle hooks to observe or mutate processing
- 📐 **Rules** - Pluggable rule validators for cross-field checks
- 🧭 **Schema diff & drift** - Compare models and detect field-level changes
- 🔁 **Transform helpers** - Pre/post validation transformations
- 📤 **Export** - Utilities to export results and reports

## Installation

```bash
pip install dydactic
```

Or with optional dev dependencies for testing:

```bash
pip install dydactic[dev]
```

## Quick Start

```python
from dydactic import validate, ErrorOption
import pydantic

# Define your Pydantic model
class Person(pydantic.BaseModel):
    id: int
    name: str
    age: float

# Validate a list of dictionaries
records = [
    {'id': 1, 'name': 'Alice', 'age': 30.0},
    {'id': 2, 'name': 'Bob', 'age': 25.5},
]

# Process results
for result in validate(records, Person):
    if result.error:
        print(f"Validation failed: {result.error}")
    else:
        print(f"Valid: {result.result.name}")
```

## Async Usage

```python
import asyncio
from dydactic import async_validate
import pydantic

class Person(pydantic.BaseModel):
    id: int
    name: str

async def main():
    records = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]

    async for result in async_validate(records, Person):
        if result.error is None:
            print(result.result)

asyncio.run(main())
```

## Usage Examples

### Basic Validation

```python
from dydactic import validate
import pydantic

class User(pydantic.BaseModel):
    email: str
    age: int

records = [
    {'email': 'alice@example.com', 'age': 30},
    {'email': 'bob@example.com', 'age': 25},
]

# Validate all records
for result in validate(records, User):
    if result.error is None:
        print(f"✅ {result.result.email}")
    else:
        print(f"❌ Error: {result.error}")
```

### Error Handling Options

dydactic provides three ways to handle validation errors:

#### 1. RETURN (Default) - Errors returned in result

```python
from dydactic import validate, ErrorOption

records = [
    {'id': 1, 'name': 'Alice', 'age': 30.0},  # Valid
    {'id': 'invalid', 'name': 'Bob', 'age': 25.5},  # Invalid
]

for result in validate(records, Person, error_option=ErrorOption.RETURN):
    if result.error:
        print(f"Error in record: {result.error}")
    else:
        print(f"Valid: {result.result.name}")
```

#### 2. RAISE - Exceptions raised immediately

```python
from dydactic import validate, ErrorOption
import pydantic

try:
    records = [
        {'id': 1, 'name': 'Alice', 'age': 30.0},
        {'id': 'invalid', 'name': 'Bob', 'age': 25.5},  # Will raise here
    ]
    for result in validate(records, Person, error_option=ErrorOption.RAISE):
        print(f"Valid: {result.result.name}")
except pydantic.ValidationError as e:
    print(f"Validation failed: {e}")
```

#### 3. SKIP - Invalid records skipped silently

```python
from dydactic import validate, ErrorOption

records = [
    {'id': 1, 'name': 'Alice', 'age': 30.0},  # Valid
    {'id': 'invalid', 'name': 'Bob', 'age': 25.5},  # Skipped
    {'id': 3, 'name': 'Charlie', 'age': 35.0},  # Valid
]

# Only valid records are yielded
for result in validate(records, Person, error_option=ErrorOption.SKIP):
    print(f"Valid: {result.result.name}")  # Only Alice and Charlie
```

### JSON String Validation

```python
from dydactic import validate

json_records = [
    '{"id": 1, "name": "Alice", "age": 30.0}',
    '{"id": 2, "name": "Bob", "age": 25.5}',
]

for result in validate(json_records, Person):
    if result.error is None:
        print(f"Valid JSON: {result.result.name}")
```

### Mixed Record Types

The `validate()` function automatically detects whether each item is a dictionary/model or JSON string:

```python
mixed_data = [
    {'id': 1, 'name': 'Alice', 'age': 30.0},  # Dictionary
    '{"id": 2, "name": "Bob", "age": 25.5}',  # JSON string
    {'id': 3, 'name': 'Charlie', 'age': 35.0},  # Dictionary
]

for result in validate(mixed_data, Person):
    print(f"Valid: {result.result.name}")
```

### Custom Annotated Classes

You can validate against any class with type annotations (not just Pydantic models):

```python
from dydactic import validate

class PersonClass:
    id: int
    name: str
    age: float

records = [
    {'id': 1, 'name': 'Alice', 'age': 30.0},
    {'id': 2, 'name': 'Bob', 'age': 25.5},
]

for result in validate(records, PersonClass):
    if result.error is None:
        person = result.result
        print(f"{person.name} (ID: {person.id})")
```

### Type Coercion and Datetime Parsing

dydactic automatically handles type coercion and datetime parsing:

```python
from datetime import datetime
from dydactic import validate

class Event:
    name: str
    timestamp: datetime

records = [
    {'name': 'Meeting', 'timestamp': '2023-01-01T12:00:00'},  # String parsed to datetime
    {'name': 'Conference', 'timestamp': datetime(2023, 6, 15, 10, 0)},  # Already datetime
]

for result in validate(records, Event):
    if result.error is None:
        print(f"{result.result.name} at {result.result.timestamp}")
```

### Union Types

Support for both `typing.Union` and Python 3.10+ `X | Y` syntax:

```python
from typing import Union
from dydactic import validate

class Config:
    value: int | str  # Python 3.10+ syntax
    # or: value: Union[int, str]  # Also works

records = [
    {'value': 42},  # int
    {'value': 'hello'},  # str
]

for result in validate(records, Config):
    print(f"Value: {result.result.value} (type: {type(result.result.value).__name__})")
```

### Strict Validation

Use Pydantic's strict mode for type checking:

```python
from dydactic import validate

# With strict=False (default), type coercion is allowed
records_permissive = [{'id': 1.0, 'name': 'Alice', 'age': 30}]  # float coerced to int
for result in validate(records_permissive, Person, strict=False):
    print(result.result.id)  # 1 (coerced)

# With strict=True, exact types required
records_strict = [{'id': 1.0, 'name': 'Alice', 'age': 30}]  # Will fail
for result in validate(records_strict, Person, strict=True):
    if result.error:
        print("Strict validation failed")  # This will print
```

## API Reference

### Main Functions

#### `validate()`

The main entry point for validating iterables of mixed record types.

```python
validate(
    records: Iterator[Record | Json],
    model: BaseModel,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    error_option: ErrorOption = ErrorOption.RETURN
) -> Generator[RecordValidationResult | JsonValidationResult, None, None]
```

**Parameters:**
- `records`: Iterator of dictionaries, Pydantic models, or JSON strings
- `model`: Pydantic BaseModel class to validate against
- `from_attributes`: Whether to validate from object attributes (Pydantic only)
- `strict`: Whether to use strict type validation
- `error_option`: How to handle errors (`RETURN`, `RAISE`, or `SKIP`)

**Returns:** Generator yielding validation results

#### `async_validate()`

Asynchronous variant that yields results using an async generator.

```python
async_validate(
    records: Iterator[Record | Json],
    model: BaseModel,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    error_option: ErrorOption = ErrorOption.RETURN
) -> AsyncGenerator[RecordValidationResult | JsonValidationResult, None]
```

#### `validate_record()`

Validate a single record.

```python
validate_record(
    record: Record,
    model: BaseModel | Callable,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    raise_errors: bool = False
) -> RecordValidationResult
```

#### `validate_records()`

Validate an iterator of records.

```python
validate_records(
    records: Iterator[Record],
    model: BaseModel,
    *,
    from_attributes: bool | None = None,
    strict: bool | None = None,
    error_option: ErrorOption = ErrorOption.RETURN
) -> Generator[RecordValidationResult, None, None]
```

#### `validate_json()`

Validate a single JSON string.

```python
validate_json(
    json: Json,
    model: BaseModel,
    *,
    strict: bool | None = None,
    raise_errors: bool = False
) -> JsonValidationResult
```

#### `validate_jsons()`

Validate an iterator of JSON strings.

```python
validate_jsons(
    records: Iterator[Json],
    model: BaseModel,
    *,
    strict: bool | None = None,
    error_option: ErrorOption = ErrorOption.RETURN
) -> Generator[JsonValidationResult, None, None]
```

### Result Types

#### `RecordValidationResult`

```python
class RecordValidationResult(NamedTuple):
    error: ValidationError | None  # None if validation succeeded
    result: BaseModel | None       # Validated model instance if successful
    value: Record                  # Original input record
```

#### `JsonValidationResult`

```python
class JsonValidationResult(NamedTuple):
    error: ValidationError | None  # None if validation succeeded
    result: BaseModel | None       # Validated model instance if successful
    value: Json                    # Original JSON string
```

### Error Handling

#### `ErrorOption`

Enum for error handling strategies:

- `ErrorOption.RETURN`: Return errors in result objects (default)
- `ErrorOption.RAISE`: Raise exceptions immediately on first error
- `ErrorOption.SKIP`: Skip invalid records silently (iterator functions only)

#### `ValidationError`

Custom exception raised when validation fails:

```python
class ValidationError(ValueError):
    errors: dict[str, dict[str, Any]]  # Field-level error details
```

### Stats

Compute aggregate metrics about a run.

```python
from dydactic import get_stats

stats = get_stats(results_iterable)
print(stats.total, stats.valid, stats.invalid)
```

### Hooks

Lifecycle hooks to observe or mutate processing.

```python
from dydactic import ValidationHooks

hooks = ValidationHooks(
    on_before_validate=lambda x: x,
    on_after_validate=lambda r: r,
)
```

### Rules

Define cross-field or dataset rules.

```python
from dydactic import ValidationRule, RuleValidator

class NonEmptyName(ValidationRule):
    def check(self, item) -> bool:
        return bool(getattr(item, "name", None))

validator = RuleValidator([NonEmptyName()])
```

### Schema diff and drift

Compare models and report field-level changes.

```python
from dydactic import schema_diff, detect_drift

diff = schema_diff(ModelV1, ModelV2)
drift = detect_drift(ModelV1, observed_records)
```

### Transform

Helpers to perform pre/post transformations around validation.

```python
from dydactic import Transform

transform = Transform(pre=lambda x: x, post=lambda y: y)
```

## Requirements

- Python >= 3.10
- Pydantic >= 2.9.2
- python-dateutil

## Development

### Installing for Development

```bash
git clone https://github.com/yourusername/dydactic.git
cd dydactic
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=dydactic --cov-report=html
```

### Type Checking

```bash
mypy dydactic
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Performance Notes

dydactic validates records one at a time using a generator pattern. While Pydantic doesn't provide a built-in bulk validation API, this approach offers:

- **Streaming support** for large datasets without materializing everything in memory
- **Flexible error handling** with per-item control (RETURN, RAISE, SKIP)
- **Works with generators** for memory-efficient processing
- **Supports mixed types** (dicts, models, JSON strings)

For performance-critical use cases with small-to-medium datasets, Pydantic's `TypeAdapter` can validate entire lists at once, but this loses streaming benefits and per-item error control. See `BULK_VALIDATION.md` for detailed analysis.

## Changelog

### 0.2.0

- Added asynchronous validation API (`async_validate`, `async_validate_record`, `async_validate_records`, `async_validate_json`, `async_validate_jsons`)
- Introduced validation hooks (`ValidationHooks`) for lifecycle callbacks
- Added validation rules framework (`ValidationRule`, `RuleValidator`)
- Added schema comparison and drift detection (`schema_diff`, `detect_drift`, `DriftReport`)
- Added statistics helpers (`ValidationStats`, `get_stats`)
- Added export utilities (`export_results`)
- Added transform helpers (`Transform`)
- Expanded public `__all__` and top-level imports in `dydactic/__init__.py`
- Updated docs and examples

### 0.1.2

- Fixed critical bugs (bare except clauses, union type detection)
- Added comprehensive test suite
- Improved error messages and documentation
- Added support for Python 3.10+ union syntax (`X | Y`)
- Enhanced type hints and docstrings
- Modernized codebase with best practices
