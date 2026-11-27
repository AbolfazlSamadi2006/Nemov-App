from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QMessageBox, QTextEdit, QFileDialog, QCheckBox, QFrame, QScrollArea,
    QStyledItemDelegate, QStyleOptionViewItem, QToolTip, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QRect, QModelIndex, QEvent
from PyQt6.QtGui import QPainter, QColor, QFont, QHelpEvent
from nemov.services.workout_service import WorkoutService
from nemov.views.components.media_viewer_dialog import MediaViewerDialog
from nemov.views.components.undo_delete_banner import UndoDeleteBanner
import os
from nemov.views.components.muscle_selector_widget import MuscleSelectorWidget, MUSCLE_DEFINITIONS
from nemov.utils.theme_manager import ThemeManager


class OperationsDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hover_row = -1
        self.hover_btn = 0  # 0: none, 1: media, 2: edit, 3: del

    def _get_button_rects(self, rect: QRect):
        start_x = rect.left() + max(0, (rect.width() - 226) // 2)
        y = rect.top() + max(0, (rect.height() - 30) // 2)
        media_rect = QRect(start_x, y, 84, 30)
        edit_rect = QRect(start_x + 90, y, 72, 30)
        del_rect = QRect(start_x + 168, y, 58, 30)
        return media_rect, edit_rect, del_rect

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        super().paint(painter, option, index)
        ex = index.data(Qt.ItemDataRole.UserRole)
        if not ex:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        btn_font = QFont(option.font)
        btn_font.setPixelSize(11)
        btn_font.setBold(True)
        painter.setFont(btn_font)

        media_rect, edit_rect, del_rect = self._get_button_rects(option.rect)
        r = index.row()

        # 1. Media
        pal = ThemeManager.get_current_palette()
        has_cloud = index.data(Qt.ItemDataRole.UserRole + 1)
        media_bg = QColor(pal.btn_sec_hover) if (self.hover_row == r and self.hover_btn == 1) else QColor(pal.btn_sec_bg)
        painter.setPen(QColor(pal.btn_sec_border))
        painter.setBrush(media_bg)
        painter.drawRoundedRect(media_rect, 6, 6)
        painter.setPen(QColor(pal.btn_sec_text))
        painter.drawText(media_rect, Qt.AlignmentFlag.AlignCenter, "🎬 رسانه ☁️" if has_cloud else "🎬 رسانه")

        # 2. Edit
        edit_bg = QColor("#B45309") if (self.hover_row == r and self.hover_btn == 2) else QColor("#D97706")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(edit_bg)
        painter.drawRoundedRect(edit_rect, 6, 6)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(edit_rect, Qt.AlignmentFlag.AlignCenter, "✏️ ویرایش")

        # 3. Delete
        del_bg = QColor("#B71C1C") if (self.hover_row == r and self.hover_btn == 3) else QColor("#D32F2F")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(del_bg)
        painter.drawRoundedRect(del_rect, 6, 6)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(del_rect, Qt.AlignmentFlag.AlignCenter, "🗑️ حذف")

        painter.restore()

    def editorEvent(self, event: QEvent, model, option: QStyleOptionViewItem, index: QModelIndex) -> bool:
        ex = index.data(Qt.ItemDataRole.UserRole)
        if not ex:
            return False

        media_rect, edit_rect, del_rect = self._get_button_rects(option.rect)
        pos = event.position().toPoint() if hasattr(event, "position") else None

        if event.type() == QEvent.Type.MouseMove and pos is not None:
            btn = 0
            if media_rect.contains(pos):
                btn = 1
            elif edit_rect.contains(pos):
                btn = 2
            elif del_rect.contains(pos):
                btn = 3

            r = index.row()
            if self.hover_row != r or self.hover_btn != btn:
                self.hover_row = r
                self.hover_btn = btn
                if option.widget:
                    option.widget.viewport().update()

            if option.widget:
                if btn != 0:
                    option.widget.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    option.widget.viewport().unsetCursor()
            return True

        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            if hasattr(event, "button") and event.button() == Qt.MouseButton.LeftButton and pos is not None:
                if media_rect.contains(pos) or edit_rect.contains(pos) or del_rect.contains(pos):
                    if event.type() == QEvent.Type.MouseButtonRelease:
                        parent_view = self.parent()
                        if media_rect.contains(pos):
                            if hasattr(parent_view, "show_media"):
                                parent_view.show_media(ex)
                        elif edit_rect.contains(pos):
                            if hasattr(parent_view, "open_edit_dialog"):
                                parent_view.open_edit_dialog(ex)
                        elif del_rect.contains(pos):
                            if hasattr(parent_view, "delete_exercise"):
                                parent_view.delete_exercise(ex)
                    return True

        return super().editorEvent(event, model, option, index)


class TwoLineDescriptionDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        self.initStyleOption(option, index)

        style = option.widget.style() if option.widget else QApplication.style()
        style.drawPrimitive(style.PrimitiveElement.PE_PanelItemViewItem, option, painter, option.widget)

        raw_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        if not raw_text or raw_text.strip() == "-":
            painter.restore()
            return

        clean_text = raw_text.replace("\r\n", " ").replace("\n", " ").strip()
        if " | " in clean_text:
            parts = [p.strip() for p in clean_text.split(" | ") if p.strip()]
            clean_text = " - ".join(parts[:2])

        rect = option.rect.adjusted(12, 4, -12, -4)
        font = QFont(option.font)
        font.setPointSize(9)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        painter.setFont(font)
        painter.setPen(QColor(ThemeManager.get_current_palette().text_secondary))

        fm = painter.fontMetrics()
        line_height = fm.lineSpacing()

        # Word wrap into at most 2 lines with elide
        words = clean_text.split()
        l1_words = []
        l2_words = []
        is_l1 = True

        for w in words:
            if is_l1:
                test_str = " ".join(l1_words + [w])
                if fm.horizontalAdvance(test_str) <= rect.width():
                    l1_words.append(w)
                else:
                    is_l1 = False
                    l2_words.append(w)
            else:
                l2_words.append(w)

        line1 = " ".join(l1_words)
        line2 = " ".join(l2_words)

        if line2:
            line2_elided = fm.elidedText(line2, Qt.TextElideMode.ElideRight, rect.width())
            total_h = line_height * 2
            start_y = rect.top() + max(0, (rect.height() - total_h) // 2)
            r1 = QRect(rect.left(), start_y, rect.width(), line_height)
            r2 = QRect(rect.left(), start_y + line_height, rect.width(), line_height)
            painter.drawText(r1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, line1)
            painter.drawText(r2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, line2_elided)
        else:
            line1_elided = fm.elidedText(line1, Qt.TextElideMode.ElideRight, rect.width())
            r1 = QRect(rect.left(), rect.top(), rect.width(), rect.height())
            painter.drawText(r1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, line1_elided)

        painter.restore()

    def helpEvent(self, event: QHelpEvent, view: QAbstractItemView, option: QStyleOptionViewItem, index: QModelIndex) -> bool:
        if event.type() == QEvent.Type.ToolTip:
            raw_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
            if raw_text and raw_text.strip() != "-":
                tooltip_text = raw_text.replace(" | ", "\n• ")
                if " | " in raw_text:
                    tooltip_text = "• " + tooltip_text
                QToolTip.showText(event.globalPos(), tooltip_text, view)
                return True
            QToolTip.hideText()
            event.ignore()
            return True
        return super().helpEvent(event, view, option, index)


class ExerciseFormDialog(QDialog):
    def __init__(self, parent=None, exercise_data=None, draft_data=None):
        super().__init__(parent)
        self.exercise_data = exercise_data
        self._draft_data = draft_data
        self._was_saved = False
        self.media_path = None
        self.media_type = "image"
        self.thumbnail_path = None
        self.video_cloud_url = None
        self.setWindowTitle("ویرایش حرکت ورزشی" if exercise_data else "افزودن حرکت جدید به بانک")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        from nemov.utils.ui_scaling import compute_responsive_size, clamp_minimum_size
        min_w, min_h = clamp_minimum_size(800, 520, widget=self, floor_w=640, floor_h=380)
        pref_w, pref_h = compute_responsive_size(880, 640, widget=self, min_w=min_w, min_h=min_h)
        self.resize(pref_w, pref_h)
        self.setMinimumSize(min_w, min_h)
        self.init_ui()
        self._apply_theme_style()
        try:
            ThemeManager.theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _on_theme_changed(self, _theme_key: str):
        self._apply_theme_style()

    def _apply_theme_style(self):
        pal = ThemeManager.get_current_palette()
        r_bg, r_fg, r_bd, r_hv = ThemeManager.get_tone_colors("rose", pal)
        if hasattr(self, "btn_remove_media"):
            self.btn_remove_media.setStyleSheet(
                f"QPushButton {{ font-size: 11px; font-weight: bold; padding: 6px 10px; "
                f"background-color: {r_bg}; color: {r_fg}; border: 1px solid {r_bd}; border-radius: 4px; }}"
                f"QPushButton:hover {{ background-color: {r_hv}; color: #FFFFFF; }}"
            )
        if hasattr(self, "lbl_media_status"):
            self.lbl_media_status.setStyleSheet(f"color: {pal.text_muted}; font-size: 11px;")
        if hasattr(self, "chk_corrective"):
            self.chk_corrective.setStyleSheet(f"font-weight: bold; color: {pal.text_primary};")
        if hasattr(self, "lbl_anat_title"):
            head_col = pal.primary_hover if pal.is_dark else pal.primary
            self.lbl_anat_title.setStyleSheet(f"font-weight: bold; color: {head_col}; font-size: 12px;")

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(18)

        # Right Column: Form Inputs with responsive scroll container and pinned save button
        vlay_form = QVBoxLayout()
        vlay_form.setSpacing(8)

        scroll_form = QScrollArea()
        scroll_form.setWidgetResizable(True)
        scroll_form.setFrameShape(QFrame.Shape.NoFrame)
        scroll_form.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        form_container = QWidget()
        form_container.setObjectName("exercise_form_container")
        form_container.setStyleSheet("QWidget#exercise_form_container { background: transparent; }")
        vlay_form_fields = QVBoxLayout(form_container)
        vlay_form_fields.setContentsMargins(6, 0, 6, 0)
        vlay_form_fields.setSpacing(7)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("نام حرکت به فارسی...")

        self.combo_muscle = QComboBox()
        self.combo_muscle.addItem("انتخاب عضله هدف...", "")
        # 15 Detailed Muscles
        for m_key, m_info in MUSCLE_DEFINITIONS.items():
            self.combo_muscle.addItem(f"{m_info['name_fa']}", m_key)
        # General legacy categories
        self.combo_muscle.addItem("--- دسته‌بندی‌های کلی ---", "")
        self.combo_muscle.addItem("سینه (کلی)", "chest")
        self.combo_muscle.addItem("پا و سرینی (کلی)", "legs")
        self.combo_muscle.addItem("پشت و زیربغل (کلی)", "back")
        self.combo_muscle.addItem("سرشانه (کلی)", "shoulders")
        self.combo_muscle.addItem("بازو (کلی)", "arms")
        self.combo_muscle.addItem("شکم و مرکز بدن (کلی)", "abs")

        self.combo_muscle.currentIndexChanged.connect(self._on_combo_muscle_changed)

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
        row_media.setSpacing(6)
        btn_choose = QPushButton("📁 انتخاب از سیستم")
        btn_choose.setObjectName("secondary_button")
        btn_choose.setStyleSheet("font-size: 11px; padding: 6px 10px;")
        btn_choose.clicked.connect(self.choose_media)

        btn_record = QPushButton("🎥 ضبط با دوربین")
        btn_record.setStyleSheet("font-size: 11px; font-weight: bold; padding: 6px 10px; background-color: #e53935; color: white; border-radius: 4px;")
        btn_record.clicked.connect(self.record_media)

        self.btn_edit_media = QPushButton("✂️ ویرایش ویدیو")
        self.btn_edit_media.setStyleSheet("font-size: 11px; font-weight: bold; padding: 6px 10px; background-color: #0088cc; color: white; border-radius: 4px;")
        self.btn_edit_media.clicked.connect(self.edit_media)
        self.btn_edit_media.hide()

        self.btn_remove_media = QPushButton("🗑️ حذف رسانه")
        self.btn_remove_media.setStyleSheet("font-size: 11px; font-weight: bold; padding: 6px 10px; background-color: #333333; color: #ff8a80; border: 1px solid #555555; border-radius: 4px;")
        self.btn_remove_media.setToolTip("حذف عکس یا ویدیوی ثبت‌شده برای این حرکت")
        self.btn_remove_media.clicked.connect(self.remove_media)
        self.btn_remove_media.hide()

        row_media.addWidget(btn_choose)
        row_media.addWidget(btn_record)
        row_media.addWidget(self.btn_edit_media)
        row_media.addWidget(self.btn_remove_media)
        row_media.addStretch()

        self.lbl_media_status = QLabel("فایلی انتخاب نشده است")
        self.lbl_media_status.setStyleSheet("color: #888888; font-size: 11px;")

        self.chk_corrective = QCheckBox("✨ این حرکت، یک حرکت اصلاحی است")
        self.chk_corrective.setStyleSheet("font-weight: bold; color: #E0E0E0;")

        self.txt_desc = QTextEdit()
        self.txt_desc.setPlaceholderText("توضیحات و نحوه اجرای صحیح...")
        self.txt_desc.setMaximumHeight(65)

        vlay_form_fields.addWidget(QLabel("نام حرکت ورزشی:"))
        vlay_form_fields.addWidget(self.txt_name)
        vlay_form_fields.addWidget(QLabel("عضله هدف (انتخاب از لیست یا کلیک روی آدمک):"))
        vlay_form_fields.addWidget(self.combo_muscle)
        vlay_form_fields.addWidget(QLabel("تجهیزات لازم:"))
        vlay_form_fields.addWidget(self.combo_equip)
        vlay_form_fields.addWidget(QLabel("منع مصرف پزشکی (آسیب‌دیدگی‌ها):"))
        vlay_form_fields.addWidget(self.txt_contra)
        vlay_form_fields.addWidget(QLabel("🌐 لینک ویدیو یا آموزش اینترنتی (اختیاری):"))
        vlay_form_fields.addWidget(self.txt_video_url)
        vlay_form_fields.addWidget(QLabel("فایل عکس/فیلم آموزشی آفلاین (اختیاری):"))
        vlay_form_fields.addLayout(row_media)
        vlay_form_fields.addWidget(self.lbl_media_status)
        vlay_form_fields.addWidget(self.chk_corrective)
        vlay_form_fields.addWidget(QLabel("توضیحات:"))
        vlay_form_fields.addWidget(self.txt_desc)

        scroll_form.setWidget(form_container)
        vlay_form.addWidget(scroll_form, 1)

        self.undo_banner = UndoDeleteBanner(self)
        vlay_form.addWidget(self.undo_banner)

        btn_save = QPushButton("ذخیره تغییرات" if self.exercise_data else "ذخیره حرکت")
        btn_save.setFixedHeight(38)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.save)
        vlay_form.addWidget(btn_save)

        # Left Column: Mannequin Visual Selector
        vlay_anatomy = QVBoxLayout()
        vlay_anatomy.setSpacing(6)
        self.lbl_anat_title = QLabel("🧍 انتخاب آناتومیک روی بدن (روبرو و پشت)")
        vlay_anatomy.addWidget(self.lbl_anat_title)

        self.muscle_selector = MuscleSelectorWidget(self, is_filter_mode=False)
        self.muscle_selector.muscle_changed.connect(self._on_mannequin_muscle_changed)
        vlay_anatomy.addWidget(self.muscle_selector, 1)

        main_layout.addLayout(vlay_form, 1)
        main_layout.addLayout(vlay_anatomy, 1)

        if self.exercise_data:
            self.load_data()
        else:
            cur_key = self.combo_muscle.currentData()
            if cur_key:
                self.muscle_selector.set_selected_muscle(cur_key)
            else:
                self.muscle_selector.clear_selection()

        self._init_draft_persistence()

    def _on_mannequin_muscle_changed(self, muscle_key: str, name_fa: str):
        if muscle_key:
            idx = self.combo_muscle.findData(muscle_key)
            if idx >= 0:
                self.combo_muscle.blockSignals(True)
                self.combo_muscle.setCurrentIndex(idx)
                self.combo_muscle.blockSignals(False)
        else:
            self.combo_muscle.blockSignals(True)
            self.combo_muscle.setCurrentIndex(0)
            self.combo_muscle.blockSignals(False)

    def _on_combo_muscle_changed(self, idx: int):
        m_key = self.combo_muscle.currentData()
        if m_key:
            self.muscle_selector.set_selected_muscle(m_key)
        else:
            self.muscle_selector.clear_selection()

    def choose_media(self):
        import shutil
        from pathlib import Path
        import config
        from nemov.utils.image_utils import extract_video_thumbnail

        filepath, _ = QFileDialog.getOpenFileName(
            self, "انتخاب عکس یا فیلم آموزشی حرکت", "", "رسانه (*.mp4 *.avi *.mkv *.png *.jpg *.jpeg *.gif *.webm *.mov)"
        )
        if not filepath:
            return

        ext = os.path.splitext(filepath)[1].lower()
        is_video = ext in ['.mp4', '.avi', '.mkv', '.webm', '.mov']

        # Ensure target folder in config.EXERCISE_MEDIA_DIR exists
        config.EXERCISE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        dest_filename = os.path.basename(filepath)
        dest_path = config.EXERCISE_MEDIA_DIR / dest_filename

        try:
            if os.path.abspath(filepath) != os.path.abspath(str(dest_path)):
                shutil.copy2(filepath, str(dest_path))
            stored_path = str(dest_path)
        except Exception:
            stored_path = filepath

        if is_video:
            self.media_type = "video"
            self.media_path = stored_path
            thumb_dest = config.EXERCISE_MEDIA_DIR / f"thumb_{Path(stored_path).stem}.jpg"
            self.thumbnail_path = extract_video_thumbnail(stored_path, str(thumb_dest)) or stored_path
            self.btn_edit_media.setText("✂️ ویرایش ویدیو")
            self.btn_edit_media.show()
        else:
            self.media_type = "image"
            self.media_path = stored_path
            self.thumbnail_path = stored_path
            self.btn_edit_media.setText("🎨 ویرایش تصویر")
            self.btn_edit_media.show()

        # Reset video_cloud_url because a brand-new local file was selected
        self.video_cloud_url = None
        # Clear previous cloud video link from txt_video_url so the old URL is not kept
        current_url = self.txt_video_url.text().strip()
        if "workers.dev" in current_url or "gymassistantapp.ir" in current_url or "nemovapp.ir" in current_url:
            self.txt_video_url.clear()

        self.lbl_media_status.setText(f"فایل: {os.path.basename(stored_path)}")
        self.lbl_media_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
        self.btn_remove_media.show()

    def record_media(self):
        from nemov.views.components.video_editor_dialog import VideoRecorderAndEditorDialog
        title = self.txt_name.text().strip() or None
        dlg = VideoRecorderAndEditorDialog(self, mode="record", exercise_title=title)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if getattr(dlg, "result_media_type", None) == "image" or getattr(dlg, "result_image_path", None):
                self.media_path = dlg.result_image_path
                self.thumbnail_path = dlg.result_image_path
                self.media_type = "image"
                self.video_cloud_url = None
                current_url = self.txt_video_url.text().strip()
                if "workers.dev" in current_url or "gymassistantapp.ir" in current_url or "nemovapp.ir" in current_url:
                    self.txt_video_url.clear()
                self.btn_edit_media.setText("🎨 ویرایش تصویر")
                self.btn_edit_media.show()
                self.btn_remove_media.show()
                self.lbl_media_status.setText(f"عکس ثبت‌شده: {os.path.basename(self.media_path)}")
                self.lbl_media_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            elif getattr(dlg, "result_video_path", None):
                self.media_path = dlg.result_video_path
                self.thumbnail_path = dlg.result_thumbnail_path
                self.media_type = "video"
                self.video_cloud_url = None
                current_url = self.txt_video_url.text().strip()
                if "workers.dev" in current_url or "gymassistantapp.ir" in current_url or "nemovapp.ir" in current_url:
                    self.txt_video_url.clear()
                self.btn_edit_media.setText("✂️ ویرایش ویدیو")
                self.btn_edit_media.show()
                self.btn_remove_media.show()
                self.lbl_media_status.setText(f"ویدیو ضبط‌شده: {os.path.basename(self.media_path)}")
                self.lbl_media_status.setStyleSheet("color: #4CAF50; font-size: 11px;")

    def edit_media(self):
        from nemov.services.cloud_sync_service import resolve_exercise_media_path
        actual_path = resolve_exercise_media_path(self.media_path) if self.media_path else None
        if not actual_path or not os.path.exists(actual_path):
            QMessageBox.warning(self, "خطا", "فایل رسانه‌ای جهت ویرایش موجود نیست.")
            return

        from nemov.views.components.video_editor_dialog import VideoRecorderAndEditorDialog
        title = self.txt_name.text().strip() or None

        if self.media_type == "video":
            dlg = VideoRecorderAndEditorDialog(self, video_path=actual_path, mode="edit", exercise_title=title)
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_video_path:
                self.media_path = dlg.result_video_path
                self.thumbnail_path = dlg.result_thumbnail_path
                self.video_cloud_url = None
                current_url = self.txt_video_url.text().strip()
                if "workers.dev" in current_url or "gymassistantapp.ir" in current_url or "nemovapp.ir" in current_url:
                    self.txt_video_url.clear()
                self.btn_remove_media.show()
                self.lbl_media_status.setText(f"ویدیو ویرایش‌شده: {os.path.basename(self.media_path)}")
                self.lbl_media_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            dlg = VideoRecorderAndEditorDialog(self, image_path=actual_path, mode="edit_image", exercise_title=title)
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_image_path:
                self.media_path = dlg.result_image_path
                self.thumbnail_path = dlg.result_image_path
                self.video_cloud_url = None
                current_url = self.txt_video_url.text().strip()
                if "workers.dev" in current_url or "gymassistantapp.ir" in current_url or "nemovapp.ir" in current_url:
                    self.txt_video_url.clear()
                self.btn_edit_media.setText("🎨 ویرایش تصویر")
                self.btn_edit_media.show()
                self.btn_remove_media.show()
                self.lbl_media_status.setText(f"تصویر ویرایش‌شده: {os.path.basename(self.media_path)}")
                self.lbl_media_status.setStyleSheet("color: #4CAF50; font-size: 11px;")

    def remove_media(self):
        reply = QMessageBox.question(
            self,
            "حذف رسانه آموزشی حرکت",
            "آیا از حذف عکس یا ویدیوی آموزشی این حرکت اطمینان دارید؟\n\nدر صورت ذخیره تغییرات، این حرکت فاقد رسانه آموزشی خواهد شد.\nنکته: پس از تایید، ۵ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        snapshot = {
            "media_path": self.media_path,
            "media_type": self.media_type,
            "thumbnail_path": self.thumbnail_path,
            "video_cloud_url": self.video_cloud_url,
            "video_url_text": self.txt_video_url.text(),
            "lbl_text": self.lbl_media_status.text(),
            "lbl_style": self.lbl_media_status.styleSheet(),
            "edit_btn_text": self.btn_edit_media.text(),
            "edit_btn_visible": self.btn_edit_media.isVisible(),
        }

        self.media_path = None
        self.media_type = "image"
        self.thumbnail_path = None
        self.video_cloud_url = None
        current_url = self.txt_video_url.text().strip()
        if "workers.dev" in current_url or "gymassistantapp.ir" in current_url or "nemovapp.ir" in current_url:
            self.txt_video_url.clear()
        self.lbl_media_status.setText("فایلی انتخاب نشده است")
        self.lbl_media_status.setStyleSheet("color: #888888; font-size: 11px;")
        self.btn_edit_media.hide()
        self.btn_remove_media.hide()

        def undo_media(items):
            if not items:
                return
            st = items[0]
            self.media_path = st["media_path"]
            self.media_type = st["media_type"]
            self.thumbnail_path = st["thumbnail_path"]
            self.video_cloud_url = st["video_cloud_url"]
            self.txt_video_url.setText(st["video_url_text"])
            self.lbl_media_status.setText(st["lbl_text"])
            self.lbl_media_status.setStyleSheet(st["lbl_style"])
            self.btn_edit_media.setText(st["edit_btn_text"])
            self.btn_edit_media.setVisible(st["edit_btn_visible"] or bool(st["media_path"]))
            self.btn_remove_media.setVisible(bool(st["media_path"]))

        self.undo_banner.start_countdown(
            item_count=1,
            pending_items=[snapshot],
            on_commit=lambda _: None,
            on_undo=undo_media,
            item_label="رسانه آموزشی حرکت",
            duration_seconds=5,
        )

    def save(self):
        if hasattr(self, "undo_banner") and self.undo_banner.timer.isActive():
            self.undo_banner.commit_now()
        name_fa = self.txt_name.text().strip()
        if not name_fa:
            QMessageBox.warning(self, "خطا", "لطفاً نام حرکت ورزشی را وارد کنید.")
            return

        muscle_key = self.combo_muscle.currentData()
        if not muscle_key:
            QMessageBox.warning(self, "خطا", "لطفاً عضله هدف حرکت را از لیست یا روی آدمک انتخاب کنید.")
            return

        # Check duplicate exercise name in bank
        exercises = WorkoutService.get_all_exercises()
        other_names = [ex.name_fa for ex in exercises if not (self.exercise_data and ex.id == self.exercise_data.id) and ex.name_fa]
        if any(n.strip().lower() == name_fa.lower() for n in other_names):
            from nemov.utils.duplicate_helper import get_next_numbered_name
            suggested_name = get_next_numbered_name(name_fa, other_names)
            reply = QMessageBox.question(
                self,
                "هشدار حرکت ورزشی تکراری",
                f"حرکت ورزشی با عنوان «{name_fa}» از قبل در بانک حرکات ورزشی ثبت شده است.\n\nدر صورت تایید، این حرکت با عنوان «{suggested_name}» ذخیره خواهد شد.\nآیا مایل به ذخیره هستید؟",
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
            "primary_muscle": self.combo_muscle.currentData(),
            "equipment": self.combo_equip.currentData(),
            "media_path": self.media_path,
            "media_type": self.media_type,
            "video_url": self.txt_video_url.text().strip() or None,
            "is_corrective": self.chk_corrective.isChecked(),
            "thumbnail_path": self.thumbnail_path,
            "video_cloud_url": getattr(self, "video_cloud_url", None),
            "contraindications": self.txt_contra.text().strip(),
            "description": self.txt_desc.toPlainText().strip()
        }

    def load_data(self):
        from nemov.services.cloud_sync_service import resolve_exercise_media_path
        ex = self.exercise_data
        self.txt_name.setText(ex.name_fa or "")
        
        idx_m = self.combo_muscle.findData(ex.primary_muscle)
        if idx_m >= 0:
            self.combo_muscle.setCurrentIndex(idx_m)
        else:
            self.combo_muscle.setCurrentIndex(0)
        if ex.primary_muscle:
            self.muscle_selector.set_selected_muscle(ex.primary_muscle)
        else:
            self.muscle_selector.clear_selection()

        idx_e = self.combo_equip.findData(ex.equipment)
        if idx_e >= 0: self.combo_equip.setCurrentIndex(idx_e)

        self.txt_contra.setText(ex.contraindications or "")
        raw_video_url = ex.video_url or ""
        if "workers.dev" in raw_video_url:
            import re
            target_base = config.DEFAULT_CLOUD_BACKUP_URL.rstrip("/")
            raw_video_url = re.sub(r"https?://[^/]+\.workers\.dev", target_base, raw_video_url)
        self.txt_video_url.setText(raw_video_url)
        self.txt_desc.setText(ex.description or "")
        self.chk_corrective.setChecked(bool(getattr(ex, "is_corrective", False)))
        self.media_path = ex.media_path
        self.media_type = ex.media_type or "image"
        self.thumbnail_path = getattr(ex, "thumbnail_path", None)
        self.video_cloud_url = getattr(ex, "video_cloud_url", None)

        actual_path = resolve_exercise_media_path(self.media_path) if self.media_path else None
        if actual_path and os.path.exists(actual_path):
            self.media_path = actual_path
            fn = os.path.basename(actual_path)
            if self.video_cloud_url:
                self.lbl_media_status.setText(f"فایل: {fn} (همگام در سرور ☁️)")
            else:
                self.lbl_media_status.setText(f"فایل: {fn}")
            self.lbl_media_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            ext = os.path.splitext(actual_path)[1].lower()
            if self.media_type == "video" or ext in ['.mp4', '.avi', '.mkv', '.webm', '.mov']:
                self.btn_edit_media.setText("✂️ ویرایش ویدیو")
                self.btn_edit_media.show()
            else:
                self.btn_edit_media.setText("🎨 ویرایش تصویر")
                self.btn_edit_media.show()
            self.btn_remove_media.show()
        else:
            self.btn_edit_media.hide()
            self.btn_remove_media.hide()

    def _init_draft_persistence(self):
        import uuid
        from nemov.services.draft_service import DebouncedDraftBinder
        self._baseline_state = self.get_data()
        draft_id = (
            self._draft_data["draft_id"]
            if self._draft_data
            else (f"exercise_form_e{self.exercise_data.id}" if self.exercise_data else f"exercise_form_new_{uuid.uuid4().hex[:8]}")
        )
        self._draft_binder = DebouncedDraftBinder(
            parent=self,
            section="exercise_form",
            section_title="فرم حرکت ورزشی",
            get_payload_fn=self.get_data,
            is_dirty_fn=lambda: (not self._was_saved) and (self.get_data() != self._baseline_state),
            get_meta_fn=self._get_draft_meta,
            draft_id=draft_id,
            debounce_ms=3000,
        )
        if self._draft_data:
            self._restore_draft(self._draft_data)

        for le in (self.txt_name, self.txt_contra, self.txt_video_url):
            le.textChanged.connect(self._draft_binder.schedule)
        self.txt_desc.textChanged.connect(self._draft_binder.schedule)
        self.combo_muscle.currentIndexChanged.connect(self._draft_binder.schedule)
        self.combo_equip.currentIndexChanged.connect(self._draft_binder.schedule)
        self.chk_corrective.stateChanged.connect(self._draft_binder.schedule)
        self.muscle_selector.muscle_changed.connect(lambda *_: self._draft_binder.schedule())

    def _get_draft_meta(self) -> dict:
        d = self.get_data()
        name = d.get("name_fa", "")
        action_lbl = "ویرایش حرکت" if self.exercise_data else "افزودن حرکت"
        title = f"{action_lbl}: {name}" if name else action_lbl
        return {
            "title": title,
            "summary": "بانک حرکات ورزشی",
            "entity_id": self.exercise_data.id if self.exercise_data else None,
        }

    def _restore_draft(self, draft: dict):
        from nemov.services.cloud_sync_service import resolve_exercise_media_path
        payload = draft.get("payload") or {}
        with self._draft_binder.suspended():
            self.txt_name.setText(payload.get("name_fa", "") or "")
            idx_m = self.combo_muscle.findData(payload.get("primary_muscle"))
            self.combo_muscle.setCurrentIndex(idx_m if idx_m >= 0 else 0)
            if payload.get("primary_muscle"):
                self.muscle_selector.set_selected_muscle(payload["primary_muscle"])
            else:
                self.muscle_selector.clear_selection()
            idx_e = self.combo_equip.findData(payload.get("equipment"))
            if idx_e >= 0:
                self.combo_equip.setCurrentIndex(idx_e)
            self.txt_contra.setText(payload.get("contraindications", "") or "")
            self.txt_video_url.setText(payload.get("video_url", "") or "")
            self.txt_desc.setText(payload.get("description", "") or "")
            self.chk_corrective.setChecked(bool(payload.get("is_corrective", False)))
            self.media_path = payload.get("media_path")
            self.media_type = payload.get("media_type") or "image"
            self.thumbnail_path = payload.get("thumbnail_path")
            self.video_cloud_url = payload.get("video_cloud_url")
            actual_path = resolve_exercise_media_path(self.media_path) if self.media_path else None
            if actual_path and os.path.exists(actual_path):
                self.media_path = actual_path
                self.lbl_media_status.setText(f"فایل: {os.path.basename(actual_path)}")
                self.lbl_media_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
                self.btn_edit_media.setVisible(True)
                self.btn_remove_media.setVisible(True)

    def closeEvent(self, event):
        if hasattr(self, "_draft_binder") and not self._was_saved:
            self._draft_binder.flush_now()
        super().closeEvent(event)
class CloudVideoSyncWorker(QThread):
    progress_updated = pyqtSignal(int, int, str)
    sync_finished = pyqtSignal(int, int, list)
    sync_error = pyqtSignal(str)

    def run(self):
        try:
            from nemov.services.cloud_sync_service import sync_all_pending_exercise_videos
            def on_progress(current, total, name):
                self.progress_updated.emit(current, total, name)

            success_count, fail_count, errors = sync_all_pending_exercise_videos(progress_callback=on_progress)
            self.sync_finished.emit(success_count, fail_count, errors)
        except Exception as e:
            self.sync_error.emit(str(e))


class WorkoutLibraryView(QWidget):
    back_requested = pyqtSignal()
    cloud_sync_progress = pyqtSignal(int, int) # (remaining, total)
    cloud_sync_finished = pyqtSignal(int, int) # (success_count, fail_count)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sync_worker = None
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()
        self._apply_theme_style()
        try:
            ThemeManager.theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _on_theme_changed(self, _theme_key: str):
        self._apply_theme_style()

    def _apply_theme_style(self):
        pal = ThemeManager.get_current_palette()
        b_bg, b_fg, b_bd, b_hv = ThemeManager.get_tone_colors("blue", pal)
        if hasattr(self, "btn_cloud_sync"):
            self.btn_cloud_sync.setStyleSheet(f"""
                QPushButton {{
                    background-color: {b_bg};
                    color: {b_fg};
                    font-weight: bold;
                    border: 1px solid {b_bd};
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 12.5px;
                }}
                QPushButton:hover {{
                    background-color: {b_hv};
                    color: #FFFFFF;
                }}
                QPushButton:disabled {{
                    background-color: {pal.btn_sec_bg};
                    color: {pal.text_muted};
                    border: 1px solid {pal.border_light};
                }}
            """)
        if hasattr(self, "btn_toggle_mannequin"):
            self.btn_toggle_mannequin.setStyleSheet(f"""
                QPushButton {{
                    background-color: {pal.btn_sec_bg};
                    color: {pal.btn_sec_text};
                    font-family: "Vazirmatn", "Segoe UI", sans-serif;
                    font-weight: bold;
                    border: 1px solid {pal.btn_sec_border};
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-size: 11.5px;
                }}
                QPushButton:hover {{
                    background-color: {pal.btn_sec_hover};
                    color: {pal.text_primary};
                }}
                QPushButton:!checked {{
                    background-color: {pal.bg_surface};
                    color: {pal.text_secondary};
                    border: 1px solid {pal.border};
                }}
                QPushButton:!checked:hover {{
                    background-color: {pal.btn_sec_hover};
                    color: {pal.text_primary};
                }}
            """)
        if hasattr(self, "btn_bulk_delete"):
            self.btn_bulk_delete.setStyleSheet(ThemeManager.get_bulk_delete_qss(pal))
        if hasattr(self, "anat_filter_frame"):
            self.anat_filter_frame.setStyleSheet(f"""
                QFrame#anatFilterCard {{
                    background-color: {pal.bg_card};
                    border: 1px solid {pal.border};
                    border-radius: 10px;
                }}
            """)
        if hasattr(self, "lbl_anat_head"):
            head_col = pal.primary_hover if pal.is_dark else pal.primary
            self.lbl_anat_head.setStyleSheet(f"color: {head_col}; font-weight: bold; font-size: 13px; background: transparent;")
        if hasattr(self, "lbl_anat_desc"):
            self.lbl_anat_desc.setStyleSheet(f"color: {pal.text_secondary}; font-size: 11px; background: transparent;")
        if hasattr(self, "lbl_filter_stats"):
            self.lbl_filter_stats.setStyleSheet(f"""
                QLabel {{
                    color: {pal.text_primary};
                    font-family: "Vazirmatn", "Segoe UI", sans-serif;
                    font-weight: bold;
                    font-size: 11.5px;
                    background-color: {pal.bg_surface};
                    border: 1px solid {pal.border};
                    border-radius: 6px;
                    padding: 5px 12px;
                }}
            """)
        if hasattr(self, "btn_show_all"):
            self.btn_show_all.setStyleSheet(f"""
                QPushButton {{
                    background-color: {pal.btn_sec_bg};
                    color: {pal.btn_sec_text};
                    font-family: "Vazirmatn", "Segoe UI", sans-serif;
                    border: 1px solid {pal.btn_sec_border};
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {pal.btn_sec_hover};
                    color: {pal.text_primary};
                }}
            """)
        if hasattr(self, "table") and self.table.viewport():
            self.table.viewport().update()

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

        self.btn_cloud_sync = QPushButton("☁️ همگام‌سازی ویدیوها در سرور")
        self.btn_cloud_sync.setObjectName("secondary_button")
        self.btn_cloud_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cloud_sync.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #2563EB;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12.5px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:disabled {
                background-color: #1F2430;
                color: #6B7280;
                border: 1px solid #374151;
            }
        """)
        self.btn_cloud_sync.clicked.connect(self.sync_videos_to_cloud)
        header.addWidget(self.btn_cloud_sync)

        header.addWidget(btn_add)
        layout.addLayout(header)

        # Search Controls
        controls = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("جستجو در نام حرکات...")
        self.txt_search.setMinimumWidth(125)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)
        self.search_timer.timeout.connect(self.load_exercises)
        self.txt_search.textChanged.connect(self.search_timer.start)

        self.combo_muscle = QComboBox()
        self.combo_muscle.addItem("همه عضلات", "all")
        self.combo_muscle.addItem("✨ حرکات اصلاحی", "corrective")
        for m_key, m_info in MUSCLE_DEFINITIONS.items():
            self.combo_muscle.addItem(f"{m_info['name_fa']}", m_key)
        self.combo_muscle.addItem("--- گروه‌های کلی ---", "")
        self.combo_muscle.addItem("سینه (کلی)", "chest")
        self.combo_muscle.addItem("پا و سرینی (کلی)", "legs")
        self.combo_muscle.addItem("پشت و زیربغل (کلی)", "back")
        self.combo_muscle.addItem("سرشانه (کلی)", "shoulders")
        self.combo_muscle.addItem("بازو (کلی)", "arms")
        self.combo_muscle.addItem("شکم و مرکز بدن (کلی)", "abs")
        self.combo_muscle.currentIndexChanged.connect(self._on_filter_muscle_combo_changed)

        self.btn_toggle_mannequin = QPushButton("🧍 مخفی‌سازی آدمک آناتومی")
        self.btn_toggle_mannequin.setCheckable(True)
        self.btn_toggle_mannequin.setChecked(True)
        self.btn_toggle_mannequin.setFixedHeight(32)
        self.btn_toggle_mannequin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_mannequin.toggled.connect(self.toggle_anatomy_filter)

        controls.addWidget(QLabel("جستجو:"))
        controls.addWidget(self.txt_search, 1)
        controls.addWidget(QLabel("عضله هدف:"))
        controls.addWidget(self.combo_muscle)
        controls.addWidget(self.btn_toggle_mannequin)

        self.chk_select_all = QCheckBox("انتخاب همه")
        self.chk_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_select_all.toggled.connect(self.toggle_select_all)

        self.btn_bulk_delete = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete.setFixedHeight(32)
        self.btn_bulk_delete.setEnabled(False)
        self.btn_bulk_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bulk_delete.clicked.connect(self.bulk_delete_exercises)

        controls.addSpacing(10)
        controls.addWidget(self.chk_select_all)
        controls.addWidget(self.btn_bulk_delete)
        layout.addLayout(controls)

        # Anatomy Filter Card Frame (Visual Mannequin above table)
        self.anat_filter_frame = QFrame()
        self.anat_filter_frame.setObjectName("anatFilterCard")
        anat_layout = QHBoxLayout(self.anat_filter_frame)
        anat_layout.setContentsMargins(14, 8, 14, 8)
        anat_layout.setSpacing(16)

        # Right side in RTL: Quick Info & Guidance Card
        vlay_info = QVBoxLayout()
        vlay_info.setSpacing(6)

        self.lbl_anat_head = QLabel("🎯 فیلتر تصویری و هوشمند بر اساس آناتومی بدن")

        self.lbl_anat_desc = QLabel(
            "با کلیک روی هر عضله از بدن آدمک (نمای روبرو یا پشت)، جدول حرکات فوراً بر اساس آن عضله فیلتر می‌شود.\n"
            "برای مشاهده مجدد تمام حرکات، روی دکمه «همه عضلات» کلیک کنید."
        )
        self.lbl_anat_desc.setWordWrap(True)

        self.lbl_filter_stats = QLabel("در حال بارگذاری...")

        self.btn_show_all = QPushButton("نمایش همه عضلات")
        self.btn_show_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_show_all.clicked.connect(self.clear_anatomy_filter)

        row_info_btns = QHBoxLayout()
        row_info_btns.addWidget(self.lbl_filter_stats)
        row_info_btns.addWidget(self.btn_show_all)
        row_info_btns.addStretch()

        vlay_info.addWidget(self.lbl_anat_head)
        vlay_info.addWidget(self.lbl_anat_desc)
        vlay_info.addLayout(row_info_btns)
        vlay_info.addStretch()

        # Left side in RTL: Mannequin widget
        self.anat_selector = MuscleSelectorWidget(self, is_filter_mode=True)
        self.anat_selector.setFixedHeight(225)
        self.anat_selector.setFixedWidth(340)
        self.anat_selector.muscle_changed.connect(self._on_anat_selector_muscle_changed)

        anat_layout.addLayout(vlay_info, 1)
        anat_layout.addWidget(self.anat_selector)

        layout.addWidget(self.anat_filter_frame)

        # Exercises Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "انتخاب", "ردیف", "نام حرکت", "عضله اصلی", "تجهیزات", "محدودیت آسیب‌دیدگی", "توضیحات", "عملیات"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(58)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(40)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 60)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 54)
        self.table.setColumnWidth(2, 195)
        self.table.setColumnWidth(3, 140)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 75)
        self.table.setColumnWidth(5, 130)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 250)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setItemDelegateForColumn(6, TwoLineDescriptionDelegate(self))
        self.table.setItemDelegateForColumn(7, OperationsDelegate(self))
        self.table.viewport().setMouseTracking(True)

        layout.addWidget(self.table, 1)

        self.undo_banner = UndoDeleteBanner(self)
        layout.addWidget(self.undo_banner)

        self.load_exercises()

    def toggle_anatomy_filter(self, checked: bool):
        self.anat_filter_frame.setVisible(checked)
        if checked:
            self.btn_toggle_mannequin.setText("🧍 مخفی‌سازی آدمک آناتومی")
        else:
            self.btn_toggle_mannequin.setText("🧍 نمایش آدمک آناتومی")

    def _on_filter_muscle_combo_changed(self):
        m_key = self.combo_muscle.currentData()
        if hasattr(self, "anat_selector"):
            if m_key and m_key not in ["all", "corrective", ""]:
                self.anat_selector.blockSignals(True)
                self.anat_selector.set_selected_muscle(m_key)
                self.anat_selector.blockSignals(False)
            else:
                self.anat_selector.blockSignals(True)
                self.anat_selector.clear_selection(emit_signal=False)
                self.anat_selector.blockSignals(False)
        self.load_exercises()

    def _on_anat_selector_muscle_changed(self, muscle_key: str, name_fa: str):
        if muscle_key:
            idx = self.combo_muscle.findData(muscle_key)
            if idx >= 0:
                self.combo_muscle.blockSignals(True)
                self.combo_muscle.setCurrentIndex(idx)
                self.combo_muscle.blockSignals(False)
        else:
            self.combo_muscle.blockSignals(True)
            self.combo_muscle.setCurrentIndex(0)
            self.combo_muscle.blockSignals(False)
        self.load_exercises()

    def clear_anatomy_filter(self):
        self.anat_selector.clear_selection(emit_signal=True)

    def load_exercises(self, force: bool = False):
        if hasattr(self, "search_timer") and self.search_timer.isActive():
            self.search_timer.stop()

        if not hasattr(self, "_exercises_filter_cache"):
            self._exercises_filter_cache = {}

        search_query = self.txt_search.text().strip()
        muscle = self.combo_muscle.currentData()
        current_filter = (search_query, muscle)
        if not force and getattr(self, "_last_loaded_filter", None) == current_filter:
            return
        self._last_loaded_filter = current_filter

        if not force and current_filter in self._exercises_filter_cache:
            exercises = self._exercises_filter_cache[current_filter]
        else:
            exercises = WorkoutService.get_all_exercises(muscle_group=muscle, search_query=search_query)
            self._exercises_filter_cache[current_filter] = exercises

        total_count = len(exercises)
        cur_muscle_name = self.combo_muscle.currentText()
        if hasattr(self, "lbl_filter_stats"):
            if muscle == "corrective":
                self.lbl_filter_stats.setText(f"✨ حرکات اصلاحی ({total_count} حرکت)")
            elif muscle and muscle not in ["all", ""]:
                self.lbl_filter_stats.setText(f"🎯 عضله: {cur_muscle_name} | {total_count} حرکت یافت شد")
            else:
                self.lbl_filter_stats.setText(f"📋 تمام حرکات بانک ({total_count} حرکت)")

        muscle_map = {
            "chest": "سینه", "legs": "پا و سرینی", "back": "پشت و زیربغل",
            "shoulders": "سرشانه", "arms": "بازو", "abs": "شکم",
            **{k: v["name_fa"] for k, v in MUSCLE_DEFINITIONS.items()}
        }
        equip_map = {
            "barbell": "هالتر", "dumbbell": "دمبل", "machine": "دستگاه",
            "cable": "سیم‌کش", "bodyweight": "وزن بدن"
        }

        self.chk_select_all.blockSignals(True)
        self.chk_select_all.setChecked(False)
        self.chk_select_all.blockSignals(False)
        self.btn_bulk_delete.setText("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete.setEnabled(False)

        n = len(exercises)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(n)

        for row, ex in enumerate(exercises):
            # Safe Checkbox in column 0 (immune to C++ wrapper deletion)
            chk = None
            try:
                chk_w = self.table.cellWidget(row, 0)
                if chk_w:
                    chk = chk_w.findChild(QCheckBox)
            except (RuntimeError, AttributeError):
                chk_w = None
                chk = None

            if not chk_w or not chk:
                chk_w = QWidget()
                chk_w.setStyleSheet("background: transparent;")
                chk_lay = QHBoxLayout(chk_w)
                chk_lay.setContentsMargins(0, 0, 0, 0)
                chk_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chk = QCheckBox(chk_w)
                chk.setCursor(Qt.CursorShape.PointingHandCursor)
                chk.toggled.connect(self.on_row_checkbox_toggled)
                chk_lay.addWidget(chk)
                self.table.setCellWidget(row, 0, chk_w)

            chk.blockSignals(True)
            chk.setChecked(False)
            chk.setProperty("item_id", ex.id)
            chk.setProperty("item_name", ex.name_fa)
            chk.blockSignals(False)

            # Column 1: Row index (Persian numerals, centered - matches Backup view)
            fa_idx = str(row + 1).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            it_idx = self.table.item(row, 1)
            if not it_idx:
                it_idx = QTableWidgetItem("")
                it_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 1, it_idx)
            it_idx.setText(fa_idx)
            it_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            it_name = self.table.item(row, 2)
            if not it_name:
                it_name = QTableWidgetItem("")
                self.table.setItem(row, 2, it_name)
            it_name.setText(ex.name_fa)
            it_name.setToolTip(ex.name_fa)

            muscle_name = muscle_map.get(ex.primary_muscle, ex.primary_muscle)
            muscle_display = f"{muscle_name} (اصلاحی)" if getattr(ex, "is_corrective", False) else muscle_name
            it_muscle = self.table.item(row, 3)
            if not it_muscle:
                it_muscle = QTableWidgetItem("")
                self.table.setItem(row, 3, it_muscle)
            it_muscle.setText(muscle_display)
            it_muscle.setToolTip(muscle_display)

            eq_txt = equip_map.get(ex.equipment, ex.equipment or "-")
            it_equip = self.table.item(row, 4)
            if not it_equip:
                it_equip = QTableWidgetItem("")
                it_equip.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, it_equip)
            it_equip.setText(eq_txt)
            it_equip.setToolTip(eq_txt)

            raw_contra = ex.contraindications or "-"
            contra_map = {
                "wrist_injury": "آسیب مچ دست",
                "elbow_injury": "آسیب آرنج",
                "shoulder_injury": "آسیب سرشانه",
                "knee_injury": "آسیب زانو",
                "back_injury": "آسیب کمر",
                "neck_injury": "آسیب گردن",
                "ankle_injury": "آسیب مچ پا",
                "hip_injury": "آسیب لگن",
                "none": "-",
                "-": "-"
            }
            if raw_contra and raw_contra != "-":
                parts = [p.strip() for p in raw_contra.replace("،", ",").split(",") if p.strip()]
                contra_txt = "، ".join(contra_map.get(p, p) for p in parts)
            else:
                contra_txt = "-"

            it_contra = self.table.item(row, 5)
            if not it_contra:
                it_contra = QTableWidgetItem("")
                it_contra.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 5, it_contra)
            it_contra.setText(contra_txt)
            it_contra.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if ex.contraindications:
                it_contra.setToolTip(contra_txt)

            desc_txt = ex.description or "-"
            it_desc = self.table.item(row, 6)
            if not it_desc:
                it_desc = QTableWidgetItem("")
                self.table.setItem(row, 6, it_desc)
            it_desc.setText(desc_txt)
            if ex.description:
                it_desc.setToolTip(desc_txt)

            # Column 7: Operations delegate data
            it7 = self.table.item(row, 7)
            if not it7:
                it7 = QTableWidgetItem()
                self.table.setItem(row, 7, it7)
            it7.setData(Qt.ItemDataRole.UserRole, ex)
            it7.setData(Qt.ItemDataRole.UserRole + 1, bool(getattr(ex, "video_cloud_url", None)))

        self.table.setUpdatesEnabled(True)

        if force or not hasattr(self, "_sync_state_initialized"):
            self._sync_state_initialized = True
            self.update_sync_button_state()

    def reload_exercises(self):
        if hasattr(self, "_exercises_filter_cache"):
            self._exercises_filter_cache.clear()
        self._sync_state_initialized = False
        self.load_exercises(force=True)

    def update_sync_button_state(self):
        if not hasattr(self, "btn_cloud_sync"):
            return
        from nemov.services.cloud_sync_service import get_pending_sync_count
        pending_count = get_pending_sync_count()
        if pending_count > 0:
            fa_count = str(pending_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.btn_cloud_sync.setText(f"☁️ همگام‌سازی رسانه‌ها ({fa_count} جدید)")
            self.btn_cloud_sync.setToolTip(f"{fa_count} رسانه محلی (فیلم یا عکس) هنوز در سرور آپلود نشده است. برای همگام‌سازی کلیک کنید.")
            self.btn_cloud_sync.setEnabled(True)
        else:
            self.btn_cloud_sync.setText("☁️ تمام رسانه‌ها همگام هستند")
            self.btn_cloud_sync.setToolTip("تمام ویدیوها و تصاویر موجود در برنامه در سرور همگام‌سازی شده‌اند.")
            self.btn_cloud_sync.setEnabled(False)

    def toggle_select_all(self, checked):
        for r in range(self.table.rowCount()):
            cell_w = self.table.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(checked)
                    chk.blockSignals(False)
        self.on_row_checkbox_toggled()

    def on_row_checkbox_toggled(self):
        count = len(self.get_selected_exercise_ids())
        total = self.table.rowCount()
        self.chk_select_all.blockSignals(True)
        self.chk_select_all.setChecked(count == total if total > 0 else False)
        self.chk_select_all.blockSignals(False)

        if count > 0:
            fa_num = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.btn_bulk_delete.setText(f"🗑️ حذف انتخاب‌شده‌ها ({fa_num})")
            self.btn_bulk_delete.setEnabled(True)
        else:
            self.btn_bulk_delete.setText("🗑️ حذف انتخاب‌شده‌ها")
            self.btn_bulk_delete.setEnabled(False)

    def get_selected_exercise_ids(self):
        selected_ids = []
        for r in range(self.table.rowCount()):
            cell_w = self.table.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    selected_ids.append(chk.property("item_id"))
        return selected_ids

    def bulk_delete_exercises(self):
        selected_ids = self.get_selected_exercise_ids()
        if not selected_ids:
            return

        count = len(selected_ids)
        fa_count = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        reply = QMessageBox.question(
            self, "تایید حذف گروهی",
            f"آیا از حذف {fa_count} حرکت ورزشی انتخاب‌شده اطمینان دارید؟\n\nنکته: پس از تایید، ۵ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_rows_by_ids(selected_ids)

        def commit_delete(ids):
            for eid in ids:
                WorkoutService.delete_exercise(eid)
            self.reload_exercises()

        def undo_delete(ids):
            self.reload_exercises()
            QMessageBox.information(self, "بازگردانی", "حرکات ورزشی با موفقیت بازگردانده شدند.")

        self.undo_banner.start_countdown(count, selected_ids, commit_delete, undo_delete, "حرکت ورزشی")

    def _hide_rows_by_ids(self, ids_to_hide):
        ids_set = set(ids_to_hide)
        for r in range(self.table.rowCount() - 1, -1, -1):
            cell_w = self.table.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.property("item_id") in ids_set:
                    self.table.hideRow(r)
        self.btn_bulk_delete.setText("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete.setEnabled(False)
        self.chk_select_all.setChecked(False)

    def show_media(self, exercise):
        target_video = exercise.video_cloud_url or exercise.video_url
        if target_video and "workers.dev" in target_video:
            import re
            target_video = re.sub(r"https?://[^/]+\.workers\.dev", config.DEFAULT_CLOUD_BACKUP_URL.rstrip("/"), target_video)
        dlg = MediaViewerDialog(
            title=exercise.name_fa,
            media_path=exercise.media_path,
            media_type=exercise.media_type,
            video_url=target_video,
            parent=self
        )
        dlg.exec()

    def delete_exercise(self, exercise):
        reply = QMessageBox.question(
            self, "تایید حذف حرکت",
            f"آیا از حذف حرکت '{exercise.name_fa}' از بانک حرکات اطمینان دارید؟\n\nنکته: پس از تایید، ۵ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._hide_rows_by_ids([exercise.id])
            self.undo_banner.start_countdown(
                1, [exercise.id],
                on_commit=lambda ids: [WorkoutService.delete_exercise(eid) for eid in ids] and self.reload_exercises(),
                on_undo=lambda ids: self.reload_exercises(),
                item_label="حرکت ورزشی"
            )

    def open_add_dialog(self):
        dlg = ExerciseFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            WorkoutService.create_exercise(data)
            self.reload_exercises()
            QMessageBox.information(self, "موفقیت", "حرکت جدید به بانک افزوده شد.")

    def open_edit_dialog(self, exercise):
        dlg = ExerciseFormDialog(self, exercise_data=exercise)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            WorkoutService.update_exercise(exercise.id, data)
            self.reload_exercises()
            QMessageBox.information(self, "موفقیت", "حرکت ورزشی با موفقیت ویرایش شد.")

    def sync_videos_to_cloud(self):
        from nemov.services.cloud_sync_service import (
            check_internet_connection,
            get_pending_sync_count
        )

        # 1. Check if sync is already running
        if self.sync_worker and self.sync_worker.isRunning():
            QMessageBox.information(self, "همگام‌سازی", "عملیات همگام‌سازی رسانه‌ها در پس‌زمینه در حال اجراست.")
            return

        # 2. Check internet connectivity first
        if not check_internet_connection():
            QMessageBox.warning(
                self,
                "عدم اتصال به اینترنت",
                "❌ دستگاه شما به اینترنت متصل نیست!\n\n"
                "برای آپلود و همگام‌سازی ویدیوها و تصاویر در سرور، لطفاً ابتدا اتصال اینترنت خود را بررسی نمایید.\n"
                "پس از برقراری ارتباط اینترنت، مجدداً روی این دکمه کلیک کنید تا عملیات همگام‌سازی بدون مشکل انجام شود."
            )
            return

        # 3. Check pending sync count
        pending_count = get_pending_sync_count()
        if pending_count == 0:
            QMessageBox.information(
                self,
                "همگام‌سازی ابری",
                "تمام ویدیوها و تصاویر موجود در برنامه از قبل در سرور همگام‌سازی شده‌اند و رسانه جدیدی وجود ندارد."
            )
            self.update_sync_button_state()
            return

        fa_count = str(pending_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        reply = QMessageBox.question(
            self, "همگام‌سازی رسانه‌ها در سرور",
            f"تعداد {fa_count} رسانه جدید (ویدیو یا تصویر) جهت آپلود در سرور آماده است.\n\n"
            "آیا مایلید عملیات آپلود و همگام‌سازی آنلاین آغاز شود؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Set button state to syncing (non-blocking)
        self.btn_cloud_sync.setEnabled(False)
        self.btn_cloud_sync.setText("☁️ در حال همگام‌سازی...")

        # Initialize sidebar progress bar immediately
        self.cloud_sync_progress.emit(pending_count, pending_count)

        # Launch background worker
        self.sync_worker = CloudVideoSyncWorker(self)
        self.sync_worker.progress_updated.connect(self._on_sync_progress_update)
        self.sync_worker.sync_finished.connect(self._on_sync_worker_finished)
        self.sync_worker.sync_error.connect(self._on_sync_worker_error)
        self.sync_worker.start()

    def _on_sync_progress_update(self, current: int, total: int, name: str):
        remaining = max(1, total - current + 1)
        self.cloud_sync_progress.emit(remaining, total)

    def _on_sync_worker_finished(self, success_count: int, fail_count: int, errors: list):
        self.reload_exercises()
        self.cloud_sync_finished.emit(success_count, fail_count)
        if errors and fail_count > 0:
            QMessageBox.warning(
                self, "گزارش همگام‌سازی ابری",
                f"عملیات همگام‌سازی پایان یافت.\n\n"
                f"✅ موفق: {success_count} رسانه\n"
                f"❌ ناموفق: {fail_count} رسانه\n\n"
                f"خطاها:\n" + "\n".join(errors[:4])
            )
        elif success_count > 0:
            fa_count = str(success_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            QMessageBox.information(
                self, "همگام‌سازی موفق",
                f"✅ تعداد {fa_count} رسانه آموزشی (فیلم یا عکس) با موفقیت در سرور آپلود شد و لینک‌های آنلاین به‌روزرسانی شدند."
            )

    def _on_sync_worker_error(self, err_msg: str):
        self.reload_exercises()
        self.cloud_sync_finished.emit(0, 1)
        QMessageBox.critical(self, "خطا در همگام‌سازی", f"خطایی در حین ارسال اطلاعات رخ داد: {err_msg}")


