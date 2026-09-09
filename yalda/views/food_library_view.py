from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from yalda.services.nutrition_service import NutritionService
from yalda.views.food_library_dialog import FoodFormDialog

class FoodLibraryView(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title & Add Button
        header = QHBoxLayout()
        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.clicked.connect(self.back_requested.emit)

        title = QLabel("🍎 بانک مواد و ارزش‌های غذایی")
        title.setObjectName("h1")

        btn_add = QPushButton("➕ افزودن ماده غذایی جدید")
        btn_add.clicked.connect(self.open_add_dialog)

        header.addWidget(btn_back)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_add)
        layout.addLayout(header)

        # Search Controls & Category Filter
        controls = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("جستجو در نام مواد غذایی...")
        self.txt_search.textChanged.connect(self.load_foods)

        self.combo_cat = QComboBox()
        self.combo_cat.addItem("همه دسته‌بندی‌ها", "all")
        self.combo_cat.addItem("برنج و نان (کربوهیدرات)", "rice")
        self.combo_cat.addItem("گوشت و مرغ و ماهی (پروتئین)", "meat")
        self.combo_cat.addItem("لبنیات", "dairy")
        self.combo_cat.addItem("میوه و سبزیجات", "fruits")
        self.combo_cat.addItem("مغزها و چربی‌های مفید", "nuts")
        self.combo_cat.addItem("مکمل‌های ورزشی", "supplements")
        self.combo_cat.currentIndexChanged.connect(self.load_foods)

        controls.addWidget(QLabel("جستجو:"))
        controls.addWidget(self.txt_search)
        controls.addWidget(QLabel("دسته‌بندی:"))
        controls.addWidget(self.combo_cat)
        layout.addLayout(controls)

        # Foods Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["نام ماده غذایی", "دسته‌بندی", "واحد اندازه‌گیری", "کالری (kcal)", "پروتئین (g)", "کربوهیدرات (g)", "چربی (g)", "عملیات"])
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 150)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)
        self.load_foods()

    def load_foods(self):
        search_query = self.txt_search.text().strip()
        category = self.combo_cat.currentData()
        foods = NutritionService.get_all_foods(category=category, search_query=search_query)

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

            # Operations Widget (Edit, Delete)
            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(5)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setFixedHeight(30)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("""
                QPushButton {
                    background-color: #8B0000;
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                    padding: 2px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #A91D22;
                }
            """)
            btn_edit.clicked.connect(lambda _, item=f: self.open_edit_dialog(item))

            btn_delete = QPushButton("🗑️")
            btn_delete.setToolTip("حذف ماده غذایی")
            btn_delete.setFixedSize(30, 30)
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #D32F2F;
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                    padding: 2px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #B71C1C;
                }
            """)
            btn_delete.clicked.connect(lambda _, item=f: self.delete_food(item))

            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_delete)

            self.table.setCellWidget(row, 7, btn_container)

    def delete_food(self, food):
        reply = QMessageBox.question(
            self, "تایید حذف ماده غذایی",
            f"آیا از حذف ماده غذایی '{food.name_fa}' از بانک مواد غذایی اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            NutritionService.delete_food(food.id)
            self.load_foods()
            QMessageBox.information(self, "موفقیت", "ماده غذایی با موفقیت حذف شد.")

    def open_add_dialog(self):
        dlg = FoodFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            NutritionService.add_custom_food(data)
            self.load_foods()
            QMessageBox.information(self, "موفقیت", "ماده غذایی جدید به بانک اضافه شد.")

    def open_edit_dialog(self, food):
        dlg = FoodFormDialog(self, food_data=food)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            NutritionService.update_food(food.id, data)
            self.load_foods()
            QMessageBox.information(self, "موفقیت", "ماده غذایی با موفقیت ویرایش شد.")
