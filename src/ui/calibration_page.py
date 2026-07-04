"""
BalanceLog Pro - Calibration Page

Step-by-step calibration wizard for defining OCR regions of interest.
Allows operators to upload screenshots and draw ROI rectangles for each field.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QFrame,
    QStackedWidget, QMessageBox, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from src.config.constants import Colors, Fonts, ROI_FIELDS, ROI_FIELD_LABELS
from src.calibration.roi_selector import ROISelector
from src.calibration.calibration_manager import CalibrationManager
from src.ui.widgets import SectionHeader


class CalibrationPage(QWidget):
    """
    Step-by-step calibration wizard.

    Steps:
    1. Upload reference screenshot(s) of the ABRO result page
    2. Select a field and draw ROI rectangle for each
    3. Review all defined ROIs
    4. Save calibration

    After calibration, the OCR engine knows exactly where each field
    is located on the ABRO result screen.
    """

    calibration_saved = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cal_manager = CalibrationManager()
        self._image_path = ""
        self._setup_ui()
        self._load_existing_calibration()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header = SectionHeader(
            "Calibration Wizard",
            "Define OCR regions for each data field on the ABRO result screen"
        )
        layout.addWidget(header)

        # Main content: left panel (field list) + right panel (ROI selector)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # ── Left Panel: Controls ──
        left_frame = QFrame()
        left_frame.setFixedWidth(280)
        left_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(10)

        # Upload button
        btn_upload = QPushButton("Upload Screenshot")
        btn_upload.setMinimumHeight(42)
        btn_upload.clicked.connect(self._upload_screenshot)
        left_layout.addWidget(btn_upload)

        self._image_label = QLabel("No image loaded")
        self._image_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        self._image_label.setWordWrap(True)
        left_layout.addWidget(self._image_label)

        # Field selector
        left_layout.addWidget(self._make_label("Select Field to Define:"))

        self._field_list = QListWidget()
        self._field_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QListWidget::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)

        for field_name in ROI_FIELDS:
            label = ROI_FIELD_LABELS.get(field_name, field_name)
            item = QListWidgetItem(f"○  {label}")
            item.setData(Qt.ItemDataRole.UserRole, field_name)
            self._field_list.addItem(item)

        self._field_list.currentItemChanged.connect(self._on_field_selected)
        left_layout.addWidget(self._field_list)

        # Undo button
        btn_undo = QPushButton("↩  Undo Last ROI")
        btn_undo.setObjectName("btnOutline")
        btn_undo.clicked.connect(self._undo)
        left_layout.addWidget(btn_undo)

        # Clear all
        btn_clear = QPushButton("Clear All ROIs")
        btn_clear.setObjectName("btnDanger")
        btn_clear.clicked.connect(self._clear_all)
        left_layout.addWidget(btn_clear)

        # Save calibration
        btn_save = QPushButton("Save Calibration")
        btn_save.setObjectName("btnSuccess")
        btn_save.setMinimumHeight(44)
        btn_save.clicked.connect(self._save_calibration)
        left_layout.addWidget(btn_save)

        # Status
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        left_layout.addWidget(self._status_label)

        content_layout.addWidget(left_frame)

        # ── Right Panel: ROI Selector ──
        self._roi_selector = ROISelector()
        self._roi_selector.roi_defined.connect(self._on_roi_defined)
        self._roi_selector.all_rois_updated.connect(self._update_field_status)
        content_layout.addWidget(self._roi_selector, 1)

        layout.addLayout(content_layout)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SMALL, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        return lbl

    # ─────────────────────────────────────────────────────────
    # Screenshot Upload
    # ─────────────────────────────────────────────────────────
    def _upload_screenshot(self) -> None:
        """Open file dialog to select an ABRO screenshot."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select ABRO Result Screenshot",
            "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)",
        )
        if path:
            self._image_path = path
            if self._roi_selector.load_image(path):
                self._image_label.setText(f"Loaded: {Path(path).name}")
                self._image_label.setStyleSheet(
                    f"color: {Colors.SUCCESS}; background: transparent;"
                )
            else:
                self._image_label.setText("Failed to load image")
                self._image_label.setStyleSheet(
                    f"color: {Colors.ERROR}; background: transparent;"
                )

    # ─────────────────────────────────────────────────────────
    # Field Selection
    # ─────────────────────────────────────────────────────────
    def _on_field_selected(self, current, previous) -> None:
        """Update ROI selector to accept drawing for the selected field."""
        if current:
            field_name = current.data(Qt.ItemDataRole.UserRole)
            self._roi_selector.set_current_field(field_name)
            self._status_label.setText(
                f"Draw a rectangle around '{ROI_FIELD_LABELS.get(field_name, field_name)}'"
            )

    def _on_roi_defined(self, field_name: str, roi: dict) -> None:
        """Handle a newly defined ROI."""
        self._update_field_status(self._roi_selector.get_rois_as_dict())

    def _update_field_status(self, rois: dict) -> None:
        """Update the field list to show which fields have been defined."""
        for i in range(self._field_list.count()):
            item = self._field_list.item(i)
            field_name = item.data(Qt.ItemDataRole.UserRole)
            label = ROI_FIELD_LABELS.get(field_name, field_name)

            if field_name in rois:
                item.setText(f"[OK]  {label}")
                item.setForeground(QColor(Colors.SUCCESS))
            else:
                item.setText(f"○  {label}")
                item.setForeground(QColor(Colors.TEXT_SECONDARY))

        defined = sum(1 for f in ROI_FIELDS if f in rois)
        self._status_label.setText(f"{defined}/{len(ROI_FIELDS)} fields defined")

    # ─────────────────────────────────────────────────────────
    # Save / Load
    # ─────────────────────────────────────────────────────────
    def _save_calibration(self) -> None:
        """Save the current ROI configuration."""
        rois = self._roi_selector.get_rois_as_dict()

        if not rois:
            QMessageBox.warning(
                self, "No ROIs Defined",
                "Please define at least one ROI before saving.",
            )
            return

        if not self._image_path:
            QMessageBox.warning(
                self, "No Screenshot",
                "Please upload a reference screenshot first.",
            )
            return

        success = self._cal_manager.save_calibration(
            rois=rois,
            template_image_path=self._image_path,
            resolution=(1920, 1080),  # Default; will be updated from actual window
            detection_method="manual",
        )

        if success:
            QMessageBox.information(
                self, "Calibration Saved",
                f"Successfully saved {len(rois)} ROI definitions.\n"
                "The OCR engine will use these regions for data extraction.",
            )
            self.calibration_saved.emit()
        else:
            QMessageBox.critical(
                self, "Save Failed",
                "Failed to save calibration. Check logs for details.",
            )

    def _load_existing_calibration(self) -> None:
        """Load existing calibration if available."""
        if self._cal_manager.is_calibrated:
            rois = self._cal_manager.get_rois()
            self._roi_selector.set_rois_from_dict(rois)
            self._update_field_status(rois)

            template_path = self._cal_manager.get_template_path()
            if template_path and Path(template_path).exists():
                self._image_path = template_path
                self._roi_selector.load_image(template_path)
                self._image_label.setText(f"Template: {Path(template_path).name}")
                self._image_label.setStyleSheet(
                    f"color: {Colors.SUCCESS}; background: transparent;"
                )

    def _undo(self) -> None:
        self._roi_selector.undo()

    def _clear_all(self) -> None:
        reply = QMessageBox.question(
            self, "Clear All ROIs",
            "Remove all ROI definitions? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._roi_selector.clear_all_rois()
            self._update_field_status({})
