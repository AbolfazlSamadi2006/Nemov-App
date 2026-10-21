from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QTextEdit, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from nemov.services.workout_service import WorkoutService
from nemov.services.nutrition_service import NutritionService
from nemov.services.member_service import MemberService
from nemov.pdf.pdf_generator import PDFGenerator
from nemov.models.database_models import Member
from nemov.views.components.searchable_combo_box import SearchableComboBox
from nemov.views.components.undo_delete_banner import UndoDeleteBanner
import re
from nemov.utils.jalali_date import get_now_shamsi_for_filename


class AssignTemplateDialog(QDialog):
    """Dialog to assign a Workout or Nutrition Template directly to a Member."""
    def __init__(self, template_type: str, template_id: int, template_title: str, parent=None):
        super().__init__(parent)
        self.template_type = template_type  # 'workout' or 'nutrition'
        self.template_id = template_id
        self.template_title = template_title

        type_fa = "تمرینی" if template_type == "workout" else "غذایی"
        self.setWindowTitle(f"🎯 تخصیص الگوی {type_fa}: {template_title}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(480, 320)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        lbl_info = QLabel(f"<b>الگوی انتخابی:</b> {self.template_title}")
        lbl_info.setStyleSheet("font-size: 14px; color: #FFFFFF;")
        layout.addWidget(lbl_info)

        layout.addWidget(QLabel("انتخاب ورزشکار (شاگرد):"))
        self.combo_member = SearchableComboBox(placeholder="جستجو یا تایپ نام ورزشکار...")
        self.combo_member.setFixedHeight(36)
        self.load_members()
        layout.addWidget(self.combo_member)

        layout.addWidget(QLabel("یادداشت یا توضیحات مربی (اختیاری):"))
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("نکات و راهنمایی‌های مربی برای ورزشکار...")
        self.txt_notes.setMaximumHeight(80)
        layout.addWidget(self.txt_notes)

        btn_box = QHBoxLayout()
        btn_assign = QPushButton("✅ تایید و تخصیص برنامه")
        btn_assign.setFixedHeight(36)
        btn_assign.clicked.connect(self.assign)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_assign)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def load_members(self):
        self.combo_member.clear()
        members = MemberService.get_all_members(status_filter="active")
        for m in members:
            self.combo_member.addItem(m.full_name, m.id)
        self.combo_member.set_empty()

    def assign(self):
        member_id = self.combo_member.currentData()
        if not member_id:
            QMessageBox.warning(self, "خطا", "لطفاً یک ورزشکار را انتخاب کنید.")
            return

        notes = self.txt_notes.toPlainText().strip() or None

        if self.template_type == "workout":
            # Smart health warning check
            health_rec = MemberService.get_health_record(member_id)
            warnings = []
            if health_rec:
                if health_rec.knee_injury: warnings.append("ورزشکار سابقه آسیب زانو دارد.")
                if health_rec.back_injury: warnings.append("ورزشکار سابقه فتق دیسک کمر دارد.")
                if health_rec.shoulder_injury: warnings.append("ورزشکار سابقه آسیب شانه دارد.")

            if warnings:
                msg = "⚠️ هشدارهای پزشکی ورزشکار:\n" + "\n".join(warnings) + "\n\nآیا مایل به تخصیص برنامه تمرینی هستید؟"
                reply = QMessageBox.question(self, "هشدار پزشکی", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    return

            WorkoutService.assign_plan_to_member(member_id, self.template_id, notes=notes)
            QMessageBox.information(self, "موفقیت", f"الگوی تمرینی با موفقیت به «{self.combo_member.currentText()}» تخصیص یافت.")
        else:
            NutritionService.assign_nutrition_plan(member_id, self.template_id, notes=notes)
            QMessageBox.information(self, "موفقیت", f"الگوی غذایی با موفقیت به «{self.combo_member.currentText()}» تخصیص یافت.")

        self.accept()


class TemplatesManagerView(QWidget):
    edit_workout_requested = pyqtSignal(int)
    edit_nutrition_requested = pyqtSignal(int)
    new_workout_requested = pyqtSignal()
    new_nutrition_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.workout_plans = []
        self.nutrition_plans = []
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_all_templates()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title and Action Bar
        header = QHBoxLayout()
        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.clicked.connect(self.back_requested.emit)

        lbl_title = QLabel("📋 بانک و مدیریت الگوهای تمرینی و غذایی")
        lbl_title.setObjectName("h1")

        btn_refresh = QPushButton("🔄 به‌روزرسانی لیست")
        btn_refresh.setObjectName("secondary_button")
        btn_refresh.clicked.connect(self.load_all_templates)

        header.addWidget(btn_back)
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # Tabs Widget (Workout Templates / Nutrition Templates)
        self.tabs = QTabWidget()
        
        # Tab 1: Workouts
        self.tab_workouts = QWidget()
        self.init_workout_tab()
        self.tabs.addTab(self.tab_workouts, "🏋️ الگوهای تمرینی")

        # Tab 2: Nutrition
        self.tab_nutrition = QWidget()
        self.init_nutrition_tab()
        self.tabs.addTab(self.tab_nutrition, "🥗 الگوهای برنامه غذایی")

        layout.addWidget(self.tabs)

    def init_workout_tab(self):
        layout = QVBoxLayout(self.tab_workouts)
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(12)

        # Search & Filter Row
        row_filter = QHBoxLayout()
        row_filter.setSpacing(10)

        self.txt_search_workout = QLineEdit()
        self.txt_search_workout.setPlaceholderText("🔍 جستجوی الگوی تمرینی بر اساس نام یا عنوان...")
        self.txt_search_workout.textChanged.connect(self.filter_workout_table)

        self.combo_filter_workout_goal = QComboBox()
        self.combo_filter_workout_goal.addItem("همه اهداف تمرینی", "all")
        self.combo_filter_workout_goal.addItem("هایپرتروفی (عضله‌سازی)", "hypertrophy")
        self.combo_filter_workout_goal.addItem("چربی‌سوزی و کاهش وزن", "fat_loss")
        self.combo_filter_workout_goal.addItem("افزایش قدرت بی‌هوازی", "strength")
        self.combo_filter_workout_goal.addItem("حرکات اصلاحی و بهبود قامت", "corrective")
        self.combo_filter_workout_goal.addItem("آمادگی جسمانی عمومی", "general_fitness")
        self.combo_filter_workout_goal.addItem("استقامت عضلانی", "endurance")
        self.combo_filter_workout_goal.currentIndexChanged.connect(self.filter_workout_table)

        self.chk_select_all_w = QCheckBox("انتخاب همه")
        self.chk_select_all_w.toggled.connect(self.toggle_select_all_w)

        self.btn_bulk_delete_w = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete_w.setEnabled(False)
        self.btn_bulk_delete_w.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
            QPushButton:disabled {
                background-color: #4B5563;
                color: #9CA3AF;
            }
        """)
        self.btn_bulk_delete_w.clicked.connect(self.bulk_delete_workout_templates)

        btn_new_w = QPushButton("➕ ساخت الگوی تمرینی جدید")
        btn_new_w.clicked.connect(self.new_workout_requested.emit)

        row_filter.addWidget(self.txt_search_workout)
        row_filter.addWidget(self.combo_filter_workout_goal)
        row_filter.addWidget(self.chk_select_all_w)
        row_filter.addWidget(self.btn_bulk_delete_w)
        row_filter.addWidget(btn_new_w)
        layout.addLayout(row_filter)

        # Workout Templates Table
        self.table_workouts = QTableWidget()
        self.table_workouts.setColumnCount(9)
        self.table_workouts.setHorizontalHeaderLabels([
            "انتخاب", "ردیف", "عنوان و نام الگو", "هدف برنامه", "روزهای تمرین", "سطح تمرین", "تعداد حرکات", "شاگردان فعال", "عملیات"
        ])
        header = self.table_workouts.horizontalHeader()
        header.setMinimumSectionSize(40)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_workouts.setColumnWidth(0, 46)   # انتخاب
        self.table_workouts.setColumnWidth(1, 46)   # ردیف
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # عنوان
        self.table_workouts.setColumnWidth(3, 150)  # هدف
        self.table_workouts.setColumnWidth(4, 86)   # روزها
        self.table_workouts.setColumnWidth(5, 80)   # سطح
        self.table_workouts.setColumnWidth(6, 84)   # تعداد حرکات
        self.table_workouts.setColumnWidth(7, 87)   # شاگردان
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table_workouts.setColumnWidth(8, 286)  # عملیات

        self.table_workouts.verticalHeader().setVisible(False)
        self.table_workouts.verticalHeader().setDefaultSectionSize(52)
        self.table_workouts.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_workouts.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table_workouts, 1)

        self.undo_banner_w = UndoDeleteBanner(self)
        layout.addWidget(self.undo_banner_w)

    def init_nutrition_tab(self):
        layout = QVBoxLayout(self.tab_nutrition)
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(12)

        # Search & Filter Row
        row_filter = QHBoxLayout()
        row_filter.setSpacing(10)

        self.txt_search_nutrition = QLineEdit()
        self.txt_search_nutrition.setPlaceholderText("🔍 جستجوی الگوی غذایی بر اساس نام یا عنوان...")
        self.txt_search_nutrition.textChanged.connect(self.filter_nutrition_table)

        self.combo_filter_nutrition_goal = QComboBox()
        self.combo_filter_nutrition_goal.addItem("همه اهداف رژیم", "all")
        self.combo_filter_nutrition_goal.addItem("عضله‌سازی (Muscle Gain)", "muscle_gain")
        self.combo_filter_nutrition_goal.addItem("کاهش وزن و چربی‌سوزی (Weight Loss)", "weight_loss")
        self.combo_filter_nutrition_goal.addItem("افزایش وزن (Weight Gain)", "weight_gain")
        self.combo_filter_nutrition_goal.addItem("تثبیت وزن (Maintenance)", "maintenance")
        self.combo_filter_nutrition_goal.currentIndexChanged.connect(self.filter_nutrition_table)

        self.chk_select_all_n = QCheckBox("انتخاب همه")
        self.chk_select_all_n.toggled.connect(self.toggle_select_all_n)

        self.btn_bulk_delete_n = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete_n.setEnabled(False)
        self.btn_bulk_delete_n.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
            QPushButton:disabled {
                background-color: #4B5563;
                color: #9CA3AF;
            }
        """)
        self.btn_bulk_delete_n.clicked.connect(self.bulk_delete_nutrition_templates)

        btn_new_n = QPushButton("➕ ساخت الگوی غذایی جدید")
        btn_new_n.clicked.connect(self.new_nutrition_requested.emit)

        row_filter.addWidget(self.txt_search_nutrition)
        row_filter.addWidget(self.combo_filter_nutrition_goal)
        row_filter.addWidget(self.chk_select_all_n)
        row_filter.addWidget(self.btn_bulk_delete_n)
        row_filter.addWidget(btn_new_n)
        layout.addLayout(row_filter)

        # Nutrition Templates Table
        self.table_nutrition = QTableWidget()
        self.table_nutrition.setColumnCount(9)
        self.table_nutrition.setHorizontalHeaderLabels([
            "انتخاب", "ردیف", "عنوان و نام رژیم", "هدف رژیم", "کالری روزانه", "پروتئین / کربوهیدرات / چربی", "تعداد وعده‌ها", "شاگردان فعال", "عملیات"
        ])
        header = self.table_nutrition.horizontalHeader()
        header.setMinimumSectionSize(40)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_nutrition.setColumnWidth(0, 46)   # انتخاب
        self.table_nutrition.setColumnWidth(1, 46)   # ردیف
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # عنوان
        self.table_nutrition.setColumnWidth(3, 150)  # هدف
        self.table_nutrition.setColumnWidth(4, 86)   # کالری
        self.table_nutrition.setColumnWidth(5, 155)  # P/C/F
        self.table_nutrition.setColumnWidth(6, 85)   # وعده‌ها
        self.table_nutrition.setColumnWidth(7, 87)   # شاگردان
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table_nutrition.setColumnWidth(8, 286)  # عملیات

        self.table_nutrition.verticalHeader().setVisible(False)
        self.table_nutrition.verticalHeader().setDefaultSectionSize(52)
        self.table_nutrition.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_nutrition.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table_nutrition, 1)

        self.undo_banner_n = UndoDeleteBanner(self)
        layout.addWidget(self.undo_banner_n)

    def load_all_templates(self):
        self.load_workout_templates()
        self.load_nutrition_templates()

    def load_workout_templates(self):
        self.workout_plans = WorkoutService.get_all_plans()
        self.filter_workout_table()

    def filter_workout_table(self):
        query = self.txt_search_workout.text().strip().lower()
        selected_goal = self.combo_filter_workout_goal.currentData()

        filtered = []
        for p in self.workout_plans:
            if query and query not in (p.title or "").lower():
                continue
            if selected_goal and selected_goal != "all" and p.goal != selected_goal:
                continue
            filtered.append(p)

        goal_map = {
            "hypertrophy": "هایپرتروفی (عضله‌سازی)",
            "fat_loss": "چربی‌سوزی و کاهش وزن",
            "strength": "افزایش قدرت بی‌هوازی",
            "corrective": "حرکات اصلاحی و بهبود قامت",
            "general_fitness": "آمادگی جسمانی عمومی",
            "endurance": "استقامت عضلانی"
        }

        level_map = {
            "beginner": "مبتدی",
            "intermediate": "متوسط",
            "advanced": "پیشرفته"
        }

        self.chk_select_all_w.blockSignals(True)
        self.chk_select_all_w.setChecked(False)
        self.chk_select_all_w.blockSignals(False)
        self.btn_bulk_delete_w.setText("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete_w.setEnabled(False)

        self.table_workouts.setRowCount(0)
        self.table_workouts.setRowCount(len(filtered))

        for row, p in enumerate(filtered):
            # Total exercise count
            try:
                ex_count = sum(len(d.workout_exercises) for d in p.days) if p.days else 0
            except Exception:
                ex_count = 0

            # Assignments count
            try:
                assignments_count = len(p.assignments) if p.assignments else 0
            except Exception:
                assignments_count = 0

            # Checkbox in column 0
            chk_w = QWidget()
            chk_w.setStyleSheet("background: transparent;")
            chk_l = QHBoxLayout(chk_w)
            chk_l.setContentsMargins(0, 0, 0, 0)
            chk_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setProperty("item_id", p.id)
            chk.setProperty("item_name", p.title)
            chk.toggled.connect(self.on_workout_row_checkbox_toggled)
            chk_l.addWidget(chk)
            self.table_workouts.setCellWidget(row, 0, chk_w)

            self.table_workouts.setItem(row, 1, QTableWidgetItem(str(row + 1)))
            self.table_workouts.setItem(row, 2, QTableWidgetItem(p.title or "بدون عنوان"))
            self.table_workouts.setItem(row, 3, QTableWidgetItem(goal_map.get(p.goal, p.goal or "-")))
            self.table_workouts.setItem(row, 4, QTableWidgetItem(f"{p.days_per_week} روزه"))
            self.table_workouts.setItem(row, 5, QTableWidgetItem(level_map.get(p.training_level, p.training_level or "-")))
            self.table_workouts.setItem(row, 6, QTableWidgetItem(f"{ex_count} حرکت"))
            self.table_workouts.setItem(row, 7, QTableWidgetItem(f"{assignments_count} نفر"))

            for c in range(1, 8):
                item = self.table_workouts.item(row, c)
                if item and c != 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Actions Widget
            action_w = QWidget()
            action_w.setStyleSheet("background: transparent;")
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(6, 2, 6, 2)
            action_l.setSpacing(6)
            action_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_assign = QPushButton("🎯 تخصیص")
            btn_assign.setToolTip("تخصیص این الگو به یکی از شاگردان باشگاه")
            btn_assign.setFixedSize(78, 30)
            btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_assign.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 4px; font-size: 11px;")
            btn_assign.clicked.connect(lambda _, pid=p.id, ptitle=p.title: self.open_assign_dialog("workout", pid, ptitle))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setToolTip("بارگذاری در طراح تمرین جهت تغییر و ذخیره")
            btn_edit.setFixedSize(72, 30)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("""
                QPushButton {
                    background-color: #D97706;
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                    padding: 2px 4px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #B45309;
                }
            """)
            btn_edit.clicked.connect(lambda _, pid=p.id: self.edit_workout_requested.emit(pid))

            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setToolTip("خروجی و چاپ فایل PDF این الگو")
            btn_pdf.setFixedSize(56, 30)
            btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pdf.setStyleSheet("background-color: #3B82F6; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 4px; font-size: 11px;")
            btn_pdf.clicked.connect(lambda _, plan=p: self.export_workout_pdf(plan))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف الگو از بانک")
            btn_del.setFixedSize(36, 30)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 6px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, pid=p.id, ptitle=p.title: self.delete_workout_template(pid, ptitle))

            action_l.addWidget(btn_assign)
            action_l.addWidget(btn_edit)
            action_l.addWidget(btn_pdf)
            action_l.addWidget(btn_del)
            self.table_workouts.setCellWidget(row, 8, action_w)

    def load_nutrition_templates(self):
        self.nutrition_plans = NutritionService.get_all_plans()
        self.filter_nutrition_table()

    def filter_nutrition_table(self):
        query = self.txt_search_nutrition.text().strip().lower()
        selected_goal = self.combo_filter_nutrition_goal.currentData()

        filtered = []
        for p in self.nutrition_plans:
            if query and query not in (p.title or "").lower():
                continue
            if selected_goal and selected_goal != "all" and p.goal != selected_goal:
                continue
            filtered.append(p)

        goal_map = {
            "muscle_gain": "عضله‌سازی (Muscle Gain)",
            "weight_loss": "کاهش وزن (Weight Loss)",
            "weight_gain": "افزایش وزن (Weight Gain)",
            "maintenance": "تثبیت وزن (Maintenance)"
        }

        self.chk_select_all_n.blockSignals(True)
        self.chk_select_all_n.setChecked(False)
        self.chk_select_all_n.blockSignals(False)
        self.btn_bulk_delete_n.setText("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete_n.setEnabled(False)

        self.table_nutrition.setRowCount(0)
        self.table_nutrition.setRowCount(len(filtered))

        for row, p in enumerate(filtered):
            try:
                meals_count = len(p.meals) if p.meals else 0
            except Exception:
                meals_count = 0
            try:
                assignments_count = len(p.assignments) if p.assignments else 0
            except Exception:
                assignments_count = 0
            macros_str = f"P: {int(p.target_protein or 0)}g | C: {int(p.target_carbs or 0)}g | F: {int(p.target_fat or 0)}g"

            chk_w = QWidget()
            chk_w.setStyleSheet("background: transparent;")
            chk_l = QHBoxLayout(chk_w)
            chk_l.setContentsMargins(0, 0, 0, 0)
            chk_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setProperty("item_id", p.id)
            chk.setProperty("item_name", p.title)
            chk.toggled.connect(self.on_nutrition_row_checkbox_toggled)
            chk_l.addWidget(chk)
            self.table_nutrition.setCellWidget(row, 0, chk_w)

            self.table_nutrition.setItem(row, 1, QTableWidgetItem(str(row + 1)))
            self.table_nutrition.setItem(row, 2, QTableWidgetItem(p.title or "بدون عنوان"))
            self.table_nutrition.setItem(row, 3, QTableWidgetItem(goal_map.get(p.goal, p.goal or "-")))
            self.table_nutrition.setItem(row, 4, QTableWidgetItem(f"{int(p.target_calories or 0)} kcal"))
            self.table_nutrition.setItem(row, 5, QTableWidgetItem(macros_str))
            self.table_nutrition.setItem(row, 6, QTableWidgetItem(f"{meals_count} وعده"))
            self.table_nutrition.setItem(row, 7, QTableWidgetItem(f"{assignments_count} نفر"))

            for c in range(1, 8):
                item = self.table_nutrition.item(row, c)
                if item and c != 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Actions Widget
            action_w = QWidget()
            action_w.setStyleSheet("background: transparent;")
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(6, 2, 6, 2)
            action_l.setSpacing(6)
            action_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_assign = QPushButton("🎯 تخصیص")
            btn_assign.setToolTip("تخصیص این الگو به یکی از شاگردان باشگاه")
            btn_assign.setFixedSize(78, 30)
            btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_assign.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 4px; font-size: 11px;")
            btn_assign.clicked.connect(lambda _, pid=p.id, ptitle=p.title: self.open_assign_dialog("nutrition", pid, ptitle))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setToolTip("بارگذاری در طراح رژیم جهت تغییر و ذخیره")
            btn_edit.setFixedSize(72, 30)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("""
                QPushButton {
                    background-color: #D97706;
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                    padding: 2px 4px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #B45309;
                }
            """)
            btn_edit.clicked.connect(lambda _, pid=p.id: self.edit_nutrition_requested.emit(pid))

            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setToolTip("خروجی و چاپ فایل PDF این الگو")
            btn_pdf.setFixedSize(56, 30)
            btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pdf.setStyleSheet("background-color: #3B82F6; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 4px; font-size: 11px;")
            btn_pdf.clicked.connect(lambda _, plan=p: self.export_nutrition_pdf(plan))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف الگو از بانک")
            btn_del.setFixedSize(36, 30)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 6px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, pid=p.id, ptitle=p.title: self.delete_nutrition_template(pid, ptitle))

            action_l.addWidget(btn_assign)
            action_l.addWidget(btn_edit)
            action_l.addWidget(btn_pdf)
            action_l.addWidget(btn_del)
            self.table_nutrition.setCellWidget(row, 8, action_w)

    def toggle_select_all_w(self, checked):
        for r in range(self.table_workouts.rowCount()):
            cell_w = self.table_workouts.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(checked)
                    chk.blockSignals(False)
        self.on_workout_row_checkbox_toggled()

    def on_workout_row_checkbox_toggled(self):
        count = len(self.get_selected_workout_template_ids())
        total = self.table_workouts.rowCount()
        self.chk_select_all_w.blockSignals(True)
        self.chk_select_all_w.setChecked(count == total if total > 0 else False)
        self.chk_select_all_w.blockSignals(False)

        if count > 0:
            fa_num = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.btn_bulk_delete_w.setText(f"🗑️ حذف انتخاب‌شده‌ها ({fa_num})")
            self.btn_bulk_delete_w.setEnabled(True)
        else:
            self.btn_bulk_delete_w.setText("🗑️ حذف انتخاب‌شده‌ها")
            self.btn_bulk_delete_w.setEnabled(False)

    def get_selected_workout_template_ids(self):
        selected_ids = []
        for r in range(self.table_workouts.rowCount()):
            cell_w = self.table_workouts.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    selected_ids.append(chk.property("item_id"))
        return selected_ids

    def _hide_workout_rows_by_ids(self, ids):
        id_set = set(ids)
        for r in range(self.table_workouts.rowCount() - 1, -1, -1):
            cell_w = self.table_workouts.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.property("item_id") in id_set:
                    self.table_workouts.hideRow(r)

    def bulk_delete_workout_templates(self):
        selected_ids = self.get_selected_workout_template_ids()
        if not selected_ids:
            return

        count = len(selected_ids)
        fa_count = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        reply = QMessageBox.question(
            self, "تایید حذف گروهی الگوهای تمرینی",
            f"آیا از حذف {fa_count} الگوی تمرینی انتخاب‌شده اطمینان دارید؟\n\nنکته: پس از حذف، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_workout_rows_by_ids(selected_ids)

        def commit_delete(ids):
            for pid in ids:
                try:
                    WorkoutService.delete_plan(pid)
                except Exception:
                    pass
            self.load_workout_templates()

        def undo_delete(ids):
            self.load_workout_templates()

        self.undo_banner_w.start_countdown(
            item_count=count,
            pending_items=selected_ids,
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label="الگوی تمرینی"
        )

    def toggle_select_all_n(self, checked):
        for r in range(self.table_nutrition.rowCount()):
            cell_w = self.table_nutrition.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(checked)
                    chk.blockSignals(False)
        self.on_nutrition_row_checkbox_toggled()

    def on_nutrition_row_checkbox_toggled(self):
        count = len(self.get_selected_nutrition_template_ids())
        total = self.table_nutrition.rowCount()
        self.chk_select_all_n.blockSignals(True)
        self.chk_select_all_n.setChecked(count == total if total > 0 else False)
        self.chk_select_all_n.blockSignals(False)

        if count > 0:
            fa_num = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.btn_bulk_delete_n.setText(f"🗑️ حذف انتخاب‌شده‌ها ({fa_num})")
            self.btn_bulk_delete_n.setEnabled(True)
        else:
            self.btn_bulk_delete_n.setText("🗑️ حذف انتخاب‌شده‌ها")
            self.btn_bulk_delete_n.setEnabled(False)

    def get_selected_nutrition_template_ids(self):
        selected_ids = []
        for r in range(self.table_nutrition.rowCount()):
            cell_w = self.table_nutrition.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    selected_ids.append(chk.property("item_id"))
        return selected_ids

    def _hide_nutrition_rows_by_ids(self, ids):
        id_set = set(ids)
        for r in range(self.table_nutrition.rowCount() - 1, -1, -1):
            cell_w = self.table_nutrition.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.property("item_id") in id_set:
                    self.table_nutrition.hideRow(r)

    def bulk_delete_nutrition_templates(self):
        selected_ids = self.get_selected_nutrition_template_ids()
        if not selected_ids:
            return

        count = len(selected_ids)
        fa_count = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        reply = QMessageBox.question(
            self, "تایید حذف گروهی الگوهای غذایی",
            f"آیا از حذف {fa_count} الگوی غذایی انتخاب‌شده اطمینان دارید؟\n\nنکته: پس از حذف، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_nutrition_rows_by_ids(selected_ids)

        def commit_delete(ids):
            for pid in ids:
                try:
                    NutritionService.delete_nutrition_plan(pid)
                except Exception:
                    pass
            self.load_nutrition_templates()

        def undo_delete(ids):
            self.load_nutrition_templates()

        self.undo_banner_n.start_countdown(
            item_count=count,
            pending_items=selected_ids,
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label="الگوی غذایی"
        )

    def export_workout_pdf(self, plan):
        try:
            dummy_member = Member(first_name="نسخه عمومی", last_name="الگو", membership_expire_shamsi="-")
            plan_title = re.sub(r'[\\/*?:"<>|]', '', plan.title or str(plan.id)).strip()
            now_str = get_now_shamsi_for_filename()
            default_name = f"الگوی تمرینی {plan_title}_{now_str}.pdf"
            from nemov.utils.export_utils import resolve_gym_export_path
            filepath, gym_folder_name = resolve_gym_export_path(
                default_name, self.window(), "ذخیره فایل PDF الگوی تمرینی", "PDF Files (*.pdf)"
            )
            if filepath:
                PDFGenerator.generate_workout_pdf(dummy_member, plan, filepath)
                QMessageBox.information(
                    self,
                    "موفقیت",
                    f"فایل PDF الگوی تمرینی با موفقیت در پوشه اختصاصی «{gym_folder_name}» ذخیره شد:\n\n{filepath}"
                )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from nemov.utils.logger import log_error
            from nemov.views.components.error_dialog import show_error_dialog
            log_error(f"Error exporting workout template PDF: {e}\n{tb}")
            show_error_dialog(
                parent=self.window(),
                message="متاسفانه در حین ایجاد فایل PDF الگوی تمرینی خطایی رخ داد.",
                technical_details=tb,
                title="خطا در صدور PDF"
            )

    def export_nutrition_pdf(self, plan):
        try:
            dummy_member = Member(first_name="نسخه عمومی", last_name="الگو", membership_expire_shamsi="-")
            plan_title = re.sub(r'[\\/*?:"<>|]', '', plan.title or str(plan.id)).strip()
            now_str = get_now_shamsi_for_filename()
            default_name = f"الگوی غذایی {plan_title}_{now_str}.pdf"
            from nemov.utils.export_utils import resolve_gym_export_path
            filepath, gym_folder_name = resolve_gym_export_path(
                default_name, self.window(), "ذخیره فایل PDF الگوی غذایی", "PDF Files (*.pdf)"
            )
            if filepath:
                PDFGenerator.generate_nutrition_pdf(dummy_member, plan, filepath)
                QMessageBox.information(
                    self,
                    "موفقیت",
                    f"فایل PDF الگوی غذایی با موفقیت در پوشه اختصاصی «{gym_folder_name}» ذخیره شد:\n\n{filepath}"
                )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from nemov.utils.logger import log_error
            from nemov.views.components.error_dialog import show_error_dialog
            log_error(f"Error exporting nutrition template PDF: {e}\n{tb}")
            show_error_dialog(
                parent=self.window(),
                message="متاسفانه در حین ایجاد فایل PDF الگوی غذایی خطایی رخ داد.",
                technical_details=tb,
                title="خطا در صدور PDF"
            )

    def open_assign_dialog(self, template_type: str, template_id: int, template_title: str):
        dlg = AssignTemplateDialog(template_type, template_id, template_title, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_all_templates()

    def delete_workout_template(self, plan_id: int, plan_title: str):
        reply = QMessageBox.warning(
            self,
            "⚠️ تایید حذف الگوی تمرینی",
            f"آیا مطمئن هستید که می‌خواهید الگوی تمرینی «{plan_title}» را از بانک حذف کنید؟\n\nنکته: پس از تایید، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_workout_rows_by_ids([plan_id])

        def commit_delete(ids):
            for pid in ids:
                try:
                    WorkoutService.delete_plan(pid)
                except Exception as e:
                    QMessageBox.critical(self, "خطا", f"خطا در حذف الگو: {str(e)}")
            self.load_workout_templates()

        def undo_delete(ids):
            self.load_workout_templates()

        self.undo_banner_w.start_countdown(
            item_count=1,
            pending_items=[plan_id],
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label=f"«{plan_title}»"
        )

    def delete_nutrition_template(self, plan_id: int, plan_title: str):
        reply = QMessageBox.warning(
            self,
            "⚠️ تایید حذف الگوی غذایی",
            f"آیا مطمئن هستید که می‌خواهید الگوی غذایی «{plan_title}» را از بانک حذف کنید؟\n\nنکته: پس از تایید، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_nutrition_rows_by_ids([plan_id])

        def commit_delete(ids):
            for pid in ids:
                try:
                    NutritionService.delete_nutrition_plan(pid)
                except Exception as e:
                    QMessageBox.critical(self, "خطا", f"خطا در حذف الگو: {str(e)}")
            self.load_nutrition_templates()

        def undo_delete(ids):
            self.load_nutrition_templates()

        self.undo_banner_n.start_countdown(
            item_count=1,
            pending_items=[plan_id],
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label=f"«{plan_title}»"
        )