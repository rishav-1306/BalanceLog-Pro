"""
BalanceLog Pro - Screen Monitor

Background QThread that continuously monitors the ABRO software window,
detects screen changes via frame differencing, detects text color (RED/GREEN)
in the value boxes, and tracks the balancing test lifecycle through a
state machine.

Emits test_complete when both initial (RED) and correction (GREEN) phases
are captured for a single test.
"""

import time
import numpy as np
import cv2
import mss
from typing import Optional, Tuple

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from src.capture.window_finder import WindowFinder, WindowInfo
from src.capture.test_state_machine import TestStateMachine, TestEvent, TestCycleData
from src.detection.color_detector import ColorDetector, ValueColorState, TextColor
from src.detection.screen_types import TestPhase
from src.config.constants import (
    DEFAULT_CAPTURE_INTERVAL_MS,
    DEFAULT_SSIM_THRESHOLD,
    MonitoringState,
)
from src.utils.logger import get_logger

logger = get_logger("capture")


class ScreenMonitor(QThread):
    """
    Background thread that monitors the ABRO software window.

    Features:
    - Captures only the ABRO window region (not full desktop)
    - Frame differencing to detect screen changes (SSIM comparison)
    - Color detection (RED/GREEN) on value boxes
    - Test lifecycle state machine (initial → running → correction)
    - Prevents duplicate captures
    - Emits signals for UI integration
    - Low CPU usage via configurable capture interval
    - Graceful handling of window minimize/close/move/resize

    Signals:
        screen_captured(np.ndarray): Emitted when a new frame is captured
        screen_changed(np.ndarray): Emitted when screen content changes
        result_detected(np.ndarray): Emitted when a result page is detected
        test_phase_changed(str): Emitted when the test phase changes
        test_complete(dict): Emitted when both initial + correction captured
        color_state_changed(str): Emitted when detected color state changes
        window_lost(): Emitted when the ABRO window is no longer found
        window_found(str): Emitted when the ABRO window is found/refound
        monitoring_state_changed(str): Emitted when monitoring state changes
        error_occurred(str): Emitted on errors
        stats_updated(dict): Emitted with performance statistics
    """

    # ── Signals ──
    screen_captured = Signal(np.ndarray)
    screen_changed = Signal(np.ndarray)
    result_detected = Signal(np.ndarray)
    test_phase_changed = Signal(str)
    test_complete = Signal(dict)
    color_state_changed = Signal(str)
    window_lost = Signal()
    window_found = Signal(str)
    monitoring_state_changed = Signal(str)
    error_occurred = Signal(str)
    stats_updated = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mutex = QMutex()
        self._window_finder = WindowFinder()

        # Configuration
        self._window_title: str = ""
        self._capture_interval_ms: int = DEFAULT_CAPTURE_INTERVAL_MS
        self._ssim_threshold: float = DEFAULT_SSIM_THRESHOLD

        # State
        self._state = MonitoringState.IDLE
        self._running = False
        self._hwnd: int = 0
        self._previous_frame: Optional[np.ndarray] = None
        self._capture_count: int = 0
        self._change_count: int = 0
        self._last_capture_time: float = 0

        # Color detection and state machine
        self._color_detector = ColorDetector()
        self._state_machine = TestStateMachine()
        self._last_color_state = ValueColorState.UNKNOWN

        # Frame stability tracking
        self._consecutive_stable_frames: int = 0
        self._stability_threshold = 3  # frames

        # ROI coordinates for color detection (set via calibration)
        self._left_box_roi: Optional[dict] = None
        self._right_box_roi: Optional[dict] = None

    # ─────────────────────────────────────────────────────────
    # Configuration
    # ─────────────────────────────────────────────────────────
    def set_window_title(self, title: str) -> None:
        """Set the ABRO window title pattern to search for."""
        with QMutexLocker(self._mutex):
            self._window_title = title

    def set_capture_interval(self, interval_ms: int) -> None:
        """Set the capture interval in milliseconds."""
        with QMutexLocker(self._mutex):
            self._capture_interval_ms = max(500, min(10000, interval_ms))

    def set_ssim_threshold(self, threshold: float) -> None:
        """Set the SSIM threshold for change detection (0.0 to 1.0)."""
        with QMutexLocker(self._mutex):
            self._ssim_threshold = max(0.5, min(1.0, threshold))

    def set_color_rois(self, left_roi: dict, right_roi: dict) -> None:
        """Set the ROI coordinates for color detection on value boxes."""
        with QMutexLocker(self._mutex):
            self._left_box_roi = left_roi
            self._right_box_roi = right_roi

    @property
    def state(self) -> MonitoringState:
        return self._state

    @property
    def capture_count(self) -> int:
        return self._capture_count

    @property
    def change_count(self) -> int:
        return self._change_count

    @property
    def test_phase(self) -> TestPhase:
        """Current test phase from the state machine."""
        return self._state_machine.phase

    @property
    def test_phase_name(self) -> str:
        """Human-readable current test phase name."""
        return self._state_machine.phase_name

    # ─────────────────────────────────────────────────────────
    # Control
    # ─────────────────────────────────────────────────────────
    def start_monitoring(self) -> None:
        """Start the monitoring thread."""
        with QMutexLocker(self._mutex):
            self._running = True
            self._previous_frame = None
            self._capture_count = 0
            self._change_count = 0
            self._consecutive_stable_frames = 0
            self._state_machine.reset()
        self._set_state(MonitoringState.RUNNING)
        if not self.isRunning():
            self.start()
        logger.info("Monitoring started — target: '%s'", self._window_title)

    def stop_monitoring(self) -> None:
        """Stop the monitoring thread gracefully."""
        with QMutexLocker(self._mutex):
            self._running = False
        self._set_state(MonitoringState.IDLE)
        logger.info("Monitoring stop requested")
        self.wait(3000)  # Wait up to 3 seconds for thread to finish

    def _set_state(self, state: MonitoringState) -> None:
        """Update monitoring state and emit signal."""
        self._state = state
        self.monitoring_state_changed.emit(state.name)

    def reset_test(self) -> None:
        """Reset the test state machine (e.g., after operator cancels a test)."""
        self._state_machine.reset()
        self._consecutive_stable_frames = 0
        self.test_phase_changed.emit(self._state_machine.phase_name)

    # ─────────────────────────────────────────────────────────
    # Manual Triggers
    # ─────────────────────────────────────────────────────────
    def force_initial_capture(self) -> None:
        """Force capture of initial values (manual trigger)."""
        frame = self.capture_now()
        if frame is not None:
            self._state_machine.force_initial_capture(frame)
            self.test_phase_changed.emit(self._state_machine.phase_name)

    def force_correction_capture(self) -> None:
        """Force capture of correction values (manual trigger)."""
        frame = self.capture_now()
        if frame is not None:
            self._state_machine.force_correction_capture(frame)
            if self._state_machine.phase == TestPhase.TEST_COMPLETE:
                self._emit_test_complete()

    # ─────────────────────────────────────────────────────────
    # Main Loop
    # ─────────────────────────────────────────────────────────
    def run(self) -> None:
        """Main monitoring loop — runs in background thread."""
        logger.info("Monitor thread started")

        with mss.mss() as sct:
            while True:
                with QMutexLocker(self._mutex):
                    if not self._running:
                        break
                    window_title = self._window_title
                    interval = self._capture_interval_ms
                    threshold = self._ssim_threshold
                    left_roi = self._left_box_roi
                    right_roi = self._right_box_roi

                try:
                    # Find the ABRO window
                    window_rect = self._find_target_window(window_title)

                    if window_rect is None:
                        if self._state != MonitoringState.WINDOW_LOST:
                            self._set_state(MonitoringState.WINDOW_LOST)
                            self.window_lost.emit()
                            logger.warning("ABRO window lost")
                        self.msleep(interval)
                        continue

                    # Window found — update state if needed
                    if self._state == MonitoringState.WINDOW_LOST:
                        self._set_state(MonitoringState.RUNNING)
                        self.window_found.emit(window_title)
                        logger.info("ABRO window refound")

                    # Capture the window region
                    frame = self._capture_region(sct, window_rect)
                    if frame is None:
                        self.msleep(interval)
                        continue

                    self._capture_count += 1
                    self.screen_captured.emit(frame)

                    # Check for screen stability (SSIM comparison)
                    is_stable = False
                    if self._previous_frame is not None:
                        ssim = self._compute_ssim(self._previous_frame, frame)
                        if ssim >= threshold:
                            self._consecutive_stable_frames += 1
                            is_stable = True
                        else:
                            self._consecutive_stable_frames = 0
                            self._change_count += 1
                            self.screen_changed.emit(frame)
                            logger.debug(
                                "Screen change detected (SSIM: %.4f, threshold: %.4f)",
                                ssim, threshold,
                            )
                    else:
                        # First frame always counts as a change
                        self.screen_changed.emit(frame)
                        self._change_count += 1

                    self._previous_frame = frame.copy()

                    # ── Color Detection & State Machine ──
                    color_state = ValueColorState.UNKNOWN
                    if left_roi and right_roi:
                        color_state, left_result, right_result = \
                            self._color_detector.detect_value_state(
                                frame, left_roi, right_roi
                            )

                        # Emit color state change
                        if color_state != self._last_color_state:
                            self._last_color_state = color_state
                            self.color_state_changed.emit(color_state.name)

                    # Feed frame to state machine
                    event = self._state_machine.process_frame(
                        frame, color_state, is_stable
                    )

                    # Handle state machine events
                    if event in (TestEvent.INITIAL_CAPTURED, TestEvent.PHASE_CHANGED):
                        self.test_phase_changed.emit(
                            self._state_machine.phase_name
                        )

                    if event == TestEvent.TEST_COMPLETE:
                        self.test_phase_changed.emit(
                            self._state_machine.phase_name
                        )
                        self._emit_test_complete()

                    # Emit stats periodically
                    if self._capture_count % 10 == 0:
                        self.stats_updated.emit({
                            "captures": self._capture_count,
                            "changes": self._change_count,
                            "state": self._state.name,
                            "test_phase": self._state_machine.phase.name,
                            "color_state": color_state.name,
                            "stable_frames": self._consecutive_stable_frames,
                        })

                except Exception as e:
                    logger.error("Monitor error: %s", e, exc_info=True)
                    self.error_occurred.emit(str(e))
                    self._set_state(MonitoringState.ERROR)

                self.msleep(interval)

        self._set_state(MonitoringState.IDLE)
        logger.info("Monitor thread stopped")

    def _emit_test_complete(self) -> None:
        """Emit the test_complete signal with test cycle data."""
        test_data = self._state_machine.get_completed_test()
        if test_data is not None:
            data = {
                "initial_frame": test_data.initial.frame if test_data.initial else None,
                "correction_frame": test_data.correction.frame if test_data.correction else None,
                "started_at": test_data.started_at,
                "completed_at": test_data.completed_at,
                "duration_sec": test_data.duration_sec,
            }
            self.test_complete.emit(data)
            logger.info(
                "Test complete emitted (duration: %.1fs)", test_data.duration_sec
            )
            # Reset for next test
            self._state_machine.reset()
            self.test_phase_changed.emit(self._state_machine.phase_name)

    # ─────────────────────────────────────────────────────────
    # Window Detection
    # ─────────────────────────────────────────────────────────
    def _find_target_window(self, title: str) -> Optional[Tuple[int, int, int, int]]:
        """Find the ABRO window and return its screen coordinates."""
        if not title:
            return None

        # If we have a cached HWND, try to use it first
        if self._hwnd:
            if WindowFinder.is_window_visible(self._hwnd):
                # Verify title still matches
                current_title = WindowFinder.get_window_title(self._hwnd)
                if title.lower() in current_title.lower():
                    return WindowFinder.get_window_rect(self._hwnd)
            # HWND is stale
            self._hwnd = 0

        # Search by title pattern
        win = self._window_finder.find_window_by_title(title)
        if win:
            self._hwnd = win.hwnd
            return win.rect
        return None

    # ─────────────────────────────────────────────────────────
    # Screen Capture
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _capture_region(
        sct: mss.mss, rect: Tuple[int, int, int, int]
    ) -> Optional[np.ndarray]:
        """
        Capture a specific screen region using mss.

        Args:
            sct: mss instance
            rect: (left, top, right, bottom) window coordinates

        Returns:
            BGR numpy array of the captured region
        """
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            return None

        monitor = {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }

        try:
            screenshot = sct.grab(monitor)
            # Convert BGRA to BGR
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            return frame
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────
    # Change Detection
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Compute structural similarity (simplified SSIM) between two frames.

        Uses a fast grayscale histogram + mean comparison approach
        for performance. Returns 0.0 (completely different) to 1.0 (identical).
        """
        # Resize to same dimensions if different
        if img1.shape != img2.shape:
            h = min(img1.shape[0], img2.shape[0])
            w = min(img1.shape[1], img2.shape[1])
            img1 = cv2.resize(img1, (w, h))
            img2 = cv2.resize(img2, (w, h))

        # Convert to grayscale for faster comparison
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Downscale for performance
        scale = 0.25
        small1 = cv2.resize(gray1, None, fx=scale, fy=scale)
        small2 = cv2.resize(gray2, None, fx=scale, fy=scale)

        # Compute normalized absolute difference
        diff = cv2.absdiff(small1, small2)
        mean_diff = np.mean(diff) / 255.0

        # Convert to similarity score
        similarity = 1.0 - mean_diff

        return similarity

    # ─────────────────────────────────────────────────────────
    # Manual Capture
    # ─────────────────────────────────────────────────────────
    def capture_now(self) -> Optional[np.ndarray]:
        """
        Perform a one-shot capture of the current ABRO window.

        Can be called from the UI thread for manual capture mode.
        Returns the captured frame or None if window is not found.
        """
        if not self._window_title:
            return None

        rect = self._find_target_window(self._window_title)
        if rect is None:
            return None

        with mss.mss() as sct:
            return self._capture_region(sct, rect)

