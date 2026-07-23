"""
BalanceLog Pro - Theme Engine

Stylesheets for PySide6.
Navbar and panels: #372549 with white text (PT Mono, bold).
Content background: off-white (#FAF9F6) with black text (Open Sans).
"""

from src.config.constants import Colors, Fonts


def get_dark_theme() -> str:
    """Return the main theme stylesheet."""
    return f"""
    /* === Global === */
    QWidget {{
        background-color: {Colors.BG_DARK};
        color: {Colors.TEXT_PRIMARY};
        font-family: "{Fonts.FAMILY}";
        font-size: {Fonts.SIZE_NORMAL}px;
    }}

    QMainWindow {{
        background-color: {Colors.BG_DARKEST};
    }}

    /* === Scrollbars === */
    QScrollBar:vertical {{
        background: {Colors.SCROLLBAR_BG};
        width: 10px;
        border-radius: 5px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {Colors.SCROLLBAR_HANDLE};
        min-height: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {Colors.BORDER_LIGHT};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {Colors.SCROLLBAR_BG};
        height: 10px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background: {Colors.SCROLLBAR_HANDLE};
        min-width: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {Colors.BORDER_LIGHT};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* === Push Buttons === */
    QPushButton {{
        background-color: {Colors.PRIMARY};
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-family: "{Fonts.FAMILY_PANEL}";
        font-size: {Fonts.SIZE_NORMAL}px;
        font-weight: bold;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background-color: {Colors.PRIMARY_LIGHT};
    }}
    QPushButton:pressed {{
        background-color: {Colors.PRIMARY_DARK};
    }}
    QPushButton:disabled {{
        background-color: {Colors.BG_LIGHT};
        color: {Colors.TEXT_DISABLED};
    }}
    QPushButton#btnDanger {{
        background-color: {Colors.ERROR};
        color: #FFFFFF;
    }}
    QPushButton#btnDanger:hover {{
        background-color: {Colors.ERROR_LIGHT};
    }}
    QPushButton#btnSuccess {{
        background-color: {Colors.SUCCESS};
        color: #FFFFFF;
    }}
    QPushButton#btnSuccess:hover {{
        background-color: {Colors.SUCCESS_LIGHT};
    }}
    QPushButton#btnWarning {{
        background-color: {Colors.WARNING};
        color: #111111;
    }}
    QPushButton#btnOutline {{
        background-color: transparent;
        border: 2px solid {Colors.PRIMARY};
        color: {Colors.PRIMARY};
    }}
    QPushButton#btnOutline:hover {{
        background-color: {Colors.PRIMARY};
        color: #FFFFFF;
    }}

    /* === Line Edits & Text Inputs === */
    QLineEdit, QSpinBox, QDoubleSpinBox {{
        background-color: #FFFFFF;
        border: 2px solid {Colors.BORDER};
        border-radius: 6px;
        padding: 8px 12px;
        color: {Colors.TEXT_PRIMARY};
        font-family: "{Fonts.FAMILY}";
        font-size: {Fonts.SIZE_NORMAL}px;
        selection-background-color: {Colors.PRIMARY};
        selection-color: #FFFFFF;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {Colors.BORDER_FOCUS};
    }}
    QLineEdit:disabled {{
        background-color: {Colors.BG_LIGHT};
        color: {Colors.TEXT_DISABLED};
    }}

    QTextEdit, QPlainTextEdit {{
        background-color: #FFFFFF;
        border: 2px solid {Colors.BORDER};
        border-radius: 6px;
        padding: 8px;
        color: {Colors.TEXT_PRIMARY};
        font-family: "{Fonts.FAMILY_MONO}";
        font-size: {Fonts.SIZE_SMALL}px;
    }}
    QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {Colors.BORDER_FOCUS};
    }}

    /* === Combo Box === */
    QComboBox {{
        background-color: #FFFFFF;
        border: 2px solid {Colors.BORDER};
        border-radius: 6px;
        padding: 8px 12px;
        color: {Colors.TEXT_PRIMARY};
        font-family: "{Fonts.FAMILY}";
        min-width: 120px;
    }}
    QComboBox:hover {{
        border-color: {Colors.BORDER_FOCUS};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox QAbstractItemView {{
        background-color: #FFFFFF;
        border: 1px solid {Colors.BORDER};
        color: {Colors.TEXT_PRIMARY};
        selection-background-color: {Colors.PRIMARY};
        selection-color: #FFFFFF;
        padding: 4px;
        max-height: 220px;
        outline: none;
    }}

    /* === Table Views === */
    QTableView, QTableWidget {{
        background-color: #FFFFFF;
        alternate-background-color: {Colors.BG_MEDIUM};
        border: 1px solid {Colors.BORDER};
        border-radius: 6px;
        gridline-color: {Colors.BORDER};
        selection-background-color: {Colors.PRIMARY};
        selection-color: #FFFFFF;
        color: {Colors.TEXT_PRIMARY};
    }}
    QTableView::item {{
        padding: 6px 8px;
        border-bottom: 1px solid {Colors.BORDER};
        color: {Colors.TEXT_PRIMARY};
    }}
    QTableView::item:selected {{
        background-color: {Colors.PRIMARY};
        color: #FFFFFF;
    }}
    QHeaderView::section {{
        background-color: {Colors.PRIMARY};
        color: #FFFFFF;
        padding: 8px 12px;
        border: none;
        border-right: 1px solid {Colors.PRIMARY_LIGHT};
        font-family: "{Fonts.FAMILY_PANEL}";
        font-weight: bold;
        font-size: {Fonts.SIZE_SMALL}px;
    }}
    QHeaderView::section:hover {{
        background-color: {Colors.PRIMARY_LIGHT};
    }}

    /* === Tab Widget === */
    QTabWidget::pane {{
        border: 1px solid {Colors.BORDER};
        border-radius: 6px;
        background-color: #FFFFFF;
    }}
    QTabBar::tab {{
        background-color: {Colors.BG_LIGHT};
        color: {Colors.TEXT_SECONDARY};
        padding: 10px 20px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        font-family: "{Fonts.FAMILY}";
    }}
    QTabBar::tab:selected {{
        background-color: {Colors.PRIMARY};
        color: #FFFFFF;
        font-family: "{Fonts.FAMILY_PANEL}";
        font-weight: bold;
    }}
    QTabBar::tab:hover {{
        background-color: {Colors.PRIMARY_LIGHT};
        color: #FFFFFF;
    }}

    /* === Group Box === */
    QGroupBox {{
        border: 1px solid {Colors.BORDER};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 16px;
        font-family: "{Fonts.FAMILY_PANEL}";
        font-weight: bold;
        color: {Colors.TEXT_PRIMARY};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 8px;
        color: {Colors.PRIMARY};
        font-family: "{Fonts.FAMILY_PANEL}";
        font-weight: bold;
    }}

    /* === Labels === */
    QLabel {{
        color: {Colors.TEXT_PRIMARY};
        background-color: transparent;
        font-family: "{Fonts.FAMILY}";
    }}
    QLabel#labelSecondary {{
        color: {Colors.TEXT_SECONDARY};
        font-size: {Fonts.SIZE_SMALL}px;
    }}
    QLabel#labelTitle {{
        font-family: "{Fonts.FAMILY_PANEL}";
        font-size: {Fonts.SIZE_TITLE}px;
        font-weight: bold;
        color: {Colors.TEXT_PRIMARY};
    }}

    /* === Progress Bar === */
    QProgressBar {{
        background-color: {Colors.BG_MEDIUM};
        border: none;
        border-radius: 4px;
        text-align: center;
        color: {Colors.TEXT_PRIMARY};
        min-height: 8px;
        max-height: 8px;
    }}
    QProgressBar::chunk {{
        background-color: {Colors.PRIMARY};
        border-radius: 4px;
    }}

    /* === Checkbox & Radio === */
    QCheckBox {{
        spacing: 8px;
        color: {Colors.TEXT_PRIMARY};
        font-family: "{Fonts.FAMILY}";
    }}
    QCheckBox::indicator {{
        width: 20px;
        height: 20px;
        border: 2px solid {Colors.BORDER};
        border-radius: 4px;
        background-color: #FFFFFF;
    }}
    QCheckBox::indicator:checked {{
        background-color: {Colors.PRIMARY};
        border-color: {Colors.PRIMARY};
    }}

    /* === Slider === */
    QSlider::groove:horizontal {{
        border: none;
        height: 6px;
        background: {Colors.BG_LIGHT};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {Colors.PRIMARY};
        width: 18px;
        height: 18px;
        margin: -6px 0;
        border-radius: 9px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {Colors.PRIMARY_LIGHT};
    }}

    /* === Calendar === */
    QCalendarWidget {{
        background-color: #FFFFFF;
    }}
    QCalendarWidget QTableView {{
        alternate-background-color: {Colors.BG_MEDIUM};
        selection-background-color: {Colors.PRIMARY};
        selection-color: #FFFFFF;
    }}

    /* === Status Bar === */
    QStatusBar {{
        background-color: {Colors.PRIMARY};
        color: #FFFFFF;
        border-top: 1px solid {Colors.PRIMARY_DARK};
        font-family: "{Fonts.FAMILY_PANEL}";
        font-size: {Fonts.SIZE_SMALL}px;
    }}

    /* === Menu Bar === */
    QMenuBar {{
        background-color: {Colors.PRIMARY};
        color: #FFFFFF;
        font-family: "{Fonts.FAMILY_PANEL}";
        font-weight: bold;
    }}
    QMenuBar::item:selected {{
        background-color: {Colors.PRIMARY_LIGHT};
    }}
    QMenu {{
        background-color: #FFFFFF;
        border: 1px solid {Colors.BORDER};
        color: {Colors.TEXT_PRIMARY};
        font-family: "{Fonts.FAMILY}";
    }}
    QMenu::item {{
        padding: 8px 24px;
    }}
    QMenu::item:selected {{
        background-color: {Colors.PRIMARY};
        color: #FFFFFF;
    }}

    /* === Tooltips === */
    QToolTip {{
        background-color: {Colors.PRIMARY};
        color: #FFFFFF;
        border: 1px solid {Colors.PRIMARY_DARK};
        border-radius: 4px;
        padding: 6px 10px;
        font-family: "{Fonts.FAMILY}";
        font-size: {Fonts.SIZE_SMALL}px;
    }}

    /* === Dialog === */
    QDialog {{
        background-color: {Colors.BG_DARK};
    }}

    /* === Splitter === */
    QSplitter::handle {{
        background-color: {Colors.BORDER};
        width: 2px;
    }}
    """


