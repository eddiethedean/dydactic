"""Schema comparison and drift detection utilities."""

import typing
from dataclasses import dataclass

import pydantic as _pydantic


@dataclass
class FieldChange:
    """Represents a change to a field between two schema versions.

    Attributes:
        field: Field name
        old_type: Previous type
        new_type: New type
        was_required: Whether field was required before
        is_required: Whether field is required now
    """

    field: str
    old_type: type | str
    new_type: type | str
    was_required: bool
    is_required: bool


@dataclass
class SchemaDiff:
    """Difference between two schema versions.

    Attributes:
        added_fields: Fields added in new schema
        removed_fields: Fields removed from old schema
        changed_fields: Fields with type or requirement changes
        is_breaking: Whether changes break backward compatibility
    """

    added_fields: list[str]
    removed_fields: list[str]
    changed_fields: list[FieldChange]
    is_breaking: bool


def _extract_schema_info(
    model: type[_pydantic.BaseModel],
) -> dict[str, dict[str, typing.Any]]:
    """Extract schema information from a Pydantic model.

    Args:
        model: Pydantic BaseModel class

    Returns:
        Dictionary mapping field names to field info (type, required, etc.)
    """
    schema_info: dict[str, dict[str, typing.Any]] = {}

    try:
        json_schema = model.model_json_schema()
        properties = json_schema.get("properties", {})
        required = set(json_schema.get("required", []))

        for field_name, field_info in properties.items():
            schema_info[field_name] = {
                "type": field_info.get("type", "unknown"),
                "required": field_name in required,
            }
    except Exception:
        # Fallback: try model_fields
        if hasattr(model, "model_fields"):
            for field_name, field_info in model.model_fields.items():
                schema_info[field_name] = {
                    "type": str(field_info.annotation)
                    if hasattr(field_info, "annotation")
                    else "unknown",
                    "required": field_info.is_required()
                    if hasattr(field_info, "is_required")
                    else True,
                }

    return schema_info


def schema_diff(
    old_model: type[_pydantic.BaseModel], new_model: type[_pydantic.BaseModel]
) -> SchemaDiff:
    """Compare two Pydantic model schemas and identify differences.

    Args:
        old_model: Older schema version
        new_model: Newer schema version

    Returns:
        SchemaDiff with identified changes

    Example:
        >>> diff = schema_diff(Person, PersonV2)
        >>> if diff.is_breaking:
        ...     print("Schema changes are breaking!")
    """
    old_schema = _extract_schema_info(old_model)
    new_schema = _extract_schema_info(new_model)

    old_fields = set(old_schema.keys())
    new_fields = set(new_schema.keys())

    added_fields = list(new_fields - old_fields)
    removed_fields = list(old_fields - new_fields)

    changed_fields: list[FieldChange] = []
    is_breaking = False

    # Check for changes in common fields
    for field_name in old_fields & new_fields:
        old_info = old_schema[field_name]
        new_info = new_schema[field_name]

        old_type = old_info.get("type", "unknown")
        new_type = new_info.get("type", "unknown")
        was_required = old_info.get("required", True)
        is_required = new_info.get("required", True)

        type_changed = old_type != new_type
        requirement_changed = was_required != is_required

        if type_changed or requirement_changed:
            changed_fields.append(
                FieldChange(
                    field=field_name,
                    old_type=old_type,
                    new_type=new_type,
                    was_required=was_required,
                    is_required=is_required,
                )
            )

            # Breaking if: removed required field, or type changed
            if was_required and not is_required:
                is_breaking = True
            if type_changed:
                is_breaking = True

    # Breaking if required fields were removed
    for field_name in removed_fields:
        if old_schema[field_name].get("required", True):
            is_breaking = True

    return SchemaDiff(
        added_fields=added_fields,
        removed_fields=removed_fields,
        changed_fields=changed_fields,
        is_breaking=is_breaking,
    )


@dataclass
class DriftReport:
    """Report on schema drift detected in records.

    Attributes:
        total_records: Number of records checked
        compatible_count: Number of records compatible with new schema
        incompatible_count: Number of records incompatible with new schema
        compatibility_percentage: Percentage of compatible records
        breaking_changes: List of breaking change descriptions
    """

    total_records: int
    compatible_count: int
    incompatible_count: int
    compatibility_percentage: float
    breaking_changes: list[str]


def detect_drift(
    records: typing.Iterable[dict[str, typing.Any]],
    old_model: type[_pydantic.BaseModel],
    new_model: type[_pydantic.BaseModel],
    *,
    sample_size: int | None = None,
) -> DriftReport:
    """Detect schema drift by validating records against both old and new schemas.

    Args:
        records: Iterable of record dictionaries
        old_model: Older schema version
        new_model: Newer schema version
        sample_size: Maximum number of records to sample (None for all)

    Returns:
        DriftReport with compatibility statistics

    Example:
        >>> report = detect_drift(records, Person, PersonV2)
        >>> print(f"Compatibility: {report.compatibility_percentage:.1f}%")
    """
    records_list = list(records)
    if sample_size is not None and len(records_list) > sample_size:
        import random

        records_list = random.sample(records_list, sample_size)

    compatible_count = 0
    incompatible_count = 0

    for record in records_list:
        # Try validating against new model
        try:
            new_model.model_validate(record)
            compatible_count += 1
        except Exception:
            incompatible_count += 1

    total = len(records_list)
    compatibility_percentage = (compatible_count / total * 100) if total > 0 else 0.0

    # Get breaking changes from schema diff
    diff = schema_diff(old_model, new_model)
    breaking_changes = []
    if diff.is_breaking:
        breaking_changes.append("Schema changes are breaking")
        if diff.removed_fields:
            breaking_changes.append(f"Removed fields: {', '.join(diff.removed_fields)}")
        for change in diff.changed_fields:
            if change.was_required and not change.is_required:
                breaking_changes.append(f"Field '{change.field}' is no longer required")
            if str(change.old_type) != str(change.new_type):
                breaking_changes.append(
                    f"Field '{change.field}' type changed: {change.old_type} -> {change.new_type}"
                )

    return DriftReport(
        total_records=total,
        compatible_count=compatible_count,
        incompatible_count=incompatible_count,
        compatibility_percentage=compatibility_percentage,
        breaking_changes=breaking_changes,
    )
