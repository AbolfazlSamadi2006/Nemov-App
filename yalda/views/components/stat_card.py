from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout

class StatCard(QFrame):
    """Modern Dashboard Stat Card Widget with Dark Red Accent"""
    def __init__(self, title: str, value: str, subtitle: str = "", icon: str = "📊", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet("""
            QFrame#card {
                background-color: #1E1E1E;
                border: 1px solid #2E2E2E;
                border-right: 4px solid #8B0000;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel {
                background: transparent;
                background-color: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #A0A0A0; font-size: 13px; font-weight: bold; background: transparent;")
        
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 20px; background: transparent;")
        
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(lbl_icon)

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet("color: #FFFFFF; font-size: 28px; font-weight: bold; margin-top: 4px; background: transparent;")

        layout.addLayout(header_layout)
        layout.addWidget(self.lbl_value)

    def set_value(self, value: str):
        self.lbl_value.setText(str(value))

    def set_subtitle(self, subtitle: str):
        pass