def get_light_theme() -> str:
    """Return the light theme stylesheet (same palette as main theme)."""
    return get_dark_theme()


def get_sidebar_style() -> str:
    """Return the sidebar-specific stylesheet for the navigation panel."""
    return f"""
    QFrame#sidebar {{
        background-color: {Colors.SIDEBAR_BG};
        border-right: 2px solid {Colors.PRIMARY_DARK};
    }}
    QPushButton.nav-btn {{
        background-color: transparent;
        color: rgba(255, 255, 255, 0.75);
        border: none;
        border-radius: 6px;
        padding: 12px 16px;
        text-align: left;
        font-family: "{Fonts.FAMILY_PANEL}";
        font-size: {Fonts.SIZE_NORMAL}px;
        font-weight: bold;
    }}
    QPushButton.nav-btn:hover {{
        background-color: {Colors.SIDEBAR_HOVER};
        color: #FFFFFF;
    }}
    QPushButton.nav-btn:checked {{
        background-color: rgba(255, 255, 255, 0.18);
        color: #FFFFFF;
        border-left: 3px solid #FFFFFF;
        font-weight: bold;
    }}
    QLabel#sidebar-title {{
        color: #FFFFFF;
        font-family: "{Fonts.FAMILY_PANEL}";
        font-size: {Fonts.SIZE_LARGE}px;
        font-weight: bold;
        padding: 4px 0;
    }}
    QLabel#sidebar-version {{
        color: rgba(255, 255, 255, 0.55);
        font-family: "{Fonts.FAMILY}";
        font-size: {Fonts.SIZE_SMALL}px;
    }}
    """
