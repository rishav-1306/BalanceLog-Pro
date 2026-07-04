"""
BalanceLog Pro - Result Detector

Detects whether the ABRO software is displaying a balancing result page.
Supports multiple detection methods: manual trigger, template matching,
histogram comparison, and ORB feature matching.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional

from .screen_types import ScreenType, DetectionResult
from src.config.config_manager import ConfigManager
from src.utils.logger import get_logger

logger = get_logger("detection")


class ResultDetector:
    """
    Detects result pages in ABRO software screenshots.

    Detection methods (in order of priority):
    1. Manual trigger — operator presses "Capture" button (always available)
    2. Template matching — OpenCV matchTemplate against reference screenshot
    3. Histogram comparison — Color histogram similarity
    4. ORB feature matching — Oriented FAST + Rotated BRIEF (future)

    Template matching and histogram methods require calibration screenshots.
    """

    def __init__(self) -> None:
        self._config = ConfigManager()
        self._template: Optional[np.ndarray] = None
        self._template_gray: Optional[np.ndarray] = None
        self._reference_histogram = None
        self._load_template()

    def _load_template(self) -> None:
        """Load the reference template image from calibration config."""
        cal = self._config.calibration
        template_path = cal.get("detection", {}).get("template_path", "")

        if template_path and Path(template_path).exists():
            self._template = cv2.imread(template_path)
            if self._template is not None:
                self._template_gray = cv2.cvtColor(
                    self._template, cv2.COLOR_BGR2GRAY
                )
                # Pre-compute reference histogram
                self._reference_histogram = cv2.calcHist(
                    [self._template], [0, 1, 2], None,
                    [8, 8, 8], [0, 256, 0, 256, 0, 256],
                )
                cv2.normalize(
                    self._reference_histogram, self._reference_histogram
                )
                logger.info("Reference template loaded: %s", template_path)
            else:
                logger.warning("Failed to read template image: %s", template_path)
        else:
            logger.info("No template image configured — using manual detection mode")

    def reload_template(self) -> None:
        """Reload template after calibration changes."""
        self._template = None
        self._template_gray = None
        self._reference_histogram = None
        self._load_template()

    # ─────────────────────────────────────────────────────────
    # Main Detection Interface
    # ─────────────────────────────────────────────────────────
    def detect_result_page(self, image: np.ndarray) -> DetectionResult:
        """
        Detect if the given image is a balancing result page.

        Tries available detection methods in order of reliability.
        Falls back to manual mode if no calibration exists.

        Args:
            image: BGR screenshot of the ABRO window

        Returns:
            DetectionResult with screen type and confidence
        """
        cal = self._config.calibration
        method = cal.get("detection", {}).get("method", "manual")

        if method == "template" and self._template is not None:
            return self._detect_by_template(image)
        elif method == "histogram" and self._reference_histogram is not None:
            return self._detect_by_histogram(image)
        elif method == "orb" and self._template is not None:
            return self._detect_by_orb(image)
        else:
            # Manual mode — always return UNKNOWN, operator decides
            return DetectionResult(
                screen_type=ScreenType.UNKNOWN,
                confidence=0.0,
                method="manual",
            )

    def detect_screen_type(self, image: np.ndarray) -> DetectionResult:
        """
        Determine what type of screen is being displayed.

        Uses histogram comparison and structural analysis to classify
        the screen into RESULT, IDLE, POPUP, SETTINGS, or UNKNOWN.
        """
        if self._reference_histogram is not None:
            result = self._detect_by_histogram(image)
            if result.confidence > 0.80:
                result.screen_type = ScreenType.RESULT
                return result

        # Basic heuristic: check if the image has dialog-like properties
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)

        # Very bright images might be popups/dialogs
        if mean_brightness > 200:
            return DetectionResult(
                screen_type=ScreenType.POPUP,
                confidence=0.50,
                method="heuristic",
            )

        return DetectionResult(
            screen_type=ScreenType.UNKNOWN,
            confidence=0.0,
            method="heuristic",
        )

    # ─────────────────────────────────────────────────────────
    # Template Matching
    # ─────────────────────────────────────────────────────────
    def _detect_by_template(self, image: np.ndarray) -> DetectionResult:
        """
        Detect result page using OpenCV template matching.

        Matches a reference screenshot (or a cropped region of it)
        against the current frame.
        """
        if self._template_gray is None:
            return DetectionResult(screen_type=ScreenType.UNKNOWN, confidence=0.0)

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Resize template if sizes differ significantly
            template = self._template_gray
            if abs(gray.shape[0] - template.shape[0]) > 50:
                scale = gray.shape[0] / template.shape[0]
                new_w = int(template.shape[1] * scale)
                new_h = int(template.shape[0] * scale)
                template = cv2.resize(template, (new_w, new_h))

            # Perform template matching
            result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            threshold = self._config.calibration.get(
                "detection", {}
            ).get("confidence_threshold", 0.80)

            screen_type = ScreenType.RESULT if max_val >= threshold else ScreenType.UNKNOWN

            logger.debug(
                "Template match: confidence=%.4f, threshold=%.4f, result=%s",
                max_val, threshold, screen_type.name,
            )

            return DetectionResult(
                screen_type=screen_type,
                confidence=float(max_val),
                method="template",
                metadata={"match_location": max_loc},
            )

        except Exception as e:
            logger.error("Template matching error: %s", e)
            return DetectionResult(
                screen_type=ScreenType.UNKNOWN,
                confidence=0.0,
                method="template",
                metadata={"error": str(e)},
            )

    # ─────────────────────────────────────────────────────────
    # Histogram Comparison
    # ─────────────────────────────────────────────────────────
    def _detect_by_histogram(self, image: np.ndarray) -> DetectionResult:
        """
        Detect result page by comparing color histograms.

        Faster than template matching but less precise.
        """
        if self._reference_histogram is None:
            return DetectionResult(screen_type=ScreenType.UNKNOWN, confidence=0.0)

        try:
            hist = cv2.calcHist(
                [image], [0, 1, 2], None,
                [8, 8, 8], [0, 256, 0, 256, 0, 256],
            )
            cv2.normalize(hist, hist)

            # Compare using correlation
            similarity = cv2.compareHist(
                self._reference_histogram, hist, cv2.HISTCMP_CORREL
            )

            screen_type = ScreenType.RESULT if similarity > 0.80 else ScreenType.UNKNOWN

            return DetectionResult(
                screen_type=screen_type,
                confidence=max(0.0, float(similarity)),
                method="histogram",
            )

        except Exception as e:
            logger.error("Histogram comparison error: %s", e)
            return DetectionResult(screen_type=ScreenType.UNKNOWN, confidence=0.0)

    # ─────────────────────────────────────────────────────────
    # ORB Feature Matching (Future)
    # ─────────────────────────────────────────────────────────
    def _detect_by_orb(self, image: np.ndarray) -> DetectionResult:
        """
        Detect result page using ORB feature matching.

        More robust to scale/rotation changes than template matching.
        """
        if self._template_gray is None:
            return DetectionResult(screen_type=ScreenType.UNKNOWN, confidence=0.0)

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            orb = cv2.ORB_create(nfeatures=500)
            kp1, des1 = orb.detectAndCompute(self._template_gray, None)
            kp2, des2 = orb.detectAndCompute(gray, None)

            if des1 is None or des2 is None or len(des1) == 0 or len(des2) == 0:
                return DetectionResult(screen_type=ScreenType.UNKNOWN, confidence=0.0)

            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            matches = sorted(matches, key=lambda x: x.distance)

            # Compute match ratio
            good_matches = [m for m in matches if m.distance < 50]
            match_ratio = len(good_matches) / max(len(kp1), 1)

            screen_type = ScreenType.RESULT if match_ratio > 0.15 else ScreenType.UNKNOWN

            return DetectionResult(
                screen_type=screen_type,
                confidence=min(1.0, match_ratio * 3),
                method="orb",
                metadata={"good_matches": len(good_matches), "total_kp": len(kp1)},
            )

        except Exception as e:
            logger.error("ORB matching error: %s", e)
            return DetectionResult(screen_type=ScreenType.UNKNOWN, confidence=0.0)

    # ─────────────────────────────────────────────────────────
    # Manual Detection (always available)
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def manual_result_detected(image: np.ndarray) -> DetectionResult:
        """
        Mark the current screen as a result page (operator-triggered).

        Used when automatic detection is not calibrated.
        """
        return DetectionResult(
            screen_type=ScreenType.RESULT,
            confidence=1.0,
            method="manual",
        )
