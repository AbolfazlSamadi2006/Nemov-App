from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from nemov.utils.theme_manager import ThemeManager

class StatCard(QFrame):
    """Modern Dashboard Stat Card Widget with Dynamic Multi-Theme Support"""
    def __init__(self, title: str, value: str, subtitle: str = "", icon: str = "📊", accent_color: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._custom_accent = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        
        self.lbl_title = QLabel(title)
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setStyleSheet("font-size: 20px; background: transparent;")
        
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_icon)

        self.lbl_value = QLabel(value)

        layout.addLayout(header_layout)
        layout.addWidget(self.lbl_value)

        # Wire live theme listener
        try:
            ThemeManager.theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

        self._apply_theme_style()

    def _on_theme_changed(self, theme_key: str):
        self._apply_theme_style()

    def _apply_theme_style(self):
        try:
            palette = ThemeManager.get_current_palette()
        except Exception:
            return

        accent = self._custom_accent if self._custom_accent else palette.primary

        self.setStyleSheet(f"""
            QFrame#{self.objectName()} {{
                background-color: {palette.bg_card};
                border: 1px solid {palette.border};
                border-right: 4px solid {accent};
                border-radius: 8px;
                padding: 12px;
            }}
            QLabel {{
                background: transparent;
                background-color: transparent;
            }}
        """)
        if hasattr(self, "lbl_title") and self.lbl_title:
            self.lbl_title.setStyleSheet(f"color: {palette.text_secondary}; font-size: 13px; font-weight: bold; background: transparent;")
        if hasattr(self, "lbl_value") and self.lbl_value:
            self.lbl_value.setStyleSheet(f"color: {palette.text_primary}; font-size: 28px; font-weight: bold; margin-top: 4px; background: transparent;")

    def set_value(self, value: str):
        self.lbl_value.setText(str(value))

    def set_custom_accent(self, color: str):
        """Allows specific domain widgets (e.g. accounting) to override the accent bar while inheriting palette surfaces."""
        self._custom_accent = color
        self._apply_theme_style()

    def set_subtitle(self, subtitle: str):
        pass
