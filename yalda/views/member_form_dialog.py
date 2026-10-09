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
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        avail_h = screen.availableGeometry().height() if screen else 800
        self._compact_mode = avail_h < 650
        dlg_h = min(585, max(525, avail_h - 36))
        self.setFixedSize(650, dlg_h)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5 if getattr(self, "_compact_mode", False) else 8)
        layout.setContentsMargins(20, 12 if getattr(self, "_compact_mode", False) else 16, 20, 12 if getattr(self, "_compact_mode", False) else 16)


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

        # Physical Stats Box (Height & Weight on top row, Activity Level on bottom row, BMR/TDEE opposite)
        row_stats_container = QHBoxLayout()
        
        vbox_hw = QVBoxLayout()
        vbox_hw.setSpacing(8)

        row_hw_top = QHBoxLayout()
        row_hw_top.setSpacing(8)

        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(0.0, 300.0)
        self.spin_height.setSpecialValueText("")
        self.spin_height.setValue(0.0)
        self.spin_height.setDecimals(0)
        self.spin_height.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_height.setFixedWidth(85)
        self.spin_height.setFixedHeight(34)
        self.spin_height.setStyleSheet("padding: 2px 4px;")

        lbl_h = QLabel("قد (cm):")
        lbl_h.setFixedWidth(55)

        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0.0, 300.0)
        self.spin_weight.setSpecialValueText("")
        self.spin_weight.setValue(0.0)
        self.spin_weight.setDecimals(1)
        self.spin_weight.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_weight.setFixedWidth(85)
        self.spin_weight.setFixedHeight(34)
        self.spin_weight.setStyleSheet("padding: 2px 4px;")

        lbl_w = QLabel("وزن (kg):")
        lbl_w.setFixedWidth(55)

        row_hw_top.addWidget(lbl_h)
        row_hw_top.addWidget(self.spin_height)
        row_hw_top.addSpacing(8)
        row_hw_top.addWidget(lbl_w)
        row_hw_top.addWidget(self.spin_weight)
        row_hw_top.addStretch()
        vbox_hw.addLayout(row_hw_top)

        row_activity = QHBoxLayout()
        row_activity.setSpacing(6)
        lbl_act = QLabel("سطح فعالیت:")
        lbl_act.setFixedWidth(78)

        from yalda.utils.bmr_calculator import PAL_LEVELS
        self.combo_activity = QComboBox()
        for idx_i, (act_key, act_info) in enumerate(PAL_LEVELS.items()):
            self.combo_activity.addItem(act_info["combo_text"], act_key)
            self.combo_activity.setItemData(
                idx_i,
                f"{act_info['title']} — {act_info['desc']}",
                Qt.ItemDataRole.ToolTipRole,
            )
        idx_default_act = self.combo_activity.findData("moderately_active")
        if idx_default_act >= 0:
            self.combo_activity.setCurrentIndex(idx_default_act)
        self.combo_activity.setFixedWidth(222)
        self.combo_activity.setFixedHeight(34)
        self.combo_activity.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.combo_activity.view().setMinimumWidth(222)

        row_activity.addWidget(lbl_act)
        row_activity.addWidget(self.combo_activity)
        row_activity.addStretch()
        vbox_hw.addLayout(row_activity)

        self.lbl_bmr_badge = QLabel("BMR: -\nTDEE: -")
        self.lbl_bmr_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bmr_badge.setFixedHeight(76)
        self.lbl_bmr_badge.setFixedWidth(295)
        self.lbl_bmr_badge.setStyleSheet("font-size: 12px; font-weight: bold; padding: 6px 8px; border-radius: 8px; background-color: #555555; color: white;")

        self.spin_height.valueChanged.connect(self.update_bmr_display)
        self.spin_weight.valueChanged.connect(self.update_bmr_display)
        self.combo_gender.currentIndexChanged.connect(self.update_bmr_display)
        self.picker_birth.date_changed.connect(self.update_bmr_display)
        self.combo_activity.currentIndexChanged.connect(self.update_bmr_display)

        row_stats_container.addLayout(vbox_hw)
        row_stats_container.addSpacing(12)
        row_stats_container.addWidget(self.lbl_bmr_badge)
        row_stats_container.addStretch()

        layout.addLayout(row_stats_container)
        self.update_bmr_display()

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
            file_filter="فایل‌های تصویری (*.png *.jpg *.jpeg *.bmp *.webp)",
            is_square_default=True
        )
        if filepath:
            self.photo_path = filepath
            self.btn_photo.setText(f"📷 عکس: {os.path.basename(filepath)[:15]}")

    def update_bmr_display(self):
        from yalda.utils.bmr_calculator import calculate_bmr_tdee, calculate_age_from_shamsi, PAL_LEVELS
        h = self.spin_height.value()
        w = self.spin_weight.value()
        act_level = self.combo_activity.currentData() or "moderately_active"
        if act_level in PAL_LEVELS:
            p_info = PAL_LEVELS[act_level]
            self.combo_activity.setToolTip(f"{p_info['title']} — {p_info['desc']}")
        if h > 0 and w > 0:
            age = calculate_age_from_shamsi(self.picker_birth.text().strip())
            gender = self.combo_gender.currentData() or "male"
            bmr, tdee, pal, act_title, color = calculate_bmr_tdee(h, w, age, gender, act_level)
            if bmr > 0:
                self.lbl_bmr_badge.setText(
                    f"\u200fمتابولیسم پایه (BMR): {bmr:,} کالری\n"
                    f"\u200fکالری روزانه (TDEE): {tdee:,} کالری ({act_title})"
                )
                self.lbl_bmr_badge.setStyleSheet(
                    f"font-size: 12px; font-weight: bold; padding: 6px 8px; border-radius: 8px; background-color: {color}; color: white;"
                )
            else:
                self.lbl_bmr_badge.setText("\u200fمتابولیسم پایه (BMR): -\n\u200fکالری روزانه (TDEE): -")
                self.lbl_bmr_badge.setStyleSheet("font-size: 12px; font-weight: bold; padding: 6px 8px; border-radius: 8px; background-color: #555555; color: white;")
        else:
            self.lbl_bmr_badge.setText("\u200fمتابولیسم پایه (BMR): -\n\u200fکالری روزانه (TDEE): -")
            self.lbl_bmr_badge.setStyleSheet("font-size: 12px; font-weight: bold; padding: 6px 8px; border-radius: 8px; background-color: #555555; color: white;")

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

        # Duplicate checks for member
        from yalda.services.member_service import MemberService
        all_members = MemberService.get_all_members()
        curr_id = self.member_data.id if self.member_data else None

        # 1. Check duplicate phone (if not "-")
        if phone != "-":
            persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
            phone_eng = phone.translate(persian_to_eng)
            for m in all_members:
                if curr_id and m.id == curr_id:
                    continue
                m_phone = (m.phone or "").translate(persian_to_eng)
                if m_phone and m_phone != "-" and m_phone == phone_eng:
                    reply = QMessageBox.question(
                        self,
                        "هشدار شماره تماس تکراری",
                        f"ورزشکاری با شماره تماس «{phone}» از قبل در سیستم ثبت شده است ({m.full_name}).\n\nآیا با وجود تکراری بودن شماره، مایل به ذخیره هستید؟",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        self.txt_phone.setFocus()
                        return
                    break

        # 2. Check duplicate full name (first_name + last_name)
        full_name_candidate = f"{first_name} {last_name}".strip().lower()
        same_name_members = [
            m for m in all_members 
            if not (curr_id and m.id == curr_id) and m.full_name and m.full_name.strip().lower() == full_name_candidate
        ]
        if same_name_members:
            from yalda.utils.duplicate_helper import get_next_numbered_name
            other_lasts = [m.last_name for m in all_members if not (curr_id and m.id == curr_id) and m.first_name and m.first_name.strip().lower() == first_name.lower() and m.last_name]
            suggested_last = get_next_numbered_name(last_name, other_lasts)
            reply = QMessageBox.question(
                self,
                "هشدار نام تکراری",
                f"ورزشکار دیگری با نام و نام خانوادگی «{first_name} {last_name}» از قبل در سیستم ثبت شده است.\n\nدر صورت تایید، این ورزشکار با مشخصات «{first_name} {suggested_last}» ذخیره خواهد شد.\nآیا مطمئن هستید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.txt_last_name.setFocus()
                return
            self.txt_last_name.setText(suggested_last)

        try:
            data = self.get_data()
            if self.member_data:
                MemberService.update_member(self.member_data.id, data)
                QMessageBox.information(self, "موفقیت", "اطلاعات ورزشکار با موفقیت ویرایش شد.")
            else:
                MemberService.create_member(data)
                # Automatically trigger welcome SMS if enabled by coach
                try:
                    import threading
                    from yalda.services.sms_service import SmsService
                    full_n = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
                    phone_n = data.get('phone', '')
                    if phone_n and phone_n != "-":
                        threading.Thread(
                            target=SmsService.send_welcome_sms_if_enabled,
                            args=(full_n, phone_n),
                            daemon=True
                        ).start()
                except Exception:
                    pass
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
            "activity_level": self.combo_activity.currentData() or "moderately_active",
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

        act_val = getattr(m, "activity_level", None) or "moderately_active"
        idx_act = self.combo_activity.findData(act_val)
        if idx_act >= 0:
            self.combo_activity.setCurrentIndex(idx_act)

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
        self.update_bmr_display()

