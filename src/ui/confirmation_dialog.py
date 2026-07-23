"""
BalanceLog Pro - Confirmation Dialog

Shown when OCR confidence is low. Displays extracted values alongside
the screenshot, allowing the operator to confirm, edit, or reject.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPixmap

from src.config.constants import Colors, Fonts
from src.database.models import BalancingRecord
from src.ocr.ocr_result import ExtractionSummary
from src.ui.widgets import ImageViewer
from src.utils.logger import get_logger

logger = get_logger("ui")


class ConfirmationDialog(QDialog):
    """
    Operator confirmation dialog for low-confidence OCR results.

    Displays:
    - Screenshot preview
    - Extracted values with confidence color coding
    - Editable fields for corrections
    - Accept / Reject buttons

    Emits:
        confirmed(BalancingRecord): When operator accepts (possibly edited) values
        rejected(): When operator rejects the extraction
    """

    confirmed = Signal(BalancingRecord)
    rejected = Signal()

    def __init__(self, record: BalancingRecord,
                 extraction: ExtractionSummary = None,
                 parent=None) -> None:
        super().__init__(parent)
        self._record = record
        self._extraction = extraction
        self._field_inputs = {}
        self.setWindowTitle("Confirm Extracted Values")
        self.setMinimumSize(650, 420)
        self.setStyleSheet(f"background-color: {Colors.BG_DARK};")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Warning header
        warning = QLabel("Low OCR Confidence — Please Review Extracted Values")
        warning.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LARGE, QFont.Weight.Bold))
        warning.setStyleSheet(f"""
            color: {Colors.WARNING};
            background-color: {Colors.BG_CARD};
            border: 2px solid {Colors.WARNING};
            border-radius: 8px;
            padding: 12px;
        """)
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)

        # Content: fields + preview
        content = QHBoxLayout()
        content.setSpacing(16)

        # Fields
        fields_frame = QFrame()
        fields_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
            }}
        """)
        grid = QGridLayout(fields_frame)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(8)

        fields = [
            ("rotor_no", "Rotor Number", self._record.rotor_no),
            ("actual_rpm", "Actual RPM", str(self._record.actual_rpm)),
            ("shaft_type", "Type", self._record.shaft_type),
            ("initial_left_value", "Initial Left (gm)", str(self._record.initial_left_value)),
            ("initial_left_angle", "Init Left Angle (°)", str(self._record.initial_left_angle)),
            ("initial_right_value", "Initial Right (gm)", str(self._record.initial_right_value)),
            ("initial_right_angle", "Init Right Angle (°)", str(self._record.initial_right_angle)),
            ("weight_addition_left", "Wt Add Left (gm)", str(self._record.weight_addition_left)),
            ("weight_addition_right", "Wt Add Right (gm)", str(self._record.weight_addition_right)),
            ("after_correction_left", "Corrected Left (gm)", str(self._record.after_correction_left)),
            ("after_correction_left_angle", "Corr Left Angle (°)", str(self._record.after_correction_left_angle)),
            ("after_correction_right", "Corrected Right (gm)", str(self._record.after_correction_right)),
            ("after_correction_right_angle", "Corr Right Angle (°)", str(self._record.after_correction_right_angle)),
        ]

        for row, (field_name, label_text, value) in enumerate(fields):
            # Confidence indicator
            confidence = 1.0
            if self._extraction and field_name in self._extraction.fields:
                confidence = self._extraction.fields[field_name].confidence

            if confidence >= 0.90:
                indicator = "[OK]"
            elif confidence >= 0.75:
                indicator = "[~]"
            else:
                indicator = "[!]"

            lbl = QLabel(f"{indicator} {label_text}:")
            lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
            grid.addWidget(lbl, row, 0)

            if field_name in ("weight_addition_left", "weight_addition_right"):
                inp = QComboBox()
                inp.addItems(["0", "10", "20", "30", "40", "50"])
                try:
                    val_float = float(value or 0)
                    val_str = str(int(val_float))
                except ValueError:
                    val_str = "0"
                idx = inp.findText(val_str)
                if idx >= 0:
                    inp.setCurrentIndex(idx)
                else:
                    inp.addItem(val_str)
                    inp.setCurrentIndex(inp.count() - 1)
            else:
                inp = QLineEdit(value)
                if confidence < 0.75:
                    inp.setStyleSheet(f"""
                        QLineEdit {{
                            border-color: {Colors.ERROR};
                            background-color: rgba(229, 57, 53, 0.1);
                        }}
                    """)
            self._field_inputs[field_name] = inp
            grid.addWidget(inp, row, 1)

            conf_label = QLabel(f"{confidence:.0%}")
            conf_label.setFixedWidth(40)
            conf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            conf_label.setStyleSheet(f"color: {Colors.TEXT_DISABLED}; background: transparent;")
            grid.addWidget(conf_label, row, 2)

        content.addWidget(fields_frame, 1)

        # Screenshot preview
        self._viewer = ImageViewer()
        if self._record.screenshot_path:
            self._viewer.load_from_path(self._record.screenshot_path)
        content.addWidget(self._viewer, 1)

        layout.addLayout(content)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_accept = QPushButton("Accept Values")
        btn_accept.setObjectName("btnSuccess")
        btn_accept.setMinimumHeight(44)
        btn_accept.clicked.connect(self._on_accept)
        btn_layout.addWidget(btn_accept)

        btn_reject = QPushButton("Reject & Discard")
        btn_reject.setObjectName("btnDanger")
        btn_reject.setMinimumHeight(44)
        btn_reject.clicked.connect(self._on_reject)
        btn_layout.addWidget(btn_reject)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def _on_accept(self) -> None:
        """Apply any edits and emit confirmed signal."""
        # Update record with potentially edited values
        try:
            self._record.rotor_no = self._field_inputs["rotor_no"].text()
            self._record.punching_number = self._record.rotor_no  # Sync legacy property
            self._record.actual_rpm = float(self._field_inputs["actual_rpm"].text() or 0)
            self._record.shaft_type = self._field_inputs["shaft_type"].text()
            self._record.initial_left_value = float(self._field_inputs["initial_left_value"].text() or 0)
            self._record.initial_left_angle = float(self._field_inputs["initial_left_angle"].text() or 0)
            self._record.initial_right_value = float(self._field_inputs["initial_right_value"].text() or 0)
            self._record.initial_right_angle = float(self._field_inputs["initial_right_angle"].text() or 0)
            self._record.weight_addition_left = float(self._field_inputs["weight_addition_left"].currentText() or 0)
            self._record.weight_addition_right = float(self._field_inputs["weight_addition_right"].currentText() or 0)
            self._record.after_correction_left = float(self._field_inputs["after_correction_left"].text() or 0)
            self._record.after_correction_left_angle = float(self._field_inputs["after_correction_left_angle"].text() or 0)
            self._record.after_correction_right = float(self._field_inputs["after_correction_right"].text() or 0)
            self._record.after_correction_right_angle = float(self._field_inputs["after_correction_right_angle"].text() or 0)
        except (ValueError, KeyError) as e:
            logger.error("Error saving edits in confirmation dialog: %s", e)

        self.confirmed.emit(self._record)
        self.accept()

    def _on_reject(self) -> None:
        """Reject the extraction."""
        self.rejected.emit()
        self.reject()
