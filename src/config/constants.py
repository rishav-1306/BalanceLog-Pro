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


# ─────────────────────────────────────────────────────────
# ROI Field Names (used in calibration)
#
# The ABRO screen shows values in blue boxes. The SAME ROI regions
# are read in both phases — color detection (RED vs GREEN) determines
# whether the values are initial or after-correction.
#
# ROI fields for the value boxes:
#   left_value_box  — covers the entire left blue box (+43.8 gm, At 5 Deg.)
#   right_value_box — covers the entire right blue box (+73.5 gm, At 154 Deg.)
#
# ROI fields for individual data extraction:
#   left_value, left_angle, right_value, right_angle — sub-regions
# ─────────────────────────────────────────────────────────
ROI_FIELDS = [
    "rotor_no",              # "Rotor No: 222" or "Rotor No: 19915 R 592 SLIP 180"
    "actual_rpm",            # "Actual RPM 2306"
    "left_value",            # "+43.8" (gm) — weight value in left blue box
    "left_angle",            # "5" (Deg.) — angle value in left blue box
    "right_value",           # "+73.5" (gm) — weight value in right blue box
    "right_angle",           # "154" (Deg.) — angle value in right blue box
    "left_value_box",        # Entire left blue box (for color detection)
    "right_value_box",       # Entire right blue box (for color detection)
]

ROI_FIELD_LABELS = {
    "rotor_no": "Rotor Number",
    "actual_rpm": "Actual RPM",
    "left_value": "Left Value (gm)",
    "left_angle": "Left Angle (Deg.)",
    "right_value": "Right Value (gm)",
    "right_angle": "Right Angle (Deg.)",
    "left_value_box": "Left Value Box (color detect)",
    "right_value_box": "Right Value Box (color detect)",
}

# Fields used for OCR text extraction (subset of ROI_FIELDS)
OCR_EXTRACT_FIELDS = [
    "rotor_no",
    "actual_rpm",
    "left_value",
    "left_angle",
    "right_value",
    "right_angle",
]

# Fields used for color detection only (not OCR)
COLOR_DETECT_FIELDS = [
    "left_value_box",
    "right_value_box",
]

# ─────────────────────────────────────────────────────────
# Full-Frame OCR — ABRO Field Regex Patterns
# Used when no ROI calibration exists. Regex patterns match
# field labels and values from raw OCR text of the full ABRO screen.
# ─────────────────────────────────────────────────────────
ABRO_FIELD_PATTERNS = {
    # "Rotor No: 222" or "Rotor No: 19915 R 592 SLIP 180"
    "rotor_no": r"[Rr]otor\s*[Nn]o[.:\s]*(.+)",
    # "Actual RPM 2306" or "RPM: 2306" or "RPM 2306"
    "actual_rpm": r"(?:[Aa]ctual\s*)?[Rr][Pp][Mm]\s*[:\s]*(\d+)",
}

# Patterns for weight values: "+43.8 gm" / "73.5 gm" / "+43.8"
ABRO_WEIGHT_PATTERN = r"[+\-]?\s*\d+\.?\d*"
# Patterns for angle values: "5 Deg" / "154 Deg." / "At 5 Deg."
ABRO_ANGLE_PATTERN = r"[Aa]t\s+(\d+\.?\d*)\s*[Dd]eg"

# Numeric OCR fields (used to decide parsing strategy)
NUMERIC_OCR_FIELDS = {"actual_rpm", "left_value", "left_angle", "right_value", "right_angle"}
