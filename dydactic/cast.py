import typing
from datetime import datetime
import types

import dateutil.parser  # type: ignore[import-untyped]
import pydantic


def cast_as(value: typing.Any, annotation: type) -> typing.Any:
    """Cast a value to the specified annotation type.

    Args:
        value: The value to cast
        annotation: The target type annotation

    Returns:
        The value cast to the annotation type

    Raises:
        ValueError: If value cannot be converted to annotation type
        TypeError: If casting fails
        dateutil.parser.ParserError: If datetime parsing fails
    """
    if isinstance(value, annotation):
        return value
    if annotation is datetime:
        return dateutil.parser.parse(value)
    return annotation(value)


def _is_union_type(annotation: typing.Any) -> bool:
    """Check if annotation is a union type (Union[X, Y] or X | Y).

    Args:
        annotation: The type annotation to check

    Returns:
        True if annotation is a union type, False otherwise
    """
    # Handle typing.Union
    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        return True

    # Handle Python 3.10+ X | Y syntax
    # types.UnionType is the class for X | Y syntax in Python 3.10+
    if isinstance(annotation, types.UnionType):
        return True

    # Additional check: if get_origin returns a non-None value and get_args
    # returns multiple types, it might be a union (but could also be other generics)
    # So we also check if it's specifically a union type structure
    if origin is not None:
        try:
            args = typing.get_args(annotation)
            # Union types typically have 2+ arguments
            # But we need to distinguish from other generics like tuple[int, str]
            # The safest check is origin == types.UnionType or isinstance check above
            if len(args) >= 2:
                # Check if origin indicates it's a union
                # In Python 3.10+, X | Y has origin of types.UnionType
                if origin is types.UnionType:
                    return True
        except (TypeError, AttributeError):
            pass

    return False


def _get_union_args(annotation: typing.Any) -> tuple[type, ...]:
    """Get the arguments from a union type annotation.

    Args:
        annotation: The union type annotation

    Returns:
        Tuple of types in the union

    Raises:
        ValueError: If annotation is not a union type
    """
    origin = typing.get_origin(annotation)

    # Handle typing.Union
    if origin is typing.Union:
        return typing.get_args(annotation)

    # Handle Python 3.10+ X | Y syntax
    # For X | Y, get_args() returns the union members
    if isinstance(annotation, types.UnionType) or origin is types.UnionType:
        args = typing.get_args(annotation)
        if args:
            return args
        # Fallback to direct __args__ access
        if hasattr(annotation, "__args__"):
            return typing.cast(tuple[type, ...], annotation.__args__)

    raise ValueError(f"{annotation} is not a union type")


def cast_as_union(value: typing.Any, union_annotation: typing.Any) -> typing.Any:
    """Cast a value to one of the types in a union.

    Args:
        value: The value to cast
        union_annotation: The union type annotation (Union[X, Y] or X | Y)

    Returns:
        The value cast to the first matching type in the union

    Raises:
        TypeError: If value cannot be cast to any type in the union
    """
    union_types = _get_union_args(union_annotation)
    attempted_types = []
    for _type in union_types:
        try:
            # Check if value is already the right type (before attempting cast)
            if isinstance(value, _type):
                return value
            # For non-container types, be strict about what we accept
            # Don't allow casting containers (list, dict, tuple) to scalar types unless explicitly appropriate
            if _type in (int, float, str, bool) and isinstance(
                value, (list, dict, tuple, set)
            ):
                # Only allow if it's a single-element container that could represent the type
                if isinstance(value, (list, tuple)) and len(value) == 1:
                    # Try casting the single element
                    return cast_as(value[0], _type)
                # Otherwise, this is not a valid cast
                attempted_types.append(_type)
                continue
            return cast_as(value, _type)
        except (ValueError, TypeError, dateutil.parser.ParserError):
            attempted_types.append(_type)
            continue
    raise TypeError(
        f"Failed to cast value {value!r} to any of the union types: "
        f"{', '.join(str(t) for t in attempted_types)}"
    )


def cls_annotations(cls: type) -> dict[str, type]:
    """Get type annotations from a class.

    Args:
        cls: The class to extract annotations from

    Returns:
        Dictionary mapping field names to their type annotations
    """
    return cls.__dict__.get("__annotations__", {})


