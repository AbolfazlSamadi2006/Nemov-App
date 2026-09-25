from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton, QTabWidget, QTableWidget, QHeaderView, QMessageBox, QGroupBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from yalda.services.workout_service import WorkoutService
from yalda.services.member_service import MemberService
from yalda.views.components.searchable_combo_box import SearchableComboBox
from yalda.views.components.day_management_dialogs import DaySelectionReductionDialog, DayIncreaseChoiceDialog

class ExerciseNotesDialog(QDialog):
    def __init__(self, exercise_name: str, current_notes: str, default_bank_notes: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("توضیحات و نکات حرکت ورزشی")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(520, 370)
        self.result_notes = current_notes or ""
        self.default_bank_notes = default_bank_notes or ""

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl_title = QLabel(f"📝 توضیحات حرکت: <b>{exercise_name}</b>")
        lbl_title.setStyleSheet("font-size: 14px; color: #FFFFFF;")
        layout.addWidget(lbl_title)

        lbl_hint = QLabel(
            "📌 این توضیحات ویژه این برنامه تمرینی است. ویرایش آن تغییری در توضیحات پایه در «بانک حرکات ورزشی» ایجاد نمی‌کند."
        )
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet("font-size: 11px; color: #9CA3AF; line-height: 16px;")
        layout.addWidget(lbl_hint)

        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("نکات اختصاصی مربی برای این حرکت، شیوه اجرا، دامنه حرکت، احتیاط‌ها و...")
        self.txt_notes.setText(self.result_notes)
        self.txt_notes.setStyleSheet("font-size: 12px; padding: 8px; border-radius: 6px;")
        layout.addWidget(self.txt_notes)

        btn_row_mid = QHBoxLayout()
        if self.default_bank_notes:
            btn_reset_bank = QPushButton("🔄 بازنشانی به توضیحات پیش‌فرض بانک")
            btn_reset_bank.setObjectName("secondary_button")
            btn_reset_bank.setFixedHeight(34)
            btn_reset_bank.setStyleSheet("font-size: 11px; padding: 4px 12px;")
            btn_reset_bank.setToolTip("بازنشانی متن به توضیحات اصلی تعریف‌شده در بانک حرکات")
            btn_reset_bank.clicked.connect(self._reset_to_bank)
            btn_row_mid.addWidget(btn_reset_bank)
        btn_row_mid.addStretch()
        layout.addLayout(btn_row_mid)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 ثبت توضیحات")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self._on_save)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_save)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def _reset_to_bank(self):
        self.txt_notes.setText(self.default_bank_notes)

    def _on_save(self):
        self.result_notes = self.txt_notes.toPlainText().strip()
        self.accept()

class WorkoutEditorView(QWidget):
    manage_templates_requested = pyqtSignal()
    open_exercise_bank_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.day_tables = []
        self.editing_plan_id = None
        self._undo_stack = []
        self._redo_stack = []
        self._undo_buttons = []
        self._redo_buttons = []
        self._is_undoing_redoing = False
        self._days_cache = {}
        self._prev_num_days = 3
        self.init_ui()
        self._last_state = self._capture_state()
        self._update_undo_redo_ui()

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

        # Header Title and Action Bar
        header = QHBoxLayout()
        self.lbl_header_title = QLabel("🏋️ برنامه‌ریزی تمرینی")
        self.lbl_header_title.setObjectName("h1")

        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.clicked.connect(self.back_requested.emit)

        self.btn_reset = QPushButton("🔄 بازنشانی تغییرات")
        self.btn_reset.setObjectName("secondary_button")
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self.revert_changes)

        btn_new_plan = QPushButton("➕ برنامه جدید")
        btn_new_plan.setObjectName("secondary_button")
        btn_new_plan.clicked.connect(self.reset_to_new_plan)

        btn_manage_tpl = QPushButton("📋 مدیریت و مشاهده الگوها")
        btn_manage_tpl.setObjectName("secondary_button")
        btn_manage_tpl.clicked.connect(self.manage_templates_requested.emit)

        btn_exercise_bank = QPushButton("🏃 بانک حرکات ورزشی")
        btn_exercise_bank.setObjectName("secondary_button")
        btn_exercise_bank.clicked.connect(self.open_exercise_bank_requested.emit)

        header.addWidget(btn_back)
        header.addWidget(self.lbl_header_title)
        header.addStretch()
        header.addWidget(self.btn_reset)
        header.addWidget(btn_new_plan)
        header.addWidget(btn_manage_tpl)
        header.addWidget(btn_exercise_bank)
        layout.addLayout(header)

        # Program Details Form Box
        form_box = QGroupBox("مشخصات کلی برنامه تمرینی")
        layout_form = QVBoxLayout(form_box)

        # Template Picker Row
        row_tpl = QHBoxLayout()
        self.combo_templates = QComboBox()
        self.combo_templates.addItem("--- انتخاب و بارگذاری الگوی آماده از بانک ---", None)
        self.load_template_dropdown()
        self.combo_templates.currentIndexChanged.connect(self.on_template_selected)

        row_tpl.addWidget(QLabel("📂 الگوهای آماده بانک:"))
        row_tpl.addWidget(self.combo_templates)
        layout_form.addLayout(row_tpl)

        row1 = QHBoxLayout()
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("عنوان برنامه (مثلاً: برنامه حجمی ۴ روزه)...")
        self.txt_title.textEdited.connect(lambda: self._snapshot_change())

        self.combo_goal = QComboBox()
        self.combo_goal.addItem("هایپرتروفی (عضله‌سازی)", "hypertrophy")
        self.combo_goal.addItem("چربی‌سوزی و کاهش وزن", "fat_loss")
        self.combo_goal.addItem("افزایش قدرت بی‌هوازی", "strength")
        self.combo_goal.addItem("حرکات اصلاحی و بهبود قامت", "corrective")
        self.combo_goal.addItem("آمادگی جسمانی عمومی", "general_fitness")
        self.combo_goal.addItem("استقامت عضلانی", "endurance")
        self.combo_goal.currentIndexChanged.connect(lambda: self._snapshot_change())

        self.combo_days = QComboBox()
        for d in range(2, 7):
            self.combo_days.addItem(f"{d} روز در هفته", d)
        self.combo_days.setCurrentIndex(1) # Default 3 days
        self.combo_days.currentIndexChanged.connect(self.on_days_changed)

        self.combo_level = QComboBox()
        self.combo_level.addItem("مبتدی", "beginner")
        self.combo_level.addItem("متوسط", "intermediate")
        self.combo_level.addItem("پیشرفته", "advanced")
        self.combo_level.currentIndexChanged.connect(lambda: self._snapshot_change())

        row1.addWidget(QLabel("عنوان:"))
        row1.addWidget(self.txt_title)
        row1.addWidget(QLabel("هدف:"))
        row1.addWidget(self.combo_goal)
        row1.addWidget(QLabel("روزهای هفته:"))
        row1.addWidget(self.combo_days)
        row1.addWidget(QLabel("سطح تمرین:"))
        row1.addWidget(self.combo_level)
        layout_form.addLayout(row1)

        layout.addWidget(form_box)

        # Tabs for Training Days
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        layout.addWidget(self.tabs)
        self.setup_day_tabs()

        # Assignment Box & Actions
        assign_box = QGroupBox("تخصیص برنامه به ورزشکار")
        layout_assign = QHBoxLayout(assign_box)

        self.combo_member = SearchableComboBox(placeholder="جستجو یا تایپ نام ورزشکار...")
        self.combo_member.setFixedHeight(36)
        self.combo_member.setMinimumWidth(260)
        self.load_members_dropdown()

        btn_save = QPushButton("💾 ذخیره الگو در بانک")
        btn_save.setObjectName("secondary_button")
        btn_save.clicked.connect(self.save_plan)

        btn_assign = QPushButton("✅ تخصیص و صدور برنامه")
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

    def _on_tab_moved(self, from_idx: int, to_idx: int):
        if from_idx == to_idx:
            return
        if 0 <= from_idx < len(self.day_tables) and 0 <= to_idx < len(self.day_tables):
            moved_item = self.day_tables.pop(from_idx)
            self.day_tables.insert(to_idx, moved_item)
            # Re-label tabs and day titles
            for i in range(self.tabs.count()):
                self.tabs.setTabText(i, f"روز {i + 1}")
                if i < len(self.day_tables):
                    txt_day_title, _ = self.day_tables[i]
                    cur_title = txt_day_title.text().strip()
                    if cur_title.startswith("روز ") and ":" in cur_title:
                        suffix = cur_title.split(":", 1)[1]
                        txt_day_title.setText(f"روز {i + 1}:{suffix}")
                    elif cur_title.startswith("روز ") and len(cur_title.split()) == 2:
                        txt_day_title.setText(f"روز {i + 1}")
            self._snapshot_change()

    def _extract_current_days_data(self) -> list:
        days_data = []
        for txt_day_title, table in self.day_tables:
            ex_list = []
            for r in range(table.rowCount()):
                combo = table.cellWidget(r, 0)
                ex_id = combo.currentData() if combo else None
                ex_text = combo.currentText() if combo else ""
                txt_sets = table.cellWidget(r, 1)
                txt_reps = table.cellWidget(r, 2)
                txt_weight = table.cellWidget(r, 3)
                txt_rest = table.cellWidget(r, 4)
                txt_tempo = table.cellWidget(r, 5)
                btn_notes = table.cellWidget(r, 6)
                trainer_notes = btn_notes.property("trainer_notes") if btn_notes else ""
                is_custom = bool(btn_notes.property("is_custom")) if btn_notes else False
                default_bank_notes = btn_notes.property("default_bank_notes") if btn_notes else ""

                ex_list.append({
                    "exercise_id": ex_id,
                    "exercise_text": ex_text,
                    "sets": txt_sets.text() if txt_sets else "3",
                    "reps": txt_reps.text() if txt_reps else "10-12",
                    "weight": txt_weight.text() if txt_weight else "-",
                    "rest": txt_rest.text() if txt_rest else "60",
                    "tempo": txt_tempo.text() if txt_tempo else "2-0-2-0",
                    "trainer_notes": trainer_notes,
                    "is_custom": is_custom,
                    "default_bank_notes": default_bank_notes
                })
            days_data.append({
                "day_title": txt_day_title.text(),
                "exercises": ex_list
            })
        return days_data

    def _has_non_empty_days(self, days_data: list) -> bool:
        if not days_data:
            return False
        for d in days_data:
            ex_list = d.get("exercises", [])
            for ex in ex_list:
                if ex.get("exercise_id") or (ex.get("exercise_text") and "انتخاب" not in ex.get("exercise_text")):
                    return True
            title = d.get("day_title", "")
            if title and not (title.startswith("روز ") and "تمرین عضلات" in title):
                return True
        return False

    def on_days_changed(self):
        new_days = self.combo_days.currentData() or 3
        old_days = getattr(self, '_prev_num_days', 3)
        if new_days == old_days:
            return

        current_days = self._extract_current_days_data()
        self._days_cache[old_days] = current_days

        selected_days = None

        if new_days < old_days:
            # Decreasing days
            summary = []
            for idx, d in enumerate(current_days):
                valid_ex_count = len([e for e in d.get("exercises", []) if e.get("exercise_id") or (e.get("exercise_text") and "انتخاب" not in e.get("exercise_text"))])
                summary.append((idx, d.get("day_title", f"روز {idx+1}"), f"{valid_ex_count} حرکت"))

            dlg = DaySelectionReductionDialog(summary, new_days, self, is_nutrition=False)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                # User cancelled
                self.combo_days.blockSignals(True)
                idx = self.combo_days.findData(old_days)
                if idx >= 0: self.combo_days.setCurrentIndex(idx)
                self.combo_days.blockSignals(False)
                return

            if dlg.start_fresh:
                selected_days = []
            else:
                selected_days = [current_days[i] for i in dlg.selected_indices if i < len(current_days)]

        else:
            # Increasing days
            cached_plan = self._days_cache.get(new_days)
            has_cached = bool(cached_plan and self._has_non_empty_days(cached_plan))

            dlg = DayIncreaseChoiceDialog(new_days, old_days, self, is_nutrition=False, has_cached_plan=has_cached)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                # User cancelled
                self.combo_days.blockSignals(True)
                idx = self.combo_days.findData(old_days)
                if idx >= 0: self.combo_days.setCurrentIndex(idx)
                self.combo_days.blockSignals(False)
                return

            if dlg.choice == "restore" and cached_plan:
                selected_days = cached_plan
            elif dlg.choice == "fresh":
                selected_days = []
            else:
                selected_days = current_days

        self._prev_num_days = new_days
        self.setup_day_tabs_with_data(new_days, selected_days)
        self._snapshot_change()

    def setup_day_tabs(self):
        num_days = self.combo_days.currentData() or 3
        self.setup_day_tabs_with_data(num_days, None)

    def setup_day_tabs_with_data(self, num_days: int, days_data: list = None):
        self.tabs.blockSignals(True)
        self.tabs.clear()
        self.day_tables.clear()
        self._undo_buttons.clear()
        self._redo_buttons.clear()
        exercises_list = WorkoutService.get_all_exercises()

        if not days_data:
            days_data = []

        for d in range(1, num_days + 1):
            day_widget = QWidget()
            layout_day = QVBoxLayout(day_widget)

            # Header row for day
            row_top = QHBoxLayout()
            lbl_title = QLabel(f"عنوان روز {d}:")

            existing_day = days_data[d - 1] if (d - 1) < len(days_data) else None
            if existing_day and existing_day.get("day_title"):
                orig_title = existing_day.get("day_title")
                if orig_title.startswith("روز ") and ":" in orig_title:
                    suffix = orig_title.split(":", 1)[1]
                    day_title_text = f"روز {d}:{suffix}"
                elif orig_title.startswith("روز ") and len(orig_title.split()) == 2:
                    day_title_text = f"روز {d}"
                else:
                    day_title_text = orig_title
            else:
                day_title_text = f"روز {d}: تمرین عضلات"

            txt_day_title = QLineEdit(day_title_text)
            txt_day_title.textEdited.connect(lambda: self._snapshot_change())

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

            btn_add_row = QPushButton("➕ افزودن حرکت")
            btn_add_row.setObjectName("secondary_button")

            row_top.addWidget(lbl_title)
            row_top.addWidget(txt_day_title)
            row_top.addStretch()
            row_top.addWidget(btn_undo)
            row_top.addWidget(btn_redo)
            row_top.addWidget(btn_add_row)
            layout_day.addLayout(row_top)

            # Table for exercises in this day
            table = QTableWidget(0, 8)
            table.setHorizontalHeaderLabels(["نام حرکت ورزشی", "ست", "تکرار", "وزنه (kg)", "استراحت (ثانیه)", "ریتم (Tempo)", "توضیحات", "حذف"])
            
            table.verticalHeader().setDefaultSectionSize(50)
            table.verticalHeader().setMinimumSectionSize(45)
            
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)     # Exercise name
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # Sets
            table.setColumnWidth(1, 65)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Reps
            table.setColumnWidth(2, 85)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # Weight
            table.setColumnWidth(3, 85)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive) # Rest
            table.setColumnWidth(4, 105)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive) # Tempo
            table.setColumnWidth(5, 105)
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive) # Notes
            table.setColumnWidth(6, 100)
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)       # Delete
            table.setColumnWidth(7, 55)

            btn_add_row.clicked.connect(lambda _, t=table: self.add_exercise_row(t, exercises_list))

            if existing_day and existing_day.get("exercises"):
                for ex in existing_day.get("exercises", []):
                    r = table.rowCount()
                    table.insertRow(r)
                    self._create_exercise_row_widgets(table, r, exercises_list, ex)

            layout_day.addWidget(table)
            self.tabs.addTab(day_widget, f"روز {d}")
            self.day_tables.append((txt_day_title, table))

        self.tabs.blockSignals(False)
        self._update_undo_redo_ui()

    def _capture_state(self):
        state = {
            "title": self.txt_title.text(),
            "goal": self.combo_goal.currentData(),
            "days_per_week": self.combo_days.currentData(),
            "level": self.combo_level.currentData(),
            "tab_index": self.tabs.currentIndex(),
            "days": []
        }
        for txt_day_title, table in self.day_tables:
            day_items = []
            for r in range(table.rowCount()):
                combo = table.cellWidget(r, 0)
                ex_id = combo.currentData() if combo else None
                ex_text = combo.currentText() if combo else ""
                txt_sets = table.cellWidget(r, 1)
                txt_reps = table.cellWidget(r, 2)
                txt_weight = table.cellWidget(r, 3)
                txt_rest = table.cellWidget(r, 4)
                txt_tempo = table.cellWidget(r, 5)
                btn_notes = table.cellWidget(r, 6)
                trainer_notes = btn_notes.property("trainer_notes") if btn_notes else ""
                is_custom = bool(btn_notes.property("is_custom")) if btn_notes else False
                default_bank_notes = btn_notes.property("default_bank_notes") if btn_notes else ""

                day_items.append({
                    "exercise_id": ex_id,
                    "exercise_text": ex_text,
                    "sets": txt_sets.text() if txt_sets else "3",
                    "reps": txt_reps.text() if txt_reps else "10-12",
                    "weight": txt_weight.text() if txt_weight else "-",
                    "rest": txt_rest.text() if txt_rest else "60",
                    "tempo": txt_tempo.text() if txt_tempo else "2-0-2-0",
                    "trainer_notes": trainer_notes,
                    "is_custom": is_custom,
                    "default_bank_notes": default_bank_notes
                })
            state["days"].append({
                "day_title": txt_day_title.text(),
                "exercises": day_items
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
        if hasattr(self, 'btn_reset') and self.btn_reset:
            self.btn_reset.setEnabled(can_undo)

    def _restore_state(self, state: dict):
        self._is_undoing_redoing = True
        try:
            self.txt_title.setText(state.get("title", ""))

            idx_g = self.combo_goal.findData(state.get("goal"))
            if idx_g >= 0: self.combo_goal.setCurrentIndex(idx_g)

            days_count = state.get("days_per_week", 3)
            self._prev_num_days = days_count
            idx_d = self.combo_days.findData(days_count)
            if idx_d >= 0 and self.combo_days.currentIndex() != idx_d:
                self.combo_days.blockSignals(True)
                self.combo_days.setCurrentIndex(idx_d)
                self.combo_days.blockSignals(False)
                self.setup_day_tabs()

            idx_l = self.combo_level.findData(state.get("level"))
            if idx_l >= 0: self.combo_level.setCurrentIndex(idx_l)

            exercises_list = WorkoutService.get_all_exercises()
            for idx, day_info in enumerate(state.get("days", [])):
                if idx < len(self.day_tables):
                    txt_day_title, table = self.day_tables[idx]
                    txt_day_title.setText(day_info.get("day_title", f"روز {idx+1}"))
                    table.setRowCount(0)
                    for ex in day_info.get("exercises", []):
                        r = table.rowCount()
                        table.insertRow(r)
                        self._create_exercise_row_widgets(table, r, exercises_list, ex)

            tab_idx = state.get("tab_index", 0)
            if 0 <= tab_idx < self.tabs.count():
                self.tabs.setCurrentIndex(tab_idx)
        finally:
            self._is_undoing_redoing = False

    def refresh_editor(self):
        self.load_members_dropdown()
        cur_tpl = self.combo_templates.currentData()
        self.load_template_dropdown()
        if cur_tpl is not None:
            idx = self.combo_templates.findData(cur_tpl)
            if idx >= 0:
                self.combo_templates.blockSignals(True)
                self.combo_templates.setCurrentIndex(idx)
                self.combo_templates.blockSignals(False)

    def _create_exercise_row_widgets(self, table: QTableWidget, row: int, exercises_list: list, data: dict = None):
        if not data:
            data = {}
        combo_ex = SearchableComboBox(placeholder="جستجو یا تایپ نام حرکت...")
        for ex in exercises_list:
            combo_ex.addItem(f"{ex.name_fa} ({ex.primary_muscle})", ex.id)

        ex_id = data.get("exercise_id")
        if ex_id:
            idx = combo_ex.findData(ex_id)
            if idx >= 0:
                combo_ex.setCurrentIndex(idx)
            else:
                combo_ex.set_empty()
        elif data.get("exercise_text"):
            combo_ex.setCurrentText(data["exercise_text"])
        else:
            combo_ex.set_empty()

        txt_sets = QLineEdit(str(data.get("sets", "3")))
        txt_sets.setAlignment(Qt.AlignmentFlag.AlignCenter)

        txt_reps = QLineEdit(str(data.get("reps", "10-12")))
        txt_reps.setAlignment(Qt.AlignmentFlag.AlignCenter)

        txt_weight = QLineEdit(str(data.get("weight", "-")))
        txt_weight.setAlignment(Qt.AlignmentFlag.AlignCenter)

        txt_rest = QLineEdit(str(data.get("rest", "60")))
        txt_rest.setAlignment(Qt.AlignmentFlag.AlignCenter)

        txt_tempo = QLineEdit(str(data.get("tempo", "2-0-2-0")))
        txt_tempo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_notes = QPushButton("📝 توضیحات")
        btn_notes.setObjectName("secondary_button")
        btn_notes.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_notes.setFixedHeight(32)

        # Lookup bank description
        curr_ex_id = combo_ex.currentData()
        bank_notes = data.get("default_bank_notes", "")
        if not bank_notes and curr_ex_id:
            for ex in exercises_list:
                if ex.id == curr_ex_id:
                    bank_notes = ex.description or ""
                    break

        trainer_notes = data.get("trainer_notes")
        is_custom = data.get("is_custom")
        if is_custom is None:
            is_custom = bool(trainer_notes and trainer_notes.strip() and trainer_notes != bank_notes)

        # Default trainer_notes to bank_notes if not provided
        if trainer_notes is None:
            trainer_notes = bank_notes

        btn_notes.setProperty("trainer_notes", trainer_notes or "")
        btn_notes.setProperty("default_bank_notes", bank_notes or "")
        btn_notes.setProperty("is_custom", is_custom)
        self._update_btn_notes_display(btn_notes)

        btn_notes.clicked.connect(lambda _, t=table, b=btn_notes, c=combo_ex, el=exercises_list: self.open_exercise_notes_dialog(t, b, c, el))

        btn_del = QPushButton("🗑️")
        btn_del.setObjectName("danger_button")
        btn_del.setToolTip("حذف حرکت ورزشی")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setFixedHeight(32)
        btn_del.clicked.connect(lambda _, t=table, b=btn_del: self.remove_exercise_row(t, b))

        # Connect listeners to snapshot undo
        combo_ex.currentIndexChanged.connect(lambda: self._on_exercise_combo_changed(combo_ex, btn_notes, exercises_list))
        txt_sets.textEdited.connect(lambda: self._snapshot_change())
        txt_reps.textEdited.connect(lambda: self._snapshot_change())
        txt_weight.textEdited.connect(lambda: self._snapshot_change())
        txt_rest.textEdited.connect(lambda: self._snapshot_change())
        txt_tempo.textEdited.connect(lambda: self._snapshot_change())

        table.setCellWidget(row, 0, combo_ex)
        table.setCellWidget(row, 1, txt_sets)
        table.setCellWidget(row, 2, txt_reps)
        table.setCellWidget(row, 3, txt_weight)
        table.setCellWidget(row, 4, txt_rest)
        table.setCellWidget(row, 5, txt_tempo)
        table.setCellWidget(row, 6, btn_notes)
        table.setCellWidget(row, 7, btn_del)

    def _update_btn_notes_display(self, btn_notes: QPushButton):
        notes = (btn_notes.property("trainer_notes") or "").strip()
        is_custom = bool(btn_notes.property("is_custom"))
        if notes:
            prefix = "توضیحات اختصاصی مربی برای این برنامه:\n" if is_custom else "توضیحات پیش‌فرض حرکت (بانک حرکات):\n"
            btn_notes.setToolTip(f"{prefix}{notes}")
            if is_custom:
                btn_notes.setText("📝 توضیحات ✓")
                btn_notes.setStyleSheet("color: #10B981; font-weight: bold; border: 1px solid #10B981; border-radius: 4px; font-size: 11px;")
            else:
                btn_notes.setText("📝 توضیحات")
                btn_notes.setStyleSheet("font-size: 11px;")
        else:
            btn_notes.setText("📝 توضیحات")
            btn_notes.setToolTip("بدون توضیحات (کلیک جهت افزودن یا ویرایش)")
            btn_notes.setStyleSheet("font-size: 11px;")

    def _on_exercise_combo_changed(self, combo_ex: SearchableComboBox, btn_notes: QPushButton, exercises_list: list):
        curr_ex_id = combo_ex.currentData()
        bank_notes = ""
        if curr_ex_id:
            for ex in exercises_list:
                if ex.id == curr_ex_id:
                    bank_notes = ex.description or ""
                    break
        btn_notes.setProperty("default_bank_notes", bank_notes)
        # If user hasn't explicitly customized notes for this row, inherit new exercise's bank description
        if not btn_notes.property("is_custom"):
            btn_notes.setProperty("trainer_notes", bank_notes)
            self._update_btn_notes_display(btn_notes)
        self._snapshot_change()

    def open_exercise_notes_dialog(self, table: QTableWidget, btn_notes: QPushButton, combo_ex: SearchableComboBox, exercises_list: list):
        ex_name = combo_ex.currentText() or "حرکت ورزشی"
        current_notes = btn_notes.property("trainer_notes") or ""
        default_bank_notes = btn_notes.property("default_bank_notes") or ""
        if not default_bank_notes:
            curr_ex_id = combo_ex.currentData()
            if curr_ex_id:
                for ex in exercises_list:
                    if ex.id == curr_ex_id:
                        default_bank_notes = ex.description or ""
                        btn_notes.setProperty("default_bank_notes", default_bank_notes)
                        break

        notes_to_edit = current_notes if current_notes else default_bank_notes

        dlg = ExerciseNotesDialog(
            exercise_name=ex_name,
            current_notes=notes_to_edit,
            default_bank_notes=default_bank_notes,
            parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_notes = dlg.result_notes
            btn_notes.setProperty("trainer_notes", new_notes)
            btn_notes.setProperty("is_custom", True)
            self._update_btn_notes_display(btn_notes)
            self._snapshot_change()

    def add_exercise_row(self, table: QTableWidget, exercises_list: list = None):
        row = table.rowCount()
        table.insertRow(row)
        if not exercises_list:
            exercises_list = WorkoutService.get_all_exercises()
        self._create_exercise_row_widgets(table, row, exercises_list)
        self._snapshot_change()

    def remove_exercise_row(self, table: QTableWidget, btn: QPushButton):
        for r in range(table.rowCount()):
            if table.cellWidget(r, 7) == btn:
                table.removeRow(r)
                break
        self._snapshot_change()

    def get_plan_data(self):
        title = self.txt_title.text().strip() or "برنامه تمرینی سفارشی"
        days_data = []

        for idx, (txt_day_title, table) in enumerate(self.day_tables, start=1):
            ex_list = []
            for row in range(table.rowCount()):
                combo_ex = table.cellWidget(row, 0)
                if not combo_ex:
                    continue
                ex_id = combo_ex.currentData()
                if not ex_id:
                    continue
                sets = table.cellWidget(row, 1).text().strip()
                reps = table.cellWidget(row, 2).text().strip()
                weight = table.cellWidget(row, 3).text().strip()
                rest = table.cellWidget(row, 4).text().strip()
                tempo = table.cellWidget(row, 5).text().strip()
                btn_notes = table.cellWidget(row, 6)
                trainer_notes = btn_notes.property("trainer_notes") if btn_notes else ""

                ex_list.append({
                    "exercise_id": ex_id,
                    "sets": int(sets) if sets.isdigit() else 3,
                    "reps": reps,
                    "weight_suggestion": weight,
                    "rest_seconds": int(rest) if rest.isdigit() else 60,
                    "tempo": tempo,
                    "trainer_notes": (trainer_notes or "").strip()
                })

            days_data.append({
                "day_number": idx,
                "day_title": txt_day_title.text().strip(),
                "exercises": ex_list
            })

        plan_info = {
            "title": title,
            "goal": self.combo_goal.currentData(),
            "days_per_week": self.combo_days.currentData(),
            "training_level": self.combo_level.currentData()
        }
        return plan_info, days_data

    def load_template_dropdown(self):
        cur = self.combo_templates.currentData()
        self.combo_templates.blockSignals(True)
        self.combo_templates.clear()
        self.combo_templates.addItem("--- انتخاب و بارگذاری الگوی آماده از بانک ---", None)
        goal_names = {
            "hypertrophy": "عضله‌سازی",
            "fat_loss": "چربی‌سوزی",
            "strength": "قدرت",
            "corrective": "حرکات اصلاحی",
            "general_fitness": "عمومی",
            "endurance": "استقامت"
        }
        plans = WorkoutService.get_all_plans()
        for p in plans:
            g_name = goal_names.get(p.goal, p.goal)
            self.combo_templates.addItem(f"{p.title} ({g_name} - {p.days_per_week} روزه)", p.id)
        if cur is not None:
            idx = self.combo_templates.findData(cur)
            if idx >= 0:
                self.combo_templates.setCurrentIndex(idx)
        self.combo_templates.blockSignals(False)

    def _load_plan_data_to_form(self, plan):
        self._loading_plan = True
        try:
            self.txt_title.setText(plan.title or "")
            idx_g = self.combo_goal.findData(plan.goal)
            if idx_g >= 0: self.combo_goal.setCurrentIndex(idx_g)

            idx_d = self.combo_days.findData(plan.days_per_week)
            self.combo_days.blockSignals(True)
            if idx_d >= 0:
                self.combo_days.setCurrentIndex(idx_d)
            self.combo_days.blockSignals(False)
            self._prev_num_days = plan.days_per_week

            idx_l = self.combo_level.findData(plan.training_level)
            if idx_l >= 0: self.combo_level.setCurrentIndex(idx_l)

            # Rebuild day tabs for loaded template's days_per_week
            self.setup_day_tabs()

            exercises_list = WorkoutService.get_all_exercises()

            # Populate day tables with exercises from loaded template
            for day_idx, w_day in enumerate(plan.days):
                if day_idx < len(self.day_tables):
                    txt_day_title, table = self.day_tables[day_idx]
                    txt_day_title.setText(w_day.day_title or f"روز {day_idx + 1}")
                    table.setRowCount(0)
                    for we in w_day.workout_exercises:
                        r = table.rowCount()
                        table.insertRow(r)
                        self._create_exercise_row_widgets(table, r, exercises_list, {
                            "exercise_id": we.exercise_id,
                            "sets": we.sets or 3,
                            "reps": we.reps or "10-12",
                            "weight": we.weight_suggestion or "-",
                            "rest": we.rest_seconds or 60,
                            "tempo": we.tempo or "2-0-2-0",
                            "trainer_notes": we.trainer_notes,
                            "is_custom": bool(we.trainer_notes and we.trainer_notes.strip())
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

            plan = WorkoutService.get_plan_by_id(plan_id)
            if not plan:
                return

            self._load_plan_data_to_form(plan)

            if not hasattr(self, '_suppress_loaded_alert') or not self._suppress_loaded_alert:
                QMessageBox.information(self, "موفقیت", f"الگوی '{plan.title}' با موفقیت در فرم بارگذاری شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در لود الگوی تمرینی: {str(e)}")

    def revert_changes(self):
        if self.editing_plan_id:
            self.load_plan_for_edit(self.editing_plan_id)
            QMessageBox.information(self, "بازنشانی", "تغییرات لغو شد و برنامه تمرینی به حالت ذخیره‌شده اولیه بازگشت.")
        else:
            self.reset_to_new_plan()
            QMessageBox.information(self, "بازنشانی", "فرم برنامه تمرینی بازنشانی شد.")

    def reset_to_new_plan(self):
        self.editing_plan_id = None
        self._days_cache.clear()
        self._prev_num_days = 3
        self.lbl_header_title.setText("🏋️ برنامه‌ریزی تمرینی")
        self.txt_title.clear()
        self.combo_goal.setCurrentIndex(0)
        self.combo_days.blockSignals(True)
        self.combo_days.setCurrentIndex(1)
        self.combo_days.blockSignals(False)
        self.combo_level.setCurrentIndex(0)
        self.setup_day_tabs()
        self.combo_templates.blockSignals(True)
        self.combo_templates.setCurrentIndex(0)
        self.combo_templates.blockSignals(False)
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._last_state = self._capture_state()
        self._update_undo_redo_ui()

    def load_plan_for_edit(self, plan_id: int):
        self._suppress_loaded_alert = True
        try:
            self.editing_plan_id = plan_id
            self._days_cache.clear()
            plan = WorkoutService.get_plan_by_id(plan_id)
            if plan:
                self._prev_num_days = plan.days_per_week
                self.lbl_header_title.setText(f"✏️ ویرایش الگوی تمرینی: {plan.title}")
                self._load_plan_data_to_form(plan)
        finally:
            self._suppress_loaded_alert = False

    def save_plan(self):
        plan_info, days_data = self.get_plan_data()
        total_exercises = sum(len(d.get("exercises", [])) for d in days_data)
        if total_exercises == 0:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا حداقل یک حرکت ورزشی به برنامه اضافه کنید.")
            return None

        # Check duplicate template title in workout plans bank
        title = plan_info["title"].strip()
        all_plans = WorkoutService.get_all_plans()
        other_titles = [p.title for p in all_plans if not (self.editing_plan_id and p.id == self.editing_plan_id) and p.title]
        if any(t.strip().lower() == title.lower() for t in other_titles):
            from yalda.utils.duplicate_helper import get_next_numbered_name
            suggested_title = get_next_numbered_name(title, other_titles)
            reply = QMessageBox.question(
                self,
                "هشدار عنوان تکراری",
                f"الگوی تمرینی دیگری با عنوان «{title}» از قبل در بانک الگوها ثبت شده است.\n\nدر صورت تایید، این الگو با عنوان «{suggested_title}» ذخیره خواهد شد.\nآیا مایل به ذخیره هستید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.txt_title.setFocus()
                return None
            title = suggested_title
            plan_info["title"] = suggested_title
            self.txt_title.setText(suggested_title)

        try:
            if self.editing_plan_id:
                plan = WorkoutService.update_workout_plan(self.editing_plan_id, plan_info, days_data)
                self.load_template_dropdown()
                from yalda.utils.logger import log_info
                log_info(f"Updated workout template: '{plan.title}' (ID: {plan.id})")
                QMessageBox.information(self, "موفقیت", f"الگوی تمرینی «{plan.title}» با موفقیت به‌روزرسانی شد.")
            else:
                plan = WorkoutService.create_workout_plan(plan_info, days_data)
                self.load_template_dropdown()
                from yalda.utils.logger import log_info
                log_info(f"Created workout template: '{plan.title}' (ID: {plan.id})")
                QMessageBox.information(self, "موفقیت", "الگوی برنامه تمرینی در بانک ذخیره گردید.")
            return plan
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from yalda.utils.logger import log_error
            from yalda.views.components.error_dialog import show_error_dialog
            log_error(f"Error saving workout template: {e}\n{tb}")
            show_error_dialog(
                parent=self,
                message="متاسفانه در ذخیره‌سازی الگوی تمرینی خطایی رخ داد.",
                technical_details=tb,
                title="خطا در ذخیره برنامه"
            )
            return None

    def assign_plan(self):
        member_id = self.combo_member.currentData()
        if not member_id:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا یک ورزشکار را انتخاب کنید.")
            return

        plan_info, days_data = self.get_plan_data()
        if not plan_info["title"]:
            QMessageBox.warning(self, "خطا", "لطفاً عنوان برنامه را وارد کنید.")
            return

        total_exercises = sum(len(d.get("exercises", [])) for d in days_data)
        if total_exercises == 0:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا حداقل یک حرکت ورزشی به برنامه اضافه کنید.")
            return

        # Check duplicate workout plan for this member
        title = plan_info["title"].strip()
        existing_asgns = WorkoutService.get_member_assignments(member_id)
        if existing_asgns:
            member = MemberService.get_member_by_id(member_id)
            member_name = member.full_name if member else "این ورزشکار"
            other_titles = [asgn.plan.title for asgn in existing_asgns if asgn.plan and asgn.plan.title]
            if any(t.strip().lower() == title.lower() for t in other_titles):
                from yalda.utils.duplicate_helper import get_next_numbered_name
                suggested_title = get_next_numbered_name(title, other_titles)
                reply = QMessageBox.question(
                    self,
                    "هشدار برنامه تکراری برای ورزشکار",
                    f"برای ورزشکار «{member_name}» قبلاً برنامه تمرینی با عنوان «{title}» صادر شده است.\n\nدر صورت تایید، این برنامه با عنوان «{suggested_title}» برای ایشان صادر خواهد شد.\nآیا مطمئن هستید؟",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.txt_title.setFocus()
                    return
                title = suggested_title
                plan_info["title"] = suggested_title
                self.txt_title.setText(suggested_title)

        # Check Smart Limitations
        health_rec = MemberService.get_health_record(member_id)
        warnings = []
        if health_rec:
            if health_rec.knee_injury:
                warnings.append("ورزشکار سابقه آسیب زانو دارد.")
            if health_rec.back_injury:
                warnings.append("ورزشکار سابقه فتق دیسک کمر دارد.")
            if health_rec.shoulder_injury:
                warnings.append("ورزشکار سابقه آسیب شانه دارد.")

        if warnings:
            msg = "⚠️ هشدارهای پزشکی ورزشکار:\n" + "\n".join(warnings) + "\n\nآیا مایل به تخصیص برنامه هستید؟"
            reply = QMessageBox.question(self, "هشدار پزشکی", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            plan = WorkoutService.create_workout_plan(plan_info, days_data)
            WorkoutService.assign_plan_to_member(member_id, plan.id)
            from yalda.utils.logger import log_info
            log_info(f"Assigned workout plan '{plan.title}' to member ID {member_id}")
            QMessageBox.information(self, "موفقیت", "برنامه تمرینی با موفقیت به ورزشکار تخصیص یافت.")
            self.reset_to_new_plan()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from yalda.utils.logger import log_error
            from yalda.views.components.error_dialog import show_error_dialog
            log_error(f"Error assigning workout plan: {e}\n{tb}")
            show_error_dialog(
                parent=self,
                message="متاسفانه در تخصیص برنامه تمرینی به ورزشکار خطایی رخ داد.",
                technical_details=tb,
                title="خطا در تخصیص برنامه"
            )
