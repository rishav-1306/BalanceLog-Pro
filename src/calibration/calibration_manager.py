"""
BalanceLog Pro - Calibration Manager

Manages ROI calibration data persistence. Stores ROI coordinates as
percentages of image dimensions for resolution independence. Handles
template image paths and scaling between monitor resolutions.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

from src.config.config_manager import ConfigManager
from src.config.constants import ROI_FIELDS, ROI_FIELD_LABELS
from src.utils.logger import get_logger

logger = get_logger("calibration")


class CalibrationManager:
    """
    Manages the calibration workflow for ROI definition and template storage.

    ROI coordinates are stored as percentages (0.0–1.0) of the image
    dimensions, making them resolution-independent. When the monitor
    resolution changes, the same percentages apply correctly.

    Calibration data structure:
    {
        "version": 1,
        "is_calibrated": true,
        "resolution": {"width": 1920, "height": 1080},
        "template_image_path": "path/to/template.png",
        "rois": {
            "punching_number": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05},
            ...
        },
        "detection": {
            "method": "template",
            "template_path": "path/to/detection_template.png",
            "confidence_threshold": 0.80
        }
    }
    """

    def __init__(self) -> None:
        self._config = ConfigManager()

    @property
    def is_calibrated(self) -> bool:
        """Check if calibration has been performed."""
        return self._config.is_calibrated

    @property
    def calibration_data(self) -> dict:
        """Get a copy of the current calibration data."""
        return self._config.calibration

    # ─────────────────────────────────────────────────────────
    # Save / Load
    # ─────────────────────────────────────────────────────────
    def save_calibration(
        self,
        rois: Dict[str, dict],
        template_image_path: str,
        resolution: Tuple[int, int],
        detection_method: str = "manual",
        detection_template_path: str = "",
        detection_threshold: float = 0.80,
    ) -> bool:
        """
        Save a complete calibration configuration.

        Args:
            rois: Dict of field_name → {"x": %, "y": %, "w": %, "h": %}
            template_image_path: Path to the reference screenshot
            resolution: (width, height) of the monitor when calibration was done
            detection_method: "manual", "template", "histogram", or "orb"
            detection_template_path: Path to template for auto-detection
            detection_threshold: Confidence threshold for auto-detection

        Returns:
            True if save was successful
        """
        # Copy template image to calibration storage directory
        stored_template = self._store_template_image(template_image_path)
        stored_detection = ""
        if detection_template_path:
            stored_detection = self._store_template_image(
                detection_template_path, "detection_template.png"
            )

        calibration = {
            "version": 1,
            "is_calibrated": True,
            "resolution": {
                "width": resolution[0],
                "height": resolution[1],
            },
            "template_image_path": stored_template,
            "rois": rois,
            "detection": {
                "method": detection_method,
                "template_path": stored_detection,
                "confidence_threshold": detection_threshold,
            },
            "calibrated_at": datetime.now().isoformat(),
        }

        success = self._config.save_calibration(calibration)
        if success:
            logger.info(
                "Calibration saved: %d ROIs, resolution %dx%d, method=%s",
                len(rois), resolution[0], resolution[1], detection_method,
            )
        else:
            logger.error("Failed to save calibration")
        return success

    def get_rois(self) -> Dict[str, dict]:
        """Get all calibrated ROI coordinates."""
        return self._config.get_all_rois()

    def get_roi(self, field_name: str) -> Optional[dict]:
        """Get ROI for a specific field."""
        return self._config.get_roi(field_name)

    def get_resolution(self) -> Tuple[int, int]:
        """Get the resolution used during calibration."""
        cal = self._config.calibration
        res = cal.get("resolution", {})
        return (res.get("width", 0), res.get("height", 0))

    def get_template_path(self) -> str:
        """Get the stored template image path."""
        return self._config.calibration.get("template_image_path", "")

    # ─────────────────────────────────────────────────────────
    # Resolution Scaling
    # ─────────────────────────────────────────────────────────
    def scale_rois(
        self,
        from_resolution: Tuple[int, int],
        to_resolution: Tuple[int, int],
    ) -> Dict[str, dict]:
        """
        Scale ROI coordinates between resolutions.

        Since ROIs are stored as percentages, they're inherently
        resolution-independent. This method is for pixel-based conversions
        if needed.
        """
        rois = self.get_rois()

        if from_resolution == to_resolution or not rois:
            return rois

        scale_x = to_resolution[0] / from_resolution[0]
        scale_y = to_resolution[1] / from_resolution[1]

        scaled = {}
        for name, roi in rois.items():
            scaled[name] = {
                "x": roi["x"],  # Already percentage-based
                "y": roi["y"],
                "w": roi["w"],
                "h": roi["h"],
            }
        return scaled

    # ─────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────
    def validate_calibration(self) -> dict:
        """
        Validate the current calibration configuration.

        Returns a dict with 'is_valid', 'missing_fields', 'warnings'.
        """
        result = {
            "is_valid": True,
            "missing_fields": [],
            "warnings": [],
        }

        if not self.is_calibrated:
            result["is_valid"] = False
            result["warnings"].append("System is not calibrated")
            return result

        rois = self.get_rois()

        # Check for missing critical fields
        critical_fields = ["punching_number", "initial_left_value", "initial_right_value"]
        for field_name in critical_fields:
            if field_name not in rois:
                result["missing_fields"].append(field_name)
                result["is_valid"] = False

        # Check for any configured ROIs
        for field_name in ROI_FIELDS:
            if field_name not in rois:
                result["warnings"].append(
                    f"Optional field '{ROI_FIELD_LABELS.get(field_name, field_name)}' not calibrated"
                )

        # Check template image exists
        template_path = self.get_template_path()
        if template_path and not Path(template_path).exists():
            result["warnings"].append("Template image file is missing")

        return result

    def get_uncalibrated_fields(self) -> list:
        """Get list of fields that haven't been calibrated yet."""
        rois = self.get_rois()
        return [f for f in ROI_FIELDS if f not in rois]

    # ─────────────────────────────────────────────────────────
    # Reset
    # ─────────────────────────────────────────────────────────
    def reset_calibration(self) -> None:
        """Reset all calibration data."""
        self._config.reset_calibration()
        logger.info("Calibration reset to defaults")

    # ─────────────────────────────────────────────────────────
    # Template Storage
    # ─────────────────────────────────────────────────────────
    def _store_template_image(
        self, source_path: str, filename: str = "calibration_template.png"
    ) -> str:
        """Copy template image to the calibration storage directory."""
        if not source_path or not Path(source_path).exists():
            return source_path

        try:
            cal_dir = self._config.get_base_dir() / "Calibration"
            cal_dir.mkdir(parents=True, exist_ok=True)

            dest = cal_dir / filename
            shutil.copy2(source_path, str(dest))
            logger.info("Template stored: %s", dest)
            return str(dest)
        except Exception as e:
            logger.error("Failed to store template image: %s", e)
            return source_path

    @staticmethod
    def get_field_names() -> list:
        """Get the list of all ROI field names."""
        return list(ROI_FIELDS)

    @staticmethod
    def get_field_labels() -> dict:
        """Get the field name to label mapping."""
        return dict(ROI_FIELD_LABELS)
