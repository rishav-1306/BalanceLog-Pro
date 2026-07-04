"""
BalanceLog Pro - Application Constants

Defines all application-wide constants including version info, default values,
data field enums, file paths, OCR thresholds, and UI color palette.
"""

from enum import Enum, auto
from pathlib import Path
import os

# ─────────────────────────────────────────────────────────────
# Application Identity
# ─────────────────────────────────────────────────────────────
APP_NAME = "BalanceLog Pro"
APP_VERSION = "1.0.0"
APP_AUTHOR = "BalanceLog Engineering"
APP_DESCRIPTION = "Automated Balancing Record Digitization System"
ORG_NAME = "BalanceLogPro"

# ─────────────────────────────────────────────────────────────
# Default Paths (relative to application root)
# ─────────────────────────────────────────────────────────────
DEFAULT_BASE_DIR = Path(os.path.expanduser("~")) / "Balancing_Records"
DEFAULT_DB_FILENAME = "balancing.db"
DEFAULT_SETTINGS_FILENAME = "settings.json"
DEFAULT_CALIBRATION_FILENAME = "calibration.json"

# ─────────────────────────────────────────────────────────────
# Monitoring Defaults
# ─────────────────────────────────────────────────────────────
DEFAULT_CAPTURE_INTERVAL_MS = 2000  # 2 seconds between captures
MIN_CAPTURE_INTERVAL_MS = 500
MAX_CAPTURE_INTERVAL_MS = 10000
DEFAULT_SSIM_THRESHOLD = 0.95  # Screen change detection sensitivity
DEFAULT_DUPLICATE_TIME_WINDOW_SEC = 5  # Ignore captures within this window

# ─────────────────────────────────────────────────────────────
# OCR Defaults
# ─────────────────────────────────────────────────────────────
DEFAULT_OCR_LANGUAGE = "en"
DEFAULT_OCR_CONFIDENCE_THRESHOLD = 0.75
OCR_MIN_CONFIDENCE_THRESHOLD = 0.50
OCR_MAX_RETRY_ATTEMPTS = 3
DEFAULT_IMAGE_SCALE_FACTOR = 2.0  # Upscale for better OCR
DEFAULT_OCR_ENGINE = "easyocr"  # "easyocr" or "tesseract"

# ─────────────────────────────────────────────────────────────
# Validation Ranges
# ─────────────────────────────────────────────────────────────
MIN_WEIGHT_VALUE = 0.0
MAX_WEIGHT_VALUE = 500.0  # grams
MIN_ANGLE_VALUE = 0.0
MAX_ANGLE_VALUE = 360.0
MIN_TUBE_LENGTH = 100.0  # mm
MAX_TUBE_LENGTH = 3000.0  # mm

# ─────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────
DB_SCHEMA_VERSION = 1
DB_WAL_MODE = True
DB_BUSY_TIMEOUT_MS = 5000

# ─────────────────────────────────────────────────────────────
# Excel
# ─────────────────────────────────────────────────────────────
EXCEL_HEADER_FILL_COLOR = "1E3A5F"
EXCEL_HEADER_FONT_COLOR = "FFFFFF"
EXCEL_DATE_FORMAT = "YYYY-MM-DD"
EXCEL_TIME_FORMAT = "HH:MM:SS"

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per log file
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ─────────────────────────────────────────────────────────────
# Performance
# ─────────────────────────────────────────────────────────────
MAX_MEMORY_MB = 300
MAX_IDLE_CPU_PERCENT = 10
TARGET_STARTUP_SEC = 5

# ─────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────

class ShaftType(Enum):
    """Type of propeller shaft being balanced."""
    FRONT = "Front"
    REAR = "Rear"
    UNKNOWN = "Unknown"


class MonitoringState(Enum):
    """States of the screen monitoring system."""
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()
    WINDOW_LOST = auto()


class OCREngineType(Enum):
    """Available OCR engines."""
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"


