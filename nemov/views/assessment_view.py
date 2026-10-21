from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QFileDialog, QMessageBox, QDialog, QGridLayout
)
from PyQt6.QtCore import Qt
import os
import shutil
import config
from nemov.views.components.jalali_calendar_widget import JalaliDatePicker
from nemov.services.assessment_service import AssessmentService


class EditAssessmentDialog(QDialog):
    """Dialog for Editing an Existing Physical Assessment Record"""
    def __init__(self, assessment, parent=None):
        super().__init__(parent)
        self.assessment = assessment
        self.before_photo_path = assessment.before_photo_path
        self.after_photo_path = assessment.after_photo_path
        self.setWindowTitle(f"✏️ ویرایش ارزیابی فیزیکی ({assessment.assessment_date_shamsi})")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(580, 420)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("تاریخ ارزیابی:"), 0, 0)
        self.picker_date = JalaliDatePicker()
        if self.assessment.assessment_date_shamsi:
            self.picker_date.setText(self.assessment.assessment_date_shamsi)
        grid.addWidget(self.picker_date, 0, 1)

        grid.addWidget(QLabel("قد (cm):"), 0, 2)
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(0.0, 300.0)
        self.spin_height.setDecimals(0)
        self.spin_height.setValue(self.assessment.height_cm or 0.0)
        grid.addWidget(self.spin_height, 0, 3)

        grid.addWidget(QLabel("وزن (kg):"), 1, 0)
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0.0, 300.0)
        self.spin_weight.setValue(self.assessment.weight_kg or 0.0)
        grid.addWidget(self.spin_weight, 1, 1)

        grid.addWidget(QLabel("درصد چربی (%):"), 1, 2)
        self.spin_fat = QDoubleSpinBox()
        self.spin_fat.setRange(0.0, 100.0)
        self.spin_fat.setValue(self.assessment.body_fat_percentage or 0.0)
        grid.addWidget(self.spin_fat, 1, 3)

        # Circumferences
        grid.addWidget(QLabel("دور گردن:"), 2, 0)
        self.spin_neck = QDoubleSpinBox()
        self.spin_neck.setRange(0.0, 150.0)
        self.spin_neck.setValue(self.assessment.neck_circ or 0.0)
        grid.addWidget(self.spin_neck, 2, 1)

        grid.addWidget(QLabel("دور سینه:"), 2, 2)
        self.spin_chest = QDoubleSpinBox()
        self.spin_chest.setRange(0.0, 250.0)
        self.spin_chest.setValue(self.assessment.chest_circ or 0.0)
        grid.addWidget(self.spin_chest, 2, 3)

        grid.addWidget(QLabel("دور بازو:"), 3, 0)
        self.spin_arm = QDoubleSpinBox()
        self.spin_arm.setRange(0.0, 150.0)
        self.spin_arm.setValue(self.assessment.arm_circ or 0.0)
        grid.addWidget(self.spin_arm, 3, 1)

        grid.addWidget(QLabel("دور شکم:"), 3, 2)
        self.spin_abdomen = QDoubleSpinBox()
        self.spin_abdomen.setRange(0.0, 250.0)
        self.spin_abdomen.setValue(self.assessment.abdomen_circ or 0.0)
        grid.addWidget(self.spin_abdomen, 3, 3)

        grid.addWidget(QLabel("دور کمر:"), 4, 0)
        self.spin_waist = QDoubleSpinBox()
        self.spin_waist.setRange(0.0, 250.0)
        self.spin_waist.setValue(self.assessment.waist_circ or 0.0)
        grid.addWidget(self.spin_waist, 4, 1)

        grid.addWidget(QLabel("دور لگن:"), 4, 2)
        self.spin_hip = QDoubleSpinBox()
        self.spin_hip.setRange(0.0, 250.0)
        self.spin_hip.setValue(self.assessment.hip_circ or 0.0)
        grid.addWidget(self.spin_hip, 4, 3)

        grid.addWidget(QLabel("دور ران:"), 5, 0)
        self.spin_thigh = QDoubleSpinBox()
        self.spin_thigh.setRange(0.0, 200.0)
        self.spin_thigh.setValue(self.assessment.thigh_circ or 0.0)
        grid.addWidget(self.spin_thigh, 5, 1)

        layout.addLayout(grid)

        # Photos
        row_p = QHBoxLayout()
        row_p.setSpacing(12)

        self.btn_before = QPushButton()
        self.btn_before.setObjectName("secondary_button")
        self.btn_before.setFixedHeight(38)
        self.btn_before.clicked.connect(self.select_before_photo)

        self.btn_after = QPushButton()
        self.btn_after.setObjectName("secondary_button")
        self.btn_after.setFixedHeight(38)
        self.btn_after.clicked.connect(self.select_after_photo)

        self._update_photo_buttons()

        row_p.addWidget(self.btn_before)
        row_p.addWidget(self.btn_after)
        layout.addLayout(row_p)

        layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 ذخیره تغییرات")
        btn_save.clicked.connect(self.save_changes)
        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def _update_photo_buttons(self):
        # Before Photo
        if self.before_photo_path and os.path.exists(self.before_photo_path):
            self.btn_before.setText("📷 مشاهده و ویرایش عکس قبل")
            self.btn_before.setToolTip(f"عکس قبل: {os.path.basename(self.before_photo_path)}\nجهت مشاهده، ویرایش، یا عکسبرداری مجدد کلیک کنید.")
        else:
            self.btn_before.setText("📷 ثبت عکس قبل")
            self.btn_before.setToolTip("ثبت یا عکسبرداری عکس قبل از طریق دوربین یا سیستم")

        # After Photo
        if self.after_photo_path and os.path.exists(self.after_photo_path):
            self.btn_after.setText("📷 مشاهده و ویرایش عکس بعد")
            self.btn_after.setToolTip(f"عکس بعد: {os.path.basename(self.after_photo_path)}\nجهت مشاهده، ویرایش، یا عکسبرداری مجدد کلیک کنید.")
        else:
            self.btn_after.setText("📷 ثبت عکس بعد")
            self.btn_after.setToolTip("ثبت یا عکسبرداری عکس بعد از طریق دوربین یا سیستم")

    def select_before_photo(self):
        from nemov.views.components.image_editor_dialog import ImageEditorDialog
        from nemov.utils.image_source_chooser import get_image_file_path

        cur_path = self.before_photo_path
        if cur_path and os.path.exists(cur_path):
            while True:
                dlg = ImageEditorDialog(
                    self,
                    image_path=cur_path,
                    title="مشاهده و ویرایش عکس قبل",
                    allow_retake=True,
                    is_square_default=False
                )
                if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_image_path:
                    dest = config.PROGRESS_PHOTOS_DIR / f"before_{os.path.basename(dlg.result_image_path)}"
                    if os.path.abspath(dlg.result_image_path) != os.path.abspath(dest):
                        shutil.copy2(dlg.result_image_path, dest)
                    self.before_photo_path = str(dest)
                    self._update_photo_buttons()
                    break
                elif dlg.retake_triggered:
                    new_fp = get_image_file_path(self, dialog_title="ثبت عکس جدید (Before)", is_square_default=False, enable_editor=False)
                    if new_fp:
                        cur_path = new_fp
                        continue
                    else:
                        continue
                else:
                    break
        else:
            new_fp = get_image_file_path(self, dialog_title="ثبت عکس قبل (Before)", is_square_default=False, enable_editor=True)
            if new_fp:
                dest = config.PROGRESS_PHOTOS_DIR / f"before_{os.path.basename(new_fp)}"
                if os.path.abspath(new_fp) != os.path.abspath(dest):
                    shutil.copy2(new_fp, dest)
                self.before_photo_path = str(dest)
                self._update_photo_buttons()

    def select_after_photo(self):
        from nemov.views.components.image_editor_dialog import ImageEditorDialog
        from nemov.utils.image_source_chooser import get_image_file_path

        cur_path = self.after_photo_path
        if cur_path and os.path.exists(cur_path):
            while True:
                dlg = ImageEditorDialog(
                    self,
                    image_path=cur_path,
                    title="مشاهده و ویرایش عکس بعد",
                    allow_retake=True,
                    is_square_default=False
                )
                if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_image_path:
                    dest = config.PROGRESS_PHOTOS_DIR / f"after_{os.path.basename(dlg.result_image_path)}"
                    if os.path.abspath(dlg.result_image_path) != os.path.abspath(dest):
                        shutil.copy2(dlg.result_image_path, dest)
                    self.after_photo_path = str(dest)
                    self._update_photo_buttons()
                    break
                elif dlg.retake_triggered:
                    new_fp = get_image_file_path(self, dialog_title="ثبت عکس جدید (After)", is_square_default=False, enable_editor=False)
                    if new_fp:
                        cur_path = new_fp
                        continue
                    else:
                        continue
                else:
                    break
        else:
            new_fp = get_image_file_path(self, dialog_title="ثبت عکس بعد (After)", is_square_default=False, enable_editor=True)
            if new_fp:
                dest = config.PROGRESS_PHOTOS_DIR / f"after_{os.path.basename(new_fp)}"
                if os.path.abspath(new_fp) != os.path.abspath(dest):
                    shutil.copy2(new_fp, dest)
                self.after_photo_path = str(dest)
                self._update_photo_buttons()

    def save_changes(self):
        w = self.spin_weight.value()
        if w <= 0:
            QMessageBox.warning(self, "خطا", "لطفاً وزن را وارد کنید.")
            return

        data = {
            "assessment_date_shamsi": self.picker_date.text(),
            "height_cm": self.spin_height.value() if self.spin_height.value() > 0 else None,
            "weight_kg": w,
            "body_fat_percentage": self.spin_fat.value() if self.spin_fat.value() > 0 else None,
            "neck_circ": self.spin_neck.value() if self.spin_neck.value() > 0 else None,
            "chest_circ": self.spin_chest.value() if self.spin_chest.value() > 0 else None,
            "arm_circ": self.spin_arm.value() if self.spin_arm.value() > 0 else None,
            "abdomen_circ": self.spin_abdomen.value() if self.spin_abdomen.value() > 0 else None,
            "waist_circ": self.spin_waist.value() if self.spin_waist.value() > 0 else None,
            "hip_circ": self.spin_hip.value() if self.spin_hip.value() > 0 else None,
            "thigh_circ": self.spin_thigh.value() if self.spin_thigh.value() > 0 else None,
            "before_photo_path": self.before_photo_path,
            "after_photo_path": self.after_photo_path
        }
        AssessmentService.update_assessment(self.assessment.id, data)
        self.accept()


