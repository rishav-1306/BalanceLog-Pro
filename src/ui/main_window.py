"""
BalanceLog Pro - Main Window

Central orchestrator connecting all UI pages, services, and controllers.
Implements sidebar navigation, signal wiring, and the monitoring pipeline.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QStatusBar, QFrame, QMessageBox,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QPixmap, QIcon, QGuiApplication

from src.config.config_manager import ConfigManager
from src.config.constants import (
    APP_NAME, APP_VERSION, Colors, Fonts, MonitoringState,
)
from src.database.db_manager import DatabaseManager
from src.database.models import BalancingRecord, SearchFilter
from src.capture.screen_monitor import ScreenMonitor
from src.detection.result_detector import ResultDetector
from src.ocr.ocr_engine import OCREngine
from src.validation.validation_engine import ValidationEngine
from src.excel.excel_exporter import ExcelExporter
from src.reports.report_generator import ReportGenerator
from src.utils.logger import setup_logging, get_logger
from src.utils.file_manager import FileManager
from src.utils.helpers import get_date_str, get_time_str, get_time_filename

from src.ui.theme import get_dark_theme, get_light_theme, get_sidebar_style
from src.ui.dashboard_page import DashboardPage
from src.ui.records_page import RecordsPage
from src.ui.search_page import SearchPage
from src.ui.calibration_page import CalibrationPage
from src.ui.settings_page import SettingsPage
from src.ui.reports_page import ReportsPage
from src.ui.logs_page import LogsPage
from src.ui.record_detail_dialog import RecordDetailDialog
from src.ui.confirmation_dialog import ConfirmationDialog

logger = get_logger("ui.main")


class MainWindow(QMainWindow):
    """
    Main application window with sidebar navigation and stacked pages.
    """

    PAGE_DASHBOARD = 0
    PAGE_RECORDS = 1
    PAGE_SEARCH = 2
    PAGE_REPORTS = 3
    PAGE_CALIBRATION = 4
    PAGE_SETTINGS = 5
    PAGE_LOGS = 6

    def __init__(self) -> None:
        super().__init__()
        self._config = ConfigManager()
        self._db = DatabaseManager()
        self._file_manager = FileManager(self._config.get_base_dir())
        self._result_detector = ResultDetector()
        self._ocr = OCREngine()
        self._validator = ValidationEngine()
        self._excel = ExcelExporter()
        self._report_gen = ReportGenerator(self._db)

        # Setup logging
        setup_logging(self._file_manager.get_logs_dir())

        # Database
        db_path = self._config.get_database_path()
        self._db.set_path(db_path)
        self._db.init_db()

        # Screen monitor thread
        self._monitor = ScreenMonitor()

        # Connect monitor signals
        self._monitor.screen_changed.connect(self._on_screen_changed)
        self._monitor.monitoring_state_changed.connect(self._on_monitoring_state)
        self._monitor.window_lost.connect(self._on_window_lost)
        self._monitor.window_found.connect(self._on_window_found)
        self._monitor.error_occurred.connect(self._on_monitor_error)
        self._monitor.test_phase_changed.connect(self._on_test_phase_changed)
        self._monitor.test_complete.connect(self._on_test_complete)
        self._monitor.color_state_changed.connect(self._on_color_state_changed)

        # ── Setup UI ──
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(900, 550)

        # Dynamic initial sizing based on monitor available geometry
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1360, max(900, int(avail.width() * 0.85)))
            target_h = min(850, max(550, int(avail.height() * 0.85)))
            self.resize(target_w, target_h)
        else:
            self.resize(1280, 720)

        self._setup_ui()
        self._connect_signals()
        self._refresh_dashboard()

        # Dashboard refresh timer
        self._dash_timer = QTimer(self)
        self._dash_timer.timeout.connect(self._refresh_dashboard)
        self._dash_timer.start(5000)

        logger.info("MainWindow initialized")

    def _setup_ui(self) -> None:
        """Build the main window layout with sidebar + stacked pages."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        sidebar.setStyleSheet(get_sidebar_style())
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        # App branding
        brand_label = QLabel("BalanceLog")
        brand_label.setObjectName("sidebar-title")
        sidebar_layout.addWidget(brand_label)

        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setObjectName("sidebar-version")
        sidebar_layout.addWidget(version_label)

        sidebar_layout.addSpacing(20)

        # Navigation buttons
        nav_items = [
            ("Dashboard", self.PAGE_DASHBOARD),
            ("Records", self.PAGE_RECORDS),
            ("Search", self.PAGE_SEARCH),
            ("Reports", self.PAGE_REPORTS),
            ("Calibration", self.PAGE_CALIBRATION),
            ("Settings", self.PAGE_SETTINGS),
            ("Logs", self.PAGE_LOGS),
        ]

        self._nav_buttons = []
        for text, page_idx in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("class", "nav-btn")
            btn.setMinimumHeight(42)
            btn.clicked.connect(lambda checked, idx=page_idx: self._switch_page(idx))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Sidebar footer
        footer = QLabel(f"© 2026 {APP_NAME}")
        footer.setObjectName("sidebar-version")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(footer)

        main_layout.addWidget(sidebar)

        # ── Stacked Pages ──
        self._stack = QStackedWidget()

        self._dashboard = DashboardPage()
        self._stack.addWidget(self._dashboard)

        self._records_page = RecordsPage()
        self._stack.addWidget(self._records_page)

        self._search_page = SearchPage()
        self._stack.addWidget(self._search_page)

        self._reports_page = ReportsPage()
        self._stack.addWidget(self._reports_page)

        self._calibration_page = CalibrationPage()
        self._stack.addWidget(self._calibration_page)

        self._settings_page = SettingsPage()
        self._stack.addWidget(self._settings_page)

        self._logs_page = LogsPage(self._file_manager.get_logs_dir())
        self._stack.addWidget(self._logs_page)

        main_layout.addWidget(self._stack, 1)

        # Select dashboard by default
        self._switch_page(self.PAGE_DASHBOARD)

        # ── Status Bar ──
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self._status_monitoring = QLabel("Monitoring: Idle")
        self._status_db = QLabel(f"DB: {self._config.get_database_path().name}")
        self._status_time = QLabel("")
        status_bar.addWidget(self._status_monitoring, 1)
        status_bar.addPermanentWidget(self._status_db)
        status_bar.addPermanentWidget(self._status_time)

        # Update status bar time
        timer = QTimer(self)
        timer.timeout.connect(
            lambda: self._status_time.setText(datetime.now().strftime("%H:%M:%S"))
        )
        timer.start(1000)

    def _connect_signals(self) -> None:
        """Wire up all page signals to controller methods."""
        # Dashboard
        self._dashboard.start_monitoring_clicked.connect(self._start_monitoring)
        self._dashboard.stop_monitoring_clicked.connect(self._stop_monitoring)
        self._dashboard.manual_capture_clicked.connect(self._manual_capture)
        self._dashboard.quick_export_clicked.connect(self._quick_export_today)

        # Records
        self._records_page.view_record.connect(self._show_record_detail)
        self._records_page.view_screenshot.connect(self._open_screenshot)
        self._records_page.delete_record.connect(self._delete_record)
        self._records_page.export_records.connect(self._export_records)
        self._records_page.record_updated.connect(self._update_record)

        # Search
        self._search_page.search_requested.connect(self._perform_search)
        self._search_page.view_record.connect(self._show_record_detail)

        # Reports
        self._reports_page.generate_report.connect(self._generate_report)
        self._reports_page.export_report.connect(self._export_report)

        # Settings
        self._settings_page.settings_changed.connect(self._on_settings_changed)
        self._settings_page.theme_changed.connect(self._apply_theme)

        # Calibration
        self._calibration_page.calibration_saved.connect(self._on_calibration_saved)

    # ─────────────────────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────────────────────
    def _switch_page(self, index: int) -> None:
        """Switch to a page and update sidebar selection."""
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

        # Refresh data when switching to certain pages
        if index == self.PAGE_RECORDS:
            self._load_records()
        elif index == self.PAGE_DASHBOARD:
            self._refresh_dashboard()

    # ─────────────────────────────────────────────────────────
    # Monitoring Pipeline
    # ─────────────────────────────────────────────────────────
    def _start_monitoring(self) -> None:
        """Start the screen monitoring thread."""
        window_title = self._config.get("monitoring.abro_window_title", "")
        if not window_title:
            QMessageBox.warning(
                self, "No Window Selected",
                "Please configure the ABRO window title in Settings first.",
            )
            self._switch_page(self.PAGE_SETTINGS)
            return

        self._monitor.set_window_title(window_title)
        self._monitor.set_capture_interval(
            self._config.get("monitoring.capture_interval_ms", 2000)
        )

        # Configure color detection ROIs from calibration
        rois = self._config.get_all_rois()
        left_box = rois.get("left_value_box")
        right_box = rois.get("right_value_box")
        if left_box and right_box:
            self._monitor.set_color_rois(left_box, right_box)
            logger.info("Color detection: ROI-based mode (calibrated)")
        else:
            # Clear ROIs so monitor uses whole-frame detection
            self._monitor.set_color_rois(None, None)
            logger.info("Color detection: whole-frame mode (no calibration)")

        self._monitor.start_monitoring()
        self._status_monitoring.setText(f"Monitoring: Active — '{window_title}'")
        logger.info("Monitoring started for '%s'", window_title)

    def _stop_monitoring(self) -> None:
        """Stop the screen monitoring thread."""
        self._monitor.stop_monitoring()
        self._status_monitoring.setText("Monitoring: Stopped")
        # Explicitly update dashboard to IDLE so buttons always reset
        self._dashboard.update_monitoring_state(MonitoringState.IDLE)
        logger.info("Monitoring stopped")

    @Slot(np.ndarray)
    def _on_screen_changed(self, frame: np.ndarray) -> None:
        """Handle a screen change — update preview. State machine handles OCR pipeline."""
        from src.utils.helpers import numpy_to_pixmap
        pixmap = numpy_to_pixmap(frame)
        phase = self._monitor.test_phase_name
        self._dashboard.update_preview(pixmap, f"Screen change | Phase: {phase}")

    def _manual_capture(self) -> None:
        """Manually capture and process the current screen."""
        window_title = self._config.get("monitoring.abro_window_title", "")
        if not window_title:
            QMessageBox.warning(
                self, "No Window Configured",
                "Set the ABRO window title in Settings first.",
            )
            return

        self._monitor.set_window_title(window_title)
        frame = self._monitor.capture_now()

        if frame is None:
            QMessageBox.warning(
                self, "Capture Failed",
                "Could not capture the ABRO window. Is it visible?",
            )
            return

        # In manual mode, process as a single-frame capture
        self._process_result_frame(frame)

    def _process_result_frame(self, frame: np.ndarray) -> None:
        """
        Process a single manually-captured frame.

        For manual captures, we create a simple record without the two-phase
        state machine workflow. The operator can manually trigger initial
        and correction captures using the force_initial/force_correction buttons.
        """
        date_str = get_date_str()
        time_str = get_time_str()

        ss_path = self._file_manager.save_screenshot_path(date_str, get_time_filename())
        cv2.imwrite(str(ss_path), frame)

        record = BalancingRecord.create_new()
        record.screenshot_path = str(ss_path)

        # Always run OCR (engine handles calibrated vs full-frame mode internally)
        if self._ocr_engine is None:
            self._ocr_engine = OCREngine()

        extraction = self._ocr_engine.extract_all_fields(frame)
        for field_name, field_result in extraction.fields.items():
            if field_result.parsed_value is not None:
                if field_name == "rotor_no":
                    record.rotor_no = str(field_result.parsed_value)
                    record.punching_number = str(field_result.parsed_value)
                elif field_name == "actual_rpm":
                    record.actual_rpm = float(field_result.parsed_value or 0)
        record.ocr_confidence = extraction.overall_confidence

        # Apply manual punching number if entered (overrides OCR)
        manual_punching = self._dashboard.get_manual_punching_no()
        if manual_punching:
            record.rotor_no = manual_punching
            record.punching_number = manual_punching

        self._save_record(record, date_str)

        from src.utils.helpers import numpy_to_pixmap
        pixmap = numpy_to_pixmap(frame)
        self._dashboard.update_preview(pixmap, f"Manual capture at {time_str}")

    @Slot(str)
    def _on_test_phase_changed(self, phase_name: str) -> None:
        """Handle test phase changes from the state machine."""
        self._dashboard.update_test_phase(phase_name)
        self._status_monitoring.setText(f"Test Phase: {phase_name}")
        logger.info("Test phase: %s", phase_name)

    @Slot(str)
    def _on_color_state_changed(self, color_state: str) -> None:
        """Handle color state changes (BOTH_RED, BOTH_GREEN, etc.)."""
        self._dashboard.update_color_state(color_state)
        logger.debug("Color state: %s", color_state)

    @Slot(dict)
    def _on_test_complete(self, test_data: dict) -> None:
        """
        Handle a completed test — both initial and correction captured.

        Runs OCR on both frames and combines into a single BalancingRecord.
        """
        initial_frame = test_data.get("initial_frame")
        correction_frame = test_data.get("correction_frame")

        if initial_frame is None or correction_frame is None:
            logger.error("Test complete but frames are missing")
            return

        date_str = get_date_str()
        time_str = get_time_str()

        # Save both screenshots
        initial_ss = self._file_manager.save_screenshot_path(
            date_str, f"{get_time_filename()}_initial"
        )
        correction_ss = self._file_manager.save_screenshot_path(
            date_str, f"{get_time_filename()}_correction"
        )
        cv2.imwrite(str(initial_ss), initial_frame)
        cv2.imwrite(str(correction_ss), correction_frame)
        logger.info("Screenshots saved: initial=%s, correction=%s", initial_ss, correction_ss)

        # Create record
        record = BalancingRecord.create_new()
        record.initial_screenshot_path = str(initial_ss)
        record.correction_screenshot_path = str(correction_ss)
        record.screenshot_path = str(correction_ss)  # Legacy: use correction as primary

        # Always run OCR on both frames (engine handles calibrated vs full-frame internally)
        if self._ocr_engine is None:
            self._ocr_engine = OCREngine()

        # OCR initial frame → populate initial fields
        initial_extraction = self._ocr_engine.extract_all_fields(initial_frame)
        for field_name, field_result in initial_extraction.fields.items():
            if field_result.parsed_value is not None:
                # Map OCR fields to initial record fields
                if field_name == "rotor_no":
                    record.rotor_no = str(field_result.parsed_value)
                    record.punching_number = str(field_result.parsed_value)
                elif field_name == "actual_rpm":
                    record.actual_rpm = float(field_result.parsed_value or 0)
                elif field_name == "left_value":
                    record.initial_left_value = float(field_result.parsed_value or 0)
                elif field_name == "left_angle":
                    record.initial_left_angle = float(field_result.parsed_value or 0)
                elif field_name == "right_value":
                    record.initial_right_value = float(field_result.parsed_value or 0)
                elif field_name == "right_angle":
                    record.initial_right_angle = float(field_result.parsed_value or 0)

        # OCR correction frame → populate after-correction fields
        correction_extraction = self._ocr_engine.extract_all_fields(correction_frame)
        for field_name, field_result in correction_extraction.fields.items():
            if field_result.parsed_value is not None:
                if field_name == "left_value":
                    record.after_correction_left = float(field_result.parsed_value or 0)
                elif field_name == "left_angle":
                    record.after_correction_left_angle = float(field_result.parsed_value or 0)
                elif field_name == "right_value":
                    record.after_correction_right = float(field_result.parsed_value or 0)
                elif field_name == "right_angle":
                    record.after_correction_right_angle = float(field_result.parsed_value or 0)

        # Average confidence from both extractions
        avg_conf = (
            initial_extraction.overall_confidence +
            correction_extraction.overall_confidence
        ) / 2.0
        record.ocr_confidence = avg_conf

        # Apply manual punching number if entered (overrides OCR)
        manual_punching = self._dashboard.get_manual_punching_no()
        if manual_punching:
            record.rotor_no = manual_punching
            record.punching_number = manual_punching

        # Validate and show confirmation if needed
        validation = self._validator.validate(record, avg_conf)
        needs_review = (
            validation.needs_confirmation or
            initial_extraction.needs_review or
            correction_extraction.needs_review
        )

        if needs_review:
            dialog = ConfirmationDialog(record, initial_extraction, self)
            dialog.confirmed.connect(lambda r: self._save_record(r, date_str))
            dialog.rejected.connect(lambda: logger.info("Record rejected by operator"))
            dialog.exec()
            return

        # Save record
        self._save_record(record, date_str)

        # Update preview with correction frame
        from src.utils.helpers import numpy_to_pixmap
        pixmap = numpy_to_pixmap(correction_frame)
        self._dashboard.update_preview(
            pixmap,
            f"Test complete at {time_str} | "
            f"Initial: L={record.initial_left_value}g R={record.initial_right_value}g | "
            f"Corrected: L={record.after_correction_left}g R={record.after_correction_right}g"
        )

    def _save_record(self, record: BalancingRecord, date_str: str) -> None:
        """Save record to database and optionally export to Excel."""
        # Check for duplicates
        if record.punching_number and self._db.check_duplicate(
            record.punching_number, record.date, record.time
        ):
            logger.warning("Duplicate record detected — skipping")
            return

        # Save to database
        record_id = self._db.insert_record(record)
        logger.info("Record saved: ID=%d, Punching=%s", record_id, record.punching_number)

        # Auto-export to Excel
        if self._config.get("excel.auto_export", True):
            try:
                records = self._db.get_records_by_date(date_str)
                excel_path = self._file_manager.get_excel_path(date_str)
                self._excel.export_daily(date_str, records, excel_path)
            except Exception as e:
                logger.error("Auto Excel export failed: %s", e)

        # Refresh dashboard
        self._refresh_dashboard()

    # ─────────────────────────────────────────────────────────
    # Monitor Signal Handlers
    # ─────────────────────────────────────────────────────────
    @Slot(str)
    def _on_monitoring_state(self, state_name: str) -> None:
        try:
            state = MonitoringState[state_name]
        except KeyError:
            state = MonitoringState.IDLE
        self._dashboard.update_monitoring_state(state)
        self._status_monitoring.setText(f"Monitoring: {state_name}")

    @Slot()
    def _on_window_lost(self) -> None:
        self._dashboard.update_monitoring_state(MonitoringState.WINDOW_LOST)

    @Slot(str)
    def _on_window_found(self, title: str) -> None:
        self._dashboard.update_monitoring_state(MonitoringState.RUNNING)

    @Slot(str)
    def _on_monitor_error(self, error: str) -> None:
        logger.error("Monitor error: %s", error)
        self._dashboard.update_monitoring_state(MonitoringState.ERROR)

    # ─────────────────────────────────────────────────────────
    # Dashboard Refresh
    # ─────────────────────────────────────────────────────────
    def _refresh_dashboard(self) -> None:
        """Update all dashboard status cards."""
        today = get_date_str()

        # Production count
        summary = self._db.get_daily_summary(today)
        self._dashboard.update_production_count(summary.total_shafts)

        # Screenshot count
        ss_count = self._file_manager.get_today_screenshot_count()
        self._dashboard.update_screenshot_count(ss_count)

        # OCR accuracy
        if summary.avg_ocr_confidence > 0:
            self._dashboard.update_accuracy(summary.avg_ocr_confidence)

        # Database status
        total = self._db.count_records()
        self._dashboard.update_database_status("OK", total)

        # Storage
        storage = self._file_manager.get_storage_info()
        self._dashboard.update_storage(storage["records_size_human"])

    # ─────────────────────────────────────────────────────────
    # Records
    # ─────────────────────────────────────────────────────────
    def _load_records(self) -> None:
        """Load records for the records page based on date filter."""
        date_from, date_to = self._records_page.get_date_range()
        filters = SearchFilter(date_from=date_from, date_to=date_to)
        records = self._db.search_records(filters)
        self._records_page.load_records(records)

    def _show_record_detail(self, record_id: int) -> None:
        """Show the record detail dialog."""
        record = self._db.get_record(record_id)
        if record:
            dialog = RecordDetailDialog(record, self)
            dialog.record_updated.connect(self._update_record)
            dialog.exec()

    def _update_record(self, record: BalancingRecord) -> None:
        """Save updated record to database."""
        self._db.update_record(record)
        self._load_records()

    def _delete_record(self, record_id: int) -> None:
        """Delete a record from the database."""
        self._db.delete_record(record_id)
        self._load_records()

    def _open_screenshot(self, path: str) -> None:
        """Open a screenshot in the system default viewer."""
        if Path(path).exists():
            os.startfile(path)

    def _export_records(self, records: list) -> None:
        """Export a list of records to Excel."""
        if not records:
            return
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Records", "records_export.xlsx",
            "Excel Files (*.xlsx)",
        )
        if path:
            self._excel.export_records(records, Path(path))
            QMessageBox.information(self, "Export Complete",
                                    f"Exported {len(records)} records.")

    # ─────────────────────────────────────────────────────────
    # Search
    # ─────────────────────────────────────────────────────────
    @Slot(SearchFilter)
    def _perform_search(self, filters: SearchFilter) -> None:
        """Execute search and display results."""
        results = self._db.search_records(filters)
        self._search_page.display_results(results)

    # ─────────────────────────────────────────────────────────
    # Reports
    # ─────────────────────────────────────────────────────────
    @Slot(str, str)
    def _generate_report(self, period: str, date_str: str) -> None:
        """Generate and display a report."""
        try:
            if period == "Daily":
                report = self._report_gen.generate_daily(date_str)
            elif period == "Weekly":
                report = self._report_gen.generate_weekly(date_str)
            elif period == "Monthly":
                parts = date_str.split("-")
                report = self._report_gen.generate_monthly(int(parts[0]), int(parts[1]))
            else:
                return
            self._reports_page.display_report(report)
        except Exception as e:
            logger.error("Report generation failed: %s", e)
            QMessageBox.critical(self, "Report Error", str(e))

    @Slot(str, str)
    def _export_report(self, fmt: str, output_path: str) -> None:
        """Export the current report."""
        report = self._reports_page._current_report
        if not report:
            return

        path = Path(output_path)
        try:
            if fmt == "xlsx":
                self._report_gen.export_to_excel(report, path)
            elif fmt == "csv":
                self._report_gen.export_to_csv(report, path)
            elif fmt == "pdf":
                self._report_gen.export_to_pdf(report, path)
            QMessageBox.information(self, "Export Complete",
                                    f"Report exported to {path.name}")
        except Exception as e:
            logger.error("Report export failed: %s", e)
            QMessageBox.critical(self, "Export Error", str(e))

    # ─────────────────────────────────────────────────────────
    # Quick Export
    # ─────────────────────────────────────────────────────────
    def _quick_export_today(self) -> None:
        """Export today's records to Excel."""
        today = get_date_str()
        records = self._db.get_records_by_date(today)
        if not records:
            QMessageBox.information(self, "No Records",
                                    "No records found for today.")
            return
        excel_path = self._file_manager.get_excel_path(today)
        self._excel.export_daily(today, records, excel_path)
        QMessageBox.information(
            self, "Export Complete",
            f"Exported {len(records)} records to:\n{excel_path}",
        )

    # ─────────────────────────────────────────────────────────
    # Settings / Theme
    # ─────────────────────────────────────────────────────────
    def _on_settings_changed(self) -> None:
        """Reload services after settings change."""
        # Update monitor
        self._monitor.set_capture_interval(
            self._config.get("monitoring.capture_interval_ms", 2000)
        )
        self._monitor.set_ssim_threshold(
            self._config.get("monitoring.ssim_threshold", 0.95)
        )
        # Update validator
        self._validator = ValidationEngine(
            self._config.get("ocr.confidence_threshold", 0.75)
        )
        # Reset OCR engine to pick up new settings
        self._ocr_engine = None
        # Update logs page
        self._logs_page.set_log_dir(self._file_manager.get_logs_dir())

        logger.info("Settings reloaded")

    def _apply_theme(self, theme: str) -> None:
        """Apply dark or light theme."""
        app = QApplication.instance()
        if theme == "light":
            app.setStyleSheet(get_light_theme())
        else:
            app.setStyleSheet(get_dark_theme())

    def _on_calibration_saved(self) -> None:
        """Handle calibration save — reload detector."""
        self._detector.reload_template()
        self._ocr_engine = None  # Force reload with new ROIs
        logger.info("Calibration updated — detector and OCR engine reloaded")

    # ─────────────────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:
        """Clean up on window close."""
        self._monitor.stop_monitoring()
        self._db.close()
        self._dash_timer.stop()
        logger.info("Application closing")
        super().closeEvent(event)
