"""
BalanceLog Pro - Custom Widgets

Reusable UI components for the industrial dashboard:
StatusCard, MonitoringIndicator, ImageViewer, AnimatedButton.
"""

from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect,
    QSizePolicy, QScrollArea, QWidget,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QSize, Property
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap

from src.config.constants import Colors, Fonts


class StatusCard(QFrame):
    """
    Dashboard status card with icon, title, value, and accent color.

    ┌───────────────────┐
    │  ● Title          │
    │  42               │
    │  Subtitle         │
    └───────────────────┘
    """

    def __init__(self, title: str, value: str = "—", subtitle: str = "",
                 accent_color: str = Colors.PRIMARY, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")
        self.setFixedHeight(130)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._accent_color = accent_color

        # Card styling
        self.setStyleSheet(f"""
            QFrame#statusCard {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
                border-left: 4px solid {accent_color};
            }}
            QFrame#statusCard:hover {{
                border-color: {accent_color};
                background-color: {Colors.BG_LIGHT};
            }}
        """)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SMALL))
        self._title_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(self._title_label)

        # Value
        self._value_label = QLabel(value)
        self._value_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_TITLE, QFont.Weight.Bold))
        self._value_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(self._value_label)

        # Subtitle
        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SMALL))
        self._subtitle_label.setStyleSheet(f"color: {Colors.TEXT_DISABLED}; background: transparent;")
        layout.addWidget(self._subtitle_label)

    def set_value(self, value: str) -> None:
        """Update the card value."""
        self._value_label.setText(value)

    def set_subtitle(self, text: str) -> None:
        """Update the subtitle."""
        self._subtitle_label.setText(text)

    def set_accent_color(self, color: str) -> None:
        """Change the accent color."""
        self._accent_color = color
        self.setStyleSheet(f"""
            QFrame#statusCard {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
                border-left: 4px solid {color};
            }}
            QFrame#statusCard:hover {{
                border-color: {color};
                background-color: {Colors.BG_LIGHT};
            }}
        """)


class MonitoringIndicator(QWidget):
    """
    Pulsing dot indicator showing monitoring status.

    Green pulsing = Active
    Red solid = Stopped
    Yellow blinking = Warning
    Gray = Idle
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._color = QColor(Colors.TEXT_DISABLED)
        self._pulse = False
        self._pulse_alpha = 255

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_pulse)
        self._direction = -5

    def set_active(self) -> None:
        """Set indicator to active (green, pulsing)."""
        self._color = QColor(Colors.SUCCESS)
        self._pulse = True
        self._timer.start(50)
        self.update()

    def set_stopped(self) -> None:
        """Set indicator to stopped (red, solid)."""
        self._color = QColor(Colors.ERROR)
        self._pulse = False
        self._timer.stop()
        self._pulse_alpha = 255
        self.update()

    def set_warning(self) -> None:
        """Set indicator to warning (yellow, blinking)."""
        self._color = QColor(Colors.WARNING)
        self._pulse = True
        self._timer.start(80)
        self.update()

    def set_idle(self) -> None:
        """Set indicator to idle (gray, solid)."""
        self._color = QColor(Colors.TEXT_DISABLED)
        self._pulse = False
        self._timer.stop()
        self._pulse_alpha = 255
        self.update()

    def _animate_pulse(self) -> None:
        """Animate the pulsing effect."""
        self._pulse_alpha += self._direction
        if self._pulse_alpha <= 80:
            self._direction = 5
        elif self._pulse_alpha >= 255:
            self._direction = -5
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer glow
        glow_color = QColor(self._color)
        glow_color.setAlpha(max(0, self._pulse_alpha // 3))
        painter.setBrush(glow_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 16, 16)

        # Inner dot
        dot_color = QColor(self._color)
        dot_color.setAlpha(self._pulse_alpha)
        painter.setBrush(dot_color)
        painter.drawEllipse(3, 3, 10, 10)

        painter.end()


class ImageViewer(QScrollArea):
    """
    Zoomable screenshot viewer with scroll support.

    Supports loading from file path, QPixmap, or numpy array.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.BG_DARKEST};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background: transparent;")
        self.setWidget(self._image_label)

        self._pixmap: QPixmap = None
        self._zoom = 1.0

    def load_from_path(self, path: str) -> bool:
        """Load image from file path."""
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._image_label.setText("Failed to load image")
            return False
        self._pixmap = pixmap
        self._update_display()
        return True

    def load_pixmap(self, pixmap: QPixmap) -> None:
        """Load image from QPixmap."""
        self._pixmap = pixmap
        self._update_display()

    def set_zoom(self, zoom: float) -> None:
        """Set zoom level (1.0 = 100%)."""
        self._zoom = max(0.1, min(5.0, zoom))
        self._update_display()

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom * 1.2)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom / 1.2)

    def fit_to_window(self) -> None:
        """Fit image to the viewer size."""
        if self._pixmap:
            w_ratio = self.width() / self._pixmap.width()
            h_ratio = self.height() / self._pixmap.height()
            self._zoom = min(w_ratio, h_ratio) * 0.95
            self._update_display()

    def _update_display(self) -> None:
        if self._pixmap:
            scaled = self._pixmap.scaled(
                int(self._pixmap.width() * self._zoom),
                int(self._pixmap.height() * self._zoom),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._image_label.setPixmap(scaled)

    def wheelEvent(self, event) -> None:
        """Zoom with Ctrl+Wheel."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)


class SectionHeader(QFrame):
    """Section header with title and optional subtitle."""

    def __init__(self, title: str, subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XLARGE, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SMALL))
            sub_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
            layout.addWidget(sub_label)