def cast_as_annotation(value: typing.Any, annotation: typing.Any) -> typing.Any:
    """Cast a value according to its type annotation.

    Handles both simple types and union types.

    Args:
        value: The value to cast
        annotation: The type annotation (can be a simple type or union)

    Returns:
        The value cast to match the annotation

    Raises:
        TypeError: If casting fails
        ValueError: If value cannot be converted
    """
    if _is_union_type(annotation):
        return cast_as_union(value, annotation)
    return cast_as(value, annotation)


class ValidationError(ValueError):
    """Raised when validation fails during type casting.

    Attributes:
        errors: Dictionary mapping field names to error details
    """

    def __init__(self, errors: dict[str, dict[str, typing.Any]]) -> None:
        """Initialize ValidationError with error details.

        Args:
            errors: Dictionary mapping field names to error information
                   Each error dict should contain 'type', 'input_value', 'input_type'
        """
        self.errors = errors
        error_msg = ", ".join(
            f"{field}: expected {err['type'].__name__}, got {err['input_type'].__name__} ({err['input_value']!r})"
            for field, err in errors.items()
        )
        super().__init__(f"Validation failed: {error_msg}")


Class = typing.TypeVar("Class", bound=type)


def cast_to_annotated_class(
    d: dict[str, typing.Any], cls: Class
) -> Class | pydantic.BaseModel | object:
    """Cast a dictionary to an instance of a class using its type annotations.

    Args:
        d: Dictionary of field names and values
        cls: The class to instantiate (must have __annotations__)

    Returns:
        Instance of cls with values cast to match annotations

    Raises:
        ValidationError: If any value cannot be cast or required keys are missing
        KeyError: If dictionary contains keys not in class annotations
    """
    annotations: dict[str, type] = cls_annotations(cls)

    # Check for missing required keys
    missing_keys = set(annotations.keys()) - set(d.keys())
    if missing_keys:
        raise ValidationError(
            {
                key: {
                    "type": annotations[key],
                    "input_value": None,
                    "input_type": type(None),
                    "error": "Missing required field",
                }
                for key in missing_keys
            }
        )

    new_data: dict[str, typing.Any] = d.copy()
    errors: dict[str, dict[str, typing.Any]] = {}

    for key, value in new_data.items():
        if key not in annotations:
            # Skip extra keys (Pydantic handles this with extra='forbid' if needed)
            continue

        annotation: type = annotations[key]
        try:
            # Check if annotation is a Pydantic BaseModel subclass
            # If so, validate the value using Pydantic
            if (
                isinstance(annotation, type)
                and issubclass(annotation, pydantic.BaseModel)
                and isinstance(value, dict)
            ):
                # Nested Pydantic model - validate it
                new_data[key] = annotation.model_validate(value)
            else:
                new_data[key] = cast_as_annotation(value, annotation)
        except (ValueError, TypeError, dateutil.parser.ParserError, KeyError) as e:
            errors[key] = {
                "type": annotation,
                "input_value": value,
                "input_type": type(value),
                "error": str(e),
            }

    if errors:
        raise ValidationError(errors)

    # Handle instantiation: check if class can accept kwargs
    # If it's a Pydantic model, use model_validate
    if issubclass(cls, pydantic.BaseModel):
        # This shouldn't happen as validate_record handles Pydantic models separately
        # But handle it anyway for safety
        try:
            return cls.model_validate(new_data)
        except Exception as e:
            raise ValidationError(
                {
                    key: {
                        "type": annotations.get(key, type(None)),
                        "input_value": new_data.get(key),
                        "input_type": type(new_data.get(key))
                        if key in new_data
                        else type(None),
                        "error": str(e),
                    }
                    for key in annotations.keys()
                }
            )

    # For regular classes, check if they have an __init__ that accepts kwargs
    import inspect

    sig = inspect.signature(cls.__init__)
    params = list(sig.parameters.keys())[1:]  # Skip 'self'

    # If class has an __init__ that accepts kwargs, use it
    if any(param in ("**kwargs", "*args") or param in new_data for param in params):
        try:
            return cls(**new_data)
        except TypeError:
            # If __init__ doesn't accept kwargs, create instance and set attributes
            instance = cls.__new__(cls)
            for key, value in new_data.items():
                setattr(instance, key, value)
            return instance
    else:
        # Create instance using __new__ and set attributes
        instance = cls.__new__(cls)
        for key, value in new_data.items():
            setattr(instance, key, value)
        return instance
