"""Export validation results to various formats."""

import json
import csv
import typing
from pathlib import Path

from . import result as _result

try:
    from openpyxl import Workbook  # type: ignore[import-untyped]

    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False


def _flatten_errors(
    error: typing.Any, detail_level: str = "summary"
) -> dict[str, typing.Any]:
    """Flatten validation error for export.

    Args:
        error: ValidationError instance
        detail_level: 'summary' or 'full'

    Returns:
        Dictionary with error information
    """
    if error is None:
        return {}

    error_info: dict[str, typing.Any] = {
        "error_type": type(error).__name__,
    }

    if detail_level == "full" and hasattr(error, "errors"):
        # Pydantic ValidationError
        errors_list = []
        for err_detail in error.errors():
            errors_list.append(
                {
                    "location": list(err_detail.get("loc", [])),
                    "message": err_detail.get("msg", ""),
                    "input": err_detail.get("input"),
                    "type": err_detail.get("type", ""),
                }
            )
        error_info["errors"] = errors_list
        error_info["error_count"] = len(errors_list)
    else:
        # Summary only
        error_info["error_message"] = str(error)
        if hasattr(error, "errors"):
            error_info["error_count"] = len(list(error.errors()))

    return error_info


def _serialize_value(value: typing.Any) -> typing.Any:
    """Serialize a value for JSON export.

    Args:
        value: Value to serialize

    Returns:
        Serializable value
    """
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    if hasattr(value, "model_dump"):
        # Pydantic model
        return value.model_dump()
    if hasattr(value, "model_dump_json"):
        # Pydantic model with JSON method
        return json.loads(value.model_dump_json())
    # Fallback to string representation
    return str(value)


def export_results(
    results: list[_result.RecordValidationResult | _result.JsonValidationResult],
    path: str | Path,
    *,
    format: typing.Literal["json", "csv", "excel"] = "json",
    errors_only: bool = False,
    include_original: bool = True,
    error_detail_level: typing.Literal["summary", "full"] = "summary",
) -> None:
    """Export validation results to file.

    Args:
        results: List of validation results to export
        path: Output file path
        format: Export format ('json' or 'csv')
        errors_only: If True, export only records with errors
        include_original: If True, include original input value in export
        error_detail_level: Level of error detail ('summary' or 'full')

    Raises:
        ValueError: If format is not supported
        ImportError: If Excel format requested but openpyxl not available
    """
    path = Path(path)

    # Filter results if errors_only
    filtered_results = results
    if errors_only:
        filtered_results = [r for r in results if r.error is not None]

    if format == "json":
        _export_json(filtered_results, path, include_original, error_detail_level)
    elif format == "csv":
        _export_csv(filtered_results, path, include_original, error_detail_level)
    elif format == "excel":
        if not EXCEL_AVAILABLE:
            raise ImportError(
                "Excel export requires 'openpyxl'. Install with: pip install openpyxl"
            )
        _export_excel(filtered_results, path, include_original, error_detail_level)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json', 'csv', or 'excel'")


def _export_json(
    results: list[_result.RecordValidationResult | _result.JsonValidationResult],
    path: Path,
    include_original: bool,
    error_detail_level: str,
) -> None:
    """Export results as JSON."""
    export_data = []

    for result in results:
        record_data: dict[str, typing.Any] = {
            "valid": result.error is None,
        }

        if include_original:
            record_data["original"] = _serialize_value(result.value)

        if result.error is not None:
            record_data["error"] = _flatten_errors(result.error, error_detail_level)
        else:
            if result.result is not None:
                record_data["validated"] = _serialize_value(result.result)

        export_data.append(record_data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)


def _export_csv(
    results: list[_result.RecordValidationResult | _result.JsonValidationResult],
    path: Path,
    include_original: bool,
    error_detail_level: str,
) -> None:
    """Export results as CSV."""
    rows = []

    for result in results:
        row: dict[str, typing.Any] = {
            "valid": "yes" if result.error is None else "no",
        }

        if result.error is not None:
            error_info = _flatten_errors(result.error, error_detail_level)
            row["error_type"] = error_info.get("error_type", "")
            row["error_message"] = error_info.get("error_message", str(result.error))

            if error_detail_level == "full" and "errors" in error_info:
                # Flatten multiple errors
                error_locs = []
                error_msgs = []
                for err in error_info["errors"]:
                    loc_str = ".".join(str(loc) for loc in err.get("location", []))
                    error_locs.append(loc_str)
                    error_msgs.append(err.get("message", ""))
                row["error_locations"] = "; ".join(error_locs)
                row["error_details"] = "; ".join(error_msgs)
        else:
            row["error_type"] = ""
            row["error_message"] = ""

        if include_original:
            # Flatten original dict or convert to string
            if isinstance(result.value, dict):
                for key, value in result.value.items():
                    row[f"original_{key}"] = str(value)
            else:
                row["original_value"] = str(result.value)

        if result.result is not None:
            # Flatten validated model
            if hasattr(result.result, "model_dump"):
                validated_dict = result.result.model_dump()
                for key, value in validated_dict.items():
                    row[f"validated_{key}"] = str(value)
            else:
                row["validated_result"] = str(result.result)

        rows.append(row)

    if not rows:
        # Write header-only CSV
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["valid"])
            writer.writeheader()
        return

    # Get all unique keys for fieldnames
    all_keys: set[str] = set()
    for row in rows:
        all_keys.update(row.keys())
    fieldnames = sorted(all_keys)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _export_excel(
    results: list[_result.RecordValidationResult | _result.JsonValidationResult],
    path: Path,
    include_original: bool,
    error_detail_level: str,
) -> None:
    """Export results as Excel (requires openpyxl)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Validation Results"

    if not results:
        ws.append(["valid"])
        wb.save(path)
        return

    # Build header row
    headers = ["valid", "error_type", "error_message"]
    if include_original:
        # Find all original keys
        for result in results:
            if isinstance(result.value, dict):
                for key in result.value.keys():
                    if f"original_{key}" not in headers:
                        headers.append(f"original_{key}")
            elif "original_value" not in headers:
                headers.append("original_value")
                break

    # Add validated columns
    for result in results:
        if result.result is not None and hasattr(result.result, "model_dump"):
            validated_dict = result.result.model_dump()
            for key in validated_dict.keys():
                if f"validated_{key}" not in headers:
                    headers.append(f"validated_{key}")

    ws.append(headers)

    # Write data rows
    for result in results:
        row: list[typing.Any] = [
            "yes" if result.error is None else "no",
            type(result.error).__name__ if result.error else "",
            str(result.error) if result.error else "",
        ]

        if include_original:
            if isinstance(result.value, dict):
                for key in headers[3:]:
                    if key.startswith("original_"):
                        field_name = key.replace("original_", "")
                        row.append(result.value.get(field_name, ""))
            else:
                if "original_value" in headers:
                    idx = headers.index("original_value")
                    # Pad row if needed
                    while len(row) <= idx:
                        row.append("")
                    row[idx] = str(result.value)

        # Add validated fields
        if result.result is not None and hasattr(result.result, "model_dump"):
            validated_dict = result.result.model_dump()
            for key in headers:
                if key.startswith("validated_"):
                    field_name = key.replace("validated_", "")
                    value = validated_dict.get(field_name, "")
                    if key not in [h for h in headers[: len(row)]]:
                        row.append(str(value))

        ws.append(row)

    wb.save(path)
