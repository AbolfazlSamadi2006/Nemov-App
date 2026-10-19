import re
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QTabWidget, QRadioButton, QButtonGroup, QCheckBox, QAbstractItemView,
    QProgressBar, QScrollArea, QDialog, QSizePolicy, QApplication, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont

import config
from yalda.services.sms_service import SmsService, DEFAULT_SMS_TEMPLATES
from yalda.services.member_service import MemberService
from yalda.database.connection import SessionLocal
from yalda.models.database_models import Member, SystemSetting
from yalda.utils.jalali_date import get_today_shamsi


class SmsBalanceThread(QThread):
    finished_signal = pyqtSignal(dict)

    def run(self):
        res = SmsService.get_balance()
        self.finished_signal.emit(res)


class SmsHistoryThread(QThread):
    finished_signal = pyqtSignal(list)

    def run(self):
        logs = SmsService.get_history()
        self.finished_signal.emit(logs)


class SmsSendBatchThread(QThread):
    progress_signal = pyqtSignal(int, int, str) # current, total, member_name
    finished_signal = pyqtSignal(int, int, int) # success_count, fail_count, final_balance

    def __init__(self, recipients, template_id, parameters_builder, message_text, message_type):
        super().__init__()
        self.recipients = recipients # list of dict: { phone, name }
        self.template_id = template_id
        self.parameters_builder = parameters_builder
        self.message_text = message_text
        self.message_type = message_type

    def run(self):
        success_count = 0
        fail_count = 0
        rem_balance = 0
        total = len(self.recipients)

        for idx, rec in enumerate(self.recipients):
            p_phone = rec.get("phone", "")
            p_name = rec.get("name", "ورزشکار")
            params = self.parameters_builder(p_name) if self.parameters_builder else []

            self.progress_signal.emit(idx + 1, total, p_name)
            ok, msg, rem = SmsService.send_single_sms(
                recipient_phone=p_phone,
                template_id=self.template_id,
                parameters=params,
                message_text=self.message_text.replace("#NAME#", p_name),
                member_name=p_name,
                message_type=self.message_type
            )
            rem_balance = rem
            if ok:
                success_count += 1
            else:
                fail_count += 1
                if rem <= 0 and "اعتبار" in msg:
                    break # Stop when completely depleted

        self.finished_signal.emit(success_count, fail_count, rem_balance)


