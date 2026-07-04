"""
BalanceLog Pro - ROI Selector Widget

Interactive PySide6 widget for drawing rectangles on a screenshot
to define OCR regions of interest. Supports zoom, pan, undo, and
label assignment for each ROI.
"""

from typing import Dict, Optional, Tuple, List
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPixmap, QColor, QPen, QFont, QMouseEvent,
    QWheelEvent, QPaintEvent, QImage,
)
import numpy as np
import cv2


class ROISelector(QWidget):
    """
    Interactive widget for drawing and editing ROI rectangles on a screenshot.

    Features:
    - Load a reference screenshot
    - Draw rectangles by click-and-drag
    - Label each ROI with a field name
    - Zoom with mouse wheel
    - Pan with middle mouse button
    - Undo/redo support
    - ROI coordinates stored as percentages (0.0–1.0) for resolution independence

    Signals:
        roi_defined(str, dict): Emitted when a new ROI is defined (field_name, roi_dict)
        roi_removed(str): Emitted when a ROI is removed
        all_rois_updated(dict): Emitted when any ROI changes
    """

    roi_defined = Signal(str, dict)
    roi_removed = Signal(str)
    all_rois_updated = Signal(dict)

    # Colors for different ROI fields
    ROI_COLORS = [
        QColor(30, 136, 229, 120),   # Blue
        QColor(67, 160, 71, 120),    # Green
        QColor(249, 168, 37, 120),   # Amber
        QColor(229, 57, 53, 120),    # Red
        QColor(142, 36, 170, 120),   # Purple
        QColor(0, 172, 193, 120),    # Cyan
        QColor(255, 109, 0, 120),    # Orange
        QColor(0, 200, 83, 120),     # Light Green
        QColor(156, 39, 176, 120),   # Deep Purple
        QColor(3, 169, 244, 120),    # Light Blue
        QColor(255, 193, 7, 120),    # Yellow
        QColor(233, 30, 99, 120),    # Pink
        QColor(0, 150, 136, 120),    # Teal
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Image
        self._pixmap: Optional[QPixmap] = None
        self._image_size = (0, 0)  # Original image size (w, h)

        # Zoom & Pan
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self._panning = False
        self._pan_start = QPointF()

        # ROIs
        self._rois: Dict[str, QRectF] = {}  # field_name -> QRectF (in image %)
        self._current_field: str = ""
        self._drawing = False
        self._draw_start = QPointF()
        self._draw_current = QRectF()

        # Undo stack
        self._undo_stack: List[Dict[str, QRectF]] = []

    # ─────────────────────────────────────────────────────────
    # Image Loading
    # ─────────────────────────────────────────────────────────
    def load_image(self, image_path: str) -> bool:
        """Load a screenshot image from file."""
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return False
        self._pixmap = pixmap
        self._image_size = (pixmap.width(), pixmap.height())
        self._zoom = min(
            self.width() / pixmap.width(),
            self.height() / pixmap.height(),
        ) * 0.9
        self._pan_offset = QPointF(0, 0)
        self.update()
        return True

    def load_numpy_image(self, image: np.ndarray) -> bool:
        """Load a screenshot from a numpy array (BGR)."""
        try:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self._pixmap = QPixmap.fromImage(q_img)
            self._image_size = (w, h)
            self._zoom = min(
                self.width() / w,
                self.height() / h,
            ) * 0.9
            self._pan_offset = QPointF(0, 0)
            self.update()
            return True
        except Exception:
            return False

    # ─────────────────────────────────────────────────────────
    # ROI Management
    # ─────────────────────────────────────────────────────────
    def set_current_field(self, field_name: str) -> None:
        """Set the field name for the next ROI to be drawn."""
        self._current_field = field_name

    def get_rois_as_dict(self) -> Dict[str, dict]:
        """
        Get all ROIs as percentage-based dictionaries.

        Returns: {field_name: {"x": float, "y": float, "w": float, "h": float}}
        """
        result = {}
        for name, rect in self._rois.items():
            result[name] = {
                "x": rect.x(),
                "y": rect.y(),
                "w": rect.width(),
                "h": rect.height(),
            }
        return result

    def set_rois_from_dict(self, rois: Dict[str, dict]) -> None:
        """Load ROIs from a dictionary (e.g., from calibration file)."""
        self._rois.clear()
        for name, roi in rois.items():
            self._rois[name] = QRectF(
                roi["x"], roi["y"], roi["w"], roi["h"]
            )
        self.update()

    def remove_roi(self, field_name: str) -> None:
        """Remove a specific ROI."""
        if field_name in self._rois:
            self._save_undo()
            del self._rois[field_name]
            self.roi_removed.emit(field_name)
            self.all_rois_updated.emit(self.get_rois_as_dict())
            self.update()

    def clear_all_rois(self) -> None:
        """Remove all ROIs."""
        self._save_undo()
        self._rois.clear()
        self.all_rois_updated.emit({})
        self.update()

    def undo(self) -> None:
        """Undo the last ROI change."""
        if self._undo_stack:
            self._rois = self._undo_stack.pop()
            self.all_rois_updated.emit(self.get_rois_as_dict())
            self.update()

    def _save_undo(self) -> None:
        """Save current state to undo stack."""
        self._undo_stack.append(dict(self._rois))
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)

    # ─────────────────────────────────────────────────────────
    # Coordinate Conversion
    # ─────────────────────────────────────────────────────────
    def _widget_to_image_pct(self, point: QPointF) -> QPointF:
        """Convert widget coordinates to image percentage coordinates."""
        if not self._pixmap:
            return QPointF(0, 0)

        # Remove pan offset and zoom
        img_x = (point.x() - self._pan_offset.x()) / (self._image_size[0] * self._zoom)
        img_y = (point.y() - self._pan_offset.y()) / (self._image_size[1] * self._zoom)

        return QPointF(
            max(0.0, min(1.0, img_x)),
            max(0.0, min(1.0, img_y)),
        )

    def _image_pct_to_widget(self, point: QPointF) -> QPointF:
        """Convert image percentage coordinates to widget coordinates."""
        if not self._pixmap:
            return QPointF(0, 0)

        wx = point.x() * self._image_size[0] * self._zoom + self._pan_offset.x()
        wy = point.y() * self._image_size[1] * self._zoom + self._pan_offset.y()
        return QPointF(wx, wy)

    # ─────────────────────────────────────────────────────────
    # Mouse Events
    # ─────────────────────────────────────────────────────────
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton and self._current_field:
            self._drawing = True
            self._draw_start = self._widget_to_image_pct(event.position())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_offset += delta
            self._pan_start = event.position()
            self.update()
        elif self._drawing:
            current = self._widget_to_image_pct(event.position())
            x = min(self._draw_start.x(), current.x())
            y = min(self._draw_start.y(), current.y())
            w = abs(current.x() - self._draw_start.x())
            h = abs(current.y() - self._draw_start.y())
            self._draw_current = QRectF(x, y, w, h)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            if self._draw_current.width() > 0.005 and self._draw_current.height() > 0.005:
                self._save_undo()
                self._rois[self._current_field] = self._draw_current
                roi_dict = {
                    "x": self._draw_current.x(),
                    "y": self._draw_current.y(),
                    "w": self._draw_current.width(),
                    "h": self._draw_current.height(),
                }
                self.roi_defined.emit(self._current_field, roi_dict)
                self.all_rois_updated.emit(self.get_rois_as_dict())
            self._draw_current = QRectF()
            self.update()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom with mouse wheel."""
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom *= 1.1
        else:
            self._zoom = max(0.1, self._zoom * 0.9)
        self.update()
        super().wheelEvent(event)

    # ─────────────────────────────────────────────────────────
    # Painting
    # ─────────────────────────────────────────────────────────
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#111820"))

        if not self._pixmap:
            painter.setPen(QColor("#9aa0a6"))
            painter.setFont(QFont("Segoe UI", 14))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "Load a screenshot to begin calibration")
            return

        # Draw image
        scaled_w = int(self._image_size[0] * self._zoom)
        scaled_h = int(self._image_size[1] * self._zoom)
        scaled_pixmap = self._pixmap.scaled(
            scaled_w, scaled_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        x_off = int(self._pan_offset.x())
        y_off = int(self._pan_offset.y())
        painter.drawPixmap(x_off, y_off, scaled_pixmap)

        # Draw existing ROIs
        for idx, (name, rect) in enumerate(self._rois.items()):
            color = self.ROI_COLORS[idx % len(self.ROI_COLORS)]
            self._draw_roi(painter, rect, name, color)

        # Draw current drawing rectangle
        if self._drawing and self._draw_current.width() > 0:
            color = QColor(255, 255, 255, 80)
            self._draw_roi(painter, self._draw_current, self._current_field, color)

        painter.end()

    def _draw_roi(self, painter: QPainter, rect_pct: QRectF,
                  label: str, color: QColor) -> None:
        """Draw a single ROI rectangle with label."""
        # Convert percentage to widget coordinates
        tl = self._image_pct_to_widget(QPointF(rect_pct.x(), rect_pct.y()))
        br = self._image_pct_to_widget(QPointF(
            rect_pct.x() + rect_pct.width(),
            rect_pct.y() + rect_pct.height(),
        ))

        widget_rect = QRectF(tl, br)

        # Fill
        fill_color = QColor(color)
        fill_color.setAlpha(40)
        painter.fillRect(widget_rect, fill_color)

        # Border
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.drawRect(widget_rect)

        # Label
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        label_color = QColor(color)
        label_color.setAlpha(255)
        painter.setPen(label_color)

        label_rect = QRectF(tl.x(), tl.y() - 18, widget_rect.width(), 18)
        bg_color = QColor(color)
        bg_color.setAlpha(180)
        painter.fillRect(label_rect, bg_color)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)
