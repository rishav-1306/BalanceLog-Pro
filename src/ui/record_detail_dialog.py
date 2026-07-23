"""
BalanceLog Pro - Record Detail Dialog

Modal dialog showing full details of a balancing record
with screenshot preview, validation status, and edit capability.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QFrame, QSizePolicy,
    QDialogButtonBox, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap

from src.config.constants import Colors, Fonts
from src.database.models import BalancingRecord
from src.ui.widgets import ImageViewer


class RecordDetailDialog(QDialog):
    """
    Modal dialog showing full record details.

    Features:
    - All extracted fields displayed
    - Screenshot preview (zoomable)
    - OCR confidence per field (color coded)
    - Edit capability for corrections
    - Notes field
    - Save / Cancel buttons
    """

    record_updated = Signal(BalancingRecord)

    def __init__(self, record: BalancingRecord, parent=None) -> None:
        super().__init__(parent)
        self._record = record
        self._edits = {}
        self.setWindowTitle(f"Record Detail — {record.punching_number}")
        self.setMinimumSize(700, 450)
        self.setStyleSheet(f"background-color: {Colors.BG_DARK};")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # ── Left: Data Fields ──
        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)

        title = QLabel(f"Record #{self._record.id or 'New'}")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XLARGE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        left_layout.addWidget(title)

        # Fields grid
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

        row = 0
        fields = [
            ("Date", self._record.date),
            ("Time", self._record.time),
            ("Rotor Number", self._record.rotor_no if self._record.rotor_no else self._record.punching_number),
            ("Actual RPM", f"{self._record.actual_rpm:.0f}"),
            ("Type", self._record.shaft_type),
            ("Initial Left", f"{self._record.initial_left_value:.2f}"),
            ("Initial Left Angle", f"{self._record.initial_left_angle:.1f}°"),
            ("Initial Right", f"{self._record.initial_right_value:.2f}"),
            ("Initial Right Angle", f"{self._record.initial_right_angle:.1f}°"),
            ("Weight Addition Left", str(self._record.weight_addition_left)),
            ("Weight Addition Right", str(self._record.weight_addition_right)),
            ("Corrected Left", f"{self._record.after_correction_left:.2f}"),
            ("Corrected Left Angle", f"{self._record.after_correction_left_angle:.1f}°"),
            ("Corrected Right", f"{self._record.after_correction_right:.2f}"),
            ("Corrected Right Angle", f"{self._record.after_correction_right_angle:.1f}°"),
            ("OCR Confidence", f"{self._record.ocr_confidence:.1%}"),
        ]

        for label_text, value_text in fields:
            lbl = QLabel(f"{label_text}:")
            lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
            lbl.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SMALL))
            grid.addWidget(lbl, row, 0)

            if label_text in ("Weight Addition Left", "Weight Addition Right"):
                val = QComboBox()
                val.addItems(["0", "10", "20", "30", "40", "50"])
                try:
                    val_float = float(value_text or 0)
                    val_str = str(int(val_float))
                except ValueError:
                    val_str = "0"
                idx = val.findText(val_str)
                if idx >= 0:
                    val.setCurrentIndex(idx)
                else:
                    val.addItem(val_str)
                    val.setCurrentIndex(val.count() - 1)
            else:
                val = QLineEdit(str(value_text))
                val.setReadOnly(True)

            self._edits[label_text] = val
            grid.addWidget(val, row, 1)

            row += 1

        left_layout.addWidget(fields_frame)

        # Notes
        notes_label = QLabel("Operator Notes:")
        notes_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        left_layout.addWidget(notes_label)

        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)
        self._notes_edit.setPlainText(self._record.operator_notes)
        left_layout.addWidget(self._notes_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Changes")
        btn_save.setObjectName("btnSuccess")
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)

        btn_close = QPushButton("Close")
        btn_close.setObjectName("btnOutline")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)

        left_layout.addLayout(btn_layout)
        layout.addLayout(left_layout, 1)

        # ── Right: Screenshot Preview ──
        right_layout = QVBoxLayout()

        preview_label = QLabel("Screenshot Preview")
        preview_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LARGE, QFont.Weight.Bold))
        preview_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        right_layout.addWidget(preview_label)

        self._viewer = ImageViewer()
        if self._record.screenshot_path:
            self._viewer.load_from_path(self._record.screenshot_path)
        right_layout.addWidget(self._viewer)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(36, 36)
        btn_zoom_in.clicked.connect(self._viewer.zoom_in)
        zoom_layout.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedSize(36, 36)
        btn_zoom_out.clicked.connect(self._viewer.zoom_out)
        zoom_layout.addWidget(btn_zoom_out)

        btn_fit = QPushButton("Fit")
        btn_fit.setObjectName("btnOutline")
        btn_fit.clicked.connect(self._viewer.fit_to_window)
        zoom_layout.addWidget(btn_fit)

        zoom_layout.addStretch()
        right_layout.addLayout(zoom_layout)

        layout.addLayout(right_layout, 1)

    def _save(self) -> None:
        """Save operator edits and notes."""
        try:
            self._record.weight_addition_left = float(self._edits["Weight Addition Left"].currentText() or 0)
            self._record.weight_addition_right = float(self._edits["Weight Addition Right"].currentText() or 0)
        except (ValueError, KeyError):
            pass

        self._record.operator_notes = self._notes_edit.toPlainText()
        self._record.update_timestamp()
        self.record_updated.emit(self._record)
        self.accept()
