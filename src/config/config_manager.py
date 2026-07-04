"""
BalanceLog Pro - Configuration Manager

Thread-safe singleton that manages all application settings and calibration data.
Persists configuration as JSON files. Provides default values for first run.
"""

import json
import threading
from pathlib import Path
from typing import Any, Optional

from .constants import (
    DEFAULT_BASE_DIR,
    DEFAULT_DB_FILENAME,
    DEFAULT_SETTINGS_FILENAME,
    DEFAULT_CALIBRATION_FILENAME,
    DEFAULT_CAPTURE_INTERVAL_MS,
    DEFAULT_OCR_LANGUAGE,
    DEFAULT_OCR_CONFIDENCE_THRESHOLD,
    DEFAULT_OCR_ENGINE,
    DEFAULT_IMAGE_SCALE_FACTOR,
    DEFAULT_SSIM_THRESHOLD,
    APP_NAME,
    APP_VERSION,
)


class ConfigManager:
    """
    Singleton configuration manager for BalanceLog Pro.

    Manages two configuration files:
    - settings.json: User preferences (paths, thresholds, theme, etc.)
    - calibration.json: ROI coordinates and template paths for OCR

    Thread-safe for concurrent access from monitoring threads.
    """

    _instance: Optional["ConfigManager"] = None
    _lock = threading.Lock()

    def __new__(cls, config_dir: Optional[Path] = None) -> "ConfigManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._rw_lock = threading.RLock()

        # Determine configuration directory
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            self._config_dir = DEFAULT_BASE_DIR

        self._config_dir.mkdir(parents=True, exist_ok=True)

        self._settings_path = self._config_dir / DEFAULT_SETTINGS_FILENAME
        self._calibration_path = self._config_dir / DEFAULT_CALIBRATION_FILENAME

        # Load or create defaults
        self._settings = self._load_or_create_settings()
        self._calibration = self._load_or_create_calibration()

    # ─────────────────────────────────────────────────────────
    # Default Settings
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _default_settings() -> dict:
        """Return default settings for first run."""
        base = str(DEFAULT_BASE_DIR)
        return {
            "app": {
                "name": APP_NAME,
                "version": APP_VERSION,
                "theme": "dark",
                "auto_startup": False,
                "language": "en",
            },
            "paths": {
                "base_directory": base,
                "screenshot_directory": str(Path(base) / "{date}" / "Screenshots"),
                "excel_directory": str(Path(base) / "{date}" / "Excel"),
                "database_directory": str(Path(base) / "Database"),
                "reports_directory": str(Path(base) / "{date}" / "Reports"),
                "logs_directory": str(Path(base) / "Logs"),
            },
            "monitoring": {
                "abro_window_title": "",
                "capture_interval_ms": DEFAULT_CAPTURE_INTERVAL_MS,
                "ssim_threshold": DEFAULT_SSIM_THRESHOLD,
                "auto_start": False,
            },
            "ocr": {
                "engine": DEFAULT_OCR_ENGINE,
                "language": DEFAULT_OCR_LANGUAGE,
                "confidence_threshold": DEFAULT_OCR_CONFIDENCE_THRESHOLD,
                "scale_factor": DEFAULT_IMAGE_SCALE_FACTOR,
                "max_retries": 3,
            },
            "database": {
                "filename": DEFAULT_DB_FILENAME,
                "wal_mode": True,
            },
            "excel": {
                "auto_export": True,
                "include_screenshots": True,
            },
        }

    @staticmethod
    def _default_calibration() -> dict:
        """Return default calibration structure."""
        return {
            "version": 1,
            "is_calibrated": False,
            "resolution": {"width": 0, "height": 0},
            "template_image_path": "",
            "rois": {},
            "detection": {
                "method": "manual",
                "template_path": "",
                "confidence_threshold": 0.80,
            },
        }

    # ─────────────────────────────────────────────────────────
    # File I/O
    # ─────────────────────────────────────────────────────────
    def _load_json(self, path: Path) -> Optional[dict]:
        """Load a JSON file safely."""
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ConfigManager] Error loading {path}: {e}")
        return None

    def _save_json(self, path: Path, data: dict) -> bool:
        """Save data to a JSON file atomically."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            tmp_path.replace(path)
            return True
        except OSError as e:
            print(f"[ConfigManager] Error saving {path}: {e}")
            return False

    def _load_or_create_settings(self) -> dict:
        """Load settings from disk or create defaults."""
        data = self._load_json(self._settings_path)
        if data is None:
            data = self._default_settings()
            self._save_json(self._settings_path, data)
        else:
            # Merge with defaults to handle missing keys after upgrades
            data = self._deep_merge(self._default_settings(), data)
        return data

    def _load_or_create_calibration(self) -> dict:
        """Load calibration from disk or create defaults."""
        data = self._load_json(self._calibration_path)
        if data is None:
            data = self._default_calibration()
            self._save_json(self._calibration_path, data)
        return data

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge override into base, preserving base keys not in override."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    # ─────────────────────────────────────────────────────────
    # Settings Access
    # ─────────────────────────────────────────────────────────
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a setting value using dot-notation path.

        Example: config.get("ocr.confidence_threshold", 0.75)
        """
        with self._rw_lock:
            keys = key_path.split(".")
            value = self._settings
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set a setting value using dot-notation path and persist.

        Example: config.set("ocr.confidence_threshold", 0.80)
        """
        with self._rw_lock:
            keys = key_path.split(".")
            d = self._settings
            for k in keys[:-1]:
                if k not in d or not isinstance(d[k], dict):
                    d[k] = {}
                d = d[k]
            d[keys[-1]] = value
            self._save_json(self._settings_path, self._settings)

    @property
    def settings(self) -> dict:
        """Return a copy of all settings."""
        with self._rw_lock:
            return json.loads(json.dumps(self._settings))

    # ─────────────────────────────────────────────────────────
    # Calibration Access
    # ─────────────────────────────────────────────────────────
    @property
    def calibration(self) -> dict:
        """Return a copy of calibration data."""
        with self._rw_lock:
            return json.loads(json.dumps(self._calibration))

    @property
    def is_calibrated(self) -> bool:
        """Check if the system has been calibrated."""
        with self._rw_lock:
            return self._calibration.get("is_calibrated", False)

    def get_roi(self, field_name: str) -> Optional[dict]:
        """Get ROI coordinates for a specific field."""
        with self._rw_lock:
            return self._calibration.get("rois", {}).get(field_name)

    def get_all_rois(self) -> dict:
        """Get all ROI configurations."""
        with self._rw_lock:
            return dict(self._calibration.get("rois", {}))

    def save_calibration(self, calibration_data: dict) -> bool:
        """Save complete calibration data and persist to disk."""
        with self._rw_lock:
            self._calibration = calibration_data
            return self._save_json(self._calibration_path, self._calibration)

    def update_roi(self, field_name: str, roi: dict) -> None:
        """Update a single ROI and persist."""
        with self._rw_lock:
            if "rois" not in self._calibration:
                self._calibration["rois"] = {}
            self._calibration["rois"][field_name] = roi
            self._save_json(self._calibration_path, self._calibration)

    # ─────────────────────────────────────────────────────────
    # Path Helpers
    # ─────────────────────────────────────────────────────────
    def get_base_dir(self) -> Path:
        """Get the base recording directory."""
        return Path(self.get("paths.base_directory", str(DEFAULT_BASE_DIR)))

    def get_screenshot_dir(self, date_str: str) -> Path:
        """Get screenshot directory for a given date."""
        template = self.get("paths.screenshot_directory", "")
        path = Path(template.replace("{date}", date_str))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_excel_dir(self, date_str: str) -> Path:
        """Get Excel directory for a given date."""
        template = self.get("paths.excel_directory", "")
        path = Path(template.replace("{date}", date_str))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_database_path(self) -> Path:
        """Get the full path to the SQLite database file."""
        db_dir = Path(self.get("paths.database_directory", str(DEFAULT_BASE_DIR / "Database")))
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / self.get("database.filename", DEFAULT_DB_FILENAME)

    def get_reports_dir(self, date_str: str) -> Path:
        """Get reports directory for a given date."""
        template = self.get("paths.reports_directory", "")
        path = Path(template.replace("{date}", date_str))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_logs_dir(self) -> Path:
        """Get the logs directory."""
        path = Path(self.get("paths.logs_directory", str(DEFAULT_BASE_DIR / "Logs")))
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ─────────────────────────────────────────────────────────
    # Reset
    # ─────────────────────────────────────────────────────────
    def reset_settings(self) -> None:
        """Reset all settings to defaults."""
        with self._rw_lock:
            self._settings = self._default_settings()
            self._save_json(self._settings_path, self._settings)

    def reset_calibration(self) -> None:
        """Reset calibration to defaults."""
        with self._rw_lock:
            self._calibration = self._default_calibration()
            self._save_json(self._calibration_path, self._calibration)

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None
