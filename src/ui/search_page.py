"""
BalanceLog Pro - Search Page

Advanced search interface with multiple filter criteria,
result highlighting, and screenshot access.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLineEdit, QComboBox, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QDateEdit, QDoubleSpinBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QFont

from src.config.constants import Colors, Fonts
from src.database.models import SearchFilter
from src.ui.widgets import SectionHeader


class SearchPage(QWidget):
    """
    Search page with flexible filtering options.

    Search by:
    - Punching Number (partial match)
    - Date range
    - Time range
    - Tube Length range
    - Shaft Type
    - Minimum OCR confidence

    Results displayed in a table with screenshot access.
    """

    search_requested = Signal(SearchFilter)
    view_record = Signal(int)
    view_screenshot = Signal(str)
    export_results = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header = SectionHeader("Search Records", "Find balancing records by any criteria")
        layout.addWidget(header)

        # Search form
        form_frame = QFrame()
        form_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(12)

        # Row 0: Punching Number + Type
        form_layout.addWidget(self._label("Punching Number:"), 0, 0)
        self._input_punching = QLineEdit()
        self._input_punching.setPlaceholderText("Enter punching number...")
        self._input_punching.returnPressed.connect(self._on_search)
        form_layout.addWidget(self._input_punching, 0, 1)

        form_layout.addWidget(self._label("Shaft Type:"), 0, 2)
        self._combo_type = QComboBox()
        self._combo_type.addItems(["All", "Front", "Rear"])
        form_layout.addWidget(self._combo_type, 0, 3)

        # Row 1: Date Range
        form_layout.addWidget(self._label("Date From:"), 1, 0)
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addDays(-30))
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        form_layout.addWidget(self._date_from, 1, 1)

        form_layout.addWidget(self._label("Date To:"), 1, 2)
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        form_layout.addWidget(self._date_to, 1, 3)

        # Row 2: Tube Length Range
        form_layout.addWidget(self._label("Tube Length Min:"), 2, 0)
        self._spin_length_min = QDoubleSpinBox()
        self._spin_length_min.setRange(0, 5000)
        self._spin_length_min.setValue(0)
        self._spin_length_min.setSuffix(" mm")
        form_layout.addWidget(self._spin_length_min, 2, 1)

        form_layout.addWidget(self._label("Tube Length Max:"), 2, 2)
        self._spin_length_max = QDoubleSpinBox()
        self._spin_length_max.setRange(0, 5000)
        self._spin_length_max.setValue(5000)
        self._spin_length_max.setSuffix(" mm")
        form_layout.addWidget(self._spin_length_max, 2, 3)

        # Search buttons
        btn_layout = QHBoxLayout()
        btn_search = QPushButton("Search")
        btn_search.setMinimumHeight(42)
        btn_search.clicked.connect(self._on_search)
        btn_layout.addWidget(btn_search)

        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("btnOutline")
        btn_clear.setMinimumHeight(42)
        btn_clear.clicked.connect(self._clear_filters)
        btn_layout.addWidget(btn_clear)

        btn_export = QPushButton("Export Results")
        btn_export.setObjectName("btnOutline")
        btn_export.setMinimumHeight(42)
        btn_export.clicked.connect(lambda: self.export_results.emit(self._results))
        btn_layout.addWidget(btn_export)

        btn_layout.addStretch()

        self._result_count = QLabel("Ready to search")
        self._result_count.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        btn_layout.addWidget(self._result_count)

        form_layout.addLayout(btn_layout, 3, 0, 1, 4)

        layout.addWidget(form_frame)

        # Results table
        self._table = QTableWidget()
        columns = [
            ("Date", 100), ("Time", 80), ("Punching No.", 140),
            ("Tube Length", 100), ("Type", 70),
            ("Init Left", 90), ("Init Right", 90),
            ("Corr Left", 90), ("Corr Right", 90),
            ("Confidence", 95), ("Screenshot", 80),
        ]
        self._table.setColumnCount(len(columns))
        self._table.setHorizontalHeaderLabels([c[0] for c in columns])
        for i, (_, w) in enumerate(columns):
            self._table.setColumnWidth(i, w)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.doubleClicked.connect(self._on_row_double_click)

        layout.addWidget(self._table)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        return lbl

    # ─────────────────────────────────────────────────────────
    # Search
    # ─────────────────────────────────────────────────────────
    def _on_search(self) -> None:
        """Build search filter and emit signal."""
        shaft_type = self._combo_type.currentText()
        if shaft_type == "All":
            shaft_type = ""

        length_min = self._spin_length_min.value()
        length_max = self._spin_length_max.value()

        filters = SearchFilter(
            punching_number=self._input_punching.text().strip(),
            date_from=self._date_from.date().toString("yyyy-MM-dd"),
            date_to=self._date_to.date().toString("yyyy-MM-dd"),
            shaft_type=shaft_type,
            tube_length_min=length_min if length_min > 0 else None,
            tube_length_max=length_max if length_max < 5000 else None,
        )
        self.search_requested.emit(filters)

    def _clear_filters(self) -> None:
        """Reset all filter inputs."""
        self._input_punching.clear()
        self._combo_type.setCurrentIndex(0)
        self._date_from.setDate(QDate.currentDate().addDays(-30))
        self._date_to.setDate(QDate.currentDate())
        self._spin_length_min.setValue(0)
        self._spin_length_max.setValue(5000)

    # ─────────────────────────────────────────────────────────
    # Results Display
    # ─────────────────────────────────────────────────────────
    def display_results(self, records: list) -> None:
        """Populate table with search results."""
        self._results = records
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(records))

        for row, r in enumerate(records):
            items = [
                r.date, r.time, r.punching_number,
                f"{r.tube_length:.0f}", r.shaft_type,
                f"{r.initial_left_value:.2f}", f"{r.initial_right_value:.2f}",
                f"{r.after_correction_left:.2f}", f"{r.after_correction_right:.2f}",
                f"{r.ocr_confidence:.1%}",
                "Yes" if r.screenshot_path else "",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, r.id)
                if col == 9:  # Confidence
                    if r.ocr_confidence >= 0.90:
                        item.setForeground(QColor(Colors.SUCCESS))
                    elif r.ocr_confidence >= 0.75:
                        item.setForeground(QColor(Colors.WARNING))
                    else:
                        item.setForeground(QColor(Colors.ERROR))
                self._table.setItem(row, col, item)

        self._table.setSortingEnabled(True)
        self._result_count.setText(f"{len(records)} results found")

    def _on_row_double_click(self, index) -> None:
        row = index.row()
        id_item = self._table.item(row, 0)
        if id_item:
            record_id = id_item.data(Qt.ItemDataRole.UserRole)
            if record_id:
                self.view_record.emit(record_id)
