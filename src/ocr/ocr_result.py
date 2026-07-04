"""
BalanceLog Pro - OCR Result Data Structures

Data containers for OCR extraction results including confidence scores,
bounding boxes, and per-field extraction outcomes.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OCRResult:
    """
    Result of a single OCR operation on one ROI region.

    Attributes:
        text: Raw text extracted by OCR
        confidence: OCR engine confidence (0.0 to 1.0)
        bounding_box: Coordinates of detected text within the ROI
        engine_used: Which OCR engine produced this result
        preprocessing: Which preprocessing pipeline was applied
    """
    text: str = ""
    confidence: float = 0.0
    bounding_box: Optional[List[int]] = None
    engine_used: str = "easyocr"
    preprocessing: str = "default"

    @property
    def is_confident(self) -> bool:
        """Check if the result meets the minimum confidence threshold."""
        return self.confidence >= 0.75

    @property
    def cleaned_text(self) -> str:
        """Return text with common OCR artifacts cleaned."""
        return self.text.strip()


@dataclass
class FieldExtractionResult:
    """
    Result of extracting a specific data field from the ABRO screen.

    Combines the raw OCR result with parsed/typed value and field metadata.

    Attributes:
        field_name: Name of the data field (e.g., 'punching_number')
        field_label: Human-readable label (e.g., 'Punching Number')
        raw_text: Raw OCR text before parsing
        parsed_value: Typed value after parsing (float, str, etc.)
        confidence: OCR confidence for this field
        is_valid: Whether the parsed value passed validation
        error_message: Validation error message if invalid
    """
    field_name: str = ""
    field_label: str = ""
    raw_text: str = ""
    parsed_value: Any = None
    confidence: float = 0.0
    is_valid: bool = True
    error_message: str = ""
    engine_used: str = "easyocr"

    def __str__(self) -> str:
        status = "✓" if self.is_valid else "✗"
        return (
            f"{status} {self.field_label}: '{self.raw_text}' → "
            f"{self.parsed_value} (confidence: {self.confidence:.2f})"
        )


@dataclass
class ExtractionSummary:
    """
    Summary of all field extractions from a single result screen.

    Attributes:
        fields: Per-field extraction results
        overall_confidence: Average confidence across all fields
        total_fields: Number of fields extracted
        valid_fields: Number of fields that passed validation
        screenshot_path: Path to the source screenshot
        extraction_time_ms: Time taken for extraction in milliseconds
    """
    fields: Dict[str, FieldExtractionResult] = field(default_factory=dict)
    overall_confidence: float = 0.0
    total_fields: int = 0
    valid_fields: int = 0
    screenshot_path: str = ""
    extraction_time_ms: float = 0.0

    def compute_summary(self) -> None:
        """Recalculate summary statistics from field results."""
        if not self.fields:
            return
        self.total_fields = len(self.fields)
        confidences = [f.confidence for f in self.fields.values()]
        self.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        self.valid_fields = sum(1 for f in self.fields.values() if f.is_valid)

    @property
    def all_valid(self) -> bool:
        """Check if all fields passed validation."""
        return self.valid_fields == self.total_fields

    @property
    def needs_review(self) -> bool:
        """Check if any field has low confidence or failed validation."""
        return not self.all_valid or self.overall_confidence < 0.75
