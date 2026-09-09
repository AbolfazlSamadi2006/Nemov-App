import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QTextEdit, QPushButton,
    QMessageBox, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QLineEdit, QFileDialog, QScrollArea,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFrame
)
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QTimer
from yalda.services.member_service import MemberService


class ZoomableGraphicsView(QGraphicsView):
    """
    Custom QGraphicsView supporting smooth mouse wheel zooming and click-and-drag panning.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(self.renderHints())
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("background-color: #181818; border: 1px solid #2C2C2C; border-radius: 8px;")

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            self.scale(0.85, 0.85)


class MedicalDocumentViewerDialog(QDialog):
    """
    Advanced viewer dialog for medical document images with:
    - Multi-page navigation (Next/Prev buttons & page indicator)
    - Interactive Zooming (Zoom In, Zoom Out, Reset, Fit View, Mouse Wheel)
    - Click-and-drag Panning
    """
    def __init__(self, title: str, file_paths: list, notes: str = None, parent=None):
        super().__init__(parent)
        self.title_str = title
        self.file_paths = [p for p in file_paths if p and os.path.exists(p)]
        self.notes_str = notes
        self.current_index = 0

        self.setWindowTitle(f"مشاهده مدرک پزشکی: {title}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(850, 680)
        self.init_ui()
        self.load_current_page()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(40, self.fit_in_view)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header Row: Title & Page Indicator
        header = QHBoxLayout()
        lbl_title = QLabel(f"📑 {self.title_str}")
        lbl_title.setObjectName("h2")

        self.lbl_page_info = QLabel("صفحه ۱ از ۱")
        self.lbl_page_info.setStyleSheet("font-size: 13px; font-weight: bold; color: #10B981; background: #1E293B; padding: 4px 12px; border-radius: 12px;")

        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(self.lbl_page_info)
        layout.addLayout(header)

        # Toolbar Row: Zoom & Page Navigation Controls
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #222222; border-radius: 8px; padding: 4px;")
        layout_tool = QHBoxLayout(toolbar)
        layout_tool.setSpacing(8)

        # Zoom Controls
        btn_zoom_in = QPushButton("🔍➕ بزرگ‌نمایی")
        btn_zoom_in.setObjectName("secondary_button")
        btn_zoom_in.clicked.connect(self.zoom_in)

        btn_zoom_out = QPushButton("🔍➖ کوچک‌نمایی")
        btn_zoom_out.setObjectName("secondary_button")
        btn_zoom_out.clicked.connect(self.zoom_out)

        btn_zoom_fit = QPushButton("↔️ تنظیم در کادر")
        btn_zoom_fit.setObjectName("secondary_button")
        btn_zoom_fit.clicked.connect(self.fit_in_view)

        # Navigation Controls
        self.btn_prev = QPushButton("◀️ صفحه قبلی")
        self.btn_prev.setObjectName("secondary_button")
        self.btn_prev.clicked.connect(self.prev_page)

        self.btn_next = QPushButton("صفحه بعدی ▶️")
        self.btn_next.setObjectName("secondary_button")
        self.btn_next.clicked.connect(self.next_page)

        layout_tool.addWidget(btn_zoom_in)
        layout_tool.addWidget(btn_zoom_out)
        layout_tool.addWidget(btn_zoom_fit)
        layout_tool.addSpacing(15)
        layout_tool.addWidget(self.btn_prev)
        layout_tool.addWidget(self.btn_next)
        layout_tool.addStretch()

        layout.addWidget(toolbar)

        # Graphics View Area for Image Display
        self.scene = QGraphicsScene(self)
        self.view = ZoomableGraphicsView(self)
        self.view.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        layout.addWidget(self.view)

        # Notes Row (if any)
        if self.notes_str:
            lbl_notes = QLabel(f"💬 توضیحات مربی: {self.notes_str}")
            lbl_notes.setWordWrap(True)
            lbl_notes.setStyleSheet("color: #DDDDDD; font-size: 12px; background-color: #1E1E1E; padding: 8px 12px; border-radius: 6px;")
            layout.addWidget(lbl_notes)

        # Footer Row with Close Button
        footer = QHBoxLayout()
        btn_close = QPushButton("بستن")
        btn_close.setObjectName("secondary_button")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)

        footer.addStretch()
        footer.addWidget(btn_close)
        layout.addLayout(footer)

        # Shortcuts for Next/Prev page
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.next_page)

    def load_current_page(self):
        if not self.file_paths:
            self.lbl_page_info.setText("هیچ فایلی یافت نشد")
            self.scene.clear()
            lbl_err = self.scene.addText("❌ فایل مدرک در مسیر ذخیره‌شده یافت نشد.")
            lbl_err.setDefaultTextColor(Qt.GlobalColor.red)
            return

        current_path = self.file_paths[self.current_index]
        pixmap = QPixmap(current_path)

        if not pixmap.isNull():
            self.pixmap_item.setPixmap(pixmap)
            self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            QTimer.singleShot(20, self.fit_in_view)
        else:
            self.scene.clear()
            lbl_err = self.scene.addText(f"❌ امکان خواندن فایل صفحه {self.current_index + 1} وجود ندارد.")
            lbl_err.setDefaultTextColor(Qt.GlobalColor.red)

        total = len(self.file_paths)
        self.lbl_page_info.setText(f"صفحه {self.current_index + 1} از {total}")
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < total - 1)

    def zoom_in(self):
        self.view.scale(1.25, 1.25)

    def zoom_out(self):
        self.view.scale(0.8, 0.8)

    def fit_in_view(self):
        self.view.resetTransform()
        if self.pixmap_item and self.pixmap_item.pixmap() and not self.pixmap_item.pixmap().isNull():
            self.view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def prev_page(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_page()

    def next_page(self):
        if self.current_index < len(self.file_paths) - 1:
            self.current_index += 1
            self.load_current_page()


class AddMedicalDocumentDialog(QDialog):
    """
    Dialog for adding medical documents with support for multiple pages/photos per document.
    """
    def __init__(self, member_id: int, parent=None):
        super().__init__(parent)
        self.member_id = member_id
        self.selected_files = []  # List of selected file paths
        self.setWindowTitle("افزودن مدرک / آزمایش پزشکی جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(520, 480)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title Input
        lbl_title = QLabel("عنوان مدرک یا آزمایش:")
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("مثلاً: آزمایش خون کامل CBC (۲ صفحه)، MRI زانو...")

        # File Selection Area
        lbl_file = QLabel("فایل‌ها / عکس‌های مدرک پزشکی:")
        
        row_file_btn = QHBoxLayout()
        btn_choose = QPushButton("📂 انتخاب عکس‌ها / صفحات مدرک")
        btn_choose.setObjectName("secondary_button")
        btn_choose.clicked.connect(self.choose_files)
        row_file_btn.addWidget(btn_choose)
        row_file_btn.addStretch()

        # Selected Pages Table
        self.table_pages = QTableWidget(0, 3)
        self.table_pages.setHorizontalHeaderLabels(["صفحه", "نام فایل", "حذف"])
        self.table_pages.verticalHeader().setVisible(False)
        self.table_pages.verticalHeader().setDefaultSectionSize(44)
        
        header_p = self.table_pages.horizontalHeader()
        header_p.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_pages.setColumnWidth(0, 80)
        header_p.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_p.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table_pages.setColumnWidth(2, 65)

        # Notes Input
        lbl_notes = QLabel("توضیحات تکمیلی مربی (اختیاری):")
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("توضیحات مربی در مورد نتیجه آزمایش یا مدرک...")
        self.txt_notes.setMaximumHeight(65)

        layout.addWidget(lbl_title)
        layout.addWidget(self.txt_title)
        layout.addWidget(lbl_file)
        layout.addLayout(row_file_btn)
        layout.addWidget(self.table_pages)
        layout.addWidget(lbl_notes)
        layout.addWidget(self.txt_notes)

        # Buttons Row
        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 ثبت و ذخیره مدرک")
        btn_save.setFixedHeight(38)
        btn_save.clicked.connect(self.save)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(38)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def choose_files(self):
        from yalda.utils.image_source_chooser import ImageSourceChoiceDialog
        choice_dlg = ImageSourceChoiceDialog(self, title="انتخاب روش افزودن مدرک پزشکی")
        if choice_dlg.exec() == QDialog.DialogCode.Accepted:
            choice = choice_dlg.selected_choice
            if choice == 'file':
                filepaths, _ = QFileDialog.getOpenFileNames(
                    self,
                    "انتخاب یک یا چند عکس/صفحه برای مدرک پزشکی",
                    "",
                    "تصاویر و مدارک (*.png *.jpg *.jpeg *.bmp *.webp *.pdf *.gif)"
                )
                if filepaths:
                    for p in filepaths:
                        if p not in self.selected_files:
                            self.selected_files.append(p)
                    self.refresh_pages_table()
            elif choice == 'camera':
                from yalda.views.camera_dialog import CameraCaptureDialog
                cam_dlg = CameraCaptureDialog(self, title="عکس‌برداری از مدرک پزشکی با دوربین")
                if cam_dlg.exec() == QDialog.DialogCode.Accepted:
                    p = cam_dlg.captured_file_path
                    if p and p not in self.selected_files:
                        self.selected_files.append(p)
                        self.refresh_pages_table()

    def refresh_pages_table(self):
        self.table_pages.setRowCount(0)
        for idx, filepath in enumerate(self.selected_files, start=1):
            row = self.table_pages.rowCount()
            self.table_pages.insertRow(row)

            item_page = QTableWidgetItem(f"صفحه {idx}")
            item_page.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_name = QTableWidgetItem(os.path.basename(filepath))
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف این صفحه")
            btn_del.setFixedSize(32, 30)
            btn_del.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 6px; font-size: 12px;")
            btn_del.clicked.connect(lambda _, path=filepath: self.remove_file(path))

            del_widget = QWidget()
            del_widget.setStyleSheet("background: transparent;")
            del_layout = QHBoxLayout(del_widget)
            del_layout.setContentsMargins(0, 0, 0, 0)
            del_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            del_layout.addWidget(btn_del)

            self.table_pages.setItem(row, 0, item_page)
            self.table_pages.setItem(row, 1, item_name)
            self.table_pages.setCellWidget(row, 2, del_widget)

    def remove_file(self, filepath: str):
        if filepath in self.selected_files:
            self.selected_files.remove(filepath)
            self.refresh_pages_table()

    def save(self):
        title = self.txt_title.text().strip()
        if not title:
            QMessageBox.warning(self, "خطا", "لطفاً عنوان مدرک یا آزمایش را وارد کنید.")
            return

        if not self.selected_files:
            QMessageBox.warning(self, "خطا", "لطفاً حداقل یک عکس یا صفحه برای مدرک پزشکی انتخاب کنید.")
            return

        try:
            notes = self.txt_notes.toPlainText().strip()
            MemberService.add_medical_document(self.member_id, title, self.selected_files, notes)
            QMessageBox.information(self, "موفقیت", f"مدرک پزشکی '{title}' با {len(self.selected_files)} صفحه با موفقیت ثبت شد.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ثبت مدرک: {str(e)}")


class HealthRecordView(QWidget):
    def __init__(self, member_id: int, parent=None):
        super().__init__(parent)
        self.member_id = member_id
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()
        self.load_data()
        self.load_documents()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area Container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Medical History Group
        group_med = QGroupBox("📋 سابقه پزشکی و بیماری‌های خاص")
        layout_med = QVBoxLayout(group_med)
        
        row_cb = QHBoxLayout()
        self.cb_hypertension = QCheckBox("فشار خون بالا")
        self.cb_diabetes = QCheckBox("دیابت")
        self.cb_heart = QCheckBox("مشکلات قلبی-عروقی")
        row_cb.addWidget(self.cb_hypertension)
        row_cb.addWidget(self.cb_diabetes)
        row_cb.addWidget(self.cb_heart)
        layout_med.addLayout(row_cb)

        layout_med.addWidget(QLabel("توضیحات سایر بیماری‌ها:"))
        self.txt_other_med = QTextEdit()
        self.txt_other_med.setMaximumHeight(60)
        layout_med.addWidget(self.txt_other_med)
        layout.addWidget(group_med)

        # Injury History Group
        group_inj = QGroupBox("⚠️ سابقه آسیب‌دیدگی مفاصل و عضلات")
        layout_inj = QVBoxLayout(group_inj)

        row_inj1 = QHBoxLayout()
        self.txt_knee = QTextEdit()
        self.txt_knee.setPlaceholderText("مثلاً: آسیب رباط صلیبی زانوی راست...")
        self.txt_knee.setMaximumHeight(50)
        
        self.txt_back = QTextEdit()
        self.txt_back.setPlaceholderText("مثلاً: فتق دیسک مهره L4-L5...")
        self.txt_back.setMaximumHeight(50)

        row_inj1.addWidget(QLabel("آسیب زانو:"))
        row_inj1.addWidget(self.txt_knee)
        row_inj1.addWidget(QLabel("دیسک و کمر:"))
        row_inj1.addWidget(self.txt_back)
        layout_inj.addLayout(row_inj1)

        row_inj2 = QHBoxLayout()
        self.txt_shoulder = QTextEdit()
        self.txt_shoulder.setPlaceholderText("مثلاً: التهاب تاندون شانه چپ...")
        self.txt_shoulder.setMaximumHeight(50)

        self.txt_wrist = QTextEdit()
        self.txt_wrist.setPlaceholderText("مثلاً: سندروم تونل کارپال مچ...")
        self.txt_wrist.setMaximumHeight(50)

        row_inj2.addWidget(QLabel("آسیب شانه:"))
        row_inj2.addWidget(self.txt_shoulder)
        row_inj2.addWidget(QLabel("آسیب مچ:"))
        row_inj2.addWidget(self.txt_wrist)
        layout_inj.addLayout(row_inj2)

        layout.addWidget(group_inj)

        # Limitations & Warnings
        group_lim = QGroupBox("🛑 محدودیت‌های ورزشی و هشدارهای مربی")
        layout_lim = QVBoxLayout(group_lim)
        
        self.txt_limitations = QTextEdit()
        self.txt_limitations.setPlaceholderText("حرکاتی که به هیچ عنوان نباید تجویز شوند...")
        self.txt_limitations.setMaximumHeight(60)
        
        layout_lim.addWidget(QLabel("محدودیت‌های صریح حرکتی:"))
        layout_lim.addWidget(self.txt_limitations)
        layout.addWidget(group_lim)

        # Save & Revert Health Record Buttons
        row_save = QHBoxLayout()
        row_save.setSpacing(12)

        btn_save = QPushButton("💾 ثبت و بروزرسانی سوابق پزشکی")
        btn_save.setFixedHeight(40)
        btn_save.clicked.connect(self.save_data)
        row_save.addWidget(btn_save)

        btn_reset = QPushButton("🔄 بازنشانی / لغو تغییرات")
        btn_reset.setFixedHeight(40)
        btn_reset.setObjectName("secondary_button")
        btn_reset.clicked.connect(self.load_data)
        row_save.addWidget(btn_reset)
        row_save.addStretch()

        layout.addLayout(row_save)

        # Medical Documents & Tests Group
        group_docs = QGroupBox("📁 اسناد، آزمایش‌ها و مدارک پزشکی ثبت‌شده")
        layout_docs = QVBoxLayout(group_docs)

        row_docs_top = QHBoxLayout()
        self.lbl_docs_count = QLabel("مدارک پزشکی ثبت‌شده:")
        self.lbl_docs_count.setStyleSheet("font-weight: bold;")

        btn_export_zip = QPushButton("📦 خروجی مدارک و نظرات (ZIP)")
        btn_export_zip.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        btn_export_zip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_zip.setFixedHeight(36)
        btn_export_zip.setFixedWidth(230)
        btn_export_zip.clicked.connect(self.export_medical_package)

        btn_add_doc = QPushButton("➕ افزودن مدرک / آزمایش جدید")
        btn_add_doc.setObjectName("secondary_button")
        btn_add_doc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_doc.setFixedHeight(36)
        btn_add_doc.setFixedWidth(230)
        btn_add_doc.clicked.connect(self.open_add_doc_dialog)

        row_docs_top.addWidget(self.lbl_docs_count)
        row_docs_top.addStretch()
        row_docs_top.addWidget(btn_export_zip)
        row_docs_top.addWidget(btn_add_doc)
        layout_docs.addLayout(row_docs_top)

        # Table for Medical Documents
        self.table_docs = QTableWidget(0, 5)
        self.table_docs.setHorizontalHeaderLabels(["عنوان مدرک / آزمایش", "تاریخ ثبت", "توضیحات تکمیلی", "مشاهده مدرک", "حذف"])
        self.table_docs.verticalHeader().setDefaultSectionSize(45)
        self.table_docs.setMinimumHeight(200)

        header_d = self.table_docs.horizontalHeader()
        header_d.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table_docs.setColumnWidth(0, 220)
        header_d.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table_docs.setColumnWidth(1, 100)
        header_d.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_d.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table_docs.setColumnWidth(3, 110)
        header_d.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table_docs.setColumnWidth(4, 70)

        layout_docs.addWidget(self.table_docs)
        layout.addWidget(group_docs)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

    def load_data(self):
        rec = MemberService.get_health_record(self.member_id)
        if rec:
            self.cb_hypertension.setChecked(rec.has_hypertension or False)
            self.cb_diabetes.setChecked(rec.has_diabetes or False)
            self.cb_heart.setChecked(rec.has_heart_issue or False)
            self.txt_other_med.setText(rec.other_medical or "")
            self.txt_knee.setText(rec.knee_injury or "")
            self.txt_back.setText(rec.back_injury or "")
            self.txt_shoulder.setText(rec.shoulder_injury or "")
            self.txt_wrist.setText(rec.wrist_injury or "")
            self.txt_limitations.setText(rec.exercise_limitations or "")

    def load_documents(self):
        docs = MemberService.get_medical_documents(self.member_id)
        self.lbl_docs_count.setText(f"مدارک پزشکی ثبت‌شده: ({len(docs)} مورد)")
        self.table_docs.setRowCount(0)

        for doc in docs:
            row = self.table_docs.rowCount()
            self.table_docs.insertRow(row)

            pages_count = len(doc.file_paths_list)
            title_text = f"{doc.title} ({pages_count} صفحه)" if pages_count > 1 else doc.title

            # Title
            item_title = QTableWidgetItem(title_text)
            item_title.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Date
            item_date = QTableWidgetItem(doc.created_at_shamsi or "-")
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Notes
            item_notes = QTableWidgetItem(doc.notes or "-")
            item_notes.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # View Media Button
            btn_view = QPushButton("👁️ مشاهده")
            btn_view.setFixedWidth(90)
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.clicked.connect(lambda _, d=doc: self.view_document(d))

            # Delete Button
            btn_del = QPushButton("🗑️")
            btn_del.setObjectName("danger_button")
            btn_del.setFixedWidth(50)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(lambda _, d=doc: self.delete_document(d.id))

            self.table_docs.setItem(row, 0, item_title)
            self.table_docs.setItem(row, 1, item_date)
            self.table_docs.setItem(row, 2, item_notes)
            self.table_docs.setCellWidget(row, 3, btn_view)
            self.table_docs.setCellWidget(row, 4, btn_del)

    def open_add_doc_dialog(self):
        dlg = AddMedicalDocumentDialog(self.member_id, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_documents()

    def view_document(self, doc):
        paths = doc.file_paths_list
        if not paths:
            QMessageBox.warning(self, "خطا", "هیچ فایلی برای این مدرک ثبت نشده است.")
            return

        dlg = MedicalDocumentViewerDialog(doc.title, paths, doc.notes, self)
        dlg.exec()

    def delete_document(self, doc_id: int):
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            "آیا از حذف این مدرک پزشکی اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            MemberService.delete_medical_document(doc_id)
            self.load_documents()
            QMessageBox.information(self, "موفقیت", "مدرک پزشکی با موفقیت حذف شد.")

    def save_data(self):
        data = {
            "has_hypertension": self.cb_hypertension.isChecked(),
            "has_diabetes": self.cb_diabetes.isChecked(),
            "has_heart_issue": self.cb_heart.isChecked(),
            "other_medical": self.txt_other_med.toPlainText().strip(),
            "knee_injury": self.txt_knee.toPlainText().strip(),
            "back_injury": self.txt_back.toPlainText().strip(),
            "shoulder_injury": self.txt_shoulder.toPlainText().strip(),
            "wrist_injury": self.txt_wrist.toPlainText().strip(),
            "exercise_limitations": self.txt_limitations.toPlainText().strip()
        }
        MemberService.update_health_record(self.member_id, data)
        QMessageBox.information(self, "موفقیت", "پرونده سلامت با موفقیت ذخیره شد.")

    def export_medical_package(self):
        import zipfile
        import re
        from yalda.utils.jalali_date import get_today_shamsi

        member = MemberService.get_member_by_id(self.member_id)
        if not member:
            QMessageBox.warning(self, "خطا", "اطلاعات ورزشکار یافت نشد.")
            return

        rec = MemberService.get_health_record(self.member_id)
        docs = MemberService.get_medical_documents(self.member_id)

        default_filename = f"پرونده_{member.full_name}.zip"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره پکیج مدارک و نظرات پزشکی",
            default_filename,
            "ZIP Files (*.zip)"
        )
        if not save_path:
            return

        try:
            with zipfile.ZipFile(save_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
                lines = []
                lines.append("=" * 60)
                lines.append("پرونده پزشکی، سوابق آسیب‌دیدگی و نظرات مربی باشگاه بدنسازی یلدا")
                lines.append("=" * 60)
                lines.append(f"نام و نام خانوادگی ورزشکار: {member.full_name}")
                lines.append(f"کد عضویت: {member.id}")
                lines.append(f"شماره تماس: {member.phone or '-'}")
                lines.append(f"تاریخ گزارش: {get_today_shamsi()}")
                lines.append("-" * 60)
                lines.append("◄ وضعیت بیماری‌های زمینه‌ای:")
                lines.append(f"  • فشار خون بالا: {'بله' if rec and rec.has_hypertension else 'خیر'}")
                lines.append(f"  • دیابت: {'بله' if rec and rec.has_diabetes else 'خیر'}")
                lines.append(f"  • بیماری قلبی-عروقی: {'بله' if rec and rec.has_heart_issue else 'خیر'}")
                lines.append(f"  • سایر بیماری‌ها، حساسیت‌ها یا داروهای خاص: {(rec.other_medical if rec and rec.other_medical else 'موردی ثبت نشده است')}")
                lines.append("")
                lines.append("◄ سوابق آسیب‌دیدگی‌های مفصلی و اسکلتی-عضلانی:")
                lines.append(f"  • آسیب زانو: {(rec.knee_injury if rec and rec.knee_injury else 'موردی ثبت نشده است')}")
                lines.append(f"  • دیسک، ستون فقرات و کمر: {(rec.back_injury if rec and rec.back_injury else 'موردی ثبت نشده است')}")
                lines.append(f"  • آسیب شانه و کتف: {(rec.shoulder_injury if rec and rec.shoulder_injury else 'موردی ثبت نشده است')}")
                lines.append(f"  • آسیب مچ و دست: {(rec.wrist_injury if rec and rec.wrist_injury else 'موردی ثبت نشده است')}")
                lines.append("")
                lines.append("◄ محدودیت‌های صریح حرکتی و هشدارهای مربی:")
                lines.append(f"  {(rec.exercise_limitations if rec and rec.exercise_limitations else 'محدودیت خاصی توسط مربی ثبت نشده است')}")
                lines.append("")
                lines.append("=" * 60)
                lines.append(f"◄ لیست اسناد، آزمایش‌ها و مدارک پزشکی پیوست شده (تعداد کل مدارک: {len(docs)}):")
                lines.append("=" * 60)

                doc_idx = 1
                for doc in docs:
                    lines.append(f"{doc_idx}. عنوان مدرک: {doc.title}")
                    lines.append(f"   تاریخ ثبت: {doc.created_at_shamsi or '-'}")
                    lines.append(f"   تعداد صفحات / عکس‌ها: {len(doc.file_paths_list)}")
                    lines.append(f"   توضیحات و یادداشت مربی: {doc.notes or 'بدون توضیح'}")
                    lines.append("")

                    for page_idx, fpath in enumerate(doc.file_paths_list, start=1):
                        if fpath and os.path.exists(fpath):
                            ext = os.path.splitext(fpath)[1]
                            clean_title = re.sub(r'[\\/*?:"<>|]', "", doc.title).strip().replace(" ", "_")
                            zip_internal_name = f"مدارک_پزشکی/{doc_idx}_{clean_title}_صفحه_{page_idx}{ext}"
                            zip_file.write(fpath, arcname=zip_internal_name)
                    doc_idx += 1

                lines.append("-" * 60)
                lines.append("باشگاه بدنسازی یلدا | مازندران، قائمشهر، خیابان کوچکسرا، نبش شقایق ۳")
                lines.append("=" * 60)

                txt_content = "\n".join(lines)
                zip_file.writestr("نظرات_و_سوابق_پزشکی_مربی.txt", txt_content.encode("utf-8-sig"))

            QMessageBox.information(
                self,
                "موفقیت",
                f"پکیج جامع پرونده و مدارک پزشکی «{member.full_name}» با موفقیت در فایل زیپ زیر ایجاد شد:\n\n{save_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "خطا در فشرده‌سازی", f"خطایی رخ داد: {str(e)}")
