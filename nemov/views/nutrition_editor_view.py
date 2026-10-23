from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTabWidget, QTableWidget, QHeaderView, QMessageBox, QGroupBox, QDialog, QFrame, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QKeySequence, QShortcut
from nemov.services.nutrition_service import NutritionService
from nemov.services.member_service import MemberService
from nemov.views.components.searchable_combo_box import SearchableComboBox
from nemov.views.components.field_validator import (
    MicroWarningLabel, validate_daily_calories, validate_protein
)
from nemov.views.components.day_management_dialogs import DaySelectionReductionDialog, DayIncreaseChoiceDialog
from nemov.views.components.unregistered_items_dialog import UnregisteredItemsDialog

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
        self._current_member_weight_kg = 0.0
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

        # Header Title & Action Buttons
        header = QHBoxLayout()
        self.lbl_header_title = QLabel("🥗 برنامه‌ریزی تغذیه")
        self.lbl_header_title.setObjectName("h1")

        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.clicked.connect(self.back_requested.emit)

        self.btn_reset = QPushButton("🔄 بازنشانی تغییرات")
        self.btn_reset.setObjectName("secondary_button")
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self.revert_changes)

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
        header.addWidget(self.btn_reset)
        header.addWidget(btn_new_plan)
        header.addWidget(btn_manage_tpl)
        header.addWidget(btn_food_bank)
        layout.addLayout(header)

        # Program Details Form Box
        form_box = QGroupBox("مشخصات کلی برنامه غذایی")
        layout_form = QVBoxLayout(form_box)
        layout_form.setSpacing(10)
        layout_form.setContentsMargins(12, 12, 12, 12)

        # Row 1: Template Picker & Diet Title
        row_top = QHBoxLayout()
        row_top.setSpacing(12)

        lbl_tpl = QLabel("📂 الگوهای آماده بانک:")
        self.combo_templates = QComboBox()
        self.combo_templates.setFixedHeight(34)
        self.combo_templates.addItem("--- انتخاب و بارگذاری الگوی آماده رژیم از بانک ---", None)
        self.load_template_dropdown()
        self.combo_templates.currentIndexChanged.connect(self.on_template_selected)

        lbl_title = QLabel("عنوان رژیم:")
        self.txt_title = QLineEdit()
        self.txt_title.setFixedHeight(34)
        self.txt_title.setPlaceholderText("مثلاً: رژیم افزایش حجم عضلانی...")
        self.txt_title.textEdited.connect(lambda: self._snapshot_change())

        row_top.addWidget(lbl_tpl)
        row_top.addWidget(self.combo_templates, 1)
        row_top.addWidget(lbl_title)
        row_top.addWidget(self.txt_title, 1)
        layout_form.addLayout(row_top)

        # Row 2: Athlete Selection -> Goal -> Days Pattern
        row_mid = QHBoxLayout()
        row_mid.setSpacing(12)

        lbl_top_member = QLabel("ورزشکار:")
        self.combo_member_top = SearchableComboBox(placeholder="انتخاب ورزشکار...")
        self.combo_member_top.setFixedHeight(34)
        self.combo_member_top.setMinimumWidth(185)

        lbl_goal = QLabel("هدف رژیم:")
        self.combo_goal = QComboBox()
        self.combo_goal.setFixedHeight(34)
        self.combo_goal.addItem("عضله‌سازی (Muscle Gain)", "muscle_gain")
        self.combo_goal.addItem("کاهش وزن و چربی‌سوزی (Weight Loss)", "weight_loss")
        self.combo_goal.addItem("افزایش وزن (Weight Gain)", "weight_gain")
        self.combo_goal.addItem("تثبیت وزن (Maintenance)", "maintenance")
        self.combo_goal.currentIndexChanged.connect(self._on_goal_changed)

        lbl_days = QLabel("روزهای هفته:")
        self.combo_days = QComboBox()
        self.combo_days.setFixedHeight(34)
        self.combo_days.addItem("📅 شنبه تا جمعه (۷ روز هفته)", "7_days")
        self.combo_days.addItem("📅 روزهای تمرینی و استراحت", "training_rest")
        self.combo_days.addItem("📅 ۲ روز در هفته", "2_days")
        self.combo_days.addItem("📅 ۳ روز در هفته", "3_days")
        self.combo_days.addItem("📅 ۴ روز در هفته", "4_days")
        self.combo_days.addItem("📅 ۵ روز در هفته", "5_days")
        self.combo_days.addItem("📅 ۶ روز در هفته", "6_days")
        self.combo_days.addItem("📅 الگوی ثابت (کلیه روزهای هفته)", "all_days")
        self.combo_days.currentIndexChanged.connect(self.on_days_pattern_changed)

        row_mid.addWidget(lbl_top_member)
        row_mid.addWidget(self.combo_member_top, 2)
        row_mid.addWidget(lbl_goal)
        row_mid.addWidget(self.combo_goal, 1)
        row_mid.addWidget(lbl_days)
        row_mid.addWidget(self.combo_days, 1)
        layout_form.addLayout(row_mid)

        # Row 3: TDEE Field & Adjust Buttons, Dynamic Total Calories Field & Live Comparison
        row_cal = QHBoxLayout()
        row_cal.setSpacing(6)

        self._current_member_tdee = 0
        self._foods_cache_by_id = {}

        lbl_tdee = QLabel("کیلوکالری دریافتی روزانه (TDEE):")
        self.txt_member_tdee = QLineEdit("0")
        self.txt_member_tdee.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_member_tdee.setFixedWidth(110)
        self.txt_member_tdee.setFixedHeight(34)
        self.txt_member_tdee.setStyleSheet(
            "font-weight: bold; color: #FBBF24; background-color: #1F2937; border: 1px solid #374151; border-radius: 6px; padding: 2px 6px;"
        )
        self.txt_member_tdee.textEdited.connect(self._on_manual_tdee_edited)

        # Quick TDEE adjustment buttons: +300, +500, -300, -500
        btn_style_plus = """
            QPushButton {
                background-color: #1A2E26;
                color: #34D399;
                border: 1px solid #059669;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #059669;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """
        btn_style_minus = """
            QPushButton {
                background-color: #2E1A1A;
                color: #F87171;
                border: 1px solid #DC2626;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #B91C1C;
            }
        """

        self.btn_tdee_p300 = QPushButton("+300")
        self.btn_tdee_p300.setFixedSize(46, 34)
        self.btn_tdee_p300.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tdee_p300.setStyleSheet(btn_style_plus)
        self.btn_tdee_p300.setToolTip("افزودن ۳۰۰ کیلوکالری به TDEE")
        self.btn_tdee_p300.clicked.connect(lambda: self.adjust_tdee(300))

        self.btn_tdee_p500 = QPushButton("+500")
        self.btn_tdee_p500.setFixedSize(46, 34)
        self.btn_tdee_p500.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tdee_p500.setStyleSheet(btn_style_plus)
        self.btn_tdee_p500.setToolTip("افزودن ۵۰۰ کیلوکالری به TDEE")
        self.btn_tdee_p500.clicked.connect(lambda: self.adjust_tdee(500))

        self.btn_tdee_m300 = QPushButton("-300")
        self.btn_tdee_m300.setFixedSize(46, 34)
        self.btn_tdee_m300.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tdee_m300.setStyleSheet(btn_style_minus)
        self.btn_tdee_m300.setToolTip("کاستن ۳۰۰ کیلوکالری از TDEE")
        self.btn_tdee_m300.clicked.connect(lambda: self.adjust_tdee(-300))

        self.btn_tdee_m500 = QPushButton("-500")
        self.btn_tdee_m500.setFixedSize(46, 34)
        self.btn_tdee_m500.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tdee_m500.setStyleSheet(btn_style_minus)
        self.btn_tdee_m500.setToolTip("کاستن ۵۰۰ کیلوکالری از TDEE")
        self.btn_tdee_m500.clicked.connect(lambda: self.adjust_tdee(-500))

        self.lbl_total_calories_title = QLabel("مجموع کیلوکالری دریافتی:")
        self.txt_total_calories = QLineEdit("\u200f0 کیلوکالری")
        self.txt_total_calories.setReadOnly(True)
        self.txt_total_calories.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_total_calories.setFixedWidth(110)
        self.txt_total_calories.setFixedHeight(34)
        self.txt_total_calories.setStyleSheet(
            "font-weight: bold; color: #34D399; background-color: #1F2937; border: 1px solid #374151; border-radius: 6px; padding: 2px 6px;"
        )

        self.lbl_calorie_comparison = QLabel("\u200f⚖️ وضعیت انرژی: ورزشکار انتخاب نشده")
        self.lbl_calorie_comparison.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_calorie_comparison.setFixedHeight(34)
        self.lbl_calorie_comparison.setMinimumWidth(210)
        self.lbl_calorie_comparison.setStyleSheet(
            "font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #374151; color: #E5E7EB;"
        )

        row_cal.addWidget(lbl_tdee)
        row_cal.addWidget(self.txt_member_tdee)
        row_cal.addWidget(self.btn_tdee_p300)
        row_cal.addWidget(self.btn_tdee_p500)
        row_cal.addWidget(self.btn_tdee_m300)
        row_cal.addWidget(self.btn_tdee_m500)
        row_cal.addSpacing(6)
        row_cal.addWidget(self.lbl_total_calories_title)
        row_cal.addWidget(self.txt_total_calories)
        row_cal.addWidget(self.lbl_calorie_comparison, 1)
        layout_form.addLayout(row_cal)

        self.lbl_cal_warn = MicroWarningLabel()
        layout_form.addWidget(self.lbl_cal_warn)

        # Row 4: Macronutrients Target Engine & Balance Cards
        self._setup_macro_cards(layout_form)

        layout.addWidget(form_box)

        # Tabs for Meals
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        self.tabs.currentChanged.connect(lambda _: self.update_dynamic_calories())
        layout.addWidget(self.tabs)
        self.setup_meal_tabs()

        # Assignment Box & Actions
        assign_box = QGroupBox("تخصیص برنامه تغذیه به ورزشکار")
        layout_assign = QHBoxLayout(assign_box)

        self.combo_member = SearchableComboBox(placeholder="جستجو یا تایپ نام ورزشکار...")
        self.combo_member.setFixedHeight(36)
        self.combo_member.setMinimumWidth(260)

        self.combo_member.currentIndexChanged.connect(self._on_bottom_member_changed)
        self.combo_member.currentTextChanged.connect(lambda t: self._on_member_text_matched(self.combo_member, t))
        self.combo_member_top.currentIndexChanged.connect(self._on_top_member_changed)
        self.combo_member_top.currentTextChanged.connect(lambda t: self._on_member_text_matched(self.combo_member_top, t))
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

    def _on_member_text_matched(self, combo: QComboBox, text: str):
        clean = (text or "").strip()
        if not clean:
            if combo.currentIndex() != -1:
                self._sync_member_combos(None)
            return
        idx = combo.findText(clean, Qt.MatchFlag.MatchExactly)
        if idx >= 0:
            m_id = combo.itemData(idx)
            if m_id != getattr(self, "_last_synced_member_id", None):
                self._sync_member_combos(m_id)

    def _sync_member_combos(self, member_id):
        self._last_synced_member_id = member_id
        for cmb in (self.combo_member, self.combo_member_top):
            cmb.blockSignals(True)
            if member_id is not None:
                idx = cmb.findData(member_id)
                if idx >= 0:
                    cmb.setCurrentIndex(idx)
                else:
                    cmb.set_empty()
            else:
                cmb.set_empty()
            cmb.blockSignals(False)
        self.update_member_tdee_display(member_id)

    def _on_bottom_member_changed(self, _index: int):
        member_id = self.combo_member.currentData()
        self._sync_member_combos(member_id)
        self._snapshot_change()

    def _on_top_member_changed(self, _index: int):
        member_id = self.combo_member_top.currentData()
        self._sync_member_combos(member_id)
        self._snapshot_change()

    def _on_manual_tdee_edited(self, text: str):
        persian_to_eng = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        digits = "".join(ch for ch in text.translate(persian_to_eng) if ch.isdigit())
        self._current_member_tdee = int(digits) if digits else 0
        self.update_dynamic_calories()
        self._snapshot_change()

    def adjust_tdee(self, delta: int):
        persian_to_eng = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        cur_text = self.txt_member_tdee.text().translate(persian_to_eng)
        digits = "".join(ch for ch in cur_text if ch.isdigit())
        base_val = int(digits) if digits else (getattr(self, "_current_member_tdee", 0) or 0)

        new_val = max(0, base_val + delta)
        self._current_member_tdee = new_val
        self.txt_member_tdee.setText(f"\u200f{new_val:,} کیلوکالری")
        self.update_dynamic_calories()
        self._snapshot_change()

    def update_member_tdee_display(self, member_id=None):
        if member_id is None:
            member_id = self.combo_member.currentData()
        if not member_id:
            self._current_member_tdee = 0
            self._current_member_weight_kg = 0.0
            self.txt_member_tdee.setText("0")
            self.txt_member_tdee.setToolTip("با انتخاب ورزشکار، مقدار TDEE ایشان به صورت خودکار محاسبه و درج می‌شود.")
            self._recalculate_target_macros_from_weight()
            self.update_dynamic_calories()
            return

        from nemov.utils.bmr_calculator import calculate_bmr_tdee, calculate_age_from_shamsi
        member = MemberService.get_member_by_id(member_id)
        if not member:
            self._current_member_tdee = 0
            self._current_member_weight_kg = 0.0
            self.txt_member_tdee.setText("0")
            self._recalculate_target_macros_from_weight()
            self.update_dynamic_calories()
            return

        h_cm = member.height_cm or 0.0
        w_kg = member.initial_weight_kg or 0.0
        if h_cm <= 0 or w_kg <= 0:
            try:
                from nemov.services.assessment_service import AssessmentService
                recs = AssessmentService.get_member_assessments(member_id)
                if recs:
                    if w_kg <= 0 and recs[0].weight_kg:
                        w_kg = recs[0].weight_kg
                    if h_cm <= 0 and getattr(recs[0], "height_cm", None):
                        h_cm = recs[0].height_cm
            except Exception:
                pass

        self._current_member_weight_kg = w_kg
        self._recalculate_target_macros_from_weight()

        age = calculate_age_from_shamsi(member.birth_date_shamsi)
        act_level = getattr(member, "activity_level", None) or "moderately_active"
        bmr, tdee, pal, act_title, _ = calculate_bmr_tdee(h_cm, w_kg, age, member.gender, act_level)
        self._current_member_tdee = tdee
        if tdee > 0:
            self.txt_member_tdee.setText(f"\u200f{tdee:,} کیلوکالری")
            self.txt_member_tdee.setToolTip(
                f"ورزشکار: {member.full_name} | BMR: {bmr:,} کیلوکالری | سطح فعالیت: {act_title} (ضریب {pal}) | TDEE: {tdee:,} کیلوکالری"
            )
        else:
            self.txt_member_tdee.setText("\u200fنامشخص (قد/وزن؟)")
            self.txt_member_tdee.setToolTip("قد یا وزن ورزشکار در پرونده ثبت نشده است.")
        self.update_dynamic_calories()

    def load_members_dropdown(self):
        cur = self.combo_member.currentData()
        if cur is None and hasattr(self, "combo_member_top"):
            cur = self.combo_member_top.currentData()
        members = MemberService.get_all_members()
        active_or_selected = [
            m for m in members
            if m.status != "archived" or (cur is not None and m.id == cur)
        ]
        for cmb in (self.combo_member, self.combo_member_top):
            cmb.blockSignals(True)
            cmb.clear()
            for m in active_or_selected:
                cmb.addItem(m.full_name, m.id)
            if cur is not None:
                idx = cmb.findData(cur)
                if idx >= 0:
                    cmb.setCurrentIndex(idx)
                else:
                    cmb.set_empty()
            else:
                cmb.set_empty()
            cmb.blockSignals(False)
        self.update_member_tdee_display(cur)

    def set_selected_member(self, member_id: int):
        self.load_members_dropdown()
        for cmb in (self.combo_member, self.combo_member_top):
            if cmb.findData(member_id) < 0:
                m = MemberService.get_member_by_id(member_id)
                if m:
                    cmb.blockSignals(True)
                    cmb.addItem(m.full_name, m.id)
                    cmb.blockSignals(False)
        self._sync_member_combos(member_id)

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

            if getattr(plan, "target_protein", 0) and plan.target_protein > 0:
                self.txt_target_p.setText(str(int(round(plan.target_protein))))
            if getattr(plan, "target_carbs", 0) and plan.target_carbs > 0:
                self.txt_target_c.setText(str(int(round(plan.target_carbs))))
            if getattr(plan, "target_fat", 0) and plan.target_fat > 0:
                self.txt_target_f.setText(str(int(round(plan.target_fat))))

            w_kg = getattr(self, "_current_member_weight_kg", 0.0) or 0.0
            if w_kg > 0:
                if hasattr(self, "txt_factor_p") and plan.target_protein:
                    self.txt_factor_p.setText(f"{plan.target_protein / w_kg:.1f}")
                if hasattr(self, "txt_factor_c") and plan.target_carbs:
                    self.txt_factor_c.setText(f"{plan.target_carbs / w_kg:.1f}")
                if hasattr(self, "txt_factor_f") and plan.target_fat:
                    self.txt_factor_f.setText(f"{plan.target_fat / w_kg:.1f}")

            if getattr(plan, "target_calories", 0) and plan.target_calories > 0:
                self._current_member_tdee = int(round(plan.target_calories))
                self.txt_member_tdee.setText(f"\u200f{int(round(plan.target_calories)):,} کیلوکالری")

            # Detect days pattern from meal names in plan
            has_7_days = any(any(d in m.meal_name for d in ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]) for m in plan.meals)
            has_train_rest = any("تمرین" in m.meal_name or "استراحت" in m.meal_name for m in plan.meals)
            word_num_map = {
                "روز اول": 1,
                "روز دوم": 2,
                "روز سوم": 3,
                "روز چهارم": 4,
                "روز پنجم": 5,
                "روز ششم": 6,
                "روز هفتم": 7
            }
            max_day_num = 0
            for m in plan.meals:
                for word, n in word_num_map.items():
                    if word in m.meal_name and n > max_day_num:
                        max_day_num = n
                for n in range(1, 8):
                    if f"روز {n}" in m.meal_name and n > max_day_num:
                        max_day_num = n

            self._days_cache.clear()
            self.combo_days.blockSignals(True)
            if has_train_rest:
                pattern_key = "training_rest"
            elif has_7_days:
                pattern_key = "7_days"
            elif max_day_num in (2, 3, 4, 5, 6):
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
                            "food_text": (item.food.name_fa if item.food else None) or getattr(item, "custom_food_name", None),
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
            "training_rest": ["روزهای تمرینی", "روزهای استراحت"],
            "2_days": ["روز اول", "روز دوم"],
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
            txt_notes = table.cellWidget(r, 3)
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
            "training_rest": 2,
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

        elif new_count > old_count:
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

        else:
            # Same count (e.g. switching between training_rest and 2_days)
            cached_plan = self._days_cache.get(new_mode)
            if cached_plan and self._has_non_empty_nutrition_days(cached_plan):
                selected_days = cached_plan
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
            "target_p": self.txt_target_p.text() if hasattr(self, "txt_target_p") else "0",
            "target_c": self.txt_target_c.text() if hasattr(self, "txt_target_c") else "0",
            "target_f": self.txt_target_f.text() if hasattr(self, "txt_target_f") else "0",
            "member_id": self.combo_member.currentData() if hasattr(self, "combo_member") else None,
            "tdee": getattr(self, "_current_member_tdee", 0) or 0,
            "meals": []
        }
        for meal_key, table in self.meal_tables:
            meal_items = []
            for r in range(table.rowCount()):
                combo = table.cellWidget(r, 0)
                f_id = combo.currentData() if combo else None
                f_text = combo.currentText() if combo else ""
                txt_amount = table.cellWidget(r, 1)
                txt_notes = table.cellWidget(r, 3)
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
        if hasattr(self, 'btn_reset') and self.btn_reset:
            self.btn_reset.setEnabled(can_undo)

    def _restore_state(self, state: dict):
        self._is_undoing_redoing = True
        try:
            self.txt_title.setText(state.get("title", ""))

            if hasattr(self, "txt_target_p") and "target_p" in state:
                self.txt_target_p.setText(state["target_p"])
            if hasattr(self, "txt_target_c") and "target_c" in state:
                self.txt_target_c.setText(state["target_c"])
            if hasattr(self, "txt_target_f") and "target_f" in state:
                self.txt_target_f.setText(state["target_f"])

            # Restore athlete selection
            st_member_id = state.get("member_id")
            self._sync_member_combos(st_member_id)

            # Restore TDEE
            if "tdee" in state:
                tdee_val = state.get("tdee", 0)
                self._current_member_tdee = tdee_val
                if hasattr(self, "txt_member_tdee"):
                    if tdee_val > 0:
                        self.txt_member_tdee.setText(f"\u200f{tdee_val:,} کیلوکالری")
                    else:
                        self.txt_member_tdee.setText("0")

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
            self.update_dynamic_calories()
        finally:
            self._is_undoing_redoing = False

    @staticmethod
    def _parse_amount(text: str) -> float:
        if not text:
            return 0.0
        persian_to_eng = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩/", "01234567890123456789.")
        clean = str(text).translate(persian_to_eng).replace(",", ".").strip()
        try:
            return max(0.0, float(clean))
        except ValueError:
            return 0.0

    def update_dynamic_calories(self):
        if not hasattr(self, "txt_total_calories"):
            return
        if not self._foods_cache_by_id:
            try:
                for f in NutritionService.get_all_foods():
                    self._foods_cache_by_id[f.id] = f
            except Exception:
                pass

        for _meal_key, table in self.meal_tables:
            for r in range(table.rowCount()):
                combo = table.cellWidget(r, 0)
                txt_amount = table.cellWidget(r, 1)
                lbl_row_cal = table.cellWidget(r, 2)
                f_id = combo.currentData() if combo else None
                amt = self._parse_amount(txt_amount.text() if txt_amount else "0")
                food = self._foods_cache_by_id.get(f_id) if f_id else None
                if lbl_row_cal:
                    if food and amt > 0:
                        r_cal = int(round((food.calories or 0.0) * amt))
                        lbl_row_cal.setText(f"\u200f{r_cal:,} کیلوکالری")
                        lbl_row_cal.setStyleSheet("color: #34D399; font-weight: bold; font-size: 12px;")
                    else:
                        lbl_row_cal.setText("\u200f0 کیلوکالری")
                        lbl_row_cal.setStyleSheet("color: #9CA3AF; font-size: 12px;")

        days_mode = self.combo_days.currentData() if hasattr(self, "combo_days") else "all_days"
        if days_mode == "all_days" or len(self.meal_tables) <= 6:
            active_tables = [tbl for _, tbl in self.meal_tables]
            day_suffix = ""
        else:
            d_idx = max(0, self.tabs.currentIndex()) if hasattr(self, "tabs") else 0
            day_slice = self.meal_tables[d_idx * 6 : (d_idx + 1) * 6]
            active_tables = [tbl for _, tbl in day_slice]
            day_title = self.tabs.tabText(d_idx).replace("📅", "").strip() if hasattr(self, "tabs") else ""
            day_suffix = f" ({day_title})" if day_title else ""

        total_cal = 0.0
        total_p = 0.0
        total_c = 0.0
        total_f = 0.0
        for tbl in active_tables:
            for r in range(tbl.rowCount()):
                combo = tbl.cellWidget(r, 0)
                txt_amount = tbl.cellWidget(r, 1)
                f_id = combo.currentData() if combo else None
                amt = self._parse_amount(txt_amount.text() if txt_amount else "0")
                food = self._foods_cache_by_id.get(f_id) if f_id else None
                if food and amt > 0:
                    total_cal += (food.calories or 0.0) * amt
                    total_p += (food.protein_g or 0.0) * amt
                    total_c += (food.carbs_g or 0.0) * amt
                    total_f += (food.fat_g or 0.0) * amt

        total_cal_int = int(round(total_cal))
        self.lbl_total_calories_title.setText(f"مجموع کیلوکالری دریافتی{day_suffix}:")
        self.txt_total_calories.setText(f"\u200f{total_cal_int:,} کیلوکالری")
        self.txt_total_calories.setToolTip(
            f"درشت‌مغذی‌های محاسبه‌شده{day_suffix}: پروتئین {int(round(total_p))} گرم | کربوهیدرات {int(round(total_c))} گرم | چربی {int(round(total_f))} گرم"
        )

        if hasattr(self, 'lbl_cal_warn'):
            cal_err = validate_daily_calories(total_cal_int)
            self.lbl_cal_warn.show_warning(cal_err)

        tdee = getattr(self, "_current_member_tdee", 0) or 0
        if tdee > 0:
            diff = total_cal_int - tdee
            if total_cal_int == 0:
                self.lbl_calorie_comparison.setText(f"\u200f⚖️ هدف روزانه (TDEE): {tdee:,} کیلوکالری")
                self.lbl_calorie_comparison.setStyleSheet(
                    "font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #374151; color: #E5E7EB;"
                )
            elif abs(diff) <= 50:
                self.lbl_calorie_comparison.setText(f"\u200f✅ منطبق با TDEE ({diff:+,} کیلوکالری)")
                self.lbl_calorie_comparison.setStyleSheet(
                    "font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #065F46; color: #FFFFFF;"
                )
            elif diff < -50:
                self.lbl_calorie_comparison.setText(f"\u200f📉 {abs(diff):,} کیلوکالری کمتر از TDEE")
                self.lbl_calorie_comparison.setStyleSheet(
                    "font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #1E40AF; color: #FFFFFF;"
                )
            else:
                self.lbl_calorie_comparison.setText(f"\u200f📈 {diff:,} کیلوکالری بیشتر از TDEE")
                self.lbl_calorie_comparison.setStyleSheet(
                    "font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #B45309; color: #FFFFFF;"
                )
        else:
            if total_cal_int > 0:
                self.lbl_calorie_comparison.setText(
                    f"\u200fپروتئین: {int(round(total_p))} گرم | کربوهیدرات: {int(round(total_c))} گرم | چربی: {int(round(total_f))} گرم"
                )
            else:
                self.lbl_calorie_comparison.setText("\u200f⚖️ وضعیت انرژی: ورزشکار انتخاب نشده")
            self.lbl_calorie_comparison.setStyleSheet(
                "font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #374151; color: #E5E7EB;"
            )

        # Update Macronutrient Target Cards & Real-Time Balance
        if hasattr(self, "card_protein"):
            act_p = int(round(total_p))
            act_c = int(round(total_c))
            act_f = int(round(total_f))

            tgt_p = self._get_target_macro("protein")
            tgt_c = self._get_target_macro("carbs")
            tgt_f = self._get_target_macro("fat")

            p_kcal = tgt_p * 4
            c_kcal = tgt_c * 4
            f_kcal = tgt_f * 9
            macro_tgt_cal = p_kcal + c_kcal + f_kcal

            self.lbl_actual_p.setText(f"\u200fمصرفی: {act_p:,} گرم")
            self.lbl_actual_c.setText(f"\u200fمصرفی: {act_c:,} گرم")
            self.lbl_actual_f.setText(f"\u200fمصرفی: {act_f:,} گرم")
            self.lbl_actual_energy.setText(f"\u200fمصرفی: {total_cal_int:,} کیلوکالری")

            self.lbl_target_p_kcal.setText(f"\u200f({p_kcal:,} کیلوکالری)")
            self.lbl_target_c_kcal.setText(f"\u200f({c_kcal:,} کیلوکالری)")
            self.lbl_target_f_kcal.setText(f"\u200f({f_kcal:,} کیلوکالری)")
            self.lbl_target_energy.setText(f"\u200f{macro_tgt_cal:,} کیلوکالری")

            # Update status badges for Protein, Carbs, Fat
            macro_labels = {
                "protein": ("پروتئین", self.lbl_status_p, act_p, tgt_p, 4),
                "carbs": ("کربوهیدرات", self.lbl_status_c, act_c, tgt_c, 4),
                "fat": ("چربی مفید", self.lbl_status_f, act_f, tgt_f, 9),
            }
            for m_key, (m_title, lbl_status, act_v, tgt_v, factor) in macro_labels.items():
                if tgt_v <= 0:
                    lbl_status.setText("\u200f—")
                    lbl_status.setToolTip(f"هدف {m_title} روزانه تعیین نشده است.")
                    lbl_status.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #1E293B; color: #94A3B8; border: none;")
                else:
                    diff = act_v - tgt_v
                    if diff < -2:
                        deficit = abs(diff)
                        lbl_status.setText(f"\u200f📉 {deficit:,} گرم کسری")
                        lbl_status.setToolTip(f"کسری {m_title}: {deficit:,} گرم (معادل {deficit * factor:,} کیلوکالری)")
                        lbl_status.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #1E3A8A; color: #93C5FD; border: none;")
                    elif abs(diff) <= 2:
                        lbl_status.setText("\u200f✅ تکمیل شد")
                        lbl_status.setToolTip(f"سهمیه {m_title} روزانه تکمیل و منطبق با هدف است.")
                        lbl_status.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #065F46; color: #A7F3D0; border: none;")
                    else:
                        surplus = diff
                        lbl_status.setText(f"\u200f📈 +{surplus:,} گرم مازاد")
                        lbl_status.setToolTip(f"مازاد {m_title}: {surplus:,} گرم (معادل {surplus * factor:,} کیلوکالری)")
                        lbl_status.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #78350F; color: #FDE68A; border: none;")

            # Update Energy Summary Status Badge
            if macro_tgt_cal <= 0:
                self.lbl_status_energy.setText("\u200f⚖️ هدف نامشخص")
                self.lbl_status_energy.setToolTip("مجموع کیلوکالری از درشت‌مغذی‌ها نامشخص است.")
                self.lbl_status_energy.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #1E293B; color: #94A3B8; border: none;")
            else:
                cal_diff = total_cal_int - macro_tgt_cal
                if cal_diff < -50:
                    self.lbl_status_energy.setText(f"\u200f📉 {abs(cal_diff):,} کیلوکالری کسری")
                    self.lbl_status_energy.setToolTip(f"کسری کل انرژی نسبت به هدف ماکروها: {abs(cal_diff):,} کیلوکالری")
                    self.lbl_status_energy.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #1E3A8A; color: #93C5FD; border: none;")
                elif abs(cal_diff) <= 50:
                    self.lbl_status_energy.setText("\u200f✅ بالانس کامل انرژی")
                    self.lbl_status_energy.setToolTip("کل کیلوکالری دریافتی روزانه با مجموع کیلوکالری ماکروها منطبق است.")
                    self.lbl_status_energy.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #065F46; color: #A7F3D0; border: none;")
                else:
                    self.lbl_status_energy.setText(f"\u200f📈 +{cal_diff:,} کیلوکالری مازاد")
                    self.lbl_status_energy.setToolTip(f"مازاد کل انرژی نسبت به هدف ماکروها: {cal_diff:,} کیلوکالری")
                    self.lbl_status_energy.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #78350F; color: #FDE68A; border: none;")

    # =========================================================================
    # MACRONUTRIENT TARGET & GAP-FILLING SUGGESTION ENGINE
    # =========================================================================

    GOAL_MACRO_FACTORS = {
        "maintenance": {"protein": 2.0, "carbs": 4.0, "fat": 1.0},
        "weight_loss": {"protein": 2.2, "carbs": 2.5, "fat": 0.8},
        "muscle_gain": {"protein": 2.2, "carbs": 5.0, "fat": 1.0},
        "weight_gain": {"protein": 2.0, "carbs": 6.0, "fat": 1.2},
    }

    def _setup_macro_cards(self, layout_form: QVBoxLayout):
        self.row_macros = QHBoxLayout()
        self.row_macros.setSpacing(8)

        # Get initial factors from goal
        goal_key = self.combo_goal.currentData() if hasattr(self, "combo_goal") else "muscle_gain"
        init_factors = self.GOAL_MACRO_FACTORS.get(goal_key, self.GOAL_MACRO_FACTORS["maintenance"])

        # Card 1: Protein (🥩 پروتئین)
        self.card_protein = QFrame()
        self.card_protein.setObjectName("card_macro_protein")
        layout_p = QVBoxLayout(self.card_protein)
        layout_p.setContentsMargins(10, 8, 10, 8)
        layout_p.setSpacing(4)

        # Row 1: Target Grams & Kcal
        p_top = QHBoxLayout()
        p_top.setSpacing(4)
        lbl_p_title = QLabel("🥩 پروتئین هدف:")
        lbl_p_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #60A5FA; border: none; background: transparent;")
        self.txt_target_p = QLineEdit("0")
        self.txt_target_p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_target_p.setFixedWidth(54)
        self.txt_target_p.setFixedHeight(24)
        self.txt_target_p.setStyleSheet("font-weight: bold; font-size: 11px; color: #60A5FA; background-color: #0F172A; border: 1px solid #3B82F6; border-radius: 4px; padding: 1px 2px;")
        self.txt_target_p.setToolTip("هدف کل پروتئین روزانه (گرم) — قابل ویرایش دستی\nفرمول: وزن شاگرد (kg) × عدد گرم بر کیلوگرم | هر گرم پروتئین = ۴ کیلوکالری ثابت")
        self.txt_target_p.textEdited.connect(lambda: self._on_target_macro_edited("protein"))
        lbl_p_unit = QLabel("گرم")
        lbl_p_unit.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        self.lbl_target_p_kcal = QLabel("(۰ کیلوکالری)")
        self.lbl_target_p_kcal.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        p_top.addWidget(lbl_p_title)
        p_top.addWidget(self.txt_target_p)
        p_top.addWidget(lbl_p_unit)
        p_top.addWidget(self.lbl_target_p_kcal)
        p_top.addStretch()
        layout_p.addLayout(p_top)

        # Row 2: Grams per Kg Formula Factor & Fixed Energy Multiplier
        p_mid = QHBoxLayout()
        p_mid.setSpacing(4)
        lbl_f_p_icon = QLabel("⚖️ فرمول:")
        lbl_f_p_icon.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        self.txt_factor_p = QLineEdit(f"{init_factors['protein']:.1f}")
        self.txt_factor_p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_factor_p.setFixedWidth(46)
        self.txt_factor_p.setFixedHeight(22)
        self.txt_factor_p.setStyleSheet("font-weight: bold; font-size: 10px; color: #93C5FD; background-color: #1E293B; border: 1px solid #3B82F6; border-radius: 4px; padding: 1px 3px;")
        self.txt_factor_p.setToolTip("گرم پروتئین به ازای هر ۱ کیلوگرم وزن بدن فرد (g/kg)\nفرمول: وزن شاگرد (kg) × عدد گرم بر کیلوگرم × ۴ کیلوکالری\nبا تغییر این عدد، هدف پروتئین روزانه بر اساس وزن شاگرد محاسبه می‌شود.")
        self.txt_factor_p.textEdited.connect(lambda: self._on_factor_edited("protein"))
        lbl_f_p_unit = QLabel("گرم/کیلوگرم")
        lbl_f_p_unit.setStyleSheet("font-size: 10px; color: #CBD5E1; border: none; background: transparent;")
        lbl_f_p_mult = QLabel("(ضریب ۴ کیلوکالری ثابت)")
        lbl_f_p_mult.setStyleSheet("font-size: 9px; color: #64748B; border: none; background: transparent;")
        p_mid.addWidget(lbl_f_p_icon)
        p_mid.addWidget(self.txt_factor_p)
        p_mid.addWidget(lbl_f_p_unit)
        p_mid.addWidget(lbl_f_p_mult)
        p_mid.addStretch()
        layout_p.addLayout(p_mid)

        # Row 3: Actual, Status, Suggestion
        p_bot = QHBoxLayout()
        p_bot.setSpacing(6)
        self.lbl_actual_p = QLabel("مصرفی: ۰ گرم")
        self.lbl_actual_p.setStyleSheet("font-size: 11px; font-weight: bold; color: #E2E8F0; border: none; background: transparent;")
        self.lbl_status_p = QLabel("۰ گرم باقیمانده")
        self.lbl_status_p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_p.setFixedHeight(22)
        self.lbl_status_p.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #1E293B; color: #94A3B8; border: none;")
        self.btn_suggest_p = QPushButton("💡 پیشنهاد")
        self.btn_suggest_p.setFixedHeight(22)
        self.btn_suggest_p.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_suggest_p.setStyleSheet("""
            QPushButton {
                background-color: #172554;
                color: #93C5FD;
                border: 1px solid #2563EB;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
                padding: 0 6px;
            }
            QPushButton:hover {
                background-color: #2563EB;
                color: #FFFFFF;
            }
        """)
        self.btn_suggest_p.setToolTip("پیشنهاد مواد غذایی غنی از پروتئین خالص برای جبران کسری")
        self.btn_suggest_p.clicked.connect(lambda: self.show_macro_suggestions("protein", self.btn_suggest_p))
        p_bot.addWidget(self.lbl_actual_p)
        p_bot.addWidget(self.lbl_status_p, 1)
        p_bot.addWidget(self.btn_suggest_p)
        layout_p.addLayout(p_bot)

        self.lbl_protein_warn = MicroWarningLabel()
        layout_p.addWidget(self.lbl_protein_warn)

        # Card 2: Carbs (🍞 کربوهیدرات)
        self.card_carbs = QFrame()
        self.card_carbs.setObjectName("card_macro_carbs")
        layout_c = QVBoxLayout(self.card_carbs)
        layout_c.setContentsMargins(10, 8, 10, 8)
        layout_c.setSpacing(4)

        # Row 1: Target Grams & Kcal
        c_top = QHBoxLayout()
        c_top.setSpacing(4)
        lbl_c_title = QLabel("🍞 کربوهیدرات هدف:")
        lbl_c_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #FBBF24; border: none; background: transparent;")
        self.txt_target_c = QLineEdit("0")
        self.txt_target_c.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_target_c.setFixedWidth(54)
        self.txt_target_c.setFixedHeight(24)
        self.txt_target_c.setStyleSheet("font-weight: bold; font-size: 11px; color: #FBBF24; background-color: #0F172A; border: 1px solid #F59E0B; border-radius: 4px; padding: 1px 2px;")
        self.txt_target_c.setToolTip("هدف کل کربوهیدرات روزانه (گرم) — قابل ویرایش دستی\nفرمول: وزن شاگرد (kg) × عدد گرم بر کیلوگرم | هر گرم کربوهیدرات = ۴ کیلوکالری ثابت")
        self.txt_target_c.textEdited.connect(lambda: self._on_target_macro_edited("carbs"))
        lbl_c_unit = QLabel("گرم")
        lbl_c_unit.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        self.lbl_target_c_kcal = QLabel("(۰ کیلوکالری)")
        self.lbl_target_c_kcal.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        c_top.addWidget(lbl_c_title)
        c_top.addWidget(self.txt_target_c)
        c_top.addWidget(lbl_c_unit)
        c_top.addWidget(self.lbl_target_c_kcal)
        c_top.addStretch()
        layout_c.addLayout(c_top)

        # Row 2: Grams per Kg Formula Factor & Fixed Energy Multiplier
        c_mid = QHBoxLayout()
        c_mid.setSpacing(4)
        lbl_f_c_icon = QLabel("⚖️ فرمول:")
        lbl_f_c_icon.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        self.txt_factor_c = QLineEdit(f"{init_factors['carbs']:.1f}")
        self.txt_factor_c.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_factor_c.setFixedWidth(46)
        self.txt_factor_c.setFixedHeight(22)
        self.txt_factor_c.setStyleSheet("font-weight: bold; font-size: 10px; color: #FDE68A; background-color: #1E293B; border: 1px solid #D97706; border-radius: 4px; padding: 1px 3px;")
        self.txt_factor_c.setToolTip("گرم کربوهیدرات به ازای هر ۱ کیلوگرم وزن بدن فرد (g/kg)\nفرمول: وزن شاگرد (kg) × عدد گرم بر کیلوگرم × ۴ کیلوکالری\nبا تغییر این عدد، هدف کربوهیدرات روزانه بر اساس وزن شاگرد محاسبه می‌شود.")
        self.txt_factor_c.textEdited.connect(lambda: self._on_factor_edited("carbs"))
        lbl_f_c_unit = QLabel("گرم/کیلوگرم")
        lbl_f_c_unit.setStyleSheet("font-size: 10px; color: #CBD5E1; border: none; background: transparent;")
        lbl_f_c_mult = QLabel("(ضریب ۴ کیلوکالری ثابت)")
        lbl_f_c_mult.setStyleSheet("font-size: 9px; color: #64748B; border: none; background: transparent;")
        c_mid.addWidget(lbl_f_c_icon)
        c_mid.addWidget(self.txt_factor_c)
        c_mid.addWidget(lbl_f_c_unit)
        c_mid.addWidget(lbl_f_c_mult)
        c_mid.addStretch()
        layout_c.addLayout(c_mid)

        # Row 3: Actual, Status, Suggestion
        c_bot = QHBoxLayout()
        c_bot.setSpacing(6)
        self.lbl_actual_c = QLabel("مصرفی: ۰ گرم")
        self.lbl_actual_c.setStyleSheet("font-size: 11px; font-weight: bold; color: #E2E8F0; border: none; background: transparent;")
        self.lbl_status_c = QLabel("۰ گرم باقیمانده")
        self.lbl_status_c.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_c.setFixedHeight(22)
        self.lbl_status_c.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #1E293B; color: #94A3B8; border: none;")
        self.btn_suggest_c = QPushButton("💡 پیشنهاد")
        self.btn_suggest_c.setFixedHeight(22)
        self.btn_suggest_c.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_suggest_c.setStyleSheet("""
            QPushButton {
                background-color: #3B2806;
                color: #FDE68A;
                border: 1px solid #D97706;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
                padding: 0 6px;
            }
            QPushButton:hover {
                background-color: #D97706;
                color: #FFFFFF;
            }
        """)
        self.btn_suggest_c.setToolTip("پیشنهاد مواد غذایی با کربوهیدرات پاک برای جبران کسری")
        self.btn_suggest_c.clicked.connect(lambda: self.show_macro_suggestions("carbs", self.btn_suggest_c))
        c_bot.addWidget(self.lbl_actual_c)
        c_bot.addWidget(self.lbl_status_c, 1)
        c_bot.addWidget(self.btn_suggest_c)
        layout_c.addLayout(c_bot)

        # Card 3: Fat (🥑 چربی مفید)
        self.card_fat = QFrame()
        self.card_fat.setObjectName("card_macro_fat")
        layout_f = QVBoxLayout(self.card_fat)
        layout_f.setContentsMargins(10, 8, 10, 8)
        layout_f.setSpacing(4)

        # Row 1: Target Grams & Kcal
        f_top = QHBoxLayout()
        f_top.setSpacing(4)
        lbl_f_title = QLabel("🥑 چربی مفید هدف:")
        lbl_f_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #34D399; border: none; background: transparent;")
        self.txt_target_f = QLineEdit("0")
        self.txt_target_f.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_target_f.setFixedWidth(54)
        self.txt_target_f.setFixedHeight(24)
        self.txt_target_f.setStyleSheet("font-weight: bold; font-size: 11px; color: #34D399; background-color: #0F172A; border: 1px solid #10B981; border-radius: 4px; padding: 1px 2px;")
        self.txt_target_f.setToolTip("هدف کل چربی مفید روزانه (گرم) — قابل ویرایش دستی\nفرمول: وزن شاگرد (kg) × عدد گرم بر کیلوگرم | هر گرم چربی = ۹ کیلوکالری ثابت")
        self.txt_target_f.textEdited.connect(lambda: self._on_target_macro_edited("fat"))
        lbl_f_unit = QLabel("گرم")
        lbl_f_unit.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        self.lbl_target_f_kcal = QLabel("(۰ کیلوکالری)")
        self.lbl_target_f_kcal.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        f_top.addWidget(lbl_f_title)
        f_top.addWidget(self.txt_target_f)
        f_top.addWidget(lbl_f_unit)
        f_top.addWidget(self.lbl_target_f_kcal)
        f_top.addStretch()
        layout_f.addLayout(f_top)

        # Row 2: Grams per Kg Formula Factor & Fixed Energy Multiplier
        f_mid = QHBoxLayout()
        f_mid.setSpacing(4)
        lbl_f_fat_icon = QLabel("⚖️ فرمول:")
        lbl_f_fat_icon.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        self.txt_factor_f = QLineEdit(f"{init_factors['fat']:.1f}")
        self.txt_factor_f.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_factor_f.setFixedWidth(46)
        self.txt_factor_f.setFixedHeight(22)
        self.txt_factor_f.setStyleSheet("font-weight: bold; font-size: 10px; color: #A7F3D0; background-color: #1E293B; border: 1px solid #059669; border-radius: 4px; padding: 1px 3px;")
        self.txt_factor_f.setToolTip("گرم چربی مفید به ازای هر ۱ کیلوگرم وزن بدن فرد (g/kg)\nفرمول: وزن شاگرد (kg) × عدد گرم بر کیلوگرم × ۹ کیلوکالری\nبا تغییر این عدد، هدف چربی مفید روزانه بر اساس وزن شاگرد محاسبه می‌شود.")
        self.txt_factor_f.textEdited.connect(lambda: self._on_factor_edited("fat"))
        lbl_f_fat_unit = QLabel("گرم/کیلوگرم")
        lbl_f_fat_unit.setStyleSheet("font-size: 10px; color: #CBD5E1; border: none; background: transparent;")
        lbl_f_fat_mult = QLabel("(ضریب ۹ کیلوکالری ثابت)")
        lbl_f_fat_mult.setStyleSheet("font-size: 9px; color: #64748B; border: none; background: transparent;")
        f_mid.addWidget(lbl_f_fat_icon)
        f_mid.addWidget(self.txt_factor_f)
        f_mid.addWidget(lbl_f_fat_unit)
        f_mid.addWidget(lbl_f_fat_mult)
        f_mid.addStretch()
        layout_f.addLayout(f_mid)

        # Row 3: Actual, Status, Suggestion
        f_bot = QHBoxLayout()
        f_bot.setSpacing(6)
        self.lbl_actual_f = QLabel("مصرفی: ۰ گرم")
        self.lbl_actual_f.setStyleSheet("font-size: 11px; font-weight: bold; color: #E2E8F0; border: none; background: transparent;")
        self.lbl_status_f = QLabel("۰ گرم باقیمانده")
        self.lbl_status_f.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_f.setFixedHeight(22)
        self.lbl_status_f.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #1E293B; color: #94A3B8; border: none;")
        self.btn_suggest_f = QPushButton("💡 پیشنهاد")
        self.btn_suggest_f.setFixedHeight(22)
        self.btn_suggest_f.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_suggest_f.setStyleSheet("""
            QPushButton {
                background-color: #064E3B;
                color: #A7F3D0;
                border: 1px solid #059669;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
                padding: 0 6px;
            }
            QPushButton:hover {
                background-color: #059669;
                color: #FFFFFF;
            }
        """)
        self.btn_suggest_f.setToolTip("پیشنهاد چربی‌های غیراشباع و دانه‌های مفید برای جبران کسری")
        self.btn_suggest_f.clicked.connect(lambda: self.show_macro_suggestions("fat", self.btn_suggest_f))
        f_bot.addWidget(self.lbl_actual_f)
        f_bot.addWidget(self.lbl_status_f, 1)
        f_bot.addWidget(self.btn_suggest_f)
        layout_f.addLayout(f_bot)

        # Card 4: Energy & Macro Summary (🔥 مجموع کالری و بالانس)
        self.card_energy = QFrame()
        self.card_energy.setObjectName("card_macro_energy")
        layout_e = QVBoxLayout(self.card_energy)
        layout_e.setContentsMargins(10, 8, 10, 8)
        layout_e.setSpacing(4)

        # Row 1: Target Energy
        e_top = QHBoxLayout()
        e_top.setSpacing(4)
        lbl_e_title = QLabel("🔥 انرژی هدف:")
        lbl_e_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #F43F5E; border: none; background: transparent;")
        self.lbl_target_energy = QLabel("۰ کیلوکالری")
        self.lbl_target_energy.setStyleSheet("font-weight: bold; font-size: 11px; color: #FBBF24; border: none; background: transparent;")
        e_top.addWidget(lbl_e_title)
        e_top.addWidget(self.lbl_target_energy)
        e_top.addStretch()
        layout_e.addLayout(e_top)

        # Row 2: Sync to TDEE Button
        e_mid = QHBoxLayout()
        e_mid.setSpacing(4)
        lbl_e_sub = QLabel("🎯 مجموع انرژی ۳ ماکرو")
        lbl_e_sub.setStyleSheet("font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        self.btn_sync_tdee = QPushButton("🎯 اعمال به TDEE")
        self.btn_sync_tdee.setFixedHeight(22)
        self.btn_sync_tdee.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync_tdee.setStyleSheet("""
            QPushButton {
                background-color: #1E1B4B;
                color: #C7D2FE;
                border: 1px solid #6366F1;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
                padding: 0 6px;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: #FFFFFF;
            }
        """)
        self.btn_sync_tdee.setToolTip("تنظیم فیلد TDEE بر اساس مجموع کیلوکالری محاسبه‌شده از اهداف ماکروها")
        self.btn_sync_tdee.clicked.connect(self._sync_tdee_with_macro_target)
        e_mid.addWidget(lbl_e_sub)
        e_mid.addStretch()
        e_mid.addWidget(self.btn_sync_tdee)
        layout_e.addLayout(e_mid)

        # Row 3: Actual Energy & Status
        e_bot = QHBoxLayout()
        e_bot.setSpacing(6)
        self.lbl_actual_energy = QLabel("مصرفی: ۰ کیلوکالری")
        self.lbl_actual_energy.setStyleSheet("font-size: 11px; font-weight: bold; color: #E2E8F0; border: none; background: transparent;")
        self.lbl_status_energy = QLabel("⚖️ بدون اختلاف")
        self.lbl_status_energy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_energy.setFixedHeight(22)
        self.lbl_status_energy.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background-color: #1E293B; color: #94A3B8; border: none;")
        e_bot.addWidget(self.lbl_actual_energy)
        e_bot.addWidget(self.lbl_status_energy, 1)
        layout_e.addLayout(e_bot)

        # Style cards
        card_qss = """
            QFrame#card_macro_protein,
            QFrame#card_macro_carbs,
            QFrame#card_macro_fat,
            QFrame#card_macro_energy {
                background-color: #111827;
                border: 1px solid #374151;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """
        for c in (self.card_protein, self.card_carbs, self.card_fat, self.card_energy):
            c.setStyleSheet(card_qss)

        self.row_macros.addWidget(self.card_protein, 1)
        self.row_macros.addWidget(self.card_carbs, 1)
        self.row_macros.addWidget(self.card_fat, 1)
        self.row_macros.addWidget(self.card_energy, 1)

        layout_form.addLayout(self.row_macros)

    def _on_goal_changed(self, _index: int = 0):
        goal_key = self.combo_goal.currentData() if hasattr(self, "combo_goal") else "maintenance"
        factors = self.GOAL_MACRO_FACTORS.get(goal_key, self.GOAL_MACRO_FACTORS["maintenance"])
        if hasattr(self, "txt_factor_p"):
            self.txt_factor_p.blockSignals(True)
            self.txt_factor_c.blockSignals(True)
            self.txt_factor_f.blockSignals(True)
            self.txt_factor_p.setText(f"{factors['protein']:.1f}")
            self.txt_factor_c.setText(f"{factors['carbs']:.1f}")
            self.txt_factor_f.setText(f"{factors['fat']:.1f}")
            self.txt_factor_p.blockSignals(False)
            self.txt_factor_c.blockSignals(False)
            self.txt_factor_f.blockSignals(False)

        self._recalculate_target_macros_from_weight()
        self.update_dynamic_calories()
        self._snapshot_change()

    def _get_factor_macro(self, macro_key: str) -> float:
        field_map = {
            "protein": getattr(self, "txt_factor_p", None),
            "carbs": getattr(self, "txt_factor_c", None),
            "fat": getattr(self, "txt_factor_f", None),
        }
        goal_key = self.combo_goal.currentData() if hasattr(self, "combo_goal") else "maintenance"
        fallback = self.GOAL_MACRO_FACTORS.get(goal_key, self.GOAL_MACRO_FACTORS["maintenance"]).get(macro_key, 2.0)
        fld = field_map.get(macro_key)
        if not fld:
            return float(fallback)
        raw = fld.text().strip()
        persian_to_eng = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩/،", "01234567890123456789..")
        clean = raw.translate(persian_to_eng)
        filtered = "".join(ch for ch in clean if ch.isdigit() or ch == '.')
        try:
            val = float(filtered)
            return val if val > 0 else float(fallback)
        except ValueError:
            return float(fallback)

    def _on_factor_edited(self, macro_key: str):
        w_kg = getattr(self, "_current_member_weight_kg", 0.0) or 0.0
        factor = self._get_factor_macro(macro_key)
        tgt_fld = {
            "protein": getattr(self, "txt_target_p", None),
            "carbs": getattr(self, "txt_target_c", None),
            "fat": getattr(self, "txt_target_f", None),
        }.get(macro_key)

        if tgt_fld and w_kg > 0:
            tgt_val = int(round(w_kg * factor))
            tgt_fld.blockSignals(True)
            tgt_fld.setText(str(tgt_val))
            tgt_fld.blockSignals(False)

        if macro_key == "protein" and hasattr(self, 'lbl_protein_warn'):
            f_val = self._get_factor_macro("protein")
            tgt_p = self._get_target_macro("protein")
            p_err = validate_protein(factor=f_val, total_grams=tgt_p)
            self.lbl_protein_warn.show_warning(p_err)

        self.update_dynamic_calories()
        self._snapshot_change()

    def _on_target_macro_edited(self, macro_key: str):
        w_kg = getattr(self, "_current_member_weight_kg", 0.0) or 0.0
        tgt_val = self._get_target_macro(macro_key)
        factor_fld = {
            "protein": getattr(self, "txt_factor_p", None),
            "carbs": getattr(self, "txt_factor_c", None),
            "fat": getattr(self, "txt_factor_f", None),
        }.get(macro_key)

        if factor_fld and w_kg > 0 and tgt_val > 0:
            rev_factor = tgt_val / w_kg
            factor_fld.blockSignals(True)
            factor_fld.setText(f"{rev_factor:.2f}" if abs(rev_factor - round(rev_factor, 1)) > 0.03 else f"{rev_factor:.1f}")
            factor_fld.blockSignals(False)

        self.update_dynamic_calories()
        self._snapshot_change()

    def _recalculate_target_macros_from_weight(self):
        w_kg = getattr(self, "_current_member_weight_kg", 0.0) or 0.0
        if w_kg <= 0:
            if hasattr(self, "txt_target_p"):
                self.txt_target_p.blockSignals(True)
                self.txt_target_c.blockSignals(True)
                self.txt_target_f.blockSignals(True)
                self.txt_target_p.setText("0")
                self.txt_target_c.setText("0")
                self.txt_target_f.setText("0")
                self.txt_target_p.blockSignals(False)
                self.txt_target_c.blockSignals(False)
                self.txt_target_f.blockSignals(False)
            return

        fp = self._get_factor_macro("protein")
        fc = self._get_factor_macro("carbs")
        ff = self._get_factor_macro("fat")

        tgt_p = int(round(w_kg * fp))
        tgt_c = int(round(w_kg * fc))
        tgt_f = int(round(w_kg * ff))

        if hasattr(self, "txt_target_p"):
            self.txt_target_p.blockSignals(True)
            self.txt_target_c.blockSignals(True)
            self.txt_target_f.blockSignals(True)

            self.txt_target_p.setText(str(tgt_p))
            self.txt_target_c.setText(str(tgt_c))
            self.txt_target_f.setText(str(tgt_f))

            self.txt_target_p.blockSignals(False)
            self.txt_target_c.blockSignals(False)
            self.txt_target_f.blockSignals(False)

    def _get_target_macro(self, macro_key: str) -> int:
        field_map = {
            "protein": getattr(self, "txt_target_p", None),
            "carbs": getattr(self, "txt_target_c", None),
            "fat": getattr(self, "txt_target_f", None),
        }
        fld = field_map.get(macro_key)
        if not fld:
            return 0
        raw = fld.text().strip()
        persian_to_eng = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        clean = "".join(ch for ch in raw.translate(persian_to_eng) if ch.isdigit())
        try:
            return int(clean) if clean else 0
        except ValueError:
            return 0

    def _get_target_protein(self) -> int:
        return self._get_target_macro("protein")

    def _get_target_carbs(self) -> int:
        return self._get_target_macro("carbs")

    def _get_target_fat(self) -> int:
        return self._get_target_macro("fat")

    def _get_target_calories(self) -> int:
        p = self._get_target_protein()
        c = self._get_target_carbs()
        f = self._get_target_fat()
        macro_cals = (p * 4) + (c * 4) + (f * 9)
        if macro_cals > 0:
            return macro_cals
        return getattr(self, "_current_member_tdee", 0) or 0

    def _sync_tdee_with_macro_target(self):
        macro_cals = self._get_target_calories()
        if macro_cals > 0:
            self._current_member_tdee = macro_cals
            self.txt_member_tdee.setText(f"\u200f{macro_cals:,} کیلوکالری")
            self.update_dynamic_calories()
            self._snapshot_change()

    def _get_active_meal_table(self):
        if not self.meal_tables:
            return None
        days_mode = self.combo_days.currentData() if hasattr(self, "combo_days") else "all_days"
        if days_mode == "all_days" or len(self.meal_tables) <= 6:
            idx = max(0, self.tabs.currentIndex()) if hasattr(self, "tabs") else 0
            if idx < len(self.meal_tables):
                return self.meal_tables[idx][1]
            return self.meal_tables[0][1]
        else:
            d_idx = max(0, self.tabs.currentIndex()) if hasattr(self, "tabs") else 0
            day_widget = self.tabs.currentWidget()
            m_idx = 0
            if isinstance(day_widget, QTabWidget):
                m_idx = max(0, day_widget.currentIndex())
            tbl_idx = d_idx * 6 + m_idx
            if 0 <= tbl_idx < len(self.meal_tables):
                return self.meal_tables[tbl_idx][1]
            return self.meal_tables[0][1]

    @staticmethod
    def _format_unit_desc(food, mult: float) -> str:
        u = food.unit or ""
        if "100 گرم" in u:
            return f"{int(round(mult * 100))} گرم"
        elif "عدد" in u:
            return f"{round(mult, 1)} عدد"
        elif "قاشق" in u:
            return f"{round(mult, 1)} قاشق"
        elif "اسکوپ" in u or "پیمانه" in u:
            return f"{round(mult, 1)} اسکوپ"
        elif "قوطی" in u:
            return f"{round(mult, 1)} قوطی"
        elif "کاسه" in u:
            return f"{round(mult, 1)} کاسه"
        elif "سیخ" in u:
            return f"{round(mult, 1)} سیخ"
        elif "لیوان" in u:
            return f"{round(mult, 1)} لیوان"
        return f"{mult} × ({u})"

    def _find_gap_filler_candidates(self, macro_key: str, gap_grams: float) -> list:
        if not self._foods_cache_by_id:
            try:
                for f in NutritionService.get_all_foods():
                    self._foods_cache_by_id[f.id] = f
            except Exception:
                pass

        preferred_ids = {
            "protein": [10, 13, 84, 79, 36, 303],
            "carbs": [7, 2, 8, 26, 3, 120, 209],
            "fat": [287, 288, 283, 271, 293]
        }.get(macro_key, [])

        candidates = []
        seen_ids = set()

        for pid in preferred_ids:
            f = self._foods_cache_by_id.get(pid)
            if f:
                val = 0.0
                if macro_key == "protein":
                    val = f.protein_g or 0.0
                elif macro_key == "carbs":
                    val = f.carbs_g or 0.0
                elif macro_key == "fat":
                    val = f.fat_g or 0.0

                if val > 0:
                    mult = round(gap_grams / val, 2)
                    if mult > 0:
                        cal_added = int(round((f.calories or 0.0) * mult))
                        desc_unit = self._format_unit_desc(f, mult)
                        candidates.append((f, mult, cal_added, desc_unit))
                        seen_ids.add(f.id)

        # Dynamic search from bank foods for pure sources
        for f in self._foods_cache_by_id.values():
            if f.id in seen_ids or (f.calories or 0.0) <= 0:
                continue
            cal = f.calories or 0.0
            if macro_key == "protein":
                m_val = f.protein_g or 0.0
                if m_val >= 5.0 and (m_val * 4) / cal >= 0.70:
                    mult = round(gap_grams / m_val, 2)
                    candidates.append((f, mult, int(round(cal * mult)), self._format_unit_desc(f, mult)))
                    seen_ids.add(f.id)
            elif macro_key == "carbs":
                m_val = f.carbs_g or 0.0
                if m_val >= 15.0 and (m_val * 4) / cal >= 0.80:
                    mult = round(gap_grams / m_val, 2)
                    candidates.append((f, mult, int(round(cal * mult)), self._format_unit_desc(f, mult)))
                    seen_ids.add(f.id)
            elif macro_key == "fat":
                m_val = f.fat_g or 0.0
                if m_val >= 8.0 and (m_val * 9) / cal >= 0.80:
                    mult = round(gap_grams / m_val, 2)
                    candidates.append((f, mult, int(round(cal * mult)), self._format_unit_desc(f, mult)))
                    seen_ids.add(f.id)

        return candidates[:8]

    def show_macro_suggestions(self, macro_key: str, btn: QPushButton):
        days_mode = self.combo_days.currentData() if hasattr(self, "combo_days") else "all_days"
        if days_mode == "all_days" or len(self.meal_tables) <= 6:
            active_tables = [tbl for _, tbl in self.meal_tables]
            day_title = ""
        else:
            d_idx = max(0, self.tabs.currentIndex()) if hasattr(self, "tabs") else 0
            day_slice = self.meal_tables[d_idx * 6 : (d_idx + 1) * 6]
            active_tables = [tbl for _, tbl in day_slice]
            day_title = self.tabs.tabText(d_idx).replace("📅", "").strip() if hasattr(self, "tabs") else ""

        total_macro = 0.0
        for tbl in active_tables:
            for r in range(tbl.rowCount()):
                combo = tbl.cellWidget(r, 0)
                txt_amount = tbl.cellWidget(r, 1)
                f_id = combo.currentData() if combo else None
                amt = self._parse_amount(txt_amount.text() if txt_amount else "0")
                food = self._foods_cache_by_id.get(f_id) if f_id else None
                if food and amt > 0:
                    if macro_key == "protein":
                        total_macro += (food.protein_g or 0.0) * amt
                    elif macro_key == "carbs":
                        total_macro += (food.carbs_g or 0.0) * amt
                    elif macro_key == "fat":
                        total_macro += (food.fat_g or 0.0) * amt

        tgt_g = self._get_target_macro(macro_key)
        gap = tgt_g - int(round(total_macro))

        name_fa = {"protein": "پروتئین", "carbs": "کربوهیدرات", "fat": "چربی مفید"}.get(macro_key, "درشت‌مغذی")
        suffix = f" در {day_title}" if day_title else ""

        if gap <= 0:
            if tgt_g <= 0:
                msg = f"هدف مشخصی برای {name_fa} تعیین نشده است. لطفاً ابتدا هدف را در کادر مربوطه وارد نمایید."
            elif gap == 0:
                msg = f"سهمیه {name_fa}{suffix} دقیقاً تکمیل است (منطبق با هدف)."
            else:
                msg = f"سهمیه {name_fa}{suffix} تکمیل شده و {abs(gap)} گرم مازاد در برنامه وجود دارد."
            QMessageBox.information(self, f"وضعیت سهمیه {name_fa}", msg)
            return

        candidates = self._find_gap_filler_candidates(macro_key, float(gap))
        if not candidates:
            QMessageBox.information(self, "عدم یافتن مورد مناسب", f"ماده غذایی با نسبت خالص برای تامین {gap} گرم {name_fa} در بانک یافت نشد.")
            return

        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1F2937;
                color: #F9FAFB;
                border: 1px solid #374151;
                border-radius: 8px;
                padding: 6px;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #374151;
                color: #34D399;
            }
            QMenu::separator {
                height: 1px;
                background-color: #374151;
                margin: 4px 6px;
            }
        """)

        header_act = menu.addAction(f"💡 گزینه‌های هوشمند برای کسری {gap} گرم {name_fa}{suffix}:")
        header_act.setEnabled(False)
        menu.addSeparator()

        for food, mult, cal_added, desc_unit in candidates:
            text = f"➕ {food.name_fa}: {desc_unit} (تامین {gap} گرم {name_fa} | {cal_added:,} کیلوکالری)"
            act = menu.addAction(text)
            act.triggered.connect(
                lambda _, f_id=food.id, m=mult, n=f"تامین سهمیه {name_fa} روزانه": self._apply_gap_suggestion(f_id, m, n)
            )

        menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))

    def _apply_gap_suggestion(self, food_id: int, amount: float, notes_text: str = ""):
        target_table = self._get_active_meal_table()
        if not target_table:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا یک وعده غذایی را از جدول‌های برنامه انتخاب نمایید.")
            return

        empty_row = -1
        for r in range(target_table.rowCount()):
            combo = target_table.cellWidget(r, 0)
            if combo and (combo.currentIndex() < 0 or not combo.currentText().strip()):
                empty_row = r
                break

        if empty_row >= 0:
            row = empty_row
        else:
            row = target_table.rowCount()
            target_table.insertRow(row)
            foods_list = NutritionService.get_all_foods()
            self._create_food_row_widgets(target_table, row, foods_list)

        combo_food = target_table.cellWidget(row, 0)
        txt_amount = target_table.cellWidget(row, 1)
        txt_notes = target_table.cellWidget(row, 3)

        if combo_food:
            idx = combo_food.findData(food_id)
            if idx >= 0:
                combo_food.setCurrentIndex(idx)
        if txt_amount:
            txt_amount.setText(str(amount))
        if txt_notes and notes_text:
            if not txt_notes.text().strip():
                txt_notes.setText(notes_text)

        self.update_dynamic_calories()
        self._snapshot_change()

    def _create_food_row_widgets(self, table: QTableWidget, row: int, foods_list: list, data: dict = None):
        if not data:
            data = {}
        for f in foods_list:
            self._foods_cache_by_id[f.id] = f

        combo_food = SearchableComboBox(placeholder="جستجو یا تایپ نام ماده غذایی...")
        for f in foods_list:
            combo_food.addItem(f"{f.name_fa} ({f.unit} - {int(f.calories)} کیلوکالری)", f.id)

        f_id = data.get("food_id")
        custom_name = data.get("food_text") or data.get("custom_food_name")
        if f_id:
            idx_f = combo_food.findData(f_id)
            if idx_f >= 0:
                combo_food.setCurrentIndex(idx_f)
            elif custom_name:
                combo_food.setCurrentIndex(-1)
                combo_food.setEditText(custom_name)
            else:
                combo_food.set_empty()
        elif custom_name:
            combo_food.setCurrentIndex(-1)
            combo_food.setEditText(custom_name)
        else:
            combo_food.set_empty()

        txt_amount = QLineEdit(str(data.get("amount", "1.0")))
        txt_amount.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_row_cal = QLabel("\u200f0 کیلوکالری")
        lbl_row_cal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_row_cal.setStyleSheet("color: #9CA3AF; font-size: 12px;")

        txt_notes = QLineEdit(str(data.get("notes", "")))
        txt_notes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt_notes.setPlaceholderText("توضیحات اختصاصی...")

        btn_del = QPushButton("🗑️")
        btn_del.setObjectName("danger_button")
        btn_del.setToolTip("حذف ماده غذایی")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.clicked.connect(lambda _, t=table, b=btn_del: self.remove_food_row(t, b))

        # Connect listeners to snapshot undo & dynamic calorie calculation
        combo_food.currentIndexChanged.connect(lambda _: (self.update_dynamic_calories(), self._snapshot_change()))
        combo_food.currentTextChanged.connect(lambda _: self.update_dynamic_calories())
        txt_amount.textChanged.connect(lambda _: self.update_dynamic_calories())
        txt_amount.textEdited.connect(lambda _: self._snapshot_change())
        txt_notes.textEdited.connect(lambda _: self._snapshot_change())

        table.setCellWidget(row, 0, combo_food)
        table.setCellWidget(row, 1, txt_amount)
        table.setCellWidget(row, 2, lbl_row_cal)
        table.setCellWidget(row, 3, txt_notes)
        table.setCellWidget(row, 4, btn_del)
        self.update_dynamic_calories()

    def add_food_row(self, table: QTableWidget, foods_list: list = None):
        row = table.rowCount()
        table.insertRow(row)
        if not foods_list:
            foods_list = NutritionService.get_all_foods()
        self._create_food_row_widgets(table, row, foods_list)
        self.update_dynamic_calories()
        self._snapshot_change()

    def remove_food_row(self, table: QTableWidget, btn: QPushButton):
        for r in range(table.rowCount()):
            if table.cellWidget(r, 4) == btn:
                table.removeRow(r)
                break
        self.update_dynamic_calories()
        self._snapshot_change()

    def _create_meal_widget(self, meal_key: str, meal_title: str, foods_list: list) -> QWidget:
        widget = QWidget()
        layout_meal = QVBoxLayout(widget)
        layout_meal.setContentsMargins(6, 6, 6, 6)
        layout_meal.setSpacing(6)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["نام ماده غذایی", "مقدار (ضریب واحد)", "کیلوکالری دریافتی", "توضیحات مربی", "حذف"])
        table.verticalHeader().setDefaultSectionSize(48)
        table.verticalHeader().setMinimumSectionSize(40)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(1, 125)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(2, 115)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(4, 60)

        layout_meal.addWidget(table)
        self.meal_tables.append((meal_key, table))
        return widget

    def _create_meal_tab_corner_widget(self) -> QWidget:
        corner = QWidget()
        corner_layout = QHBoxLayout(corner)
        corner_layout.setContentsMargins(6, 2, 8, 2)
        corner_layout.setSpacing(6)

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
        btn_add_item.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_item.clicked.connect(self.on_add_food_clicked)

        corner_layout.addWidget(btn_undo)
        corner_layout.addWidget(btn_redo)
        corner_layout.addWidget(btn_add_item)

        return corner

    def get_current_active_meal_table(self) -> QTableWidget:
        current_w = self.tabs.currentWidget()
        if isinstance(current_w, QTabWidget):
            current_w = current_w.currentWidget()
        if current_w:
            tbl = current_w.findChild(QTableWidget)
            if tbl:
                return tbl
        if self.meal_tables:
            return self.meal_tables[0][1]
        return None

    def on_add_food_clicked(self):
        table = self.get_current_active_meal_table()
        if table:
            foods_list = NutritionService.get_all_foods()
            self.add_food_row(table, foods_list)

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
        for f in foods_list:
            self._foods_cache_by_id[f.id] = f

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
        elif days_mode == "training_rest":
            days = [
                ("training", "روزهای تمرینی"),
                ("rest", "روزهای استراحت")
            ]
        elif days_mode == "2_days":
            days = [("day1", "روز اول"), ("day2", "روز دوم")]
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
            self.tabs.setCornerWidget(self._create_meal_tab_corner_widget(), Qt.Corner.TopRightCorner)
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
                day_tab_widget.setCornerWidget(self._create_meal_tab_corner_widget(), Qt.Corner.TopRightCorner)
                self.tabs.addTab(day_tab_widget, f"📅 {day_title}")

        self.tabs.blockSignals(False)
        self._update_undo_redo_ui()
        self.update_dynamic_calories()

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
        self.update_dynamic_calories()

    def get_plan_data(self):
        title = self.txt_title.text().strip() or "برنامه غذایی ایرانی"
        meals_data = []
        total_cal = 0.0
        total_p = 0.0
        total_c = 0.0
        total_f = 0.0
        days_count = max(1, len(self.meal_tables) // 6) if len(self.meal_tables) >= 6 else 1

        # Build bank foods lookup by name and display format
        bank_foods = NutritionService.get_all_foods(include_unlisted=False)
        bank_food_by_name = {f.name_fa.strip().lower(): f for f in bank_foods}

        for idx, (meal_key, table) in enumerate(self.meal_tables, start=1):
            items = []
            for row in range(table.rowCount()):
                combo_food = table.cellWidget(row, 0)
                if not combo_food:
                    continue
                raw_text = combo_food.currentText().strip()
                if not raw_text:
                    continue

                food_id = combo_food.currentData()
                custom_name = None

                # Check if currentData matches currentText
                idx_curr = combo_food.currentIndex()
                if idx_curr >= 0:
                    selected_item_text = combo_food.itemText(idx_curr).strip().lower()
                    if selected_item_text != raw_text.lower():
                        # The user modified the text, verify against bank
                        lower_text = raw_text.lower()
                        if lower_text in bank_food_by_name:
                            matched_food = bank_food_by_name[lower_text]
                            food_id = matched_food.id
                        else:
                            matched = None
                            for f in bank_foods:
                                if f.name_fa.strip().lower() == lower_text:
                                    matched = f
                                    break
                            if matched:
                                food_id = matched.id
                            else:
                                food_id = None
                                custom_name = raw_text
                else:
                    # User typed freely
                    lower_text = raw_text.lower()
                    if lower_text in bank_food_by_name:
                        matched_food = bank_food_by_name[lower_text]
                        food_id = matched_food.id
                    else:
                        matched = None
                        for f in bank_foods:
                            if f.name_fa.strip().lower() == lower_text:
                                matched = f
                                break
                        if matched:
                            food_id = matched.id
                        else:
                            food_id = None
                            custom_name = raw_text

                amount_str = table.cellWidget(row, 1).text().strip()
                notes_widget = table.cellWidget(row, 3)
                notes = notes_widget.text().strip() if notes_widget else ""

                amount = self._parse_amount(amount_str)
                if amount <= 0:
                    amount = 1.0

                food = self._foods_cache_by_id.get(food_id) if food_id else None
                if food:
                    total_cal += (food.calories or 0.0) * amount
                    total_p += (food.protein_g or 0.0) * amount
                    total_c += (food.carbs_g or 0.0) * amount
                    total_f += (food.fat_g or 0.0) * amount

                items.append({
                    "food_id": food_id,
                    "custom_food_name": custom_name,
                    "amount": amount,
                    "notes": notes
                })

            meals_data.append({
                "meal_name": meal_key,
                "order_index": idx,
                "items": items
            })

        p_tgt = float(self._get_target_protein())
        c_tgt = float(self._get_target_carbs())
        f_tgt = float(self._get_target_fat())
        cal_tgt = float(self._get_target_calories())

        plan_info = {
            "title": title,
            "goal": self.combo_goal.currentData(),
            "target_calories": cal_tgt if cal_tgt > 0 else (round(total_cal / days_count, 1) if total_cal > 0 else float(getattr(self, "_current_member_tdee", 0) or 0.0)),
            "target_protein": p_tgt if p_tgt > 0 else round(total_p / days_count, 1),
            "target_carbs": c_tgt if c_tgt > 0 else round(total_c / days_count, 1),
            "target_fat": f_tgt if f_tgt > 0 else round(total_f / days_count, 1)
        }
        return plan_info, meals_data

    def _handle_unregistered_foods(self, meals_data: list, mode: str = "assign") -> bool:
        """
        Scans meals_data for food items that don't have a food_id in the bank.
        If any are found, shows UnregisteredItemsDialog.
        Returns True to proceed with plan creation/assignment, or False if canceled.
        """
        unregistered_names = []
        for m in meals_data:
            for itm in m.get("items", []):
                if not itm.get("food_id") and itm.get("custom_food_name"):
                    name = itm["custom_food_name"]
                    if name not in unregistered_names:
                        unregistered_names.append(name)

        if not unregistered_names:
            return True

        dlg = UnregisteredItemsDialog(
            item_type="food",
            unregistered_items=unregistered_names,
            mode=mode,
            parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False

        action = dlg.action_result
        if action == UnregisteredItemsDialog.ACTION_CANCEL:
            return False

        is_unlisted = (action == UnregisteredItemsDialog.ACTION_UNLISTED)
        name_to_id = {}
        for name in unregistered_names:
            created_food = NutritionService.add_custom_food({
                "name_fa": name,
                "category": "other",
                "unit": "واحد",
                "calories": 0.0,
                "protein_g": 0.0,
                "carbs_g": 0.0,
                "fat_g": 0.0,
                "is_custom": True,
                "is_unlisted": is_unlisted
            })
            name_to_id[name] = created_food.id

        # Update meals_data with newly created IDs
        for m in meals_data:
            for itm in m.get("items", []):
                c_name = itm.get("custom_food_name")
                if not itm.get("food_id") and c_name in name_to_id:
                    itm["food_id"] = name_to_id[c_name]
                    if not is_unlisted:
                        itm["custom_food_name"] = None

        if not is_unlisted:
            self.refresh_editor()

        return True

    def save_plan(self, auto_reset: bool = True):
        plan_info, meals_data = self.get_plan_data()
        total_items = sum(len(m.get("items", [])) for m in meals_data)
        if total_items == 0:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا حداقل یک ماده غذایی به برنامه اضافه کنید.")
            return None

        # Check duplicate template title in nutrition plans bank
        title = plan_info["title"].strip()
        all_plans = NutritionService.get_all_plans()
        other_titles = [p.title for p in all_plans if not (self.editing_plan_id and p.id == self.editing_plan_id) and p.title]
        if any(t.strip().lower() == title.lower() for t in other_titles):
            from nemov.utils.duplicate_helper import get_next_numbered_name
            suggested_title = get_next_numbered_name(title, other_titles)
            reply = QMessageBox.question(
                self,
                "هشدار عنوان تکراری",
                f"الگوی برنامه غذایی دیگری با عنوان «{title}» از قبل در بانک الگوها ثبت شده است.\n\nدر صورت تایید، این الگو با عنوان «{suggested_title}» ذخیره خواهد شد.\nآیا مایل به ذخیره هستید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.txt_title.setFocus()
                return None
            title = suggested_title
            plan_info["title"] = suggested_title
            self.txt_title.setText(suggested_title)

        # Check and handle unregistered food items in the bank
        if not self._handle_unregistered_foods(meals_data, mode="save"):
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
                from nemov.utils.logger import log_info
                log_info(f"Updated nutrition plan template: '{plan.title}' (ID: {plan.id})")
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
                from nemov.utils.logger import log_info
                log_info(f"Created nutrition plan template: '{plan.title}' (ID: {plan.id})")
                QMessageBox.information(self, "موفقیت", "الگوی برنامه غذایی با موفقیت در بانک ذخیره شد.")
            return plan
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from nemov.utils.logger import log_error
            from nemov.views.components.error_dialog import show_error_dialog
            log_error(f"Error saving nutrition template: {e}\n{tb}")
            show_error_dialog(
                parent=self,
                message="متاسفانه در ذخیره‌سازی الگوی برنامه غذایی خطایی رخ داد.",
                technical_details=tb,
                title="خطا در ذخیره برنامه غذایی"
            )
            return None

    def _do_reset_fields(self):
        """پاکسازی فیلدهای مشخصات کلی رژیم"""
        widgets_to_block = [self.txt_title, self.combo_goal, self.combo_days, self.combo_templates]
        if hasattr(self, "txt_target_p"):
            widgets_to_block.extend([self.txt_target_p, self.txt_target_c, self.txt_target_f])
        if hasattr(self, "txt_factor_p"):
            widgets_to_block.extend([self.txt_factor_p, self.txt_factor_c, self.txt_factor_f])
        for w in widgets_to_block:
            w.blockSignals(True)

        self.txt_title.setText("")
        self.combo_goal.setCurrentIndex(0)
        self.combo_days.setCurrentIndex(0)

        if hasattr(self, "txt_target_p"):
            self.txt_target_p.setText("0")
            self.txt_target_c.setText("0")
            self.txt_target_f.setText("0")

        if hasattr(self, "txt_factor_p"):
            init_goal = self.combo_goal.itemData(0) or "muscle_gain"
            init_facs = self.GOAL_MACRO_FACTORS.get(init_goal, self.GOAL_MACRO_FACTORS["maintenance"])
            self.txt_factor_p.setText(f"{init_facs['protein']:.1f}")
            self.txt_factor_c.setText(f"{init_facs['carbs']:.1f}")
            self.txt_factor_f.setText(f"{init_facs['fat']:.1f}")

        for w in widgets_to_block:
            w.blockSignals(False)

        # Clear athlete selection completely
        self._sync_member_combos(None)

        # Reset TDEE, weight and calorie calculations to 0
        self._current_member_tdee = 0
        self._current_member_weight_kg = 0.0
        if hasattr(self, "txt_member_tdee"):
            self.txt_member_tdee.setText("0")
            self.txt_member_tdee.setToolTip("با انتخاب ورزشکار، مقدار TDEE ایشان به صورت خودکار محاسبه و درج می‌شود.")
        self.update_dynamic_calories()

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

        # Check duplicate nutrition plan for this member
        title = plan_info["title"].strip()
        existing_asgns = NutritionService.get_member_assignments(member_id)
        if existing_asgns:
            from nemov.services.member_service import MemberService
            member = MemberService.get_member_by_id(member_id)
            member_name = member.full_name if member else "این ورزشکار"
            other_titles = [asgn.plan.title for asgn in existing_asgns if asgn.plan and asgn.plan.title]
            if any(t.strip().lower() == title.lower() for t in other_titles):
                from nemov.utils.duplicate_helper import get_next_numbered_name
                suggested_title = get_next_numbered_name(title, other_titles)
                reply = QMessageBox.question(
                    self,
                    "هشدار برنامه تکراری برای ورزشکار",
                    f"برای ورزشکار «{member_name}» قبلاً برنامه غذایی با عنوان «{title}» صادر شده است.\n\nدر صورت تایید، این برنامه با عنوان «{suggested_title}» برای ایشان صادر خواهد شد.\nآیا مطمئن هستید؟",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.txt_title.setFocus()
                    return
                title = suggested_title
                plan_info["title"] = suggested_title
                self.txt_title.setText(suggested_title)

        # Check and handle unregistered food items in the bank
        if not self._handle_unregistered_foods(meals_data, mode="assign"):
            return

        try:
            plan = NutritionService.create_nutrition_plan(plan_info, meals_data)
            NutritionService.assign_nutrition_plan(member_id, plan.id)
            from nemov.utils.logger import log_info
            log_info(f"Assigned nutrition plan '{plan.title}' to member ID {member_id}")
            QMessageBox.information(self, "موفقیت", "برنامه غذایی با موفقیت به ورزشکار تخصیص یافت.")
            self.reset_form()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from nemov.utils.logger import log_error
            from nemov.views.components.error_dialog import show_error_dialog
            log_error(f"Error assigning nutrition plan: {e}\n{tb}")
            show_error_dialog(
                parent=self,
                message="متاسفانه در تخصیص برنامه غذایی به ورزشکار خطایی رخ داد.",
                technical_details=tb,
                title="خطا در تخصیص برنامه غذایی"
            )

    def open_food_bank(self):
        from nemov.views.food_library_dialog import FoodLibraryDialog
        dlg = FoodLibraryDialog(self)
        dlg.exec()
        self.setup_meal_tabs()
