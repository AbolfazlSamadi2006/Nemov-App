from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QMessageBox, QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from yalda.services.workout_service import WorkoutService
from yalda.views.components.media_viewer_dialog import MediaViewerDialog
import os

class ExerciseFormDialog(QDialog):
    def __init__(self, parent=None, exercise_data=None):
        super().__init__(parent)
        self.exercise_data = exercise_data
        self.media_path = None
        self.media_type = "image"
        self.setWindowTitle("ویرایش حرکت ورزشی" if exercise_data else "افزودن حرکت جدید به بانک")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(500, 580)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(9)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("نام حرکت به فارسی...")

        self.combo_muscle = QComboBox()
        self.combo_muscle.addItem("سینه", "chest")
        self.combo_muscle.addItem("پا و سرینی", "legs")
        self.combo_muscle.addItem("پشت و زیربغل", "back")
        self.combo_muscle.addItem("سرشانه", "shoulders")
        self.combo_muscle.addItem("بازو", "arms")
        self.combo_muscle.addItem("شکم و مرکز بدن", "abs")

        self.combo_equip = QComboBox()
        self.combo_equip.addItem("هالتر", "barbell")
        self.combo_equip.addItem("دمبل", "dumbbell")
        self.combo_equip.addItem("دستگاه", "machine")
        self.combo_equip.addItem("سیم‌کش", "cable")
        self.combo_equip.addItem("وزن بدن", "bodyweight")

        self.txt_contra = QLineEdit()
        self.txt_contra.setPlaceholderText("مثلاً: knee_injury, back_injury")

        # Video URL Input
        self.txt_video_url = QLineEdit()
        self.txt_video_url.setPlaceholderText("https://... (لینک آموزش ویدیویی از آپارات، یوتیوب، گوگل و...)")

        # Local Media Selection Row
        row_media = QHBoxLayout()
        btn_media = QPushButton("🎬 انتخاب فایل عکس/ویدیو آفلاین")
        btn_media.setObjectName("secondary_button")
        btn_media.clicked.connect(self.choose_media)
        self.lbl_media_status = QLabel("فایلی انتخاب نشده است")
        self.lbl_media_status.setStyleSheet("color: #888888; font-size: 11px;")
        row_media.addWidget(btn_media)
        row_media.addWidget(self.lbl_media_status)
        row_media.addStretch()

        self.txt_desc = QTextEdit()
        self.txt_desc.setPlaceholderText("توضیحات و نحوه اجرای صحیح...")
        self.txt_desc.setMaximumHeight(65)

        layout.addWidget(QLabel("نام حرکت ورزشی:"))
        layout.addWidget(self.txt_name)
        layout.addWidget(QLabel("عضله اصلی:"))
        layout.addWidget(self.combo_muscle)
        layout.addWidget(QLabel("تجهیزات لازم:"))
        layout.addWidget(self.combo_equip)
        layout.addWidget(QLabel("منع مصرف پزشکی (آسیب‌دیدگی‌ها):"))
        layout.addWidget(self.txt_contra)
        layout.addWidget(QLabel("🌐 لینک ویدیو یا آموزش اینترنتی (اختیاری):"))
        layout.addWidget(self.txt_video_url)
        layout.addWidget(QLabel("فایل عکس/فیلم آموزشی آفلاین (اختیاری):"))
        layout.addLayout(row_media)
        layout.addWidget(QLabel("توضیحات:"))
        layout.addWidget(self.txt_desc)

        btn_save = QPushButton("ذخیره تغییرات" if self.exercise_data else "ذخیره حرکت")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

        if self.exercise_data:
            self.load_data()

    def choose_media(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "انتخاب عکس یا فیلم آموزشی حرکت", "", "رسانه (*.mp4 *.avi *.mkv *.png *.jpg *.jpeg *.gif *.webm)"
        )
        if filepath:
            self.media_path = filepath
            ext = os.path.splitext(filepath)[1].lower()
            self.media_type = "video" if ext in ['.mp4', '.avi', '.mkv', '.webm', '.mov'] else "image"
            self.lbl_media_status.setText(f"فایل: {os.path.basename(filepath)}")
            self.lbl_media_status.setStyleSheet("color: #4CAF50; font-size: 11px;")

    def save(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "خطا", "لطفاً نام حرکت ورزشی را وارد کنید.")
            return
        self.accept()

    def get_data(self):
        return {
            "name_fa": self.txt_name.text().strip(),
            "primary_muscle": self.combo_muscle.currentData(),
            "equipment": self.combo_equip.currentData(),
            "media_path": self.media_path,
            "media_type": self.media_type,
            "video_url": self.txt_video_url.text().strip() or None,
            "contraindications": self.txt_contra.text().strip(),
            "description": self.txt_desc.toPlainText().strip()
        }

    def load_data(self):
        ex = self.exercise_data
        self.txt_name.setText(ex.name_fa or "")
        
        idx_m = self.combo_muscle.findData(ex.primary_muscle)
        if idx_m >= 0: self.combo_muscle.setCurrentIndex(idx_m)

        idx_e = self.combo_equip.findData(ex.equipment)
        if idx_e >= 0: self.combo_equip.setCurrentIndex(idx_e)

        self.txt_contra.setText(ex.contraindications or "")
        self.txt_video_url.setText(ex.video_url or "")
        self.txt_desc.setText(ex.description or "")
        self.media_path = ex.media_path
        self.media_type = ex.media_type or "image"
        if self.media_path and os.path.exists(self.media_path):
            self.lbl_media_status.setText(f"فایل: {os.path.basename(self.media_path)}")
            self.lbl_media_status.setStyleSheet("color: #4CAF50; font-size: 11px;")