class CompareDialog(QDialog):
    """Side-by-Side Comparison Dialog for 2 Assessment Dates"""
    def __init__(self, comparison_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مقایسه پیشرفت بدنی ورزشکار")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(700, 580)

        layout = QVBoxLayout(self)
        a1 = comparison_data["first"]
        a2 = comparison_data["second"]
        diff = comparison_data["diff"]

        title = QLabel(f"مقایسه ارزیابی {a1.assessment_date_shamsi} با {a2.assessment_date_shamsi}")
        title.setObjectName("h2")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Stats Diff Table (12 Metrics)
        table = QTableWidget(12, 4)
        table.setHorizontalHeaderLabels(["شاخص", f"تاریخ {a1.assessment_date_shamsi}", f"تاریخ {a2.assessment_date_shamsi}", "تغییرات"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        metrics = [
            ("قد (cm)", getattr(a1, 'height_cm', None) or "-", getattr(a2, 'height_cm', None) or "-", diff.get('height_diff', 0)),
            ("وزن (kg)", a1.weight_kg, a2.weight_kg, diff['weight_diff']),
            ("درصد چربی (%)", a1.body_fat_percentage or "-", a2.body_fat_percentage or "-", diff['fat_diff']),
            ("متابولیسم پایه - BMR (kcal)", diff.get('bmr1') or "-", diff.get('bmr2') or "-", diff.get('bmr_diff', 0)),
            ("کالری روزانه - TDEE (kcal)", diff.get('tdee1') or "-", diff.get('tdee2') or "-", diff.get('tdee_diff', 0)),
            ("دور گردن (cm)", getattr(a1, 'neck_circ', None) or "-", getattr(a2, 'neck_circ', None) or "-", diff.get('neck_diff', 0)),
            ("دور سینه (cm)", a1.chest_circ or "-", a2.chest_circ or "-", diff['chest_diff']),
            ("دور بازو (cm)", a1.arm_circ or "-", a2.arm_circ or "-", diff['arm_diff']),
            ("دور شکم (cm)", getattr(a1, 'abdomen_circ', None) or "-", getattr(a2, 'abdomen_circ', None) or "-", diff.get('abdomen_diff', 0)),
            ("دور کمر (cm)", a1.waist_circ or "-", a2.waist_circ or "-", diff['waist_diff']),
            ("دور لگن (cm)", getattr(a1, 'hip_circ', None) or "-", getattr(a2, 'hip_circ', None) or "-", diff.get('hip_diff', 0)),
            ("دور ران (cm)", a1.thigh_circ or "-", a2.thigh_circ or "-", diff['thigh_diff'])
        ]

        for row, (name, v1, v2, d) in enumerate(metrics):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(str(v1)))
            table.setItem(row, 2, QTableWidgetItem(str(v2)))
            
            diff_item = QTableWidgetItem(f"{d:+}" if d else "0")
            diff_item.setForeground(Qt.GlobalColor.white)
            table.setItem(row, 3, diff_item)

        layout.addWidget(table)

        # Photos Row
        row_photos = QHBoxLayout()
        photos1 = [p for p in [a1.before_photo_path, a1.after_photo_path] if p and os.path.exists(p)]
        photos2 = [p for p in [a2.before_photo_path, a2.after_photo_path] if p and os.path.exists(p)]

        if photos1:
            btn1 = QPushButton(f"🖼️ مشاهده عکس‌های {a1.assessment_date_shamsi}")
            btn1.setObjectName("secondary_button")
            btn1.clicked.connect(lambda: self.open_photos(a1.assessment_date_shamsi, photos1))
            row_photos.addWidget(btn1)

        if photos2:
            btn2 = QPushButton(f"🖼️ مشاهده عکس‌های {a2.assessment_date_shamsi}")
            btn2.setObjectName("secondary_button")
            btn2.clicked.connect(lambda: self.open_photos(a2.assessment_date_shamsi, photos2))
            row_photos.addWidget(btn2)

        if photos1 or photos2:
            layout.addLayout(row_photos)

        btn_close = QPushButton("بستن")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def open_photos(self, date_str, photos):
        from nemov.views.health_record_view import MedicalDocumentViewerDialog
        dlg = MedicalDocumentViewerDialog(f"عکس‌های پیشرفت بدنی ({date_str})", photos, parent=self)
        dlg.exec()


class AssessmentView(QWidget):
    def __init__(self, member_id: int, parent=None):
        super().__init__(parent)
        self.member_id = member_id
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.before_photo_path = None
        self.after_photo_path = None

        self.init_ui()
        self.load_history()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # New Assessment Group Box
        group_new = QGroupBox("➕ ثبت ارزیابی فیزیکی و سایز جدید")
        layout_form = QVBoxLayout(group_new)

        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl_date = QLabel("تاریخ ارزیابی:")
        self.picker_date = JalaliDatePicker(default_today=True)
        self.picker_date.setFixedWidth(175)
        self.picker_date.setFixedHeight(38)


        lbl_h = QLabel("قد (cm):")
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(0.0, 300.0)
        self.spin_height.setSpecialValueText("")
        self.spin_height.setValue(0.0)
        self.spin_height.setDecimals(0)
        self.spin_height.setFixedWidth(115)

        lbl_w = QLabel("وزن (kg):")
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0.0, 300.0)
        self.spin_weight.setSpecialValueText("")
        self.spin_weight.setValue(0.0)
        self.spin_weight.setFixedWidth(115)

        lbl_f = QLabel("درصد چربی (%):")
        self.spin_fat = QDoubleSpinBox()
        self.spin_fat.setRange(0.0, 100.0)
        self.spin_fat.setSpecialValueText("")
        self.spin_fat.setValue(0.0)
        self.spin_fat.setFixedWidth(115)

        self.lbl_live_bmr = QLabel("BMR: - | TDEE: -")
        self.lbl_live_bmr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_live_bmr.setFixedHeight(34)
        self.lbl_live_bmr.setMinimumWidth(240)
        self.lbl_live_bmr.setMaximumWidth(360)
        self.lbl_live_bmr.setStyleSheet("font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #555555; color: white;")

        row1.addWidget(lbl_date)
        row1.addWidget(self.picker_date)
        row1.addSpacing(10)
        row1.addWidget(lbl_h)
        row1.addWidget(self.spin_height)
        row1.addSpacing(10)
        row1.addWidget(lbl_w)
        row1.addWidget(self.spin_weight)
        row1.addSpacing(10)
        row1.addWidget(lbl_f)
        row1.addWidget(self.spin_fat)
        row1.addSpacing(10)
        row1.addWidget(self.lbl_live_bmr, stretch=1)
        row1.addStretch()

        self.spin_height.valueChanged.connect(self.update_live_bmr)
        self.spin_weight.valueChanged.connect(self.update_live_bmr)
        layout_form.addLayout(row1)

        self.update_live_bmr()

        row2 = QHBoxLayout()
        row2.setSpacing(6)

        lbl_neck = QLabel("دور گردن:")
        self.spin_neck = QDoubleSpinBox()
        self.spin_neck.setRange(0.0, 150.0)
        self.spin_neck.setDecimals(1)
        self.spin_neck.setSpecialValueText("")
        self.spin_neck.setValue(0.0)
        self.spin_neck.setFixedWidth(90)
        self.spin_neck.setFixedHeight(34)

        lbl_chest = QLabel("دور سینه:")
        self.spin_chest = QDoubleSpinBox()
        self.spin_chest.setRange(0.0, 250.0)
        self.spin_chest.setDecimals(1)
        self.spin_chest.setSpecialValueText("")
        self.spin_chest.setValue(0.0)
        self.spin_chest.setFixedWidth(90)
        self.spin_chest.setFixedHeight(34)

        lbl_arm = QLabel("دور بازو:")
        self.spin_arm = QDoubleSpinBox()
        self.spin_arm.setRange(0.0, 150.0)
        self.spin_arm.setDecimals(1)
        self.spin_arm.setSpecialValueText("")
        self.spin_arm.setValue(0.0)
        self.spin_arm.setFixedWidth(90)
        self.spin_arm.setFixedHeight(34)

        lbl_abdomen = QLabel("دور شکم:")
        self.spin_abdomen = QDoubleSpinBox()
        self.spin_abdomen.setRange(0.0, 250.0)
        self.spin_abdomen.setDecimals(1)
        self.spin_abdomen.setSpecialValueText("")
        self.spin_abdomen.setValue(0.0)
        self.spin_abdomen.setFixedWidth(90)
        self.spin_abdomen.setFixedHeight(34)

        lbl_waist = QLabel("دور کمر:")
        self.spin_waist = QDoubleSpinBox()
        self.spin_waist.setRange(0.0, 250.0)
        self.spin_waist.setDecimals(1)
        self.spin_waist.setSpecialValueText("")
        self.spin_waist.setValue(0.0)
        self.spin_waist.setFixedWidth(90)
        self.spin_waist.setFixedHeight(34)

        lbl_hip = QLabel("دور لگن:")
        self.spin_hip = QDoubleSpinBox()
        self.spin_hip.setRange(0.0, 250.0)
        self.spin_hip.setDecimals(1)
        self.spin_hip.setSpecialValueText("")
        self.spin_hip.setValue(0.0)
        self.spin_hip.setFixedWidth(90)
        self.spin_hip.setFixedHeight(34)

        lbl_thigh = QLabel("دور ران:")
        self.spin_thigh = QDoubleSpinBox()
        self.spin_thigh.setRange(0.0, 200.0)
        self.spin_thigh.setDecimals(1)
        self.spin_thigh.setSpecialValueText("")
        self.spin_thigh.setValue(0.0)
        self.spin_thigh.setFixedWidth(90)
        self.spin_thigh.setFixedHeight(34)

        row2.addWidget(lbl_neck)
        row2.addWidget(self.spin_neck)
        row2.addSpacing(6)
        row2.addWidget(lbl_chest)
        row2.addWidget(self.spin_chest)
        row2.addSpacing(6)
        row2.addWidget(lbl_arm)
        row2.addWidget(self.spin_arm)
        row2.addSpacing(6)
        row2.addWidget(lbl_abdomen)
        row2.addWidget(self.spin_abdomen)
        row2.addSpacing(6)
        row2.addWidget(lbl_waist)
        row2.addWidget(self.spin_waist)
        row2.addSpacing(6)
        row2.addWidget(lbl_hip)
        row2.addWidget(self.spin_hip)
        row2.addSpacing(6)
        row2.addWidget(lbl_thigh)
        row2.addWidget(self.spin_thigh)
        row2.addStretch()
        layout_form.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(8)

        self.btn_before = QPushButton("📷 عکس قبل")
        self.btn_before.setObjectName("secondary_button")
        self.btn_before.setMinimumWidth(135)
        self.btn_before.setFixedHeight(34)
        self.btn_before.clicked.connect(self.select_before_photo)

        self.btn_after = QPushButton("📷 عکس بعد")
        self.btn_after.setObjectName("secondary_button")
        self.btn_after.setMinimumWidth(135)
        self.btn_after.setFixedHeight(34)
        self.btn_after.clicked.connect(self.select_after_photo)

        btn_save = QPushButton("💾 ذخیره ارزیابی")
        btn_save.setFixedSize(120, 34)
        btn_save.clicked.connect(self.save_assessment)

        btn_reset = QPushButton("🔄 بازنشانی فرم")
        btn_reset.setFixedSize(120, 34)
        btn_reset.setObjectName("secondary_button")
        btn_reset.clicked.connect(self.reset_form)

        row3.addWidget(self.btn_before)
        row3.addSpacing(6)
        row3.addWidget(self.btn_after)
        row3.addStretch()
        row3.addWidget(btn_save)
        row3.addWidget(btn_reset)
        layout_form.addLayout(row3)

        layout.addWidget(group_new)

        # History Table & Compare Button
        row_hist = QHBoxLayout()
        lbl_hist = QLabel("📊 تاریخچه ارزیابی‌های آنتروپومتریک")
        lbl_hist.setObjectName("h2")
        
        btn_compare = QPushButton("🔍 مقایسه دو تاریخ")
        btn_compare.setObjectName("secondary_button")
        btn_compare.clicked.connect(self.compare_selected)

        row_hist.addWidget(lbl_hist)
        row_hist.addStretch()
        row_hist.addWidget(btn_compare)
        layout.addLayout(row_hist)

        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "تاریخ (شمسی)", "قد (cm)", "وزن (kg)", "درصد چربی", "BMR / TDEE (kcal)", "دور گردن", "دور سینه", "دور بازو", "دور شکم", "دور کمر", "دور لگن", "دور ران", "تصاویر پیشرفت", "عملیات"
        ])
        
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(40)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 92)   # تاریخ
        self.table.setColumnWidth(1, 58)   # قد
        self.table.setColumnWidth(2, 64)   # وزن
        self.table.setColumnWidth(3, 78)   # چربی
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # BMR / TDEE
        self.table.setColumnWidth(5, 64)   # گردن
        self.table.setColumnWidth(6, 64)   # سینه
        self.table.setColumnWidth(7, 58)   # بازو
        self.table.setColumnWidth(8, 64)   # شکم
        self.table.setColumnWidth(9, 58)   # کمر
        self.table.setColumnWidth(10, 58)  # لگن
        self.table.setColumnWidth(11, 56)  # ران
        self.table.setColumnWidth(12, 96)  # عکس‌ها
        header.setSectionResizeMode(13, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(13, 140) # عملیات

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table, 1)

    def select_before_photo(self):
        from nemov.utils.image_source_chooser import get_image_file_path
        fp = get_image_file_path(self, dialog_title="انتخاب یا ثبت عکس قبل (Before)")
        if fp:
            dest = config.PROGRESS_PHOTOS_DIR / f"before_{os.path.basename(fp)}"
            shutil.copy2(fp, dest)
            self.before_photo_path = str(dest)
            self.btn_before.setText(f"📷 عکس قبل: {os.path.basename(fp)[:12]}")

    def select_after_photo(self):
        from nemov.utils.image_source_chooser import get_image_file_path
        fp = get_image_file_path(self, dialog_title="انتخاب یا ثبت عکس بعد (After)")
        if fp:
            dest = config.PROGRESS_PHOTOS_DIR / f"after_{os.path.basename(fp)}"
            shutil.copy2(fp, dest)
            self.after_photo_path = str(dest)
            self.btn_after.setText(f"📷 عکس بعد: {os.path.basename(fp)[:12]}")

    def save_assessment(self):
        date_str = self.picker_date.text()
        if not date_str:
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ ارزیابی را وارد کنید.")
            return

        weight = self.spin_weight.value()
        height = self.spin_height.value()

        if weight <= 0:
            QMessageBox.warning(self, "خطا", "لطفاً وزن را به درستی وارد کنید.")
            return

        data = {
            "assessment_date_shamsi": date_str,
            "weight_kg": weight,
            "body_fat_percentage": self.spin_fat.value() if self.spin_fat.value() > 0 else None,
            "height_cm": height if height > 0 else None,
            "neck_circ": self.spin_neck.value() if self.spin_neck.value() > 0 else None,
            "chest_circ": self.spin_chest.value() if self.spin_chest.value() > 0 else None,
            "arm_circ": self.spin_arm.value() if self.spin_arm.value() > 0 else None,
            "waist_circ": self.spin_waist.value() if self.spin_waist.value() > 0 else None,
            "abdomen_circ": self.spin_abdomen.value() if self.spin_abdomen.value() > 0 else None,
            "hip_circ": self.spin_hip.value() if self.spin_hip.value() > 0 else None,
            "thigh_circ": self.spin_thigh.value() if self.spin_thigh.value() > 0 else None,
            "before_photo_path": self.before_photo_path,
            "after_photo_path": self.after_photo_path
        }

        try:
            AssessmentService.add_assessment(self.member_id, data)
            QMessageBox.information(self, "موفقیت", "ارزیابی با موفقیت ذخیره شد.")
            self.reset_form()
            self.load_history()
            if hasattr(self.parent(), 'load_member_info'):
                self.parent().load_member_info()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره ارزیابی: {str(e)}")

    def reset_form(self):
        self.spin_height.setValue(0.0)
        self.spin_weight.setValue(0.0)
        self.spin_fat.setValue(0.0)
        self.spin_neck.setValue(0.0)
        self.spin_chest.setValue(0.0)
        self.spin_arm.setValue(0.0)
        self.spin_abdomen.setValue(0.0)
        self.spin_waist.setValue(0.0)
        self.spin_hip.setValue(0.0)
        self.spin_thigh.setValue(0.0)
        self.before_photo_path = None
        self.after_photo_path = None
        self.btn_before.setText("📷 عکس قبل")
        self.btn_after.setText("📷 عکس بعد")
        self.update_live_bmr()

    def update_live_bmr(self):
        from nemov.services.member_service import MemberService
        from nemov.utils.bmr_calculator import calculate_bmr_tdee, calculate_age_from_shamsi
        member = MemberService.get_member_by_id(self.member_id)
        
        input_h = self.spin_height.value()
        height_cm = input_h if input_h > 0 else (member.height_cm if member and member.height_cm else 0.0)
        weight_kg = self.spin_weight.value()

        if height_cm > 0 and weight_kg > 0:
            age = calculate_age_from_shamsi(member.birth_date_shamsi if member else None)
            gender = member.gender if member else "male"
            act_level = getattr(member, "activity_level", None) or "moderately_active"
            bmr, tdee, pal, act_title, color = calculate_bmr_tdee(height_cm, weight_kg, age, gender, act_level)
            if bmr > 0:
                self.lbl_live_bmr.setText(f"\u200fBMR: {bmr:,} | کالری روزانه: {tdee:,} کالری")
                self.lbl_live_bmr.setStyleSheet(f"font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: {color}; color: white;")
            else:
                self.lbl_live_bmr.setText("BMR: - | TDEE: -")
                self.lbl_live_bmr.setStyleSheet("font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #555555; color: white;")
        else:
            self.lbl_live_bmr.setText("BMR: - | TDEE: -")
            self.lbl_live_bmr.setStyleSheet("font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #555555; color: white;")

    def load_history(self):
        from nemov.services.member_service import MemberService
        from nemov.services.assessment_service import AssessmentService
        from nemov.utils.bmr_calculator import calculate_bmr_tdee, calculate_age_from_shamsi
        member = MemberService.get_member_by_id(self.member_id)
        fallback_height = member.height_cm if member else 175.0
        age = calculate_age_from_shamsi(member.birth_date_shamsi if member else None)
        gender = member.gender if member else "male"
        act_level = getattr(member, "activity_level", None) or "moderately_active"

        records = AssessmentService.get_member_assessments(self.member_id)
        self.table.setRowCount(len(records))
        self.records_list = records

        for row, rec in enumerate(records):
            rec_height = getattr(rec, 'height_cm', None) or fallback_height
            bmr_calc, tdee_calc, _, _, _ = calculate_bmr_tdee(rec_height or 175.0, rec.weight_kg, age, gender, act_level)
            rec_bmr = int(round(getattr(rec, 'bmr', None) or bmr_calc))
            rec_tdee = int(round(getattr(rec, 'tdee', None) or tdee_calc))
            bmr_tdee_text = f"BMR: {rec_bmr:,} | TDEE: {rec_tdee:,}" if rec_bmr > 0 else "-"

            height_display = str(rec.height_cm) if (hasattr(rec, 'height_cm') and rec.height_cm) else "-"

            items = [
                QTableWidgetItem(rec.assessment_date_shamsi),
                QTableWidgetItem(height_display),
                QTableWidgetItem(str(rec.weight_kg)),
                QTableWidgetItem(str(rec.body_fat_percentage or "-")),
                QTableWidgetItem(bmr_tdee_text),
                QTableWidgetItem(str(getattr(rec, 'neck_circ', None) or "-")),
                QTableWidgetItem(str(rec.chest_circ or "-")),
                QTableWidgetItem(str(rec.arm_circ or "-")),
                QTableWidgetItem(str(getattr(rec, 'abdomen_circ', None) or "-")),
                QTableWidgetItem(str(rec.waist_circ or "-")),
                QTableWidgetItem(str(rec.hip_circ or "-")),
                QTableWidgetItem(str(rec.thigh_circ or "-")),
            ]

            for c_idx, itm in enumerate(items):
                itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, c_idx, itm)

            # Progress Photos Button
            photos = [p for p in [rec.before_photo_path, rec.after_photo_path] if p and os.path.exists(p)]
            if photos:
                btn_photos = QPushButton(f"🖼️ {len(photos)} عکس")
                btn_photos.setObjectName("secondary_button")
                btn_photos.setFixedHeight(28)
                btn_photos.setStyleSheet("font-size: 11px; padding: 2px 6px;")
                btn_photos.clicked.connect(lambda _, d=rec.assessment_date_shamsi, p=photos: self.view_progress_photos(d, p))
                self.table.setCellWidget(row, 12, btn_photos)
            else:
                item_no_photo = QTableWidgetItem("-")
                item_no_photo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 12, item_no_photo)

            # Action Buttons Cell
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.setSpacing(5)

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
            btn_edit.clicked.connect(lambda _, r=rec: self.edit_assessment(r))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف ارزیابی")
            btn_del.setFixedSize(32, 30)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 6px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, r=rec: self.delete_assessment_confirm(r))

            action_layout.addWidget(btn_edit)
            action_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 13, action_widget)

    def edit_assessment(self, assessment):
        dlg = EditAssessmentDialog(assessment, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_history()
            if hasattr(self.parent(), 'load_member_info'):
                self.parent().load_member_info()
            QMessageBox.information(self, "موفقیت", "تغییرات ارزیابی با موفقیت ذخیره شد.")

    def delete_assessment_confirm(self, assessment):
        reply = QMessageBox.question(
            self, "تایید حذف", f"آیا از حذف ارزیابی مورخ {assessment.assessment_date_shamsi} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if AssessmentService.delete_assessment(assessment.id):
                self.load_history()
                if hasattr(self.parent(), 'load_member_info'):
                    self.parent().load_member_info()
                QMessageBox.information(self, "حذف شد", "ارزیابی با موفقیت حذف گردید.")

    def view_progress_photos(self, date_str: str, photos_list: list):
        from nemov.views.health_record_view import MedicalDocumentViewerDialog
        dlg = MedicalDocumentViewerDialog(f"عکس‌های پیشرفت بدنی ({date_str})", photos_list, parent=self)
        dlg.exec()

    def compare_selected(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if len(selected_rows) != 2:
            QMessageBox.warning(self, "راهنما", "لطفاً دقیقاً دو سطر از جدول تاریخچه را جهت مقایسه انتخاب کنید (با کلید Ctrl).")
            return

        idx1 = selected_rows[0].row()
        idx2 = selected_rows[1].row()
        rec1 = self.records_list[idx1]
        rec2 = self.records_list[idx2]

        comp_data = AssessmentService.compare_assessments(rec1.id, rec2.id)
        if comp_data:
            dlg = CompareDialog(comp_data, self)
            dlg.exec()
