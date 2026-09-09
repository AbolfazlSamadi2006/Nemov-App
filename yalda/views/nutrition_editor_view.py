from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTabWidget, QTableWidget, QHeaderView, QMessageBox, QGroupBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from yalda.services.nutrition_service import NutritionService
from yalda.services.member_service import MemberService
from yalda.views.components.searchable_combo_box import SearchableComboBox
from yalda.views.components.day_management_dialogs import DaySelectionReductionDialog, DayIncreaseChoiceDialog

class NutritionEditorView(QWidget):
    manage_templates_requested = pyqtSignal()
    open_food_bank_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.meal_tables = []
        self.editing_plan_id = None
        self._undo_stack = []
        self._redo_stack = []
        self._undo_buttons = []
        self._redo_buttons = []
        self._is_undoing_redoing = False
        self._days_cache = {}
        self._prev_days_mode = "7_days"
        self.init_ui()

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_members_dropdown()
        self.load_template_dropdown()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title & Action Buttons
        header = QHBoxLayout()
        self.lbl_header_title = QLabel("🥗 برنامه‌ریزی تغذیه")
        self.lbl_header_title.setObjectName("h1")

        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.clicked.connect(self.back_requested.emit)

        btn_reset = QPushButton("🔄 بازنشانی تغییرات")
        btn_reset.setObjectName("secondary_button")
        btn_reset.clicked.connect(self.revert_changes)

        btn_new_plan = QPushButton("➕ رژیم جدید")
        btn_new_plan.setObjectName("secondary_button")
        btn_new_plan.clicked.connect(self.reset_form)

        btn_manage_tpl = QPushButton("📋 مدیریت و مشاهده الگوها")
        btn_manage_tpl.setObjectName("secondary_button")
        btn_manage_tpl.clicked.connect(self.manage_templates_requested.emit)

        btn_food_bank = QPushButton("🥗 بانک مواد غذایی")
        btn_food_bank.setObjectName("secondary_button")
        btn_food_bank.clicked.connect(self.open_food_bank_requested.emit)

        header.addWidget(btn_back)
        header.addWidget(self.lbl_header_title)
        header.addStretch()
        header.addWidget(btn_reset)
        header.addWidget(btn_new_plan)
        header.addWidget(btn_manage_tpl)
        header.addWidget(btn_food_bank)
        layout.addLayout(header)

        # Program Details Form Box
        form_box = QGroupBox("مشخصات کلی برنامه غذایی")
        layout_form = QVBoxLayout(form_box)
        layout_form.setSpacing(10)
        layout_form.setContentsMargins(12, 12, 12, 12)

        # Template Picker Row (Full width like Workout Editor)
        row_tpl = QHBoxLayout()
        row_tpl.setSpacing(10)
        self.combo_templates = QComboBox()
        self.combo_templates.addItem("--- انتخاب و بارگذاری الگوی آماده از بانک ---", None)
        self.load_template_dropdown()
        self.combo_templates.currentIndexChanged.connect(self.on_template_selected)

        row_tpl.addWidget(QLabel("📂 الگوهای آماده بانک:"))
        row_tpl.addWidget(self.combo_templates)
        layout_form.addLayout(row_tpl)

        # Row 2: Title -> Goal -> Days Pattern
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        lbl_title = QLabel("عنوان رژیم:")
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("مثلاً: رژیم افزایش حجم عضلانی...")
        self.txt_title.textEdited.connect(lambda: self._snapshot_change())

        lbl_goal = QLabel("هدف رژیم:")
        self.combo_goal = QComboBox()
        self.combo_goal.addItem("عضله‌سازی (Muscle Gain)", "muscle_gain")
        self.combo_goal.addItem("کاهش وزن و چربی‌سوزی (Weight Loss)", "weight_loss")
        self.combo_goal.addItem("افزایش وزن (Weight Gain)", "weight_gain")
        self.combo_goal.addItem("تثبیت وزن (Maintenance)", "maintenance")
        self.combo_goal.currentIndexChanged.connect(lambda: self._snapshot_change())

        lbl_days = QLabel("روزهای هفته:")
        self.combo_days = QComboBox()
        self.combo_days.addItem("📅 شنبه تا جمعه (۷ روز هفته)", "7_days")
        self.combo_days.addItem("📅 روزهای تمرین و استراحت (۲ روزه)", "2_days")
        self.combo_days.addItem("📅 ۳ روز در هفته", "3_days")
        self.combo_days.addItem("📅 ۴ روز در هفته", "4_days")
        self.combo_days.addItem("📅 ۵ روز در هفته", "5_days")
        self.combo_days.addItem("📅 ۶ روز در هفته", "6_days")
        self.combo_days.addItem("📅 الگوی ثابت (کلیه روزهای هفته)", "all_days")
        self.combo_days.currentIndexChanged.connect(self.on_days_pattern_changed)

        row1.addWidget(lbl_title)
        row1.addWidget(self.txt_title, 2)
        row1.addWidget(lbl_goal)
        row1.addWidget(self.combo_goal, 1)
        row1.addWidget(lbl_days)
        row1.addWidget(self.combo_days, 1)
        layout_form.addLayout(row1)

        layout.addWidget(form_box)

        # Tabs for Meals
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        layout.addWidget(self.tabs)
        self.setup_meal_tabs()

        # Assignment Box & Actions
        assign_box = QGroupBox("تخصیص برنامه تغذیه به ورزشکار")
        layout_assign = QHBoxLayout(assign_box)

        self.combo_member = SearchableComboBox(placeholder="جستجو یا تایپ نام ورزشکار...")
        self.combo_member.setFixedHeight(36)
        self.combo_member.setMinimumWidth(260)
        self.load_members_dropdown()

        btn_save = QPushButton("💾 ذخیره الگوی رژیم در بانک")
        btn_save.setObjectName("secondary_button")
        btn_save.clicked.connect(self.save_plan)

        btn_assign = QPushButton("✅ تخصیص به ورزشکار")
        btn_assign.clicked.connect(self.assign_plan)

        layout_assign.addWidget(QLabel("انتخاب ورزشکار:"))
        layout_assign.addWidget(self.combo_member)
        layout_assign.addStretch()
        layout_assign.addWidget(btn_save)
        layout_assign.addWidget(btn_assign)

        layout.addWidget(assign_box)

    def load_members_dropdown(self):
        cur = self.combo_member.currentData()
        self.combo_member.blockSignals(True)
        self.combo_member.clear()
        members = MemberService.get_all_members(status_filter="active")
        for m in members:
            self.combo_member.addItem(m.full_name, m.id)
        if cur is not None:
            idx = self.combo_member.findData(cur)
            if idx >= 0:
                self.combo_member.setCurrentIndex(idx)
            else:
                self.combo_member.set_empty()
        else:
            self.combo_member.set_empty()
        self.combo_member.blockSignals(False)

    def set_selected_member(self, member_id: int):
        self.load_members_dropdown()
        idx = self.combo_member.findData(member_id)
        if idx >= 0:
            self.combo_member.setCurrentIndex(idx)

    def load_template_dropdown(self):
        cur = self.combo_templates.currentData()
        self.combo_templates.blockSignals(True)
        self.combo_templates.clear()
        self.combo_templates.addItem("--- انتخاب و بارگذاری الگوی آماده رژیم از بانک ---", None)
        plans = NutritionService.get_all_plans()
        for p in plans:
            goal_title = {
                "muscle_gain": "عضله‌سازی",
                "weight_loss": "کاهش وزن",
                "weight_gain": "افزایش وزن",
                "maintenance": "تثبیت وزن"
            }.get(p.goal, p.goal)
            self.combo_templates.addItem(f"🥗 {p.title} ({goal_title})", p.id)
        if cur is not None:
            idx = self.combo_templates.findData(cur)
            if idx >= 0:
                self.combo_templates.setCurrentIndex(idx)
        else:
            self.combo_templates.setCurrentIndex(0)
        self.combo_templates.blockSignals(False)

    def _load_plan_data_to_form(self, plan):
        if not plan:
            return
        self._loading_plan = True
        try:
            self.txt_title.setText(plan.title or "")

            idx_g = self.combo_goal.findData(plan.goal)
            if idx_g >= 0:
                self.combo_goal.setCurrentIndex(idx_g)

            # Detect days pattern from meal names in plan
            has_7_days = any(any(d in m.meal_name for d in ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]) for m in plan.meals)
            has_2_days = any("تمرین" in m.meal_name or "استراحت" in m.meal_name for m in plan.meals)
            max_day_num = 0
            for m in plan.meals:
                for n in range(1, 8):
                    if f"روز {n}" in m.meal_name and n > max_day_num:
                        max_day_num = n

            self._days_cache.clear()
            self.combo_days.blockSignals(True)
            if has_2_days:
                pattern_key = "2_days"
            elif has_7_days:
                pattern_key = "7_days"
            elif max_day_num in (3, 4, 5, 6):
                pattern_key = f"{max_day_num}_days"
            else:
                pattern_key = "all_days"

            idx_d = self.combo_days.findData(pattern_key)
            if idx_d >= 0:
                self.combo_days.setCurrentIndex(idx_d)
            self._prev_days_mode = pattern_key
            self.combo_days.blockSignals(False)

            # Rebuild meal tabs
            self.setup_meal_tabs()

            foods_list = NutritionService.get_all_foods()

            meal_alias_map = {
                "breakfast": ["breakfast", "صبحانه"],
                "morning_snack": ["morning_snack", "میان‌وعده صبح", "میان وعده صبح"],
                "lunch": ["lunch", "ناهار"],
                "afternoon_snack": ["afternoon_snack", "عصرانه"],
                "dinner": ["dinner", "شام"],
                "evening_snack": ["evening_snack", "قبل از خواب", "خواب"]
            }
            day_keys = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "تمرین", "استراحت", "روز اول", "روز دوم", "روز سوم", "روز چهارم", "روز پنجم", "روز ششم"]

            def match_meal(table_k, m_name):
                if table_k == m_name or m_name in table_k or table_k in m_name:
                    return True
                for meal_code, aliases in meal_alias_map.items():
                    if any(a in table_k for a in aliases):
                        if any(a in m_name for a in aliases):
                            t_day = next((d for d in day_keys if d in table_k), None)
                            m_day = next((d for d in day_keys if d in m_name), None)
                            if t_day and m_day:
                                return t_day == m_day
                            if t_day and not m_day:
                                return t_day == "شنبه" or len(plan.meals) <= 6
                            return True
                return False

            for meal_key, table in self.meal_tables:
                table.setRowCount(0)
                matched_m = None
                for m in plan.meals:
                    if match_meal(meal_key, m.meal_name):
                        matched_m = m
                        break

                if matched_m and matched_m.items:
                    for item in matched_m.items:
                        r = table.rowCount()
                        table.insertRow(r)
                        self._create_food_row_widgets(table, r, foods_list, {
                            "food_id": item.food_id,
                            "amount": item.amount or 1.0,
                            "notes": item.notes or ""
                        })
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._last_state = self._capture_state()
            self._update_undo_redo_ui()
        finally:
            self._loading_plan = False

    def on_template_selected(self, index: int):
        try:
            plan_id = self.combo_templates.currentData()
            if not plan_id:
                return

            plan = NutritionService.get_plan_by_id(plan_id)
            if not plan:
                return

            self._load_plan_data_to_form(plan)
            QMessageBox.information(self, "موفقیت", f"الگوی رژیم '{plan.title}' با موفقیت در فرم بارگذاری شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری الگوی رژیم: {str(e)}")

    def _get_day_names_for_mode(self, days_mode: str) -> list:
        day_names_map = {
            "7_days": ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"],
            "2_days": ["روزهای تمرینی", "روزهای استراحت"],
            "3_days": ["روز اول", "روز دوم", "روز سوم"],
            "4_days": ["روز اول", "روز دوم", "روز سوم", "روز چهارم"],
            "5_days": ["روز اول", "روز دوم", "روز سوم", "روز چهارم", "روز پنجم"],
            "6_days": ["روز اول", "روز دوم", "روز سوم", "روز چهارم", "روز پنجم", "روز ششم"],
        }
        return day_names_map.get(days_mode, ["برنامه کلیه روزهای هفته"])

    def _on_tab_moved(self, from_idx: int, to_idx: int):
        if from_idx == to_idx:
            return
        days_mode = self.combo_days.currentData() or "all_days"
        if days_mode == "all_days":
            return

        num_days = self.tabs.count()
        if len(self.meal_tables) == num_days * 6 and 0 <= from_idx < num_days and 0 <= to_idx < num_days:
            start_from = from_idx * 6
            moved_chunk = self.meal_tables[start_from : start_from + 6]
            del self.meal_tables[start_from : start_from + 6]
            start_to = to_idx * 6
            self.meal_tables[start_to : start_to] = moved_chunk

            names = self._get_day_names_for_mode(days_mode)
            for i in range(self.tabs.count()):
                if i < len(names):
                    self.tabs.setTabText(i, f"📅 {names[i]}")

            for d in range(num_days):
                day_tab_text = self.tabs.tabText(d).replace("📅", "").strip()
                for m_idx in range(6):
                    table_idx = d * 6 + m_idx
                    if table_idx < len(self.meal_tables):
                        old_key, tbl = self.meal_tables[table_idx]
                        meal_title = old_key.split(":", 1)[1].strip() if ":" in old_key else old_key
                        new_key = f"{day_tab_text}: {meal_title}"
                        self.meal_tables[table_idx] = (new_key, tbl)

            self._snapshot_change()

    def _extract_table_items(self, table: QTableWidget) -> list:
        items = []
        for r in range(table.rowCount()):
            combo = table.cellWidget(r, 0)
            f_id = combo.currentData() if combo else None
            f_text = combo.currentText() if combo else ""
            txt_amount = table.cellWidget(r, 1)
            txt_notes = table.cellWidget(r, 2)
            items.append({
                "food_id": f_id,
                "food_text": f_text,
                "amount": txt_amount.text() if txt_amount else "1.0",
                "notes": txt_notes.text() if txt_notes else ""
            })
        return items

    def _extract_current_nutrition_days_data(self) -> list:
        days_data = []
        days_mode = self.combo_days.currentData() or "all_days"

        if days_mode == "all_days":
            meals_list = []
            for meal_key, table in self.meal_tables:
                items = self._extract_table_items(table)
                meals_list.append({"meal_title": meal_key, "items": items})
            days_data.append({"day_title": "برنامه کلیه روزهای هفته", "meals": meals_list})
        else:
            num_days = self.tabs.count()
            for d in range(num_days):
                day_tab_text = self.tabs.tabText(d).replace("📅", "").strip()
                meals_list = []
                day_slice = self.meal_tables[d * 6 : (d + 1) * 6]
                for full_key, table in day_slice:
                    items = self._extract_table_items(table)
                    meal_title = full_key.split(":", 1)[1].strip() if ":" in full_key else full_key
                    meals_list.append({"meal_title": meal_title, "items": items})
                days_data.append({"day_title": day_tab_text, "meals": meals_list})
        return days_data

    def _has_non_empty_nutrition_days(self, days_data: list) -> bool:
        if not days_data:
            return False
        for d in days_data:
            for m in d.get("meals", []):
                for item in m.get("items", []):
                    if item.get("food_id") or (item.get("food_text") and "انتخاب" not in item.get("food_text")):
                        return True
        return False

    def on_days_pattern_changed(self):
        new_mode = self.combo_days.currentData() or "all_days"
        old_mode = getattr(self, '_prev_days_mode', "7_days")
        if new_mode == old_mode:
            return

        mode_to_count = {
            "all_days": 1,
            "2_days": 2,
            "3_days": 3,
            "4_days": 4,
            "5_days": 5,
            "6_days": 6,
            "7_days": 7
        }
        old_count = mode_to_count.get(old_mode, len(self.tabs))
        new_count = mode_to_count.get(new_mode, 1)

        current_days = self._extract_current_nutrition_days_data()
        self._days_cache[old_mode] = current_days

        selected_days = None

        if new_count < old_count:
            # Decreasing
            summary = []
            for idx, d in enumerate(current_days):
                tot_food = sum(len([item for item in m.get("items", []) if item.get("food_id") or (item.get("food_text") and "انتخاب" not in item.get("food_text"))]) for m in d.get("meals", []))
                summary.append((idx, d.get("day_title", f"روز {idx+1}"), f"{tot_food} ماده غذایی"))

            dlg = DaySelectionReductionDialog(summary, new_count, self, is_nutrition=True)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.combo_days.blockSignals(True)
                idx = self.combo_days.findData(old_mode)
                if idx >= 0: self.combo_days.setCurrentIndex(idx)
                self.combo_days.blockSignals(False)
                return

            if dlg.start_fresh:
                selected_days = []
            else:
                selected_days = [current_days[i] for i in dlg.selected_indices if i < len(current_days)]

        else:
            # Increasing
            cached_plan = self._days_cache.get(new_mode)
            has_cached = bool(cached_plan and self._has_non_empty_nutrition_days(cached_plan))

            dlg = DayIncreaseChoiceDialog(new_count, old_count, self, is_nutrition=True, has_cached_plan=has_cached)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.combo_days.blockSignals(True)
                idx = self.combo_days.findData(old_mode)
                if idx >= 0: self.combo_days.setCurrentIndex(idx)
                self.combo_days.blockSignals(False)
                return

            if dlg.choice == "restore" and cached_plan:
                selected_days = cached_plan
            elif dlg.choice == "fresh":
                selected_days = []
            else:
                selected_days = current_days

        self._prev_days_mode = new_mode
        self.setup_meal_tabs_with_data(new_mode, selected_days)
        self._snapshot_change()

    def _capture_state(self):
        state = {
            "title": self.txt_title.text(),
            "goal": self.combo_goal.currentData(),
            "days_pattern": self.combo_days.currentData(),
            "tab_index": self.tabs.currentIndex(),
            "meals": []
        }
        for meal_key, table in self.meal_tables:
            meal_items = []
            for r in range(table.rowCount()):
                combo = table.cellWidget(r, 0)
                f_id = combo.currentData() if combo else None
                f_text = combo.currentText() if combo else ""
                txt_amount = table.cellWidget(r, 1)
                txt_notes = table.cellWidget(r, 2)
                meal_items.append({
                    "food_id": f_id,
                    "food_text": f_text,
                    "amount": txt_amount.text() if txt_amount else "1.0",
                    "notes": txt_notes.text() if txt_notes else ""
                })
            state["meals"].append({
                "meal_key": meal_key,
                "items": meal_items
            })
        return state

    def _snapshot_change(self):
        if self._is_undoing_redoing or getattr(self, '_loading_plan', False):
            return
        new_state = self._capture_state()
        if not hasattr(self, '_last_state') or self._last_state is None:
            self._last_state = new_state
            return
        if self._last_state == new_state:
            return
        self._undo_stack.append(self._last_state)
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._last_state = new_state
        self._update_undo_redo_ui()

    def _push_undo_state(self):
        self._snapshot_change()

    def undo(self):
        if not self._undo_stack:
            return
        current = self._capture_state()
        self._redo_stack.append(current)
        prev = self._undo_stack.pop()
        self._restore_state(prev)
        self._last_state = prev
        self._update_undo_redo_ui()

    def redo(self):
        if not self._redo_stack:
            return
        current = self._capture_state()
        self._undo_stack.append(current)
        next_st = self._redo_stack.pop()
        self._restore_state(next_st)
        self._last_state = next_st
        self._update_undo_redo_ui()

    def _update_undo_redo_ui(self):
        can_undo = len(self._undo_stack) > 0
        can_redo = len(self._redo_stack) > 0
        for btn in getattr(self, '_undo_buttons', []):
            btn.setEnabled(can_undo)
        for btn in getattr(self, '_redo_buttons', []):
            btn.setEnabled(can_redo)

    def _restore_state(self, state: dict):
        self._is_undoing_redoing = True
        try:
            self.txt_title.setText(state.get("title", ""))

            idx_g = self.combo_goal.findData(state.get("goal"))
            if idx_g >= 0: self.combo_goal.setCurrentIndex(idx_g)

            pattern = state.get("days_pattern", "7_days")
            self._prev_days_mode = pattern
            idx_d = self.combo_days.findData(pattern)
            if idx_d >= 0 and self.combo_days.currentIndex() != idx_d:
                self.combo_days.blockSignals(True)
                self.combo_days.setCurrentIndex(idx_d)
                self.combo_days.blockSignals(False)
                self.setup_meal_tabs()

            foods_list = NutritionService.get_all_foods()
            state_meals = state.get("meals", [])

            for idx, (meal_key, table) in enumerate(self.meal_tables):
                if idx < len(state_meals):
                    table.setRowCount(0)
                    for itm in state_meals[idx].get("items", []):
                        r = table.rowCount()
                        table.insertRow(r)
                        self._create_food_row_widgets(table, r, foods_list, itm)

            names = self._get_day_names_for_mode(pattern)
            if pattern != "all_days":
                for i in range(self.tabs.count()):
                    if i < len(names):
                        self.tabs.setTabText(i, f"📅 {names[i]}")

            tab_idx = state.get("tab_index", 0)
            if 0 <= tab_idx < self.tabs.count():
                self.tabs.setCurrentIndex(tab_idx)
        finally:
            self._is_undoing_redoing = False

    def _create_food_row_widgets(self, table: QTableWidget, row: int, foods_list: list, data: dict = None):
        if not data:
            data = {}
        combo_food = SearchableComboBox(placeholder="جستجو یا تایپ نام ماده غذایی...")
        for f in foods_list:
            combo_food.addItem(f"{f.name_fa} ({f.unit} - {int(f.calories)}kcal)", f.id)

        f_id = data.get("food_id")
        if f_id:
            idx_f = combo_food.findData(f_id)
            if idx_f >= 0:
                combo_food.setCurrentIndex(idx_f)
            else:
                combo_food.set_empty()
        elif data.get("food_text"):
            combo_food.setCurrentText(data["food_text"])
        else:
            combo_food.set_empty()

        txt_amount = QLineEdit(str(data.get("amount", "1.0")))
        txt_amount.setAlignment(Qt.AlignmentFlag.AlignCenter)

        txt_notes = QLineEdit(str(data.get("notes", "")))
        txt_notes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt_notes.setPlaceholderText("توضیحات اختصاصی...")

        btn_del = QPushButton("🗑️")
        btn_del.setObjectName("danger_button")
        btn_del.setToolTip("حذف ماده غذایی")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.clicked.connect(lambda _, t=table, b=btn_del: self.remove_food_row(t, b))

        # Connect listeners to snapshot undo
        combo_food.currentIndexChanged.connect(lambda: self._snapshot_change())
        txt_amount.textEdited.connect(lambda: self._snapshot_change())
        txt_notes.textEdited.connect(lambda: self._snapshot_change())

        table.setCellWidget(row, 0, combo_food)
        table.setCellWidget(row, 1, txt_amount)
        table.setCellWidget(row, 2, txt_notes)
        table.setCellWidget(row, 3, btn_del)

    def add_food_row(self, table: QTableWidget, foods_list: list = None):
        row = table.rowCount()
        table.insertRow(row)
        if not foods_list:
            foods_list = NutritionService.get_all_foods()
        self._create_food_row_widgets(table, row, foods_list)
        self._snapshot_change()

    def remove_food_row(self, table: QTableWidget, btn: QPushButton):
        for r in range(table.rowCount()):
            if table.cellWidget(r, 3) == btn:
                table.removeRow(r)
                break
        self._snapshot_change()

    def _create_meal_widget(self, meal_key: str, meal_title: str, foods_list: list) -> QWidget:
        widget = QWidget()
        layout_meal = QVBoxLayout(widget)
        layout_meal.setContentsMargins(8, 8, 8, 8)
        layout_meal.setSpacing(10)

        row_top = QHBoxLayout()
        btn_undo = QPushButton("↩️ Undo")
        btn_undo.setObjectName("undo_button")
        btn_undo.setToolTip("بازگشت به مرحله قبل (Ctrl+Z)")
        btn_undo.clicked.connect(self.undo)

        btn_redo = QPushButton("↪️ Redo")
        btn_redo.setObjectName("redo_button")
        btn_redo.setToolTip("انجام مجدد مرحله بعد (Ctrl+Y)")
        btn_redo.clicked.connect(self.redo)

        self._undo_buttons.append(btn_undo)
        self._redo_buttons.append(btn_redo)

        btn_add_item = QPushButton("➕ افزودن ماده غذایی")
        btn_add_item.setObjectName("secondary_button")

        row_top.addStretch()
        row_top.addWidget(btn_undo)
        row_top.addWidget(btn_redo)
        row_top.addWidget(btn_add_item)
        layout_meal.addLayout(row_top)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["نام ماده غذایی", "مقدار (ضریب واحد)", "توضیحات مربی", "حذف"])
        table.verticalHeader().setDefaultSectionSize(48)
        table.verticalHeader().setMinimumSectionSize(40)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(1, 140)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(3, 60)

        btn_add_item.clicked.connect(lambda _, t=table: self.add_food_row(t, foods_list))

        layout_meal.addWidget(table)
        self.meal_tables.append((meal_key, table))
        return widget

    def setup_meal_tabs(self):
        days_mode = self.combo_days.currentData() or "all_days"
        self.setup_meal_tabs_with_data(days_mode, None)

    def setup_meal_tabs_with_data(self, days_mode: str, days_data: list = None):
        self.tabs.blockSignals(True)
        self.tabs.clear()
        self.meal_tables.clear()
        self._undo_buttons.clear()
        self._redo_buttons.clear()
        foods_list = NutritionService.get_all_foods()

        if days_mode == "7_days":
            days = [
                ("sat", "شنبه"),
                ("sun", "یکشنبه"),
                ("mon", "دوشنبه"),
                ("tue", "سه‌شنبه"),
                ("wed", "چهارشنبه"),
                ("thu", "پنج‌شنبه"),
                ("fri", "جمعه")
            ]
        elif days_mode == "2_days":
            days = [
                ("training", "روزهای تمرینی"),
                ("rest", "روزهای استراحت")
            ]
        elif days_mode == "3_days":
            days = [("day1", "روز اول"), ("day2", "روز دوم"), ("day3", "روز سوم")]
        elif days_mode == "4_days":
            days = [("day1", "روز اول"), ("day2", "روز دوم"), ("day3", "روز سوم"), ("day4", "روز چهارم")]
        elif days_mode == "5_days":
            days = [("day1", "روز اول"), ("day2", "روز دوم"), ("day3", "روز سوم"), ("day4", "روز چهارم"), ("day5", "روز پنجم")]
        elif days_mode == "6_days":
            days = [("day1", "روز اول"), ("day2", "روز دوم"), ("day3", "روز سوم"), ("day4", "روز چهارم"), ("day5", "روز پنجم"), ("day6", "روز ششم")]
        else:
            days = [("daily", "برنامه کلیه روزهای هفته")]

        meals = [
            ("breakfast", "🌅 صبحانه"),
            ("morning_snack", "🍎 میان‌وعده صبح"),
            ("lunch", "🍗 ناهار"),
            ("afternoon_snack", "🍌 عصرانه"),
            ("dinner", "🍲 شام"),
            ("evening_snack", "🥛 قبل از خواب")
        ]

        if not days_data:
            days_data = []

        if len(days) == 1:
            day_info = days_data[0] if len(days_data) > 0 else None
            meals_map = {}
            if day_info and day_info.get("meals"):
                for m_idx, m in enumerate(day_info["meals"]):
                    meals_map[m_idx] = m.get("items", [])
                    meals_map[m.get("meal_title", "")] = m.get("items", [])

            for m_idx, (meal_key, meal_title) in enumerate(meals):
                widget = self._create_meal_widget(meal_key, meal_title, foods_list)
                existing_items = meals_map.get(meal_title) or meals_map.get(m_idx) or []
                table = self.meal_tables[-1][1]
                for itm in existing_items:
                    r = table.rowCount()
                    table.insertRow(r)
                    self._create_food_row_widgets(table, r, foods_list, itm)
                self.tabs.addTab(widget, meal_title)
        else:
            for d_idx, (day_key, day_title) in enumerate(days):
                day_info = days_data[d_idx] if d_idx < len(days_data) else None
                meals_map = {}
                if day_info and day_info.get("meals"):
                    for m_idx, m in enumerate(day_info["meals"]):
                        meals_map[m_idx] = m.get("items", [])
                        meals_map[m.get("meal_title", "")] = m.get("items", [])

                day_tab_widget = QTabWidget()
                for m_idx, (meal_key, meal_title) in enumerate(meals):
                    full_key = f"{day_title}: {meal_title}"
                    widget = self._create_meal_widget(full_key, meal_title, foods_list)
                    existing_items = meals_map.get(meal_title) or meals_map.get(m_idx) or []
                    table = self.meal_tables[-1][1]
                    for itm in existing_items:
                        r = table.rowCount()
                        table.insertRow(r)
                        self._create_food_row_widgets(table, r, foods_list, itm)
                    day_tab_widget.addTab(widget, meal_title)
                self.tabs.addTab(day_tab_widget, f"📅 {day_title}")

        self.tabs.blockSignals(False)
        self._update_undo_redo_ui()

    def refresh_editor(self):
        self.load_members_dropdown()
        cur_tpl = self.combo_templates.currentData()
        self.combo_templates.blockSignals(True)
        self.load_template_dropdown()
        if cur_tpl is not None:
            idx = self.combo_templates.findData(cur_tpl)
            if idx >= 0:
                self.combo_templates.setCurrentIndex(idx)
        self.combo_templates.blockSignals(False)

    def get_plan_data(self):
        title = self.txt_title.text().strip() or "برنامه غذایی ایرانی"
        meals_data = []

        for idx, (meal_key, table) in enumerate(self.meal_tables, start=1):
            items = []
            for row in range(table.rowCount()):
                combo_food = table.cellWidget(row, 0)
                if not combo_food:
                    continue
                food_id = combo_food.currentData()
                if not food_id:
                    continue
                amount_str = table.cellWidget(row, 1).text().strip()
                notes = table.cellWidget(row, 2).text().strip()

                try:
                    amount = float(amount_str)
                except ValueError:
                    amount = 1.0

                items.append({
                    "food_id": food_id,
                    "amount": amount,
                    "notes": notes
                })

            meals_data.append({
                "meal_name": meal_key,
                "order_index": idx,
                "items": items
            })

        plan_info = {
            "title": title,
            "goal": self.combo_goal.currentData(),
            "target_calories": 0.0,
            "target_protein": 0.0,
            "target_carbs": 0.0,
            "target_fat": 0.0
        }
        return plan_info, meals_data

    def save_plan(self, auto_reset: bool = True):
        plan_info, meals_data = self.get_plan_data()
        total_items = sum(len(m.get("items", [])) for m in meals_data)
        if total_items == 0:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا حداقل یک ماده غذایی به برنامه اضافه کنید.")
            return None

        try:
            if self.editing_plan_id:
                plan = NutritionService.update_nutrition_plan(self.editing_plan_id, plan_info, meals_data)
                if auto_reset:
                    self.reset_form()
                else:
                    self.combo_templates.blockSignals(True)
                    self.load_template_dropdown()
                    self.combo_templates.blockSignals(False)
                QMessageBox.information(self, "موفقیت", f"الگوی برنامه غذایی «{plan.title}» با موفقیت به‌روزرسانی شد.")
            else:
                plan = NutritionService.create_nutrition_plan(plan_info, meals_data)
                if auto_reset:
                    self._do_reset_fields()
                self.combo_templates.blockSignals(True)
                self.load_template_dropdown()
                self.combo_templates.blockSignals(False)
                if auto_reset:
                    self.setup_meal_tabs()
                QMessageBox.information(self, "موفقیت", "الگوی برنامه غذایی با موفقیت در بانک ذخیره شد.")
            return plan
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره الگوی برنامه غذایی:\n{str(e)}")
            return None

    def _do_reset_fields(self):
        """پاکسازی فیلدهای مشخصات کلی رژیم"""
        for w in [self.txt_title, self.combo_goal, self.combo_days, self.combo_templates]:
            w.blockSignals(True)

        self.txt_title.setText("")
        self.combo_goal.setCurrentIndex(0)
        self.combo_days.setCurrentIndex(0)

        for w in [self.txt_title, self.combo_goal, self.combo_days, self.combo_templates]:
            w.blockSignals(False)

    def revert_changes(self):
        if self.editing_plan_id:
            self.load_plan_for_edit(self.editing_plan_id)
            QMessageBox.information(self, "بازنشانی", "تغییرات لغو شد و برنامه غذایی به حالت ذخیره‌شده اولیه بازگشت.")
        else:
            self.reset_form()
            QMessageBox.information(self, "بازنشانی", "فرم برنامه غذایی بازنشانی شد.")

    def reset_form(self):
        self.editing_plan_id = None
        self._days_cache.clear()
        self._prev_days_mode = "7_days"
        self.lbl_header_title.setText("🥗 برنامه‌ریزی تغذیه")
        self._do_reset_fields()
        self.combo_templates.blockSignals(True)
        if self.combo_templates.count() > 0:
            self.combo_templates.setCurrentIndex(0)
        self.combo_templates.blockSignals(False)
        self.setup_meal_tabs()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._last_state = self._capture_state()
        self._update_undo_redo_ui()

    def load_plan_for_edit(self, plan_id: int):
        self.editing_plan_id = plan_id
        self._days_cache.clear()
        plan = NutritionService.get_plan_by_id(plan_id)
        if plan:
            self.lbl_header_title.setText(f"✏️ ویرایش الگوی غذایی: {plan.title}")
            self._load_plan_data_to_form(plan)

    def assign_plan(self):
        member_id = self.combo_member.currentData()
        if not member_id:
            QMessageBox.warning(self, "خطا", "لطفاً یک ورزشکار را جهت تخصیص انتخاب کنید.")
            return

        plan_info, meals_data = self.get_plan_data()
        total_items = sum(len(m.get("items", [])) for m in meals_data)
        if total_items == 0:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا حداقل یک ماده غذایی به برنامه اضافه کنید.")
            return

        try:
            plan = NutritionService.create_nutrition_plan(plan_info, meals_data)
            NutritionService.assign_nutrition_plan(member_id, plan.id)
            QMessageBox.information(self, "موفقیت", "برنامه غذایی با موفقیت به ورزشکار تخصیص یافت.")
            self.reset_form()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در تخصیص برنامه غذایی:\n{str(e)}")

    def open_food_bank(self):
        from yalda.views.food_library_dialog import FoodLibraryDialog
        dlg = FoodLibraryDialog(self)
        dlg.exec()
        self.setup_meal_tabs()
