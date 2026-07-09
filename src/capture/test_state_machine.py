"""
BalanceLog Pro - Test State Machine

Tracks the lifecycle of one balancing test from initial measurement (RED text)
through machine running to after-correction measurement (GREEN text).

State transitions:
    WAITING_FOR_INITIAL  → INITIAL_CAPTURED     (BOTH_RED + stable screen)
    INITIAL_CAPTURED     → MACHINE_RUNNING      (screen starts changing)
    MACHINE_RUNNING      → MACHINE_RUNNING      (values fluctuating or MIXED)
    MACHINE_RUNNING      → WAITING_FOR_CORRECTION (screen becomes stable)
    WAITING_FOR_CORRECTION → TEST_COMPLETE       (BOTH_GREEN + stable screen)
    TEST_COMPLETE        → WAITING_FOR_INITIAL   (after record is saved)
"""

import time
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any

from src.detection.screen_types import TestPhase
from src.detection.color_detector import ValueColorState
from src.utils.logger import get_logger

logger = get_logger("capture")


class TestEvent(Enum):
    """Events emitted by the state machine."""
    NONE = auto()              # No significant event
    INITIAL_CAPTURED = auto()  # Initial RED values captured
    CORRECTION_CAPTURED = auto()  # Correction GREEN values captured
    TEST_COMPLETE = auto()     # Full test (initial + correction) ready to save
    PHASE_CHANGED = auto()     # State machine phase changed


@dataclass
class CapturedPhaseData:
    """Data from one phase of the test (initial or correction)."""
    frame: Optional[np.ndarray] = None
    color_state: ValueColorState = ValueColorState.UNKNOWN
    capture_time: float = 0.0
    screenshot_path: str = ""


@dataclass
class TestCycleData:
    """Complete data for one balancing test cycle."""
    initial: Optional[CapturedPhaseData] = None
    correction: Optional[CapturedPhaseData] = None
    rotor_info: Dict[str, Any] = field(default_factory=dict)
    started_at: float = 0.0
    completed_at: float = 0.0

    @property
    def is_complete(self) -> bool:
        """Check if both phases have been captured."""
        return self.initial is not None and self.correction is not None

    @property
    def duration_sec(self) -> float:
        """Time from initial capture to correction capture."""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return 0.0