class ValidationSeverity(Enum):
    """Severity levels for validation results."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReportPeriod(Enum):
    """Report time periods."""
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    CUSTOM = "Custom"


class ExportFormat(Enum):
    """Available export formats."""
    EXCEL = "xlsx"
    CSV = "csv"
    PDF = "pdf"


# ─────────────────────────────────────────────────────────────
# UI Color Palette — Industrial Dark Theme
# ─────────────────────────────────────────────────────────────
class Colors:
    """Application color palette — off-white background with deep plum navbar/panels."""
    # Main background (off-white)
    BG_DARKEST = "#F0EEE9"
    BG_DARK = "#FAF9F6"
    BG_MEDIUM = "#F0EDE8"
    BG_LIGHT = "#E8E4DE"
    BG_CARD = "#EFEFEF"

    # Navbar / panel colour
    PRIMARY = "#372549"
    PRIMARY_LIGHT = "#4E3468"
    PRIMARY_DARK = "#261839"

    # Status colors
    SUCCESS = "#2E7D32"
    SUCCESS_LIGHT = "#43A047"
    WARNING = "#F57F17"
    WARNING_LIGHT = "#FBC02D"
    ERROR = "#C62828"
    ERROR_LIGHT = "#E53935"
    INFO = "#0277BD"

    # Text — black for main content areas, white for navbar/panels
    TEXT_PRIMARY = "#111111"
    TEXT_SECONDARY = "#444444"
    TEXT_DISABLED = "#999999"
    TEXT_ACCENT = "#372549"
    TEXT_ON_PANEL = "#FFFFFF"

    # Borders
    BORDER = "#D6D1CC"
    BORDER_LIGHT = "#C8C2BB"
    BORDER_FOCUS = "#372549"

    # Sidebar
    SIDEBAR_BG = "#372549"
    SIDEBAR_HOVER = "#4E3468"
    SIDEBAR_ACTIVE = "#261839"

    # Scrollbar
    SCROLLBAR_BG = "#E8E4DE"
    SCROLLBAR_HANDLE = "#B0A8A0"

    # Chart colors
    CHART_1 = "#372549"
    CHART_2 = "#2E7D32"
    CHART_3 = "#F57F17"
    CHART_4 = "#C62828"
    CHART_5 = "#6A1B9A"
    CHART_6 = "#00838F"


# ─────────────────────────────────────────────────────────────
# UI Fonts
# ─────────────────────────────────────────────────────────────
class Fonts:
    """Font configuration."""
    FAMILY = "Open Sans"          # Body / general text
    FAMILY_PANEL = "PT Mono"      # Navbar and panel headings (bold)
    FAMILY_MONO = "PT Mono, Courier New"
    SIZE_SMALL = 11
    SIZE_NORMAL = 13
    SIZE_LARGE = 16
    SIZE_XLARGE = 20
    SIZE_TITLE = 28
    SIZE_HERO = 42


# ─────────────────────────────────────────────────────────────
# ROI Field Names (used in calibration)
# ─────────────────────────────────────────────────────────────
ROI_FIELDS = [
    "punching_number",
    "tube_length",
    "shaft_type",
    "initial_zero_degree",
    "initial_left_value",
    "initial_left_angle",
    "initial_right_value",
    "initial_right_angle",
    "weight_addition_left",
    "weight_addition_right",
    "after_correction_zero_degree",
    "after_correction_left",
    "after_correction_right",
]

ROI_FIELD_LABELS = {
    "punching_number": "Punching Number",
    "tube_length": "Tube Length",
    "shaft_type": "Shaft Type (Front/Rear)",
    "initial_zero_degree": "Initial 0°",
    "initial_left_value": "Initial Left Value",
    "initial_left_angle": "Initial Left Angle",
    "initial_right_value": "Initial Right Value",
    "initial_right_angle": "Initial Right Angle",
    "weight_addition_left": "Weight Addition Left",
    "weight_addition_right": "Weight Addition Right",
    "after_correction_zero_degree": "After Correction 0°",
    "after_correction_left": "After Correction Left",
    "after_correction_right": "After Correction Right",
}
