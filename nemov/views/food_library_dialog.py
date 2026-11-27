from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from nemov.services.nutrition_service import NutritionService
from nemov.views.components.field_validator import (
    MicroWarningLabel, validate_food_macros
)

class FoodFormDialog(QDialog):
    def __init__(self, parent=None, food_data=None, draft_data=None):
        super().__init__(parent)
        self.food_data = food_data
        self._draft_data = draft_data
        self._was_saved = False
        self.setWindowTitle("ویرایش ماده غذایی" if food_data else "افزودن ماده غذایی جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(560, 400)
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
        self.combo_cat.addItem("چای و نوشیدنی", "beverages")

        self.txt_unit = QLineEdit("100 گرم")

        spin_style = """
            QDoubleSpinBox {
                padding-left: 24px;
                padding-right: 4px;
                padding-top: 2px;
                padding-bottom: 2px;
                font-size: 13px;
                font-weight: bold;
                min-width: 76px;
            }
        """

        self.spin_cal = QDoubleSpinBox()
        self.spin_cal.setRange(0, 2000)
        self.spin_cal.setValue(150)
        self.spin_cal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_cal.setStyleSheet(spin_style)

        self.spin_protein = QDoubleSpinBox()
        self.spin_protein.setRange(0, 100)
        self.spin_protein.setValue(20)
        self.spin_protein.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_protein.setStyleSheet(spin_style)

        self.spin_carbs = QDoubleSpinBox()
        self.spin_carbs.setRange(0, 100)
        self.spin_carbs.setValue(10)
        self.spin_carbs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_carbs.setStyleSheet(spin_style)

        self.spin_fat = QDoubleSpinBox()
        self.spin_fat.setRange(0, 100)
        self.spin_fat.setValue(2)
        self.spin_fat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_fat.setStyleSheet(spin_style)

        layout.addWidget(QLabel("نام ماده غذایی:"))
        layout.addWidget(self.txt_name)
        layout.addWidget(QLabel("دسته‌بندی:"))
        layout.addWidget(self.combo_cat)
        
        row_unit = QHBoxLayout()
        row_unit.setSpacing(10)
        row_unit.addWidget(QLabel("واحد اندازه‌گیری:"))
        row_unit.addWidget(self.txt_unit)
        row_unit.addWidget(QLabel("کالری (kcal):"))
        row_unit.addWidget(self.spin_cal)
        layout.addLayout(row_unit)

        row_macros = QHBoxLayout()
        row_macros.setSpacing(8)
        row_macros.addWidget(QLabel("پروتئین (g):"))
        row_macros.addWidget(self.spin_protein)
        row_macros.addWidget(QLabel("کربوهیدرات (g):"))
        row_macros.addWidget(self.spin_carbs)
        row_macros.addWidget(QLabel("چربی (g):"))
        row_macros.addWidget(self.spin_fat)
        layout.addLayout(row_macros)

        self.lbl_food_warn = MicroWarningLabel()
        layout.addWidget(self.lbl_food_warn)

        self.spin_cal.editingFinished.connect(self._check_food_macros)
        self.spin_protein.editingFinished.connect(self._check_food_macros)
        self.spin_carbs.editingFinished.connect(self._check_food_macros)
        self.spin_fat.editingFinished.connect(self._check_food_macros)

        btn_save = QPushButton("ذخیره تغییرات" if self.food_data else "افزودن به بانک")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

        if self.food_data:
            self.load_data()

        self._init_draft_persistence()

    def _check_food_macros(self):
        err = validate_food_macros(
            self.spin_cal.value(),
            self.spin_protein.value(),
            self.spin_carbs.value(),
            self.spin_fat.value()
        )
        self.lbl_food_warn.show_warning(err)
        return err is None

    def save(self):
        if not self._check_food_macros():
            err = validate_food_macros(
                self.spin_cal.value(),
                self.spin_protein.value(),
                self.spin_carbs.value(),
                self.spin_fat.value()
            )
            if err:
                QMessageBox.warning(self, "خطا در مقادیر تغذیه‌ای", err.replace("⚠️ ", ""))
                return
        name_fa = self.txt_name.text().strip()
        if not name_fa:
            QMessageBox.warning(self, "خطا", "لطفاً نام ماده غذایی را وارد کنید.")
            return

        # Check duplicate food name in food bank
        foods = NutritionService.get_all_foods()
        other_names = [f.name_fa for f in foods if not (self.food_data and f.id == self.food_data.id) and f.name_fa]
        if any(n.strip().lower() == name_fa.lower() for n in other_names):
            from nemov.utils.duplicate_helper import get_next_numbered_name
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

        self._was_saved = True
        if hasattr(self, "_draft_binder"):
            self._draft_binder.clear_draft(rotate_id=False)
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

    def _init_draft_persistence(self):
        import uuid
        from nemov.services.draft_service import DebouncedDraftBinder
        self._baseline_state = self.get_data()
        draft_id = (
            self._draft_data["draft_id"]
            if self._draft_data
            else (f"food_form_f{self.food_data.id}" if self.food_data else f"food_form_new_{uuid.uuid4().hex[:8]}")
        )
        self._draft_binder = DebouncedDraftBinder(
            parent=self,
            section="food_form",
            section_title="فرم ماده غذایی",
            get_payload_fn=self.get_data,
            is_dirty_fn=lambda: (not self._was_saved) and (self.get_data() != self._baseline_state),
            get_meta_fn=self._get_draft_meta,
            draft_id=draft_id,
            debounce_ms=3000,
        )
        if self._draft_data:
            self._restore_draft(self._draft_data)

        self.txt_name.textChanged.connect(self._draft_binder.schedule)
        self.txt_unit.textChanged.connect(self._draft_binder.schedule)
        self.combo_cat.currentIndexChanged.connect(self._draft_binder.schedule)
        for sp in (self.spin_cal, self.spin_protein, self.spin_carbs, self.spin_fat):
            sp.valueChanged.connect(self._draft_binder.schedule)

    def _get_draft_meta(self) -> dict:
        d = self.get_data()
        name = d.get("name_fa", "")
        action_lbl = "ویرایش ماده غذایی" if self.food_data else "افزودن ماده غذایی"
        title = f"{action_lbl}: {name}" if name else action_lbl
        return {
            "title": title,
            "summary": f"{int(round(d.get('calories') or 0))} کالری • {d.get('unit', '')}",
            "entity_id": self.food_data.id if self.food_data else None,
        }

    def _restore_draft(self, draft: dict):
        payload = draft.get("payload") or {}
        with self._draft_binder.suspended():
            self.txt_name.setText(payload.get("name_fa", "") or "")
            idx = self.combo_cat.findData(payload.get("category"))
            if idx >= 0:
                self.combo_cat.setCurrentIndex(idx)
            self.txt_unit.setText(payload.get("unit", "100 گرم") or "100 گرم")
            self.spin_cal.setValue(float(payload.get("calories") or 0.0))
            self.spin_protein.setValue(float(payload.get("protein_g") or 0.0))
            self.spin_carbs.setValue(float(payload.get("carbs_g") or 0.0))
            self.spin_fat.setValue(float(payload.get("fat_g") or 0.0))

    def closeEvent(self, event):
        if hasattr(self, "_draft_binder") and not self._was_saved:
            self._draft_binder.flush_now()
        super().closeEvent(event)

class FoodLibraryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("بانک مواد غذایی و ارزش‌های تغذیه‌ای")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        from nemov.utils.ui_scaling import clamp_minimum_size
        min_w, min_h = clamp_minimum_size(700, 500, widget=self, floor_w=600, floor_h=360)
        self.setMinimumSize(min_w, min_h)
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
            "rice": "برنج و نان", "meat": "پروتئین‌ها", "legumes": "حبوبات", "dairy": "لبنیات",
            "fruits": "میوه و سبزیجات", "nuts": "مغزها", "supplements": "مکمل‌ها", "beverages": "چای و نوشیدنی"
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
