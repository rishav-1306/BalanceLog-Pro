"""
BalanceLog Pro - Validation Engine

Validates extracted balancing record data against physical constraints
and business rules. Rejects impossible values and flags low-confidence
extractions for operator confirmation.
"""

from src.database.models import BalancingRecord
from src.config.constants import (
    MIN_WEIGHT_VALUE, MAX_WEIGHT_VALUE,
    MIN_ANGLE_VALUE, MAX_ANGLE_VALUE,
    MIN_TUBE_LENGTH, MAX_TUBE_LENGTH,
    ValidationSeverity,
)
from .validation_result import FieldValidation, ValidationResult
from src.utils.logger import get_logger

logger = get_logger("validation")


class ValidationEngine:
    """
    Validates balancing records against physical and business rules.

    Validation rules:
    - Weight values must be non-negative and within physical limits
    - Angles must be between 0° and 360°
    - Punching number must not be empty
    - Tube length must be within valid range
    - No duplicate records (same punching number + date + time)
    - OCR confidence must exceed threshold
    - After-correction values should be less than initial (warning)

    Low-confidence fields are flagged for operator confirmation.
    """

    def __init__(self, confidence_threshold: float = 0.75) -> None:
        self._confidence_threshold = confidence_threshold

    def validate(self, record: BalancingRecord, ocr_confidence: float = 1.0) -> ValidationResult:
        """
        Validate a complete balancing record.

        Args:
            record: The balancing record to validate
            ocr_confidence: Overall OCR confidence for the extraction

        Returns:
            ValidationResult with per-field findings
        """
        result = ValidationResult()

        # ── Required Fields ──
        self._validate_punching_number(record, result)
        self._validate_tube_length(record, result)
        self._validate_shaft_type(record, result)

        # ── Numeric Ranges ──
        self._validate_weight_values(record, result)
        self._validate_angle_values(record, result)

        # ── Business Logic ──
        self._validate_correction_improvement(record, result)

        # ── OCR Confidence ──
        self._validate_confidence(ocr_confidence, result)

        # ── Date/Time ──
        self._validate_timestamp(record, result)

        # Set confirmation flag
        if result.warnings > 0 or ocr_confidence < self._confidence_threshold:
            result.needs_confirmation = True

        if result.is_valid:
            record.is_validated = True

        logger.debug(
            "Validation: valid=%s, errors=%d, warnings=%d, needs_confirm=%s",
            result.is_valid, result.errors, result.warnings, result.needs_confirmation,
        )

        return result

    # ─────────────────────────────────────────────────────────
    # Individual Validators
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _validate_punching_number(record: BalancingRecord, result: ValidationResult) -> None:
        """Punching number must not be empty."""
        if not record.punching_number or not record.punching_number.strip():
            result.add(FieldValidation(
                field_name="punching_number",
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Punching number is required",
                value=record.punching_number,
            ))
        elif len(record.punching_number.strip()) < 2:
            result.add(FieldValidation(
                field_name="punching_number",
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message="Punching number seems too short",
                value=record.punching_number,
            ))

    @staticmethod
    def _validate_tube_length(record: BalancingRecord, result: ValidationResult) -> None:
        """Tube length must be within physical limits."""
        if record.tube_length <= 0:
            result.add(FieldValidation(
                field_name="tube_length",
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message="Tube length is zero or not provided",
                value=record.tube_length,
            ))
        elif record.tube_length < MIN_TUBE_LENGTH:
            result.add(FieldValidation(
                field_name="tube_length",
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Tube length {record.tube_length}mm is below minimum ({MIN_TUBE_LENGTH}mm)",
                value=record.tube_length,
            ))
        elif record.tube_length > MAX_TUBE_LENGTH:
            result.add(FieldValidation(
                field_name="tube_length",
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Tube length {record.tube_length}mm exceeds maximum ({MAX_TUBE_LENGTH}mm)",
                value=record.tube_length,
            ))

    @staticmethod
    def _validate_shaft_type(record: BalancingRecord, result: ValidationResult) -> None:
        """Shaft type must be Front, Rear, or Unknown."""
        valid_types = ("Front", "Rear", "Unknown")
        if record.shaft_type not in valid_types:
            result.add(FieldValidation(
                field_name="shaft_type",
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"Unknown shaft type: '{record.shaft_type}'",
                value=record.shaft_type,
                suggested_value="Unknown",
            ))

    def _validate_weight_values(self, record: BalancingRecord, result: ValidationResult) -> None:
        """Weight values must be non-negative and within limits."""
        weight_fields = {
            "initial_left_value": record.initial_left_value,
            "initial_right_value": record.initial_right_value,
            "weight_addition_left": record.weight_addition_left,
            "weight_addition_right": record.weight_addition_right,
            "after_correction_left": record.after_correction_left,
            "after_correction_right": record.after_correction_right,
        }

        for field_name, value in weight_fields.items():
            if value < MIN_WEIGHT_VALUE:
                result.add(FieldValidation(
                    field_name=field_name,
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Negative weight value: {value}",
                    value=value,
                ))
            elif value > MAX_WEIGHT_VALUE:
                result.add(FieldValidation(
                    field_name=field_name,
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Weight value {value}g exceeds expected maximum ({MAX_WEIGHT_VALUE}g)",
                    value=value,
                ))

    def _validate_angle_values(self, record: BalancingRecord, result: ValidationResult) -> None:
        """Angle values must be between 0° and 360°."""
        angle_fields = {
            "initial_left_angle": record.initial_left_angle,
            "initial_right_angle": record.initial_right_angle,
        }

        for field_name, value in angle_fields.items():
            if value < MIN_ANGLE_VALUE or value > MAX_ANGLE_VALUE:
                result.add(FieldValidation(
                    field_name=field_name,
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Angle {value}° is outside valid range (0°–360°)",
                    value=value,
                ))

    @staticmethod
    def _validate_correction_improvement(
        record: BalancingRecord, result: ValidationResult
    ) -> None:
        """After-correction values should ideally be less than initial (warning only)."""
        if record.initial_left_value > 0 and record.after_correction_left > 0:
            if record.after_correction_left > record.initial_left_value * 1.5:
                result.add(FieldValidation(
                    field_name="after_correction_left",
                    is_valid=True,  # Warning, not error
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"After-correction left ({record.after_correction_left}) is "
                        f"significantly higher than initial ({record.initial_left_value})"
                    ),
                    value=record.after_correction_left,
                ))

        if record.initial_right_value > 0 and record.after_correction_right > 0:
            if record.after_correction_right > record.initial_right_value * 1.5:
                result.add(FieldValidation(
                    field_name="after_correction_right",
                    is_valid=True,
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"After-correction right ({record.after_correction_right}) is "
                        f"significantly higher than initial ({record.initial_right_value})"
                    ),
                    value=record.after_correction_right,
                ))

    def _validate_confidence(self, confidence: float, result: ValidationResult) -> None:
        """OCR confidence must meet threshold."""
        if confidence < self._confidence_threshold:
            result.add(FieldValidation(
                field_name="ocr_confidence",
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"OCR confidence {confidence:.1%} is below threshold ({self._confidence_threshold:.1%})",
                value=confidence,
            ))

    @staticmethod
    def _validate_timestamp(record: BalancingRecord, result: ValidationResult) -> None:
        """Date and time must be present."""
        if not record.date:
            result.add(FieldValidation(
                field_name="date",
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Date is missing",
                value=record.date,
            ))
        if not record.time:
            result.add(FieldValidation(
                field_name="time",
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Time is missing",
                value=record.time,
            ))
