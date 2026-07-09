"""
BalanceLog Pro - Records Page

Displays balancing records in a sortable, filterable table view.
Supports date filtering, inline editing, context menu, and screenshot viewing.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QDateEdit, QMenu,
    QAbstractItemView, QMessageBox, QFrame, QComboBox,
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QColor, QAction

from src.config.constants import Colors, Fonts
from src.database.models import BalancingRecord
from src.ui.widgets import SectionHeader


class RecordsPage(QWidget):
    """
    Table view of all balancing records with date filtering.

    Features:
    - Sortable columns
    - Date filter
    - Double-click to view record detail
    - Context menu (View, Edit, Delete, Export)
    - Color-coded OCR confidence
    """

    view_record = Signal(int)       # record ID
    view_screenshot = Signal(str)   # screenshot path
    export_records = Signal(list)   # list of records
    delete_record = Signal(int)     # record ID
    record_updated = Signal(BalancingRecord)

    # Column definitions
    COLUMNS = [
        ("ID", 50),
        ("Date", 100),
        ("Time", 80),
        ("Punching No.", 140),
        ("Tube Length", 100),
        ("Type", 70),
        ("Init Left", 90),
        ("Init Right", 90),
        ("Wt Add L", 80),
        ("Wt Add R", 80),
        ("Corr Left", 90),
        ("Corr Right", 90),
        ("Confidence", 95),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._records = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header = SectionHeader(
            "Balancing Records",
            "View and manage all recorded balancing cycles"
        )
        layout.addWidget(header)

        # Filter bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        filter_layout.addWidget(QLabel("From:"))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate())
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self._date_from)

        filter_layout.addWidget(QLabel("To:"))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self._date_to)

        btn_filter = QPushButton("Apply Filter")
        btn_filter.clicked.connect(self._on_filter)
        filter_layout.addWidget(btn_filter)

        btn_today = QPushButton("Today")
        btn_today.setObjectName("btnOutline")
        btn_today.clicked.connect(self._show_today)
        filter_layout.addWidget(btn_today)

        filter_layout.addStretch()

        self._count_label = QLabel("0 records")
        self._count_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        filter_layout.addWidget(self._count_label)

        btn_export = QPushButton("Export")
        btn_export.setObjectName("btnOutline")
        btn_export.clicked.connect(self._on_export)
        filter_layout.addWidget(btn_export)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._on_filter)
        filter_layout.addWidget(btn_refresh)

        layout.addWidget(filter_frame)

        # Table
        self._table = QTableWidget()
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                gridline-color: {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QTableWidget QLineEdit {{
                background-color: {Colors.BG_DARK};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.INFO};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels([c[0] for c in self.COLUMNS])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self._table.itemChanged.connect(self._on_item_changed)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(38)

        # Set column widths and resize modes
        header_view = self._table.horizontalHeader()
        for i in range(len(self.COLUMNS)):
            header_view.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)

    # ─────────────────────────────────────────────────────────
    # Data Loading
    # ─────────────────────────────────────────────────────────
    def load_records(self, records: list) -> None:
        """Load records into the table."""
        self._records = records
        self._table.setSortingEnabled(False)
        self._table.blockSignals(True)
        self._table.setRowCount(len(records))

        for row, record in enumerate(records):
            items = [
                (str(record.daily_seq or record.id or ""), Qt.AlignmentFlag.AlignCenter),
                (record.date, Qt.AlignmentFlag.AlignCenter),
                (record.time, Qt.AlignmentFlag.AlignCenter),
                (record.rotor_no if record.rotor_no else record.punching_number, Qt.AlignmentFlag.AlignLeft),
                (f"{record.tube_length:.0f}", Qt.AlignmentFlag.AlignCenter),
                (record.shaft_type, Qt.AlignmentFlag.AlignCenter),
                (f"{record.initial_left_value:.2f}", Qt.AlignmentFlag.AlignCenter),
                (f"{record.initial_right_value:.2f}", Qt.AlignmentFlag.AlignCenter),
                (str(record.weight_addition_left), Qt.AlignmentFlag.AlignCenter),
                (str(record.weight_addition_right), Qt.AlignmentFlag.AlignCenter),
                (f"{record.after_correction_left:.2f}", Qt.AlignmentFlag.AlignCenter),
                (f"{record.after_correction_right:.2f}", Qt.AlignmentFlag.AlignCenter),
                (f"{record.ocr_confidence:.1%}", Qt.AlignmentFlag.AlignCenter),
            ]

            for col, (text, alignment) in enumerate(items):
                item = QTableWidgetItem("") if col in (8, 9) else QTableWidgetItem(text)
                item.setTextAlignment(alignment)

                # Store record ID in first column
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, record.id)

                # Color code confidence
                if col == len(items) - 1:
                    if record.ocr_confidence >= 0.90:
                        item.setForeground(QColor(Colors.SUCCESS))
                    elif record.ocr_confidence >= 0.75:
                        item.setForeground(QColor(Colors.WARNING))
                    else:
                        item.setForeground(QColor(Colors.ERROR))

                # Allow inline editing only for Punching No. (col 3)
                if col == 3:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self._table.setItem(row, col, item)

                # Wt Add L (col 8) and Wt Add R (col 9) as comboboxes
                if col in (8, 9):
                    combo = QComboBox()
                    combo.addItems(["0", "10", "20", "30", "40", "50"])
                    try:
                        val_float = float(text or 0)
                        val_str = str(int(val_float))
                    except ValueError:
                        val_str = "0"
                    idx = combo.findText(val_str)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                    else:
                        combo.addItem(val_str)
                        combo.setCurrentIndex(combo.count() - 1)

                    combo.setStyleSheet(f"""
                        QComboBox {{
                            background-color: {Colors.BG_CARD};
                            border: 1px solid {Colors.BORDER};
                            border-radius: 4px;
                            color: {Colors.TEXT_PRIMARY};
                            padding: 2px;
                        }}
                    """)

                    field_name = "weight_addition_left" if col == 8 else "weight_addition_right"
                    combo.currentIndexChanged.connect(
                        lambda _, r=record, field=field_name, cb=combo: self._on_combo_changed(r, field, cb)
                    )
                    self._table.setCellWidget(row, col, combo)

        self._table.blockSignals(False)
        self._table.setSortingEnabled(True)

        # Auto-resize columns to fit contents
        self._table.resizeColumnsToContents()
        # Force minimum widths for dropdown columns so they don't look compressed
        self._table.setColumnWidth(8, max(self._table.columnWidth(8), 90))
        self._table.setColumnWidth(9, max(self._table.columnWidth(9), 90))
        # Ensure Punching No has a minimum width but still stretches
        self._table.setColumnWidth(3, max(self._table.columnWidth(3), 150))
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self._count_label.setText(f"{len(records)} records")

    # ─────────────────────────────────────────────────────────
    # Events
    # ─────────────────────────────────────────────────────────
    def _on_filter(self) -> None:
        """Emit signal with date range for filtering."""
        # This signal is handled by main_window to reload from DB
        pass  # Connected externally

    def _show_today(self) -> None:
        """Set date filters to today."""
        self._date_from.setDate(QDate.currentDate())
        self._date_to.setDate(QDate.currentDate())
        self._on_filter()

    def _on_export(self) -> None:
        """Export currently displayed records."""
        self.export_records.emit(self._records)

    def _on_double_click(self, index) -> None:
        """Handle double-click on a row."""
        # Col 3 (Punching No.) is editable inline, do not open detail dialog
        if index.column() == 3:
            return
        row = index.row()
        id_item = self._table.item(row, 0)
        if id_item:
            record_id = id_item.data(Qt.ItemDataRole.UserRole)
            if record_id:
                self.view_record.emit(record_id)

    def _show_context_menu(self, position) -> None:
        """Show right-click context menu."""
        row = self._table.rowAt(position.y())
        if row < 0:
            return

        id_item = self._table.item(row, 0)
        if not id_item:
            return
        record_id = id_item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        view_action = QAction("View Details", self)
        view_action.triggered.connect(lambda: self.view_record.emit(record_id))
        menu.addAction(view_action)

        if row < len(self._records):
            ss_path = self._records[row].screenshot_path
            if ss_path:
                screenshot_action = QAction("Open Screenshot", self)
                screenshot_action.triggered.connect(
                    lambda: self.view_screenshot.emit(ss_path)
                )
                menu.addAction(screenshot_action)

        menu.addSeparator()

        delete_action = QAction("Delete Record", self)
        delete_action.triggered.connect(lambda: self._confirm_delete(record_id))
        menu.addAction(delete_action)

        menu.exec(self._table.mapToGlobal(position))

    def _confirm_delete(self, record_id: int) -> None:
        """Confirm deletion of a record."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete record #{record_id}? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_record.emit(record_id)

    def get_date_range(self) -> tuple:
        """Get the current date filter range."""
        return (
            self._date_from.date().toString("yyyy-MM-dd"),
            self._date_to.date().toString("yyyy-MM-dd"),
        )

    def _on_combo_changed(self, record: BalancingRecord, field: str, combo: QComboBox) -> None:
        """Handle inline combobox edits for weight additions."""
        try:
            val = float(combo.currentText() or 0)
            if getattr(record, field) != val:
                setattr(record, field, val)
                record.update_timestamp()
                self.record_updated.emit(record)
        except ValueError:
            pass

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle inline text edits (Punching No.)."""
        row = item.row()
        col = item.column()
        if col == 3 and row < len(self._records):
            record = self._records[row]
            new_text = item.text().strip()
            # Only update if changed
            current_val = record.rotor_no if record.rotor_no else record.punching_number
            if new_text != current_val:
                record.rotor_no = new_text
                record.punching_number = new_text
                record.update_timestamp()
                self.record_updated.emit(record)
