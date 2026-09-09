from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QFrame, QMessageBox, QFileDialog, QDialog, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import pyqtSignal, Qt
from yalda.services.member_service import MemberService
from yalda.services.workout_service import WorkoutService
from yalda.services.nutrition_service import NutritionService
from yalda.views.health_record_view import HealthRecordView
from yalda.views.assessment_view import AssessmentView
from yalda.views.components.media_viewer_dialog import MediaViewerDialog
from yalda.pdf.pdf_generator import PDFGenerator
import os

class ViewWorkoutPlanDialog(QDialog):
    """Full detail view dialog for a Workout Plan showing days, exercises, sets, reps and media."""
    def __init__(self, plan, member, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.member = member
        self.setWindowTitle(f"📋 جزئیات برنامه تمرینی: {plan.title or 'بدون عنوان'}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(980, 620)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        goal_map = {
            "hypertrophy": "هایپرتروفی (عضله‌سازی)",
            "fat_loss": "چربی‌سوزی و کاهش وزن",
            "strength": "افزایش قدرت بی‌هوازی",
            "corrective": "حرکات اصلاحی و بهبود قامت",
            "general_fitness": "آمادگی جسمانی عمومی",
            "endurance": "استقامت عضلانی"
        }
        goal_fa = goal_map.get(self.plan.goal, self.plan.goal or "-")
        level_map = {"beginner": "مبتدی", "intermediate": "متوسط", "advanced": "پیشرفته"}
        level_fa = level_map.get(self.plan.training_level, self.plan.training_level or "-")

        card = QFrame()
        card.setObjectName("card")
        card_l = QHBoxLayout(card)
        card_l.setContentsMargins(15, 12, 15, 12)
        
        lbl_info = QLabel(
            f"<b>عنوان برنامه:</b> {self.plan.title}  |  "
            f"<b>هدف تمرین:</b> {goal_fa}  |  "
            f"<b>تعداد روزها:</b> {self.plan.days_per_week} روز در هفته  |  "
            f"<b>سطح تمرین:</b> {level_fa}"
        )
        lbl_info.setStyleSheet("color: #FFFFFF; font-size: 13px;")
        card_l.addWidget(lbl_info)
        layout.addWidget(card)

        table = QTableWidget()
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            "ردیف", "روز تمرین", "نام حرکت ورزشی", "ست", "تکرار", "وزنه پیشنهادی", "زمان استراحت", "ریتم", "آموزش تصویری"
        ])
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(0, 45)
        table.setColumnWidth(1, 195)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(3, 45)
        table.setColumnWidth(4, 65)
        table.setColumnWidth(5, 95)
        table.setColumnWidth(6, 85)
        table.setColumnWidth(7, 75)
        table.setColumnWidth(8, 100)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(42)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        rows = []
        for day in (self.plan.days or []):
            for we in (day.workout_exercises or []):
                rows.append((day.day_title, we))

        table.setRowCount(len(rows))
        for idx, (day_title, we) in enumerate(rows):
            ex_name = we.exercise.name_fa if we.exercise else "-"
            table.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
            table.setItem(idx, 1, QTableWidgetItem(day_title))
            table.setItem(idx, 2, QTableWidgetItem(ex_name))
            table.setItem(idx, 3, QTableWidgetItem(str(we.sets)))
            table.setItem(idx, 4, QTableWidgetItem(str(we.reps)))
            table.setItem(idx, 5, QTableWidgetItem(str(we.weight_suggestion or "-")))
            table.setItem(idx, 6, QTableWidgetItem(f"{we.rest_seconds} ثانیه"))
            notes = f"{we.tempo or ''} {we.trainer_notes or ''}".strip()
            table.setItem(idx, 7, QTableWidgetItem(notes or "-"))

            for c in (0, 1, 3, 4, 5, 6, 7):
                it = table.item(idx, c)
                if it: it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_media = QPushButton("🎬 عکس/فیلم")
            btn_media.setObjectName("secondary_button")
            btn_media.setStyleSheet("padding: 2px 6px; font-size: 11px; height: 28px;")
            if we.exercise and (we.exercise.media_path or we.exercise.video_url):
                btn_media.clicked.connect(lambda _, ex=we.exercise: self.show_media(ex))
            else:
                btn_media.setEnabled(False)
            table.setCellWidget(idx, 8, btn_media)

        layout.addWidget(table)

        btn_box = QHBoxLayout()
        btn_pdf = QPushButton("📄 صدور فایل PDF")
        btn_pdf.setFixedHeight(36)
        btn_pdf.clicked.connect(self.export_pdf)

        btn_close = QPushButton("بستن")
        btn_close.setObjectName("secondary_button")
        btn_close.setFixedHeight(36)
        btn_close.clicked.connect(self.accept)

        btn_box.addWidget(btn_pdf)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def show_media(self, exercise):
        dlg = MediaViewerDialog(
            title=exercise.name_fa,
            media_path=exercise.media_path,
            media_type=exercise.media_type,
            video_url=exercise.video_url,
            parent=self
        )
        dlg.exec()

    def export_pdf(self):
        default_name = f"workout_{self.member.last_name}_{self.plan.id}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل PDF برنامه تمرینی", default_name, "PDF Files (*.pdf)")
        if filepath:
            PDFGenerator.generate_workout_pdf(self.member, self.plan, filepath)
            QMessageBox.information(self, "موفقیت", "فایل PDF با موفقیت ذخیره شد.")


