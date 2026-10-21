from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QFrame, QMessageBox, QFileDialog, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QTextEdit, QSizePolicy
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import pyqtSignal, Qt
from nemov.services.member_service import MemberService
from nemov.services.workout_service import WorkoutService
from nemov.services.nutrition_service import NutritionService
from nemov.views.health_record_view import HealthRecordView
from nemov.views.assessment_view import AssessmentView
from nemov.views.components.media_viewer_dialog import MediaViewerDialog
from nemov.views.components.undo_delete_banner import UndoDeleteBanner
from nemov.pdf.pdf_generator import PDFGenerator
import os
import re
from nemov.utils.jalali_date import get_now_shamsi_for_filename

class ViewWorkoutPlanDialog(QDialog):
    """Full detail view dialog for a Workout Plan showing days, exercises, sets, reps and media."""
    def __init__(self, plan, member, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.member = member
        self.setWindowTitle(f"📋 جزئیات برنامه تمرینی: {plan.title or 'بدون عنوان'}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(1020, 640)
        self.init_ui()

    def show_notes_dialog(self, exercise_name: str, notes: str):
        """Displays a clean modal dialog with the full trainer notes."""
        dlg = QDialog(self)
        dlg.setWindowTitle("📝 توضیحات مربی")
        dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dlg.setFixedWidth(460)

        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(20, 20, 20, 20)
        dlg_layout.setSpacing(14)

        lbl_title = QLabel(f"<b>نام حرکت:</b> {exercise_name}")
        lbl_title.setStyleSheet("font-size: 14px; color: #FFFFFF;")
        dlg_layout.addWidget(lbl_title)

        txt_notes = QTextEdit()
        txt_notes.setReadOnly(True)
        txt_notes.setText(notes)
        txt_notes.setStyleSheet(
            "background-color: #1A202C; color: #E2E8F0; font-size: 13px; "
            "border: 1px solid #4A5568; border-radius: 6px; padding: 10px; line-height: 1.6;"
        )
        txt_notes.setFixedHeight(160)
        dlg_layout.addWidget(txt_notes)

        btn_close = QPushButton("بستن")
        btn_close.setObjectName("secondary_button")
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(dlg.accept)
        dlg_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignLeft)

        dlg.exec()

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

        # Tabs organized by workout days
        tabs = QTabWidget()
        tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        days = self.plan.days or []
        if not days:
            table = QTableWidget()
            table.setColumnCount(9)
            table.setHorizontalHeaderLabels([
                "ردیف", "نام حرکت ورزشی", "ست", "تکرار", "وزنه پیشنهادی", "زمان استراحت", "ریتم", "توضیحات مربی", "آموزش تصویری"
            ])
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            table.setColumnWidth(0, 45)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.setColumnWidth(2, 50)
            table.setColumnWidth(3, 65)
            table.setColumnWidth(4, 90)
            table.setColumnWidth(5, 90)
            table.setColumnWidth(6, 80)
            table.setColumnWidth(7, 90)
            table.setColumnWidth(8, 100)
            table.verticalHeader().setVisible(False)
            table.setRowCount(0)
            tabs.addTab(table, "📅 روزهای تمرین")
        else:
            for day_idx, day in enumerate(days):
                tab_page = QWidget()
                page_layout = QVBoxLayout(tab_page)
                page_layout.setContentsMargins(0, 8, 0, 0)
                page_layout.setSpacing(0)

                table = QTableWidget()
                table.setColumnCount(9)
                table.setHorizontalHeaderLabels([
                    "ردیف", "نام حرکت ورزشی", "ست", "تکرار", "وزنه پیشنهادی", "زمان استراحت", "ریتم", "توضیحات مربی", "آموزش تصویری"
                ])
                header = table.horizontalHeader()
                header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                table.setColumnWidth(0, 45)   # ردیف
                header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # نام حرکت ورزشی (فوق‌العاده عریض و بدون کوتاه‌سازی)
                table.setColumnWidth(2, 50)   # ست
                table.setColumnWidth(3, 65)   # تکرار
                table.setColumnWidth(4, 90)   # وزنه پیشنهادی
                table.setColumnWidth(5, 90)   # زمان استراحت
                table.setColumnWidth(6, 80)   # ریتم
                table.setColumnWidth(7, 90)   # توضیحات مربی (دکمه پاپ‌آپ شکیل)
                table.setColumnWidth(8, 100)  # آموزش تصویری
                table.verticalHeader().setVisible(False)
                table.verticalHeader().setDefaultSectionSize(44)
                table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

                exercises = day.workout_exercises or []
                table.setRowCount(len(exercises))
                for idx, we in enumerate(exercises):
                    ex_name = (we.exercise.name_fa if we.exercise else None) or getattr(we, "custom_exercise_name", None) or "-"
                    table.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))

                    item_name = QTableWidgetItem(ex_name)
                    item_name.setToolTip(ex_name)
                    table.setItem(idx, 1, item_name)

                    table.setItem(idx, 2, QTableWidgetItem(str(we.sets)))
                    table.setItem(idx, 3, QTableWidgetItem(str(we.reps)))
                    table.setItem(idx, 4, QTableWidgetItem(str(we.weight_suggestion or "-")))
                    table.setItem(idx, 5, QTableWidgetItem(f"{we.rest_seconds} ثانیه"))
                    table.setItem(idx, 6, QTableWidgetItem(we.tempo or "-"))

                    for c in (0, 2, 3, 4, 5, 6):
                        it = table.item(idx, c)
                        if it: it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # توضیحات مربی (راهکار ۱: دکمه پاپ‌آپ و تول‌تیپ تعاملی)
                    raw_notes = we.trainer_notes if (we.trainer_notes and we.trainer_notes.strip()) else (
                        we.exercise.description if (we.exercise and we.exercise.description and we.exercise.description.strip()) else ""
                    )
                    if raw_notes and raw_notes.strip() and raw_notes.strip() != "-":
                        btn_notes = QPushButton("📝 مشاهده")
                        btn_notes.setObjectName("secondary_button")
                        btn_notes.setStyleSheet("padding: 2px 8px; font-size: 11px; height: 28px;")
                        btn_notes.setToolTip(raw_notes.strip())
                        btn_notes.clicked.connect(lambda _, n=raw_notes.strip(), name=ex_name: self.show_notes_dialog(name, n))
                        table.setCellWidget(idx, 7, btn_notes)
                    else:
                        item_dash = QTableWidgetItem("-")
                        item_dash.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        table.setItem(idx, 7, item_dash)

                    # آموزش تصویری
                    btn_media = QPushButton("🎬 عکس/فیلم")
                    btn_media.setObjectName("secondary_button")
                    btn_media.setStyleSheet("padding: 2px 6px; font-size: 11px; height: 28px;")
                    if we.exercise and (we.exercise.media_path or we.exercise.video_url or we.exercise.video_cloud_url):
                        btn_media.clicked.connect(lambda _, ex=we.exercise: self.show_media(ex))
                    else:
                        btn_media.setEnabled(False)
                    table.setCellWidget(idx, 8, btn_media)

                page_layout.addWidget(table)
                tab_title = f"📅 {day.day_title or f'روز {day.day_number}'}"
                tabs.addTab(tab_page, tab_title)

        layout.addWidget(tabs)

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
        target_video = exercise.video_cloud_url or exercise.video_url
        dlg = MediaViewerDialog(
            title=exercise.name_fa,
            media_path=exercise.media_path,
            media_type=exercise.media_type,
            video_url=target_video,
            parent=self
        )
        dlg.exec()

    def export_pdf(self):
        try:
            athlete_name = (self.member.full_name or f"{self.member.first_name} {self.member.last_name}").strip() if self.member else "ورزشکار"
            athlete_name = re.sub(r'[\\/*?:"<>|]', '', athlete_name).strip() or "ورزشکار"
            now_str = get_now_shamsi_for_filename()
            default_name = f"برنامه تمرینی {athlete_name}_{now_str}.pdf"
            parent_win = self.window() or self
            from nemov.utils.export_utils import resolve_athlete_export_path
            filepath, athlete_clean_name = resolve_athlete_export_path(
                self.member, default_name, parent_win, "ذخیره فایل PDF برنامه تمرینی"
            )
            if filepath:
                PDFGenerator.generate_workout_pdf(self.member, self.plan, filepath)
                QMessageBox.information(
                    self,
                    "موفقیت",
                    f"فایل PDF برنامه تمرینی با موفقیت در پوشه اختصاصی «{athlete_clean_name}» ذخیره شد:\n\n{filepath}"
                )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from nemov.utils.logger import log_error
            from nemov.views.components.error_dialog import show_error_dialog
            log_error(f"Error exporting workout PDF in ViewWorkoutPlanDialog: {e}\n{tb}")
            show_error_dialog(
                parent=self.window() or self,
                message="متاسفانه در حین ایجاد فایل PDF برنامه تمرینی خطایی رخ داد.",
                technical_details=tb,
                title="خطا در صدور PDF"
            )


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
        table.setColumnWidth(1, 220)
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
            f_name = (item.food.name_fa if item.food else None) or getattr(item, "custom_food_name", None) or "-"
            table.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))

            it_meal = QTableWidgetItem(m_fa)
            it_meal.setToolTip(m_fa)
            table.setItem(idx, 1, it_meal)

            it_food = QTableWidgetItem(f_name)
            it_food.setToolTip(f_name)
            table.setItem(idx, 2, it_food)

            table.setItem(idx, 3, QTableWidgetItem(f"{item.amount} {item.unit or (item.food.unit if item.food else '')}"))

            it_notes = QTableWidgetItem(item.notes or "-")
            if item.notes:
                it_notes.setToolTip(item.notes)
            table.setItem(idx, 4, it_notes)

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
        try:
            athlete_name = (self.member.full_name or f"{self.member.first_name} {self.member.last_name}").strip() if self.member else "ورزشکار"
            athlete_name = re.sub(r'[\\/*?:"<>|]', '', athlete_name).strip() or "ورزشکار"
            now_str = get_now_shamsi_for_filename()
            default_name = f"برنامه غذایی {athlete_name}_{now_str}.pdf"
            parent_win = self.window() or self
            from nemov.utils.export_utils import resolve_athlete_export_path
            filepath, athlete_clean_name = resolve_athlete_export_path(
                self.member, default_name, parent_win, "ذخیره فایل PDF برنامه غذایی"
            )
            if filepath:
                PDFGenerator.generate_nutrition_pdf(self.member, self.plan, filepath)
                QMessageBox.information(
                    self,
                    "موفقیت",
                    f"فایل PDF برنامه غذایی با موفقیت در پوشه اختصاصی «{athlete_clean_name}» ذخیره شد:\n\n{filepath}"
                )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from nemov.utils.logger import log_error
            from nemov.views.components.error_dialog import show_error_dialog
            log_error(f"Error exporting nutrition PDF in ViewNutritionPlanDialog: {e}\n{tb}")
            show_error_dialog(
                parent=self.window() or self,
                message="متاسفانه در حین ایجاد فایل PDF برنامه غذایی خطایی رخ داد.",
                technical_details=tb,
                title="خطا در صدور PDF"
            )


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

        btn_edit = QPushButton("✏️ ویرایش مشخصات")
        btn_edit.setFixedHeight(34)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #D97706;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #B45309;
            }
        """)
        btn_edit.clicked.connect(self.open_edit_dialog)

        header.addWidget(btn_back)
        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(btn_edit)
        layout.addLayout(header)

        # Member Info Card
        info_card = QFrame()
        info_card.setObjectName("card")
        info_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
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

        layout.addWidget(self.tabs, 1)
        self.load_member_info()

    def open_edit_dialog(self):
        try:
            from nemov.views.member_form_dialog import MemberFormDialog
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
            from nemov.utils.bmr_calculator import calculate_bmr_tdee, calculate_age_from_shamsi
            age = calculate_age_from_shamsi(member.birth_date_shamsi)
            act_level = getattr(member, 'activity_level', None) or 'moderately_active'
            bmr, tdee, pal, act_title, color = calculate_bmr_tdee(
                member.height_cm, member.initial_weight_kg, age, member.gender, act_level
            )
            bmr_tdee_str = (
                f"<font color='{color}'><b>BMR: {bmr:,}</b> | <b>کالری روزانه (TDEE): {tdee:,} کالری</b> ({act_title})</font>"
                if bmr > 0 else "-"
            )
            reg_str = member.registration_date_shamsi if hasattr(member, 'registration_date_shamsi') and member.registration_date_shamsi else "-"
            ins_str = member.insurance_date_shamsi if hasattr(member, 'insurance_date_shamsi') and member.insurance_date_shamsi else "-"
            fee_str = f"{int(member.tuition_fee):,} تومان" if hasattr(member, 'tuition_fee') and member.tuition_fee else "-"
            h_text = f"{int(member.height_cm)}cm" if member.height_cm else "-"
            w_text = f"{int(member.initial_weight_kg)}kg" if member.initial_weight_kg else "-"
            hw_display = "-" if (not member.height_cm and not member.initial_weight_kg) else f"{h_text} / {w_text}"

            info_str = f"<b>کد عضویت:</b> {member.id}  |  <b>تلفن:</b> {member.phone}  |  <b>ثبت نام:</b> {reg_str}  |  <b>بیمه:</b> {ins_str}  |  <b>شهریه:</b> {fee_str}<br><b>قد/وزن:</b> {hw_display}  |  <b>متابولیسم و کالری:</b> {bmr_tdee_str}  |  <b>تاریخ انقضا:</b> <font color='#EF4444'><b>{member.membership_expire_shamsi or '-'}</b></font>"
            self.lbl_member_details.setText(info_str)

            if member.photo_path and os.path.exists(member.photo_path):
                pixmap = QPixmap(member.photo_path)
                if not pixmap.isNull():
                    from nemov.utils.image_utils import get_circular_pixmap
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
        top_box.setSpacing(12)
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        lbl_title = QLabel("🏋️ بایگانی و تاریخچه برنامه‌های تمرینی ورزشکار")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        lbl_sub = QLabel("مشاهده جزئیات، ویرایش، صدور PDF و حذف برنامه‌های تمرینی به ترتیب تاریخ تخصیص")
        lbl_sub.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        top_box.addLayout(title_box)
        top_box.addStretch()

        self.chk_select_all_workout = QCheckBox("انتخاب همه")
        self.chk_select_all_workout.setFixedWidth(120)
        self.chk_select_all_workout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_select_all_workout.toggled.connect(self.toggle_select_all_workout)

        self.btn_bulk_delete_workout = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete_workout.setEnabled(False)
        self.btn_bulk_delete_workout.setFixedSize(190, 36)
        self.btn_bulk_delete_workout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bulk_delete_workout.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
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
        self.btn_bulk_delete_workout.clicked.connect(self.bulk_delete_workout_plans)

        btn_assign_new = QPushButton("➕ تخصیص برنامه تمرینی")
        btn_assign_new.setFixedSize(190, 36)
        btn_assign_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_assign_new.clicked.connect(lambda: self.create_workout_requested.emit(self.member_id))

        top_box.addWidget(self.chk_select_all_workout)
        top_box.addWidget(self.btn_bulk_delete_workout)
        top_box.addWidget(btn_assign_new)
        layout.addLayout(top_box)

        # Table & Empty Label
        self.table_workout = QTableWidget()
        self.table_workout.setColumnCount(9)
        self.table_workout.setHorizontalHeaderLabels([
            "انتخاب", "ردیف", "عنوان برنامه تمرینی", "هدف برنامه", "روزهای تمرین", "سطح تمرین", "تاریخ تخصیص", "وضعیت", "عملیات"
        ])
        header = self.table_workout.horizontalHeader()
        header.setMinimumSectionSize(40)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_workout.setColumnWidth(0, 52)
        self.table_workout.setColumnWidth(1, 46)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_workout.setColumnWidth(3, 162)
        self.table_workout.setColumnWidth(4, 86)
        self.table_workout.setColumnWidth(5, 80)
        self.table_workout.setColumnWidth(6, 92)
        self.table_workout.setColumnWidth(7, 105)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table_workout.setColumnWidth(8, 268)
        self.table_workout.verticalHeader().setVisible(False)
        self.table_workout.verticalHeader().setDefaultSectionSize(52)
        self.table_workout.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_workout.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table_workout, 1)

        self.undo_banner_workout = UndoDeleteBanner(self)
        layout.addWidget(self.undo_banner_workout)

        self.lbl_no_workout = QLabel("هیچ برنامه تمرینی در تاریخچه این ورزشکار ثبت نشده است.")
        self.lbl_no_workout.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_no_workout.setStyleSheet("""
            QLabel {
                color: #777777;
                font-size: 14px;
                padding: 40px;
                background-color: #141414;
                border: 1px solid #282828;
                border-radius: 8px;
            }
        """)
        self.lbl_no_workout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_workout.setVisible(False)
        layout.addWidget(self.lbl_no_workout, 1)

        self.load_workout_archive()

    def load_workout_archive(self):
        assignments = WorkoutService.get_member_assignments(self.member_id)
        if not assignments:
            self.table_workout.setRowCount(0)
            self.table_workout.setVisible(False)
            self.lbl_no_workout.setVisible(True)
            self.chk_select_all_workout.setEnabled(False)
            self.btn_bulk_delete_workout.setEnabled(False)
            return

        self.lbl_no_workout.setVisible(False)
        self.table_workout.setVisible(True)
        self.chk_select_all_workout.setEnabled(True)
        self.chk_select_all_workout.blockSignals(True)
        self.chk_select_all_workout.setChecked(False)
        self.chk_select_all_workout.blockSignals(False)
        self.btn_bulk_delete_workout.setText("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete_workout.setEnabled(False)
        self.table_workout.setRowCount(0)
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

            chk_w = QWidget()
            chk_w.setStyleSheet("background: transparent;")
            chk_l = QHBoxLayout(chk_w)
            chk_l.setContentsMargins(0, 0, 0, 0)
            chk_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setProperty("item_id", asgn.id)
            chk.setProperty("item_name", plan_title)
            chk.toggled.connect(self.on_workout_row_checkbox_toggled)
            chk_l.addWidget(chk)
            self.table_workout.setCellWidget(row, 0, chk_w)

            self.table_workout.setItem(row, 1, QTableWidgetItem(str(row + 1)))
            self.table_workout.setItem(row, 2, QTableWidgetItem(plan_title))
            self.table_workout.setItem(row, 3, QTableWidgetItem(goal_fa))
            self.table_workout.setItem(row, 4, QTableWidgetItem(days_fa))
            self.table_workout.setItem(row, 5, QTableWidgetItem(level_fa))
            self.table_workout.setItem(row, 6, QTableWidgetItem(date_fa))
            self.table_workout.setItem(row, 7, QTableWidgetItem(status_fa))

            for c in (1, 3, 4, 5, 6, 7):
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
            btn_view.setFixedSize(72, 30)
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 6px; font-size: 11px;")
            if p:
                btn_view.clicked.connect(lambda _, pl=p: self.view_workout_plan(pl))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setToolTip("باز کردن در طراح برنامه تمرینی جهت ویرایش")
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
            if p:
                btn_edit.clicked.connect(lambda _, pid=p.id, mid=self.member_id: self.edit_workout_requested.emit(pid, mid))

            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setToolTip("صدور فایل PDF برای چاپ")
            btn_pdf.setFixedSize(56, 30)
            btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pdf.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 4px; font-size: 11px;")
            if p:
                btn_pdf.clicked.connect(lambda _, pl=p: self.export_workout_pdf(pl))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف این برنامه از بایگانی ورزشکار")
            btn_del.setFixedSize(32, 30)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 6px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, aid=asgn.id, ptitle=plan_title: self.delete_workout_plan(aid, ptitle))

            action_l.addWidget(btn_view)
            action_l.addWidget(btn_edit)
            action_l.addWidget(btn_pdf)
            action_l.addWidget(btn_del)
            self.table_workout.setCellWidget(row, 8, action_w)

    def toggle_select_all_workout(self, checked):
        for r in range(self.table_workout.rowCount()):
            cell_w = self.table_workout.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(checked)
                    chk.blockSignals(False)
        self.on_workout_row_checkbox_toggled()

    def on_workout_row_checkbox_toggled(self):
        count = len(self.get_selected_workout_assignment_ids())
        total = self.table_workout.rowCount()
        self.chk_select_all_workout.blockSignals(True)
        self.chk_select_all_workout.setChecked(count == total if total > 0 else False)
        self.chk_select_all_workout.blockSignals(False)

        if count > 0:
            fa_num = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.btn_bulk_delete_workout.setText(f"🗑️ حذف انتخاب‌شده‌ها ({fa_num})")
            self.btn_bulk_delete_workout.setEnabled(True)
        else:
            self.btn_bulk_delete_workout.setText("🗑️ حذف انتخاب‌شده‌ها")
            self.btn_bulk_delete_workout.setEnabled(False)

    def get_selected_workout_assignment_ids(self):
        selected_ids = []
        for r in range(self.table_workout.rowCount()):
            cell_w = self.table_workout.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    selected_ids.append(chk.property("item_id"))
        return selected_ids

    def _hide_workout_rows_by_ids(self, ids):
        id_set = set(ids)
        for r in range(self.table_workout.rowCount() - 1, -1, -1):
            cell_w = self.table_workout.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.property("item_id") in id_set:
                    self.table_workout.hideRow(r)

    def bulk_delete_workout_plans(self):
        selected_ids = self.get_selected_workout_assignment_ids()
        if not selected_ids:
            return

        count = len(selected_ids)
        fa_count = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        reply = QMessageBox.question(
            self, "تایید حذف گروهی برنامه‌های تمرینی",
            f"آیا از حذف {fa_count} برنامه تمرینی انتخاب‌شده از بایگانی این ورزشکار اطمینان دارید؟\n\nنکته: پس از حذف، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_workout_rows_by_ids(selected_ids)

        def commit_delete(ids):
            for aid in ids:
                try:
                    WorkoutService.delete_workout_assignment(aid)
                except Exception:
                    pass
            self.load_workout_archive()

        def undo_delete(ids):
            self.load_workout_archive()

        self.undo_banner_workout.start_countdown(
            item_count=count,
            pending_items=selected_ids,
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label="برنامه تمرینی"
        )

    def init_nutrition_tab(self):
        layout = QVBoxLayout(self.tab_nutrition)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Header Row
        top_box = QHBoxLayout()
        top_box.setSpacing(12)
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

        self.chk_select_all_nutrition = QCheckBox("انتخاب همه")
        self.chk_select_all_nutrition.setFixedWidth(120)
        self.chk_select_all_nutrition.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_select_all_nutrition.toggled.connect(self.toggle_select_all_nutrition)

        self.btn_bulk_delete_nutrition = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete_nutrition.setEnabled(False)
        self.btn_bulk_delete_nutrition.setFixedSize(190, 36)
        self.btn_bulk_delete_nutrition.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bulk_delete_nutrition.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
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
        self.btn_bulk_delete_nutrition.clicked.connect(self.bulk_delete_nutrition_plans)

        btn_assign = QPushButton("➕ تخصیص برنامه غذایی")
        btn_assign.setFixedSize(190, 36)
        btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_assign.clicked.connect(lambda: self.create_nutrition_requested.emit(self.member_id))

        top_box.addWidget(self.chk_select_all_nutrition)
        top_box.addWidget(self.btn_bulk_delete_nutrition)
        top_box.addWidget(btn_assign)
        layout.addLayout(top_box)

        # Nutrition Plans Table
        self.table_nutrition = QTableWidget()
        self.table_nutrition.setColumnCount(9)
        self.table_nutrition.setHorizontalHeaderLabels([
            "انتخاب", "ردیف", "عنوان برنامه غذایی", "هدف رژیم", "کالری هدف", "درشت‌مغذی‌ها (P/C/F)", "تاریخ تخصیص", "وضعیت", "عملیات"
        ])
        header = self.table_nutrition.horizontalHeader()
        header.setMinimumSectionSize(40)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_nutrition.setColumnWidth(0, 52)
        self.table_nutrition.setColumnWidth(1, 46)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_nutrition.setColumnWidth(3, 162)
        self.table_nutrition.setColumnWidth(4, 86)
        self.table_nutrition.setColumnWidth(5, 158)
        self.table_nutrition.setColumnWidth(6, 92)
        self.table_nutrition.setColumnWidth(7, 105)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table_nutrition.setColumnWidth(8, 268)
        self.table_nutrition.verticalHeader().setVisible(False)
        self.table_nutrition.verticalHeader().setDefaultSectionSize(52)
        self.table_nutrition.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_nutrition.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table_nutrition, 1)

        self.undo_banner_nutrition = UndoDeleteBanner(self)
        layout.addWidget(self.undo_banner_nutrition)

        self.lbl_no_nutrition = QLabel("هیچ برنامه غذایی در تاریخچه این ورزشکار ثبت نشده است.")
        self.lbl_no_nutrition.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_no_nutrition.setStyleSheet("""
            QLabel {
                color: #777777;
                font-size: 14px;
                padding: 40px;
                background-color: #141414;
                border: 1px solid #282828;
                border-radius: 8px;
            }
        """)
        self.lbl_no_nutrition.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_nutrition.setVisible(False)
        layout.addWidget(self.lbl_no_nutrition, 1)

        self.load_nutrition_archive()

    def load_nutrition_archive(self):
        assignments = NutritionService.get_member_assignments(self.member_id)
        if not assignments:
            self.table_nutrition.setRowCount(0)
            self.table_nutrition.setVisible(False)
            self.lbl_no_nutrition.setVisible(True)
            self.chk_select_all_nutrition.setEnabled(False)
            self.btn_bulk_delete_nutrition.setEnabled(False)
            return

        self.lbl_no_nutrition.setVisible(False)
        self.table_nutrition.setVisible(True)
        self.chk_select_all_nutrition.setEnabled(True)
        self.chk_select_all_nutrition.blockSignals(True)
        self.chk_select_all_nutrition.setChecked(False)
        self.chk_select_all_nutrition.blockSignals(False)
        self.btn_bulk_delete_nutrition.setText("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete_nutrition.setEnabled(False)
        self.table_nutrition.setRowCount(0)
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

            chk_w = QWidget()
            chk_w.setStyleSheet("background: transparent;")
            chk_l = QHBoxLayout(chk_w)
            chk_l.setContentsMargins(0, 0, 0, 0)
            chk_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setProperty("item_id", asgn.id)
            chk.setProperty("item_name", plan_title)
            chk.toggled.connect(self.on_nutrition_row_checkbox_toggled)
            chk_l.addWidget(chk)
            self.table_nutrition.setCellWidget(row, 0, chk_w)

            self.table_nutrition.setItem(row, 1, QTableWidgetItem(str(row + 1)))
            self.table_nutrition.setItem(row, 2, QTableWidgetItem(plan_title))
            self.table_nutrition.setItem(row, 3, QTableWidgetItem(goal_fa))
            self.table_nutrition.setItem(row, 4, QTableWidgetItem(cal_fa))
            self.table_nutrition.setItem(row, 5, QTableWidgetItem(macros_fa))
            self.table_nutrition.setItem(row, 6, QTableWidgetItem(date_fa))
            self.table_nutrition.setItem(row, 7, QTableWidgetItem(status_fa))

            for c in (1, 3, 4, 5, 6, 7):
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
            btn_view.setFixedSize(72, 30)
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 6px; font-size: 11px;")
            if p:
                btn_view.clicked.connect(lambda _, pl=p: self.view_nutrition_plan(pl))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setToolTip("باز کردن در طراح برنامه غذایی جهت ویرایش")
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
            if p:
                btn_edit.clicked.connect(lambda _, pid=p.id, mid=self.member_id: self.edit_nutrition_requested.emit(pid, mid))

            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setToolTip("صدور فایل PDF برای چاپ")
            btn_pdf.setFixedSize(56, 30)
            btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pdf.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 4px; font-size: 11px;")
            if p:
                btn_pdf.clicked.connect(lambda _, pl=p: self.export_nutrition_pdf(pl))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف این برنامه از بایگانی ورزشکار")
            btn_del.setFixedSize(32, 30)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 6px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, aid=asgn.id, ptitle=plan_title: self.delete_nutrition_plan(aid, ptitle))

            action_l.addWidget(btn_view)
            action_l.addWidget(btn_edit)
            action_l.addWidget(btn_pdf)
            action_l.addWidget(btn_del)
            self.table_nutrition.setCellWidget(row, 8, action_w)

    def toggle_select_all_nutrition(self, checked):
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
        count = len(self.get_selected_nutrition_assignment_ids())
        total = self.table_nutrition.rowCount()
        self.chk_select_all_nutrition.blockSignals(True)
        self.chk_select_all_nutrition.setChecked(count == total if total > 0 else False)
        self.chk_select_all_nutrition.blockSignals(False)

        if count > 0:
            fa_num = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.btn_bulk_delete_nutrition.setText(f"🗑️ حذف انتخاب‌شده‌ها ({fa_num})")
            self.btn_bulk_delete_nutrition.setEnabled(True)
        else:
            self.btn_bulk_delete_nutrition.setText("🗑️ حذف انتخاب‌شده‌ها")
            self.btn_bulk_delete_nutrition.setEnabled(False)

    def get_selected_nutrition_assignment_ids(self):
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

    def bulk_delete_nutrition_plans(self):
        selected_ids = self.get_selected_nutrition_assignment_ids()
        if not selected_ids:
            return

        count = len(selected_ids)
        fa_count = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        reply = QMessageBox.question(
            self, "تایید حذف گروهی برنامه‌های غذایی",
            f"آیا از حذف {fa_count} برنامه غذایی انتخاب‌شده از بایگانی این ورزشکار اطمینان دارید؟\n\nنکته: پس از حذف، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_nutrition_rows_by_ids(selected_ids)

        def commit_delete(ids):
            for aid in ids:
                try:
                    NutritionService.delete_nutrition_assignment(aid)
                except Exception:
                    pass
            self.load_nutrition_archive()

        def undo_delete(ids):
            self.load_nutrition_archive()

        self.undo_banner_nutrition.start_countdown(
            item_count=count,
            pending_items=selected_ids,
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label="برنامه غذایی"
        )

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
            f"آیا از حذف برنامه تمرینی «{plan_title}» از بایگانی این ورزشکار اطمینان دارید؟\n\nنکته: پس از تایید، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_workout_rows_by_ids([assignment_id])

        def commit_delete(ids):
            for aid in ids:
                try:
                    WorkoutService.delete_workout_assignment(aid)
                except Exception as e:
                    QMessageBox.critical(self, "خطا", f"خطا در حذف برنامه: {str(e)}")
            self.load_workout_archive()

        def undo_delete(ids):
            self.load_workout_archive()

        self.undo_banner_workout.start_countdown(
            item_count=1,
            pending_items=[assignment_id],
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label=f"«{plan_title}»"
        )

    def delete_nutrition_plan(self, assignment_id: int, plan_title: str):
        reply = QMessageBox.warning(
            self, "⚠️ تایید حذف برنامه غذایی",
            f"آیا از حذف برنامه غذایی «{plan_title}» از بایگانی این ورزشکار اطمینان دارید؟\n\nنکته: پس از تایید، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_nutrition_rows_by_ids([assignment_id])

        def commit_delete(ids):
            for aid in ids:
                try:
                    NutritionService.delete_nutrition_assignment(aid)
                except Exception as e:
                    QMessageBox.critical(self, "خطا", f"خطا در حذف برنامه: {str(e)}")
            self.load_nutrition_archive()

        def undo_delete(ids):
            self.load_nutrition_archive()

        self.undo_banner_nutrition.start_countdown(
            item_count=1,
            pending_items=[assignment_id],
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label=f"«{plan_title}»"
        )

    def export_workout_pdf(self, plan):
        try:
            member = MemberService.get_member_by_id(self.member_id)
            if not member:
                member = Member(first_name="ورزشکار", last_name="", membership_expire_shamsi="-")
            athlete_name = (member.full_name or f"{member.first_name} {member.last_name}").strip()
            athlete_name = re.sub(r'[\\/*?:"<>|]', '', athlete_name).strip() or "ورزشکار"
            now_str = get_now_shamsi_for_filename()
            default_name = f"برنامه تمرینی {athlete_name}_{now_str}.pdf"
            parent = self.window() if hasattr(self, 'window') and self.window() else self
            from nemov.utils.export_utils import resolve_athlete_export_path
            filepath, athlete_clean_name = resolve_athlete_export_path(
                member, default_name, parent, "ذخیره فایل PDF برنامه تمرینی"
            )
            if filepath:
                PDFGenerator.generate_workout_pdf(member, plan, filepath)
                QMessageBox.information(
                    parent,
                    "موفقیت",
                    f"فایل PDF برنامه تمرینی با موفقیت در پوشه اختصاصی «{athlete_clean_name}» ذخیره شد:\n\n{filepath}"
                )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from nemov.utils.logger import log_error
            from nemov.views.components.error_dialog import show_error_dialog
            log_error(f"Error exporting workout PDF: {e}\n{tb}")
            parent = self.window() if hasattr(self, 'window') and self.window() else self
            show_error_dialog(
                parent=parent,
                message="متاسفانه در حین تولید و ذخیره فایل PDF برنامه تمرینی خطایی رخ داد.",
                technical_details=tb,
                title="خطا در خروجی PDF"
            )

    def export_nutrition_pdf(self, plan):
        try:
            member = MemberService.get_member_by_id(self.member_id)
            if not member:
                member = Member(first_name="ورزشکار", last_name="", membership_expire_shamsi="-")
            athlete_name = (member.full_name or f"{member.first_name} {member.last_name}").strip()
            athlete_name = re.sub(r'[\\/*?:"<>|]', '', athlete_name).strip() or "ورزشکار"
            now_str = get_now_shamsi_for_filename()
            default_name = f"برنامه غذایی {athlete_name}_{now_str}.pdf"
            parent = self.window() if hasattr(self, 'window') and self.window() else self
            from nemov.utils.export_utils import resolve_athlete_export_path
            filepath, athlete_clean_name = resolve_athlete_export_path(
                member, default_name, parent, "ذخیره فایل PDF برنامه غذایی"
            )
            if filepath:
                PDFGenerator.generate_nutrition_pdf(member, plan, filepath)
                QMessageBox.information(
                    parent,
                    "موفقیت",
                    f"فایل PDF برنامه غذایی با موفقیت در پوشه اختصاصی «{athlete_clean_name}» ذخیره شد:\n\n{filepath}"
                )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            from nemov.utils.logger import log_error
            from nemov.views.components.error_dialog import show_error_dialog
            log_error(f"Error exporting nutrition PDF: {e}\n{tb}")
            parent = self.window() if hasattr(self, 'window') and self.window() else self
            show_error_dialog(
                parent=parent,
                message="متاسفانه در حین تولید و ذخیره فایل PDF برنامه غذایی خطایی رخ داد.",
                technical_details=tb,
                title="خطا در خروجی PDF"
            )
