from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt


class BackupDestinationDialog(QDialog):
    """Dialog to choose backup destination: System (custom path), Server (cloud), or Installation directory."""

    CHOICE_SYSTEM = "system"
    CHOICE_SERVER = "server"
    CHOICE_EMAIL = "email"
    CHOICE_INSTALL_DIR = "install_dir"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_choice = None
        self.setWindowTitle("انتخاب محل ذخیره‌سازی فایل پشتیبان")
        self.setFixedWidth(540)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        lbl_title = QLabel("💾 ایجاد نسخه پشتیبان جدید")
        lbl_title.setObjectName("h1")
        layout.addWidget(lbl_title)

        # Subtitle
        lbl_msg = QLabel("لطفاً مقصد مورد نظر جهت ذخیره نسخه پشتیبان (پایگاه‌داده و تصاویر) را انتخاب نمایید:")
        lbl_msg.setObjectName("muted_text")
        lbl_msg.setWordWrap(True)
        layout.addWidget(lbl_msg)

        layout.addSpacing(6)

        # ----------------------------------------------------
        # Option 1: Save to Custom System Path
        # ----------------------------------------------------
        btn_system = self._create_option_button(
            title="💻 ذخیره در سیستم",
            description="انتخاب پوشه دلخواه در حافظه سیستم (دسکتاپ، فلش مموری، درایو دیگر و...)",
            bg_color="#059669",
            hover_color="#047857"
        )
        btn_system.clicked.connect(lambda: self._select_choice(self.CHOICE_SYSTEM))
        layout.addWidget(btn_system)

        # ----------------------------------------------------
        # Option 2: Save to Cloud Server
        # ----------------------------------------------------
        btn_server = self._create_option_button(
            title="☁️ ذخیره در سرور ابری (آنلاین)",
            description="ارسال مستقیم و امن فایل پشتیبان به سرور ابری نِمُو جهت حفاظت در برابر خرابی سیستم",
            bg_color="#2563EB",
            hover_color="#1D4ED8"
        )
        btn_server.clicked.connect(lambda: self._select_choice(self.CHOICE_SERVER))
        layout.addWidget(btn_server)

        # ----------------------------------------------------
        # Option 3: Send directly to Coach Email
        # ----------------------------------------------------
        btn_email = self._create_option_button(
            title="📧 ارسال به ایمیل مربی",
            description="ارسال مستقیم و امن فایل پایگاه‌داده (.db) به آدرس ایمیل ثبت‌شده مربی باشگاه",
            bg_color="#0D9488",
            hover_color="#0F766E"
        )
        btn_email.clicked.connect(lambda: self._select_choice(self.CHOICE_EMAIL))
        layout.addWidget(btn_email)

        # ----------------------------------------------------
        # Option 4: Save to Default Installation Directory
        # ----------------------------------------------------
        btn_install_dir = self._create_option_button(
            title="📁 ذخیره در مسیر نصب برنامه",
            description="ذخیره خودکار در پوشه پیش‌فرض آرشیو نرم‌افزار (پوشه data/backups)",
            bg_color="#4F46E5",
            hover_color="#4338CA"
        )
        btn_install_dir.clicked.connect(lambda: self._select_choice(self.CHOICE_INSTALL_DIR))
        layout.addWidget(btn_install_dir)

        layout.addSpacing(6)

        # ----------------------------------------------------
        # Spam Guide Link
        # ----------------------------------------------------
        btn_help_spam = QPushButton("💡 راهنمای دریافت ایمیل در اینباکس (خروج از پوشه هرزنامه)")
        btn_help_spam.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_help_spam.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #38BDF8;
                border: none;
                font-size: 11px;
                text-decoration: underline;
                padding: 4px;
            }
            QPushButton:hover {
                color: #7DD3FC;
            }
        """)
        btn_help_spam.clicked.connect(self._open_spam_guide)
        layout.addWidget(btn_help_spam, alignment=Qt.AlignmentFlag.AlignCenter)

        # ----------------------------------------------------
        # Cancel Button
        # ----------------------------------------------------
        btn_cancel = QPushButton("انصراف و بستن")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel, alignment=Qt.AlignmentFlag.AlignCenter)

    def _open_spam_guide(self):
        from nemov.views.components.email_spam_guide_dialog import EmailSpamGuideDialog
        EmailSpamGuideDialog(self).exec()

    def _create_option_button(self, title: str, description: str, bg_color: str, hover_color: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(66)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: #FFFFFF;
                border-radius: 8px;
                border: none;
                text-align: right;
                padding: 10px 16px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)

        # Custom layout inside button for Title + Description
        btn_layout = QVBoxLayout(btn)
        btn_layout.setContentsMargins(12, 6, 12, 6)
        btn_layout.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lbl_t.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF; background: transparent; font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;")

        lbl_d = QLabel(description)
        lbl_d.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lbl_d.setStyleSheet("font-size: 11px; color: #E0E7FF; background: transparent;")

        btn_layout.addWidget(lbl_t)
        btn_layout.addWidget(lbl_d)

        return btn

    def _select_choice(self, choice: str):
        self.selected_choice = choice
        self.accept()
