"""
BalanceLog Pro - Reports Page

Report generation interface for daily, weekly, and monthly production
summaries with export to Excel, CSV, and PDF.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QComboBox, QDateEdit, QFrame, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont

from src.config.constants import Colors, Fonts
from src.database.models import ReportData
from src.ui.widgets import StatusCard, SectionHeader


class ReportsPage(QWidget):
    """
    Report generation and export page.

    Features:
    - Period selector (Daily / Weekly / Monthly)
    - Date picker for the report period
    - Statistics summary cards
    - Export to Excel, CSV, PDF
    """

    generate_report = Signal(str, str)  # period, date_str
    export_report = Signal(str, str)    # format, output_path

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_report = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # Header
        header = SectionHeader("Production Reports", "Generate and export production summaries")
        layout.addWidget(header)

        # Control bar
        control_frame = QFrame()
        control_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(20, 16, 20, 16)
        control_layout.setSpacing(16)

        control_layout.addWidget(QLabel("Report Period:"))
        self._combo_period = QComboBox()
        self._combo_period.addItems(["Daily", "Weekly", "Monthly"])
        control_layout.addWidget(self._combo_period)

        control_layout.addWidget(QLabel("Date:"))
        self._date_picker = QDateEdit()
        self._date_picker.setCalendarPopup(True)
        self._date_picker.setDate(QDate.currentDate())
        self._date_picker.setDisplayFormat("yyyy-MM-dd")
        control_layout.addWidget(self._date_picker)

        btn_generate = QPushButton("Generate Report")
        btn_generate.setMinimumHeight(40)
        btn_generate.clicked.connect(self._on_generate)
        control_layout.addWidget(btn_generate)

        control_layout.addStretch()

        layout.addWidget(control_frame)

        # Statistics cards
        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        self._card_total = StatusCard(
            "TOTAL SHAFTS", "—", "In this period",
            accent_color=Colors.PRIMARY,
        )
        cards_layout.addWidget(self._card_total, 0, 0)

        self._card_front = StatusCard(
            "FRONT SHAFTS", "—", "",
            accent_color=Colors.CHART_1,
        )
        cards_layout.addWidget(self._card_front, 0, 1)

        self._card_rear = StatusCard(
            "REAR SHAFTS", "—", "",
            accent_color=Colors.CHART_2,
        )
        cards_layout.addWidget(self._card_rear, 0, 2)

        self._card_avg_initial = StatusCard(
            "AVG INITIAL IMBALANCE", "—", "grams",
            accent_color=Colors.WARNING,
        )
        cards_layout.addWidget(self._card_avg_initial, 1, 0)

        self._card_avg_final = StatusCard(
            "AVG FINAL IMBALANCE", "—", "grams",
            accent_color=Colors.SUCCESS,
        )
        cards_layout.addWidget(self._card_avg_final, 1, 1)

        self._card_common_weight = StatusCard(
            "COMMON CORRECTION", "—", "Most used weight",
            accent_color=Colors.INFO,
        )
        cards_layout.addWidget(self._card_common_weight, 1, 2)

        layout.addLayout(cards_layout)

        # Export buttons
        export_frame = QFrame()
        export_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        export_layout = QHBoxLayout(export_frame)
        export_layout.setContentsMargins(20, 16, 20, 16)
        export_layout.setSpacing(12)

        export_layout.addWidget(QLabel("Export Report:"))

        btn_excel = QPushButton("Export Excel")
        btn_excel.setObjectName("btnSuccess")
        btn_excel.setMinimumHeight(40)
        btn_excel.clicked.connect(lambda: self._on_export("xlsx"))
        export_layout.addWidget(btn_excel)

        btn_csv = QPushButton("Export CSV")
        btn_csv.setObjectName("btnOutline")
        btn_csv.setMinimumHeight(40)
        btn_csv.clicked.connect(lambda: self._on_export("csv"))
        export_layout.addWidget(btn_csv)

        btn_pdf = QPushButton("Export PDF")
        btn_pdf.setObjectName("btnOutline")
        btn_pdf.setMinimumHeight(40)
        btn_pdf.clicked.connect(lambda: self._on_export("pdf"))
        export_layout.addWidget(btn_pdf)

        export_layout.addStretch()

        self._export_status = QLabel("")
        self._export_status.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        export_layout.addWidget(self._export_status)

        layout.addWidget(export_frame)

        layout.addStretch()

    # ─────────────────────────────────────────────────────────
    # Report Generation
    # ─────────────────────────────────────────────────────────
    def _on_generate(self) -> None:
        period = self._combo_period.currentText()
        date_str = self._date_picker.date().toString("yyyy-MM-dd")
        self.generate_report.emit(period, date_str)

    def display_report(self, report: ReportData) -> None:
        """Display report statistics in the cards."""
        self._current_report = report

        self._card_total.set_value(str(report.total_shafts))
        self._card_total.set_subtitle(f"{report.period}: {report.start_date} — {report.end_date}")

        self._card_front.set_value(str(report.front_count))
        self._card_rear.set_value(str(report.rear_count))

        self._card_avg_initial.set_value(f"{report.avg_initial_imbalance:.2f}")
        self._card_avg_final.set_value(f"{report.avg_final_imbalance:.2f}")
        self._card_common_weight.set_value(f"{report.most_common_weight:.1f}g")

    def _on_export(self, fmt: str) -> None:
        if not self._current_report:
            QMessageBox.warning(self, "No Report",
                                "Generate a report first before exporting.")
            return

        filters = {
            "xlsx": "Excel Files (*.xlsx)",
            "csv": "CSV Files (*.csv)",
            "pdf": "PDF Files (*.pdf)",
        }

        default_name = f"Report_{self._current_report.period}_{self._current_report.start_date}.{fmt}"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export {fmt.upper()} Report",
            default_name, filters.get(fmt, ""),
        )
        if path:
            self.export_report.emit(fmt, path)
            self._export_status.setText(f"Exported to {path}")
