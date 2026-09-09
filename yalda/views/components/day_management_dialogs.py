from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QGroupBox, QRadioButton
)
from PyQt6.QtCore import Qt


class DaySelectionReductionDialog(QDialog):
    """
    Dialog shown when the user reduces the number of days in a workout or nutrition plan.
    Allows selecting which existing days to keep, their order, or starting fresh.
    """
    def __init__(self, current_days_summary: list, target_count: int, parent=None, is_nutrition=False):
        super().__init__(parent)
        self.current_days_summary = current_days_summary  # list of tuples: (index, title, count_text)
        self.target_count = target_count
        self.is_nutrition = is_nutrition
        self.selected_indices = []
        self.start_fresh = False

        plan_type = "تغذیه" if is_nutrition else "تمرینی"
        self.setWindowTitle(f"⚙️ کاهش روزهای برنامه {plan_type}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(460)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Info
        lbl_msg = QLabel(
            f"شما تعداد روزهای برنامه را از <b>{len(self.current_days_summary)} روز</b> به <b>{self.target_count} روز</b> کاهش دادید.<br>"
            f"لطفاً مشخص کنید کدام روزها و با چه ترتیبی به عنوان برنامه جدید چیده شوند:"
        )
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-size: 13px; line-height: 1.5;")
        layout.addWidget(lbl_msg)

        # Dropdowns container
        box_slots = QGroupBox(f"انتخاب {self.target_count} روز مدنظر")
        layout_slots = QVBoxLayout(box_slots)
        layout_slots.setSpacing(10)

        self.combos = []
        for i in range(1, self.target_count + 1):
            row = QHBoxLayout()
            lbl = QLabel(f"روز {i}: ")
            lbl.setFixedWidth(55)
            combo = QComboBox()
            combo.setFixedHeight(34)
            for idx, title, count_text in self.current_days_summary:
                combo.addItem(f"{title} ({count_text})", idx)
            # Default to i-1 if in range
            default_idx = min(i - 1, len(self.current_days_summary) - 1)
            combo.setCurrentIndex(default_idx)
            self.combos.append(combo)
            row.addWidget(lbl)
            row.addWidget(combo)
            layout_slots.addLayout(row)

        layout.addWidget(box_slots)

        # Action Buttons
        btn_box = QVBoxLayout()
        btn_box.setSpacing(8)

        btn_confirm = QPushButton("✅ تایید و چینش روزهای انتخابی")
        btn_confirm.setFixedHeight(38)
        btn_confirm.clicked.connect(self.on_confirm)

        btn_fresh = QPushButton("✨ شروع برنامه جدید (خالی)")
        btn_fresh.setObjectName("secondary_button")
        btn_fresh.setFixedHeight(36)
        btn_fresh.clicked.connect(self.on_fresh)

        btn_cancel = QPushButton("انصراف (حفظ تعداد روز قبلی)")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_confirm)
        btn_box.addWidget(btn_fresh)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def on_confirm(self):
        self.selected_indices = [c.currentData() for c in self.combos]
        self.start_fresh = False
        self.accept()

    def on_fresh(self):
        self.selected_indices = []
        self.start_fresh = True
        self.accept()


class DayIncreaseChoiceDialog(QDialog):
    """
    Dialog shown when the user increases the number of days in a workout or nutrition plan.
    """
    def __init__(self, target_days: int, prev_days_count: int, parent=None, is_nutrition=False, has_cached_plan=False):
        super().__init__(parent)
        self.target_days = target_days
        self.prev_days_count = prev_days_count
        self.is_nutrition = is_nutrition
        self.has_cached_plan = has_cached_plan
        self.choice = "append"  # 'append', 'restore', or 'fresh'

        plan_type = "تغذیه" if is_nutrition else "تمرینی"
        self.setWindowTitle(f"🔄 افزایش روزهای برنامه {plan_type}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(480)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        if self.has_cached_plan:
            msg_text = (
                f"تعداد روزها از <b>{self.prev_days_count} روز</b> به <b>{self.target_days} روز</b> افزایش یافت.<br>"
                f"برای برنامه <b>{self.target_days} روزه</b> یک پیش‌نویس ذخیره‌شده از قبل در این نشست وجود دارد. مایلید چگونه ادامه دهید؟"
            )
        else:
            msg_text = (
                f"تعداد روزها از <b>{self.prev_days_count} روز</b> به <b>{self.target_days} روز</b> افزایش یافت.<br>"
                f"لطفاً نحوه اعمال این تغییر را مشخص کنید:"
            )

        lbl_msg = QLabel(msg_text)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-size: 13px; line-height: 1.5;")
        layout.addWidget(lbl_msg)

        box_options = QGroupBox("نحوه چینش روزها")
        layout_opt = QVBoxLayout(box_options)
        layout_opt.setSpacing(12)

        self.radio_append = QRadioButton(f"➕ افزودن روز جدید در ادامه همین {self.prev_days_count} روز فعلی (پیشنهادی)")
        self.radio_append.setChecked(True)
        layout_opt.addWidget(self.radio_append)

        if self.has_cached_plan:
            self.radio_restore = QRadioButton(f"🔁 بازگردانی کامل برنامه {self.target_days} روزه قبلی")
            layout_opt.addWidget(self.radio_restore)
        else:
            self.radio_restore = None

        self.radio_fresh = QRadioButton(f"✨ شروع برنامه {self.target_days} روزه جدید و خالی")
        layout_opt.addWidget(self.radio_fresh)
        layout.addWidget(box_options)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        btn_ok = QPushButton("✅ تایید")
        btn_ok.setFixedHeight(38)
        btn_ok.clicked.connect(self.on_confirm)

        btn_cancel = QPushButton("انصراف (حفظ تعداد روز قبلی)")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(38)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def on_confirm(self):
        if self.radio_restore and self.radio_restore.isChecked():
            self.choice = "restore"
        elif self.radio_fresh.isChecked():
            self.choice = "fresh"
        else:
            self.choice = "append"
        self.accept()
