import shutil
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QFrame
)
import config


class DataMigrationDialog(QDialog):
    """
    Dialog presented on startup if no existing yalda.db is found.
    Allows user to select previous version's data folder/file or start fresh.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("فراخوانی اطلاعات نسخه قبلی - نرم‌افزار یلدا")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(560, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.imported_successfully = False

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        # Header Icon & Title
        header_layout = QHBoxLayout()
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)

        title_label = QLabel("فراخوانی اطلاعات نسخه قبلی")
        title_label.setObjectName("h1")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        card_layout.addLayout(header_layout)

        # Description text
        desc_label = QLabel(
            "دیتابیس برنامه‌ای در این پوشه یافت نشد.\n\n"
            "اگر قبلاً از نرم‌افزار یلدا استفاده می‌کردید و فایل‌های نسخه قبل را در پوشه یا درایو دیگری دارید، "
            "می‌توانید اطلاعات قبلی خود را فراخوانی کنید تا تمامی داده‌ها و پرونده‌های شاگردان به این نسخه منتقل شوند."
        )
        desc_label.setWordWrap(True)
        desc_label.setObjectName("muted_text")
        card_layout.addWidget(desc_label)

        card_layout.addStretch()

        # Action Buttons
        self.btn_import = QPushButton("📁 فراخوانی پوشه data یا فایل yalda.db نسخه قبل")
        self.btn_import.setObjectName("primary_button")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.clicked.connect(self._on_import_clicked)

        self.btn_fresh = QPushButton("✨ شروع با نرم‌افزار خام (ایجاد دیتابیس جدید)")
        self.btn_fresh.setObjectName("secondary_button")
        self.btn_fresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fresh.clicked.connect(self._on_fresh_clicked)

        card_layout.addWidget(self.btn_import)
        card_layout.addWidget(self.btn_fresh)

        layout.addWidget(card)

    def _on_import_clicked(self):
        # Allow picking directory first
        msg = QMessageBox(self)
        msg.setWindowTitle("انتخاب روش فراخوانی")
        msg.setText("نحوه فراخوانی اطلاعات نسخه قبل را انتخاب کنید:")
        btn_folder = msg.addButton("انتخاب پوشه (data یا پوشه نسخه قبل)", QMessageBox.ButtonRole.AcceptRole)
        btn_file = msg.addButton("انتخاب مستقیم فایل yalda.db", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("انصراف", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_folder:
            selected_dir = QFileDialog.getExistingDirectory(
                self, "انتخاب پوشه data یا پوشه برنامه نسخه قبل"
            )
            if selected_dir:
                self._import_from_directory(Path(selected_dir))
        elif clicked == btn_file:
            selected_file, _ = QFileDialog.getOpenFileName(
                self, "انتخاب فایل yalda.db نسخه قبل", "", "SQLite Database (*.db);;All Files (*)"
            )
            if selected_file:
                self._import_from_file(Path(selected_file))

    def _import_from_directory(self, src_path: Path):
        # Look for data folder inside or if src_path IS data folder
        data_dir = src_path
        if (src_path / "data").exists():
            data_dir = src_path / "data"

        db_file = data_dir / "yalda.db"
        if not db_file.exists():
            QMessageBox.warning(
                self, "خطا در یافتن دیتابیس",
                f"فایل yalda.db در پوشه انتخاب‌شده ({data_dir.name}) یافت نشد.\nلطفاً پوشه صحیح را انتخاب کنید."
            )
            return

        try:
            for item in data_dir.iterdir():
                dest = config.DATA_DIR / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                elif item.is_file():
                    shutil.copy2(item, dest)

            self.imported_successfully = True
            QMessageBox.information(
                self, "موفقیت",
                "اطلاعات نسخه قبلی با موفقیت بازیابی و به این نسخه منتقل شد! 🚀"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "خطا در انتقال داده‌ها",
                f"خطایی هنگام کپی اطلاعات رخ داد:\n{str(e)}"
            )

    def _import_from_file(self, db_file: Path):
        try:
            shutil.copy2(db_file, config.DB_PATH)
            # If there's an uploads folder in the same parent dir, copy it too
            parent_uploads = db_file.parent / "uploads"
            if parent_uploads.exists() and parent_uploads.is_dir():
                for item in parent_uploads.iterdir():
                    dest = config.UPLOADS_DIR / item.name
                    if item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                    elif item.is_file():
                        shutil.copy2(item, dest)

            self.imported_successfully = True
            QMessageBox.information(
                self, "موفقیت",
                "فایل دیتابیس با موفقیت جایگزین شد! 🚀"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "خطا در کپی دیتابیس",
                f"خطایی هنگام کپی فایل رخ داد:\n{str(e)}"
            )

    def _on_fresh_clicked(self):
        # User explicitly chooses fresh install
        self.accept()