class RechargeInfoDialog(QDialog):
    """Modal dialog displaying instructions for recharging SMS balance via card-to-card."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ راهنمای خرید و شارژ بسته پیامک")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(580, 570)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("💳 تعرفه بسته‌ها و اطلاعات واریز کارت‌به‌کارت")
        title.setObjectName("h2")
        layout.addWidget(title)

        desc = QLabel(
            "جهت شارژ اعتبار پیامک، مربی گرامی می‌تواند یکی از بسته‌های زیر را انتخاب و مبلغ آن را واریز نماید. "
            "مشخصات شما با اتصال اینترنت به صورت خودکار در سامانه ثبت می‌شود و پس از واریز فعال خواهد شد:"
        )
        desc.setWordWrap(True)
        desc.setObjectName("muted_text")
        layout.addWidget(desc)

        # Packages Card
        pkg_card = QFrame()
        pkg_card.setObjectName("card")
        pkg_layout = QVBoxLayout(pkg_card)
        pkg_layout.setContentsMargins(16, 12, 16, 12)
        pkg_layout.setSpacing(8)

        packages = [
            ("🥉 بسته برنزی: ۱۰۰ پیامک خدماتی", "۳۰,۰۰۰ تومان"),
            ("🥈 بسته نقره‌ای: ۲۵۰ پیامک خدماتی", "۷۵,۰۰۰ تومان"),
            ("🥇 بسته طلایی: ۵۰۰ پیامک خدماتی", "۱۵۰,۰۰۰ تومان"),
            ("💎 بسته الماس: ۱۰۰۰ پیامک خدماتی", "۳۰۰,۰۰۰ تومان"),
        ]
        for title_txt, price_txt in packages:
            row = QHBoxLayout()
            lbl_title = QLabel(title_txt)
            lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #F3F4F6;")
            lbl_price = QLabel(price_txt)
            lbl_price.setStyleSheet("font-size: 13px; font-weight: bold; color: #34D399;")
            row.addWidget(lbl_title)
            row.addStretch()
            row.addWidget(lbl_price)
            pkg_layout.addLayout(row)

        layout.addWidget(pkg_card)

        # Bank & Contact Card with Copy Buttons
        bank_card = QFrame()
        bank_card.setObjectName("bankCard")
        bank_card.setStyleSheet("""
            QFrame#bankCard {
                background-color: #121826;
                border: 1px solid #1D4ED8;
                border-radius: 8px;
            }
        """)
        bank_layout = QVBoxLayout(bank_card)
        bank_layout.setContentsMargins(16, 12, 16, 12)
        bank_layout.setSpacing(10)

        # Card row
        card_row = QHBoxLayout()
        card_row.setSpacing(8)
        lbl_card_title = QLabel("💳 شماره کارت:")
        lbl_card_title.setStyleSheet("color: #93C5FD; font-size: 12px; font-weight: bold;")
        lbl_card_val = QLabel("6280 - 2313 - 2802 - 6199")
        lbl_card_val.setStyleSheet("color: #FCD34D; font-family: monospace; font-size: 14px; font-weight: bold; direction: ltr;")
        self.btn_copy_card = QPushButton("📋 کپی شماره کارت")
        self.btn_copy_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_card.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #E2E8F0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_copy_card.clicked.connect(lambda: self.copy_to_clipboard("6280231328026199", self.btn_copy_card, "📋 کپی شماره کارت"))
        card_row.addWidget(lbl_card_title)
        card_row.addWidget(lbl_card_val)
        card_row.addStretch()
        card_row.addWidget(self.btn_copy_card)
        bank_layout.addLayout(card_row)

        # Phone row
        phone_row = QHBoxLayout()
        phone_row.setSpacing(8)
        lbl_phone_title = QLabel("📞 تماس و پیامک:")
        lbl_phone_title.setStyleSheet("color: #93C5FD; font-size: 12px; font-weight: bold;")
        lbl_phone_val = QLabel("09336427711")
        lbl_phone_val.setStyleSheet("color: #6EE7B7; font-family: monospace; font-size: 14px; font-weight: bold; direction: ltr;")
        self.btn_copy_phone = QPushButton("📋 کپی شماره تماس")
        self.btn_copy_phone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_phone.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #E2E8F0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_copy_phone.clicked.connect(lambda: self.copy_to_clipboard("09336427711", self.btn_copy_phone, "📋 کپی شماره تماس"))
        phone_row.addWidget(lbl_phone_title)
        phone_row.addWidget(lbl_phone_val)
        phone_row.addStretch()
        phone_row.addWidget(self.btn_copy_phone)
        bank_layout.addLayout(phone_row)

        layout.addWidget(bank_card)

        # Contact Info & Notice
        contact_card = QFrame()
        contact_card.setObjectName("contactCard")
        contact_card.setStyleSheet("""
            QFrame#contactCard {
                background-color: #18181B;
                border: 1px dashed #6366F1;
                border-radius: 8px;
            }
        """)
        contact_layout = QVBoxLayout(contact_card)
        contact_layout.setContentsMargins(14, 10, 14, 10)
        contact_layout.setSpacing(6)
        phone = SmsService.get_trainer_phone() or "شماره ثبت‌نشده"
        name = SmsService.get_trainer_name()
        lbl_acc = QLabel(f"📱 شناسه شما در سامانه پیامکی: {phone} ({name})")
        lbl_acc.setStyleSheet("color: #818CF8; font-weight: bold; background: transparent; border: none; font-size: 12px;")
        lbl_notice = QLabel("⚡ پس از واریز، تصویر فیش را ارسال فرمایید یا جهت شارژ سریع‌تر با پیامک یا تماس اطلاع دهید.")
        lbl_notice.setStyleSheet("color: #FCD34D; font-weight: bold; background: transparent; border: none; font-size: 12px;")
        lbl_notice.setWordWrap(True)
        contact_layout.addWidget(lbl_acc)
        contact_layout.addWidget(lbl_notice)
        layout.addWidget(contact_card)

        layout.addStretch()

        btn_close = QPushButton("متوجه شدم")
        btn_close.setObjectName("primary_button")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

    def copy_to_clipboard(self, text: str, btn: QPushButton, original_text: str):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
        btn.setText("کپی شد! ✅")
        btn.setStyleSheet("background-color: #065F46; color: #6EE7B7; border: 1px solid #059669; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: bold;")
        QTimer.singleShot(2000, lambda: self.reset_copy_btn(btn, original_text))

    def reset_copy_btn(self, btn: QPushButton, original_text: str):
        btn.setText(original_text)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #E2E8F0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)


class SmsView(QWidget):
    """
    Main SMS Center view providing wallet balance, broadcast notices,
    holiday announcements, template preview, and automated rules.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._balance_data = {"remaining": 0, "status": "unknown"}
        self._all_members = []
        self._selected_member_ids = set()

        self.init_ui()
        self.load_members()
        self.refresh_balance()
        self.load_auto_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # =====================================================================
        # 1. Header & Wallet Status Card
        # =====================================================================
        header_frame = QFrame()
        header_frame.setObjectName("card")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(16)

        # Title & Description
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        lbl_title = QLabel("📱 سامانه هوشمند پیامک و اطلاع‌رسانی باشگاه")
        lbl_title.setObjectName("h1")
        lbl_sub = QLabel("ارسال پیام‌های گروهی، اعلام تعطیلی باشگاه و ارسال خودکار پیام‌های تبریک تولد و شهریه")
        lbl_sub.setObjectName("muted_text")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_layout.addLayout(title_box, 1)

        # Wallet Info
        wallet_box = QHBoxLayout()
        wallet_box.setSpacing(14)

        self.card_balance = QFrame()
        self.card_balance.setObjectName("cardBalance")
        from yalda.utils.theme_manager import ThemeManager
        palette = ThemeManager.get_current_palette()
        self.card_balance.setStyleSheet(f"""
            QFrame#cardBalance {{
                background-color: {palette.bg_surface};
                border: 1px solid {palette.border_light};
                border-radius: 8px;
            }}
        """)
        cb_layout = QVBoxLayout(self.card_balance)
        cb_layout.setContentsMargins(16, 8, 16, 8)
        cb_layout.setSpacing(2)
        lbl_b_caption = QLabel("اعتبار پیامک باقیمانده")
        lbl_b_caption.setStyleSheet("font-size: 11px; color: #93C5FD; background: transparent; border: none;")
        self.lbl_balance_val = QLabel("در حال دریافت...")
        self.lbl_balance_val.setStyleSheet("font-size: 17px; font-weight: bold; color: #60A5FA; background: transparent; border: none;")
        cb_layout.addWidget(lbl_b_caption)
        cb_layout.addWidget(self.lbl_balance_val)
        wallet_box.addWidget(self.card_balance)

        # Refresh & Recharge Buttons
        btn_box = QVBoxLayout()
        btn_box.setSpacing(6)

        self.btn_refresh_bal = QPushButton("🔄 به‌روزرسانی موجودی")
        self.btn_refresh_bal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh_bal.setStyleSheet("""
            QPushButton {
                background-color: #27272A;
                color: #FFFFFF;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3F3F46;
            }
        """)
        self.btn_refresh_bal.clicked.connect(self.refresh_balance)

        self.btn_buy_pkg = QPushButton("⚡ شارژ بسته پیامکی")
        self.btn_buy_pkg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_buy_pkg.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        self.btn_buy_pkg.clicked.connect(self.show_recharge_dialog)

        btn_box.addWidget(self.btn_refresh_bal)
        btn_box.addWidget(self.btn_buy_pkg)
        wallet_box.addLayout(btn_box)

        header_layout.addLayout(wallet_box)
        main_layout.addWidget(header_frame)

        # =====================================================================
        # 2. Main Tab Widget
        # =====================================================================
        self.tabs = QTabWidget()

        self.tab_broadcast = QScrollArea()
        self.tab_broadcast.setWidgetResizable(True)
        self.tab_broadcast.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.tab_automated = QScrollArea()
        self.tab_automated.setWidgetResizable(True)
        self.tab_automated.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.tab_history = QWidget()

        self.setup_broadcast_tab()
        self.setup_automated_tab()
        self.setup_history_tab()

        self.tabs.addTab(self.tab_broadcast, "🚀  ارسال پیامک جدید و تعطیلی باشگاه")
        self.tabs.addTab(self.tab_automated, "⚙️  تنظیمات ارسال خودکار (خوش‌آمدگویی، تولد و شهریه)")
        self.tabs.addTab(self.tab_history, "📜  تاریخچه پیامک‌های ارسالی")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        main_layout.addWidget(self.tabs, 1)

    # =========================================================================
    # Tab 1: Broadcast & Manual SMS
    # =========================================================================
    def setup_broadcast_tab(self):
        container = QWidget()
        container.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(14)

        # Right Column: Editor & Members Selection
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)

        # 1. Template Selector
        tpl_row = QHBoxLayout()
        lbl_tpl = QLabel("انتخاب الگوی پیامک:")
        lbl_tpl.setStyleSheet("font-weight: bold; font-size: 13px; color: #FFFFFF;")
        self.combo_templates = QComboBox()
        self.combo_templates.setStyleSheet("""
            QComboBox {
                background-color: #27272A;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                color: #FFFFFF;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        self.combo_templates.addItem("🏖️  اعلام تعطیلی باشگاه (الگوی تاییدشده ۱۴۶۸۷۷)", "holiday")
        self.combo_templates.addItem("⏰  تغییر ساعت و سانس‌های باشگاه (الگوی تاییدشده ۳۸۵۰۰۳)", "hours")
        self.combo_templates.currentIndexChanged.connect(self.on_template_changed)
        tpl_row.addWidget(lbl_tpl)
        tpl_row.addWidget(self.combo_templates, 1)
        right_panel.addLayout(tpl_row)

        # 2. Dynamic Input Fields for template
        self.dynamic_frame = QFrame()
        self.dynamic_frame.setObjectName("card")
        self.dyn_layout = QVBoxLayout(self.dynamic_frame)
        self.dyn_layout.setContentsMargins(12, 8, 12, 8)
        self.dyn_layout.setSpacing(8)

        try:
            from yalda.utils.theme_manager import ThemeManager
            _pal = ThemeManager.get_current_palette()
        except Exception:
            _pal = None
        _chip_hover_border = _pal.primary if _pal else "#DC2626"

        chip_btn_style = f"""
            QPushButton {{
                background-color: #27272A;
                color: #D1D5DB;
                border: 1px solid #3F3F46;
                border-radius: 11px;
                padding: 3px 9px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #3F3F46;
                color: #FFFFFF;
                border-color: {_chip_hover_border};
            }}
        """

        # ---------------------------------------------------------------------
        # Panel 1: Holiday
        # ---------------------------------------------------------------------
        self.panel_holiday = QWidget()
        l_hol = QVBoxLayout(self.panel_holiday)
        l_hol.setContentsMargins(0, 0, 0, 0)
        l_hol.setSpacing(8)

        hol_row1 = QHBoxLayout()
        hol_row1.setSpacing(10)

        col_date = QVBoxLayout()
        col_date.setSpacing(4)
        lbl_dyn_date = QLabel("📅 تاریخ تعطیلی:")
        lbl_dyn_date.setStyleSheet("font-size: 11px; font-weight: bold; color: #D1D5DB;")
        self.input_dyn_date = QLineEdit()
        self.input_dyn_date.setPlaceholderText("مثال: فردا چهارشنبه ۲ مهر یا ۲ الی ۴ مهر")
        self.input_dyn_date.setText(f"امروز ({get_today_shamsi()})")
        self.input_dyn_date.textChanged.connect(self.update_preview)
        col_date.addWidget(lbl_dyn_date)
        col_date.addWidget(self.input_dyn_date)

        col_reason = QVBoxLayout()
        col_reason.setSpacing(4)
        lbl_dyn_reason = QLabel("🛑 علت تعطیلی باشگاه:")
        lbl_dyn_reason.setStyleSheet("font-size: 11px; font-weight: bold; color: #D1D5DB;")
        self.input_dyn_reason = QLineEdit()
        self.input_dyn_reason.setPlaceholderText("مثال: تعطیلات رسمی / تعمیرات سالن و سرویس تجهیزات")
        self.input_dyn_reason.setText("تعطیلات رسمی")
        self.input_dyn_reason.textChanged.connect(self.update_preview)
        col_reason.addWidget(lbl_dyn_reason)
        col_reason.addWidget(self.input_dyn_reason)

        hol_row1.addLayout(col_date, 1)
        hol_row1.addLayout(col_reason, 1)
        l_hol.addLayout(hol_row1)

        hol_chips_row = QHBoxLayout()
        hol_chips_row.setSpacing(6)
        lbl_hol_chips = QLabel("علت‌های پرتکرار:")
        lbl_hol_chips.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        hol_chips_row.addWidget(lbl_hol_chips)

        for r_chip_text, r_chip_val in [
            ("تعطیلات رسمی", "تعطیلات رسمی"),
            ("تعمیرات سالن", "تعمیرات سالن و بهسازی"),
            ("سرویس تجهیزات", "سرویس دوره‌ای تجهیزات و دستگاه‌ها"),
            ("برودت هوا", "برودت هوا و یخبندان معابر"),
            ("ایام سوگواری", "ایام سوگواری رسمی"),
        ]:
            btn_c = QPushButton(r_chip_text)
            btn_c.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_c.setStyleSheet(chip_btn_style)
            btn_c.clicked.connect(lambda _, v=r_chip_val: self.set_holiday_reason_preset(v))
            hol_chips_row.addWidget(btn_c)

        hol_chips_row.addStretch()
        l_hol.addLayout(hol_chips_row)
        self.dyn_layout.addWidget(self.panel_holiday)

        # ---------------------------------------------------------------------
        # ---------------------------------------------------------------------
        # Panel 2: Working Hours (Template ID: 385003)
        # ---------------------------------------------------------------------
        self.panel_hours = QWidget()
        l_hours = QVBoxLayout(self.panel_hours)
        l_hours.setContentsMargins(0, 0, 0, 0)
        l_hours.setSpacing(8)

        hours_row1 = QHBoxLayout()
        hours_row1.setSpacing(10)

        col_h_days = QVBoxLayout()
        col_h_days.setSpacing(4)
        lbl_h_days = QLabel("🗓️ روزها:")
        lbl_h_days.setStyleSheet("font-size: 11px; font-weight: bold; color: #D1D5DB;")
        self.combo_hours_days = QComboBox()
        self.combo_hours_days.setEditable(True)
        self.combo_hours_days.setStyleSheet("QComboBox { background-color: #27272A; border: 1px solid #3F3F46; border-radius: 6px; color: #FFFFFF; padding: 5px 8px; font-size: 12px; }")
        for day_opt in [
            "شنبه تا پنجشنبه",
            "همه روزه (شنبه تا پنجشنبه)",
            "شنبه، دوشنبه، چهارشنبه",
            "یکشنبه، سه‌شنبه، پنجشنبه",
            "جمعه‌ها و روزهای تعطیل",
        ]:
            self.combo_hours_days.addItem(day_opt)
        self.combo_hours_days.currentTextChanged.connect(self.update_preview)
        col_h_days.addWidget(lbl_h_days)
        col_h_days.addWidget(self.combo_hours_days)

        col_h_women = QVBoxLayout()
        col_h_women.setSpacing(4)
        lbl_h_women = QLabel("👩 سانس بانوان:")
        lbl_h_women.setStyleSheet("font-size: 11px; font-weight: bold; color: #F472B6;")
        self.combo_hours_women = QComboBox()
        self.combo_hours_women.setEditable(True)
        self.combo_hours_women.setStyleSheet("QComboBox { background-color: #27272A; border: 1px solid #3F3F46; border-radius: 6px; color: #FFFFFF; padding: 5px 8px; font-size: 12px; }")
        for w_opt in [
            "۸ الی ۱۲ و ۱۵ الی ۱۹",
            "۰۸:۰۰ الی ۱۲:۰۰ و ۱۵:۰۰ الی ۱۹:۰۰",
            "۰۸:۰۰ الی ۱۲:۰۰ (صبح)",
            "۱۵:۰۰ الی ۱۹:۰۰ (عصر)",
            "بدون تغییر",
        ]:
            self.combo_hours_women.addItem(w_opt)
        self.combo_hours_women.setCurrentText("۸ الی ۱۲ و ۱۵ الی ۱۹")
        self.combo_hours_women.currentTextChanged.connect(self.update_preview)
        col_h_women.addWidget(lbl_h_women)
        col_h_women.addWidget(self.combo_hours_women)

        col_h_men = QVBoxLayout()
        col_h_men.setSpacing(4)
        lbl_h_men = QLabel("👨 سانس آقایان:")
        lbl_h_men.setStyleSheet("font-size: 11px; font-weight: bold; color: #60A5FA;")
        self.combo_hours_men = QComboBox()
        self.combo_hours_men.setEditable(True)
        self.combo_hours_men.setStyleSheet("QComboBox { background-color: #27272A; border: 1px solid #3F3F46; border-radius: 6px; color: #FFFFFF; padding: 5px 8px; font-size: 12px; }")
        for m_opt in [
            "۱۲ الی ۱۵ و ۱۹ الی ۲۳",
            "۱۲:۰۰ الی ۱۵:۰۰ و ۱۹:۰۰ الی ۲۳:۰۰",
            "۱۲:۰۰ الی ۱۵:۰۰ (ظهر)",
            "۱۹:۰۰ الی ۲۳:۰۰ (شب)",
            "بدون تغییر",
        ]:
            self.combo_hours_men.addItem(m_opt)
        self.combo_hours_men.setCurrentText("۱۲ الی ۱۵ و ۱۹ الی ۲۳")
        self.combo_hours_men.currentTextChanged.connect(self.update_preview)
        col_h_men.addWidget(lbl_h_men)
        col_h_men.addWidget(self.combo_hours_men)

        hours_row1.addLayout(col_h_days, 2)
        hours_row1.addLayout(col_h_women, 2)
        hours_row1.addLayout(col_h_men, 2)
        l_hours.addLayout(hours_row1)

        hours_row2 = QHBoxLayout()
        hours_row2.setSpacing(10)
        lbl_h_note = QLabel("توضیحات تکمیلی (اختیاری):")
        lbl_h_note.setStyleSheet("font-size: 11px; color: #D1D5DB;")
        self.input_hours_note = QLineEdit()
        self.input_hours_note.setPlaceholderText("مثال: جمعه‌ها سالن تعطیل است / پذیرش تا ۲۱:۳۰")
        self.input_hours_note.setText("جمعه‌ها سالن تعطیل است")
        self.input_hours_note.textChanged.connect(self.update_preview)
        hours_row2.addWidget(lbl_h_note)
        hours_row2.addWidget(self.input_hours_note, 1)
        l_hours.addLayout(hours_row2)

        hours_chips_row = QHBoxLayout()
        hours_chips_row.setSpacing(6)
        lbl_hc = QLabel("تنظیم سریع:")
        lbl_hc.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        hours_chips_row.addWidget(lbl_hc)

        btn_default = QPushButton("برنامه رسمی باشگاه یلدا")
        btn_default.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_default.setStyleSheet(chip_btn_style)
        btn_default.clicked.connect(lambda: self.set_hours_preset(
            "شنبه تا پنجشنبه", "۸ الی ۱۲ و ۱۵ الی ۱۹", "۱۲ الی ۱۵ و ۱۹ الی ۲۳", "جمعه‌ها سالن تعطیل است"
        ))
        hours_chips_row.addWidget(btn_default)

        btn_women = QPushButton("تغییر سانس بانوان")
        btn_women.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_women.setStyleSheet(chip_btn_style)
        btn_women.clicked.connect(lambda: self.set_hours_preset(
            "شنبه تا پنجشنبه", "۰۸:۰۰ الی ۱۲:۰۰ و ۱۵:۰۰ الی ۱۹:۰۰", "بدون تغییر", "شیفت جدید بانوان"
        ))
        hours_chips_row.addWidget(btn_women)

        btn_men = QPushButton("تغییر سانس آقایان")
        btn_men.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_men.setStyleSheet(chip_btn_style)
        btn_men.clicked.connect(lambda: self.set_hours_preset(
            "شنبه تا پنجشنبه", "بدون تغییر", "۱۲:۰۰ الی ۱۵:۰۰ و ۱۹:۰۰ الی ۲۳:۰۰", "شیفت جدید آقایان"
        ))
        hours_chips_row.addWidget(btn_men)

        btn_friday = QPushButton("جمعه‌ها و تعطیلات")
        btn_friday.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_friday.setStyleSheet(chip_btn_style)
        btn_friday.clicked.connect(lambda: self.set_hours_preset(
            "جمعه‌ها و ایام تعطیل", "۱۰:۰۰ الی ۱۴:۰۰", "۱۴:۰۰ الی ۱۹:۰۰", "پذیرش آخرین شیفت ساعت ۱۸:۳۰"
        ))
        hours_chips_row.addWidget(btn_friday)

        hours_chips_row.addStretch()
        l_hours.addLayout(hours_chips_row)
        self.dyn_layout.addWidget(self.panel_hours)

        right_panel.addWidget(self.dynamic_frame)

        # 3. Recipients Selector
        recip_head = QHBoxLayout()
        lbl_recip = QLabel("👥 انتخاب دریافت‌کنندگان پیامک:")
        lbl_recip.setStyleSheet("font-weight: bold; font-size: 13px; color: #FFFFFF;")
        recip_head.addWidget(lbl_recip)

        # Filter buttons
        self.rb_all = QRadioButton("تمام ورزشکاران")
        self.rb_active = QRadioButton("فقط فعال")
        self.rb_custom = QRadioButton("انتخابی")
        self.rb_all.setChecked(True)
        self.rb_all.toggled.connect(self.filter_members_selection)
        self.rb_active.toggled.connect(self.filter_members_selection)
        self.rb_custom.toggled.connect(self.filter_members_selection)

        self.bg_recip = QButtonGroup(self)
        self.bg_recip.addButton(self.rb_all)
        self.bg_recip.addButton(self.rb_active)
        self.bg_recip.addButton(self.rb_custom)

        self.btn_deselect_all = QPushButton("🚫  لغو انتخاب همه")
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.setToolTip("لغو انتخاب تمام شاگردان جهت انتخاب دستی ۱ یا چند نفر")
        self.btn_deselect_all.setStyleSheet("""
            QPushButton {
                background-color: #27272A;
                color: #F87171;
                border: 1px solid #7F1D1D;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #991B1B;
                color: #FFFFFF;
                border-color: #EF4444;
            }
            QPushButton:pressed {
                background-color: #7F1D1D;
            }
        """)
        self.btn_deselect_all.clicked.connect(self.deselect_all_members)

        recip_head.addStretch()
        recip_head.addWidget(self.rb_all)
        recip_head.addWidget(self.rb_active)
        recip_head.addWidget(self.rb_custom)
        recip_head.addWidget(self.btn_deselect_all)
        right_panel.addLayout(recip_head)

        # Search Bar
        self.input_search_member = QLineEdit()
        self.input_search_member.setPlaceholderText("🔍 جستجوی نام یا شماره ورزشکار...")
        self.input_search_member.setStyleSheet("background-color: #202024; border: 1px solid #27272A; border-radius: 6px; padding: 6px 12px; color: #FFFFFF; font-size: 12px;")
        self.input_search_member.textChanged.connect(self.search_members_table)
        right_panel.addWidget(self.input_search_member)

        # Members Selection Table (Spacious with compact row height for maximum athlete visibility)
        self.table_members = QTableWidget()
        self.table_members.setColumnCount(4)
        self.table_members.setHorizontalHeaderLabels(["انتخاب", "نام و نام خانوادگی", "شماره تماس", "وضعیت عضویت"])
        self.table_members.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_members.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_members.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_members.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_members.verticalHeader().setVisible(False)
        self.table_members.verticalHeader().setDefaultSectionSize(32)
        self.table_members.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_members.setMinimumHeight(185)
        self.table_members.setMaximumHeight(205)
        right_panel.addWidget(self.table_members, 1)

        # 4. Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(12)

        self.lbl_selection_summary = QLabel("تعداد دریافت‌کنندگان: ۰ نفر")
        self.lbl_selection_summary.setStyleSheet("font-size: 12px; color: #F59E0B; font-weight: bold;")
        action_bar.addWidget(self.lbl_selection_summary)
        action_bar.addStretch()

        self.btn_send_broadcast = QPushButton("🚀  ارسال پیامک به دریافت‌کنندگان")
        self.btn_send_broadcast.setObjectName("primary_button")
        self.btn_send_broadcast.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send_broadcast.setStyleSheet("padding: 10px 24px; font-size: 14px;")
        self.btn_send_broadcast.clicked.connect(self.execute_broadcast_send)
        action_bar.addWidget(self.btn_send_broadcast)
        right_panel.addLayout(action_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #27272A;
                border-radius: 6px;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 6px;
            }
        """)
        right_panel.addWidget(self.progress_bar)

        layout.addLayout(right_panel, 2)

        # =====================================================================
        # Left Column: Smartphone Live Preview Container
        # =====================================================================
        phone_container = QVBoxLayout()
        phone_container.setSpacing(10)
        phone_container.setAlignment(Qt.AlignmentFlag.AlignTop)

        lbl_phone_title = QLabel("📱 پیش‌نمایش در صفحه گوشی شاگرد:")
        lbl_phone_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #E4E4E7;")
        phone_container.addWidget(lbl_phone_title)

        # Mock Smartphone Frame
        self.phone_mockup = QFrame()
        self.phone_mockup.setFixedWidth(290)
        self.phone_mockup.setMinimumHeight(350)
        self.phone_mockup.setMaximumHeight(375)
        self.phone_mockup.setStyleSheet("""
            QFrame {
                background-color: #0A0A0C;
                border: 3px solid #27272A;
                border-radius: 28px;
                padding: 14px;
            }
        """)
        mock_layout = QVBoxLayout(self.phone_mockup)
        mock_layout.setContentsMargins(10, 10, 10, 10)
        mock_layout.setSpacing(8)

        # Speaker Notch
        notch = QFrame()
        notch.setFixedSize(60, 4)
        notch.setStyleSheet("background-color: #3F3F46; border-radius: 2px;")
        mock_layout.addWidget(notch, alignment=Qt.AlignmentFlag.AlignCenter)

        # Phone Header
        p_hdr = QLabel(f"پیامک از: {config.APP_NAME}")
        p_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_hdr.setStyleSheet("font-size: 11px; color: #9CA3AF; margin-bottom: 8px;")
        mock_layout.addWidget(p_hdr)

        # Chat Bubble
        self.chat_bubble = QFrame()
        self.chat_bubble.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        bubble_layout = QVBoxLayout(self.chat_bubble)
        bubble_layout.setContentsMargins(8, 8, 8, 8)
        bubble_layout.setSpacing(6)

        self.lbl_preview_msg = QLabel("متن پیامک اینجا نمایش داده می‌شود...")
        self.lbl_preview_msg.setWordWrap(True)
        self.lbl_preview_msg.setStyleSheet("font-size: 12px; color: #F1F5F9; line-height: 1.5;")
        bubble_layout.addWidget(self.lbl_preview_msg)

        lbl_time = QLabel("هم‌اکنون • ۱۰۰٪ خدماتی")
        lbl_time.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lbl_time.setStyleSheet("font-size: 10px; color: #64748B;")
        bubble_layout.addWidget(lbl_time)

        mock_layout.addWidget(self.chat_bubble)
        mock_layout.addStretch()

        # Phone Home Bar
        home_bar = QFrame()
        home_bar.setFixedSize(70, 3)
        home_bar.setStyleSheet("background-color: #3F3F46; border-radius: 1px;")
        mock_layout.addWidget(home_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        phone_container.addWidget(self.phone_mockup)
        layout.addLayout(phone_container, 1)

        self.tab_broadcast.setWidget(container)

        # Trigger initial preview
        self.on_template_changed(0)

    # =========================================================================
    # Tab 2: Automated Triggers
    # =========================================================================
    def setup_automated_tab(self):
        container = QWidget()
        container.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        lbl_head = QLabel("⚙️ سیستم ارسال خودکار پیام‌های هوشمند")
        lbl_head.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "با فعال‌سازی این گزینه‌ها، پیام‌های خوش‌آمدگویی، تبریک تولد و یادآوری شهریه به صورت کاملاً خودکار برای ورزشکاران ارسال می‌شوند. "
            "برنامه مجهز به سیستم ضدتکرار است و از ارسال پیامک مجدد در یک روز به یک شاگرد جلوگیری می‌نماید."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 12px; color: #A1A1AA; line-height: 1.6;")
        layout.addWidget(lbl_desc)

        card_style = """
            QFrame {
                background-color: #202024;
                border: 1px solid #27272A;
                border-radius: 10px;
            }
        """
        tpl_box_style = """
            QFrame {
                background-color: #18181B;
                border: 1px dashed #3F3F46;
                border-radius: 6px;
            }
        """
        chk_style = """
            QCheckBox {
                font-size: 13px;
                font-weight: bold;
                color: #FFFFFF;
                background: transparent;
                border: none;
                spacing: 10px;
                min-height: 28px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """

        # Card 1: Welcome New Member
        card_welcome = QFrame()
        card_welcome.setObjectName("cardWelcome")
        card_welcome.setStyleSheet(card_style)
        l_wel = QVBoxLayout(card_welcome)
        l_wel.setContentsMargins(18, 16, 18, 16)
        l_wel.setSpacing(12)

        lbl_wel_title = QLabel("🤝 پیامک خودکار خوش‌آمدگویی و تایید ثبت‌نام")
        lbl_wel_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #60A5FA; background: transparent; border: none;")
        l_wel.addWidget(lbl_wel_title)

        self.chk_auto_welcome = QCheckBox("فعال‌سازی ارسال خودکار پیامک خوش‌آمدگویی بلافاصله پس از ثبت‌نام ورزشکار جدید")
        self.chk_auto_welcome.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_auto_welcome.setStyleSheet(chk_style)
        l_wel.addWidget(self.chk_auto_welcome)

        tpl_box_wel = QFrame()
        tpl_box_wel.setStyleSheet(tpl_box_style)
        l_tpl_w = QVBoxLayout(tpl_box_wel)
        l_tpl_w.setContentsMargins(12, 10, 12, 10)
        l_tpl_w.setSpacing(4)
        lbl_tag_w = QLabel("📋 متن الگوی خدماتی ثبت‌شده در سامانه (شناسه ۶۷۶۷۰۰):")
        lbl_tag_w.setStyleSheet("font-size: 11px; font-weight: bold; color: #9CA3AF; background: transparent; border: none;")
        l_tpl_w.addWidget(lbl_tag_w)
        lbl_wel_tpl = QLabel(f"ورزشکار گرامی #NAME#، ثبت‌نام شما در باشگاه {config.APP_NAME} با موفقیت انجام شد. از همراهی شما سپاسگزاریم")
        lbl_wel_tpl.setWordWrap(True)
        lbl_wel_tpl.setStyleSheet("font-size: 12px; color: #E4E4E7; line-height: 1.5; background: transparent; border: none;")
        l_tpl_w.addWidget(lbl_wel_tpl)
        l_wel.addWidget(tpl_box_wel)
        layout.addWidget(card_welcome)

        # Card 2: Birthday
        card_bday = QFrame()
        card_bday.setObjectName("cardBday")
        card_bday.setStyleSheet(card_style)
        l_bday = QVBoxLayout(card_bday)
        l_bday.setContentsMargins(18, 16, 18, 16)
        l_bday.setSpacing(12)

        lbl_bday_title = QLabel("🎂 پیامک تبریک سالروز تولد")
        lbl_bday_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #C084FC; background: transparent; border: none;")
        l_bday.addWidget(lbl_bday_title)

        self.chk_auto_birthday = QCheckBox("فعال‌سازی ارسال خودکار تبریک تولد به ورزشکاران در روز تولدشان")
        self.chk_auto_birthday.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_auto_birthday.setStyleSheet(chk_style)
        l_bday.addWidget(self.chk_auto_birthday)

        tpl_box_bday = QFrame()
        tpl_box_bday.setStyleSheet(tpl_box_style)
        l_tpl_b = QVBoxLayout(tpl_box_bday)
        l_tpl_b.setContentsMargins(12, 10, 12, 10)
        l_tpl_b.setSpacing(4)
        lbl_tag_b = QLabel("📋 متن الگوی خدماتی ثبت‌شده در سامانه (شناسه ۸۷۵۱۷۲):")
        lbl_tag_b.setStyleSheet("font-size: 11px; font-weight: bold; color: #9CA3AF; background: transparent; border: none;")
        l_tpl_b.addWidget(lbl_tag_b)
        lbl_bday_tpl = QLabel(f"ورزشکار گرامی #NAME#، زادروزتان خجسته باد! با آرزوی تندرستی، باشگاه ورزشی {config.APP_NAME}")
        lbl_bday_tpl.setWordWrap(True)
        lbl_bday_tpl.setStyleSheet("font-size: 12px; color: #E4E4E7; line-height: 1.5; background: transparent; border: none;")
        l_tpl_b.addWidget(lbl_bday_tpl)
        l_bday.addWidget(tpl_box_bday)
        layout.addWidget(card_bday)

        # Card 3: Tuition (Clear, spacious, zero-overlap layout)
        card_tuition = QFrame()
        card_tuition.setObjectName("cardTuition")
        card_tuition.setStyleSheet(card_style)
        l_tuition = QVBoxLayout(card_tuition)
        l_tuition.setContentsMargins(18, 16, 18, 16)
        l_tuition.setSpacing(12)

        lbl_tui_title = QLabel("🚨 یادآوری سررسید دوره عضویت (شهریه)")
        lbl_tui_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FBBF24; background: transparent; border: none;")
        l_tuition.addWidget(lbl_tui_title)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(16)

        self.chk_auto_tuition = QCheckBox("فعال‌سازی ارسال خودکار یادآوری سررسید دوره عضویت")
        self.chk_auto_tuition.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_auto_tuition.setStyleSheet(chk_style)
        ctrl_row.addWidget(self.chk_auto_tuition)
        ctrl_row.addStretch()

        self.lbl_tuition_days = QLabel("زمان ارسال پیامک یادآوری:")
        self.lbl_tuition_days.setStyleSheet("font-size: 12px; color: #D1D5DB; font-weight: bold; background: transparent; border: none;")
        ctrl_row.addWidget(self.lbl_tuition_days)

        self.combo_tuition_days = QComboBox()
        self.combo_tuition_days.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_tuition_days.setStyleSheet("""
            QComboBox {
                background-color: #27272A;
                color: #FFFFFF;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 5px 30px 5px 12px;
                font-size: 12px;
                font-weight: bold;
                min-height: 32px;
                min-width: 170px;
            }
            QComboBox:hover {
                border-color: #EF4444;
            }
        """)
        self.combo_tuition_days.addItem("دقیقاً در روز پایان دوره", "0")
        self.combo_tuition_days.addItem("۱ روز قبل از انقضا", "1")
        self.combo_tuition_days.addItem("۲ روز قبل از انقضا", "2")
        ctrl_row.addWidget(self.combo_tuition_days)
        l_tuition.addLayout(ctrl_row)

        self.chk_auto_tuition.toggled.connect(self._on_tuition_chk_toggled)

        tpl_box_tuition = QFrame()
        tpl_box_tuition.setStyleSheet(tpl_box_style)
        l_tpl_t = QVBoxLayout(tpl_box_tuition)
        l_tpl_t.setContentsMargins(12, 10, 12, 10)
        l_tpl_t.setSpacing(4)
        lbl_tag_t = QLabel("📋 متن الگوی خدماتی ثبت‌شده در سامانه (شناسه ۱۸۳۳۴۴):")
        lbl_tag_t.setStyleSheet("font-size: 11px; font-weight: bold; color: #9CA3AF; background: transparent; border: none;")
        l_tpl_t.addWidget(lbl_tag_t)
        lbl_tui_tpl = QLabel(f"ورزشکار گرامی #NAME#، اعتبار دوره عضویت شما در تاریخ #DATE# به پایان می‌رسد. جهت تمدید دوره، به مدیریت باشگاه مراجعه فرمایید. باشگاه {config.APP_NAME}")
        lbl_tui_tpl.setWordWrap(True)
        lbl_tui_tpl.setStyleSheet("font-size: 12px; color: #E4E4E7; line-height: 1.5; background: transparent; border: none;")
        l_tpl_t.addWidget(lbl_tui_tpl)
        l_tuition.addWidget(tpl_box_tuition)
        layout.addWidget(card_tuition)

        # Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_save_settings = QPushButton("💾  ذخیره تنظیمات خودکار")
        self.btn_save_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_settings.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_save_settings.clicked.connect(self.save_auto_settings)
        btn_row.addWidget(self.btn_save_settings)

        self.btn_run_check_now = QPushButton("⚡  بررسی و ارسال پیام‌های امروز هم‌اکنون")
        self.btn_run_check_now.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run_check_now.setStyleSheet("""
            QPushButton {
                background-color: #3F3F46;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #52525B;
            }
        """)
        self.btn_run_check_now.clicked.connect(self.run_automated_check_now)
        btn_row.addWidget(self.btn_run_check_now)
        btn_row.addStretch()

        layout.addLayout(btn_row)
        layout.addStretch()

        self.tab_automated.setWidget(container)

    def _on_tuition_chk_toggled(self, checked: bool):
        if hasattr(self, "combo_tuition_days"):
            self.combo_tuition_days.setEnabled(checked)
        if hasattr(self, "lbl_tuition_days"):
            self.lbl_tuition_days.setEnabled(checked)

    # =========================================================================
    # Tab 3: SMS History Log
    # =========================================================================
    def setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        h_row = QHBoxLayout()
        lbl_h_title = QLabel("📜 گزارش آخرین پیامک‌های تحویل‌داده‌شده")
        lbl_h_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        h_row.addWidget(lbl_h_title)
        h_row.addStretch()

        self.btn_refresh_history = QPushButton("🔄 بازخوانی گزارش‌ها")
        self.btn_refresh_history.setStyleSheet("background-color: #27272A; color: #FFF; border: 1px solid #3F3F46; border-radius: 6px; padding: 6px 14px; font-size: 12px;")
        self.btn_refresh_history.clicked.connect(self.load_history)
        h_row.addWidget(self.btn_refresh_history)
        layout.addLayout(h_row)

        self.table_history = QTableWidget()
        self.table_history.setColumnCount(6)
        self.table_history.setHorizontalHeaderLabels(["ردیف", "تاریخ و ساعت", "نام ورزشکار", "شماره موبایل", "نوع پیامک", "وضعیت"])
        self.table_history.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_history.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.verticalHeader().setVisible(False)
        layout.addWidget(self.table_history, 1)

    # =========================================================================
    # Event Handlers & Logics
    # =========================================================================

    def refresh_balance(self):
        self.lbl_balance_val.setText("در حال استعلام...")
        from yalda.utils.theme_manager import ThemeManager
        palette = ThemeManager.get_current_palette()
        self.card_balance.setStyleSheet(f"QFrame#cardBalance {{ background-color: {palette.bg_surface}; border: 1px solid {palette.border_light}; border-radius: 8px; }}")
        self.btn_refresh_bal.setEnabled(False)

        self.bal_thread = SmsBalanceThread()
        self.bal_thread.finished_signal.connect(self.on_balance_received)
        self.bal_thread.start()

    def on_balance_received(self, res: dict):
        self.btn_refresh_bal.setEnabled(True)
        rem = res.get("remaining", 0)
        total_cred = res.get("total_credited", 0)
        self._balance_data = res

        if res.get("success"):
            if rem > 0:
                self.lbl_balance_val.setText(f"{rem:,} عدد")
                self.card_balance.setStyleSheet("QFrame#cardBalance { background-color: #064E3B; border: 1px solid #059669; border-radius: 8px; }")
                self.lbl_balance_val.setStyleSheet("font-size: 17px; font-weight: bold; color: #6EE7B7; background: transparent; border: none;")
            elif total_cred == 0:
                self.lbl_balance_val.setText("۰ عدد (در انتظار شارژ)")
                self.card_balance.setStyleSheet("QFrame#cardBalance { background-color: #2E1A05; border: 1px solid #D97706; border-radius: 8px; }")
                self.lbl_balance_val.setStyleSheet("font-size: 14px; font-weight: bold; color: #FBBF24; background: transparent; border: none;")
            else:
                self.lbl_balance_val.setText("۰ عدد (پایان اعتبار)")
                self.card_balance.setStyleSheet("QFrame#cardBalance { background-color: #450A0A; border: 1px solid #DC2626; border-radius: 8px; }")
                self.lbl_balance_val.setStyleSheet("font-size: 14px; font-weight: bold; color: #FCA5A5; background: transparent; border: none;")
        else:
            from yalda.utils.theme_manager import ThemeManager
            palette = ThemeManager.get_current_palette()
            self.lbl_balance_val.setText("عدم اتصال به اینترنت")
            self.card_balance.setStyleSheet(f"QFrame#cardBalance {{ background-color: {palette.bg_surface}; border: 1px solid {palette.border_light}; border-radius: 8px; }}")
            self.lbl_balance_val.setStyleSheet(f"font-size: 13px; color: {palette.text_muted}; background: transparent; border: none;")

    def show_recharge_dialog(self):
        dlg = RechargeInfoDialog(self)
        dlg.exec()

    def set_holiday_reason_preset(self, reason: str):
        self.input_dyn_reason.setText(reason)

    def set_hours_preset(self, days: str, women: str, men: str, note: str = ""):
        self.combo_hours_days.setCurrentText(days)
        self.combo_hours_women.setCurrentText(women)
        self.combo_hours_men.setCurrentText(men)
        self.input_hours_note.setText(note)

    def on_template_changed(self, idx):
        tpl_key = self.combo_templates.currentData()

        self.panel_holiday.setVisible(tpl_key == "holiday")
        self.panel_hours.setVisible(tpl_key == "hours")

        self.update_preview()

    def update_preview(self):
        tpl_key = self.combo_templates.currentData()
        gym_name = config.APP_NAME

        if tpl_key == "holiday":
            d_val = self.input_dyn_date.text().strip() or "فردا"
            r_val = self.input_dyn_reason.text().strip() or "تعطیلات رسمی"
            msg = f"ورزشکار محترم باشگاه {gym_name}، به اطلاع می‌رساند باشگاه در تاریخ {d_val} به علت {r_val} تعطیل می‌باشد."
        else: # hours
            days_val = self.combo_hours_days.currentText().strip() or "شنبه تا پنجشنبه"
            women_val = self.combo_hours_women.currentText().strip() or "۸ الی ۱۲ و ۱۵ الی ۱۹"
            men_val = self.combo_hours_men.currentText().strip() or "۱۲ الی ۱۵ و ۱۹ الی ۲۳"
            note_val = self.input_hours_note.text().strip() or "-"
            msg = (
                f"ورزشکار محترم، زمان‌بندی جدید سانس‌های باشگاه ورزشی {gym_name}:\n"
                f"روزها: {days_val}\n"
                f"بانوان: {women_val}\n"
                f"آقایان: {men_val}\n"
                f"توضیحات: {note_val}"
            )

        self.lbl_preview_msg.setText(msg)

    def load_members(self):
        self._all_members = MemberService.get_all_members() or []
        self.populate_members_table(self._all_members)

    def populate_members_table(self, members):
        # Clean up any existing cell widgets to prevent duplicate or floating orphaned widgets
        for r in range(self.table_members.rowCount()):
            w = self.table_members.cellWidget(r, 0)
            if w:
                w.setParent(None)
                w.deleteLater()
            self.table_members.removeCellWidget(r, 0)
        self.table_members.clearContents()
        self.table_members.setRowCount(len(members))
        today_shamsi = get_today_shamsi()

        for row, m in enumerate(members):
            chk = QCheckBox()
            # Select by default if matching current radio filter
            is_active = (m.membership_expire_shamsi and m.membership_expire_shamsi >= today_shamsi)
            should_check = True
            if self.rb_active.isChecked() and not is_active:
                should_check = False

            chk.setChecked(should_check)
            chk.stateChanged.connect(lambda _, mid=m.id: self.on_member_check_changed(mid))

            chk_w = QWidget()
            ch_lay = QHBoxLayout(chk_w)
            ch_lay.setContentsMargins(4, 0, 4, 0)
            ch_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ch_lay.addWidget(chk)

            self.table_members.setCellWidget(row, 0, chk_w)

            name_item = QTableWidgetItem(m.full_name or "-")
            name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table_members.setItem(row, 1, name_item)

            phone_item = QTableWidgetItem(m.phone or "-")
            phone_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_members.setItem(row, 2, phone_item)

            status_str = "فعال ✅" if is_active else "منقضی ❌"
            st_item = QTableWidgetItem(status_str)
            st_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            st_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            st_item.setForeground(QBrush(QColor("#10B981" if is_active else "#EF4444")))
            self.table_members.setItem(row, 3, st_item)

        self.update_selection_summary()

    def filter_members_selection(self):
        today_shamsi = get_today_shamsi()
        for row in range(self.table_members.rowCount()):
            cell_w = self.table_members.cellWidget(row, 0)
            if not cell_w:
                continue
            chk = cell_w.findChild(QCheckBox)
            if not chk:
                continue

            st_item = self.table_members.item(row, 3)
            is_active = st_item and "فعال" in st_item.text()

            if self.rb_all.isChecked():
                chk.blockSignals(True)
                chk.setChecked(True)
                chk.blockSignals(False)
            elif self.rb_active.isChecked():
                chk.blockSignals(True)
                chk.setChecked(is_active)
                chk.blockSignals(False)
            elif self.rb_custom.isChecked():
                pass # keep as is

        self.update_selection_summary()

    def deselect_all_members(self):
        """Unchecks all members in the table and activates custom mode for selective manual picking."""
        for row in range(self.table_members.rowCount()):
            cell_w = self.table_members.cellWidget(row, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(False)
                    chk.blockSignals(False)
        self.rb_custom.setChecked(True)
        self.update_selection_summary()

    def on_member_check_changed(self, mid):
        if not self.rb_custom.isChecked():
            self.rb_custom.blockSignals(True)
            self.rb_custom.setChecked(True)
            self.rb_custom.blockSignals(False)
        self.update_selection_summary()

    def update_selection_summary(self):
        selected_count = 0
        for row in range(self.table_members.rowCount()):
            cell_w = self.table_members.cellWidget(row, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    selected_count += 1

        self.lbl_selection_summary.setText(f"تعداد دریافت‌کنندگان: {selected_count} نفر")
        if selected_count > 0:
            self.btn_send_broadcast.setText(f"🚀  ارسال پیامک گروهی به {selected_count} ورزشکار")
            self.btn_send_broadcast.setEnabled(True)
        else:
            self.btn_send_broadcast.setText("🚀  ارسال پیامک گروهی (۰ ورزشکار انتخاب شده)")
            self.btn_send_broadcast.setEnabled(False)

    def search_members_table(self, query):
        q = query.strip().lower()
        for row in range(self.table_members.rowCount()):
            name_it = self.table_members.item(row, 1)
            phone_it = self.table_members.item(row, 2)
            name_txt = name_it.text().lower() if name_it else ""
            phone_txt = phone_it.text().lower() if phone_it else ""
            matched = (q in name_txt or q in phone_txt) if q else True
            self.table_members.setRowHidden(row, not matched)

    def get_selected_recipients(self):
        recipients = []
        for row in range(self.table_members.rowCount()):
            if self.table_members.isRowHidden(row):
                continue
            cell_w = self.table_members.cellWidget(row, 0)
            if not cell_w:
                continue
            chk = cell_w.findChild(QCheckBox)
            if chk and chk.isChecked():
                name_it = self.table_members.item(row, 1)
                phone_it = self.table_members.item(row, 2)
                if name_it and phone_it and phone_it.text().strip():
                    recipients.append({
                        "name": name_it.text().strip(),
                        "phone": phone_it.text().strip()
                    })
        return recipients

    def execute_broadcast_send(self):
        recipients = self.get_selected_recipients()
        if not recipients:
            QMessageBox.warning(self, "خطا", "هیچ ورزشکاری برای ارسال پیامک انتخاب نشده است.")
            return

        balance = self._balance_data.get("remaining", 0)
        needed = len(recipients)
        if balance < needed:
            QMessageBox.warning(
                self,
                "عدم موجودی کافی",
                f"اعتبار باقیمانده شما {balance} پیامک است اما برای ارسال به {needed} نفر نیاز به شارژ دارید.\n"
                "لطفاً نسبت به شارژ بسته پیامکی اقدام فرمایید."
            )
            return

        confirm = QMessageBox.question(
            self,
            "تایید نهایی ارسال پیامک",
            f"آیا از ارسال پیامک به {needed} نفر از ورزشکاران اطمینان دارید؟\n"
            f"پس از ارسال، تعداد {needed} عدد از موجودی پیامک شما کسر خواهد شد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        tpl_key = self.combo_templates.currentData()
        tpl_info = DEFAULT_SMS_TEMPLATES.get(tpl_key, DEFAULT_SMS_TEMPLATES.get("holiday", {}))
        template_id = tpl_info.get("template_id")
        gym_name = config.APP_NAME

        # Parameter builder for verify endpoint
        def build_params(member_name):
            if tpl_key == "holiday":
                return [
                    {"name": "GYM", "value": gym_name},
                    {"name": "DATE", "value": self.input_dyn_date.text().strip() or "فردا"},
                    {"name": "REASON", "value": self.input_dyn_reason.text().strip() or "تعطیلات رسمی"}
                ]
            else: # hours
                days_val = self.combo_hours_days.currentText().strip() or "شنبه تا پنجشنبه"
                women_val = self.combo_hours_women.currentText().strip() or "۸ الی ۱۲ و ۱۵ الی ۱۹"
                men_val = self.combo_hours_men.currentText().strip() or "۱۲ الی ۱۵ و ۱۹ الی ۲۳"
                note_val = self.input_hours_note.text().strip() or "-"
                return [
                    {"name": "GYM", "value": gym_name},
                    {"name": "DAYS", "value": days_val},
                    {"name": "WOMEN", "value": women_val},
                    {"name": "MEN", "value": men_val},
                    {"name": "NOTE", "value": note_val}
                ]

        msg_text = self.lbl_preview_msg.text()

        self.btn_send_broadcast.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(recipients))
        self.progress_bar.setValue(0)

        self.send_thread = SmsSendBatchThread(
            recipients=recipients,
            template_id=template_id,
            parameters_builder=build_params,
            message_text=msg_text,
            message_type=tpl_key
        )
        self.send_thread.progress_signal.connect(self.on_send_progress)
        self.send_thread.finished_signal.connect(self.on_send_finished)
        self.send_thread.start()

    def on_send_progress(self, curr, total, name):
        self.progress_bar.setValue(curr)
        self.btn_send_broadcast.setText(f"در حال ارسال ({curr}/{total})...")

    def on_send_finished(self, succ, fail, rem_balance):
        self.progress_bar.setVisible(False)
        self.btn_send_broadcast.setEnabled(True)
        self.update_selection_summary()
        self.refresh_balance()
        self.load_history()

        if fail == 0:
            QMessageBox.information(self, "موفقیت", f"✅ پیامک با موفقیت به تمام {succ} ورزشکار ارسال گردید.")
        else:
            QMessageBox.warning(self, "گزارش ارسال", f"ارسال به {succ} نفر موفق و به {fail} نفر ناموفق بود.\nاعتبار باقیمانده: {rem_balance}")

    # =========================================================================
    # Automated Settings Persistence
    # =========================================================================

    def load_auto_settings(self):
        session = SessionLocal()
        try:
            w_flag = session.query(SystemSetting).filter_by(key="sms_auto_welcome_enabled").first()
            self.chk_auto_welcome.setChecked(bool(w_flag and w_flag.value == "1"))

            b_flag = session.query(SystemSetting).filter_by(key="sms_auto_birthday_enabled").first()
            self.chk_auto_birthday.setChecked(bool(b_flag and b_flag.value == "1"))

            t_flag = session.query(SystemSetting).filter_by(key="sms_auto_tuition_enabled").first()
            self.chk_auto_tuition.setChecked(bool(t_flag and t_flag.value == "1"))

            t_days = session.query(SystemSetting).filter_by(key="sms_auto_tuition_days").first()
            if t_days and t_days.value:
                idx = self.combo_tuition_days.findData(t_days.value)
                if idx >= 0:
                    self.combo_tuition_days.setCurrentIndex(idx)
        except Exception:
            pass
        finally:
            session.close()

    def save_auto_settings(self):
        session = SessionLocal()
        try:
            w_val = "1" if self.chk_auto_welcome.isChecked() else "0"
            b_val = "1" if self.chk_auto_birthday.isChecked() else "0"
            t_val = "1" if self.chk_auto_tuition.isChecked() else "0"
            days_val = self.combo_tuition_days.currentData()

            for k, v in [
                ("sms_auto_welcome_enabled", w_val),
                ("sms_auto_birthday_enabled", b_val),
                ("sms_auto_tuition_enabled", t_val),
                ("sms_auto_tuition_days", days_val)
            ]:
                s = session.query(SystemSetting).filter_by(key=k).first()
                if s:
                    s.value = v
                else:
                    session.add(SystemSetting(key=k, value=v))

            session.commit()
            QMessageBox.information(self, "موفقیت", "تنظیمات ارسال خودکار پیامک با موفقیت ذخیره شد.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره تنظیمات: {e}")
        finally:
            session.close()

    def run_automated_check_now(self):
        self.btn_run_check_now.setEnabled(False)
        self.btn_run_check_now.setText("در حال بررسی...")

        r_bday = SmsService.check_and_send_automated_birthdays()
        r_tui = SmsService.check_and_send_automated_tuitions()

        self.btn_run_check_now.setEnabled(True)
        self.btn_run_check_now.setText("⚡  بررسی و ارسال پیام‌های امروز هم‌اکنون")
        self.refresh_balance()

        b_count = r_bday.get("sent_count", 0)
        t_count = r_tui.get("sent_count", 0)
        QMessageBox.information(
            self,
            "نتیجه بررسی خودکار",
            f"بررسی با موفقیت انجام شد:\n"
            f"• پیامک‌های تبریک تولد امروز: {b_count} عدد\n"
            f"• پیامک‌های سررسید شهریه امروز: {t_count} عدد"
        )

    def on_tab_changed(self, index: int):
        if index == 2:  # Tab 3: SMS History
            self.load_history()

    # =========================================================================
    # History Log Loader
    # =========================================================================

    def load_history(self):
        self.btn_refresh_history.setEnabled(False)
        self.btn_refresh_history.setText("در حال دریافت...")
        self.hist_thread = SmsHistoryThread()
        self.hist_thread.finished_signal.connect(self.on_history_received)
        self.hist_thread.start()

    def on_history_received(self, logs: list):
        self.btn_refresh_history.setEnabled(True)
        self.btn_refresh_history.setText("🔄 بازخوانی گزارش‌ها")
        self.populate_history_table(logs)

    def populate_history_table(self, logs: list):
        self.table_history.setRowCount(len(logs))

        for row, l in enumerate(logs):
            item_idx = QTableWidgetItem(str(row + 1))
            item_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_history.setItem(row, 0, item_idx)

            item_date = QTableWidgetItem(l.get("date_shamsi", "-"))
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_history.setItem(row, 1, item_date)

            item_name = QTableWidgetItem(l.get("member_name", "-"))
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_history.setItem(row, 2, item_name)

            item_phone = QTableWidgetItem(l.get("recipient", "-"))
            item_phone.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_history.setItem(row, 3, item_phone)

            m_type = l.get("type", "custom")
            if m_type == "birthday":
                type_str = "🎂 تبریک تولد"
            elif m_type == "tuition":
                type_str = "🚨 سررسید شهریه"
            elif m_type == "holiday":
                type_str = "🏖️ اعلام تعطیلی باشگاه"
            elif m_type == "hours":
                type_str = "⏰ ساعت کاری باشگاه"
            elif m_type == "welcome":
                type_str = "🎉 خوش‌آمدگویی"
            else:
                type_str = "📩 اطلاع‌رسانی"

            item_type = QTableWidgetItem(type_str)
            item_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_history.setItem(row, 4, item_type)

            detail = l.get("detail", "")
            is_sim = "آزمایشی" in detail or "شبیه‌ساز" in detail
            status_text = "آزمایشی (شبیه‌ساز) 🧪" if is_sim else "ارسال موفق ✅"
            st_item = QTableWidgetItem(status_text)
            st_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            st_item.setForeground(QBrush(QColor("#60A5FA" if is_sim else "#10B981")))
            self.table_history.setItem(row, 5, st_item)
