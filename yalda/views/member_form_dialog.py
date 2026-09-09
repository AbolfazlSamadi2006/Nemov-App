from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit, QMessageBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from yalda.views.components.jalali_calendar_widget import JalaliDatePicker
from yalda.utils.jalali_date import add_months_shamsi
import os

class MemberFormDialog(QDialog):
    def __init__(self, parent=None, member_data=None):
        super().__init__(parent)
        self.member_data = member_data
        self.photo_path = None
        self.setWindowTitle("ثبت / ویرایش ورزشکار جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(650, 560)

        self.init_ui()



    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)


        # Name Row
        row1 = QHBoxLayout()
        self.txt_first_name = QLineEdit()
        self.txt_first_name.setPlaceholderText("نام")
        self.txt_last_name = QLineEdit()
        self.txt_last_name.setPlaceholderText("نام خانوادگی")
        row1.addWidget(QLabel("نام:"))
        row1.addWidget(self.txt_first_name)
        row1.addWidget(QLabel("نام خانوادگی:"))
        row1.addWidget(self.txt_last_name)
        layout.addLayout(row1)

        # Phone, Job & Gender Row
        row2 = QHBoxLayout()
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("09123456789")
        self.txt_phone.setMaxLength(11)
        self.txt_phone.setFixedWidth(115)

        self.txt_job = QLineEdit()
        self.txt_job.setPlaceholderText("شغل / حرفه")

        self.combo_gender = QComboBox()
        self.combo_gender.addItem("آقا", "male")
        self.combo_gender.addItem("خانم", "female")
        self.combo_gender.setMinimumWidth(90)

        row2.addWidget(QLabel("تلفن همراه:"))
        row2.addWidget(self.txt_phone)
        row2.addWidget(QLabel("شغل:"))
        row2.addWidget(self.txt_job)
        row2.addWidget(QLabel("جنسیت:"))
        row2.addWidget(self.combo_gender)
        layout.addLayout(row2)

        # Birthdate & Profile Photo Selection Row
        row_birth_photo = QHBoxLayout()
        self.picker_birth = JalaliDatePicker(default_today=False)
        self.picker_birth.setFixedWidth(155)
        self.picker_birth.setFixedHeight(38)


        self.btn_photo = QPushButton("📷 تصویر پروفایل")
        self.btn_photo.setObjectName("secondary_button")
        self.btn_photo.clicked.connect(self.choose_photo)

        row_birth_photo.addWidget(QLabel("تاریخ تولد:"))
        row_birth_photo.addWidget(self.picker_birth)
        row_birth_photo.addSpacing(15)
        row_birth_photo.addWidget(self.btn_photo)
        row_birth_photo.addStretch()
        layout.addLayout(row_birth_photo)

        # Physical Stats Box (Height & Weight stacked vertically, BMI opposite)
        row_stats_container = QHBoxLayout()
        
        vbox_hw = QVBoxLayout()
        vbox_hw.setSpacing(8)

        row_h = QHBoxLayout()
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(0.0, 300.0)
        self.spin_height.setSpecialValueText("")
        self.spin_height.setValue(0.0)
        self.spin_height.setDecimals(0)
        self.spin_height.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_height.setFixedWidth(90)
        self.spin_height.setStyleSheet("padding: 2px 4px;")

        lbl_h = QLabel("قد (cm):")
        lbl_h.setFixedWidth(65)

        row_h.addWidget(lbl_h)
        row_h.addWidget(self.spin_height)
        row_h.addStretch()
        vbox_hw.addLayout(row_h)

        row_w = QHBoxLayout()
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0.0, 300.0)
        self.spin_weight.setSpecialValueText("")
        self.spin_weight.setValue(0.0)
        self.spin_weight.setDecimals(1)
        self.spin_weight.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_weight.setFixedWidth(90)
        self.spin_weight.setStyleSheet("padding: 2px 4px;")

        lbl_w = QLabel("وزن (kg):")
        lbl_w.setFixedWidth(65)

        row_w.addWidget(lbl_w)
        row_w.addWidget(self.spin_weight)
        row_w.addStretch()
        vbox_hw.addLayout(row_w)

        self.lbl_bmi_badge = QLabel("BMI: -")
        self.lbl_bmi_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bmi_badge.setFixedHeight(65)
        self.lbl_bmi_badge.setMinimumWidth(180)
        self.lbl_bmi_badge.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px; border-radius: 8px; background-color: #555555; color: white;")

        self.spin_height.valueChanged.connect(self.update_bmi_display)
        self.spin_weight.valueChanged.connect(self.update_bmi_display)

        row_stats_container.addLayout(vbox_hw)
        row_stats_container.addSpacing(20)
        row_stats_container.addWidget(self.lbl_bmi_badge)
        row_stats_container.addStretch()

        layout.addLayout(row_stats_container)
        self.update_bmi_display()

        # Membership Dates, Fee, Type & Status Grid (4 Rows, 4 Columns)
        grid_mem = QGridLayout()
        grid_mem.setHorizontalSpacing(12)
        grid_mem.setVerticalSpacing(8)

        # Row 0: Registration Date (Col 0,1) & Sports Insurance Date (Col 2,3)
        lbl_reg = QLabel("تاریخ ثبت نام:")
        lbl_reg.setFixedWidth(80)
        self.picker_reg = JalaliDatePicker(default_today=True)
        self.picker_reg.setFixedWidth(160)
        self.picker_reg.setFixedHeight(38)

        lbl_ins = QLabel("تاریخ بیمه ورزشی:")
        lbl_ins.setFixedWidth(105)
        self.picker_insurance = JalaliDatePicker(default_today=False)
        self.picker_insurance.setFixedWidth(170)
        self.picker_insurance.setFixedHeight(38)

        grid_mem.addWidget(lbl_reg, 0, 0)
        grid_mem.addWidget(self.picker_reg, 0, 1)
        grid_mem.addWidget(lbl_ins, 0, 2)
        grid_mem.addWidget(self.picker_insurance, 0, 3)

        # Row 1: Start Date (Col 0,1) & Tuition Fee (Col 2,3)
        lbl_start = QLabel("تاریخ شروع:")
        lbl_start.setFixedWidth(80)
        self.picker_start = JalaliDatePicker(default_today=True)
        self.picker_start.setFixedWidth(160)
        self.picker_start.setFixedHeight(38)
        self.picker_start.date_changed.connect(self.recalculate_expiry)

        lbl_fee = QLabel("مبلغ شهریه:")
        lbl_fee.setFixedWidth(105)
        self.txt_tuition_fee = QLineEdit()
        self.txt_tuition_fee.setFixedWidth(170)
        self.txt_tuition_fee.setFixedHeight(38)
        self.txt_tuition_fee.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_tuition_fee.textChanged.connect(self.format_tuition_input)

        grid_mem.addWidget(lbl_start, 1, 0)
        grid_mem.addWidget(self.picker_start, 1, 1)
        grid_mem.addWidget(lbl_fee, 1, 2)
        grid_mem.addWidget(self.txt_tuition_fee, 1, 3)

        # Row 2: Expiry Date (Col 0,1) & Membership Type (Col 2,3)
        lbl_expire = QLabel("تاریخ انقضا:")
        lbl_expire.setFixedWidth(80)
        self.picker_expire = JalaliDatePicker(default_today=False)
        self.picker_expire.setFixedWidth(160)
        self.picker_expire.setFixedHeight(38)
        self.picker_expire.date_changed.connect(self.auto_update_status)


        lbl_membership_type = QLabel("نوع عضویت:")
        lbl_membership_type.setFixedWidth(105)
        self.combo_membership = QComboBox()
        self.combo_membership.addItem("۸ جلسه در ماه", "8_sessions")
        self.combo_membership.addItem("۱۲ جلسه در ماه", "12_sessions")
        self.combo_membership.addItem("۱۶ جلسه در ماه", "16_sessions")
        self.combo_membership.addItem("۲۰ جلسه در ماه", "20_sessions")
        self.combo_membership.addItem("همه روزه", "daily_access")
        self.combo_membership.setFixedWidth(170)
        self.combo_membership.setFixedHeight(38)
        self.combo_membership.currentIndexChanged.connect(self.on_membership_type_changed)

        grid_mem.addWidget(lbl_expire, 2, 0)
        grid_mem.addWidget(self.picker_expire, 2, 1)
        grid_mem.addWidget(lbl_membership_type, 2, 2)
        grid_mem.addWidget(self.combo_membership, 2, 3)

        # Row 3: Trainer Notes Label (Col 0 - Under Expiry Date) & File Status (Col 2,3 - Under Membership Type)
        lbl_notes = QLabel("یادداشت‌های مربی:")
        lbl_notes.setFixedWidth(105)

        lbl_status = QLabel("وضعیت پرونده:")
        lbl_status.setFixedWidth(105)
        self.combo_status = QComboBox()
        self.combo_status.addItem("🟢 فعال", "active")
        self.combo_status.addItem("🔴 منقضی", "expired")
        self.combo_status.addItem("⚪ آرشیو شده", "archived")
        self.combo_status.setFixedWidth(170)
        self.combo_status.setFixedHeight(38)

        grid_mem.addWidget(lbl_notes, 3, 0)
        grid_mem.addWidget(lbl_status, 3, 2)
        grid_mem.addWidget(self.combo_status, 3, 3)

        layout.addLayout(grid_mem)

        # Notes Text Box (Directly below grid)
        self.txt_notes = QTextEdit()
        self.txt_notes.setAcceptRichText(False)
        self.txt_notes.setFixedHeight(80)
        layout.addWidget(self.txt_notes)





        # Submit Buttons
        btn_box = QHBoxLayout()
        btn_save = QPushButton("ذخیره اطلاعات")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

        # Load existing data if editing, else calculate default 1-month expiry from start date
        if self.member_data:
            self.load_member_data()
        else:
            self.recalculate_expiry()


    def choose_photo(self):
        from yalda.utils.image_source_chooser import get_image_file_path
        filepath = get_image_file_path(
            self,
            dialog_title="انتخاب یا ثبت تصویر پروفایل ورزشکار",
            file_filter="فایل‌های تصویری (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if filepath:
            self.photo_path = filepath
            self.btn_photo.setText(f"📷 عکس: {os.path.basename(filepath)[:15]}")

    def update_bmi_display(self):
        from yalda.utils.bmi_calculator import calculate_bmi_info
        h = self.spin_height.value()
        w = self.spin_weight.value()
        if h > 0 and w > 0:
            bmi, cat, color = calculate_bmi_info(h, w)
            if bmi > 0:
                self.lbl_bmi_badge.setText(f"BMI: {bmi}\n({cat})")
                self.lbl_bmi_badge.setStyleSheet(f"font-size: 13px; font-weight: bold; padding: 10px; border-radius: 8px; background-color: {color}; color: white;")
            else:
                self.lbl_bmi_badge.setText("BMI: -")
                self.lbl_bmi_badge.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px; border-radius: 8px; background-color: #555555; color: white;")
        else:
            self.lbl_bmi_badge.setText("BMI: -")
            self.lbl_bmi_badge.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px; border-radius: 8px; background-color: #555555; color: white;")

    def format_tuition_input(self, text: str):
        persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        raw = text.translate(persian_to_eng).replace(',', '').replace(' ', '').strip()
        if raw.isdigit():
            val = int(raw)
            formatted = f"{val:,}"
            if text != formatted:
                self.txt_tuition_fee.blockSignals(True)
                self.txt_tuition_fee.setText(formatted)
                self.txt_tuition_fee.blockSignals(False)
        elif not raw:
            if text != "":
                self.txt_tuition_fee.blockSignals(True)
                self.txt_tuition_fee.setText("")
                self.txt_tuition_fee.blockSignals(False)

    def recalculate_expiry(self):
        try:
            start_date = self.picker_start.text().strip()
            if start_date:
                expire_date = add_months_shamsi(start_date, 1)
                if expire_date:
                    self.picker_expire.setText(expire_date)
            else:
                self.picker_expire.setText("")
        except Exception:
            pass
        self.auto_update_status()

    def auto_update_status(self):
        try:
            from yalda.utils.jalali_date import is_membership_active
            start_date = self.picker_start.text().strip()
            expire_date = self.picker_expire.text().strip()

            if not start_date:
                idx = self.combo_status.findData("archived")
                if idx >= 0:
                    self.combo_status.setCurrentIndex(idx)
            elif expire_date and not is_membership_active(expire_date):
                idx = self.combo_status.findData("expired")
                if idx >= 0:
                    self.combo_status.setCurrentIndex(idx)
            else:
                idx = self.combo_status.findData("active")
                if idx >= 0:
                    self.combo_status.setCurrentIndex(idx)
        except Exception:
            pass

    def on_membership_type_changed(self):
        self.recalculate_expiry()


    def save(self):
        first_name = self.txt_first_name.text().strip()
        last_name = self.txt_last_name.text().strip()
        phone = self.txt_phone.text().strip()

        missing_fields = []
        if not first_name:
            missing_fields.append("نام")
        if not last_name:
            missing_fields.append("نام خانوادگی")
        if not phone:
            missing_fields.append("شماره تلفن (یا علامت -)")

        if missing_fields:
            if len(missing_fields) == 1:
                msg = f"لطفاً {missing_fields[0]} را وارد کنید."
            elif len(missing_fields) == 2:
                msg = f"لطفاً {missing_fields[0]} و {missing_fields[1]} را وارد کنید."
            else:
                msg = f"لطفاً {', '.join(missing_fields[:-1])} و {missing_fields[-1]} را وارد کنید."
            QMessageBox.warning(self, "خطا", msg)
            return

        # Phone format check (Must not exceed 11 digits, or '-' for no phone)
        if phone != "-":
            persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
            phone_eng = phone.translate(persian_to_eng)
            if len(phone_eng) > 11:
                QMessageBox.warning(
                    self,
                    "خطا در شماره تلفن",
                    "شماره تماس نمی‌تواند بیشتر از ۱۱ رقم باشد.\nدر صورت عدم وجود تلفن، علامت - را قرار دهید."
                )
                self.txt_phone.setFocus()
                return

        try:
            from yalda.services.member_service import MemberService
            data = self.get_data()
            if self.member_data:
                MemberService.update_member(self.member_data.id, data)
                QMessageBox.information(self, "موفقیت", "اطلاعات ورزشکار با موفقیت ویرایش شد.")
            else:
                MemberService.create_member(data)
                QMessageBox.information(self, "موفقیت", "ورزشکار جدید با موفقیت ثبت شد.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ثبت اطلاعات: {str(e)}")

    def get_data(self) -> dict:
        phone_val = self.txt_phone.text().strip()
        if phone_val != "-":
            persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
            phone_val = phone_val.translate(persian_to_eng)

        raw_fee = self.txt_tuition_fee.text().strip()
        persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        raw_fee_clean = raw_fee.translate(persian_to_eng).replace(',', '').replace(' ', '')
        tuition_val = float(raw_fee_clean) if raw_fee_clean.isdigit() else None

        return {
            "first_name": self.txt_first_name.text().strip(),
            "last_name": self.txt_last_name.text().strip(),
            "phone": phone_val,
            "job": self.txt_job.text().strip(),
            "gender": self.combo_gender.currentData(),
            "birth_date_shamsi": self.picker_birth.text(),
            "height_cm": self.spin_height.value() if self.spin_height.value() > 0 else None,
            "initial_weight_kg": self.spin_weight.value() if self.spin_weight.value() > 0 else None,
            "registration_date_shamsi": self.picker_reg.text(),
            "insurance_date_shamsi": self.picker_insurance.text(),
            "tuition_fee": tuition_val,
            "membership_type": self.combo_membership.currentData(),
            "membership_start_shamsi": self.picker_start.text(),
            "membership_expire_shamsi": self.picker_expire.text(),
            "photo_path": self.photo_path,
            "notes": self.txt_notes.toPlainText().strip(),
            "status": self.combo_status.currentData()
        }

    def load_member_data(self):
        m = self.member_data
        self.txt_first_name.setText(m.first_name)
        self.txt_last_name.setText(m.last_name)
        self.txt_phone.setText(m.phone)
        if hasattr(m, 'job') and m.job:
            self.txt_job.setText(m.job)
        self.spin_height.setValue(m.height_cm or 0.0)
        self.spin_weight.setValue(m.initial_weight_kg or 0.0)

        self.photo_path = m.photo_path
        if self.photo_path and os.path.exists(self.photo_path):
            self.btn_photo.setText(f"📷 عکس: {os.path.basename(self.photo_path)[:15]}")
        
        idx_g = self.combo_gender.findData(m.gender)
        if idx_g >= 0:
            self.combo_gender.setCurrentIndex(idx_g)

        idx_m = self.combo_membership.findData(m.membership_type)
        if idx_m >= 0:
            self.combo_membership.setCurrentIndex(idx_m)

        idx_s = self.combo_status.findData(m.status)
        if idx_s >= 0:
            self.combo_status.setCurrentIndex(idx_s)


        if hasattr(m, 'registration_date_shamsi') and m.registration_date_shamsi:
            self.picker_reg.setText(m.registration_date_shamsi)
        if hasattr(m, 'insurance_date_shamsi') and m.insurance_date_shamsi:
            self.picker_insurance.setText(m.insurance_date_shamsi)
        if hasattr(m, 'tuition_fee') and m.tuition_fee is not None:
            val = int(m.tuition_fee)
            self.txt_tuition_fee.setText(f"{val:,}")

        if m.birth_date_shamsi:
            self.picker_birth.setText(m.birth_date_shamsi)
        if m.membership_start_shamsi:
            self.picker_start.setText(m.membership_start_shamsi)
        if m.membership_expire_shamsi:
            self.picker_expire.setText(m.membership_expire_shamsi)
        if m.notes:
            self.txt_notes.setText(m.notes)
        self.update_bmi_display()

