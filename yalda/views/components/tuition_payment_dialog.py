from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTextEdit, QPushButton, QMessageBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt
from yalda.services.accounting_service import AccountingService
from yalda.services.member_service import MemberService
from yalda.database.connection import get_session
from yalda.views.components.jalali_calendar_widget import JalaliDatePicker
from yalda.utils.jalali_date import get_today_shamsi, is_valid_shamsi, add_months_shamsi, normalize_digits
from yalda.auth.authentication import CurrentUser

class TuitionPaymentDialog(QDialog):
    def __init__(self, parent=None, member_id=None, payment=None):
        super().__init__(parent)
        self.payment = payment
        self.is_edit = payment is not None
        self.preselected_member_id = payment.get("member_id") if self.is_edit else member_id
        self.setWindowTitle("ویرایش پرداخت شهریه" if self.is_edit else "ثبت پرداخت و تمدید شهریه")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog {
                background-color: #161616;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #10B981;
                background-color: #282828;
            }
            QPushButton#btn_save {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                height: 38px;
                font-size: 13px;
            }
            QPushButton#btn_save:hover {
                background-color: #059669;
            }
            QPushButton#btn_cancel {
                background-color: #2C2C2C;
                color: #CCCCCC;
                border: 1px solid #444444;
                border-radius: 6px;
                height: 38px;
                font-size: 13px;
            }
            QPushButton#btn_cancel:hover {
                background-color: #3A3A3A;
                color: #FFFFFF;
            }
            QCheckBox {
                color: #E0E0E0;
                font-size: 12.5px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title
        header_title = "✏️ ویرایش پرداخت شهریه" if self.is_edit else "💰 ثبت دریافتی و شهریه ورزشکار"
        lbl_header = QLabel(header_title)
        lbl_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #10B981; margin-bottom: 4px;")
        layout.addWidget(lbl_header)

        # 1. Member Selector
        layout.addWidget(QLabel("انتخاب ورزشکار: *"))
        self.combo_member = QComboBox()
        self.combo_member.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trainers_map = {t.id: t.display_name for t in AccountingService.get_all_trainers()}
        try:
            from yalda.models.database_models import User
            with get_session() as s:
                admin_u = s.query(User).filter(User.username == "admin").first()
                if admin_u:
                    self.trainers_map[admin_u.id] = admin_u.display_name
        except Exception:
            pass

        self.members = MemberService.get_all_members()
        for m in self.members:
            trainer_name = self.trainers_map.get(m.user_id, "بدون مربی")
            self.combo_member.addItem(f"{m.full_name} (مربی: {trainer_name} | تلفن: {m.phone})", m.id)

        self.combo_member.currentIndexChanged.connect(self._on_member_changed)
        layout.addWidget(self.combo_member)

        # Member Info Card
        self.lbl_member_info = QLabel()
        self.lbl_member_info.setStyleSheet("background-color: #202020; border: 1px solid #333; border-radius: 6px; padding: 8px; color: #BBB; font-size: 12px; font-weight: normal;")
        layout.addWidget(self.lbl_member_info)

        # 2. Payment Amount
        layout.addWidget(QLabel("مبلغ پرداختی (تومان): *"))
        self.txt_amount = QLineEdit()
        self.txt_amount.setPlaceholderText("مبلغ به تومان (مثلاً ۲,۰۰۰,۰۰۰)")
        self.txt_amount.textChanged.connect(self._format_amount_input)
        layout.addWidget(self.txt_amount)

        # 3. Payment Date
        layout.addWidget(QLabel("تاریخ پرداخت (شمسی): *"))
        self.date_picker = JalaliDatePicker()
        self.date_picker.setText(get_today_shamsi())
        layout.addWidget(self.date_picker)

        # 4. Payment Type
        layout.addWidget(QLabel("نوع پرداخت:"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["شهریه دوره ماهانه", "شهریه تک جلسه", "شهریه برنامه تمرینی/تغذیه", "سایر دریافتی‌ها"])
        self.combo_type.currentTextChanged.connect(self._on_type_changed)
        layout.addWidget(self.combo_type)

        # 5. Optional: Extend Member's Expiration Date
        self.chk_extend = QCheckBox("تمدید خودکار تاریخ انقضای عضویت ورزشکار به مدت ۱ ماه")
        self.chk_extend.setChecked(True)
        self.chk_extend.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.chk_extend)

        # 6. Notes
        layout.addWidget(QLabel("توضیحات (اختیاری):"))
        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("شماره فیش، شماره پیگیری، نحوه پرداخت و ...")
        layout.addWidget(self.txt_notes)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        self.btn_save = QPushButton("💾 ذخیره تغییرات پرداخت" if self.is_edit else "💰 ثبت نهایی پرداخت")
        self.btn_save.setObjectName("btn_save")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_payment)

        self.btn_cancel = QPushButton("انصراف")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(self.btn_save, 2)
        btn_box.addWidget(self.btn_cancel, 1)
        layout.addLayout(btn_box)

        # Preselect if member_id given
        if self.preselected_member_id:
            for idx, m in enumerate(self.members):
                if m.id == self.preselected_member_id:
                    self.combo_member.setCurrentIndex(idx)
                    self.combo_member.setEnabled(False)
                    break
        else:
            self._on_member_changed()

        if self.is_edit and self.payment:
            self.chk_extend.setVisible(False)
            self.txt_amount.setText(f"{int(self.payment['amount']):,}")
            self.date_picker.setText(self.payment['date_shamsi'])
            cat = self.payment.get('category', 'شهریه دوره ماهانه')
            if cat in ["شهریه دوره", "تمدید عضویت باشگاه"]:
                cat = "شهریه دوره ماهانه"
            idx = self.combo_type.findText(cat)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
            else:
                self.combo_type.addItem(cat)
                self.combo_type.setCurrentText(cat)
            notes_val = self.payment.get('description', '')
            if notes_val == '-':
                notes_val = ''
            self.txt_notes.setText(notes_val)

    def _on_type_changed(self, text: str):
        if hasattr(self, "chk_extend") and not self.is_edit:
            if text == "شهریه تک جلسه":
                self.chk_extend.setChecked(False)
            elif text == "شهریه دوره ماهانه":
                self.chk_extend.setChecked(True)

    def _on_member_changed(self):
        mid = self.combo_member.currentData()
        if not mid:
            self.lbl_member_info.setText("ورزشکاری انتخاب نشده است.")
            return

        m = MemberService.get_member_by_id(mid)
        if m:
            trainers_map = getattr(self, 'trainers_map', {})
            trainer_name = trainers_map.get(m.user_id, "بدون مربی")
            exp_date = m.membership_expire_shamsi or "-"
            fee = int(m.tuition_fee) if m.tuition_fee else 0
            fee_str = f"{fee:,} تومان" if fee else "ثبت‌نشده"
            self.lbl_member_info.setText(
                f"👤 نام: {m.full_name}   |   مربی: {trainer_name}\n"
                f"📅 تاریخ انقضای فعلی: {exp_date}   |   شهریه ثبت‌شده: {fee_str}"
            )
            if fee > 0 and not self.txt_amount.text().strip():
                self.txt_amount.setText(f"{fee:,}")

    def _format_amount_input(self, text: str):
        clean = text.replace(",", "").replace("٬", "").strip()
        clean = normalize_digits(clean)
        if clean.isdigit():
            val = int(clean)
            formatted = f"{val:,}"
            if text != formatted:
                self.txt_amount.blockSignals(True)
                self.txt_amount.setText(formatted)
                self.txt_amount.blockSignals(False)

    def save_payment(self):
        mid = self.combo_member.currentData()
        if not mid:
            QMessageBox.warning(self, "خطا", "لطفاً یک ورزشکار را انتخاب فرمایید.")
            return

        amt_str = self.txt_amount.text().replace(",", "").replace("٬", "").strip()
        amt_str = normalize_digits(amt_str)
        if not amt_str.isdigit() or int(amt_str) <= 0:
            QMessageBox.warning(self, "خطای ورودی", "لطفاً مبلغ شهریه معتبری وارد نمایید.")
            self.txt_amount.setFocus()
            return
        amount = float(amt_str)

        date_val = self.date_picker.get_date()
        if not is_valid_shamsi(date_val):
            QMessageBox.warning(self, "خطای ورودی", "تاریخ پرداخت معتبر نمی‌باشد (فرمت: YYYY/MM/DD).")
            return

        pay_type = self.combo_type.currentText().strip()
        notes = self.txt_notes.text().strip()

        if self.is_edit:
            try:
                AccountingService.update_tuition_payment(
                    payment_id=self.payment["id"],
                    amount=amount,
                    payment_date_shamsi=date_val,
                    payment_type=pay_type,
                    notes=notes
                )
                QMessageBox.information(self, "موفقیت", "اطلاعات پرداخت شهریه با موفقیت ویرایش شد.")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در ویرایش پرداخت شهریه: {str(e)}")
            return

        try:
            m = MemberService.get_member_by_id(mid)
            trainer_id = m.user_id if m else CurrentUser.get_id()

            # Record tuition payment
            AccountingService.add_tuition_payment(
                member_id=mid,
                amount=amount,
                payment_date_shamsi=date_val,
                user_id=trainer_id,
                payment_type=pay_type,
                notes=notes
            )

            # Optionally extend membership expiration
            if self.chk_extend.isChecked() and m:
                # If current expiration is valid and in future, extend from current expiration, else from payment date
                base_date = m.membership_expire_shamsi if (m.membership_expire_shamsi and is_valid_shamsi(m.membership_expire_shamsi)) else date_val
                new_exp = add_months_shamsi(base_date, 1)
                MemberService.update_member(mid, {
                    "membership_expire_shamsi": new_exp,
                    "tuition_fee": amount
                })

            QMessageBox.information(self, "موفقیت", "پرداخت شهریه با موفقیت ثبت شد و در تراز مالی قرار گرفت.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ثبت پرداخت شهریه: {str(e)}")
