from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from yalda.services.nutrition_service import NutritionService
from yalda.views.food_library_dialog import FoodFormDialog
from yalda.views.components.undo_delete_banner import UndoDeleteBanner

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

        # Header Bar
        header = QHBoxLayout()
        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.clicked.connect(self.back_requested.emit)

        title = QLabel("🥗 بانک مواد غذایی و ارزش تغذیه‌ای")
        title.setObjectName("h1")

        btn_add = QPushButton("➕ افزودن ماده غذایی جدید")
        btn_add.setFixedHeight(36)
        btn_add.clicked.connect(self.open_add_dialog)

        header.addWidget(btn_back)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_add)
        layout.addLayout(header)

        # Search & Filter Controls
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

        self.chk_select_all = QCheckBox("انتخاب همه")
        self.chk_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_select_all.toggled.connect(self.toggle_select_all)

        self.btn_bulk_delete = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete.setFixedHeight(32)
        self.btn_bulk_delete.setEnabled(False)
        self.btn_bulk_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bulk_delete.setStyleSheet("""
            QPushButton {
                background-color: #7B1113;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #9B1B1E;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #777777;
            }
        """)
        self.btn_bulk_delete.clicked.connect(self.bulk_delete_foods)

        controls.addWidget(QLabel("جستجو:"))
        controls.addWidget(self.txt_search)
        controls.addWidget(QLabel("دسته‌بندی:"))
        controls.addWidget(self.combo_cat)
        controls.addSpacing(10)
        controls.addWidget(self.chk_select_all)
        controls.addWidget(self.btn_bulk_delete)
        layout.addLayout(controls)

        # Foods Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["انتخاب", "نام ماده غذایی", "دسته‌بندی", "واحد اندازه‌گیری", "کالری (kcal)", "پروتئین (g)", "کربوهیدرات (g)", "چربی (g)", "عملیات"])
        self.table.verticalHeader().setDefaultSectionSize(52)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 52)   # انتخاب
        self.table.setColumnWidth(2, 120)  # دسته‌بندی
        self.table.setColumnWidth(3, 135)  # واحد اندازه‌گیری
        self.table.setColumnWidth(4, 95)   # کالری (kcal)
        self.table.setColumnWidth(5, 85)   # پروتئین (g)
        self.table.setColumnWidth(6, 105)  # کربوهیدرات (g)
        self.table.setColumnWidth(7, 85)   # چربی (g)
        self.table.setColumnWidth(8, 145)  # عملیات

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table, 1)

        self.undo_banner = UndoDeleteBanner(self)
        layout.addWidget(self.undo_banner)

        self.load_foods()

    def load_foods(self):
        search_query = self.txt_search.text().strip()
        category = self.combo_cat.currentData()
        foods = NutritionService.get_all_foods(category=category, search_query=search_query)

        cat_map = {
            "rice": "برنج و نان", "meat": "پروتئین‌ها", "dairy": "لبنیات",
            "fruits": "میوه و سبزیجات", "nuts": "مغزها", "supplements": "مکمل‌ها"
        }

        self.chk_select_all.blockSignals(True)
        self.chk_select_all.setChecked(False)
        self.chk_select_all.blockSignals(False)
        self.btn_bulk_delete.setText("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete.setEnabled(False)

        self.table.setRowCount(0)
        self.table.setRowCount(len(foods))
        for row, f in enumerate(foods):
            # Checkbox in column 0
            chk_w = QWidget()
            chk_w.setStyleSheet("background: transparent;")
            chk_l = QHBoxLayout(chk_w)
            chk_l.setContentsMargins(0, 0, 0, 0)
            chk_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setProperty("item_id", f.id)
            chk.setProperty("item_name", f.name_fa)
            chk.toggled.connect(self.on_row_checkbox_toggled)
            chk_l.addWidget(chk)
            self.table.setCellWidget(row, 0, chk_w)

            self.table.setItem(row, 1, QTableWidgetItem(f.name_fa))
            self.table.setItem(row, 2, QTableWidgetItem(cat_map.get(f.category, f.category)))
            self.table.setItem(row, 3, QTableWidgetItem(f.unit or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{int(f.calories or 0)} kcal"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{int(f.protein_g or 0)}g"))
            self.table.setItem(row, 6, QTableWidgetItem(f"{int(f.carbs_g or 0)}g"))
            self.table.setItem(row, 7, QTableWidgetItem(f"{int(f.fat_g or 0)}g"))

            # Operations Widget (Edit, Delete)
            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(5)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setFixedSize(78, 30)
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

            btn_delete = QPushButton("🗑️")
            btn_delete.setToolTip("حذف ماده غذایی")
            btn_delete.setFixedSize(32, 30)
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

            self.table.setCellWidget(row, 8, btn_container)

    def toggle_select_all(self, checked):
        for r in range(self.table.rowCount()):
            cell_w = self.table.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(checked)
                    chk.blockSignals(False)
        self.on_row_checkbox_toggled()

    def on_row_checkbox_toggled(self):
        count = len(self.get_selected_food_ids())
        total = self.table.rowCount()
        self.chk_select_all.blockSignals(True)
        self.chk_select_all.setChecked(count == total if total > 0 else False)
        self.chk_select_all.blockSignals(False)

        if count > 0:
            fa_num = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.btn_bulk_delete.setText(f"🗑️ حذف انتخاب‌شده‌ها ({fa_num})")
            self.btn_bulk_delete.setEnabled(True)
        else:
            self.btn_bulk_delete.setText("🗑️ حذف انتخاب‌شده‌ها")
            self.btn_bulk_delete.setEnabled(False)

    def get_selected_food_ids(self):
        selected_ids = []
        for r in range(self.table.rowCount()):
            cell_w = self.table.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    selected_ids.append(chk.property("item_id"))
        return selected_ids

    def bulk_delete_foods(self):
        selected_ids = self.get_selected_food_ids()
        if not selected_ids:
            return

        count = len(selected_ids)
        fa_count = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        reply = QMessageBox.question(
            self, "تایید حذف گروهی",
            f"آیا از حذف {fa_count} ماده غذایی انتخاب‌شده اطمینان دارید؟\n\nنکته: پس از حذف، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_rows_by_ids(selected_ids)

        def commit_delete(ids):
            for fid in ids:
                NutritionService.delete_food(fid)
            self.load_foods()

        def undo_delete(ids):
            self.load_foods()
            QMessageBox.information(self, "بازگردانی", "مواد غذایی با موفقیت بازگردانده شدند.")

        self.undo_banner.start_countdown(count, selected_ids, commit_delete, undo_delete, "ماده غذایی")

    def _hide_rows_by_ids(self, ids_to_hide):
        ids_set = set(ids_to_hide)
        for r in range(self.table.rowCount() - 1, -1, -1):
            cell_w = self.table.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.property("item_id") in ids_set:
                    self.table.hideRow(r)
        self.btn_bulk_delete.setText("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete.setEnabled(False)
        self.chk_select_all.setChecked(False)

    def delete_food(self, food):
        reply = QMessageBox.question(
            self, "تایید حذف ماده غذایی",
            f"آیا از حذف ماده غذایی '{food.name_fa}' از بانک مطمئن هستید؟\n\nنکته: پس از حذف، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._hide_rows_by_ids([food.id])
            self.undo_banner.start_countdown(
                1, [food.id],
                on_commit=lambda ids: [NutritionService.delete_food(fid) for fid in ids] and self.load_foods(),
                on_undo=lambda ids: self.load_foods(),
                item_label="ماده غذایی"
            )

    def open_add_dialog(self):
        dlg = FoodFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            NutritionService.create_food(data)
            self.load_foods()
            QMessageBox.information(self, "موفقیت", "ماده غذایی جدید با موفقیت اضافه شد.")

    def open_edit_dialog(self, food):
        dlg = FoodFormDialog(self, food_data=food)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            NutritionService.update_food(food.id, data)
            self.load_foods()
            QMessageBox.information(self, "موفقیت", "ماده غذایی با موفقیت ویرایش شد.")
