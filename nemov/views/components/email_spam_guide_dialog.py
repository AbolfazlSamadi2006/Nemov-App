from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, QTimer
import config
from nemov.utils.theme_manager import ThemeManager


class EmailSpamGuideDialog(QDialog):
    """
    Dialog providing step-by-step visual guidance to coaches on how to whitelist
    the application's support email and move messages from the Spam folder to the Inbox.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("راهنمای انتقال ایمیل‌ها به صندوق اصلی (خروج از اسپم)")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        screen = QApplication.primaryScreen()
        avail_h = screen.availableGeometry().height() if screen else 800
        self.setFixedSize(640, min(680, max(520, avail_h - 36)))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        palette = ThemeManager.get_current_palette()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content_widget = QFrame()
        content_widget.setFixedWidth(570)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 8, 15, 8)
        content_layout.setSpacing(14)

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------
        header_card = QFrame()
        header_card.setStyleSheet(f"""
            QFrame {{
                background-color: {palette.bg_surface};
                border: 1px solid {palette.border};
                border-radius: 10px;
                padding: 14px;
            }}
        """)
        h_layout = QVBoxLayout(header_card)
        h_layout.setSpacing(6)

        title_lbl = QLabel("🛡️ راهنمای دریافت ایمیل‌ها در صندوق اصلی (Inbox)")
        title_lbl.setStyleSheet(f"color: {palette.primary}; font-size: 16px; font-weight: bold;")
        h_layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "به دلیل سیاست‌های امنیتی و ضداسپم جدید گوگل، ایمیل‌های خودکار حاوی فایل پشتیبان یا کد تایید "
            "ممکن است در اولین مرتبه به پوشه <b>Spam (هرزنامه)</b> ارسال شوند.<br><br>"
            "با انجام یکی از دو راهکار ساده زیر (فقط برای <b>یک‌بار</b>)، تمام ایمیل‌های بعدی مستقیماً به <b>Inbox (صندوق اصلی)</b> شما خواهند آمد:"
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {palette.text_secondary}; font-size: 12px; line-height: 1.7;")
        h_layout.addWidget(desc_lbl)

        content_layout.addWidget(header_card)

        # ----------------------------------------------------
        # Method 1: Report Not Spam (Web & Mobile)
        # ----------------------------------------------------
        method1_card = QFrame()
        method1_card.setObjectName("card")
        m1_layout = QVBoxLayout(method1_card)
        m1_layout.setSpacing(10)

        m1_title = QLabel("⭐ روش اول (سریع‌ترین راه): گزارش به‌عنوان هرزنامه نیست")
        m1_title.setStyleSheet("color: #10B981; font-size: 14px; font-weight: bold;")
        m1_layout.addWidget(m1_title)

        # Web Gmail instructions
        web_box = QFrame()
        web_box.setStyleSheet("background-color: #242427; border-radius: 8px; padding: 10px;")
        web_layout = QVBoxLayout(web_box)
        web_layout.setSpacing(4)
        lbl_web_head = QLabel("💻 در نسخه وب جیمیل (کامپیوتر یا مرورگر):")
        lbl_web_head.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 12px;")
        web_layout.addWidget(lbl_web_head)

        lbl_web_steps = QLabel(
            "۱. در منوی سمت راست (یا چپ) جیمیل وارد پوشه <b>Spam (هرزنامه)</b> شوید.<br>"
            "۲. ایمیل ارسالی از <b>باشگاه ورزشی یلدا</b> را باز کنید.<br>"
            "۳. در بالای صفحه روی دکمه خاکستری <b>«گزارش به‌عنوان هرزنامه نیست» (Report not spam)</b> کلیک نمایید.<br>"
            "← ایمیل فوراً به صندوق اصلی منتقل شده و دفعات بعد نیز به Inbox می‌رود."
        )
        lbl_web_steps.setWordWrap(True)
        lbl_web_steps.setStyleSheet("color: #E2E8F0; font-size: 12px; line-height: 1.8;")
        web_layout.addWidget(lbl_web_steps)
        m1_layout.addWidget(web_box)

        # Mobile Gmail instructions
        mobile_box = QFrame()
        mobile_box.setStyleSheet("background-color: #242427; border-radius: 8px; padding: 10px;")
        mobile_layout = QVBoxLayout(mobile_box)
        mobile_layout.setSpacing(4)
        lbl_mob_head = QLabel("📱 در برنامه جیمیل گوشی (اندروید یا آیفون):")
        lbl_mob_head.setStyleSheet("color: #F472B6; font-weight: bold; font-size: 12px;")
        mobile_layout.addWidget(lbl_mob_head)

        lbl_mob_steps = QLabel(
            "۱. منوی سه‌خط بالای جیمیل را باز کرده و به بخش <b>Spam</b> بروید.<br>"
            "۲. ایمیل ارسال‌شده را باز کنید.<br>"
            "۳. روی آیکون <b>سه نقطه (⋮)</b> در گوشه بالا بزنید و گزینه <b>«گزارش به‌عنوان هرزنامه نیست» (Report not spam)</b> یا <b>«انتقال به صندوق ورودی» (Move to inbox)</b> را انتخاب کنید."
        )
        lbl_mob_steps.setWordWrap(True)
        lbl_mob_steps.setStyleSheet("color: #E2E8F0; font-size: 12px; line-height: 1.8;")
        mobile_layout.addWidget(lbl_mob_steps)
        m1_layout.addWidget(mobile_box)

        content_layout.addWidget(method1_card)

        # ----------------------------------------------------
        # Method 2: Add to Google Contacts (Guaranteed)
        # ----------------------------------------------------
        method2_card = QFrame()
        method2_card.setObjectName("card")
        m2_layout = QVBoxLayout(method2_card)
        m2_layout.setSpacing(10)

        m2_title = QLabel("🔒 روش دوم (تضمینی و دائمی): افزودن ایمیل نرم‌افزار به مخاطبین")
        m2_title.setStyleSheet("color: #FBBF24; font-size: 14px; font-weight: bold;")
        m2_layout.addWidget(m2_title)

        lbl_m2_desc = QLabel(
            "طبق قوانین رسمی گوگل، تمامی ایمیل‌های ارسالی از آدرس‌هایی که در لیست مخاطبین شما باشند، "
            "<b>۱۰۰٪ و بدون استثنا</b> مستقیماً به صندوق اصلی (Inbox) تحویل داده می‌شوند."
        )
        lbl_m2_desc.setWordWrap(True)
        lbl_m2_desc.setStyleSheet(f"color: {palette.text_secondary}; font-size: 12px; line-height: 1.7;")
        m2_layout.addWidget(lbl_m2_desc)

        # Support email display and Copy button
        email_addr = getattr(config, "SUPPORT_EMAIL_ADDRESS", "gymassistantapp.support@gmail.com")
        email_row = QHBoxLayout()
        email_row.setSpacing(8)

        lbl_email_box = QLabel(email_addr)
        lbl_email_box.setFixedHeight(36)
        lbl_email_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_email_box.setStyleSheet(f"""
            background-color: {palette.bg_input};
            color: {palette.primary};
            border: 1px dashed {palette.primary};
            border-radius: 6px;
            font-family: Consolas, monospace;
            font-size: 13px;
            font-weight: bold;
            padding: 0 12px;
        """)
        email_row.addWidget(lbl_email_box, 1)

        self.btn_copy_email = QPushButton("📋 کپی آدرس")
        self.btn_copy_email.setFixedHeight(36)
        self.btn_copy_email.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_email.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_copy_email.clicked.connect(lambda: self._copy_email_to_clipboard(email_addr))
        email_row.addWidget(self.btn_copy_email)

        m2_layout.addLayout(email_row)

        lbl_m2_tip = QLabel("کافیست نشانی بالا را در مخاطبین گوشی خود با عنوان «پشتیبانی باشگاه یلدا» ذخیره فرمایید.")
        lbl_m2_tip.setStyleSheet(f"color: {palette.text_muted}; font-size: 11px;")
        m2_layout.addWidget(lbl_m2_tip)

        content_layout.addWidget(method2_card)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # ----------------------------------------------------
        # Close Button
        # ----------------------------------------------------
        btn_close = QPushButton("متوجه شدم و بستن")
        btn_close.setFixedHeight(40)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setObjectName("primary_button")
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close)

    def _copy_email_to_clipboard(self, email_addr: str):
        clipboard = QApplication.clipboard()
        clipboard.setText(email_addr)
        self.btn_copy_email.setText("✅ کپی شد!")
        self.btn_copy_email.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 14px;
            }
        """)
        QTimer.singleShot(2500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self.btn_copy_email.setText("📋 کپی آدرس")
        self.btn_copy_email.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
