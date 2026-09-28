from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from yalda.services.nutrition_service import NutritionService

class FoodFormDialog(QDialog):
    def __init__(self, parent=None, food_data=None):
        super().__init__(parent)
        self.food_data = food_data
        self.setWindowTitle("ویرایش ماده غذایی" if food_data else "افزودن ماده غذایی جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(500, 390)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("نام ماده غذایی به فارسی...")

        self.combo_cat = QComboBox()
        self.combo_cat.addItem("برنج و نان (کربوهیدرات)", "rice")
        self.combo_cat.addItem("گوشت و مرغ و ماهی (پروتئین)", "meat")
        self.combo_cat.addItem("حبوبات", "legumes")
        self.combo_cat.addItem("لبنیات", "dairy")
        self.combo_cat.addItem("میوه و سبزیجات", "fruits")
        self.combo_cat.addItem("مغزها و چربی‌های مفید", "nuts")
        self.combo_cat.addItem("مکمل‌های ورزشی", "supplements")

        self.txt_unit = QLineEdit("100 گرم")

        self.spin_cal = QDoubleSpinBox()
        self.spin_cal.setRange(0, 2000)
        self.spin_cal.setValue(150)
        self.spin_cal.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spin_protein = QDoubleSpinBox()
        self.spin_protein.setRange(0, 100)
        self.spin_protein.setValue(20)
        self.spin_protein.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spin_carbs = QDoubleSpinBox()
        self.spin_carbs.setRange(0, 100)
        self.spin_carbs.setValue(10)
        self.spin_carbs.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spin_fat = QDoubleSpinBox()
        self.spin_fat.setRange(0, 100)
        self.spin_fat.setValue(2)
        self.spin_fat.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(QLabel("نام ماده غذایی:"))
        layout.addWidget(self.txt_name)
        layout.addWidget(QLabel("دسته‌بندی:"))
        layout.addWidget(self.combo_cat)
        
        row_unit = QHBoxLayout()
        row_unit.addWidget(QLabel("واحد اندازه‌گیری:"))
        row_unit.addWidget(self.txt_unit)
        row_unit.addWidget(QLabel("کالری (kcal):"))
        row_unit.addWidget(self.spin_cal)
        layout.addLayout(row_unit)

        row_macros = QHBoxLayout()
        row_macros.addWidget(QLabel("پروتئین (g):"))
        row_macros.addWidget(self.spin_protein)
        row_macros.addWidget(QLabel("کربوهیدرات (g):"))
        row_macros.addWidget(self.spin_carbs)
        row_macros.addWidget(QLabel("چربی (g):"))
        row_macros.addWidget(self.spin_fat)
        layout.addLayout(row_macros)

        btn_save = QPushButton("ذخیره تغییرات" if self.food_data else "افزودن به بانک")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

        if self.food_data:
            self.load_data()

    def save(self):
        name_fa = self.txt_name.text().strip()
        if not name_fa:
            QMessageBox.warning(self, "خطا", "لطفاً نام ماده غذایی را وارد کنید.")
            return

        # Check duplicate food name in food bank
        foods = NutritionService.get_all_foods()
        other_names = [f.name_fa for f in foods if not (self.food_data and f.id == self.food_data.id) and f.name_fa]
        if any(n.strip().lower() == name_fa.lower() for n in other_names):
            from yalda.utils.duplicate_helper import get_next_numbered_name
            suggested_name = get_next_numbered_name(name_fa, other_names)
            reply = QMessageBox.question(
                self,
                "هشدار ماده غذایی تکراری",
                f"ماده غذایی با عنوان «{name_fa}» از قبل در بانک مواد غذایی ثبت شده است.\n\nدر صورت تایید، این مورد با عنوان «{suggested_name}» ذخیره خواهد شد.\nآیا مایل به ذخیره هستید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.txt_name.setFocus()
                return
            self.txt_name.setText(suggested_name)

        self.accept()

    def get_data(self):
        return {
            "name_fa": self.txt_name.text().strip(),
            "category": self.combo_cat.currentData(),
            "unit": self.txt_unit.text().strip() or "100 گرم",
            "calories": self.spin_cal.value(),
            "protein_g": self.spin_protein.value(),
            "carbs_g": self.spin_carbs.value(),
            "fat_g": self.spin_fat.value()
        }

    def load_data(self):
        f = self.food_data
        self.txt_name.setText(f.name_fa or "")
        idx = self.combo_cat.findData(f.category)
        if idx >= 0: self.combo_cat.setCurrentIndex(idx)
        self.txt_unit.setText(f.unit or "100 گرم")
        self.spin_cal.setValue(f.calories or 0)
        self.spin_protein.setValue(f.protein_g or 0)
        self.spin_carbs.setValue(f.carbs_g or 0)
        self.spin_fat.setValue(f.fat_g or 0)

class FoodLibraryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("بانک مواد غذایی و ارزش‌های تغذیه‌ای")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumSize(700, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        header = QHBoxLayout()
        lbl_title = QLabel("🥗 لیست و ارزش‌های مواد غذایی")
        lbl_title.setObjectName("h2")

        btn_add = QPushButton("➕ افزودن ماده غذایی جدید")
        btn_add.clicked.connect(self.open_add_dialog)

        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(btn_add)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["نام", "دسته‌بندی", "واحد", "کالری", "پروتئین", "کربوهیدرات", "چربی", "عملیات"])
        self.table.verticalHeader().setDefaultSectionSize(40)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 85)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 95)
        self.table.setColumnWidth(6, 80)
        self.table.setColumnWidth(7, 90)

        layout.addWidget(self.table)
        self.load_foods()

    def load_foods(self):
        foods = NutritionService.get_all_foods()
        cat_map = {
            "rice": "برنج و نان", "meat": "پروتئین‌ها", "dairy": "لبنیات",
            "fruits": "میوه و سبزیجات", "nuts": "مغزها", "supplements": "مکمل‌ها"
        }

        self.table.setRowCount(len(foods))
        for row, f in enumerate(foods):
            self.table.setItem(row, 0, QTableWidgetItem(f.name_fa))
            self.table.setItem(row, 1, QTableWidgetItem(cat_map.get(f.category, f.category)))
            self.table.setItem(row, 2, QTableWidgetItem(f.unit or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{int(f.calories or 0)} kcal"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{int(f.protein_g or 0)}g"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{int(f.carbs_g or 0)}g"))
            self.table.setItem(row, 6, QTableWidgetItem(f"{int(f.fat_g or 0)}g"))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setFixedSize(72, 30)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("""
                QPushButton {
                    background-color: #D97706;
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                    padding: 2px 6px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #B45309;
                }
            """)
            btn_edit.clicked.connect(lambda _, item=f: self.open_edit_dialog(item))
            self.table.setCellWidget(row, 7, btn_edit)

    def open_add_dialog(self):
        dlg = FoodFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            NutritionService.add_custom_food(data)
            self.load_foods()
            QMessageBox.information(self, "موفقیت", "ماده غذایی جدید اضافه شد.")

    def open_edit_dialog(self, food):
        dlg = FoodFormDialog(self, food_data=food)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            NutritionService.update_food(food.id, data)
            self.load_foods()
            QMessageBox.information(self, "موفقیت", "ماده غذایی با موفقیت ویرایش شد.")
