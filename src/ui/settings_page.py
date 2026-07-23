"""
BalanceLog Pro - Settings Page

Application settings for ABRO window selection, paths, OCR configuration,
theme, and auto-startup options.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QCheckBox, QSlider, QGroupBox,
    QFileDialog, QFrame, QSpinBox, QDoubleSpinBox, QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.config.config_manager import ConfigManager
from src.config.constants import Colors, Fonts
from src.capture.window_finder import WindowFinder
from src.ui.widgets import SectionHeader


class SettingsPage(QWidget):
    """
    Application settings page.

    Sections:
    - ABRO Window: Select/detect the ABRO software window
    - Paths: Screenshot, Excel, database, log directories
    - OCR: Engine, language, confidence threshold, scale factor
    - Monitoring: Capture interval, change detection sensitivity
    - Theme: Dark/Light toggle
    - Auto-startup: Launch on Windows login
    """

    settings_changed = Signal()
    theme_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._config = ConfigManager()
        self._window_finder = WindowFinder()
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {Colors.BG_DARK}; }}")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # Header
        header = SectionHeader("Settings", "Configure BalanceLog Pro")
        layout.addWidget(header)

        # ── ABRO Window ──
        window_group = self._group_box("ABRO Window Configuration")
        wg_layout = QGridLayout(window_group)
        wg_layout.setSpacing(10)

        wg_layout.addWidget(QLabel("Window Title:"), 0, 0)
        self._input_window_title = QLineEdit()
        self._input_window_title.setPlaceholderText("Enter ABRO window title pattern...")
        wg_layout.addWidget(self._input_window_title, 0, 1)

        btn_detect = QPushButton("Detect Windows")
        btn_detect.clicked.connect(self._detect_windows)
        wg_layout.addWidget(btn_detect, 0, 2)

        wg_layout.addWidget(QLabel("Available Windows:"), 1, 0)
        self._combo_windows = QComboBox()
        self._combo_windows.setMaxVisibleItems(8)
        self._combo_windows.currentTextChanged.connect(self._on_window_selected)
        wg_layout.addWidget(self._combo_windows, 1, 1, 1, 2)

        layout.addWidget(window_group)

        # ── Paths ──
        paths_group = self._group_box("File Paths")
        pg_layout = QGridLayout(paths_group)
        pg_layout.setSpacing(10)

        self._input_base_dir = self._path_row(pg_layout, 0, "Base Directory:", is_dir=True)
        self._input_db_dir = self._path_row(pg_layout, 1, "Database Directory:", is_dir=True)

        layout.addWidget(paths_group)

        # ── OCR Settings ──
        ocr_group = self._group_box("OCR Configuration")
        og_layout = QGridLayout(ocr_group)
        og_layout.setSpacing(10)

        og_layout.addWidget(QLabel("OCR Engine:"), 0, 0)
        self._combo_engine = QComboBox()
        self._combo_engine.setMaxVisibleItems(8)
        self._combo_engine.addItems(["easyocr", "tesseract"])
        og_layout.addWidget(self._combo_engine, 0, 1)

        og_layout.addWidget(QLabel("Language:"), 0, 2)
        self._combo_language = QComboBox()
        self._combo_language.setMaxVisibleItems(8)
        self._combo_language.addItems(["en", "de", "fr", "es", "it", "pt"])
        og_layout.addWidget(self._combo_language, 0, 3)

        og_layout.addWidget(QLabel("Image Scale Factor:"), 1, 0)
        self._spin_scale = QDoubleSpinBox()
        self._spin_scale.setRange(1.0, 4.0)
        self._spin_scale.setSingleStep(0.5)
        self._spin_scale.setDecimals(1)
        og_layout.addWidget(self._spin_scale, 1, 1)

        layout.addWidget(ocr_group)

        # ── Monitoring ──
        monitor_group = self._group_box("Monitoring Configuration")
        mg_layout = QGridLayout(monitor_group)
        mg_layout.setSpacing(10)

        mg_layout.addWidget(QLabel("Capture Interval:"), 0, 0)
        self._spin_interval = QSpinBox()
        self._spin_interval.setRange(500, 10000)
        self._spin_interval.setSingleStep(500)
        self._spin_interval.setSuffix(" ms")
        mg_layout.addWidget(self._spin_interval, 0, 1)

        mg_layout.addWidget(QLabel("Change Detection Sensitivity:"), 1, 0)
        self._slider_ssim = QSlider(Qt.Orientation.Horizontal)
        self._slider_ssim.setRange(50, 99)
        self._slider_ssim.setTickPosition(QSlider.TickPosition.TicksBelow)
        mg_layout.addWidget(self._slider_ssim, 1, 1)
        self._label_ssim = QLabel("95%")
        self._label_ssim.setFixedWidth(40)
        self._slider_ssim.valueChanged.connect(
            lambda v: self._label_ssim.setText(f"{v}%")
        )
        mg_layout.addWidget(self._label_ssim, 1, 2)

        layout.addWidget(monitor_group)

        # ── Appearance ──
        appearance_group = self._group_box("Appearance")
        ag_layout = QHBoxLayout(appearance_group)

        ag_layout.addWidget(QLabel("Theme:"))
        self._combo_theme = QComboBox()
        self._combo_theme.setMaxVisibleItems(8)
        self._combo_theme.addItems(["Dark", "Light"])
        self._combo_theme.currentTextChanged.connect(
            lambda t: self.theme_changed.emit(t.lower())
        )
        ag_layout.addWidget(self._combo_theme)

        ag_layout.addWidget(QLabel("Auto Export to Excel:"))
        self._check_auto_export = QCheckBox()
        ag_layout.addWidget(self._check_auto_export)

        ag_layout.addStretch()

        layout.addWidget(appearance_group)

        # ── Save Button ──
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Settings")
        btn_save.setObjectName("btnSuccess")
        btn_save.setMinimumHeight(44)
        btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(btn_save)

        btn_reset = QPushButton("Reset to Defaults")
        btn_reset.setObjectName("btnDanger")
        btn_reset.setMinimumHeight(44)
        btn_reset.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _group_box(self, title: str) -> QGroupBox:
        gb = QGroupBox(title)
        return gb

    def _path_row(self, layout, row, label, is_dir=True) -> QLineEdit:
        layout.addWidget(QLabel(label), row, 0)
        line_edit = QLineEdit()
        layout.addWidget(line_edit, row, 1)
        btn = QPushButton("Browse...")
        btn.setFixedWidth(90)
        btn.clicked.connect(
            lambda: self._browse_dir(line_edit) if is_dir
            else self._browse_file(line_edit)
        )
        layout.addWidget(btn, row, 2)
        return line_edit

    def _browse_dir(self, line_edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            line_edit.setText(path)

    def _browse_file(self, line_edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path:
            line_edit.setText(path)

    # ─────────────────────────────────────────────────────────
    # Window Detection
    # ─────────────────────────────────────────────────────────
    def _detect_windows(self) -> None:
        """Enumerate all visible windows and populate dropdown."""
        self._combo_windows.clear()
        self._combo_windows.addItem("-- Select a window --")
        windows = self._window_finder.list_all_windows()
        for win in windows:
            self._combo_windows.addItem(f"{win.title} (PID: {win.process_id})")

    def _on_window_selected(self, text: str) -> None:
        if text and not text.startswith("--"):
            # Extract window title (before PID)
            title = text.split(" (PID:")[0]
            self._input_window_title.setText(title)

    # ─────────────────────────────────────────────────────────
    # Load / Save
    # ─────────────────────────────────────────────────────────
    def _load_settings(self) -> None:
        """Load current settings into form fields."""
        self._input_window_title.setText(
            self._config.get("monitoring.abro_window_title", "")
        )
        self._input_base_dir.setText(
            self._config.get("paths.base_directory", "")
        )
        self._input_db_dir.setText(
            self._config.get("paths.database_directory", "")
        )
        self._combo_engine.setCurrentText(
            self._config.get("ocr.engine", "easyocr")
        )
        self._combo_language.setCurrentText(
            self._config.get("ocr.language", "en")
        )
        self._spin_scale.setValue(
            self._config.get("ocr.scale_factor", 2.0)
        )
        self._spin_interval.setValue(
            self._config.get("monitoring.capture_interval_ms", 2000)
        )
        self._slider_ssim.setValue(
            int(self._config.get("monitoring.ssim_threshold", 0.95) * 100)
        )
        theme = self._config.get("app.theme", "dark")
        self._combo_theme.setCurrentText(theme.capitalize())
        self._check_auto_export.setChecked(
            self._config.get("excel.auto_export", True)
        )

    def _save_settings(self) -> None:
        """Save form values to configuration."""
        self._config.set("monitoring.abro_window_title",
                         self._input_window_title.text())
        self._config.set("paths.base_directory",
                         self._input_base_dir.text())
        self._config.set("paths.database_directory",
                         self._input_db_dir.text())
        self._config.set("ocr.engine",
                         self._combo_engine.currentText())
        self._config.set("ocr.language",
                         self._combo_language.currentText())
        self._config.set("ocr.scale_factor",
                         self._spin_scale.value())
        self._config.set("monitoring.capture_interval_ms",
                         self._spin_interval.value())
        self._config.set("monitoring.ssim_threshold",
                         self._slider_ssim.value() / 100.0)
        self._config.set("app.theme",
                         self._combo_theme.currentText().lower())
        self._config.set("excel.auto_export",
                         self._check_auto_export.isChecked())

        self.settings_changed.emit()
        QMessageBox.information(self, "Settings Saved",
                                "Settings saved successfully.")

    def _reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._config.reset_settings()
            self._load_settings()
