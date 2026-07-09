"""
BalanceLog Pro — Application Entry Point

Initializes the PySide6 application, applies the industrial dark theme,
and launches the main window.

Usage:
    python main.py
"""

import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Force CPU-only PyTorch ──────────────────────────────────────────────────
# Prevents PyTorch from attempting to use CUDA, which would fail on machines
# without a GPU.  Must be set before torch is imported (EasyOCR imports it).
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# ── PyInstaller offline support ─────────────────────────────────────────────
# When running as a packaged .exe, redirect EasyOCR to the bundled model
# directory instead of trying to download from the internet.
if getattr(sys, "frozen", False):
    _bundle_dir = sys._MEIPASS  # PyInstaller temp extraction folder
    _easyocr_model_dir = os.path.join(_bundle_dir, "EasyOCR")
    os.environ["EASYOCR_MODULE_PATH"] = _easyocr_model_dir
# ───────────────────────────────────────────────────────────────────────────


from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt

from src.config.constants import APP_NAME, APP_VERSION, Fonts
from src.ui.theme import get_dark_theme


def main():
    """Launch BalanceLog Pro application."""
    # High DPI scaling
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("BalanceLogPro")

    # Set default font
    font = QFont(Fonts.FAMILY, Fonts.SIZE_NORMAL)
    app.setFont(font)

    # Apply dark theme
    app.setStyleSheet(get_dark_theme())

    # Import and create main window
    from src.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