class TestStateMachine:
    """
    Tracks one balancing test from initial RED values to correction GREEN values.

    Requires N consecutive stable frames before capturing to avoid
    grabbing values while the machine is still running.

    Usage:
        sm = TestStateMachine()
        for frame in frames:
            event = sm.process_frame(frame, color_state, is_stable)
            if event == TestEvent.TEST_COMPLETE:
                data = sm.get_completed_test()
                sm.reset()
    """

    # Number of consecutive stable frames required before capturing
    STABILITY_FRAMES_REQUIRED = 3

    # Maximum time (seconds) to wait for correction after initial capture
    # If exceeded, assume the operator has moved on and reset
    MAX_CORRECTION_WAIT_SEC = 600  # 10 minutes

    def __init__(self) -> None:
        self._phase = TestPhase.WAITING_FOR_INITIAL
        self._current_test = TestCycleData()
        self._stable_frame_count = 0
        self._last_stable_color_state = ValueColorState.UNKNOWN
        self._last_frame: Optional[np.ndarray] = None
        self._phase_entered_at = time.time()

    @property
    def phase(self) -> TestPhase:
        """Current test phase."""
        return self._phase

    @property
    def phase_name(self) -> str:
        """Human-readable phase name."""
        names = {
            TestPhase.WAITING_FOR_INITIAL: "Waiting for Initial Values",
            TestPhase.INITIAL_CAPTURED: "Initial Values Captured",
            TestPhase.MACHINE_RUNNING: "Machine Running",
            TestPhase.WAITING_FOR_CORRECTION: "Waiting for Correction Values",
            TestPhase.TEST_COMPLETE: "Test Complete",
        }
        return names.get(self._phase, "Unknown")

    def process_frame(
        self,
        frame: np.ndarray,
        color_state: ValueColorState,
        is_stable: bool,
    ) -> TestEvent:
        """
        Feed a captured frame to the state machine.

        Args:
            frame: BGR screenshot of the ABRO window
            color_state: Detected color state (BOTH_RED, BOTH_GREEN, MIXED, UNKNOWN)
            is_stable: True if the screen hasn't changed for several consecutive frames

        Returns:
            TestEvent indicating what happened (NONE, INITIAL_CAPTURED, etc.)
        """
        event = TestEvent.NONE
        previous_phase = self._phase

        # Track stability for the same color state
        if is_stable and color_state == self._last_stable_color_state:
            self._stable_frame_count += 1
        elif color_state != self._last_stable_color_state:
            self._stable_frame_count = 1 if is_stable else 0
            self._last_stable_color_state = color_state

        is_fully_stable = self._stable_frame_count >= self.STABILITY_FRAMES_REQUIRED

        # ── State Machine Transitions ──
        if self._phase == TestPhase.WAITING_FOR_INITIAL:
            if color_state == ValueColorState.BOTH_RED and is_fully_stable:
                # Capture initial values
                self._current_test.initial = CapturedPhaseData(
                    frame=frame.copy(),
                    color_state=color_state,
                    capture_time=time.time(),
                )
                self._current_test.started_at = time.time()
                self._set_phase(TestPhase.INITIAL_CAPTURED)
                event = TestEvent.INITIAL_CAPTURED
                logger.info("Initial RED values captured (stability: %d frames)",
                            self._stable_frame_count)

        elif self._phase == TestPhase.INITIAL_CAPTURED:
            # Wait for screen to start changing (machine running)
            if not is_stable:
                self._set_phase(TestPhase.MACHINE_RUNNING)
                event = TestEvent.PHASE_CHANGED
                logger.info("Machine started running — values changing")
            # Also transition if colors change to green immediately
            elif color_state == ValueColorState.BOTH_GREEN and is_fully_stable:
                self._current_test.correction = CapturedPhaseData(
                    frame=frame.copy(),
                    color_state=color_state,
                    capture_time=time.time(),
                )
                self._current_test.completed_at = time.time()
                self._set_phase(TestPhase.TEST_COMPLETE)
                event = TestEvent.TEST_COMPLETE
                logger.info("Correction GREEN values captured immediately")

        elif self._phase == TestPhase.MACHINE_RUNNING:
            # Check for timeout
            elapsed = time.time() - self._phase_entered_at
            if elapsed > self.MAX_CORRECTION_WAIT_SEC:
                logger.warning(
                    "Correction wait timeout (%.0fs) — resetting test",
                    elapsed,
                )
                self.reset()
                return TestEvent.PHASE_CHANGED

            if is_stable:
                # Screen has stabilized — move to waiting for correction
                self._set_phase(TestPhase.WAITING_FOR_CORRECTION)
                event = TestEvent.PHASE_CHANGED
                logger.info("Machine stopped — screen stable, checking colors")
                # Fall through to check color immediately
                return self._check_correction(frame, color_state, is_fully_stable,
                                              previous_phase)

        elif self._phase == TestPhase.WAITING_FOR_CORRECTION:
            event = self._check_correction(frame, color_state, is_fully_stable,
                                           previous_phase)
            # If screen starts changing again, go back to MACHINE_RUNNING
            if not is_stable and color_state != ValueColorState.BOTH_GREEN:
                self._set_phase(TestPhase.MACHINE_RUNNING)
                event = TestEvent.PHASE_CHANGED
                logger.info("Screen changing again — back to machine running")

        elif self._phase == TestPhase.TEST_COMPLETE:
            # Waiting for external code to call get_completed_test() + reset()
            pass

        # Log phase change
        if self._phase != previous_phase and event == TestEvent.NONE:
            event = TestEvent.PHASE_CHANGED

        self._last_frame = frame

        return event

    def _check_correction(
        self,
        frame: np.ndarray,
        color_state: ValueColorState,
        is_fully_stable: bool,
        previous_phase: TestPhase,
    ) -> TestEvent:
        """Check if correction values (BOTH GREEN) are available."""
        if color_state == ValueColorState.BOTH_GREEN and is_fully_stable:
            self._current_test.correction = CapturedPhaseData(
                frame=frame.copy(),
                color_state=color_state,
                capture_time=time.time(),
            )
            self._current_test.completed_at = time.time()
            self._set_phase(TestPhase.TEST_COMPLETE)
            logger.info(
                "Correction GREEN values captured (test duration: %.1fs)",
                self._current_test.duration_sec,
            )
            return TestEvent.TEST_COMPLETE

        if color_state == ValueColorState.MIXED:
            logger.debug("Only one side green — waiting for both sides")

        return TestEvent.NONE

    def _set_phase(self, phase: TestPhase) -> None:
        """Update the current phase and record entry time."""
        logger.info("Test phase: %s → %s", self._phase.name, phase.name)
        self._phase = phase
        self._phase_entered_at = time.time()
        self._stable_frame_count = 0

    def get_completed_test(self) -> Optional[TestCycleData]:
        """
        Get the completed test data.

        Returns None if the test is not yet complete.
        Call reset() after retrieving to prepare for the next test.
        """
        if self._phase == TestPhase.TEST_COMPLETE and self._current_test.is_complete:
            return self._current_test
        return None

    def get_initial_frame(self) -> Optional[np.ndarray]:
        """Get the initial phase frame (if captured)."""
        if self._current_test.initial:
            return self._current_test.initial.frame
        return None

    def reset(self) -> None:
        """Reset the state machine for a new test cycle."""
        logger.info("State machine reset — ready for next test")
        self._phase = TestPhase.WAITING_FOR_INITIAL
        self._current_test = TestCycleData()
        self._stable_frame_count = 0
        self._last_stable_color_state = ValueColorState.UNKNOWN
        self._last_frame = None
        self._phase_entered_at = time.time()

    def force_initial_capture(self, frame: np.ndarray) -> None:
        """
        Force capture of initial values (manual trigger).

        Used when the operator manually triggers initial value capture
        regardless of color detection state.
        """
        self._current_test.initial = CapturedPhaseData(
            frame=frame.copy(),
            color_state=ValueColorState.BOTH_RED,
            capture_time=time.time(),
        )
        self._current_test.started_at = time.time()
        self._set_phase(TestPhase.INITIAL_CAPTURED)
        logger.info("Initial values force-captured (manual trigger)")

    def force_correction_capture(self, frame: np.ndarray) -> None:
        """
        Force capture of correction values (manual trigger).

        Used when the operator manually triggers correction value capture
        regardless of color detection state.
        """
        if self._current_test.initial is None:
            logger.warning("Cannot capture correction — no initial values captured yet")
            return

        self._current_test.correction = CapturedPhaseData(
            frame=frame.copy(),
            color_state=ValueColorState.BOTH_GREEN,
            capture_time=time.time(),
        )
        self._current_test.completed_at = time.time()
        self._set_phase(TestPhase.TEST_COMPLETE)
        logger.info("Correction values force-captured (manual trigger)")
