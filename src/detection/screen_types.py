"""
BalanceLog Pro - Screen Types

Enumerations and data structures for screen detection results.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any


class ScreenType(Enum):
    """Types of screens that may be displayed in the ABRO software."""
    RESULT = auto()      # Balancing result page with measurement data
    IDLE = auto()        # Machine idle / waiting for cycle
    POPUP = auto()       # Dialog box or popup message
    SETTINGS = auto()    # Settings or configuration page
    MEASURING = auto()   # Measurement in progress
    UNKNOWN = auto()     # Unrecognized screen


@dataclass
class DetectionResult:
    """
    Result of a screen type detection operation.

    Attributes:
        screen_type: Detected type of the screen
        confidence: How confident the detection is (0.0 to 1.0)
        method: Detection method used (manual, template, histogram, orb)
        metadata: Additional detection info (template match location, etc.)
    """
    screen_type: ScreenType = ScreenType.UNKNOWN
    confidence: float = 0.0
    method: str = "manual"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_result_page(self) -> bool:
        """Check if the detected screen is a result page."""
        return self.screen_type == ScreenType.RESULT

    @property
    def is_confident(self) -> bool:
        """Check if detection confidence exceeds the minimum threshold."""
        return self.confidence >= 0.70

    def __str__(self) -> str:
        return (
            f"DetectionResult(type={self.screen_type.name}, "
            f"confidence={self.confidence:.2f}, method={self.method})"
        )
