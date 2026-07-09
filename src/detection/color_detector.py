"""
BalanceLog Pro - Color Detector

Detects the color of text within the ABRO balancing screen's blue value boxes.
Uses HSV color space analysis to distinguish RED text (initial values) from
GREEN text (after-correction values).

The ABRO screen displays:
- RED text on blue background → initial imbalance (OUT OF TOL)
- GREEN text on blue background → after correction (IN TOL)
"""

import cv2
import numpy as np
from enum import Enum, auto
from dataclasses import dataclass
from typing import Tuple

from src.utils.logger import get_logger

logger = get_logger("detection")


class TextColor(Enum):
    """Detected color of value text in the blue boxes."""
    RED = "red"
    GREEN = "green"
    UNKNOWN = "unknown"


class ValueColorState(Enum):
    """Combined color state of both left and right value boxes."""
    BOTH_RED = auto()       # Initial values — both sides show red text
    BOTH_GREEN = auto()     # After correction — both sides show green text
    MIXED = auto()          # One red, one green — correction in progress
    UNKNOWN = auto()        # Cannot determine color state


@dataclass
class ColorDetectionResult:
    """Result of color detection on one value box."""
    color: TextColor = TextColor.UNKNOWN
    red_pixel_count: int = 0
    green_pixel_count: int = 0
    total_non_blue_pixels: int = 0
    confidence: float = 0.0

    @property
    def is_confident(self) -> bool:
        """Check if the detection is reliable."""
        return self.confidence >= 0.60


class ColorDetector:
    """
    Detects text color (RED vs GREEN) within the ABRO value display boxes.

    The ABRO software uses blue boxes with large colored text:
    - RED text: HSV hue ≈ 0-10 or 170-180, high saturation
    - GREEN text: HSV hue ≈ 35-85, high saturation

    The blue background is filtered out since it has hue ≈ 100-130.

    This detector analyzes the pixel colors in a given ROI to determine
    if the displayed values are initial (red) or after-correction (green).
    """

    # ── HSV Range Definitions ──
    # Red wraps around in HSV, so we need two ranges
    RED_LOWER_1 = np.array([0, 80, 80])
    RED_UPPER_1 = np.array([12, 255, 255])
    RED_LOWER_2 = np.array([165, 80, 80])
    RED_UPPER_2 = np.array([180, 255, 255])

    # Green range
    GREEN_LOWER = np.array([35, 80, 80])
    GREEN_UPPER = np.array([85, 255, 255])

    # Blue background range (to exclude)
    BLUE_LOWER = np.array([90, 50, 50])
    BLUE_UPPER = np.array([135, 255, 255])

    # Minimum pixel count to consider a valid detection
    MIN_COLOR_PIXELS = 50

    # Minimum ratio of dominant color to total colored pixels
    MIN_DOMINANCE_RATIO = 0.55

    def __init__(self) -> None:
        pass

    def detect_text_color(self, roi_image: np.ndarray) -> ColorDetectionResult:
        """
        Detect whether the text in an ROI image is RED or GREEN.

        The ROI should be cropped to the blue value box area containing
        the weight/angle values.

        Args:
            roi_image: BGR image of the value box region

        Returns:
            ColorDetectionResult with detected color and confidence
        """
        if roi_image is None or roi_image.size == 0:
            return ColorDetectionResult()

        # Convert to HSV for color analysis
        hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)

        # Create masks for each color
        red_mask_1 = cv2.inRange(hsv, self.RED_LOWER_1, self.RED_UPPER_1)
        red_mask_2 = cv2.inRange(hsv, self.RED_LOWER_2, self.RED_UPPER_2)
        red_mask = cv2.bitwise_or(red_mask_1, red_mask_2)

        green_mask = cv2.inRange(hsv, self.GREEN_LOWER, self.GREEN_UPPER)
        blue_mask = cv2.inRange(hsv, self.BLUE_LOWER, self.BLUE_UPPER)

        # Count pixels of each color
        red_count = int(cv2.countNonZero(red_mask))
        green_count = int(cv2.countNonZero(green_mask))
        blue_count = int(cv2.countNonZero(blue_mask))

        total_pixels = roi_image.shape[0] * roi_image.shape[1]
        non_blue_colored = red_count + green_count

        result = ColorDetectionResult(
            red_pixel_count=red_count,
            green_pixel_count=green_count,
            total_non_blue_pixels=non_blue_colored,
        )

        # Need minimum colored pixels to make a decision
        if non_blue_colored < self.MIN_COLOR_PIXELS:
            logger.debug(
                "Insufficient colored pixels: red=%d, green=%d (min=%d)",
                red_count, green_count, self.MIN_COLOR_PIXELS,
            )
            result.color = TextColor.UNKNOWN
            result.confidence = 0.0
            return result

        # Determine dominant color
        if red_count > green_count:
            ratio = red_count / non_blue_colored
            if ratio >= self.MIN_DOMINANCE_RATIO:
                result.color = TextColor.RED
                result.confidence = ratio
            else:
                result.color = TextColor.UNKNOWN
                result.confidence = ratio
        else:
            ratio = green_count / non_blue_colored
            if ratio >= self.MIN_DOMINANCE_RATIO:
                result.color = TextColor.GREEN
                result.confidence = ratio
            else:
                result.color = TextColor.UNKNOWN
                result.confidence = ratio

        logger.debug(
            "Color detection: %s (red=%d, green=%d, ratio=%.2f)",
            result.color.value, red_count, green_count, result.confidence,
        )

        return result

    def detect_value_state(
        self,
        frame: np.ndarray,
        left_roi: dict,
        right_roi: dict,
    ) -> Tuple[ValueColorState, ColorDetectionResult, ColorDetectionResult]:
        """
        Detect the combined color state of both left and right value boxes.

        Args:
            frame: Full BGR screenshot of the ABRO screen
            left_roi: ROI dict for the left value box {"x": %, "y": %, "w": %, "h": %}
            right_roi: ROI dict for the right value box {"x": %, "y": %, "w": %, "h": %}

        Returns:
            Tuple of (ValueColorState, left_result, right_result)
        """
        from src.ocr.image_preprocessor import ImagePreprocessor

        # Crop the ROI regions
        left_crop = ImagePreprocessor.crop_roi(frame, left_roi)
        right_crop = ImagePreprocessor.crop_roi(frame, right_roi)

        # Detect colors
        left_result = self.detect_text_color(left_crop)
        right_result = self.detect_text_color(right_crop)

        # Determine combined state
        if not left_result.is_confident or not right_result.is_confident:
            state = ValueColorState.UNKNOWN
        elif left_result.color == TextColor.RED and right_result.color == TextColor.RED:
            state = ValueColorState.BOTH_RED
        elif left_result.color == TextColor.GREEN and right_result.color == TextColor.GREEN:
            state = ValueColorState.BOTH_GREEN
        elif left_result.color in (TextColor.RED, TextColor.GREEN) and \
             right_result.color in (TextColor.RED, TextColor.GREEN):
            state = ValueColorState.MIXED
        else:
            state = ValueColorState.UNKNOWN

        logger.debug(
            "Value state: %s (left=%s %.2f, right=%s %.2f)",
            state.name, left_result.color.value, left_result.confidence,
            right_result.color.value, right_result.confidence,
        )

        return state, left_result, right_result
