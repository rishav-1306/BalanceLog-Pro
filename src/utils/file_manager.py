"""
BalanceLog Pro - File Manager

Manages the date-based folder structure for screenshots, Excel files,
reports, and database. Handles disk space monitoring and old file cleanup.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple

from src.utils.logger import get_logger

logger = get_logger("file_manager")


class FileManager:
    """
    Manages the hierarchical folder structure:

    Balancing_Records/
        YYYY-MM-DD/
            Screenshots/
                HH-MM-SS.png
            Excel/
                Balancing_Record_YYYY-MM-DD.xlsx
            Reports/
        Database/
            balancing.db
        Logs/
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("FileManager initialized — base: %s", self._base_dir)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    # ─────────────────────────────────────────────────────────
    # Directory Creation
    # ─────────────────────────────────────────────────────────
    def get_date_dir(self, date_str: Optional[str] = None) -> Path:
        """Get or create the directory for a specific date."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        path = self._base_dir / date_str
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_screenshot_dir(self, date_str: Optional[str] = None) -> Path:
        """Get or create the screenshot directory for a date."""
        date_dir = self.get_date_dir(date_str)
        path = date_dir / "Screenshots"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_excel_dir(self, date_str: Optional[str] = None) -> Path:
        """Get or create the Excel directory for a date."""
        date_dir = self.get_date_dir(date_str)
        path = date_dir / "Excel"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_reports_dir(self, date_str: Optional[str] = None) -> Path:
        """Get or create the reports directory for a date."""
        date_dir = self.get_date_dir(date_str)
        path = date_dir / "Reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_database_dir(self) -> Path:
        """Get or create the database directory."""
        path = self._base_dir / "Database"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_logs_dir(self) -> Path:
        """Get or create the logs directory."""
        path = self._base_dir / "Logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ─────────────────────────────────────────────────────────
    # Screenshot Management
    # ─────────────────────────────────────────────────────────
    def save_screenshot_path(self, date_str: Optional[str] = None,
                             time_str: Optional[str] = None) -> Path:
        """
        Generate the full path for saving a screenshot.

        Returns: Path like Balancing_Records/2024-01-15/Screenshots/14-30-45.png
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        if time_str is None:
            time_str = datetime.now().strftime("%H-%M-%S")

        screenshot_dir = self.get_screenshot_dir(date_str)
        filename = f"{time_str}.png"

        # Avoid overwriting — append milliseconds if exists
        path = screenshot_dir / filename
        if path.exists():
            ms = datetime.now().strftime("%f")[:3]
            filename = f"{time_str}_{ms}.png"
            path = screenshot_dir / filename

        return path

    def get_excel_path(self, date_str: Optional[str] = None) -> Path:
        """Get the Excel file path for a specific date."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        excel_dir = self.get_excel_dir(date_str)
        return excel_dir / f"Balancing_Record_{date_str}.xlsx"

    # ─────────────────────────────────────────────────────────
    # Disk Space
    # ─────────────────────────────────────────────────────────
    def get_storage_info(self) -> dict:
        """
        Get storage usage information.

        Returns dict with: total_bytes, used_bytes, free_bytes,
        records_size_bytes, records_size_human
        """
        try:
            disk_usage = shutil.disk_usage(str(self._base_dir))
            records_size = self._get_dir_size(self._base_dir)
            return {
                "total_bytes": disk_usage.total,
                "used_bytes": disk_usage.used,
                "free_bytes": disk_usage.free,
                "records_size_bytes": records_size,
                "records_size_human": self._format_size(records_size),
                "free_human": self._format_size(disk_usage.free),
            }
        except OSError as e:
            logger.error("Failed to get storage info: %s", e)
            return {
                "total_bytes": 0, "used_bytes": 0, "free_bytes": 0,
                "records_size_bytes": 0, "records_size_human": "N/A",
                "free_human": "N/A",
            }

    def get_today_screenshot_count(self) -> int:
        """Count screenshots taken today."""
        today = datetime.now().strftime("%Y-%m-%d")
        ss_dir = self._base_dir / today / "Screenshots"
        if not ss_dir.exists():
            return 0
        return len(list(ss_dir.glob("*.png")))

    # ─────────────────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────────────────
    def cleanup_old_records(self, days_to_keep: int = 365) -> int:
        """
        Remove recording directories older than the specified days.
        Returns the number of directories removed.
        """
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        removed = 0
        try:
            for item in self._base_dir.iterdir():
                if item.is_dir() and self._is_date_dir(item.name):
                    try:
                        dir_date = datetime.strptime(item.name, "%Y-%m-%d")
                        if dir_date < cutoff:
                            shutil.rmtree(str(item))
                            removed += 1
                            logger.info("Cleaned up old directory: %s", item.name)
                    except ValueError:
                        continue
        except OSError as e:
            logger.error("Cleanup error: %s", e)
        return removed

    # ─────────────────────────────────────────────────────────
    # Private Helpers
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _is_date_dir(name: str) -> bool:
        """Check if a directory name matches YYYY-MM-DD format."""
        try:
            datetime.strptime(name, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def _get_dir_size(path: Path) -> int:
        """Calculate total size of a directory in bytes."""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except OSError:
            pass
        return total

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes into human-readable string."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