class ViewNutritionPlanDialog(QDialog):
    """Full detail view dialog for a Nutrition Plan showing meals, items, macros, and notes."""
    def __init__(self, plan, member, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.member = member
        self.setWindowTitle(f"🥗 جزئیات برنامه غذایی: {plan.title or 'بدون عنوان'}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(920, 620)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        nutrition_goals = {
            "muscle_gain": "عضله‌سازی (Muscle Gain)",
            "weight_loss": "کاهش وزن و چربی‌سوزی (Weight Loss)",
            "weight_gain": "افزایش وزن (Weight Gain)",
            "maintenance": "تثبیت وزن (Maintenance)"
        }
        goal_fa = nutrition_goals.get(self.plan.goal, self.plan.goal or "-")

        card = QFrame()
        card.setObjectName("card")
        card_l = QHBoxLayout(card)
        card_l.setContentsMargins(15, 12, 15, 12)

        macros_str = f"P: {int(self.plan.target_protein or 0)}g | C: {int(self.plan.target_carbs or 0)}g | F: {int(self.plan.target_fat or 0)}g"
        lbl_info = QLabel(
            f"<b>عنوان رژیم:</b> {self.plan.title}  |  "
            f"<b>هدف:</b> {goal_fa}  |  "
            f"<b>کالری کل روزانه:</b> {int(self.plan.target_calories or 0)} kcal  |  "
            f"<b>درشت‌مغذی‌ها:</b> {macros_str}"
        )
        lbl_info.setStyleSheet("color: #FFFFFF; font-size: 13px;")
        card_l.addWidget(lbl_info)
        layout.addWidget(card)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "ردیف", "نام وعده غذایی", "نام ماده غذایی", "مقدار / واحد", "توضیحات مربی"
        ])
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(0, 45)
        table.setColumnWidth(1, 140)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(3, 140)
        table.setColumnWidth(4, 220)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(42)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        meal_names_map = {
            "breakfast": "صبحانه", "morning_snack": "میان‌وعده صبح", "lunch": "ناهار",
            "afternoon_snack": "عصرانه", "dinner": "شام", "evening_snack": "قبل از خواب"
        }

        rows = []
        for meal in (self.plan.meals or []):
            m_fa = meal_names_map.get(meal.meal_name, meal.meal_name)
            for item in (meal.items or []):
                rows.append((m_fa, item))

        table.setRowCount(len(rows))
        for idx, (m_fa, item) in enumerate(rows):
            f_name = item.food.name_fa if item.food else "-"
            table.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
            table.setItem(idx, 1, QTableWidgetItem(m_fa))
            table.setItem(idx, 2, QTableWidgetItem(f_name))
            table.setItem(idx, 3, QTableWidgetItem(f"{item.amount} {item.unit or (item.food.unit if item.food else '')}"))
            table.setItem(idx, 4, QTableWidgetItem(item.notes or "-"))

            for c in (0, 1, 3):
                it = table.item(idx, c)
                if it: it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(table)

        btn_box = QHBoxLayout()
        btn_pdf = QPushButton("📄 صدور فایل PDF")
        btn_pdf.setFixedHeight(36)
        btn_pdf.clicked.connect(self.export_pdf)

        btn_close = QPushButton("بستن")
        btn_close.setObjectName("secondary_button")
        btn_close.setFixedHeight(36)
        btn_close.clicked.connect(self.accept)

        btn_box.addWidget(btn_pdf)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def export_pdf(self):
        default_name = f"nutrition_{self.member.last_name}_{self.plan.id}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل PDF برنامه غذایی", default_name, "PDF Files (*.pdf)")
        if filepath:
            PDFGenerator.generate_nutrition_pdf(self.member, self.plan, filepath)
            QMessageBox.information(self, "موفقیت", "فایل PDF با موفقیت ذخیره شد.")


