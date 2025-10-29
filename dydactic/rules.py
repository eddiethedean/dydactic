"""Validation rules beyond type checking."""

import typing


class ValidationRule:
    """A validation rule to apply after type validation.

    Attributes:
        field: Field name to validate (or '*' for record-level)
        validator: Function that takes value and returns bool
        message: Error message if validation fails
        priority: Execution order (lower numbers execute first)
    """

    def __init__(
        self,
        field: str,
        validator: typing.Callable[[typing.Any], bool],
        message: str,
        priority: int = 0,
    ) -> None:
        """Initialize ValidationRule.

        Args:
            field: Field name or '*' for record-level validation
            validator: Function(value) -> bool (True if valid)
            message: Error message if validation fails
            priority: Execution order
        """
        self.field = field
        self.validator = validator
        self.message = message
        self.priority = priority

    def validate(self, value: typing.Any) -> tuple[bool, str]:
        """Validate a value.

        Args:
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            is_valid = self.validator(value)
            return (is_valid, "" if is_valid else self.message)
        except Exception as e:
            return (False, f"{self.message}: {str(e)}")


class RuleValidator:
    """Validates records against a collection of rules."""

    def __init__(self, rules: typing.Iterable[ValidationRule]) -> None:
        """Initialize RuleValidator.

        Args:
            rules: Collection of ValidationRule instances
        """
        self.rules = sorted(rules, key=lambda r: r.priority)
        self.field_rules: dict[str, list[ValidationRule]] = {}
        self.record_rules: list[ValidationRule] = []

        for rule in self.rules:
            if rule.field == "*":
                self.record_rules.append(rule)
            else:
                if rule.field not in self.field_rules:
                    self.field_rules[rule.field] = []
                self.field_rules[rule.field].append(rule)

    def validate(
        self, record: dict[str, typing.Any] | typing.Any
    ) -> dict[str, dict[str, typing.Any]]:
        """Validate a record against rules.

        Args:
            record: Record to validate (dict or validated model instance)

        Returns:
            Dictionary of errors (field -> error_info), empty if valid
        """
        errors: dict[str, dict[str, typing.Any]] = {}

        # Convert model to dict if needed
        if not isinstance(record, dict):
            if hasattr(record, "model_dump"):
                record_dict = record.model_dump()
            elif hasattr(record, "__dict__"):
                record_dict = record.__dict__
            else:
                # Can't validate non-dict/non-model
                return errors
        else:
            record_dict = record

        # Validate record-level rules
        for rule in self.record_rules:
            is_valid, error_msg = rule.validate(record_dict)
            if not is_valid:
                errors["__record__"] = {
                    "rule": rule.field,
                    "message": error_msg,
                    "type": "ValidationRule",
                    "input_value": record_dict,
                }

        # Validate field-level rules
        for field_name, field_rules in self.field_rules.items():
            if field_name in record_dict:
                value = record_dict[field_name]
                for rule in field_rules:
                    is_valid, error_msg = rule.validate(value)
                    if not is_valid:
                        if field_name not in errors:
                            errors[field_name] = {
                                "rule": rule.field,
                                "message": error_msg,
                                "type": "ValidationRule",
                                "input_value": value,
                            }

        return errors
