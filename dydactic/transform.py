"""Transformations for pre-processing records before validation."""

import typing


class Transform:
    """A transformation to apply to records before validation.

    Attributes:
        func: Transformation function
        field: Field name to transform (None for record-level transform)
        apply_before_validation: Whether to apply before validation (default: True)
    """

    def __init__(
        self,
        func: typing.Callable[[typing.Any], typing.Any],
        field: str | None = None,
        apply_before_validation: bool = True,
    ) -> None:
        """Initialize Transform.

        Args:
            func: Function to apply (field value for field-level, dict for record-level)
            field: Field name for field-level transform (None for record-level)
            apply_before_validation: Apply before validation (True) or after (False)
        """
        self.func = func
        self.field = field
        self.apply_before_validation = apply_before_validation


def apply_transforms(
    record: dict[str, typing.Any],
    transforms: dict[str, Transform] | list[Transform] | None,
) -> dict[str, typing.Any]:
    """Apply transformations to a record.

    Args:
        record: Dictionary record to transform
        transforms: Dictionary mapping field names to Transform, or list of Transforms

    Returns:
        Transformed record dictionary
    """
    if transforms is None:
        return record

    result = record.copy()

    # Handle dict of transforms
    if isinstance(transforms, dict):
        for field_name, transform in transforms.items():
            if transform.field is None:
                # Record-level transform
                result = transform.func(result)
                if not isinstance(result, dict):
                    raise ValueError(
                        f"Record-level transform must return dict, got {type(result)}"
                    )
            else:
                # Field-level transform
                if field_name in result:
                    result[field_name] = transform.func(result[field_name])
    elif isinstance(transforms, list):
        # List of transforms
        for transform in transforms:
            if transform.field is None:
                # Record-level transform
                result = transform.func(result)
                if not isinstance(result, dict):
                    raise ValueError(
                        f"Record-level transform must return dict, got {type(result)}"
                    )
            else:
                # Field-level transform
                if transform.field in result:
                    result[transform.field] = transform.func(result[transform.field])

    return result
