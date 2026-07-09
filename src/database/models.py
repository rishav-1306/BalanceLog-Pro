"""
BalanceLog Pro - Data Models

Dataclasses representing balancing records, search filters, and summaries.
These models are shared across database, validation, OCR, and UI layers.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class ShaftType(Enum):
    """Type of propeller shaft."""
    FRONT = "Front"
    REAR = "Rear"
    UNKNOWN = "Unknown"


@dataclass
class BalancingRecord:
    """
    Complete record of a single balancing cycle.

    Captures data from TWO phases of the ABRO screen:
    1. Initial phase (RED text) — initial imbalance values
    2. Correction phase (GREEN text) — after-correction values

    The same left_value/left_angle/right_value/right_angle ROIs are read
    in both phases. Color detection determines which phase the values
    belong to, and they are stored in the appropriate initial_* or
    after_correction_* fields.
    """
    # ── Primary Key ──
    id: Optional[int] = None

    # ── Timestamp ──
    date: str = ""          # YYYY-MM-DD
    time: str = ""          # HH:MM:SS

    # ── Identification ──
    punching_number: str = ""   # Legacy — maps to rotor_no for backward compat
    rotor_no: str = ""          # Rotor number from ABRO screen
    daily_seq: int = 0          # Serial number of the task of the day
    tube_length: float = 0.0
    shaft_type: str = "Unknown"  # Front / Rear
    actual_rpm: float = 0.0     # Actual RPM from ABRO screen

    # ── Initial Imbalance (RED text phase) ──
    initial_zero_degree: float = 0.0
    initial_left_value: float = 0.0
    initial_left_angle: float = 0.0
    initial_right_value: float = 0.0
    initial_right_angle: float = 0.0

    # ── Weight Addition (manually entered or from separate screen) ──
    weight_addition_left: float = 0.0
    weight_addition_right: float = 0.0

    # ── After Correction (GREEN text phase) ──
    after_correction_zero_degree: float = 0.0
    after_correction_left: float = 0.0         # Left value after correction
    after_correction_left_angle: float = 0.0   # Left angle after correction
    after_correction_right: float = 0.0        # Right value after correction
    after_correction_right_angle: float = 0.0  # Right angle after correction

    # ── Screenshots (one per phase) ──
    screenshot_path: str = ""              # Legacy / primary screenshot
    initial_screenshot_path: str = ""      # Screenshot of RED (initial) screen
    correction_screenshot_path: str = ""   # Screenshot of GREEN (correction) screen

    # ── Metadata ──
    ocr_confidence: float = 0.0
    operator_notes: str = ""

    # ── Internal ──
    created_at: str = ""
    updated_at: str = ""
    is_validated: bool = False

    def to_dict(self) -> dict:
        """Convert record to dictionary for database insertion."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BalancingRecord":
        """Create a record from a dictionary (database row)."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def create_new(cls) -> "BalancingRecord":
        """Create a new record with current timestamp."""
        now = datetime.now()
        return cls(
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )

    def update_timestamp(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now().isoformat()


@dataclass
class SearchFilter:
    """
    Filter criteria for searching balancing records.
    None/empty values are ignored in the query.
    """
    punching_number: str = ""
    date_from: str = ""       # YYYY-MM-DD
    date_to: str = ""         # YYYY-MM-DD
    time_from: str = ""       # HH:MM:SS
    time_to: str = ""         # HH:MM:SS
    tube_length_min: Optional[float] = None
    tube_length_max: Optional[float] = None
    shaft_type: str = ""      # Front / Rear / "" (any)
    min_confidence: Optional[float] = None
    limit: int = 500
    offset: int = 0
    order_by: str = "date"
    order_dir: str = "DESC"

    def has_filters(self) -> bool:
        """Check if any filter criteria is set."""
        return any([
            self.punching_number,
            self.date_from,
            self.date_to,
            self.time_from,
            self.time_to,
            self.tube_length_min is not None,
            self.tube_length_max is not None,
            self.shaft_type,
            self.min_confidence is not None,
        ])


@dataclass
class DailySummary:
    """Summary statistics for a single day's production."""
    date: str = ""
    total_shafts: int = 0
    front_shafts: int = 0
    rear_shafts: int = 0
    avg_initial_left: float = 0.0
    avg_initial_right: float = 0.0
    avg_final_left: float = 0.0
    avg_final_right: float = 0.0
    avg_ocr_confidence: float = 0.0
    most_common_weight_left: float = 0.0
    most_common_weight_right: float = 0.0
    screenshots_count: int = 0


@dataclass
class ReportData:
    """Data container for report generation."""
    period: str = ""          # Daily / Weekly / Monthly
    start_date: str = ""
    end_date: str = ""
    total_shafts: int = 0
    front_count: int = 0
    rear_count: int = 0
    avg_initial_imbalance: float = 0.0
    avg_final_imbalance: float = 0.0
    most_common_weight: float = 0.0
    daily_summaries: List[DailySummary] = field(default_factory=list)
    records: List[BalancingRecord] = field(default_factory=list)
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
