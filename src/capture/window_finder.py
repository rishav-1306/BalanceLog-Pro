"""
BalanceLog Pro - Window Finder

Enumerates visible Windows application windows using the Win32 API.
Finds the ABRO software window by title pattern and tracks its position.
"""

import ctypes
import ctypes.wintypes
from dataclasses import dataclass
from typing import List, Optional, Tuple

from src.utils.logger import get_logger

logger = get_logger("capture")

# ─────────────────────────────────────────────────────────────
# Win32 API Constants and Types
# ─────────────────────────────────────────────────────────────
user32 = ctypes.windll.user32
GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

DWMWA_EXTENDED_FRAME_BOUNDS = 9

try:
    dwmapi = ctypes.windll.dwmapi
except OSError:
    dwmapi = None


@dataclass
class WindowInfo:
    """Information about a visible window."""
    hwnd: int
    title: str
    rect: Tuple[int, int, int, int]  # left, top, right, bottom
    is_visible: bool
    process_id: int = 0

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    @property
    def position(self) -> Tuple[int, int]:
        return (self.rect[0], self.rect[1])


class WindowFinder:
    """
    Finds and tracks application windows on the Windows desktop.

    Uses Win32 API to enumerate windows, find the ABRO software by
    title pattern, and monitor its position/size for screen capture.
    """

    def list_all_windows(self) -> List[WindowInfo]:
        """
        Enumerate all visible, non-tool application windows.

        Returns a list of WindowInfo objects for the Settings window picker.
        """
        windows: List[WindowInfo] = []

        def enum_callback(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True

            # Skip tool windows and windows without owners
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if ex_style & WS_EX_TOOLWINDOW:
                return True

            # Get window title
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True

            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()

            if not title:
                return True

            # Get window rectangle
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

            # Skip zero-size windows
            if rect.right - rect.left <= 0 or rect.bottom - rect.top <= 0:
                return True

            # Get process ID
            pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            windows.append(WindowInfo(
                hwnd=hwnd,
                title=title,
                rect=(rect.left, rect.top, rect.right, rect.bottom),
                is_visible=True,
                process_id=pid.value,
            ))
            return True

        # Define the callback type
        WNDENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

        return windows

    def find_window_by_title(self, title_pattern: str) -> Optional[WindowInfo]:
        """
        Find a window whose title contains the given pattern (case-insensitive).

        Args:
            title_pattern: Substring to search for in window titles

        Returns:
            WindowInfo if found, None otherwise
        """
        if not title_pattern:
            return None

        pattern_lower = title_pattern.lower()
        for win in self.list_all_windows():
            if pattern_lower in win.title.lower():
                logger.debug("Found window: '%s' (HWND: %s)", win.title, win.hwnd)
                return win

        logger.warning("Window not found with pattern: '%s'", title_pattern)
        return None

    @staticmethod
    def get_window_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the current rectangle of a window by its handle.

        Uses DWM extended frame bounds for accurate sizing (accounts for
        window shadows on Windows 10/11).

        Returns: (left, top, right, bottom) or None if window is invalid
        """
        if not user32.IsWindow(hwnd):
            return None

        rect = ctypes.wintypes.RECT()

        # Try DWM extended frame bounds first (more accurate)
        if dwmapi is not None:
            result = dwmapi.DwmGetWindowAttribute(
                hwnd,
                DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(rect),
                ctypes.sizeof(rect),
            )
            if result == 0:  # S_OK
                return (rect.left, rect.top, rect.right, rect.bottom)

        # Fallback to standard GetWindowRect
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top, rect.right, rect.bottom)

        return None

    @staticmethod
    def is_window_visible(hwnd: int) -> bool:
        """Check if a window is visible and not minimized."""
        if not user32.IsWindow(hwnd):
            return False
        if not user32.IsWindowVisible(hwnd):
            return False
        # Check if minimized (iconic)
        if user32.IsIconic(hwnd):
            return False
        return True

    @staticmethod
    def get_window_title(hwnd: int) -> str:
        """Get the current title of a window."""
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    @staticmethod
    def bring_to_front(hwnd: int) -> bool:
        """Bring a window to the foreground (for calibration)."""
        try:
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False
