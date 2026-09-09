from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from yalda.services.workout_service import WorkoutService
from yalda.services.nutrition_service import NutritionService
from yalda.services.member_service import MemberService
from yalda.pdf.pdf_generator import PDFGenerator
from yalda.models.database_models import Member
from yalda.views.components.searchable_combo_box import SearchableComboBox


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

        btn_new_w = QPushButton("➕ ساخت الگوی تمرینی جدید")
        btn_new_w.clicked.connect(self.new_workout_requested.emit)

        row_filter.addWidget(self.txt_search_workout)
        row_filter.addWidget(self.combo_filter_workout_goal)
        row_filter.addWidget(btn_new_w)
        layout.addLayout(row_filter)

        # Workout Templates Table
        self.table_workouts = QTableWidget()
        self.table_workouts.setColumnCount(8)
        self.table_workouts.setHorizontalHeaderLabels([
            "ردیف", "عنوان و نام الگو", "هدف برنامه", "روزهای تمرین", "سطح تمرین", "تعداد حرکات", "شاگردان فعال", "عملیات"
        ])
        header = self.table_workouts.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_workouts.setColumnWidth(0, 45)   # ردیف
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # عنوان
        self.table_workouts.setColumnWidth(2, 160)  # هدف
        self.table_workouts.setColumnWidth(3, 90)   # روزها
        self.table_workouts.setColumnWidth(4, 85)   # سطح
        self.table_workouts.setColumnWidth(5, 85)   # تعداد حرکات
        self.table_workouts.setColumnWidth(6, 90)   # شاگردان
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table_workouts.setColumnWidth(7, 290)  # عملیات

        self.table_workouts.verticalHeader().setVisible(False)
        self.table_workouts.verticalHeader().setDefaultSectionSize(52)
        self.table_workouts.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_workouts.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table_workouts)

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

        btn_new_n = QPushButton("➕ ساخت الگوی غذایی جدید")
        btn_new_n.clicked.connect(self.new_nutrition_requested.emit)

        row_filter.addWidget(self.txt_search_nutrition)
        row_filter.addWidget(self.combo_filter_nutrition_goal)
        row_filter.addWidget(btn_new_n)
        layout.addLayout(row_filter)

        # Nutrition Templates Table
        self.table_nutrition = QTableWidget()
        self.table_nutrition.setColumnCount(8)
        self.table_nutrition.setHorizontalHeaderLabels([
            "ردیف", "عنوان و نام رژیم", "هدف رژیم", "کالری روزانه", "پروتئین / کربوهیدرات / چربی", "تعداد وعده‌ها", "شاگردان فعال", "عملیات"
        ])
        header = self.table_nutrition.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_nutrition.setColumnWidth(0, 45)   # ردیف
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # عنوان
        self.table_nutrition.setColumnWidth(2, 160)  # هدف
        self.table_nutrition.setColumnWidth(3, 95)   # کالری
        self.table_nutrition.setColumnWidth(4, 160)  # P/C/F
        self.table_nutrition.setColumnWidth(5, 85)   # وعده‌ها
        self.table_nutrition.setColumnWidth(6, 90)   # شاگردان
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table_nutrition.setColumnWidth(7, 290)  # عملیات

        self.table_nutrition.verticalHeader().setVisible(False)
        self.table_nutrition.verticalHeader().setDefaultSectionSize(52)
        self.table_nutrition.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_nutrition.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table_nutrition)

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

            self.table_workouts.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table_workouts.setItem(row, 1, QTableWidgetItem(p.title or "بدون عنوان"))
            self.table_workouts.setItem(row, 2, QTableWidgetItem(goal_map.get(p.goal, p.goal or "-")))
            self.table_workouts.setItem(row, 3, QTableWidgetItem(f"{p.days_per_week} روزه"))
            self.table_workouts.setItem(row, 4, QTableWidgetItem(level_map.get(p.training_level, p.training_level or "-")))
            self.table_workouts.setItem(row, 5, QTableWidgetItem(f"{ex_count} حرکت"))
            self.table_workouts.setItem(row, 6, QTableWidgetItem(f"{assignments_count} نفر"))

            for c in range(7):
                item = self.table_workouts.item(row, c)
                if item and c != 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Actions Widget
            action_w = QWidget()
            action_w.setStyleSheet("background: transparent;")
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 2, 4, 2)
            action_l.setSpacing(5)
            action_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_assign = QPushButton("🎯 تخصیص")
            btn_assign.setToolTip("تخصیص این الگو به یکی از شاگردان باشگاه")
            btn_assign.setFixedHeight(28)
            btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_assign.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            btn_assign.clicked.connect(lambda _, pid=p.id, ptitle=p.title: self.open_assign_dialog("workout", pid, ptitle))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setToolTip("بارگذاری در طراح تمرین جهت تغییر و ذخیره")
            btn_edit.setFixedHeight(28)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            btn_edit.clicked.connect(lambda _, pid=p.id: self.edit_workout_requested.emit(pid))

            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setToolTip("خروجی و چاپ فایل PDF این الگو")
            btn_pdf.setFixedHeight(28)
            btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pdf.setStyleSheet("background-color: #3B82F6; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            btn_pdf.clicked.connect(lambda _, plan=p: self.export_workout_pdf(plan))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف الگو از بانک")
            btn_del.setFixedSize(28, 28)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 4px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, pid=p.id, ptitle=p.title: self.delete_workout_template(pid, ptitle))

            action_l.addWidget(btn_assign)
            action_l.addWidget(btn_edit)
            action_l.addWidget(btn_pdf)
            action_l.addWidget(btn_del)
            self.table_workouts.setCellWidget(row, 7, action_w)

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

            self.table_nutrition.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table_nutrition.setItem(row, 1, QTableWidgetItem(p.title or "بدون عنوان"))
            self.table_nutrition.setItem(row, 2, QTableWidgetItem(goal_map.get(p.goal, p.goal or "-")))
            self.table_nutrition.setItem(row, 3, QTableWidgetItem(f"{int(p.target_calories or 0)} kcal"))
            self.table_nutrition.setItem(row, 4, QTableWidgetItem(macros_str))
            self.table_nutrition.setItem(row, 5, QTableWidgetItem(f"{meals_count} وعده"))
            self.table_nutrition.setItem(row, 6, QTableWidgetItem(f"{assignments_count} نفر"))

            for c in range(7):
                item = self.table_nutrition.item(row, c)
                if item and c != 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Actions Widget
            action_w = QWidget()
            action_w.setStyleSheet("background: transparent;")
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 2, 4, 2)
            action_l.setSpacing(5)
            action_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_assign = QPushButton("🎯 تخصیص")
            btn_assign.setToolTip("تخصیص این الگو به یکی از شاگردان باشگاه")
            btn_assign.setFixedHeight(28)
            btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_assign.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            btn_assign.clicked.connect(lambda _, pid=p.id, ptitle=p.title: self.open_assign_dialog("nutrition", pid, ptitle))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setToolTip("بارگذاری در طراح رژیم جهت تغییر و ذخیره")
            btn_edit.setFixedHeight(28)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            btn_edit.clicked.connect(lambda _, pid=p.id: self.edit_nutrition_requested.emit(pid))

            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setToolTip("خروجی و چاپ فایل PDF این الگو")
            btn_pdf.setFixedHeight(28)
            btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pdf.setStyleSheet("background-color: #3B82F6; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            btn_pdf.clicked.connect(lambda _, plan=p: self.export_nutrition_pdf(plan))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف الگو از بانک")
            btn_del.setFixedSize(28, 28)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 4px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, pid=p.id, ptitle=p.title: self.delete_nutrition_template(pid, ptitle))

            action_l.addWidget(btn_assign)
            action_l.addWidget(btn_edit)
            action_l.addWidget(btn_pdf)
            action_l.addWidget(btn_del)
            self.table_nutrition.setCellWidget(row, 7, action_w)

    def export_workout_pdf(self, plan):
        dummy_member = Member(full_name="نسخه عمومی الگو", membership_expire_shamsi="-")
        default_name = f"workout_template_{plan.id}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل PDF الگوی تمرینی", default_name, "PDF Files (*.pdf)")
        if filepath:
            PDFGenerator.generate_workout_pdf(dummy_member, plan, filepath)
            QMessageBox.information(self, "موفقیت", "فایل PDF الگوی تمرینی با موفقیت ایجاد شد.")

    def export_nutrition_pdf(self, plan):
        dummy_member = Member(full_name="نسخه عمومی الگو", membership_expire_shamsi="-")
        default_name = f"nutrition_template_{plan.id}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل PDF الگوی غذایی", default_name, "PDF Files (*.pdf)")
        if filepath:
            PDFGenerator.generate_nutrition_pdf(dummy_member, plan, filepath)
            QMessageBox.information(self, "موفقیت", "فایل PDF الگوی غذایی با موفقیت ایجاد شد.")

    def open_assign_dialog(self, template_type: str, template_id: int, template_title: str):
        dlg = AssignTemplateDialog(template_type, template_id, template_title, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_all_templates()

    def delete_workout_template(self, plan_id: int, plan_title: str):
        reply = QMessageBox.warning(
            self,
            "⚠️ تایید حذف الگوی تمرینی",
            f"آیا مطمئن هستید که می‌خواهید الگوی تمرینی «{plan_title}» را از بانک حذف کنید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                WorkoutService.delete_plan(plan_id)
                QMessageBox.information(self, "موفقیت", f"الگوی تمرینی «{plan_title}» حذف گردید.")
                self.load_workout_templates()
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف الگو: {str(e)}")

    def delete_nutrition_template(self, plan_id: int, plan_title: str):
        reply = QMessageBox.warning(
            self,
            "⚠️ تایید حذف الگوی غذایی",
            f"آیا مطمئن هستید که می‌خواهید الگوی غذایی «{plan_title}» را از بانک حذف کنید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                NutritionService.delete_nutrition_plan(plan_id)
                QMessageBox.information(self, "موفقیت", f"الگوی غذایی «{plan_title}» حذف گردید.")
                self.load_nutrition_templates()
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف الگو: {str(e)}")