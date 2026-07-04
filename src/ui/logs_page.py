"""
BalanceLog Pro - Logs Page

Live log viewer with filtering by log level, log file selection,
and search within logs.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QPlainTextEdit, QLineEdit, QFrame, QFileDialog,
)
from PySide6.QtCore import Qt, QTimer, QFileSystemWatcher
from PySide6.QtGui import QFont, QTextCharFormat, QColor

from src.config.constants import Colors, Fonts
from src.ui.widgets import SectionHeader


class LogsPage(QWidget):
    """
    Live log viewer with syntax highlighting and filtering.

    Features:
    - Log file selector (app, ocr, error, capture, performance)
    - Log level filter (DEBUG, INFO, WARNING, ERROR)
    - Search within logs
    - Auto-refresh from log files
    - Clear and export log
    """

    def __init__(self, log_dir: Path = None, parent=None) -> None:
        super().__init__(parent)
        self._log_dir = log_dir
        self._current_file = ""
        self._setup_ui()

        # Auto-refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_log)
        self._refresh_timer.start(3000)  # Every 3 seconds

    def set_log_dir(self, log_dir: Path) -> None:
        """Set the log directory."""
        self._log_dir = log_dir

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header = SectionHeader("Application Logs", "Monitor system events and debug information")
        layout.addWidget(header)

        # Controls
        controls_frame = QFrame()
        controls_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
            }}
        """)
        controls = QHBoxLayout(controls_frame)
        controls.setContentsMargins(16, 12, 16, 12)
        controls.setSpacing(10)

        controls.addWidget(QLabel("Log File:"))
        self._combo_file = QComboBox()
        self._combo_file.addItems([
            "app.log", "ocr.log", "error.log", "capture.log", "performance.log"
        ])
        self._combo_file.currentTextChanged.connect(self._on_file_changed)
        controls.addWidget(self._combo_file)

        controls.addWidget(QLabel("Filter:"))
        self._combo_level = QComboBox()
        self._combo_level.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self._combo_level.currentTextChanged.connect(self._apply_filter)
        controls.addWidget(self._combo_level)

        controls.addWidget(QLabel("Search:"))
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search logs...")
        self._search_input.setFixedWidth(200)
        self._search_input.textChanged.connect(self._apply_filter)
        controls.addWidget(self._search_input)

        controls.addStretch()

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._refresh_log)
        controls.addWidget(btn_refresh)

        btn_clear = QPushButton("Clear View")
        btn_clear.setObjectName("btnOutline")
        btn_clear.clicked.connect(lambda: self._log_view.clear())
        controls.addWidget(btn_clear)

        btn_export = QPushButton("Export")
        btn_export.setObjectName("btnOutline")
        btn_export.clicked.connect(self._export_log)
        controls.addWidget(btn_export)

        layout.addWidget(controls_frame)

        # Log viewer
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(5000)
        self._log_view.setFont(QFont(Fonts.FAMILY_MONO, 11))
        self._log_view.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {Colors.BG_DARKEST};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self._log_view)

        # Status bar
        self._status = QLabel("Ready")
        self._status.setStyleSheet(f"color: {Colors.TEXT_DISABLED};")
        layout.addWidget(self._status)

    # ─────────────────────────────────────────────────────────
    # Log Loading
    # ─────────────────────────────────────────────────────────
    def _on_file_changed(self, filename: str) -> None:
        """Load a different log file."""
        self._current_file = filename
        self._refresh_log()

    def _refresh_log(self) -> None:
        """Reload the current log file."""
        if not self._log_dir or not self._current_file:
            return

        log_path = self._log_dir / self._current_file
        if not log_path.exists():
            self._log_view.setPlainText(f"Log file not found: {log_path}")
            return

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                # Read last 500 lines for performance
                lines = f.readlines()
                recent = lines[-500:] if len(lines) > 500 else lines
                self._all_lines = recent
                self._apply_filter()
                self._status.setText(
                    f"Showing {len(recent)} of {len(lines)} lines — "
                    f"File: {log_path.name} ({log_path.stat().st_size / 1024:.0f} KB)"
                )
        except Exception as e:
            self._log_view.setPlainText(f"Error reading log: {e}")

    def _apply_filter(self) -> None:
        """Apply level and search filters to the log display."""
        if not hasattr(self, "_all_lines"):
            return

        level = self._combo_level.currentText()
        search = self._search_input.text().lower()

        filtered = []
        for line in self._all_lines:
            # Level filter
            if level != "ALL":
                if f"| {level}" not in line and level not in line:
                    continue
            # Search filter
            if search and search not in line.lower():
                continue
            filtered.append(line)

        # Apply syntax coloring via simple text (QPlainTextEdit)
        colored_text = ""
        for line in filtered:
            colored_text += line

        self._log_view.setPlainText(colored_text)

        # Auto-scroll to bottom
        scrollbar = self._log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _export_log(self) -> None:
        """Export the current log view to a file."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Log",
            f"exported_{self._current_file or 'log'}.txt",
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._log_view.toPlainText())
