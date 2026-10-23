from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTextEdit, QPushButton, QMessageBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt
import jdatetime
from nemov.services.accounting_service import AccountingService
from nemov.services.member_service import MemberService
from nemov.database.connection import get_session
from nemov.models.database_models import TuitionPayment
from nemov.views.components.jalali_calendar_widget import JalaliDatePicker
from nemov.views.components.field_validator import (
    MicroWarningLabel, validate_tuition_amount
)
from nemov.utils.jalali_date import (
    get_today_shamsi, is_valid_shamsi, add_months_shamsi,
    normalize_digits, days_until_expire, parse_shamsi
)
from nemov.auth.authentication import CurrentUser

class TuitionPaymentDialog(QDialog):
    def __init__(self, parent=None, member_id=None, payment=None):
        super().__init__(parent)
        self.payment = payment
        self.is_edit = payment is not None
        self.preselected_member_id = payment.get("member_id") if self.is_edit else member_id
        self.setWindowTitle("ویرایش پرداخت شهریه" if self.is_edit else "ثبت پرداخت و تمدید شهریه")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title
        header_title = "✏️ ویرایش پرداخت شهریه" if self.is_edit else "💰 ثبت دریافتی و شهریه ورزشکار"
        lbl_header = QLabel(header_title)
        lbl_header.setObjectName("h2")
        layout.addWidget(lbl_header)

        # 1. Member Selector
        layout.addWidget(QLabel("انتخاب ورزشکار: *"))
        self.combo_member = QComboBox()
        self.combo_member.setObjectName("combo_member")
        self.combo_member.setFixedHeight(42)
        self.combo_member.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trainers_map = {t.id: t.display_name for t in AccountingService.get_all_trainers()}
        try:
            from nemov.models.database_models import User
            with get_session() as s:
                admin_u = s.query(User).filter(User.username == "admin").first()
                if admin_u:
                    self.trainers_map[admin_u.id] = admin_u.display_name
        except Exception:
            pass

        self.members = MemberService.get_all_members()
        for m in self.members:
            trainer_name = self.trainers_map.get(m.user_id, "بدون مربی")
            phone_str = m.phone if m.phone else "بدون تلفن"
            self.combo_member.addItem(f"{m.full_name}   (مربی: {trainer_name})   -   {phone_str}", m.id)

        self.combo_member.currentIndexChanged.connect(self._on_member_changed)
        layout.addWidget(self.combo_member)

        # Member Info Card
        self.lbl_member_info = QLabel()
        self.lbl_member_info.setObjectName("card")
        layout.addWidget(self.lbl_member_info)

        # 2. Payment Amount
        layout.addWidget(QLabel("مبلغ پرداختی (تومان): *"))
        self.txt_amount = QLineEdit()
        self.txt_amount.setPlaceholderText("مبلغ به تومان (مثلاً ۲,۰۰۰,۰۰۰)")
        self.txt_amount.textChanged.connect(self._format_amount_input)
        layout.addWidget(self.txt_amount)

        self.lbl_amount_warn = MicroWarningLabel()
        layout.addWidget(self.lbl_amount_warn)
        self.txt_amount.editingFinished.connect(self._validate_amount_field)

        # 3. Payment Date
        layout.addWidget(QLabel("تاریخ پرداخت (شمسی): *"))
        self.date_picker = JalaliDatePicker()
        self.date_picker.setText(get_today_shamsi())
        self.date_picker.date_changed.connect(lambda _: self._update_extend_checkbox())
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
        self.btn_save.setObjectName("primary_button")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_payment)

        self.btn_cancel = QPushButton("انصراف")
        self.btn_cancel.setObjectName("secondary_button")
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
        self._update_extend_checkbox()

    def _calculate_new_expiry(self, m, payment_date: str) -> str:
        if not m or not is_valid_shamsi(payment_date):
            return ""

        curr_exp = m.membership_expire_shamsi if (m.membership_expire_shamsi and is_valid_shamsi(m.membership_expire_shamsi)) else None

        # If no current expiration date or it is already expired (days_until_expire < 0), renew 1 month from payment date
        if not curr_exp or days_until_expire(curr_exp) < 0:
            return add_months_shamsi(payment_date, 1)

        # Member is currently active (curr_exp is in the future).
        # Check if member has any recorded tuition payments prior to this one:
        session = get_session()
        try:
            prev_payments_count = session.query(TuitionPayment).filter(TuitionPayment.member_id == m.id).count()
        except Exception:
            prev_payments_count = 0
        finally:
            session.close()

        # If member has 0 previous tuition payments:
        # This payment is the initial payment for the registration period!
        # The member's expiration date was already initialized to 1 month from start date.
        # Do not add a second month prematurely.
        if prev_payments_count == 0:
            return curr_exp

        # Otherwise, this is a renewal payment for the next month: extend 1 month from current expiration
        return add_months_shamsi(curr_exp, 1)

    def _update_extend_checkbox(self):
        if not hasattr(self, "chk_extend") or self.is_edit:
            return
        mid = self.combo_member.currentData()
        if not mid:
            self.chk_extend.setText("تمدید خودکار تاریخ انقضای عضویت ورزشکار به مدت ۱ ماه")
            return
        m = MemberService.get_member_by_id(mid)
        payment_date = self.date_picker.get_date()
        new_exp = self._calculate_new_expiry(m, payment_date)
        if new_exp:
            self.chk_extend.setText(f"تمدید خودکار تاریخ انقضا به مدت ۱ ماه (انقضای جدید: {new_exp})")
        else:
            self.chk_extend.setText("تمدید خودکار تاریخ انقضای عضویت ورزشکار به مدت ۱ ماه")

    def _get_registration_start_date(self, m) -> str:
        if not m:
            return ""
        for attr in ["membership_start_shamsi", "registration_date_shamsi"]:
            val = getattr(m, attr, None)
            if val and is_valid_shamsi(str(val).strip()):
                return str(val).strip()
        return ""

    def _get_suggested_payment_date(self, m) -> str:
        """
        Sets payment date day equal to the day of member's registration start date,
        unless they are already equal.
        """
        reg_date_str = self._get_registration_start_date(m)
        today_str = get_today_shamsi()
        if not reg_date_str or not is_valid_shamsi(reg_date_str) or not is_valid_shamsi(today_str):
            return today_str

        try:
            reg_dt = parse_shamsi(reg_date_str)
            today_dt = parse_shamsi(today_str)
            reg_day = reg_dt.day

            if today_dt.day == reg_day:
                return today_str

            def _clamp(y: int, m_idx: int, d: int) -> int:
                if m_idx <= 6:
                    max_d = 31
                elif m_idx <= 11:
                    max_d = 30
                else:
                    try:
                        jdatetime.date(y, 12, 30)
                        max_d = 30
                    except ValueError:
                        max_d = 29
                return min(d, max_d)

            y_curr, m_curr = today_dt.year, today_dt.month
            d_curr = _clamp(y_curr, m_curr, reg_day)
            dt_curr = jdatetime.date(y_curr, m_curr, d_curr)

            m_prev = 12 if m_curr == 1 else m_curr - 1
            y_prev = y_curr - 1 if m_curr == 1 else y_curr
            d_prev = _clamp(y_prev, m_prev, reg_day)
            dt_prev = jdatetime.date(y_prev, m_prev, d_prev)

            if today_dt.day > reg_day:
                return dt_curr.strftime("%Y/%m/%d")
            else:
                days_ahead = (dt_curr - today_dt).days
                days_behind = (today_dt - dt_prev).days
                if days_behind < days_ahead:
                    return dt_prev.strftime("%Y/%m/%d")
                else:
                    return dt_curr.strftime("%Y/%m/%d")
        except Exception:
            return today_str

    def _on_member_changed(self):
        mid = self.combo_member.currentData()
        if not mid:
            self.lbl_member_info.setText("ورزشکاری انتخاب نشده است.")
            if not self.is_edit:
                self.txt_amount.clear()
            self._update_extend_checkbox()
            return

        m = MemberService.get_member_by_id(mid)
        if m:
            trainers_map = getattr(self, 'trainers_map', {})
            trainer_name = trainers_map.get(m.user_id, "بدون مربی")
            exp_date = m.membership_expire_shamsi or "-"
            start_date = self._get_registration_start_date(m) or "-"
            fee = int(m.tuition_fee) if m.tuition_fee else 0
            fee_str = f"{fee:,} تومان" if fee else "ثبت‌نشده"
            self.lbl_member_info.setText(
                f"👤 نام: {m.full_name}   |   مربی: {trainer_name}\n"
                f"📅 شروع ثبت‌نام: {start_date}   |   انقضای فعلی: {exp_date}\n"
                f"💰 شهریه ثبت‌شده: {fee_str}"
            )
            if not self.is_edit:
                if fee > 0:
                    self.txt_amount.setText(f"{fee:,}")
                else:
                    self.txt_amount.clear()

                sug_date = self._get_suggested_payment_date(m)
                if sug_date:
                    self.date_picker.setText(sug_date)

        self._update_extend_checkbox()

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

    def _validate_amount_field(self):
        err = validate_tuition_amount(self.txt_amount.text())
        self.lbl_amount_warn.show_warning(err)
        return err is None

    def save_payment(self):
        if not self._validate_amount_field():
            err = validate_tuition_amount(self.txt_amount.text())
            if err:
                QMessageBox.warning(self, "خطای ورودی", err.replace("⚠️ ", ""))
                self.txt_amount.setFocus()
                return
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
                new_exp = self._calculate_new_expiry(m, date_val)
                if new_exp:
                    MemberService.update_member(mid, {
                        "membership_expire_shamsi": new_exp,
                        "tuition_fee": amount
                    })

            QMessageBox.information(self, "موفقیت", "پرداخت شهریه با موفقیت ثبت شد و در تراز مالی قرار گرفت.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ثبت پرداخت شهریه: {str(e)}")