class WorkoutLibraryView(QWidget):
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

        title = QLabel("🏃 بانک حرکات ورزشی و آناتومیک")
        title.setObjectName("h1")

        btn_add = QPushButton("➕ افزودن حرکت جدید")
        btn_add.clicked.connect(self.open_add_dialog)

        header.addWidget(btn_back)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_add)
        layout.addLayout(header)

        # Search Controls
        controls = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("جستجو در نام حرکات...")
        self.txt_search.textChanged.connect(self.load_exercises)

        self.combo_muscle = QComboBox()
        self.combo_muscle.addItem("همه عضلات", "all")
        self.combo_muscle.addItem("سینه", "chest")
        self.combo_muscle.addItem("پا", "legs")
        self.combo_muscle.addItem("پشت و زیربغل", "back")
        self.combo_muscle.addItem("سرشانه", "shoulders")
        self.combo_muscle.addItem("بازو", "arms")
        self.combo_muscle.addItem("شکم", "abs")
        self.combo_muscle.currentIndexChanged.connect(self.load_exercises)

        controls.addWidget(QLabel("جستجو:"))
        controls.addWidget(self.txt_search)
        controls.addWidget(QLabel("عضله هدف:"))
        controls.addWidget(self.combo_muscle)
        layout.addLayout(controls)

        # Exercises Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["نام حرکت", "عضله اصلی", "تجهیزات", "محدودیت آسیب‌دیدگی", "توضیحات", "عملیات"])
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 240)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)
        self.load_exercises()

    def load_exercises(self):
        search_query = self.txt_search.text().strip()
        muscle = self.combo_muscle.currentData()
        exercises = WorkoutService.get_all_exercises(muscle_group=muscle, search_query=search_query)

        muscle_map = {
            "chest": "سینه", "legs": "پا و سرینی", "back": "پشت و زیربغل",
            "shoulders": "سرشانه", "arms": "بازو", "abs": "شکم"
        }
        equip_map = {
            "barbell": "هالتر", "dumbbell": "دمبل", "machine": "دستگاه",
            "cable": "سیم‌کش", "bodyweight": "وزن بدن"
        }

        self.table.setRowCount(len(exercises))
        for row, ex in enumerate(exercises):
            self.table.setItem(row, 0, QTableWidgetItem(ex.name_fa))
            self.table.setItem(row, 1, QTableWidgetItem(muscle_map.get(ex.primary_muscle, ex.primary_muscle)))
            self.table.setItem(row, 2, QTableWidgetItem(equip_map.get(ex.equipment, ex.equipment or "-")))
            self.table.setItem(row, 3, QTableWidgetItem(ex.contraindications or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(ex.description or "-"))

            # Operations Widget (Media, Edit, Delete)
            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(5)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_media = QPushButton("🎬 رسانه")
            btn_media.setFixedHeight(30)
            btn_media.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_media.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D2D;
                    color: #FFFFFF;
                    font-weight: bold;
                    border: 1px solid #444444;
                    border-radius: 6px;
                    padding: 2px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #3D3D3D;
                }
            """)
            btn_media.clicked.connect(lambda _, item=ex: self.show_media(item))

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
                    padding: 2px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #A91D22;
                }
            """)
            btn_edit.clicked.connect(lambda _, item=ex: self.open_edit_dialog(item))

            btn_delete = QPushButton("🗑️")
            btn_delete.setToolTip("حذف حرکت")
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
            btn_delete.clicked.connect(lambda _, item=ex: self.delete_exercise(item))

            btn_layout.addWidget(btn_media)
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_delete)

            self.table.setCellWidget(row, 5, btn_container)

    def show_media(self, exercise):
        dlg = MediaViewerDialog(
            title=exercise.name_fa,
            media_path=exercise.media_path,
            media_type=exercise.media_type,
            video_url=exercise.video_url,
            parent=self
        )
        dlg.exec()

    def delete_exercise(self, exercise):
        reply = QMessageBox.question(
            self, "تایید حذف حرکت",
            f"آیا از حذف حرکت '{exercise.name_fa}' از بانک حرکات اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            WorkoutService.delete_exercise(exercise.id)
            self.load_exercises()
            QMessageBox.information(self, "موفقیت", "حرکت ورزشی با موفقیت حذف گردید.")

    def open_add_dialog(self):
        dlg = ExerciseFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            WorkoutService.create_exercise(data)
            self.load_exercises()
            QMessageBox.information(self, "موفقیت", "حرکت جدید به بانک افزوده شد.")

    def open_edit_dialog(self, exercise):
        dlg = ExerciseFormDialog(self, exercise_data=exercise)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            WorkoutService.update_exercise(exercise.id, data)
            self.load_exercises()
            QMessageBox.information(self, "موفقیت", "حرکت ورزشی با موفقیت ویرایش شد.")
