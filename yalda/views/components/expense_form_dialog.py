from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTextEdit, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from yalda.services.accounting_service import AccountingService, EXPENSE_CATEGORIES
from yalda.views.components.jalali_calendar_widget import JalaliDatePicker
from yalda.utils.jalali_date import get_today_shamsi, is_valid_shamsi
from yalda.auth.authentication import CurrentUser

class ExpenseFormDialog(QDialog):
    def __init__(self, parent=None, expense=None):
        super().__init__(parent)
        self.expense = expense
        self.is_edit = expense is not None
        self.setWindowTitle("ویرایش هزینه باشگاه" if self.is_edit else "ثبت هزینه جدید باشگاه")
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
                border: 1px solid #DC2626;
                background-color: #282828;
            }
            QPushButton#btn_save {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                height: 38px;
                font-size: 13px;
            }
            QPushButton#btn_save:hover {
                background-color: #B91C1C;
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
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title
        lbl_header = QLabel("✏️ ویرایش هزینه" if self.is_edit else "➕ ثبت مخارج و هزینه جدید")
        lbl_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF; margin-bottom: 4px;")
        layout.addWidget(lbl_header)

        # 1. Expense Title
        layout.addWidget(QLabel("عنوان هزینه / شرح پرداخت: *"))
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("مثلاً: خرید روغن دستگاه‌ها، قبض برق، خرید مکمل ...")
        layout.addWidget(self.txt_title)

        # 2. Category
        layout.addWidget(QLabel("دسته‌بندی هزینه: *"))
        self.combo_category = QComboBox()
        self.combo_category.addItems(EXPENSE_CATEGORIES)
        layout.addWidget(self.combo_category)

        # 3. Amount
        layout.addWidget(QLabel("مبلغ هزینه (تومان): *"))
        self.txt_amount = QLineEdit()
        self.txt_amount.setPlaceholderText("مبلغ به تومان (مثلاً ۵۰۰,۰۰۰)")
        self.txt_amount.textChanged.connect(self._format_amount_input)
        layout.addWidget(self.txt_amount)

        # 4. Date
        layout.addWidget(QLabel("تاریخ پرداخت (شمسی): *"))
        self.date_picker = JalaliDatePicker()
        self.date_picker.setText(get_today_shamsi())
        layout.addWidget(self.date_picker)

        # 5. Trainer Selector
        layout.addWidget(QLabel("مربی / ثبت‌کننده هزینه:"))
        self.combo_trainer = QComboBox()
        self.combo_trainer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trainers = AccountingService.get_all_trainers()

        # Ensure current user is in list if not already present (e.g. admin)
        curr_u = CurrentUser.get()
        curr_uid = CurrentUser.get_id()
        if curr_u and not any(t.id == curr_u.id for t in self.trainers):
            self.trainers.insert(0, curr_u)

        for t in self.trainers:
            self.combo_trainer.addItem(f"👤 {t.display_name}", t.id)

        # Preselect current logged-in trainer
        for idx, t in enumerate(self.trainers):
            if t.id == curr_uid:
                self.combo_trainer.setCurrentIndex(idx)
                break

        layout.addWidget(self.combo_trainer)

        # 6. Description
        layout.addWidget(QLabel("توضیحات تکمیلی (اختیاری):"))
        self.txt_desc = QTextEdit()
        self.txt_desc.setFixedHeight(65)
        self.txt_desc.setPlaceholderText("هرگونه توضیحات اضافه، نام فروشگاه یا جزئیات ...")
        layout.addWidget(self.txt_desc)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        self.btn_save = QPushButton("💾 ذخیره هزینه" if self.is_edit else "➕ ثبت هزینه")
        self.btn_save.setObjectName("btn_save")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_expense)

        self.btn_cancel = QPushButton("انصراف")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(self.btn_save, 2)
        btn_box.addWidget(self.btn_cancel, 1)
        layout.addLayout(btn_box)

        # Populate if editing
        if self.is_edit:
            self.txt_title.setText(self.expense.get("title", ""))
            amt = int(self.expense.get("amount", 0))
            self.txt_amount.setText(f"{amt:,}")
            self.date_picker.setText(self.expense.get("date_shamsi", get_today_shamsi()))
            cat = self.expense.get("category", "")
            idx = self.combo_category.findText(cat)
            if idx >= 0:
                self.combo_category.setCurrentIndex(idx)
            self.txt_desc.setText(self.expense.get("description", ""))

            exp_uid = self.expense.get("user_id")
            if exp_uid:
                for i in range(self.combo_trainer.count()):
                    if self.combo_trainer.itemData(i) == exp_uid:
                        self.combo_trainer.setCurrentIndex(i)
                        break

    def _format_amount_input(self, text: str):
        clean = text.replace(",", "").replace("٬", "").strip()
        from yalda.utils.jalali_date import normalize_digits
        clean = normalize_digits(clean)
        if clean.isdigit():
            val = int(clean)
            formatted = f"{val:,}"
            if text != formatted:
                self.txt_amount.blockSignals(True)
                self.txt_amount.setText(formatted)
                self.txt_amount.blockSignals(False)

    def save_expense(self):
        title = self.txt_title.text().strip()
        if not title:
            QMessageBox.warning(self, "خطای ورودی", "لطفاً عنوان هزینه را وارد نمایید.")
            self.txt_title.setFocus()
            return

        amt_str = self.txt_amount.text().replace(",", "").replace("٬", "").strip()
        from yalda.utils.jalali_date import normalize_digits
        amt_str = normalize_digits(amt_str)
        if not amt_str.isdigit() or int(amt_str) <= 0:
            QMessageBox.warning(self, "خطای ورودی", "لطفاً مبلغ معتبری به تومان وارد نمایید.")
            self.txt_amount.setFocus()
            return
        amount = float(amt_str)

        date_val = self.date_picker.get_date()
        if not is_valid_shamsi(date_val):
            QMessageBox.warning(self, "خطای ورودی", "تاریخ واردشده معتبر نمی‌باشد (فرمت: YYYY/MM/DD).")
            return

        category = self.combo_category.currentText().strip()
        desc = self.txt_desc.toPlainText().strip()
        user_id = self.combo_trainer.currentData()

        try:
            if self.is_edit:
                AccountingService.update_expense(
                    expense_id=self.expense["id"],
                    title=title,
                    amount=amount,
                    expense_date_shamsi=date_val,
                    category=category,
                    description=desc,
                    user_id=user_id
                )
                QMessageBox.information(self, "موفقیت", "هزینه با موفقیت ویرایش گردید.")
            else:
                AccountingService.add_expense(
                    title=title,
                    amount=amount,
                    expense_date_shamsi=date_val,
                    category=category,
                    description=desc,
                    user_id=user_id
                )
                QMessageBox.information(self, "موفقیت", "هزینه جدید با موفقیت ثبت شد.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره اطلاعات هزینه: {str(e)}")
