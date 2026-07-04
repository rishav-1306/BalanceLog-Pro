"""
BalanceLog Pro - Helper Utilities

Common utility functions for timestamps, image conversion, path handling,
and PyInstaller resource resolution.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np


def get_timestamp() -> str:
    """Get current timestamp as ISO format string."""
    return datetime.now().isoformat()


def get_date_str() -> str:
    """Get current date as YYYY-MM-DD string."""
    return datetime.now().strftime("%Y-%m-%d")


def get_time_str() -> str:
    """Get current time as HH:MM:SS string."""
    return datetime.now().strftime("%H:%M:%S")


def get_time_filename() -> str:
    """Get current time as HH-MM-SS string (safe for filenames)."""
    return datetime.now().strftime("%H-%M-%S")


def resource_path(relative_path: str) -> Path:
    """
    Get absolute path to a resource, works for dev and PyInstaller.

    PyInstaller creates a temp folder and stores path in _MEIPASS.
    In development, we use the project root.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent.parent
    return base_path / relative_path


def numpy_to_pixmap(image: np.ndarray):
    """
    Convert a NumPy image (BGR or grayscale) to QPixmap.

    Args:
        image: OpenCV image (numpy array)

    Returns:
        QPixmap for display in PySide6 widgets
    """
    from PySide6.QtGui import QImage, QPixmap

    if len(image.shape) == 2:
        # Grayscale
        h, w = image.shape
        bytes_per_line = w
        q_img = QImage(image.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
    elif image.shape[2] == 3:
        # BGR -> RGB
        import cv2
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    elif image.shape[2] == 4:
        # BGRA -> RGBA
        import cv2
        rgba = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        h, w, ch = rgba.shape
        bytes_per_line = ch * w
        q_img = QImage(rgba.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
    else:
        raise ValueError(f"Unsupported image shape: {image.shape}")

    return QPixmap.fromImage(q_img)


def format_confidence(confidence: float) -> str:
    """Format OCR confidence as percentage string."""
    return f"{confidence * 100:.1f}%"


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs:.0f}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"


def safe_float(value: str, default: float = 0.0) -> float:
    """Safely convert string to float, returning default on failure."""
    try:
        cleaned = value.strip().replace(",", ".")
        # Remove common OCR artifacts
        cleaned = cleaned.replace("O", "0").replace("o", "0")
        cleaned = cleaned.replace("l", "1").replace("I", "1")
        return float(cleaned)
    except (ValueError, AttributeError):
        return default


def safe_int(value: str, default: int = 0) -> int:
    """Safely convert string to integer."""
    try:
        return int(float(value.strip()))
    except (ValueError, AttributeError):
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def is_valid_date(date_str: str) -> bool:
    """Check if a string is a valid YYYY-MM-DD date."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def normalize_path(path_str: str) -> Path:
    """Normalize a path string to a Path object with forward slashes."""
    return Path(os.path.normpath(path_str))
