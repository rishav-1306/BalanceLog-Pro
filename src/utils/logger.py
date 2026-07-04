"""
BalanceLog Pro - Logging Setup

Configures rotating file handlers for application, OCR, error, capture,
and performance logs. Each log channel writes to its own file with rotation.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.config.constants import LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOG_FORMAT, LOG_DATE_FORMAT

# Global registry of initialized loggers
_initialized = False
_log_dir: Optional[Path] = None


def setup_logging(log_dir: Path, console_level: int = logging.INFO) -> None:
    """
    Initialize all logging channels with rotating file handlers.

    Creates separate log files for:
    - app.log       — general application events
    - ocr.log       — OCR-specific operations and confidence scores
    - error.log     — errors and exceptions only
    - capture.log   — screen capture events
    - performance.log — timing and resource usage

    Args:
        log_dir: Directory to store log files
        console_level: Minimum level for console output
    """
    global _initialized, _log_dir
    if _initialized:
        return

    _log_dir = Path(log_dir)
    _log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # ── Channel definitions ──
    channels = {
        "balancelog":    ("app.log",         logging.DEBUG),
        "balancelog.ocr":       ("ocr.log",         logging.DEBUG),
        "balancelog.capture":   ("capture.log",     logging.DEBUG),
        "balancelog.performance": ("performance.log", logging.DEBUG),
    }

    for logger_name, (filename, level) in channels.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = (logger_name != "balancelog")  # only root propagates

        # Rotating file handler
        file_handler = RotatingFileHandler(
            str(_log_dir / filename),
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # ── Error-only handler (catches WARNING+ from all channels) ──
    error_handler = RotatingFileHandler(
        str(_log_dir / "error.log"),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    logging.getLogger("balancelog").addHandler(error_handler)

    # ── Console handler ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logging.getLogger("balancelog").addHandler(console_handler)

    _initialized = True
    logging.getLogger("balancelog").info("Logging system initialized — log dir: %s", _log_dir)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger under the balancelog hierarchy.

    Usage:
        logger = get_logger("ocr")         # -> balancelog.ocr
        logger = get_logger("capture")     # -> balancelog.capture
        logger = get_logger("ui.dashboard") # -> balancelog.ui.dashboard
    """
    if name.startswith("balancelog"):
        return logging.getLogger(name)
    return logging.getLogger(f"balancelog.{name}")


def get_log_dir() -> Optional[Path]:
    """Return the current log directory path."""
    return _log_dir
