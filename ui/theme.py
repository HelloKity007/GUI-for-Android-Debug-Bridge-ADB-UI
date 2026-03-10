# -*- coding: utf-8 -*-
"""
Theme Manager - Color schemes and styling
"""

LIGHT_COLORS = {
    'bg': '#f5f5f5',
    'fg': '#1f1f1f',
    'accent': '#0078d4',
    'accent_hover': '#106ebe',
    'success': '#107c10',
    'warning': '#ff8c00',
    'error': '#d13438',
    'card_bg': '#ffffff',
    'border': '#e1e1e1',
    'text_secondary': '#666666',
    'text_tertiary': '#999999',
}

DARK_COLORS = {
    'bg': '#1e1e1e',
    'fg': '#e0e0e0',
    'accent': '#0078d4',
    'accent_hover': '#106ebe',
    'success': '#4ec9b0',
    'warning': '#ffaa44',
    'error': '#f48771',
    'card_bg': '#252526',
    'border': '#3e3e42',
    'text_secondary': '#cccccc',
    'text_tertiary': '#858585',
}


class ThemeManager:
    """Manages application theme and colors"""
    
    def __init__(self, dark_mode=False):
        self.dark_mode = dark_mode
        self.colors = DARK_COLORS.copy() if dark_mode else LIGHT_COLORS.copy()
    
    def toggle(self):
        """Toggle between light and dark mode"""
        self.dark_mode = not self.dark_mode
        self.colors = DARK_COLORS.copy() if self.dark_mode else LIGHT_COLORS.copy()
        return self.dark_mode
    
    def set_dark_mode(self, enabled):
        """Set dark mode state"""
        self.dark_mode = enabled
        self.colors = DARK_COLORS.copy() if enabled else LIGHT_COLORS.copy()
    
    def get_stylesheet(self):
        """Get global application stylesheet"""
        c = self.colors
        return f"""
            QMainWindow, QDialog {{
                background-color: {c['bg']};
                color: {c['fg']};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {c['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: {c['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: {c['fg']};
            }}
            QPushButton {{
                background-color: {c['card_bg']};
                color: {c['fg']};
                border: 1px solid {c['border']};
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: {c['accent']};
                color: white;
                border-color: {c['accent']};
            }}
            QPushButton:pressed {{
                background-color: {c['accent_hover']};
            }}
            QPushButton[accent="true"] {{
                background-color: {c['accent']};
                color: white;
                border-color: {c['accent']};
            }}
            QPushButton[accent="true"]:hover {{
                background-color: {c['accent_hover']};
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {c['card_bg']};
                color: {c['fg']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 6px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {c['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {c['fg']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {c['card_bg']};
                color: {c['fg']};
                selection-background-color: {c['accent']};
            }}
            QScrollBar:vertical {{
                background-color: {c['bg']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {c['border']};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {c['text_secondary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QTabWidget::pane {{
                border: 1px solid {c['border']};
                border-radius: 4px;
                background-color: {c['card_bg']};
            }}
            QTabBar::tab {{
                background-color: {c['bg']};
                color: {c['text_secondary']};
                padding: 8px 16px;
                border: 1px solid {c['border']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {c['card_bg']};
                color: {c['fg']};
            }}
            QCheckBox {{
                color: {c['fg']};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {c['border']};
                border-radius: 3px;
                background-color: {c['card_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {c['accent']};
                border-color: {c['accent']};
            }}
            QLabel {{
                color: {c['fg']};
            }}
            QListWidget, QTreeWidget {{
                background-color: {c['card_bg']};
                color: {c['fg']};
                border: 1px solid {c['border']};
                border-radius: 4px;
            }}
            QListWidget::item:selected, QTreeWidget::item:selected {{
                background-color: {c['accent']};
                color: white;
            }}
            QProgressBar {{
                border: 1px solid {c['border']};
                border-radius: 4px;
                text-align: center;
                background-color: {c['card_bg']};
            }}
            QProgressBar::chunk {{
                background-color: {c['accent']};
                border-radius: 3px;
            }}
        """
