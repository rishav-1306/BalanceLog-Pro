"""
BalanceLog Pro - Dashboard Page

Main dashboard displaying real-time monitoring status, production stats,
and quick-action buttons. Industrial dark-themed with status cards.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap

from src.config.constants import Colors, Fonts, MonitoringState
from src.ui.widgets import StatusCard, MonitoringIndicator, ImageViewer, SectionHeader


class DashboardPage(QWidget):
    """
    Industrial dashboard with status cards, action buttons,
    and a live preview thumbnail of the last captured screenshot.

    Status Cards:
    - Monitoring Status (green/red indicator)
    - Today's Production count
    - Today's Screenshots
    - OCR Accuracy
    - Database Status
    - Storage Used

    Action Buttons:
    - Start / Stop Monitoring
    - Manual Capture
    - Quick Export
    """

    # Signals for main window to handle
    start_monitoring_clicked = Signal()
    stop_monitoring_clicked = Signal()
    manual_capture_clicked = Signal()
    quick_export_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._monitoring_state = MonitoringState.IDLE

        # Auto-refresh dashboard every 5 seconds
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._update_time)
        self._refresh_timer.start(1000)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # ── Header ──
        header = SectionHeader(
            "Dashboard",
            "Real-time monitoring and production overview"
        )
        layout.addWidget(header)

        # ── Status Cards Row ──
        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        self._card_monitoring = StatusCard(
            "MONITORING STATUS", "IDLE", "Not running",
            accent_color=Colors.TEXT_DISABLED,
        )
        cards_layout.addWidget(self._card_monitoring, 0, 0)

        self._card_production = StatusCard(
            "TODAY'S PRODUCTION", "0", "Shafts balanced",
            accent_color=Colors.PRIMARY,
        )
        cards_layout.addWidget(self._card_production, 0, 1)

        self._card_screenshots = StatusCard(
            "SCREENSHOTS", "0", "Captured today",
            accent_color=Colors.INFO,
        )
        cards_layout.addWidget(self._card_screenshots, 0, 2)

        self._card_accuracy = StatusCard(
            "OCR ACCURACY", "—", "Average confidence",
            accent_color=Colors.SUCCESS,
        )
        cards_layout.addWidget(self._card_accuracy, 1, 0)

        self._card_database = StatusCard(
            "DATABASE", "OK", "Total records: 0",
            accent_color=Colors.SUCCESS,
        )
        cards_layout.addWidget(self._card_database, 1, 1)

        self._card_storage = StatusCard(
            "STORAGE", "—", "Space used",
            accent_color=Colors.WARNING,
        )
        cards_layout.addWidget(self._card_storage, 1, 2)

        layout.addLayout(cards_layout)

        # ── Action Buttons + Preview Row ──
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        # Action buttons panel
        actions_frame = QFrame()
        actions_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(20, 20, 20, 20)
        actions_layout.setSpacing(12)

        actions_title = QLabel("Quick Actions")
        actions_title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LARGE, QFont.Weight.Bold))
        actions_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        actions_layout.addWidget(actions_title)

        # Monitoring indicator + label
        monitor_row = QHBoxLayout()
        self._monitor_indicator = MonitoringIndicator()
        monitor_row.addWidget(self._monitor_indicator)
        self._monitor_label = QLabel("Monitoring: Idle")
        self._monitor_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        monitor_row.addWidget(self._monitor_label)
        monitor_row.addStretch()
        actions_layout.addLayout(monitor_row)

        # Start button
        self._btn_start = QPushButton("▶  Start Monitoring")
        self._btn_start.setObjectName("btnSuccess")
        self._btn_start.setMinimumHeight(44)
        self._btn_start.clicked.connect(self.start_monitoring_clicked.emit)
        actions_layout.addWidget(self._btn_start)

        # Stop button
        self._btn_stop = QPushButton("■  Stop Monitoring")
        self._btn_stop.setObjectName("btnDanger")
        self._btn_stop.setMinimumHeight(44)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self.stop_monitoring_clicked.emit)
        actions_layout.addWidget(self._btn_stop)

        # Manual capture button
        self._btn_capture = QPushButton("Manual Capture")
        self._btn_capture.setMinimumHeight(44)
        self._btn_capture.clicked.connect(self.manual_capture_clicked.emit)
        actions_layout.addWidget(self._btn_capture)

        # Quick export button
        self._btn_export = QPushButton("Export Today's Records")
        self._btn_export.setObjectName("btnOutline")
        self._btn_export.setMinimumHeight(44)
        self._btn_export.clicked.connect(self.quick_export_clicked.emit)
        actions_layout.addWidget(self._btn_export)

        actions_layout.addStretch()

        # Current time display
        self._time_label = QLabel()
        self._time_label.setFont(QFont(Fonts.FAMILY_MONO, Fonts.SIZE_XLARGE, QFont.Weight.Bold))
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_label.setStyleSheet(f"color: {Colors.PRIMARY}; background: transparent;")
        self._update_time()
        actions_layout.addWidget(self._time_label)

        bottom_layout.addWidget(actions_frame, 1)

        # Preview panel
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(20, 20, 20, 20)

        preview_title = QLabel("Last Capture Preview")
        preview_title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LARGE, QFont.Weight.Bold))
        preview_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        preview_layout.addWidget(preview_title)

        self._preview_viewer = ImageViewer()
        self._preview_viewer.setMinimumHeight(250)
        preview_layout.addWidget(self._preview_viewer)

        self._preview_info = QLabel("No captures yet")
        self._preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        preview_layout.addWidget(self._preview_info)

        bottom_layout.addWidget(preview_frame, 2)

        layout.addLayout(bottom_layout)

    # ─────────────────────────────────────────────────────────
    # Update Methods
    # ─────────────────────────────────────────────────────────
    def update_monitoring_state(self, state: MonitoringState) -> None:
        """Update dashboard to reflect monitoring state."""
        self._monitoring_state = state

        if state == MonitoringState.RUNNING:
            self._card_monitoring.set_value("ACTIVE")
            self._card_monitoring.set_subtitle("Monitoring ABRO window")
            self._card_monitoring.set_accent_color(Colors.SUCCESS)
            self._monitor_indicator.set_active()
            self._monitor_label.setText("Monitoring: Active")
            self._btn_start.setEnabled(False)
            self._btn_stop.setEnabled(True)
        elif state == MonitoringState.WINDOW_LOST:
            self._card_monitoring.set_value("WARNING")
            self._card_monitoring.set_subtitle("ABRO window not found")
            self._card_monitoring.set_accent_color(Colors.WARNING)
            self._monitor_indicator.set_warning()
            self._monitor_label.setText("Monitoring: Window Lost")
        elif state == MonitoringState.ERROR:
            self._card_monitoring.set_value("ERROR")
            self._card_monitoring.set_subtitle("Monitor error occurred")
            self._card_monitoring.set_accent_color(Colors.ERROR)
            self._monitor_indicator.set_stopped()
            self._monitor_label.setText("Monitoring: Error")
        else:
            self._card_monitoring.set_value("IDLE")
            self._card_monitoring.set_subtitle("Not running")
            self._card_monitoring.set_accent_color(Colors.TEXT_DISABLED)
            self._monitor_indicator.set_idle()
            self._monitor_label.setText("Monitoring: Idle")
            self._btn_start.setEnabled(True)
            self._btn_stop.setEnabled(False)

    def update_production_count(self, count: int) -> None:
        self._card_production.set_value(str(count))

    def update_screenshot_count(self, count: int) -> None:
        self._card_screenshots.set_value(str(count))

    def update_accuracy(self, accuracy: float) -> None:
        self._card_accuracy.set_value(f"{accuracy:.1%}")

    def update_database_status(self, status: str, total: int) -> None:
        self._card_database.set_value(status)
        self._card_database.set_subtitle(f"Total records: {total}")

    def update_storage(self, used: str) -> None:
        self._card_storage.set_value(used)

    def update_preview(self, pixmap: QPixmap, info: str = "") -> None:
        """Update the screenshot preview."""
        self._preview_viewer.load_pixmap(pixmap)
        self._preview_info.setText(info or datetime.now().strftime("%H:%M:%S"))

    def _update_time(self) -> None:
        """Update the time display."""
        self._time_label.setText(datetime.now().strftime("%H:%M:%S"))
