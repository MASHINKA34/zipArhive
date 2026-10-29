from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette

C_WINDOW = "#1a1a1a"
C_BAR = "#202020"
C_PANEL = "#252525"
C_PANEL_ALT = "#2a2a2a"
C_HOVER = "#323232"
C_BORDER = "#333333"
C_ACCENT = "#0078D4"
C_ACCENT_HI = "#3A9BE5"
C_ACCENT_BR = "#1A8AE0"
C_TEXT = "#ffffff"
C_TEXT_DIM = "#888888"
C_TEXT_SOFT = "#cccccc"
C_TEXT_FAINT = "#666666"
C_GREEN = "#2BC27A"
C_AMBER = "#E0A030"
C_CLOSE = "#C42B1C"

TOOLBAR_QSS = f"""
#toolbar {{
    background: {C_PANEL};
    border-bottom: 1px solid {C_BORDER};
}}
"""

TOOL_BUTTON_QSS = f"""
QPushButton {{
    background: {C_PANEL_ALT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 7px 14px;
    color: {C_TEXT};
    font-size: 13px;
    text-align: left;
}}
QPushButton:hover {{ background: {C_HOVER}; }}
QPushButton:pressed {{ background: #2f2f2f; }}
QPushButton:disabled {{ color: {C_TEXT_FAINT}; border-color: #2b2b2b; }}
"""

PRIMARY_BUTTON_QSS = f"""
QPushButton {{
    background: {C_ACCENT};
    border: 1px solid {C_ACCENT_BR};
    border-radius: 4px;
    padding: 11px 22px;
    color: white;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {C_ACCENT_BR}; }}
QPushButton:pressed {{ background: #006ABE; }}
"""

MUTED_BUTTON_QSS = f"""
QPushButton {{
    background: {C_BORDER};
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 11px 22px;
    color: {C_TEXT_FAINT};
    font-size: 14px;
    font-weight: 600;
}}
"""

CANCEL_BUTTON_QSS = f"""
QPushButton {{
    background: {C_PANEL_ALT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 11px 22px;
    color: {C_TEXT_SOFT};
    font-size: 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {C_CLOSE}; color: white; }}
"""

PROGRESS_QSS = f"""
QProgressBar {{
    background: {C_WINDOW};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {C_ACCENT}; border-radius: 3px; }}
"""

SCROLLBAR_QSS = f"""
QScrollBar:vertical {{
    background: {C_WINDOW}; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #3a3a3a; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #4a4a4a; }}
QScrollBar:horizontal {{
    background: {C_WINDOW}; height: 10px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #3a3a3a; border-radius: 5px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: #4a4a4a; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""

TREE_QSS = f"""
QTreeView {{
    background: {C_PANEL};
    alternate-background-color: {C_PANEL_ALT};
    color: {C_TEXT};
    font-size: 13px;
    border: none;
    outline: none;
}}
QHeaderView {{ background: {C_BAR}; }}
QHeaderView::section {{
    background: {C_BAR};
    color: {C_TEXT_DIM};
    font-size: 12px;
    font-weight: 600;
    border: 0px;
    border-bottom: 1px solid {C_BORDER};
    padding: 0 10px;
}}
QHeaderView::section:first {{ padding-left: 46px; }}
QTreeView::item {{ height: 30px; border: none; }}
QTreeView::item:hover {{ background: #2c2f33; }}
QTreeView::item:selected {{ background: #2f3a45; color: {C_TEXT}; }}
""" + SCROLLBAR_QSS

MENU_QSS = f"""
QMenu {{
    background: {C_PANEL};
    border: 1px solid {C_BORDER};
    color: {C_TEXT};
    padding: 4px;
}}
QMenu::item {{ padding: 6px 22px 6px 14px; border-radius: 3px; }}
QMenu::item:selected {{ background: {C_ACCENT}; }}
QMenu::separator {{ height: 1px; background: {C_BORDER}; margin: 4px 8px; }}
"""

DIALOG_QSS = f"""
QMessageBox {{ background: {C_WINDOW}; }}
QMessageBox QLabel {{ color: {C_TEXT}; font-size: 13px; }}
QMessageBox QPushButton {{
    background: {C_PANEL_ALT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 6px 18px;
    color: {C_TEXT};
    min-width: 76px;
}}
QMessageBox QPushButton:hover {{ background: {C_HOVER}; }}
QMessageBox QPushButton:default {{
    background: {C_ACCENT}; border-color: {C_ACCENT_BR};
}}
"""

APP_QSS = MENU_QSS + DIALOG_QSS + f"""
QToolTip {{
    background: {C_BAR};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    padding: 4px 6px;
}}
"""


def dark_palette() -> QPalette:
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: C_WINDOW,
        QPalette.ColorRole.WindowText: C_TEXT,
        QPalette.ColorRole.Base: C_PANEL,
        QPalette.ColorRole.AlternateBase: C_PANEL_ALT,
        QPalette.ColorRole.Text: C_TEXT,
        QPalette.ColorRole.Button: C_PANEL_ALT,
        QPalette.ColorRole.ButtonText: C_TEXT,
        QPalette.ColorRole.ToolTipBase: C_BAR,
        QPalette.ColorRole.ToolTipText: C_TEXT,
        QPalette.ColorRole.Highlight: C_ACCENT,
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: C_TEXT_DIM,
        QPalette.ColorRole.Link: C_ACCENT_HI,
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor(C_TEXT_FAINT),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(C_TEXT_FAINT),
    )
    return palette
