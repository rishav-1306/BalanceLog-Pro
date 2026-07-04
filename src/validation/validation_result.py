"""
BalanceLog Pro - Validation Result Data Structures

Data containers for validation outcomes including per-field validation
status, severity levels, and aggregate results.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from src.config.constants import ValidationSeverity


@dataclass
class FieldValidation:
    """
    Validation result for a single data field.

    Attributes:
        field_name: Name of the validated field
        is_valid: Whether the field passed all validation rules
        severity: Severity of the validation finding
        message: Human-readable validation message
        value: The value that was validated
        suggested_value: Suggested correction if invalid
    """
    field_name: str = ""
    is_valid: bool = True
    severity: ValidationSeverity = ValidationSeverity.INFO
    message: str = ""
    value: object = None
    suggested_value: object = None

    @property
    def is_error(self) -> bool:
        return self.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)

    @property
    def is_warning(self) -> bool:
        return self.severity == ValidationSeverity.WARNING


@dataclass
class ValidationResult:
    """
    Aggregate validation result for a complete balancing record.

    Attributes:
        is_valid: Overall validation passed
        field_validations: Per-field validation results
        errors: Count of error-level findings
        warnings: Count of warning-level findings
        needs_confirmation: Whether operator confirmation is required
    """
    is_valid: bool = True
    field_validations: List[FieldValidation] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    needs_confirmation: bool = False

    def add(self, validation: FieldValidation) -> None:
        """Add a field validation result and update counts."""
        self.field_validations.append(validation)
        if not validation.is_valid:
            self.is_valid = False
            if validation.is_error:
                self.errors += 1
            elif validation.is_warning:
                self.warnings += 1

    @property
    def error_messages(self) -> List[str]:
        """Get all error messages."""
        return [
            f"{v.field_name}: {v.message}"
            for v in self.field_validations
            if v.is_error
        ]

    @property
    def warning_messages(self) -> List[str]:
        """Get all warning messages."""
        return [
            f"{v.field_name}: {v.message}"
            for v in self.field_validations
            if v.is_warning
        ]

    @property
    def all_messages(self) -> List[str]:
        """Get all validation messages."""
        return [
            f"[{v.severity.value.upper()}] {v.field_name}: {v.message}"
            for v in self.field_validations
            if not v.is_valid
        ]