class MemberDetailView(QWidget):
    back_requested = pyqtSignal()
    edit_workout_requested = pyqtSignal(int, int)
    edit_nutrition_requested = pyqtSignal(int, int)
    create_workout_requested = pyqtSignal(int)
    create_nutrition_requested = pyqtSignal(int)

    def __init__(self, member_id: int, parent=None):
        super().__init__(parent)
        self.member_id = member_id
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title and Actions
        header = QHBoxLayout()
        self.lbl_title = QLabel("پرونده جامع ورزشکار")
        self.lbl_title.setObjectName("h1")

        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.clicked.connect(self.back_requested.emit)

        btn_edit = QPushButton("ویرایش مشخصات ✏️")
        btn_edit.clicked.connect(self.open_edit_dialog)

        header.addWidget(btn_back)
        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(btn_edit)
        layout.addLayout(header)

        # Member Info Card
        info_card = QFrame()
        info_card.setObjectName("card")
        info_card_layout = QHBoxLayout(info_card)
        info_card_layout.setContentsMargins(15, 15, 15, 15)

        # Avatar Column
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(100, 100)
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_avatar.setStyleSheet("border-radius: 50px; background-color: #2E2E2E; font-size: 40px;")
        info_card_layout.addWidget(self.lbl_avatar)

        # Details Column
        self.lbl_member_details = QLabel()
        self.lbl_member_details.setStyleSheet("font-size: 13px; line-height: 1.6;")
        info_card_layout.addWidget(self.lbl_member_details, 1)

        layout.addWidget(info_card)

        # Tab Widget for Comprehensive History
        self.tabs = QTabWidget()

        # Tab 1: Health & Assessment
        self.view_health = HealthRecordView(self.member_id)
        self.tabs.addTab(self.view_health, "📋 سوابق پزشکی و آسیب‌دیدگی")

        # Tab 2: Physical Assessments
        self.view_assessment = AssessmentView(self.member_id)
        self.tabs.addTab(self.view_assessment, "📊 ارزیابی فیزیکی و سایز")

        # Tab 3: Workout Plans Archive
        self.tab_workout = QWidget()
        self.init_workout_tab()
        self.tabs.addTab(self.tab_workout, "🏋️ بایگانی برنامه‌های تمرینی")

        # Tab 4: Nutrition Plans Archive
        self.tab_nutrition = QWidget()
        self.init_nutrition_tab()
        self.tabs.addTab(self.tab_nutrition, "🥗 بایگانی برنامه‌های غذایی")

        layout.addWidget(self.tabs)
        self.load_member_info()

    def open_edit_dialog(self):
        try:
            from yalda.views.member_form_dialog import MemberFormDialog
            member = MemberService.get_member_by_id(self.member_id)
            if member:
                dlg = MemberFormDialog(self, member_data=member)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self.load_member_info()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطایی رخ داد: {str(e)}")

    def load_member_info(self):
        member = MemberService.get_member_by_id(self.member_id)
        if member:
            self.lbl_title.setText(f"پرونده جامع: {member.full_name}")
            from yalda.utils.bmi_calculator import calculate_bmi_info
            bmi, cat, color = calculate_bmi_info(member.height_cm, member.initial_weight_kg)
            bmi_str = f"<font color='{color}'><b>{bmi}</b> ({cat})</font>" if bmi > 0 else "-"
            reg_str = member.registration_date_shamsi if hasattr(member, 'registration_date_shamsi') and member.registration_date_shamsi else "-"
            ins_str = member.insurance_date_shamsi if hasattr(member, 'insurance_date_shamsi') and member.insurance_date_shamsi else "-"
            fee_str = f"{int(member.tuition_fee):,} تومان" if hasattr(member, 'tuition_fee') and member.tuition_fee else "-"
            h_text = f"{int(member.height_cm)}cm" if member.height_cm else "-"
            w_text = f"{int(member.initial_weight_kg)}kg" if member.initial_weight_kg else "-"
            hw_display = "-" if (not member.height_cm and not member.initial_weight_kg) else f"{h_text} / {w_text}"

            info_str = f"<b>کد عضویت:</b> {member.id}  |  <b>تلفن:</b> {member.phone}  |  <b>ثبت نام:</b> {reg_str}  |  <b>بیمه:</b> {ins_str}  |  <b>شهریه:</b> {fee_str}<br><b>قد/وزن:</b> {hw_display}  |  <b>شاخص BMI:</b> {bmi_str}  |  <b>تاریخ انقضا:</b> <font color='#8B0000'>{member.membership_expire_shamsi}</font>"
            self.lbl_member_details.setText(info_str)

            if member.photo_path and os.path.exists(member.photo_path):
                pixmap = QPixmap(member.photo_path)
                if not pixmap.isNull():
                    from yalda.utils.image_utils import get_circular_pixmap
                    circ_pix = get_circular_pixmap(pixmap, 100)
                    self.lbl_avatar.setPixmap(circ_pix)
                    self.lbl_avatar.setStyleSheet("border: none; background: transparent;")
                else:
                    self.lbl_avatar.setText("👤")
                    self.lbl_avatar.setStyleSheet("font-size: 50px; background-color: #2E2E2E; border-radius: 50px;")
            else:
                self.lbl_avatar.setText("👤")
                self.lbl_avatar.setStyleSheet("font-size: 50px; background-color: #2E2E2E; border-radius: 50px;")

    def init_workout_tab(self):
        layout = QVBoxLayout(self.tab_workout)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Header Row
        top_box = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("🏋️ بایگانی و تاریخچه برنامه‌های تمرینی ورزشکار")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        lbl_sub = QLabel("مشاهده جزئیات، ویرایش، صدور PDF و حذف برنامه‌های تمرینی به ترتیب تاریخ تخصیص")
        lbl_sub.setStyleSheet("font-size: 12px; color: #888888;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)

        btn_assign_new = QPushButton("➕ تخصیص برنامه تمرینی")
        btn_assign_new.setFixedHeight(36)
        btn_assign_new.clicked.connect(lambda: self.create_workout_requested.emit(self.member_id))

        top_box.addLayout(title_box)
        top_box.addStretch()
        top_box.addWidget(btn_assign_new)
        layout.addLayout(top_box)

        # Table & Empty Label
        self.table_workout = QTableWidget()
        self.table_workout.setColumnCount(8)
        self.table_workout.setHorizontalHeaderLabels([
            "ردیف", "عنوان برنامه تمرینی", "هدف برنامه", "روزهای تمرین", "سطح تمرین", "تاریخ تخصیص", "وضعیت", "عملیات"
        ])
        header = self.table_workout.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_workout.setColumnWidth(0, 45)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_workout.setColumnWidth(2, 160)
        self.table_workout.setColumnWidth(3, 85)
        self.table_workout.setColumnWidth(4, 85)
        self.table_workout.setColumnWidth(5, 100)
        self.table_workout.setColumnWidth(6, 120)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table_workout.setColumnWidth(7, 280)
        self.table_workout.verticalHeader().setVisible(False)
        self.table_workout.verticalHeader().setDefaultSectionSize(52)
        self.table_workout.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_workout.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table_workout)

        self.lbl_no_workout = QLabel("هیچ برنامه تمرینی در تاریخچه این ورزشکار ثبت نشده است.")
        self.lbl_no_workout.setStyleSheet("color: #888888; font-size: 14px; padding: 30px;")
        self.lbl_no_workout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_workout.setVisible(False)
        layout.addWidget(self.lbl_no_workout)

        self.load_workout_archive()

    def load_workout_archive(self):
        assignments = WorkoutService.get_member_assignments(self.member_id)
        if not assignments:
            self.table_workout.setRowCount(0)
            self.table_workout.setVisible(False)
            self.lbl_no_workout.setVisible(True)
            return

        self.lbl_no_workout.setVisible(False)
        self.table_workout.setVisible(True)
        self.table_workout.setRowCount(len(assignments))

        goal_map = {
            "hypertrophy": "هایپرتروفی (عضله‌سازی)",
            "fat_loss": "چربی‌سوزی و کاهش وزن",
            "strength": "افزایش قدرت بی‌هوازی",
            "corrective": "حرکات اصلاحی و بهبود قامت",
            "general_fitness": "آمادگی جسمانی عمومی",
            "endurance": "استقامت عضلانی"
        }
        level_map = {"beginner": "مبتدی", "intermediate": "متوسط", "advanced": "پیشرفته"}

        for row, asgn in enumerate(assignments):
            p = asgn.plan
            plan_title = p.title if p else "بدون عنوان"
            goal_fa = goal_map.get(p.goal, p.goal or "-") if p else "-"
            days_fa = f"{p.days_per_week} روزه" if p else "-"
            level_fa = level_map.get(p.training_level, p.training_level or "-") if p else "-"
            date_fa = asgn.assigned_date_shamsi or "-"
            status_fa = "🟢 فعال (جاری)" if asgn.is_active else "⚪ بایگانی (سابق)"

            self.table_workout.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table_workout.setItem(row, 1, QTableWidgetItem(plan_title))
            self.table_workout.setItem(row, 2, QTableWidgetItem(goal_fa))
            self.table_workout.setItem(row, 3, QTableWidgetItem(days_fa))
            self.table_workout.setItem(row, 4, QTableWidgetItem(level_fa))
            self.table_workout.setItem(row, 5, QTableWidgetItem(date_fa))
            self.table_workout.setItem(row, 6, QTableWidgetItem(status_fa))

            for c in (0, 2, 3, 4, 5, 6):
                it = self.table_workout.item(row, c)
                if it: it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            action_w = QWidget()
            action_w.setStyleSheet("background: transparent;")
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 2, 4, 2)
            action_l.setSpacing(5)
            action_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_view = QPushButton("👁️ مشاهده")
            btn_view.setToolTip("مشاهده کامل جدول برنامه تمرینی")
            btn_view.setFixedHeight(28)
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            if p:
                btn_view.clicked.connect(lambda _, pl=p: self.view_workout_plan(pl))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setToolTip("باز کردن در طراح برنامه تمرینی جهت ویرایش")
            btn_edit.setFixedHeight(28)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            if p:
                btn_edit.clicked.connect(lambda _, pid=p.id, mid=self.member_id: self.edit_workout_requested.emit(pid, mid))

            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setToolTip("صدور فایل PDF برای چاپ")
            btn_pdf.setFixedHeight(28)
            btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pdf.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            if p:
                btn_pdf.clicked.connect(lambda _, pl=p: self.export_workout_pdf(pl))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف این برنامه از بایگانی ورزشکار")
            btn_del.setFixedSize(28, 28)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 4px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, aid=asgn.id, ptitle=plan_title: self.delete_workout_plan(aid, ptitle))

            action_l.addWidget(btn_view)
            action_l.addWidget(btn_edit)
            action_l.addWidget(btn_pdf)
            action_l.addWidget(btn_del)
            self.table_workout.setCellWidget(row, 7, action_w)

    def init_nutrition_tab(self):
        layout = QVBoxLayout(self.tab_nutrition)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Header Row
        top_box = QHBoxLayout()
        title = QLabel("🥗 تاریخچه و بایگانی برنامه‌های غذایی")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        subtitle = QLabel("مشاهده جزئیات، ویرایش، صدور PDF و حذف برنامه‌های غذایی به ترتیب تاریخ تخصیص")
        subtitle.setStyleSheet("color: #AAAAAA; font-size: 12px;")

        top_info = QVBoxLayout()
        top_info.setSpacing(4)
        top_info.addWidget(title)
        top_info.addWidget(subtitle)
        top_box.addLayout(top_info)
        top_box.addStretch()

        btn_assign = QPushButton("🥗 تخصیص برنامه غذایی جدید")
        btn_assign.setFixedHeight(36)
        btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_assign.clicked.connect(lambda: self.create_nutrition_requested.emit(self.member_id))
        top_box.addWidget(btn_assign)
        layout.addLayout(top_box)

        # Nutrition Plans Table
        self.table_nutrition = QTableWidget()
        self.table_nutrition.setColumnCount(8)
        self.table_nutrition.setHorizontalHeaderLabels([
            "ردیف", "عنوان برنامه غذایی", "هدف رژیم", "کالری هدف", "درشت‌مغذی‌ها (P/C/F)", "تاریخ تخصیص", "وضعیت", "عملیات"
        ])
        header = self.table_nutrition.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_nutrition.setColumnWidth(0, 45)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_nutrition.setColumnWidth(2, 160)
        self.table_nutrition.setColumnWidth(3, 90)
        self.table_nutrition.setColumnWidth(4, 150)
        self.table_nutrition.setColumnWidth(5, 100)
        self.table_nutrition.setColumnWidth(6, 120)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table_nutrition.setColumnWidth(7, 280)
        self.table_nutrition.verticalHeader().setVisible(False)
        self.table_nutrition.verticalHeader().setDefaultSectionSize(52)
        self.table_nutrition.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_nutrition.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table_nutrition)

        self.lbl_no_nutrition = QLabel("هیچ برنامه غذایی در تاریخچه این ورزشکار ثبت نشده است.")
        self.lbl_no_nutrition.setStyleSheet("color: #888888; font-size: 14px; padding: 30px;")
        self.lbl_no_nutrition.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_nutrition.setVisible(False)
        layout.addWidget(self.lbl_no_nutrition)

        self.load_nutrition_archive()

    def load_nutrition_archive(self):
        assignments = NutritionService.get_member_assignments(self.member_id)
        if not assignments:
            self.table_nutrition.setRowCount(0)
            self.table_nutrition.setVisible(False)
            self.lbl_no_nutrition.setVisible(True)
            return

        self.lbl_no_nutrition.setVisible(False)
        self.table_nutrition.setVisible(True)
        self.table_nutrition.setRowCount(len(assignments))

        nutrition_goals = {
            "muscle_gain": "عضله‌سازی (Muscle Gain)",
            "weight_loss": "کاهش وزن و چربی‌سوزی (Weight Loss)",
            "weight_gain": "افزایش وزن (Weight Gain)",
            "maintenance": "تثبیت وزن (Maintenance)"
        }

        for row, asgn in enumerate(assignments):
            p = asgn.plan
            plan_title = p.title if p else "بدون عنوان"
            goal_fa = nutrition_goals.get(p.goal, p.goal or "-") if p else "-"
            cal_fa = f"{int(p.target_calories or 0)} kcal" if p else "-"
            macros_fa = f"P:{int(p.target_protein or 0)}g | C:{int(p.target_carbs or 0)}g | F:{int(p.target_fat or 0)}g" if p else "-"
            date_fa = asgn.assigned_date_shamsi or "-"
            status_fa = "🟢 فعال (جاری)" if asgn.is_active else "⚪ بایگانی (سابق)"

            self.table_nutrition.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table_nutrition.setItem(row, 1, QTableWidgetItem(plan_title))
            self.table_nutrition.setItem(row, 2, QTableWidgetItem(goal_fa))
            self.table_nutrition.setItem(row, 3, QTableWidgetItem(cal_fa))
            self.table_nutrition.setItem(row, 4, QTableWidgetItem(macros_fa))
            self.table_nutrition.setItem(row, 5, QTableWidgetItem(date_fa))
            self.table_nutrition.setItem(row, 6, QTableWidgetItem(status_fa))

            for c in (0, 2, 3, 4, 5, 6):
                it = self.table_nutrition.item(row, c)
                if it: it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            action_w = QWidget()
            action_w.setStyleSheet("background: transparent;")
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 2, 4, 2)
            action_l.setSpacing(5)
            action_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_view = QPushButton("👁️ مشاهده")
            btn_view.setToolTip("مشاهده کامل جدول برنامه غذایی")
            btn_view.setFixedHeight(28)
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            if p:
                btn_view.clicked.connect(lambda _, pl=p: self.view_nutrition_plan(pl))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setToolTip("باز کردن در طراح برنامه غذایی جهت ویرایش")
            btn_edit.setFixedHeight(28)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            if p:
                btn_edit.clicked.connect(lambda _, pid=p.id, mid=self.member_id: self.edit_nutrition_requested.emit(pid, mid))

            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setToolTip("صدور فایل PDF برای چاپ")
            btn_pdf.setFixedHeight(28)
            btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pdf.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
            if p:
                btn_pdf.clicked.connect(lambda _, pl=p: self.export_nutrition_pdf(pl))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف این برنامه از بایگانی ورزشکار")
            btn_del.setFixedSize(28, 28)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 4px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, aid=asgn.id, ptitle=plan_title: self.delete_nutrition_plan(aid, ptitle))

            action_l.addWidget(btn_view)
            action_l.addWidget(btn_edit)
            action_l.addWidget(btn_pdf)
            action_l.addWidget(btn_del)
            self.table_nutrition.setCellWidget(row, 7, action_w)

    def view_workout_plan(self, plan):
        member = MemberService.get_member_by_id(self.member_id)
        fresh_plan = WorkoutService.get_plan_by_id(plan.id) if hasattr(plan, 'id') and plan.id else plan
        dlg = ViewWorkoutPlanDialog(fresh_plan, member, parent=self)
        dlg.exec()

    def view_nutrition_plan(self, plan):
        member = MemberService.get_member_by_id(self.member_id)
        fresh_plan = NutritionService.get_plan_by_id(plan.id) if hasattr(plan, 'id') and plan.id else plan
        dlg = ViewNutritionPlanDialog(fresh_plan, member, parent=self)
        dlg.exec()

    def delete_workout_plan(self, assignment_id: int, plan_title: str):
        reply = QMessageBox.warning(
            self, "⚠️ تایید حذف برنامه تمرینی",
            f"آیا از حذف برنامه تمرینی «{plan_title}» از بایگانی این ورزشکار اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            WorkoutService.delete_workout_assignment(assignment_id)
            self.load_workout_archive()
            QMessageBox.information(self, "موفقیت", f"برنامه تمرینی «{plan_title}» با موفقیت از بایگانی ورزشکار حذف گردید.")

    def delete_nutrition_plan(self, assignment_id: int, plan_title: str):
        reply = QMessageBox.warning(
            self, "⚠️ تایید حذف برنامه غذایی",
            f"آیا از حذف برنامه غذایی «{plan_title}» از بایگانی این ورزشکار اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            NutritionService.delete_nutrition_assignment(assignment_id)
            self.load_nutrition_archive()
            QMessageBox.information(self, "موفقیت", f"برنامه غذایی «{plan_title}» با موفقیت از بایگانی ورزشکار حذف گردید.")

    def export_workout_pdf(self, plan):
        member = MemberService.get_member_by_id(self.member_id)
        default_name = f"workout_{member.last_name}_{plan.id}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل PDF برنامه تمرینی", default_name, "PDF Files (*.pdf)")
        if filepath:
            PDFGenerator.generate_workout_pdf(member, plan, filepath)
            QMessageBox.information(self, "موفقیت", "فایل PDF برنامه تمرینی با موفقیت ایجاد شد.")

    def export_nutrition_pdf(self, plan):
        member = MemberService.get_member_by_id(self.member_id)
        default_name = f"nutrition_{member.last_name}_{plan.id}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل PDF برنامه غذایی", default_name, "PDF Files (*.pdf)")
        if filepath:
            PDFGenerator.generate_nutrition_pdf(member, plan, filepath)
            QMessageBox.information(self, "موفقیت", "فایل PDF برنامه غذایی با موفقیت ایجاد شد.")
